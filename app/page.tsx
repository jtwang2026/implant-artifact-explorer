"use client";

import Image from "next/image";

/* ============================================================
 * 植位智探 · 首页（2026-08-16 重构：用户友好型叙事）
 * 30 秒讲清：研究什么 → 方法可信 → 未来怎么跑
 * ============================================================ */

const PROBLEMS = [
  { tag: "科学问题", title: "放置参数如何改变伪影？", text: "固定病例与成像条件下，种植体的深度、倾角和方向，如何影响伪影的强度与空间分布？目前尚无公认答案。" },
  { tag: "固定什么", title: "只改变放置，其余全冻结", text: "病例 24 / FDI36、CAD、Ti-6Al-4V、扫描与重建全部固定——隔离出「放置」这一个变量。" },
  { tag: "探索什么", title: "三个自由度，合法域内", text: "倾角（0–20°）、倾斜方向（颊/舌/近/远中）、轴向深度。每个位姿先过合法性检查，越界即拒。" },
  { tag: "如何判定", title: "信号先定义，不事后追认", text: "U 包络分级（≤U 不足 / <3U 候选 / ≥3U 强候选），候选须独立确认；被清晰解释的负结果同样有价值。" },
];

const EVIDENCE = [
  { img: "/fig1_sv_shell_all.png", title: "仿真工作流真实跑通", text: "13 组受控单因素 + 24 套真实仿真 + 8 个 Agent 选点，全部落盘可追溯。" },
  { img: "/fig2_explore_residual.png", title: "Agent 真的在检验假设", text: "历史探索点相对铁律预测的残差：深螺纹区出现方向一致的候选信号（单轮证据，未升级）。" },
  { img: "/fig5_cross_shape.png", title: "发现真实边界", text: "跨真实种植体系统时规律 R² 从 0.94 降至 0.82——暴露未建模因素，这正是放置问题要回答的。" },
  { img: "/fig4b_s_vs_sv_ctrl13.png", title: "指标可比较、可检验", text: "强度 A± 与形貌 p± 分开度量；人类种子假设交由 Agent 独立检验。" },
];

const TRUST = [
  { title: "+51.1% 盲测提升 → 已撤回", text: "审计发现 Agent 3 例 vs 基线 5 例不具可比性，结论无效并保留失败证据。", state: "诚实" },
  { title: "24/24 网格质量警告留痕", text: "mesh→mask 数值误差全部记录，不隐藏；科学结论等待质量门控。", state: "留痕" },
  { title: "当前真实探索状态：NO-GO", text: "P0–C4 契约未全部冻结，不启动新仿真；初赛用缓存场景验证控制流。", state: "严谨" },
];

export default function Home() {
  return (
    <main>
      <nav className="nav" aria-label="主导航">
        <a className="brand" href="#top"><span>植位</span>智探</a>
        <div className="navlinks">
          <a href="#problem">问题与环境</a><a href="#evidence">真实证据</a><a href="#trust">可信度</a><a href="#next">下一步</a>
          <a href="/geometry">几何实验室</a><a href="/sim">仿真对比</a><a href="/kb">参数溯源</a><a href="/playground">体验闭环</a>
        </div>
      </nav>

      {/* ① HERO：30 秒讲清研究什么 */}
      <section className="hero" id="top" style={{ minHeight: "auto", padding: "90px clamp(22px,8vw,130px) 60px" }}>
        <div className="eyebrow"><i /> AI for Research · 开放探索赛题</div>
        <h1>种植体放置参数<br />如何改变 CBCT 金属伪影？</h1>
        <p className="lead">固定病例与成像条件，只改变放置——用可审计的 Agent 科学探索环境，回答深度、倾角与方向如何影响伪影的强度与空间分布；确认后的规律，再用于改善 MAR 训练数据。</p>
        <div className="hero-actions">
          <a className="primary" href="/playground">体验 Agent 闭环 →</a>
          <a className="nav-cta" href="#evidence">查看真实证据 ↓</a>
          <span>问题定义已冻结 · 真实放置探索 <b>NO-GO</b>（诚实披露）</span>
        </div>
      </section>

      {/* ② 问题与环境：4 卡讲清定义 */}
      <section className="section" id="problem" style={{ padding: "70px clamp(22px,7vw,110px)" }}>
        <header className="section-head">
          <div><span className="kicker">问题与环境</span><h2>我们在研究什么</h2></div>
          <p>一个定义清楚、可证伪、可比较、可停止的探索环境——不是自由聊天，也不是黑箱优化器。</p>
        </header>
        <div className="home-probs">
          {PROBLEMS.map((p) => (
            <article key={p.tag}>
              <span>{p.tag}</span>
              <h3>{p.title}</h3>
              <p>{p.text}</p>
            </article>
          ))}
        </div>
        <aside className="boundary"><b>证据边界：</b>以上是「拟议环境」的定义。真实放置探索尚未执行（NO-GO）；历史几何探索（见下）只证明工作流可运行，不构成放置问题的证据。</aside>
      </section>

      {/* ③ 真实证据：工作流可行性 */}
      <section className="section" id="evidence" style={{ padding: "70px clamp(22px,7vw,110px)" }}>
        <header className="section-head">
          <div><span className="kicker">真实证据</span><h2>方法已验证可行</h2></div>
          <p>以下全部为已执行的物理仿真与测量结果（13 组受控 + 24 套仿真 + 8 个 Agent 点），不是演示数据。</p>
        </header>
        <div className="exp-grid">
          {EVIDENCE.map((e) => (
            <figure key={e.title}>
              <Image src={e.img} width={720} height={520} alt={e.title} />
              <figcaption><b>{e.title}</b>{e.text}</figcaption>
            </figure>
          ))}
        </div>
        <div className="home-links">
          <a className="nav-cta" href="/geometry" style={{ background: "var(--teal)" }}>进入几何参数探索实验室 →</a>
          <a className="nav-cta" href="/sim" style={{ background: "var(--teal)" }}>查看仿真配对数据与分层物理 →</a>
        </div>
      </section>

      {/* ④ 可信度：诚实三连 */}
      <section className="section dark" id="trust" style={{ padding: "70px clamp(22px,7vw,110px)", background: "var(--ink)", color: "#e9e4d6" }}>
        <header className="section-head">
          <div><span className="kicker" style={{ color: "var(--mint)" }}>可信度</span><h2 style={{ color: "#fff" }}>我们选择诚实</h2></div>
          <p style={{ color: "#9fb0a8" }}>开放赛题评审 35% 明确奖励「被清晰解释的负结果」。以下是我们的失败与边界——全部如实保留。</p>
        </header>
        <div className="home-trust">
          {TRUST.map((t) => (
            <article key={t.title}>
              <span className="state">{t.state}</span>
              <h3>{t.title}</h3>
              <p>{t.text}</p>
            </article>
          ))}
        </div>
        <div className="home-links" style={{ marginTop: 26 }}>
          <a className="nav-cta" href="/kb" style={{ background: "var(--teal)" }}>查看种植体参数溯源（官方 vs 假设分离）→</a>
        </div>
      </section>

      {/* ⑤ 下一步 */}
      <section className="section" id="next" style={{ padding: "70px clamp(22px,7vw,110px)" }}>
        <header className="section-head">
          <div><span className="kicker">下一步</span><h2>从「已验证可行」到「放置探索」</h2></div>
        </header>
        <div className="next-grid">
          <figure>
            <Image src="/local-frame.png" width={900} height={650} alt="种植体局部坐标系校准图" />
            <figcaption>局部坐标已校准：平台原点、轴向平移、四方向骨嵴深度。</figcaption>
          </figure>
          <figure>
            <Image src="/crest-calibration.png" width={900} height={650} alt="四方向骨嵴参考校准图" />
            <figcaption>骨嵴方向差异达 2.583 mm，单一标量深度方案未通过预注册门——深度语义须联合四方向。</figcaption>
          </figure>
          <div className="contract">
            <h3>已冻结的定义</h3>
            <ul>
              <li>固定 case24 / FDI36、CAD、Ti-6Al-4V、扫描与重建</li>
              <li>探索：倾角 0–20°、局部倾斜方向、轴向放置</li>
              <li>深度：轴心参考 + 四方向联合语义</li>
              <li>判定：U 包络分级，候选须独立确认</li>
              <li>预算：初赛 3 缓存场景，0 新仿真</li>
            </ul>
            <div className="gate"><b>当前闸门</b><span>P0–C4 未全部冻结</span><em>NO-GO</em></div>
          </div>
        </div>
      </section>

      <footer>
        <div className="brand"><span>植位</span>智探</div>
        <p>定义清楚 · 双重自检 · 负责人确认后再实验</p>
        <p className="fine">本页面为初赛演示材料。历史观察不等于当前科学问题的验证结果；缓存演示不作科学证据。</p>
      </footer>
    </main>
  );
}
