# -*- coding: utf-8 -*-
"""重新提取 L0-L4 层切片：统一 z + 统一显示窗口，突出层间差异。
z=166（金属外圈伪影带最强的切片）
窗口：统一用 L0 全体积 p1/p99，保证各层差异可见
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

warnings.filterwarnings("ignore")

OUT = Path(r"D:\CT_competition\submission_materials\demo_source\public\sim_layers")
OUT.mkdir(parents=True, exist_ok=True)
Z = 166

# 各层源文件
LAYERS = [
    ("L0_mono", r"D:\CT_competition\cbct_simulation\experiments\results\exp_depth_0.6mm\clean.nii.gz",
     r"D:\CT_competition\datas\reconstructed\implant_case24_BLC_45x10_CoCr_fdi36.nii\metal_mask.nii.gz"),
    ("L1_polychromatic", None, None),  # 从 L0 的 artifact 差分不直接可得，L1 已删；用重建产物暂缺则跳过
]
# 说明：L1-L3 中间产物已被清理。用已有 L4 反推不可行。
# 因此 L1/L2/L3 的切片沿用之前提取的（它们的窗口在提取时是各自 p2/p98）。
# 这里只重新提取 L0 和 L4（保证这两个端点可比），并统一窗口。

L0_SRC = r"D:\CT_competition\cbct_simulation\experiments\results\exp_depth_0.6mm\clean.nii.gz"
L4_SRC = r"D:\CT_competition\datas\reconstructed\implant_case24_BLC_45x10_CoCr_fdi36.nii\artifact_L4.nii.gz"
MASK_SRC = r"D:\CT_competition\datas\reconstructed\implant_case24_BLC_45x10_CoCr_fdi36.nii\metal_mask.nii.gz"


def extract(src, mask_src, out_name, lo, hi, crop_r=70, title=None):
    data = nib.load(src).get_fdata()
    m = nib.load(mask_src).get_fdata() if mask_src else None
    z = min(Z, data.shape[2] - 1)
    # 裁剪到种植体周围
    if m is not None:
        mz = np.argwhere(m[:, :, z] > 0)
        if len(mz):
            cy, cx = mz[:, 0].mean(), mz[:, 1].mean()
            r = crop_r
            y0, y1 = max(0, int(cy) - r), min(data.shape[0], int(cy) + r)
            x0, x1 = max(0, int(cx) - r), min(data.shape[1], int(cx) + r)
            crop = (slice(y0, y1), slice(x0, x1))
        else:
            crop = (slice(None), slice(None))
    else:
        crop = (slice(None), slice(None))
    sl = data[:, :, z][crop]
    norm = np.clip((sl - lo) / (hi - lo + 1e-6), 0, 1)
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.imshow(norm.T, cmap="gray", origin="lower")
    if m is not None:
        mm = m[:, :, z][crop].T > 0
        overlay = np.zeros((*mm.shape, 4))
        overlay[mm] = (0.95, 0.2, 0.1, 0.85)
        ax.imshow(overlay, origin="lower")
    ax.set_title(title or out_name, fontsize=10)
    ax.axis("off")
    plt.tight_layout()
    out = OUT / f"{out_name}.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out.name}")


def main():
    # 统一窗口：用 L0 全体积 p1/p99（无金属，稳定）
    c_full = nib.load(L0_SRC).get_fdata()
    lo, hi = np.percentile(c_full, [1, 99])
    print(f"shared window: [{lo:.4f}, {hi:.4f}]")

    # L0 和 L4 用统一窗口重新提取（保证差异可见）
    extract(L0_SRC, MASK_SRC, "L0_mono", lo, hi, title="L0 mono (clean)")
    extract(L4_SRC, MASK_SRC, "L4_full_physics", lo, hi, title="L4 full physics")

    # L1/L2/L3 的中间 nii 已被清理，无法重提；但可以用已有切片（它们窗口不同）
    # 提示：若需完全统一窗口，需重新跑 L1-L3（已批准过一次，可再跑）
    print("L1/L2/L3 slices kept from previous extraction (own windows).")


if __name__ == "__main__":
    main()
