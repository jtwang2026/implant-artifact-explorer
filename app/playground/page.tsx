"use client";

import { useState } from "react";

/* ============================================================
 * Agent 闭环体验器（缓存/合成演示）
 * 对应初赛问题定义 4.1：三类缓存/合成场景（支持/反驳/质量失败）
 * 纯前端交互，0 个新物理仿真；结果标注为缓存/合成，不作科学证据。
 * ============================================================ */

type Verdict = "supported" | "refuted" | "insufficient";

interface CacheResult {
  legality: "pass" | "fail";
  quality: "pass" | "fail";
  shell_mae: number | null;
  u: number | null;
  verdict: Verdict | null;
  note: string;
  changesNext: string;
}

interface Scenario {
  id: string;
  label: string;
  tone: "support" | "refute" | "quality";
  env: string[];
  hypothesis: { predict: string; falsify: string; compete: string };
  proposal: { tilt: string; azimuth: string; depth: string };
  result: CacheResult;
}

const SCENARIOS: Scenario[] = [
  {
    id: "support",
    label: "场景一 · 支持",
    tone: "support",
    env: [
      "环境身份：case24 / FDI36 / Ti-6Al-4V / YOFO 重建",
      "契约版本：C1 v0.2 · 指标版本 v0.3",
      "剩余预算：2 新点（共 3）",
    ],
    hypothesis: {
      predict: "倾角增大（0°→10°）不改变总负荷，但亮形貌传播尺度增加",
      falsify: "若 10° 与 0° 的亮形貌传播尺度差异 ≤ U，则证据不足",
      compete: "替代解释：骨占比随倾角变化（中介量），非角度直接效应",
    },
    proposal: {
      tilt: "10°",
      azimuth: "颊侧（e_y 正方向）",
      depth: "轴向基准 +0.0 mm",
    },
    result: {
      legality: "pass",
      quality: "pass",
      shell_mae: 0.8532,
      u: 0.012,
      verdict: "supported",
      note: "缓存结果与预注册预测方向一致（Δ=0.31 mm 传播尺度，2.6U，候选）",
      changesNext: "保留假设，提议一个确认点（同配置不同噪声种子）验证 2.6U 是否稳定",
    },
  },
  {
    id: "refute",
    label: "场景二 · 反驳",
    tone: "refute",
    env: [
      "环境身份：case24 / FDI36 / Ti-6Al-4V / YOFO 重建",
      "契约版本：C1 v0.2 · 指标版本 v0.3",
      "剩余预算：2 新点（共 3）",
    ],
    hypothesis: {
      predict: "深度加深 1.0 mm 会单调增加近场伪影强度",
      falsify: "若加深后 shell MAE 增量 ≤ U 或反向，则拒绝单调假设",
      compete: "替代解释：加深改变埋骨率（中介），骨接触变化才是驱动",
    },
    proposal: {
      tilt: "0°",
      azimuth: "null（倾角为 0）",
      depth: "轴向基准 +1.0 mm（预注册域内）",
    },
    result: {
      legality: "pass",
      quality: "pass",
      shell_mae: 0.8611,
      u: 0.012,
      verdict: "refuted",
      note: "缓存结果偏离预注册预测方向（Δ=0.14 mm，11.7U，反向）",
      changesNext: "修改假设：深度效应不单调；登记修订链并保留旧版本，提议等深度不同方位点",
    },
  },
  {
    id: "quality",
    label: "场景三 · 质量失败",
    tone: "quality",
    env: [
      "环境身份：case24 / FDI36 / Ti-6Al-4V / YOFO 重建",
      "契约版本：C1 v0.2 · 指标版本 v0.3",
      "剩余预算：2 新点（共 3）",
    ],
    hypothesis: {
      predict: "任意合法位姿均可进入测度反馈",
      falsify: "若重建质量失败，则本点不产生任何测度",
      compete: "质量失败 = 环境/测量问题，不得解释为物理效应",
    },
    proposal: {
      tilt: "10°",
      azimuth: "远中（e_x 正方向）",
      depth: "轴向基准 +0.5 mm",
    },
    result: {
      legality: "pass",
      quality: "fail",
      shell_mae: null,
      u: null,
      verdict: null,
      note: "重建质量门控未通过（mask 连通性断裂，体积误差 >10%）；不返回任何测度",
      changesNext: "质量失败只用于修正环境：标记任务为失败模式，修复 mask 管线后重试；不解释为物理效应",
    },
  },
];

const STEPS = ["读取环境", "登记假设", "提交提案", "门控检查", "结果反馈", "判断与下一步"] as const;

export default function Playground() {
  const [scenarioId, setScenarioId] = useState("support");
  const [step, setStep] = useState(0);
  const [showGate, setShowGate] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const scenario = SCENARIOS.find((s) => s.id === scenarioId)!;

  const reset = () => {
    setStep(0);
    setShowGate(false);
    setShowResult(false);
  };

  const advance = () => {
    if (step === 0) { setStep(1); return; }
    if (step === 1) { setStep(2); return; }
    if (step === 2) { setShowGate(true); setStep(3); return; }
    if (step === 3) { setShowResult(true); setStep(4); return; }
    if (step === 4) { setStep(5); return; }
  };

  const toneClass = `tone-${scenario.tone}`;

  return (
    <main className="playground">
      <nav className="nav" aria-label="主导航">
        <a className="brand" href="/"><span>植位</span>智探</a>
        <div className="navlinks">
          <a href="/">首页</a><a href="/#trajectory">Agent 轨迹</a><a href="/#audit">外部审计</a>
        </div>
        <span className="nav-cta" style={{ background: "var(--orange)" }}>缓存/合成演示</span>
      </nav>

      <section className="pg-hero">
        <div className="eyebrow"><i /> 初赛验证范围 · 0 个新物理仿真</div>
        <h1>Agent 闭环<br /><em>体验器</em></h1>
        <p className="lead">对应初赛问题定义 4.1：在三类缓存/合成场景（支持、反驳、质量失败）中，走通"读取环境 → 登记假设 → 提交提案 → 门控检查 → 结果反馈 → 判断与下一步"完整事件链。本页面所有结果均为缓存/合成数据，不作为科学证据。</p>
      </section>

      <section className="pg-stage">
        <div className="pg-controls">
          <div className="pg-scenarios">
            {SCENARIOS.map((s) => (
              <button
                key={s.id}
                className={scenarioId === s.id ? `scenario active ${s.tone}` : `scenario ${s.tone}`}
                onClick={() => { setScenarioId(s.id); reset(); }}
                aria-pressed={scenarioId === s.id}
              >
                {s.label}
              </button>
            ))}
          </div>
          <div className="pg-progress">
            {STEPS.map((label, i) => (
              <span key={label} className={i <= step ? "done" : ""}><i>{i + 1}</i>{label}</span>
            ))}
          </div>
        </div>

        <div className="pg-board">
          {/* 左栏：环境 + 步骤内容 */}
          <div className="pg-main">
            {step === 0 && (
              <div className="pg-card">
                <h3>① 读取环境快照</h3>
                <ul className="env-list">{scenario.env.map((line) => <li key={line}>{line}</li>)}</ul>
                <p className="hint">Agent 只读取预定义摘要，不读取完整体素场。</p>
              </div>
            )}
            {step === 1 && (
              <div className="pg-card">
                <h3>② 登记假设（register_hypothesis）</h3>
                <div className="hypo">
                  <div><small>预测</small><p>{scenario.hypothesis.predict}</p></div>
                  <div><small>证伪条件</small><p>{scenario.hypothesis.falsify}</p></div>
                  <div><small>竞争解释</small><p>{scenario.hypothesis.compete}</p></div>
                </div>
              </div>
            )}
            {step === 2 && (
              <div className="pg-card">
                <h3>③ 提交提案（propose_experiment）</h3>
                <div className="proposal">
                  <div><small>倾角</small><strong>{scenario.proposal.tilt}</strong></div>
                  <div><small>倾斜方向</small><strong>{scenario.proposal.azimuth}</strong></div>
                  <div><small>轴向放置</small><strong>{scenario.proposal.depth}</strong></div>
                </div>
                <p className="hint">每个提案带匹配基准，声明唯一改变因素与停止条件。</p>
              </div>
            )}
            {step >= 3 && showGate && (
              <div className="pg-card">
                <h3>④ 门控检查</h3>
                <ul className="gate-list">
                  <li className={scenario.result.legality === "pass" ? "ok" : "bad"}>
                    <b>合法性</b><span>{scenario.result.legality === "pass" ? "通过（位姿在冻结域内）" : "不通过"}</span>
                  </li>
                  <li className="ok"><b>预算</b><span>通过（剩余 2 新点，未超预算）</span></li>
                  <li className={scenario.result.quality === "pass" ? "ok" : "bad"}>
                    <b>质量门控</b><span>{scenario.result.quality === "pass" ? "通过（mask 连通、体积误差达标）" : "不通过（重建质量失败）"}</span>
                  </li>
                </ul>
                {scenario.result.quality === "fail" && (
                  <p className="warn">质量失败只返回失败原因，不返回任何测度；不得解释为物理效应。</p>
                )}
              </div>
            )}
            {step >= 4 && showResult && (
              <div className="pg-card">
                <h3>⑤ 结果反馈</h3>
                {scenario.result.quality === "fail" ? (
                  <div className="result-fail">
                    <strong>质量失败</strong>
                    <p>{scenario.result.note}</p>
                  </div>
                ) : (
                  <>
                    <div className="result-metrics">
                      <div><small>shell MAE（0–2 mm）</small><strong>{scenario.result.shell_mae!.toFixed(4)}</strong></div>
                      <div><small>技术不确定度 U</small><strong>{scenario.result.u!.toFixed(4)}</strong></div>
                    </div>
                    <p>{scenario.result.note}</p>
                  </>
                )}
              </div>
            )}
            {step === 5 && (
              <div className="pg-card">
                <h3>⑥ 判断与下一步</h3>
                <div className={`verdict ${scenario.result.verdict ?? "quality"}`}>
                  {scenario.result.verdict === "supported" && <strong>supported（支持）</strong>}
                  {scenario.result.verdict === "refuted" && <strong>refuted（反驳）</strong>}
                  {scenario.result.verdict === null && <strong>无判断（质量失败）</strong>}
                  <p>{scenario.result.changesNext}</p>
                </div>
                <p className="hint">判断改变下一步：保留/修订假设或触发停止；系统不替 Agent 生成结论。</p>
              </div>
            )}

            <div className="pg-actions">
              {step < 5 ? (
                <button className="primary" onClick={advance}>
                  {step === 0 ? "读取环境 →" : step === 1 ? "提交假设 →" : step === 2 ? "提交提案 →" : step === 3 ? "执行门控 →" : "返回结果 →"}
                </button>
              ) : (
                <button className="primary" onClick={reset}>重新体验</button>
              )}
              {step > 0 && <button className="ghost" onClick={() => { setStep((s) => Math.max(0, s - 1)); setShowGate(step <= 3); setShowResult(step <= 4); }}>← 上一步</button>}
            </div>
          </div>

          {/* 右栏：事件链 */}
          <aside className="pg-log">
            <h3>事件链（追加式日志）</h3>
            <ol>
              <li className={step >= 0 ? "on" : ""}><b>observe</b><span>读取环境身份、预算、历史事件链</span></li>
              <li className={step >= 1 ? "on" : ""}><b>hypothesis</b><span>登记预测、证伪条件、竞争解释</span></li>
              <li className={step >= 2 ? "on" : ""}><b>propose</b><span>提出结构化位姿 + 匹配基准</span></li>
              <li className={step >= 3 ? "on" : ""}><b>gate</b><span>合法性 · 预算 · 质量门控</span></li>
              <li className={step >= 4 ? "on" : ""}><b>feedback</b><span>{scenario.result.quality === "pass" ? "测度与 U 回流" : "仅失败原因，无测度"}</span></li>
              <li className={step >= 5 ? "on" : ""}><b>judge</b><span>{scenario.result.verdict ?? "no-verdict"} → 修订/停止</span></li>
            </ol>
            <div className="log-note">
              <b>缓存说明</b>
              <p>本页面全部为缓存/合成数据，标注"不作科学证据"；仅演示控制流与可审计性，不验证放置规律（对应 4.1 边界）。</p>
            </div>
          </aside>
        </div>
      </section>

      <footer><div className="brand"><span>植位</span>智探</div><p>定义清楚 · 双重自检 · 负责人确认后再实验</p><p className="fine">缓存/合成演示，不作为科学证据。</p></footer>
    </main>
  );
}
