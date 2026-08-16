# -*- coding: utf-8 -*-
"""伪影差分可视化（真实配对数据，无需新仿真）
对模块一的 clean + artifact_L4 真实配对，生成：
  1. 差分热图（artifact - clean，暖=亮伪影 冷=暗伪影）
  2. 剖面线对比（穿过种植体，clean vs artifact 强度曲线）
  3. 距离-伪影分布（按距金属表面距离分环，对应 shell 指标）
输出到 demo public，供 /sim 页面展示。
"""
import json
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(r"D:\CT_competition")
RESULTS = ROOT / "cbct_simulation" / "experiments" / "results"
OUT = ROOT / "submission_materials" / "demo_source" / "public" / "sim_diff"
OUT.mkdir(parents=True, exist_ok=True)

EXPS = [
    ("exp_depth_0.6mm", "深度 0.6 mm"),
    ("exp_depth_1mm", "深度 1.0 mm"),
    ("exp_pitch_1.6mm", "螺距 1.6 mm"),
    ("exp_osstem_tsiii_baseline", "OSSTEM TSIII"),
    ("exp_ti64_depth_0.6mm", "Ti-6Al-4V"),
]

Z_SLICE = 167


def norm(x, lo, hi):
    return np.clip((x - lo) / (hi - lo + 1e-6), 0, 1)


def load_pair(name):
    exp = RESULTS / name
    clean = nib.load(str(exp / "clean.nii.gz")).get_fdata()
    art = nib.load(str(exp / "artifact_L4.nii.gz")).get_fdata()
    mask = None
    mp = exp / "metal_mask.nii.gz"
    if mp.exists():
        mask = nib.load(str(mp)).get_fdata()
    return clean, art, mask


def find_center(mask, z):
    if mask is None:
        return None
    mz = mask[:, :, z]
    idx = np.argwhere(mz > 0)
    if len(idx) == 0:
        return None
    cy, cx = idx[:, 0].mean(), idx[:, 1].mean()
    return int(cy), int(cx)


def make_diff(name, label):
    clean, art, mask = load_pair(name)
    z = min(Z_SLICE, clean.shape[2] - 1)
    c = clean[:, :, z]
    a = art[:, :, z]
    m = mask[:, :, z] if mask is not None else None

    # 裁剪区域（围绕种植体）
    if m is not None:
        idx = np.argwhere(m > 0)
        if len(idx):
            cy, cx = idx[:, 0].mean(), idx[:, 1].mean()
            r = 60
            y0, y1 = max(0, int(cy) - r), min(c.shape[0], int(cy) + r)
            x0, x1 = max(0, int(cx) - r), min(c.shape[1], int(cx) + r)
            crop = (slice(y0, y1), slice(x0, x1))
        else:
            crop = (slice(None), slice(None))
    else:
        crop = (slice(None), slice(None))

    cc, aa, mm = c[crop], a[crop], m[crop] if m is not None else None
    diff = aa - cc

    # ===== 1. 差分热图（冷暖色）=====
    lo, hi = np.percentile(diff, [1, 99])
    vmax = max(abs(lo), abs(hi))
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    im = ax.imshow(diff.T, cmap="RdBu_r", origin="lower", vmin=-vmax, vmax=vmax)
    if mm is not None:
        # 金属轮廓
        ax.contour(mm.T, levels=[0.5], colors="k", linewidths=0.8)
    ax.set_title("Artifact - Clean (diff)", fontsize=10)
    ax.axis("off")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="diff")
    plt.tight_layout()
    diff_png = OUT / f"{name}_diff.png"
    fig.savefig(diff_png, dpi=110, bbox_inches="tight")
    plt.close(fig)

    # ===== 2. 剖面线对比 =====
    center = find_center(art, z) if mask is not None else (c.shape[0] // 2, c.shape[1] // 2)
    if center:
        cy, cx = center
        # 水平剖面线穿过种植体
        line_c = c[cy, :]
        line_a = a[cy, :]
        xs = np.arange(len(line_c))
        fig, ax = plt.subplots(figsize=(6.5, 3.2))
        ax.plot(xs, line_c, "b-", lw=1.2, label="Clean")
        ax.plot(xs, line_a, "r-", lw=1.2, label="Artifact (L4)")
        ax.axvspan(cx - 8, cx + 8, color="gray", alpha=0.25, label="implant")
        ax.set_xlabel("x position (px)")
        ax.set_ylabel("attenuation")
        ax.set_title("Profile line (y=%d)" % cy, fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        plt.tight_layout()
        prof_png = OUT / f"{name}_profile.png"
        fig.savefig(prof_png, dpi=110, bbox_inches="tight")
        plt.close(fig)
    else:
        prof_png = None

    # ===== 3. 距离-伪影分布（对应 shell 指标）=====
    if mm is not None and (mm > 0).any():
        idx = np.argwhere(mm > 0)
        cy, cx = idx[:, 0].mean(), idx[:, 1].mean()
        yy, xx = np.mgrid[0:mm.shape[0], 0:mm.shape[1]]
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        # 掩膜膨胀近似距离带：用 mask 的欧氏距离
        from scipy import ndimage
        dist_to_metal = ndimage.distance_transform_edt(1 - mm)
        bands = [(0, 2), (2, 5), (5, 10)]  # px 近似 mm（voxel≈0.2mm? 需核对）
        # 实际 voxel size 未知，按相对距离展示
        bands_px = [(0, 2), (2, 5), (5, 10)]
        fig, ax = plt.subplots(figsize=(6.5, 3.4))
        for (b0, b1) in bands_px:
            sel = (dist_to_metal >= b0) & (dist_to_metal < b1) & (dist_to_metal > 0)
            if sel.sum() == 0:
                continue
            dvals = diff[sel]
            ax.bar(f"{b0}-{b1}px", dvals.mean(), yerr=dvals.std(), capsize=3,
                   color="#c0392b" if dvals.mean() > 0 else "#2c7fb8")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_ylabel("mean diff")
        ax.set_xlabel("distance band (px from metal)")
        ax.set_title("Artifact by distance band", fontsize=10)
        plt.tight_layout()
        dist_png = OUT / f"{name}_dist.png"
        fig.savefig(dist_png, dpi=110, bbox_inches="tight")
        plt.close(fig)
    else:
        dist_png = None

    return {
        "key": name, "label": label,
        "diff": f"sim_diff/{name}_diff.png",
        "profile": f"sim_diff/{name}_profile.png" if prof_png else None,
        "dist": f"sim_diff/{name}_dist.png" if dist_png else None,
    }


def main():
    entries = []
    for name, label in EXPS:
        print("processing", name)
        try:
            r = make_diff(name, label)
            entries.append(r)
        except Exception as e:
            print(f"  FAIL {name}: {type(e).__name__}: {e}")
    with open(ROOT / "submission_materials" / "demo_source" / "public" / "sim_diff_index.json", "w", encoding="utf-8") as f:
        json.dump({"experiments": entries}, f, ensure_ascii=False, indent=1)
    print("done, entries:", len(entries))


if __name__ == "__main__":
    main()
