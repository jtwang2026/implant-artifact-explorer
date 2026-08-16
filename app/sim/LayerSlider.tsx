"use client";

import { useState } from "react";
import Image from "next/image";

/* ============================================================
 * 分层仿真滑杆：L0 → L1 → L2 → L3 → L4 逐步叠加
 * 数据：sim_layers/*.png（真实分层仿真切片，z=240 金属主体中段）
 * 视图：原始灰度（统一窗口）+ 差分热图（该层 - L0，冷暖色放大单层效应）
 * ============================================================ */

const LAYERS = [
  { idx: 0, tag: "L0", name: "单能基线", img: "/sim_layers/L0_mono.png", diff: null,
    desc: "单能 X 射线（金属用 70 keV）重建。无束硬化、无噪声的基线。" },
  { idx: 1, tag: "L1", name: "多能谱", img: "/sim_layers/L1_polychromatic.png", diff: "/sim_layers/L1_diff.png",
    desc: "金属改用 SpekPy 20-bin 多能谱积分（100 kVp / W 阳极）：束硬化产生金属周围方向性暗区/亮纹（见差分图红色/蓝色斑块）。" },
  { idx: 2, tag: "L2", name: "光子饥饿", img: "/sim_layers/L2_photon_noise.png", diff: "/sim_layers/L2_diff.png",
    desc: "加入 Poisson 噪声（N₀=10k）：金属衰减路径上信噪比骤降，差分图出现沿投影方向的条纹噪声。" },
  { idx: 3, tag: "L3", name: "散射", img: "/sim_layers/L3_scatter.png", diff: "/sim_layers/L3_diff.png",
    desc: "加入 3D 高斯散射（SPR=0.05）：杯状伪影与对比度损失，伪影区域进一步扩大。" },
  { idx: 4, tag: "L4", name: "探测器 MTF", img: "/sim_layers/L4_full_physics.png", diff: "/sim_layers/L4_diff.png",
    desc: "加入探测器 MTF（0.7px）：全物理叠加，与 MAR 训练使用的配对数据一致，伪影最显著。" },
];

export default function LayerSlider() {
  const [level, setLevel] = useState(1);
  const layer = LAYERS[level];

  return (
    <div className="layer-slider-wrap">
      <div className="layer-slider-row">
        {LAYERS.map((l) => (
          <button
            key={l.idx}
            className={level === l.idx ? "on" : ""}
            onClick={() => setLevel(l.idx)}
            title={l.name}
          >
            <b>{l.tag}</b>
            <span>{l.name}</span>
          </button>
        ))}
      </div>
      <input
        type="range"
        min="0"
        max="4"
        step="1"
        value={level}
        onChange={(e) => setLevel(Number(e.target.value))}
        aria-label="物理层级别"
      />
      <div className="layer-view">
        <div className="layer-img">
          <Image src={layer.img} width={520} height={520} alt={`L${level} 重建切片`} priority />
          <span className="layer-badge">{layer.tag}</span>
        </div>
        {layer.diff ? (
          <div className="layer-view-right">
            <div className="layer-img diff">
              <Image src={layer.diff} width={520} height={520} alt={`L${level} 差分热图`} />
              <span className="layer-badge diff-badge">{layer.tag} − L0</span>
            </div>
            <div className="layer-desc">
              <h4>{layer.name}</h4>
              <p>{layer.desc}</p>
              <p className="layer-note">左：原始重建（统一窗口）；右：差分热图（该层 − L0，红=增强 蓝=减弱）。拖动滑杆对比各层新增的物理效应。</p>
            </div>
          </div>
        ) : (
          <div className="layer-desc">
            <h4>{layer.name}</h4>
            <p>{layer.desc}</p>
            <p className="layer-note">基线层。向右拖动滑杆，观察伪影随物理层叠加逐步出现。</p>
          </div>
        )}
      </div>
    </div>
  );
}
