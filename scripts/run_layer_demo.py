# -*- coding: utf-8 -*-
"""分层仿真 L0-L3 驱动脚本（负责人已批准，2026-08-16）
流程（流式，各层输出到 L2/L3 脚本期望的默认路径，跑完统一清理）：
  L0+L1: simulate_poly.py --keep-intermediate
         -> L1_poly/P_poly.npy + L1_poly/artifact_mono.nii.gz (L0) + artifact_poly.nii.gz (L1)
  L2:    simulate_L2_photon_noise.py  -> L2_photon_noise/P_noisy.npy + artifact_L2_*.nii.gz
  L3:    simulate_L3_scatter.py       -> L3_scatter/P_scatter.npy + artifact_L3_*.nii.gz
保留：每层轴向切片 PNG（demo 用）；清理所有中间 npy/nii
"""
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(r"D:\CT_competition")
PY = r"D:\CT_competition\mar_env\Scripts\python.exe"
SIM = ROOT / "cbct_simulation"
RECON = ROOT / "datas" / "reconstructed"
OUT_PNG = ROOT / "submission_materials" / "demo_source" / "public" / "sim_layers"
OUT_PNG.mkdir(parents=True, exist_ok=True)

DIR_L1 = RECON / "L1_poly"
DIR_L2 = RECON / "L2_photon_noise"
DIR_L3 = RECON / "L3_scatter"

Z_SLICE = 240  # 金属主体中段（z=218-289），束硬化差异最强（环内 mean diff 最大）


def run(script, args, tag):
    print(f"\n{'='*60}\n[{tag}] {script.name}\n{'='*60}")
    cmd = [PY, str(script)] + args
    t0 = time.time()
    env = dict(__import__("os").environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(cmd, cwd=str(SIM), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    tail = r.stdout[-2500:] if r.stdout else ""
    print(tail)
    if r.stderr:
        err = r.stderr[-1200:]
        print("STDERR:", err)
    print(f"[{tag}] exit={r.returncode} elapsed={time.time()-t0:.0f}s")
    if r.returncode != 0:
        raise RuntimeError(f"{tag} failed (exit {r.returncode})")


def extract_slice(nii_path, out_name, lo, hi, mask_path=None, diff_ref=None, diff_name=None):
    """提取切片 PNG + 可选差分热图（该层 - 参考层，冷暖色放大单层效应）。"""
    data = nib.load(str(nii_path)).get_fdata()
    print(f"  extract {nii_path.name}: shape={data.shape}")
    z = Z_SLICE
    sl = data[:, :, z]
    norm = np.clip((sl - lo) / (hi - lo + 1e-6), 0, 1)
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.imshow(norm.T, cmap="gray", origin="lower")
    if mask_path is not None and mask_path.exists():
        try:
            m = nib.load(str(mask_path)).get_fdata()[:, :, z]
            overlay = np.zeros((*m.T.shape, 4))
            mm = m.T > 0
            overlay[mm] = (0.95, 0.2, 0.1, 0.85)
            ax.imshow(overlay, origin="lower")
        except Exception:
            pass
    ax.set_title(out_name, fontsize=10)
    ax.axis("off")
    plt.tight_layout()
    out = OUT_PNG / f"{out_name}.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out.name}")

    # 差分热图：该层 - 参考层（L0），冷暖色放大单层效应
    if diff_ref is not None and diff_name is not None:
        ref = nib.load(str(diff_ref)).get_fdata()
        diff = sl - ref[:, :, z]
        d_lo, d_hi = np.percentile(diff, [1, 99])
        vmax = max(abs(d_lo), abs(d_hi))
        fig, ax = plt.subplots(figsize=(5.0, 5.0))
        im = ax.imshow(diff.T, cmap="RdBu_r", origin="lower", vmin=-vmax, vmax=vmax)
        if mask_path is not None and mask_path.exists():
            try:
                m = nib.load(str(mask_path)).get_fdata()[:, :, z]
                ax.contour(m.T, levels=[0.5], colors="k", linewidths=0.8)
            except Exception:
                pass
        ax.set_title(f"{diff_name} - L0", fontsize=10)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="diff")
        plt.tight_layout()
        dout = OUT_PNG / f"{diff_name}_diff.png"
        fig.savefig(dout, dpi=110, bbox_inches="tight")
        plt.close(fig)
        print(f"  saved: {dout.name}")
    return out


def cleanup():
    print("\n[cleanup] removing intermediate dirs...")
    for d in (DIR_L1, DIR_L2, DIR_L3):
        if d.exists():
            print(f"  remove {d}")
            shutil.rmtree(d, ignore_errors=True)


def main():
    t_start = time.time()
    mask = r"D:\CT_competition\datas\metal_masks\case24_v1_crown_16_metal_labels.nii.gz"

    # 统一显示窗口：L0（clean 基线）全体积 p1/p99
    clean_ref = ROOT / "cbct_simulation" / "experiments" / "results" / "exp_depth_0.6mm" / "clean.nii.gz"
    if not clean_ref.exists():
        raise RuntimeError("clean reference missing for window")
    c_full = nib.load(str(clean_ref)).get_fdata()
    lo, hi = np.percentile(c_full, [1, 99])
    print(f"shared window (clean p1/p99): [{lo:.4f}, {hi:.4f}]")

    try:
        # ===== L0 + L1（产物已存在则跳过计算，只提取切片）=====
        DIR_L1.mkdir(parents=True, exist_ok=True)
        mono = DIR_L1 / "artifact_mono.nii.gz"
        poly = DIR_L1 / "artifact_poly.nii.gz"
        p_poly = DIR_L1 / "P_poly.npy"
        mask_out = DIR_L1 / "metal_mask.nii.gz"
        if not (mono.exists() and poly.exists() and p_poly.exists()):
            run(SIM / "simulate_poly.py",
                ["--mask", mask, "--output-dir", str(DIR_L1), "--keep-intermediate"],
                "L0+L1")
        if mono.exists():
            extract_slice(mono, "L0_mono", lo, hi, mask_path=mask_out)
        if poly.exists():
            extract_slice(poly, "L1_polychromatic", lo, hi, mask_path=mask_out,
                          diff_ref=clean_ref, diff_name="L1")
        if not p_poly.exists():
            raise RuntimeError("P_poly.npy not produced by L1")
        print(f"  P_poly OK: {p_poly} ({p_poly.stat().st_size/1e9:.2f} GB)")

        # ===== L2 =====
        DIR_L2.mkdir(parents=True, exist_ok=True)
        if not (DIR_L2 / "P_noisy.npy").exists() and not list(DIR_L2.glob("artifact_L2*.nii.gz")):
            run(SIM / "simulate_L2_photon_noise.py", ["--n0", "10000", "--seed", "42"], "L2")
        l2 = list(DIR_L2.glob("artifact_L2*.nii.gz"))
        if l2:
            extract_slice(l2[0], "L2_photon_noise", lo, hi, mask_path=DIR_L1 / "metal_mask.nii.gz",
                          diff_ref=clean_ref, diff_name="L2")
        if not (DIR_L2 / "P_noisy.npy").exists():
            raise RuntimeError("P_noisy.npy not produced by L2")

        # ===== L3 =====
        DIR_L3.mkdir(parents=True, exist_ok=True)
        if not list(DIR_L3.glob("artifact_L3*.nii.gz")):
            run(SIM / "simulate_L3_scatter.py", ["--spr", "0.05"], "L3")
        l3 = list(DIR_L3.glob("artifact_L3*.nii.gz"))
        if l3:
            extract_slice(l3[0], "L3_scatter", lo, hi, mask_path=DIR_L1 / "metal_mask.nii.gz",
                          diff_ref=clean_ref, diff_name="L3")

        # ===== L4（已有产物，统一窗口 + 差分）=====
        l4_candidates = list((ROOT / "datas" / "reconstructed").rglob("artifact_L4*.nii.gz"))
        l4_case = ROOT / "datas" / "reconstructed" / "implant_case24_BLC_45x10_CoCr_fdi36.nii" / "artifact_L4.nii.gz"
        if l4_case.exists():
            extract_slice(l4_case, "L4_full_physics", lo, hi, mask_path=l4_case.parent / "metal_mask.nii.gz",
                          diff_ref=clean_ref, diff_name="L4")
        elif l4_candidates:
            extract_slice(l4_candidates[0], "L4_full_physics", lo, hi, mask_path=None,
                          diff_ref=clean_ref, diff_name="L4")

        print(f"\n{'='*60}\nDONE in {time.time()-t_start:.0f}s")
        print("slices:", sorted(p.name for p in OUT_PNG.glob("*.png")))
        return 0
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")
        return 1
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
