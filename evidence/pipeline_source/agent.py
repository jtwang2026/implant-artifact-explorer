"""
LLM 探索 Agent（Qwen via SiliconFlow）

Agent 收到环境摘要 + 已知格点 + 进行中任务 + 当前观测，决定下一组几何参数。
探索目标是发现型信号：找到偏离已知 S/V→MAE 铁律的点（反例/边界/新现象）。

关键改进（v2）:
  - 进行中任务感知：prompt 列出已提交未完成的仿真，禁止重复提交
  - 决策理由（reasoning）：每步记录"为什么选这个点"，构成探索日志的推理链
  - 已探索点作为硬约束：避免重复探索（此前 v1 的 step3 重复 step1 问题）

API Key 通过环境变量 SILICONFLOW_KEY 传入，不写入代码。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
import urllib.request
from typing import Any

MODEL = "Qwen/Qwen3.6-35B-A3B"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

# ===== Prompt 版本控制（科研规范 P3）=====
# v1.0 初版：探索目标 = 找偏离 S/V→MAE 铁律的点；无进行中任务感知
# v2.0 加：进行中任务禁重复、reasoning 字段、已探索点硬约束
# v2.1 加：35B 模型、max_tokens 2000、禁 thinking（修复截断）
# v2.2 加：拒绝-重试机制（选重复点被拒后重新决策）
# v2.3 加：探索策略建议区（外推/边界/组合/Ti64轴）；禁区列表强化标注
# v3.0 当前：串行自适应模式适配（决策→等结果→再决策）
PROMPT_VERSION = "3.0"

SYSTEM_PROMPT = """你是材料成像科学探索Agent。你的任务是探索种植体几何参数与CBCT金属伪影的关系。

环境信息：
- 每个点用 (螺纹深度 thread_depth_mm, 螺距 thread_pitch_mm, 材料 material, 植入深度 offset_mm) 标识
- S/V = 表面/体积比（几何复杂度指标）
- shell_0_2mm = 0-2mm 球壳MAE（伪影强度，越大伪影越强）
- bone_ratio = 埋骨率（种植体埋在骨头里的比例，是混杂变量，随 offset 变化）
- offset_mm ∈ {-1.0, -0.5, 0.0, +0.5, +1.0}（植入深度；已知13组全部在 +0.5）

已知铁律（环境规则，已验证）：
- 在固定材料内，S/V 与 shell_0_2mm 大致线性（CoCr 和 Ti64 各一条线，斜率不同）
- 材料会改变"S/V 影响伪影的力度"（CoCr 斜率 > Ti64 斜率）

你的探索目标：找到偏离已知线性关系的格点，即反例、异常或规律边界。
这些点最有科学价值——说明可能存在未结构化的新现象。

探索策略（建议从这些区域选新点）:
1. 沿已知线外推：depth 已测 0.2~1.0，可试 1.1~1.5（外推边界）
2. pitch 边界：已测 0.8~2.4，可试 0.4~0.7 或 2.5~3.0（超细/超粗螺距）
3. 组合区：depth 和 pitch 同时变的组合大多未测（当前只测了单变量扫描）
4. Ti64 材料：目前只测了 depth 轴（pitch=0.8 固定），Ti64 的 pitch 轴完全未探索

⚠️ 残差信号（关键）：残差 > 0.025 表示该点偏离 S/V 铁律——这是规律松动的候选信号，
   值得深挖！发现偏离点后应优先在其邻近区域探索，验证是局部松动还是系统性效应。

探索纪律（必须遵守，违反会被拒绝）:
1. 你选择的新点必须满足：不在"已知格点（已探索过）"列表中，也不在"进行中的仿真任务"列表中。
   "已知格点"是禁区，不是候选——严禁从这里选。
2. 每次选择必须给出 reasoning（决策理由），说明你为什么怀疑这个点有价值
3. 材料只能是 CoCr 或 Ti64
"""


class SiliconFlowClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def chat(self, messages: list[dict], max_tokens: int = 2000) -> str:
        req = urllib.request.Request(
            API_URL,
            data=json.dumps({
                "model": MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "thinking": {"type": "disabled"},
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"__ERROR__: {e}"


def parse_action(text: str) -> dict | None:
    """从 LLM 输出解析 JSON 动作（含 reasoning）"""
    if "__ERROR__" in text:
        return None
    # 提取 JSON 块（可能是 ```json ... ``` 包裹，也可能是裸 JSON）
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        action = json.loads(m.group(0))
        return {
            "thread_depth_mm": float(action.get("thread_depth_mm", 0.6)),
            "thread_pitch_mm": float(action.get("thread_pitch_mm", 0.8)),
            "material": action.get("material", "CoCr"),
            "offset_mm": float(action["offset_mm"]) if action.get("offset_mm") is not None else 0.5,
            "reasoning": str(action.get("reasoning", "")).strip(),
        }
    except Exception:
        return None


class ExploreAgent:
    def __init__(self, api_key: str, env_summary: str, max_steps: int = 10):
        self.client = SiliconFlowClient(api_key)
        self.env_summary = env_summary
        self.max_steps = max_steps
        self.log = []  # 探索日志（含 reasoning）

    def decide(self, observation: dict, step: int,
               pending: list[dict] | None = None,
               known_keys: list[tuple] | None = None,
               rejected: list[str] | None = None) -> dict | None:
        """
        基于观测 + 进行中任务 + 已知格点 决定下一动作。

        pending: 进行中任务的参数列表（禁重复提交）
        known_keys: 已完成的 (depth, pitch, material) 列表（禁重复探索）
        rejected: 本步已拒绝的动作描述（重试提示）
        """
        history_text = "\n".join(
            f"  step {i}: 选了 {json.dumps(h.get('action', {}), ensure_ascii=False)}"
            f" → 结果 {json.dumps(h.get('observation', {}), ensure_ascii=False)[:120]}"
            for i, h in enumerate(self.log)
        ) or "  （尚未探索）"

        pending_text = "\n".join(
            f"  - d={p.get('thread_depth_mm')} p={p.get('thread_pitch_mm')} {p.get('material')}"
            for p in (pending or [])
        ) or "  （无）"

        known_text = ""
        if known_keys:
            lines = []
            for d, p, m, off in known_keys:
                off_str = f"{off:.1f}" if off is not None else "None"
                lines.append(f"  d={d:.1f} p={p:.1f} {m} of={off_str}")
            known_text = "\n".join(lines[:25])  # 防过长

        rejected_text = ""
        if rejected:
            rejected_text = "\n".join(f"  - {r}" for r in rejected[-5:])

        reject_hint = ""
        if rejected_text:
            reject_hint = "❌ 你上一次选择被拒绝了（重复），请换一个不同的点：\n" + rejected_text

        user_msg = f"""当前是第 {step}/{self.max_steps} 步探索。

⚠️ 硬约束：你选择的新点必须不在下面的"禁区"和"进行中任务"两个列表里，否则动作会被拒绝。禁区列表仅供参考，严禁从中选择。

🔴 禁区（已探索过，严禁选择）：
{known_text if known_text else '  （无）'}

🟡 进行中的仿真任务（请勿重复提交）：
{pending_text}

已探索的历史：
{history_text}

{reject_hint}
环境全貌：
{self.env_summary}

请从探索策略建议的区域中选择一组尚未探索的几何参数。输出 JSON:
{{"thread_depth_mm": 1.2, "thread_pitch_mm": 1.2, "material": "CoCr", "reasoning": "为什么选这个点的简要说明"}}
"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        text = self.client.chat(messages)
        action = parse_action(text)
        if action is None:
            print(f"  [agent] 输出无法解析: {text[:200]}")
        return action

    def summarize(self, known_keys: list[tuple] | None = None) -> str:
        """探索结束后，基于全部结果生成 Agent 自主总结（观察/信号/下一步建议）。

        2026-08-04 新增：让 Agent 自己对本轮探索做分析和总结（层次 2 分析能力的第一步），
        与人工统计结论并列可对比。独立审计 Agent 另设，防自我确认。
        """
        if not self.log:
            return ""
        known_text = ""
        if known_keys:
            lines = []
            for d, p, m, off in known_keys:
                off_str = f"{off:.1f}" if off is not None else "None"
                lines.append(f"  d={d:.1f} p={p:.1f} {m} of={off_str}")
            known_text = "\n".join(lines[:40])  # 防过长
        history_text = "\n".join(
            f"  step {i}: 选了 {json.dumps(h.get('action', {}), ensure_ascii=False)}"
            f" → 结果 {json.dumps(h.get('observation', {}), ensure_ascii=False)[:150]}"
            for i, h in enumerate(self.log)
        ) or "  （无探索记录）"

        summary_system = (
            "你是一个在物理仿真环境中自主探索的科研 Agent。你的任务是：基于本轮探索的完整"
            "记录，客观总结你观察到什么、证据支持或挑战了什么、下一步该验证什么。诚实第一："
            "只总结数据实际支持的内容，不夸大、不编造；没有结论就如实说'证据不足'。"
        )
        user_msg = f"""本轮探索已结束（共 {len(self.log)} 步）。请写一份简短的本轮探索总结（300 字以内，中文），包含：
1. 你选了什么点、为什么（选点策略）
2. 你观察到了什么模式或信号（结合所有点的结果）
3. 哪些证据支持或挑战了已知铁律（S/V→shell 线性）
4. 下一步最值得验证的假设或区域

已知格点（含本轮新增）：
{known_text}

你的探索历史：
{history_text}

环境全貌：
{self.env_summary}
"""
        messages = [
            {"role": "system", "content": summary_system},
            {"role": "user", "content": user_msg},
        ]
        try:
            text = self.client.chat(messages)
            return text.strip()
        except Exception as e:
            print(f"  [agent] 总结失败: {e}")
            return ""

    def record(self, step: int, action: dict, observation: dict, reward: float):
        self.log.append({
            "step": step,
            "action": action,
            "reasoning": action.get("reasoning", "") if action else "",
            "observation": observation,
            "reward": reward,
        })

    def save_partial_log(self, path: Path, report_extra: dict | None = None):
        """
        实时落盘：把当前探索进度写入日志文件（每步决策后调用）。
        这样即使进程被杀/中断，已完成的决策链也不会丢。
        """
        report = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            "model": MODEL,
            "prompt_version": PROMPT_VERSION,
            "status": "partial",
            "log": self.log,
            **(report_extra or {}),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
