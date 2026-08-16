"""
实时仿真执行器：给定 STL + 参数 → 生成 mask → 仿真 → 算指标。

这是 env.step 的核心：Agent 提出的每个新参数组合，
都触发一次真实仿真（生成 STL → mask → simulate_poly → 球壳MAE）。

用法:
  from cbct_simulation.explore.run_simulation import simulate_params

  result = simulate_params(thread_depth_mm=0.5, thread_pitch_mm=1.4,
                           material='CoCr', out_dir=Path(...))
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np

from scripts.project_config import EXPLORE_DIR, EXPLORE_RESULTS, DATAS_DIR, OUTPUTS_DIR

BASE = EXPLORE_DIR
RESULTS_DIR = EXPLORE_RESULTS
CASE24_CBCT = DATAS_DIR / "Training_Set" / "YOFO_No_Metal" / "YOFO_No_Metal_24.nii.gz"
PLACEMENT_BASE = OUTPUTS_DIR / "case24_phase2b_depth_search"


def _rasterize_stl(stl_path: Path, out_dir: Path, placement_json: Path) -> Path:
    """用 generate_implant_mask_from_cad 生成 mask"""
    mask_path = out_dir / "metal_mask.nii.gz"
    cmd = [
        sys.executable,
        "-m", "cbct_simulation.generate_implant_mask_from_cad",
        "--cbct", str(CASE24_CBCT),
        "--stl", str(stl_path),
        "--output", str(mask_path),
        "--transform-json", str(placement_json),
        "--backend", "voxelized",
        "--sampling-pitch-mm", "0.1",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return mask_path


def _simulate(mask_path: Path, material: str, out_dir: Path) -> None:
    """调 simulate_poly 跑完整仿真"""
    cmd = [
        sys.executable,
        "-m", "cbct_simulation.simulate_poly",
        "--mask", str(mask_path),
        "--material", material,
        "--output-dir", str(out_dir),
        "--full",
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _compute_metrics(artifact_path: Path, clean_path: Path, mask_path: Path) -> dict:
    """算 0-2mm 球壳 MAE + S/V"""
    from scipy.ndimage import distance_transform_edt
    from skimage import measure

    art = nib.load(str(artifact_path)).get_fdata().astype(np.float64)
    clean = nib.load(str(clean_path)).get_fdata().astype(np.float64)
    mask = nib.load(str(mask_path)).get_fdata().astype(bool)

    if art.shape != clean.shape:
        clean = np.transpose(clean, (2, 1, 0))
    if mask.shape != clean.shape:
        mask = np.transpose(mask, (2, 1, 0))

    sp = [0.2, 0.2, 0.2]
    dist = distance_transform_edt(~mask, sampling=sp)
    diff = art - clean
    ring02 = (dist > 0) & (dist <= 2)
    shell_0_2 = float(np.abs(diff[ring02]).mean()) if ring02.sum() > 0 else None

    # S/V
    verts, faces, _, _ = measure.marching_cubes(mask, spacing=sp)
    sa = 0.0
    for f in faces:
        v0, v1, v2 = verts[f[0]], verts[f[1]], verts[f[2]]
        sa += 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))
    vol = int(mask.sum()) * (0.2 ** 3)
    sv = sa / (vol + 1e-8)

    return {
        "shell_0_2mm": shell_0_2,
        "sv_ratio": round(sv, 3),
        "surface_area_mm2": round(sa, 2),
        "volume_mm3": round(vol, 2),
        "mu_max": round(float(art.max()), 2),
        "metal_voxels": int(mask.sum()),
    }


def simulate_params(
    thread_depth_mm: float,
    thread_pitch_mm: float,
    material: str,
    out_dir: Path | None = None,
    offset_mm: float | None = None,
) -> dict:
    """
    完整执行一次仿真，返回指标。

    offset_mm: 植入深度偏移（mm）。None 用默认 offset_plus0.5（13组同款）
    其他值映射到 phase2b 的 placement（-1.0/-0.5/0/+0.5/+1.0）

    out_dir 若为 None，自动创建带时间戳的目录。
    """
    from cbct_simulation.explore.generate_stl import generate_stl_for_params

    if out_dir is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_dir = RESULTS_DIR / f"sim_d{thread_depth_mm:.2f}_p{thread_pitch_mm:.2f}_{material}_{ts}"

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 生成 STL
    stl_path = generate_stl_for_params(thread_depth_mm, thread_pitch_mm, out_dir)

    # 2. 生成 mask（按 offset 选择 placement）
    if offset_mm is not None:
        # phase2b 目录名格式: offset_plus0.5 / offset_minus0.5 / offset_plus0.0
        sign = "plus" if offset_mm >= 0 else "minus"
        offset_dir = f"offset_{sign}{abs(offset_mm):.1f}"
        placement_json = PLACEMENT_BASE / offset_dir / "placement.json"
        if not placement_json.exists():
            raise FileNotFoundError(f"placement 不存在: {placement_json}")
    else:
        placement_json = PLACEMENT_BASE / "offset_plus0.5" / "placement.json"
    mask_path = _rasterize_stl(stl_path, out_dir, placement_json)

    # 3. 仿真
    sim_dir = out_dir / "sim"
    _simulate(mask_path, material, sim_dir)

    # 4. 算指标
    metrics = _compute_metrics(sim_dir / "artifact_L4.nii.gz",
                               sim_dir / "clean.nii.gz",
                               mask_path)

    # 5. 投影域指标（仿真中间产物，轻量，顺手提取）
    proj_file = sim_dir / "projection_metrics.json"
    proj = {}
    if proj_file.exists():
        try:
            proj = json.loads(proj_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 保存结果（含投影域）
    result = {
        "thread_depth_mm": thread_depth_mm,
        "thread_pitch_mm": thread_pitch_mm,
        "material": material,
        "offset_mm": offset_mm,
        "stl": str(stl_path),
        "mask": str(mask_path),
        **metrics,
        # 投影域摘要（轻量，不用大数据 CSV）
        "metal_ray_ratio": proj.get("metal_ray_ratio"),
        "path_len_max": proj.get("path_len_max"),
        "path_len_mean": proj.get("path_len_mean"),
        "path_len_std": proj.get("path_len_std"),
        "angle_max_TV": proj.get("angle_max_TV"),
        "n_angles": proj.get("n_angles"),
    }
    (out_dir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 清理大数据文件（投影逐角度 CSV ~1MB，删掉）
    csv_file = sim_dir / "projection_by_angle.csv"
    if csv_file.exists():
        csv_file.unlink(missing_ok=True)
    return result


if __name__ == "__main__":
    r = simulate_params(0.5, 1.4, "CoCr")
    print(json.dumps(r, indent=2))
