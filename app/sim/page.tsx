"use client";

import { useState } from "react";
import Image from "next/image";
import simIndex from "../../public/sim_index.json";
import diffIndex from "../../public/sim_diff_index.json";
import LayerSlider from "./LayerSlider";

/* ============================================================
 * 仿真环境展示：真实配对数据对比 + 差分可视化 + 分层架构
 * 数据：真实仿真重建（cbct_simulation/experiments/results/*）
 * 互动：滑杆对比 / 差分热图 / 剖面线 / 距离分布 / 实验切换
 * ============================================================ */

const EXPS = (simIndex as any).experiments as any[];
const DIFF = (diffIndex as any).experiments as any[];

type ViewMode = "slider" | "diff" | "profile" | "dist";

export default function SimCompare() {
  const [idx, setIdx] = useState(0);
  const [slider, setSlider] = useState(50);
  const [view, setView] = useState<ViewMode>("slider");
  const exp = EXPS[idx];
  const diff = DIFF[idx];

  return (
    <main className="sim">
      <nav className="nav" aria-label="主导航">
        <a className="brand" href="/"><span>植位</span>智探</a>
        <div className="navlinks">
          <a href="/">首页</a><a href="/geometry">几何实验室</a><a href="/kb">参数溯源</a><a href="/playground">体验闭环</a>
        </div>
        <span className="nav-cta" style={{ background: "var(--teal)" }}>真实仿真 · 配对数据</span>
      </nav>

      <section className="sim-hero">
        <div className="eyebrow"><i /> 真实仿真重建 · 非演示数据</div>
        <h1>仿真配对数据<br /><em>对比与伪影可视化</em></h1>
        <p className="lead">同一病例、同一几何，仅"有无金属"的区别。原始重建人眼难辨差异，因此提供三种伪影可视化：差分热图（直接显示伪影分布）、剖面线（定量对比）、距离分布（伪影随距离衰减）。全部来自真实 L4 全物理仿真。</p>
      </section>

      <section className="sim-stage">
        <div className="sim-controls">
          <div className="sim-exp-btns">
            {EXPS.map((e, i) => (
              <button key={e.key} className={i === idx ? "on" : ""} onClick={() => { setIdx(i); setSlider(50); }}>
                {e.label}
              </button>
            ))}
          </div>
          <div className="sim-view-tabs">
            <button className={view === "slider" ? "on" : ""} onClick={() => setView("slider")}>① 原始对比</button>
            <button className={view === "diff" ? "on" : ""} onClick={() => setView("diff")}>② 差分热图</button>
            <button className={view === "profile" ? "on" : ""} onClick={() => setView("profile")}>③ 剖面线</button>
            <button className={view === "dist" ? "on" : ""} onClick={() => setView("dist")}>④ 距离分布</button>
          </div>
        </div>

        {view === "slider" && (
          <>
            <div className="sim-slider-row">
              <span className="side-label">Clean</span>
              <input type="range" min="0" max="100" value={slider} onChange={(e) => setSlider(Number(e.target.value))} />
              <span className="side-label">Artifact</span>
            </div>
            <div className="sim-compare">
              <div className="compare-box">
                <div className="compare-layer artifact">
                  <Image src={`/${exp.artifact}`} width={520} height={520} alt="含金属伪影重建切片" priority />
                </div>
                <div className="compare-layer clean" style={{ clipPath: `inset(0 ${100 - slider}% 0 0)` }}>
                  <Image src={`/${exp.clean}`} width={520} height={520} alt="无金属重建切片" priority />
                </div>
                <div className="divider-line" style={{ left: `${slider}%` }} />
                <div className="compare-tag tag-clean">CLEAN</div>
                <div className="compare-tag tag-artifact">ARTIFACT</div>
              </div>
            </div>
          </>
        )}

        {view === "diff" && diff && (
          <div className="sim-single-fig">
            <Image src={`/${diff.diff}`} width={520} height={520} alt="伪影差分热图" priority />
            <p className="fig-note">Artifact − Clean 差分：<b className="red">红 = 亮伪影（强度升高）</b>，<b className="blue">蓝 = 暗伪影（强度降低）</b>，黑线为金属轮廓。伪影的空间分布一目了然。</p>
          </div>
        )}

        {view === "profile" && diff?.profile && (
          <div className="sim-single-fig">
            <Image src={`/${diff.profile}`} width={680} height={380} alt="剖面线对比" priority />
            <p className="fig-note">穿过种植体的水平剖面线：蓝 = Clean，红 = Artifact（L4）。灰色带为种植体位置。可见金属处强度尖峰与周围暗区凹陷。</p>
          </div>
        )}

        {view === "dist" && diff?.dist && (
          <div className="sim-single-fig">
            <Image src={`/${diff.dist}`} width={680} height={380} alt="伪影距离分布" priority />
            <p className="fig-note">伪影差分强度按距金属表面距离分带统计：近带（0–2 px）伪影最强，随距离衰减——这正是 shell_0_2mm 等分级指标的物理基础。</p>
          </div>
        )}

        <div className="sim-meta">
          <div><small>实验</small><b>{exp.label}</b></div>
          <div><small>轴向切片</small><b># {exp.slice}</b></div>
          <div><small>配对</small><b>clean ↔ artifact（像素对齐）</b></div>
          <div><small>视图</small><b>{view === "slider" ? "原始对比" : view === "diff" ? "差分热图" : view === "profile" ? "剖面线" : "距离分布"}</b></div>
        </div>

        <aside className="boundary"><b>数据说明：</b>以上切片与可视化来自已执行的分层物理仿真（SpekPy 20-bin 多能谱 → 光子饥饿 → 散射 → MTF，YOFO FBP 重建），全部为仿真产物（可开源）。红色标记为金属掩膜位置。配对数据服务于 MAR 训练需求；仿真—临床域差异仍属待验证问题。</aside>
      </section>

      {/* ===== 模块二：分层物理仿真 ===== */}
      <section className="sim-section" id="layers">
        <header className="section-head"><div><span className="kicker">模块二 / 分层物理仿真</span><h2>伪影不是黑箱：每一层物理都可见</h2></div><p>拖动滑杆，观察伪影随物理复杂度逐层叠加：L0 单能基线 → L1 多能谱（束硬化）→ L2 光子饥饿 → L3 散射 → L4 探测器 MTF。以下切片为真实分层仿真输出。</p></header>

        <LayerSlider />

        <div className="layer-stats">
          <div><small>层级</small><b>L0 → L4</b></div>
          <div><small>暗区比例（近金属）</small><b>L2: 15.31% → L3: 16.21% → 真实: 16.30%</b></div>
          <div><small>耗时</small><b>L1–L3 全链 834 s（GPU）</b></div>
          <div><small>数据</small><b>真实重建，中间产物已清理</b></div>
        </div>
        <p className="layer-finding"><b>关键证据：</b>暗区比例随物理层叠加单调逼近真实含金属数据（L2 光子饥饿 15.31% → L3 散射 16.21% → 真实 16.30%）——证明分层仿真"每加一层物理，伪影统计特性更接近真实"，这是管线有效性的量化证据，也是"伪影可解释"的核心。</p>

        <div className="sim-figs">
          <div className="sinogram-pair">
            <figure>
              <Image src="/sim_assets/sinogram_clean.png" width={620} height={420} alt="无金属投影正弦图" style={{ width: "100%", height: "auto" }} />
              <figcaption>投影域：Clean 正弦图（无金属）。</figcaption>
            </figure>
            <figure>
              <Image src="/sim_assets/sinogram_artifact.png" width={620} height={420} alt="含金属投影正弦图" style={{ width: "100%", height: "auto" }} />
              <figcaption>投影域：Artifact 正弦图（金属轨迹产生强衰减条纹）。</figcaption>
            </figure>
          </div>
          <figure>
            <Image src="/sim_assets/sinogram_artifact_row277.png" width={900} height={500} alt="正弦图单行剖面对比" style={{ width: "100%", height: "auto" }} />
            <figcaption>正弦图单行剖面：金属投影位置的强度塌陷（光子饥饿的直接证据）。</figcaption>
          </figure>
        </div>

        <aside className="boundary"><b>证据边界：</b>L0–L3 由分层管线重新生成（负责人批准，2026-08-16），L4 为已有全物理产物；中间投影/重建文件已清理，仅保留展示切片。分层叠加保证 L4 包含 L0–L3 全部效应。</aside>
      </section>

      <footer><div className="brand"><span>植位</span>智探</div><p>定义清楚 · 双重自检 · 负责人确认后再实验</p><p className="fine">仿真配对数据展示：真实重建切片，不作为临床影像。</p></footer>
    </main>
  );
}
