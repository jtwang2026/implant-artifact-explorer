"""
探索环境：种植体几何参数 → CBCT 金属伪影（查表 + 实时仿真混合）

已知格点（13 组严格单因素 + A/B 对照）走查表快路径；
未知格点提交到异步任务队列，后台真实仿真，结果回流后并入格点。

观测（observation）:
  - thread_depth_mm / thread_pitch_mm / material
  - sv_ratio: 表面/体积比（几何复杂度）
  - shell_0_2mm: 0-2mm 球壳 MAE（伪影强度）
  - bone_ratio: 埋骨率（协变量，用于判断角度/位置混杂）
  - normal_entropy: 法向熵

动作（action）:
  选择一组几何参数 (thread_depth_mm, thread_pitch_mm, material)

奖励（reward）:
  发现型奖励——优先探索偏离已知 S/V→MAE 关系的点（潜在反例/边界）。
  环境规则：已知关系（CoCr/Ti64 各自线性）作为基线，残差大 → 奖励高。
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from cbct_simulation.explore.task_queue import SimulationTaskQueue
from scripts.project_config import CONTROLLED_CSV, EXPLORE_DIR

BASE = EXPLORE_DIR.parent.parent

MATERIALS = ["CoCr", "Ti64"]

# 探索空间边界（用于提示 Agent 合法性）
DEPTH_RANGE = (0.0, 1.5)
PITCH_RANGE = (0.4, 3.0)


def offsets_equal(a, b, tol: float = 1e-3) -> bool:
    """None-safe offset comparison shared by lookup and result merging."""
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) < tol


class ImplantArtifactEnv:
    """种植体几何 → 伪影 探索环境（查表 + 实时仿真混合）"""

    def __init__(self, csv_path: Path | None = None,
                 n_workers: int = 2,
                 known_only: bool = False):
        """
        known_only=True 时只用查表（测试用，不启动真实仿真）。
        """
        self.csv_path = csv_path or CONTROLLED_CSV
        self.known_only = known_only
        self.grid = self._load_grid()
        self.history = []  # 已探索格点记录
        self.queue = None if known_only else SimulationTaskQueue(n_workers=n_workers)
        self._line = None  # 已知 S/V→MAE 线性基线（按材料）

    # ---------- 数据加载 ----------

    def _load_grid(self) -> list[dict]:
        """从统一受控表加载已知格点（13 组单因素 + A/B 对照）"""
        rows = []
        with open(self.csv_path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["dir"].startswith("implant_case"):  # A/B 对照
                    continue
                try:
                    row = {
                        "thread_depth_mm": self._label_to_depth_pitch(r["dir"])[0],
                        "thread_pitch_mm": self._label_to_depth_pitch(r["dir"])[1],
                        "material": r["material"],
                        "offset_mm": 0.5,  # 13 组全部用 offset_plus0.5 placement
                        "sv_ratio": float(r["sv_ratio"]),
                        "shell_0_2mm": float(r["shell_0_2mm"]),
                        "bone_ratio": float(r["bone_ratio"]) if r.get("bone_ratio") not in ("", "None") else None,
                        "normal_entropy": float(r["normal_entropy"]) if r.get("normal_entropy") not in ("", "None") else None,
                        "surface_area_mm2": float(r["surface_area_mm2"]) if r.get("surface_area_mm2") not in ("", "None") else None,
                        "volume_mm3": float(r["volume_mm3"]) if r.get("volume_mm3") not in ("", "None") else None,
                        "source": "controlled",
                    }
                    rows.append(row)
                except (ValueError, KeyError, TypeError):
                    continue
        # 去重（pitch_0.8 与 depth_0.6 是同一实验）
        seen = set()
        unique = []
        for r in rows:
            key = (r["thread_depth_mm"], r["thread_pitch_mm"], r["material"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def _label_to_depth_pitch(self, label: str) -> tuple[float, float]:
        """从实验目录名解析 (depth, pitch)。13 组固定：depth 扫描 pitch=0.8，pitch 扫描 depth=0.6"""
        if "depth_" in label:
            try:
                return float(label.split("depth_")[1].split("mm")[0]), 0.8
            except (IndexError, ValueError):
                pass
        if "pitch_" in label:
            try:
                return 0.6, float(label.split("pitch_")[1].split("mm")[0])
            except (IndexError, ValueError):
                pass
        return 0.6, 0.8  # 兜底（exp_osstem_tsiii_baseline）

    # ---------- 已知关系基线 ----------

    def _fit_line(self):
        """按材料拟合 S/V→shell 线性基线（CoCr / Ti64）"""
        if self._line is not None:
            return self._line
        self._line = {}
        for mat in MATERIALS:
            pts = [
                g for g in self.grid
                if g.get("material") == mat
                and g.get("sv_ratio") is not None
                and g.get("shell_0_2mm") is not None
            ]
            if len(pts) >= 3:
                sv = np.array([g["sv_ratio"] for g in pts])
                sh = np.array([g["shell_0_2mm"] for g in pts])
                slope, intercept = np.polyfit(sv, sh, 1)
                r2 = 1 - np.sum((sh - (slope * sv + intercept)) ** 2) / \
                    np.sum((sh - sh.mean()) ** 2)
                self._line[mat] = {"slope": float(slope), "intercept": float(intercept),
                                   "r2": float(r2), "n": len(pts)}
        return self._line

    def _expected_shell(self, mat: str, sv: float) -> float | None:
        """已知基线预测的 shell（铁律预测值）"""
        line = self._fit_line().get(mat)
        if line is None:
            return None
        return line["slope"] * sv + line["intercept"]

    # ---------- 环境接口 ----------

    def reset(self) -> dict:
        """重置：返回一个已知格点作为初始观测"""
        self.history = []
        obs = self.grid[0].copy()
        obs["in_grid"] = True
        self.history.append(obs)
        return obs

    def available_points(self) -> list[dict]:
        """返回所有已知格点"""
        return list(self.grid)

    def pending_params(self) -> list[dict]:
        """进行中仿真任务的参数（Agent 感知用，避免重复提交）"""
        if self.queue is None:
            return []
        return self.queue.pending_params()

    def poll_results(self) -> list[dict]:
        """检查已完成的仿真任务，把结果并入格点。返回新完成的格点"""
        if self.queue is None:
            return []

        results = self.queue.completed_results()
        merged = []
        for res in results:
            key = (float(res["thread_depth_mm"]), float(res["thread_pitch_mm"]), res["material"])
            off = res.get("offset_mm", 0.5)  # 旧 result 无此字段时默认 0.5；字段存在但为 None 时保持 None
            if any(abs(g["thread_depth_mm"] - key[0]) < 1e-3 and
                   abs(g["thread_pitch_mm"] - key[1]) < 1e-3 and
                   g["material"] == key[2] and
                   offsets_equal(g.get("offset_mm"), off) for g in self.grid):
                continue  # 已在格点
            g = {
                "thread_depth_mm": key[0],
                "thread_pitch_mm": key[1],
                "material": key[2],
                "offset_mm": off,
                "sv_ratio": res.get("sv_ratio"),
                "shell_0_2mm": res.get("shell_0_2mm"),
                "bone_ratio": res.get("bone_ratio"),
                "normal_entropy": res.get("normal_entropy"),
                "surface_area_mm2": res.get("surface_area_mm2"),
                "volume_mm3": res.get("volume_mm3"),
                "mu_max": res.get("mu_max"),
                "metal_voxels": res.get("metal_voxels"),
                # 投影域指标（2026-08-03 新增，从仿真中间产物提取）
                "metal_ray_ratio": res.get("metal_ray_ratio"),
                "path_len_max": res.get("path_len_max"),
                "path_len_mean": res.get("path_len_mean"),
                "path_len_std": res.get("path_len_std"),
                "angle_max_TV": res.get("angle_max_TV"),
                "source": "simulated",
                "task_id": None,
            }
            # 从 stl 路径提取 task 名（容错：可能为空或格式不同）
            stl = res.get("stl") or ""
            parts = str(stl).replace("\\", "/").split("/")
            if len(parts) >= 2 and parts[-2]:
                g["task_id"] = parts[-2]
            # 计算残差（新探索点偏离铁律的程度）
            sv = g.get("sv_ratio")
            sh = g.get("shell_0_2mm")
            if sv is not None and sh is not None:
                expected = self._expected_shell(g["material"], sv)
                g["residual"] = round(abs(sh - expected), 4) if expected else None
            self.grid.append(g)
            merged.append(g)
        return merged

    def step(self, action: dict) -> tuple[dict, float, bool]:
        """
        执行动作：选择 (depth, pitch, material)。
        已知格点 → 查表返回（快路径）
        未知格点 → 提交队列（异步仿真），返回"已提交"观测
        Returns: (observation, reward, done)
        """
        depth = float(action.get("thread_depth_mm", 0.6))
        pitch = float(action.get("thread_pitch_mm", 0.8))
        material = action.get("material", "CoCr")
        offset = action.get("offset_mm", 0.5)  # 默认 0.5（13组基准），Agent 可探索其他值
        if material not in MATERIALS:
            material = "CoCr"
        if offset is not None:
            offset = float(offset)

        # 查已知格点（含 offset 匹配）
        for g in self.grid:
            if (abs(g["thread_depth_mm"] - depth) < 1e-3 and
                abs(g["thread_pitch_mm"] - pitch) < 1e-3 and
                    g["material"] == material and
                    offsets_equal(g.get("offset_mm", 0.5), offset)):
                reward = self._novelty_reward(g)
                obs = {**g, "in_grid": True}
                self.history.append(obs)
                return obs, reward, False  # done=False：探索继续

        # 未知格点：提交队列（或标记未探索）
        if self.known_only:
            obs = {"thread_depth_mm": depth, "thread_pitch_mm": pitch,
                   "material": material, "offset_mm": offset,
                   "in_grid": False, "queued": False,
                   "sv_ratio": None, "shell_0_2mm": None}
            return obs, 0.0, True

        task_id = self.queue.submit(depth, pitch, material, offset_mm=offset)
        obs = {"thread_depth_mm": depth, "thread_pitch_mm": pitch,
               "material": material, "offset_mm": offset,
               "in_grid": False, "queued": task_id is not None,
               "task_id": task_id,
               "sv_ratio": None, "shell_0_2mm": None,
               "note": "已提交后台仿真，结果将异步回流"}
        self.history.append(obs)
        return obs, 0.0, False  # 不结束，等结果回流

    # ---------- 奖励 ----------

    def _novelty_reward(self, point: dict) -> float:
        """
        发现型奖励：
        - 偏离已知 S/V→MAE 线性基线的程度（反例/边界残差）
        - 新颖性：距最近已探索点的 S/V 距离
        - 已知基线（铁律）作为环境规则：偏离越大越有价值
        """
        sv = point.get("sv_ratio")
        shell = point.get("shell_0_2mm")
        if sv is None or shell is None:
            return 0.0

        # 对已知基线的残差（该材料自己的线）
        expected = self._expected_shell(point["material"], sv)
        residual = abs(shell - expected) if expected is not None else 0.0

        # 新颖性：距最近已探索点（含已知格点）的 S/V 距离
        novelty = 0.0
        all_sv = [g["sv_ratio"] for g in self.grid if g.get("sv_ratio")]
        if all_sv:
            novelty = min(abs(np.array(all_sv) - sv))
        else:
            novelty = 1.0

        # 组合：残差为主（0.7），新颖性为辅（0.3）
        reward = 0.7 * residual + 0.3 * novelty
        return float(reward)

    def _indicator_ranking(self) -> dict:
        """候选指标解释力排名（R² vs shell_0_2mm, n≥3）"""
        candidates = [
            ("surface_area_mm2", "表面积 (独立值)"),
            ("sv_ratio",         "S/V (几何复杂度)"),
            ("volume_mm3",       "体积"),
            ("bone_ratio",       "埋骨率"),
            ("path_len_mean",    "投影路径均值"),
            ("metal_ray_ratio",  "金属投影比"),
            ("angle_max_TV",     "投影角度变差"),
        ]
        ranking = {}
        for key, label in candidates:
            pairs = [(g.get(key), g["shell_0_2mm"]) for g in self.grid
                     if g.get(key) is not None and g.get("shell_0_2mm")]
            if len(pairs) < 3:
                ranking[key] = {"label": label, "n": len(pairs), "r2": None}
                continue
            x = np.array([p[0] for p in pairs])
            y = np.array([p[1] for p in pairs])
            slope, intercept = np.polyfit(x, y, 1)
            r2 = 1 - np.sum((y - slope * x - intercept) ** 2) / np.sum((y - np.mean(y)) ** 2)
            ranking[key] = {"label": label, "n": len(pairs), "r2": float(r2)}
        return ranking

    def _offset_hint(self) -> str:
        """动态提示：几何空间是否饱和，建议探索 offset"""
        n_geom = sum(1 for g in self.grid if g.get("offset_mm") == 0.5)
        n_off = sum(1 for g in self.grid if g.get("offset_mm") not in (None, 0.5))
        if n_geom > 15 and n_off == 0:
            return (f"  ⚠️ 几何空间已 {n_geom} 点，但 offset 维度零探索！\n"
                    f"    强烈建议：探索 offset ∈ {{-1.0, -0.5, 0.0, +1.0}} 检验埋骨率→伪影关系")
        return ""

    def summary(self) -> str:
        """生成探索摘要（供 Agent 参考）：已知格点 + 已知基线 + 探索空间"""
        lines = []
        lines.append("=== 已知格点 (depth, pitch, material, S/V, shell_0_2mm, bone_ratio) ===")
        for g in self.grid:
            lines.append(
                f"  d={g['thread_depth_mm']:.1f} p={g['thread_pitch_mm']:.1f} "
                f"{g['material']:4s} S/V={g['sv_ratio']:.3f} shell={g['shell_0_2mm']:.3f} "
                f"bone={g.get('bone_ratio', '?')}"
            )
        lines.append("")
        lines.append("=== 已知铁律（环境规则，按材料）===")
        for mat, line in self._fit_line().items():
            lines.append(
                f"  {mat}: shell = {line['slope']:.4f} × S/V + {line['intercept']:.4f}  "
                f"(R²={line['r2']:.3f}, n={line['n']})"
            )
        lines.append("")
        lines.append(f"=== 探索空间 ===")
        lines.append(f"  depth ∈ [{DEPTH_RANGE[0]}, {DEPTH_RANGE[1]}] mm")
        lines.append(f"  pitch ∈ [{PITCH_RANGE[0]}, {PITCH_RANGE[1]}] mm")
        lines.append(f"  material ∈ {MATERIALS}")
        lines.append(f"  offset ∈ {{-1.0, -0.5, 0.0, +0.5, +1.0}} mm（植入深度，13组基准=+0.5）")
        lines.append("  ⚠️ offset 是待探索维度：埋骨率随 offset 变化（52%→72%），")
        lines.append("     可检验 '埋骨率→伪影' 关系（当前只有 13 组固定 offset 的点）")
        lines.append("")
        lines.append("=== 候选指标解释力排名（R² vs shell, n≥3）===")
        rank = self._indicator_ranking()
        sorted_rank = sorted(rank.items(), key=lambda x: x[1].get("r2") or -1, reverse=True)
        for key, info in sorted_rank:
            if info["r2"] is not None:
                lines.append(f"  {info['label']:12s}: R²={info['r2']:.4f} (n={info['n']})")
            else:
                lines.append(f"  {info['label']:12s}: 待补 (n={info['n']})")
        lines.append("")
        lines.append("=== 已知线索（背景知识）===")
        lines.append("  - 角度 15° 疑似增强过冲（BLC 0°/15° 埋骨率 54%/58% 接近，shell 0.971→0.989）")
        lines.append("  - 30° 因埋骨率下降（49%）有混杂，不可当角度效应")
        lines.append("  - ⚠️ 数据审计：22 组系统消融实际在右侧切牙/尖牙区（非磨牙），只用于组内相对比较，见 docs/fdi_placement_audit.md")
        lines.append("  - dark% 恒定 ~10%，由物理参数主导，探索价值低")
        hint = self._offset_hint()
        if hint:
            lines.append(hint)
        return "\n".join(lines)


if __name__ == "__main__":
    env = ImplantArtifactEnv(known_only=True)
    print(f"已加载 {len(env.grid)} 个已知格点")
    print(env.summary())
