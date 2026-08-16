# -*- coding: utf-8 -*-
"""从真实仿真配对数据提取轴向切片，生成 clean vs artifact 对比图。
输入：cbct_simulation/experiments/results/*/clean.nii.gz + artifact_L4.nii.gz
输出：demo_source/public/sim_slices/*_clean.png + *_artifact.png
只读分析 + 可视化，不产生科学结论。
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

ROOT = Path(r"D:\CT_competition")
RESULTS = ROOT / "cbct_simulation" / "experiments" / "results"
OUT = ROOT / "submission_materials" / "demo_source" / "public" / "sim_slices"

# 展示哪些实验（真实跑过的受控单因素 + 系统）
SHOW = [
    ("exp_depth_0.6mm", "深度 0.6 mm（单因素）"),
    ("exp_depth_1mm", "深度 1.0 mm（单因素）"),
    ("exp_pitch_1.6mm", "螺距 1.6 mm（单因素）"),
    ("exp_osstem_tsiii_baseline", "OSSTEM TSIII 基线"),
    ("exp_ti64_depth_0.6mm", "Ti-6Al-4V 深度 0.6 mm"),
]


def find_implant_slice(data, mask, pad=8):
    """在 mask 里找包含种植体的轴向切片（取种植体中心附近）。"""
    if mask is None:
        return data.shape[2] // 2
    mz = np.argwhere(mask > 0)
    if len(mz) == 0:
        return data.shape[2] // 2
    zmin, zmax = mz[:, 2].min(), mz[:, 2].max()
    mid = (zmin + zmax) // 2
    return int(np.clip(mid, 0, data.shape[2] - 1))


def norm_slice(slice_2d, lo, hi):
    if hi - lo < 1e-6:
        hi = lo + 1e-6
    return np.clip((slice_2d - lo) / (hi - lo), 0, 1)


def extract(name, label):
    exp = RESULTS / name
    clean_p = exp / "clean.nii.gz"
    art_p = exp / "artifact_L4.nii.gz"
    mask_p = exp / "metal_mask.nii.gz"
    if not clean_p.exists() or not art_p.exists():
        print(f"  SKIP {name}: missing files")
        return None

    clean = nib.load(str(clean_p)).get_fdata()
    art = nib.load(str(art_p)).get_fdata()
    mask = None
    if mask_p.exists():
        mask = nib.load(str(mask_p)).get_fdata()

    # 找到种植体中心切片
    z = find_implant_slice(art, mask)
    # 取包含种植体与周围伪影带的区域（大裁剪：保留牙弓上下文）
    if mask is not None:
        mz = np.argwhere(mask > 0)
        if len(mz):
            ymin, ymax = mz[:, 0].min(), mz[:, 0].max()
            xmin, xmax = mz[:, 1].min(), mz[:, 1].max()
            cy, cx = (ymin + ymax) // 2, (xmin + xmax) // 2
            r = max(ymax - ymin, xmax - xmin) // 2 + 55
            r = int(np.clip(r, 55, 110))
            crop = (slice(cy - r, cy + r), slice(cx - r, cx + r))
        else:
            crop = (slice(None), slice(None))
    else:
        crop = (slice(None), slice(None))

    # 关键修复：共用同一显示窗口（取 clean 的 p2/p98），
    # 使 artifact 的伪影（暗带/亮纹）在对比中真实可见，
    # 而不是各自归一化把差异抹平。金属自然饱和为白。
    c_full = clean[:, :, z]
    lo, hi = np.percentile(c_full, [2, 98])
    print(f"  {name}: z={z} shared window=[{lo:.3f}, {hi:.3f}]")

    c_slice = norm_slice(clean[:, :, z][crop], lo, hi)
    a_slice = norm_slice(art[:, :, z][crop], lo, hi)
    m_slice = mask[:, :, z][crop] if mask is not None else None

    # clean 图（英文标题，避免 CJK 字体问题）
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.imshow(c_slice.T, cmap="gray", origin="lower")
    if m_slice is not None:
        overlay = np.zeros((*m_slice.T.shape, 4))
        mm = m_slice.T > 0
        overlay[mm] = (0.95, 0.2, 0.1, 0.85)
        ax.imshow(overlay, origin="lower")
    ax.set_title("Clean (no metal)", fontsize=10)
    ax.axis("off")
    plt.tight_layout()
    clean_out = OUT / f"{name}_clean.png"
    fig.savefig(clean_out, dpi=110, bbox_inches="tight")
    plt.close(fig)

    # artifact 图
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.imshow(a_slice.T, cmap="gray", origin="lower")
    if m_slice is not None:
        overlay = np.zeros((*m_slice.T.shape, 4))
        mm = m_slice.T > 0
        overlay[mm] = (0.95, 0.2, 0.1, 0.85)
        ax.imshow(overlay, origin="lower")
    ax.set_title("Artifact (metal, L4 full physics)", fontsize=10)
    ax.axis("off")
    plt.tight_layout()
    art_out = OUT / f"{name}_artifact.png"
    fig.savefig(art_out, dpi=110, bbox_inches="tight")
    plt.close(fig)

    return {
        "key": name,
        "label": label,
        "clean": f"sim_slices/{name}_clean.png",
        "artifact": f"sim_slices/{name}_artifact.png",
        "slice": int(z),
        "size": c_slice.shape,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, label in SHOW:
        print("processing", name)
        r = extract(name, label)
        if r:
            entries.append(r)

    index = {"experiments": entries}
    idx_out = ROOT / "submission_materials" / "demo_source" / "public" / "sim_index.json"
    with open(idx_out, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"saved index: {idx_out} ({len(entries)} entries)")
    print("done")


if __name__ == "__main__":
    main()
