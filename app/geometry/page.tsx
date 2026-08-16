"use client";

import { useState } from "react";
import Image from "next/image";

/* ============================================================
 * 几何参数探索实验室（真实数据互动）
 * 展示已执行的螺纹深度 × 螺距探索：Agent 决策链重演 + 参数扫描器
 * 全部为真实仿真结果；单轮证据，含数值警告，不作因果结论。
 * ============================================================ */

// ---- 8 个真实 Agent 选点（来自历史探索日志，result.json 已核验） ----
interface AgentStep {
  round: string;
  step: number;
  d: number;
  p: number;
  shell: number;
  sv: number;
  rationale: string;
  test: string;
  outcome: string;
  impact: string;
}

const AGENT_STEPS: AgentStep[] = [
  {
    round: "08-03", step: 1, d: 1.4, p: 2.4, shell: 0.858103, sv: 1.822,
    rationale: "补齐大深度 × 最大螺距边界，检查 S/V—shell 线性关系是否遗漏组合几何效应。",
    test: "若该点偏离既有线性预测，则保留\"单一 S/V 不足\"的候选解释。",
    outcome: "残差 -0.054（原始口径，5.2× 已见范围）",
    impact: "负偏离方向与深螺纹区假设一致，候选信号保留",
  },
  {
    round: "08-03", step: 2, d: 1.2, p: 2.4, shell: 0.856000, sv: 1.681,
    rationale: "在 d=1.2 的扫描中补齐 p=2.4，检查极端稀疏螺纹在高深度下的表现。",
    test: "观察结果是否低于既有 S/V 线性预期；这里只登记候选，不直接判机制。",
    outcome: "残差 -0.041（原始口径，3.9×）",
    impact: "与上一点同向，深螺纹区负偏离初步成组",
  },
  {
    round: "08-03", step: 3, d: 1.5, p: 0.8, shell: 0.963070, sv: 2.588,
    rationale: "沿深度轴向外推到 d=1.5，探查历史线性模型的应用边界。",
    test: "若显著偏离 d=0.2–1.4 的预测，说明边界处可能存在未建模非线性。",
    outcome: "残差 -0.034（原始口径，3.3×）",
    impact: "外推区仍负偏离；但该区点含外推误差，不可单独作证",
  },
  {
    round: "08-03", step: 4, d: 1.2, p: 1.6, shell: 0.880744, sv: 1.843,
    rationale: "填补 d=1.2 扫描中唯一缺失的中等螺距点，检查趋势是否连续。",
    test: "比较中等螺距与两端点是否共同遵循同一趋势。",
    outcome: "残差 -0.034（原始口径，3.3×）",
    impact: "深螺纹区（d≥1.2 且 p≥1.6）负偏离点增至 3 个",
  },
  {
    round: "08-03", step: 5, d: 0.8, p: 2.8, shell: 0.845321, sv: 1.391,
    rationale: "把 p 扩展到 2.8，检验较大螺距与较高深度组合的外推边界。",
    test: "检查趋势是否仍稳定；结果只作为历史探索线索。",
    outcome: "残差 -0.020（原始口径，1.9×，弱负）",
    impact: "负偏离不严格限于深螺纹区，出现区外弱负点",
  },
  {
    round: "08-04", step: 1, d: 1.4, p: 1.2, shell: 0.920646, sv: 2.210,
    rationale: "在中等螺距下补入更深点，继续检验几何复杂度增加后的线性稳定性。",
    test: "观察是否出现无法由 S/V 单指标解释的偏离。",
    outcome: "带内残差（未超阈值）",
    impact: "深螺纹区假设未被进一步支持，也未反驳",
  },
  {
    round: "08-04", step: 2, d: 1.4, p: 0.6, shell: 0.942833, sv: 2.391,
    rationale: "选择历史未覆盖的\"大深度 + 细螺距\"组合，探查高复杂度边界。",
    test: "比较细螺距下的增长是否出现饱和或突变线索。",
    outcome: "带内残差",
    impact: "高 S/V 区点落在线内，未发现非线性饱和",
  },
  {
    round: "08-04", step: 3, d: 0.8, p: 1.2, shell: 0.882691, sv: 1.609,
    rationale: "填补中等深度 × 中等螺距网格空白，建立更可比较的组合。",
    test: "历史日志预设：残差 > 0.025 才保留非线性交互候选。",
    outcome: "带内残差",
    impact: "网格填充完成；候选信号仍集中在深螺纹区",
  },
];

// ---- 13 组受控单因素真实数据（_controlled_metrics.csv，埋骨率恒定 ≈67%） ----
const DEPTH_SCAN = [
  { d: 0.2, shell: 0.8451 }, { d: 0.3, shell: 0.8541 }, { d: 0.4, shell: 0.8652 },
  { d: 0.6, shell: 0.8854 }, { d: 0.8, shell: 0.9059 }, { d: 1.0, shell: 0.9251 },
];
const PITCH_SCAN = [
  { p: 1.2, shell: 0.8692 }, { p: 1.6, shell: 0.8567 }, { p: 2.0, shell: 0.8506 }, { p: 2.4, shell: 0.8449 },
];
const TI64_SCAN = [
  { d: 0.2, shell: 0.7714 }, { d: 0.6, shell: 0.8066 }, { d: 1.0, shell: 0.8401 },
];

const STEPS_LABEL = ["观察历史", "选择点位", "登记预期", "执行仿真", "结果回流", "判断影响"] as const;

export default function GeometryLab() {
  const [stepIdx, setStepIdx] = useState(0);
  const [depth, setDepth] = useState(0.6);
  const [pitch, setPitch] = useState(1.6);
  const [material, setMaterial] = useState<"CoCr" | "Ti64">("CoCr");

  const step = AGENT_STEPS[stepIdx];
  const depthVal = DEPTH_SCAN.reduce((a, b) => (Math.abs(b.d - depth) < Math.abs(a.d - depth) ? b : a));
  const pitchVal = PITCH_SCAN.reduce((a, b) => (Math.abs(b.p - pitch) < Math.abs(a.p - pitch) ? b : a));

  return (
    <main className="geometry">
      <nav className="nav" aria-label="主导航">
        <a className="brand" href="/"><span>植位</span>智探</a>
        <div className="navlinks">
          <a href="/">首页</a><a href="/#experiments">真实实验</a><a href="/#trajectory">Agent 轨迹</a><a href="/playground">体验闭环</a>
        </div>
        <span className="nav-cta" style={{ background: "var(--teal)" }}>真实数据 · 历史探索</span>
      </nav>

      <section className="geo-hero">
        <div className="eyebrow"><i /> 已执行探索 · 非新仿真</div>
        <h1>几何参数<br /><em>探索实验室</em></h1>
        <p className="lead">螺纹深度 × 螺距的真实探索回顾：8 个 Agent 选点逐步重演决策链，13 组受控单因素提供参数—伪影定量关系。全部为已落盘仿真结果，标注证据等级，不作当前放置问题的因果证据。</p>
      </section>

      {/* ===== 模块一：Agent 决策链重演 ===== */}
      <section className="geo-section" id="replay-chain">
        <header className="section-head"><div><span className="kicker">模块一 / 决策链重演</span><h2>Agent 当时为什么选这个点</h2></div><p>点击"下一步"逐步回放 8 个真实选点：观察→选点→预期→仿真→回流→判断。</p></header>

        <div className="chain-control">
          <div className="chain-steps">
            {AGENT_STEPS.map((s, i) => (
              <button key={`${s.round}-${s.step}`} className={i === stepIdx ? "active" : ""} onClick={() => setStepIdx(i)}>
                {s.round.slice(3)}·{s.step}
              </button>
            ))}
          </div>
          <div className="chain-nav">
            <button className="ghost" disabled={stepIdx === 0} onClick={() => setStepIdx((i) => Math.max(0, i - 1))}>← 上一点</button>
            <span className="chain-pos">第 {stepIdx + 1} / 8 点</span>
            <button className="primary" disabled={stepIdx === AGENT_STEPS.length - 1} onClick={() => setStepIdx((i) => Math.min(AGENT_STEPS.length - 1, i + 1))}>下一点 →</button>
          </div>
        </div>

        <div className="chain-board">
          <div className="chain-left">
            <div className="chain-params">
              <div><small>THREAD DEPTH</small><strong>{step.d.toFixed(1)}<em> mm</em></strong></div>
              <div><small>THREAD PITCH</small><strong>{step.p.toFixed(1)}<em> mm</em></strong></div>
              <div><small>S/V</small><strong>{step.sv.toFixed(3)}</strong></div>
              <div><small>SHELL 0–2mm</small><strong>{step.shell.toFixed(4)}</strong></div>
            </div>
            <div className="chain-flow">
              {STEPS_LABEL.map((label, i) => (
                <div key={label} className={i <= 5 ? "on" : ""}>
                  <i>{i + 1}</i><span>{label}</span>
                </div>
              ))}
            </div>
            <div className="chain-detail">
              <h3>Agent 选点依据</h3><p>{step.rationale}</p>
              <h3>登记的可检验预期</h3><p>{step.test}</p>
            </div>
          </div>
          <aside className="chain-outcome">
            <h3>真实仿真回流</h3>
            <div className="outcome-row"><small>结果</small><strong>{step.outcome}</strong></div>
            <div className="outcome-row"><small>对假设的影响</small><strong>{step.impact}</strong></div>
            <div className="log-note">
              <b>证据等级</b>
              <p>原始口径残差仅作历史信号展示；统一 0.10 mm 口径后深点残差仍为负（-0.029 ~ -0.033），但单轮证据、含 mesh→mask 数值警告，未升级为机制结论。</p>
            </div>
          </aside>
        </div>
      </section>

      {/* ===== 模块二：参数扫描器（真实单因素） ===== */}
      <section className="geo-section" id="scanner">
        <header className="section-head"><div><span className="kicker">模块二 / 参数扫描器</span><h2>拖动参数，看真实测量值</h2></div><p>基于 13 组受控单因素（埋骨率恒定 ≈67%）：深度与螺距各自单因素变化下的真实 shell 测量。</p></header>

        <div className="scanner">
          <div className="scanner-controls">
            <div className="mat-switch">
              <button className={material === "CoCr" ? "on" : ""} onClick={() => setMaterial("CoCr")}>CoCr</button>
              <button className={material === "Ti64" ? "on" : ""} onClick={() => setMaterial("Ti64")}>Ti-6Al-4V</button>
            </div>
            <div className="slider-row">
              <label>螺纹深度 d <span>{material === "CoCr" ? depthVal.d.toFixed(1) : TI64_SCAN.reduce((a, b) => (Math.abs(b.d - depth) < Math.abs(a.d - depth) ? b : a)).d.toFixed(1)} mm</span></label>
              <input type="range" min="0.2" max="1.0" step="0.1" value={depth}
                onChange={(e) => setDepth(parseFloat(e.target.value))} disabled={material === "Ti64"} />
            </div>
            <div className="slider-row">
              <label>螺距 p <span>{pitchVal.p.toFixed(1)} mm</span></label>
              <input type="range" min="1.2" max="2.4" step="0.2" value={pitch}
                onChange={(e) => setPitch(parseFloat(e.target.value))} disabled={material === "Ti64"} />
            </div>
            <p className="scanner-hint">{material === "CoCr"
              ? `当前显示：深度 ${depthVal.d.toFixed(1)} mm → shell ${depthVal.shell.toFixed(4)}；螺距 ${pitchVal.p.toFixed(1)} mm → shell ${pitchVal.shell.toFixed(4)}`
              : `Ti-6Al-4V 深度 ${TI64_SCAN.reduce((a, b) => (Math.abs(b.d - depth) < Math.abs(a.d - depth) ? b : a)).d.toFixed(1)} mm → shell ${TI64_SCAN.reduce((a, b) => (Math.abs(b.d - depth) < Math.abs(a.d - depth) ? b : a)).shell.toFixed(4)}（Ti64 仅深度扫描）`}</p>
          </div>
          <div className="scanner-chart">
            <div className="bar-chart">
              {material === "CoCr" ? (
                <>
                  {DEPTH_SCAN.map((pt) => (
                    <div key={`d${pt.d}`} className={Math.abs(pt.d - depth) < 0.05 ? "bar on" : "bar"} style={{ height: `${(pt.shell / 1.0) * 100}%` }} title={`d=${pt.d} shell=${pt.shell.toFixed(4)}`}>
                      <span>{pt.shell.toFixed(3)}</span><b>d={pt.d.toFixed(1)}</b>
                    </div>
                  ))}
                </>
              ) : (
                <>
                  {TI64_SCAN.map((pt) => (
                    <div key={`t${pt.d}`} className={Math.abs(pt.d - depth) < 0.05 ? "bar on" : "bar"} style={{ height: `${(pt.shell / 1.0) * 100}%` }} title={`d=${pt.d} shell=${pt.shell.toFixed(4)}`}>
                      <span>{pt.shell.toFixed(3)}</span><b>d={pt.d.toFixed(1)}</b>
                    </div>
                  ))}
                </>
              )}
            </div>
            <p className="chart-note">横轴为螺纹深度 d（mm），柱高为真实 shell 0–2mm 测量值。CoCr 深度单调上升；Ti64 整体低于 CoCr（材料调节伪影放大率）。</p>
          </div>
        </div>
      </section>

      <section className="geo-section">
        <figure className="full-fig">
          <Image src="/fig1_sv_shell_all.png" width={1000} height={722} alt="全量数据 S/V 与伪影强度散点图" style={{ width: "100%", height: "auto" }} />
          <figcaption>全量真实数据：S/V 与伪影强度（含受控 13 组、A/B 随机形状、系统消融与探索点）。CoCr 铁律 R²≈0.94；跨系统降至 0.82 级，暴露未建模因素。</figcaption>
        </figure>
      </section>

      <footer><div className="brand"><span>植位</span>智探</div><p>定义清楚 · 双重自检 · 负责人确认后再实验</p><p className="fine">本页面全部为历史真实仿真结果；单轮证据，不作当前放置问题的因果证据。</p></footer>
    </main>
  );
}
