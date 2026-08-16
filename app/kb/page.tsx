"use client";

import { useState } from "react";
import kbData from "../../public/kb_data.json";

/* ============================================================
 * 种植体参数溯源（知识库 viewer 交互版）
 * 数据：kb_data.json（从 SQLite 只读导出，对应 viewer/queries.py）
 * 功能对齐 Streamlit viewer 的"快速查询 + 模型状态"：
 *   厂家→系列→REF → 参数表（官方/工程分离）→ 证据链 → 假设/缺口/验证
 * ============================================================ */

interface Rec { [key: string]: any }
const KB = kbData as any;

const GRADE_LABELS: Rec = {
  A: "A｜厂家正式资料明确给出",
  B: "B｜由厂家正式参数直接推导",
  C: "C｜学术文献或可靠测量",
  D: "D｜工程假设或图像估计",
  E: "E｜证据不足或尚未确认",
};

const DOMAIN_LABELS: Rec = {
  identity: "产品身份", geometry: "几何尺寸", connection: "连接结构",
  material: "材料", surface: "表面处理", simulation: "仿真建模",
};

const PARAM_LABELS: Rec = {
  implant_nominal_diameter_mm: "植体标称直径", implant_length_mm: "植体长度",
  maximum_body_outer_diameter_mm: "体部最大外径", connection_diameter_mm: "连接直径",
  platform_diameter_mm: "平台直径", thread_lead_mm: "螺纹导程", thread_depth_mm: "螺纹深度",
  thread_flank_lead_deg: "螺纹侧面导角", thread_included_angle_deg: "螺纹牙型夹角",
  thread_crest_radius_mm: "螺纹牙顶圆角半径", thread_root_radius_mm: "螺纹牙底圆角半径",
  thread_start_count: "螺纹起始数", thread_start_phase_deg: "螺纹起始相位",
  body_taper_angle_deg: "体部锥角", tapered_part_length_mm: "锥形段长度",
  apical_thread_diameter_mm: "根尖螺纹外径", apical_core_diameter_mm: "根尖芯径",
  material: "植体材料", surface: "表面处理",
  coronal_transition_geometry: "冠方过渡建模方式", cutting_flute_geometry: "切削槽建模方式",
  coronal_outer_diameter_mm: "冠方外径", apical_transition_outer_diameter_mm: "根尖过渡外径",
  apical_end_outer_diameter_mm: "根尖端外径", apical_region_length_mm: "根尖区域长度",
  apex_diameter_mm: "根尖直径", apex_length_mm: "根尖区域长度",
  neck_height_mm: "颈部高度", thread_apical_runout_mm: "根尖螺纹延展",
  thread_coronal_runout_mm: "冠方螺纹延展", thread_end_z_mm: "螺纹区终点坐标",
  thread_start_z_mm: "螺纹区起点坐标", threaded_length_mm: "螺纹区长度",
  internal_hex_size_mm: "内六角尺寸",
};

function cn(code: string): string { return PARAM_LABELS[code] || code; }
function domainLabel(d: string): string { return DOMAIN_LABELS[d] || d || "—"; }
function gradeLabel(g: string | null, isMfr: boolean): string {
  if (g && GRADE_LABELS[g]) return GRADE_LABELS[g];
  return isMfr ? "厂家参数" : "D｜工程假设或模型简化";
}

export default function KbViewer() {
  const mfrs = KB.manufacturers as Rec[];
  const seriesAll = KB.series as Rec[];
  const variants = KB.variants as Rec[];
  const models = KB.geometry_models as Rec[];
  const adopted = KB.adopted_parameters as Rec[];
  const assumptions = KB.engineering_assumptions as Rec[];
  const gaps = KB.model_gaps as Rec[];
  const tasks = KB.validation_tasks as Rec[];
  const claims = KB.claims as Rec[];
  const evidence = KB.evidence as Rec[];
  const applicability = KB.applicability as Rec[];
  const docs = KB.source_documents as Rec[];
  const terms = KB.term_mappings as Rec[];

  const [mfrId, setMfrId] = useState<number>(2);
  const [seriesId, setSeriesId] = useState<number>(4);
  const [variantId, setVariantId] = useState<number>(6);
  const [modelId, setModelId] = useState<number>(5);
  const [selParamIdx, setSelParamIdx] = useState<number>(0);
  const [tab, setTab] = useState<"params" | "assumptions" | "gaps" | "tasks">("params");

  const mfr = mfrs.find((m) => m.id === mfrId);
  const series = seriesAll.find((s) => s.id === seriesId);
  const variant = variants.find((v) => v.id === variantId);
  const model = models.find((m) => m.id === modelId);
  const variantModels = models.filter((m) => m.product_variant_id === variantId);
  const adoptedFor = adopted.filter((a) => a.geometry_model_id === modelId);
  const assumptionsFor = assumptions.filter((a) => a.geometry_model_id === modelId);
  const gapsFor = gaps.filter((g) => g.geometry_model_id === modelId);
  const tasksFor = tasks.filter((t) => t.geometry_model_id === modelId);
  const claimsFor = claims.filter((c) => c.product_variant_id === variantId);

  const official = adoptedFor.filter((a) => a.is_manufacturer_value === 1);
  const engineering = adoptedFor.filter((a) => a.is_manufacturer_value !== 1);

  const selParam = adoptedFor[selParamIdx] || null;
  const selClaimId = selParam?.selected_claim_id;
  const selEvidence = selClaimId ? evidence.filter((e) => e.parameter_claim_id === selClaimId) : [];
  const selApplic = selClaimId ? applicability.filter((a) => a.parameter_claim_id === selClaimId) : [];

  const variantLabel = variant?.official_ref_resolved === 0
    ? "目录配置记录（非官方 REF）" : "官方 REF";

  return (
    <main className="kb">
      <nav className="nav" aria-label="主导航">
        <a className="brand" href="/"><span>植位</span>智探</a>
        <div className="navlinks">
          <a href="/">首页</a><a href="/geometry">几何实验室</a><a href="/playground">体验闭环</a>
        </div>
        <span className="nav-cta" style={{ background: "var(--teal)" }}>参数溯源 · 真实知识库</span>
      </nav>

      <section className="kb-hero">
        <div className="eyebrow"><i /> 固定 CAD 的可信度来源</div>
        <h1>种植体参数<br /><em>溯源库</em></h1>
        <p className="lead">放置参数研究要求"固定 CAD"——固定不是随便选的。本页从厂商官方规格出发，逐条展示参数来源、证据等级与工程假设，官方值与假设严格分离。数据来自 dental_implant_kb（SQLite 只读导出，342 条记录）。</p>
      </section>

      {/* 选择器 */}
      <section className="kb-section">
        <div className="kb-selector">
          <div className="sel-block">
            <small>① 厂家</small>
            <select value={mfrId} onChange={(e) => {
              const mid = Number(e.target.value);
              setMfrId(mid);
              const s = seriesAll.find((x) => x.manufacturer_id === mid);
              if (s) {
                setSeriesId(s.id);
                const v = variants.find((x) => x.product_series_id === s.id);
                if (v) {
                  setVariantId(v.id);
                  const mo = models.find((x) => x.product_variant_id === v.id);
                  if (mo) { setModelId(mo.id); setSelParamIdx(0); }
                }
              }
            }}>
              {mfrs.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </div>
          <div className="sel-block">
            <small>② 产品系列</small>
            <select value={seriesId} onChange={(e) => {
              const sid = Number(e.target.value);
              setSeriesId(sid);
              const v = variants.find((x) => x.product_series_id === sid);
              if (v) {
                setVariantId(v.id);
                const mo = models.find((x) => x.product_variant_id === v.id);
                if (mo) { setModelId(mo.id); setSelParamIdx(0); }
              }
            }}>
              {seriesAll.filter((s) => s.manufacturer_id === mfrId).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="sel-block">
            <small>③ 具体型号 / REF</small>
            <select value={variantId} onChange={(e) => {
              const vid = Number(e.target.value);
              setVariantId(vid);
              const mo = models.find((x) => x.product_variant_id === vid);
              if (mo) { setModelId(mo.id); setSelParamIdx(0); }
            }}>
              {variants.filter((v) => v.product_series_id === seriesId).map((v) => (
                <option key={v.id} value={v.id}>{v.ref_code}{v.official_ref_resolved === 0 ? "（目录配置）" : ""}</option>
              ))}
            </select>
          </div>
          {variantModels.length > 1 && (
            <div className="sel-block">
              <small>④ 几何模型</small>
              <select value={modelId} onChange={(e) => { setModelId(Number(e.target.value)); setSelParamIdx(0); }}>
                {variantModels.map((m) => <option key={m.id} value={m.id}>{m.name} v{m.version}</option>)}
              </select>
            </div>
          )}
        </div>

        <div className="kb-variant">
          <div>
            <b>{mfr?.name} {series?.name}</b>
            <span>REF：<b>{variant?.ref_code}</b>（{variantLabel}）</span>
            <span>{variant?.commercial_name} · {variant?.market_region}</span>
            {variant?.official_ref_resolved === 0 && <em className="warn-tag">官方 REF 未解析：目录配置级记录</em>}
          </div>
          <div className="kb-vstats">
            <span><b>{adoptedFor.length}</b>采纳参数</span>
            <span><b>{assumptionsFor.length}</b>工程假设</span>
            <span><b>{gapsFor.filter((g) => g.status === "open").length}</b>未关闭缺口</span>
            <span><b>{tasksFor.length}</b>验证任务</span>
          </div>
        </div>
      </section>

      {/* 参数与证据 */}
      <section className="kb-section">
        <div className="kb-tabs">
          <button className={tab === "params" ? "on" : ""} onClick={() => setTab("params")}>采用参数（{adoptedFor.length}）</button>
          <button className={tab === "assumptions" ? "on" : ""} onClick={() => setTab("assumptions")}>工程假设（{assumptionsFor.length}）</button>
          <button className={tab === "gaps" ? "on" : ""} onClick={() => setTab("gaps")}>模型缺口（{gapsFor.length}）</button>
          <button className={tab === "tasks" ? "on" : ""} onClick={() => setTab("tasks")}>验证任务（{tasksFor.length}）</button>
        </div>

        {tab === "params" && (
          <div className="kb-params-layout">
            <div className="kb-param-list">
              <div className="kb-list-head"><span>参数</span><span>采用值</span><span>性质</span><span>证据</span></div>
              {adoptedFor.map((p, i) => {
                const isMfr = p.is_manufacturer_value === 1;
                return (
                  <button key={p.id} className={i === selParamIdx ? "on" : ""} onClick={() => setSelParamIdx(i)}>
                    <span className="pn">{cn(p.code)}</span>
                    <span className="pv">{p.value} {p.unit || ""}</span>
                    <span className="pt">{isMfr ? "厂家参数" : "工程补全"}</span>
                    <span className="pg">{p.selected_claim_grade || (isMfr ? "—" : "D")}</span>
                  </button>
                );
              })}
              {adoptedFor.length === 0 && <p className="empty">该模型尚无采纳参数。</p>}
            </div>

            {selParam && (
              <div className="kb-param-detail">
                <h3>{cn(selParam.code)} <code>{selParam.code}</code></h3>
                <div className="detail-metrics">
                  <div><small>采用值</small><strong>{selParam.value} {selParam.unit || ""}</strong></div>
                  <div><small>性质</small><strong>{selParam.is_manufacturer_value === 1 ? "厂家参数" : "工程补全"}</strong></div>
                  <div><small>证据等级</small><strong>{gradeLabel(selParam.selected_claim_grade, selParam.is_manufacturer_value === 1)}</strong></div>
                </div>
                {selParam.adoption_reason && <p className="reason"><b>采用理由：</b>{selParam.adoption_reason}</p>}
                {selParam.description && <p className="desc">{selParam.description}</p>}
                {selParam.adoption_method && <p className="muted">采用方式：{selParam.adoption_method}</p>}
                {selParam.uncertainty_text && <p className="muted">不确定性：{selParam.uncertainty_text}</p>}

                {!selClaimId ? (
                  <p className="warn-para">该参数来自工程假设或模型策略，无对应厂家声明；依据见"工程假设"页签。</p>
                ) : (
                  <>
                    {selApplic.length > 0 && (
                      <div className="ev-block">
                        <h4>适用范围</h4>
                        {selApplic.map((a, i) => (
                          <div key={i} className="ev-row">
                            <span>{a.dimension_code} {a.operator} {a.value_real ?? a.value_text ?? (a.range_min !== null ? `${a.range_min}~${a.range_max}` : "")} {a.unit || ""}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="ev-block">
                      <h4>来源证据（{selEvidence.length}）</h4>
                      {selEvidence.length === 0 && <p className="muted">未登记证据记录。</p>}
                      {selEvidence.map((e, i) => (
                        <div key={i} className="ev-card">
                          <div className="ev-head"><b>{e.source_title || "未命名来源"}</b>{e.page_number && <span>第 {e.page_number} 页</span>}</div>
                          {e.quoted_text && <blockquote>{e.quoted_text}</blockquote>}
                          <div className="ev-meta">
                            {e.source_type && <span>{e.source_type}</span>}
                            <span>{e.is_official === 1 ? "官方来源" : "非官方"}</span>
                            {e.verified_by_human === 1 && <span className="ok-tag">✓ 人工核验</span>}
                            {e.url && <a href={e.url} target="_blank" rel="noreferrer">打开来源 ↗</a>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {tab === "assumptions" && (
          <div className="kb-plain-table">
            {assumptionsFor.length === 0 ? <p className="empty">无工程假设。</p> : (
              <table>
                <thead><tr><th>参数</th><th>假设值</th><th>类型</th><th>依据</th><th>敏感性</th><th>理由</th></tr></thead>
                <tbody>
                  {assumptionsFor.map((a) => (
                    <tr key={a.id}><td>{cn(a.code)}</td><td><b>{a.value} {a.unit || ""}</b></td><td>{a.assumption_type || "—"}</td><td>{a.basis_type || "—"}</td><td>{a.sensitivity_level || "—"}</td><td>{a.rationale || "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === "gaps" && (
          <div className="kb-plain-table">
            {gapsFor.length === 0 ? <p className="empty">无模型缺口。</p> : (
              <table>
                <thead><tr><th>参数</th><th>缺口类型</th><th>严重度</th><th>状态</th><th>处理策略</th><th>处理记录</th></tr></thead>
                <tbody>
                  {gapsFor.map((g) => (
                    <tr key={g.id}><td>{g.parameter_code || "—"}</td><td>{g.gap_category || "—"}</td><td>{g.severity || "—"}</td><td>{g.status || "—"}</td><td>{g.resolution_strategy || "—"}</td><td>{g.resolution_notes || "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === "tasks" && (
          <div className="kb-plain-table">
            {tasksFor.length === 0 ? <p className="empty">无验证任务。</p> : (
              <table>
                <thead><tr><th>任务</th><th>优先级</th><th>状态</th><th>方法</th><th>通过标准</th></tr></thead>
                <tbody>
                  {tasksFor.map((t) => (
                    <tr key={t.id}><td>{t.title}</td><td>{t.priority || "—"}</td><td>{t.status || "—"}</td><td>{t.method || "—"}</td><td>{t.acceptance_criteria || "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </section>

      <section className="kb-section">
        <div className="kb-stats-row">
          <div><b>{KB.manufacturers.length}</b><span>厂家</span></div>
          <div><b>{KB.variants.length}</b><span>具体 REF</span></div>
          <div><b>{KB.claims.length}</b><span>参数声明</span></div>
          <div><b>{KB.evidence.length}</b><span>证据记录</span></div>
          <div><b>{KB.source_documents.length}</b><span>源文档</span></div>
          <div><b>{KB.term_mappings.length}</b><span>术语映射</span></div>
        </div>
        <aside className="boundary"><b>口径纪律：</b>"thread lead = 轴向螺距 × 头数"（官方 1.6 mm 为每转前进量，存为 lead）；工程假设永不升级为厂家声明；模型为 manufacturer-inspired，非厂商精确 CAD。该 CAD 是放置问题中的固定输入，不是被探索的变量。</aside>
      </section>

      <footer><div className="brand"><span>植位</span>智探</div><p>定义清楚 · 双重自检 · 负责人确认后再实验</p><p className="fine">知识库数据来自厂商公开规格与显式工程假设；本页为 SQLite 只读导出的静态展示。</p></footer>
    </main>
  );
}
