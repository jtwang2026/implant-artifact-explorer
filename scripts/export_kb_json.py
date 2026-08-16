# -*- coding: utf-8 -*-
"""导出种植体知识库为静态 JSON，供 demo（GitHub Pages 静态托管）前端读取。
对应 viewer/queries.py 的查询逻辑，输出一份自包含的 JSON。
用法: python export_kb_json.py
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / ".."))
from pathlib import Path as P

KB = P(r"D:\downloads\dental_implant_kb_v0_10_alpha_osstem_source_collector\dental_implant_kb_v0_10_alpha")
DB = KB / "database" / "implant_kb_v0_10_dev.sqlite3"
OUT = P(r"D:\CT_competition\submission_materials\demo_source\public\kb_data.json")


def connect_readonly(db_path):
    path = P(db_path).expanduser().resolve()
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]


def main():
    conn = connect_readonly(DB)

    data = {
        "generated_at": "2026-08-16",
        "schema_version": "kb_v0_10_alpha",
        "manufacturers": rows(conn, "SELECT id, name FROM manufacturer ORDER BY name"),
        "series": rows(conn, """
            SELECT ps.id, ps.name, ps.abbreviation, ps.status, ps.manufacturer_id,
                   ps.notes
            FROM product_series ps ORDER BY ps.manufacturer_id, ps.name
        """),
        "variants": rows(conn, """
            SELECT pv.id, pv.ref_code, pv.commercial_name, pv.market_region,
                   pv.lifecycle_status, pv.notes, pv.identity_status,
                   pv.source_designation, pv.official_ref_resolved,
                   pv.product_series_id
            FROM product_variant pv ORDER BY pv.product_series_id, pv.ref_code
        """),
        "geometry_models": rows(conn, """
            SELECT gm.id, gm.product_variant_id, gm.name, gm.geometry_class,
                   gm.version, gm.coordinate_convention, gm.cad_format,
                   gm.cad_file_path, gm.mesh_file_path, gm.model_sha256,
                   gm.construction_method, gm.validation_status, gm.notes
            FROM geometry_model gm ORDER BY gm.name, gm.version
        """),
        "adopted_parameters": rows(conn, """
            SELECT ap.id, gm.product_variant_id, ap.geometry_model_id,
                   pd.code, pd.canonical_name, pd.domain, pd.description,
                   COALESCE(CAST(ap.adopted_value_real AS TEXT),
                            CAST(ap.adopted_value_integer AS TEXT),
                            ap.adopted_value_text,
                            CAST(ap.adopted_value_boolean AS TEXT),
                            ap.adopted_value_json) AS value,
                   COALESCE(ap.unit, pd.canonical_unit) AS unit,
                   ap.adoption_reason, ap.adoption_method, ap.source_value_snapshot,
                   ap.transformation_expression, ap.is_manufacturer_value,
                   ap.requires_engineering_completion, ap.uncertainty_text,
                   ap.selected_claim_id,
                   pc.evidence_grade AS selected_claim_grade
            FROM adopted_parameter ap
            JOIN parameter_definition pd ON pd.id = ap.parameter_definition_id
            LEFT JOIN parameter_claim pc ON pc.id = ap.selected_claim_id
            LEFT JOIN geometry_model gm ON gm.id = ap.geometry_model_id
            ORDER BY pd.domain, pd.code
        """),
        "engineering_assumptions": rows(conn, """
            SELECT ea.id, ea.geometry_model_id,
                   pd.code, pd.canonical_name, pd.domain,
                   COALESCE(CAST(ea.assumed_value_real AS TEXT),
                            CAST(ea.assumed_value_integer AS TEXT),
                            ea.assumed_value_text,
                            CAST(ea.assumed_value_boolean AS TEXT),
                            ea.assumed_value_json) AS value,
                   COALESCE(ea.unit, pd.canonical_unit) AS unit,
                   ea.assumption_type, ea.basis_type, ea.rationale,
                   ea.basis_reference, ea.evidence_grade, ea.sensitivity_level,
                   ea.requires_sensitivity_analysis, ea.status
            FROM engineering_assumption ea
            JOIN parameter_definition pd ON pd.id = ea.parameter_definition_id
            ORDER BY pd.domain, pd.code
        """),
        "model_gaps": rows(conn, """
            SELECT id, geometry_model_id, parameter_code, gap_category,
                   severity, resolution_strategy, status, resolution_notes, notes
            FROM geometry_model_gap ORDER BY severity, parameter_code
        """),
        "validation_tasks": rows(conn, """
            SELECT id, geometry_model_id, title, priority, status, method,
                   acceptance_criteria
            FROM validation_task ORDER BY priority, id
        """),
        "claims": rows(conn, """
            SELECT pc.id AS claim_id, pc.product_variant_id,
                   pd.code, pd.canonical_name, pd.domain,
                   COALESCE(CAST(pc.value_real AS TEXT), CAST(pc.value_integer AS TEXT),
                            pc.value_text, CAST(pc.value_boolean AS TEXT), pc.value_date,
                            pc.value_json) AS value,
                   COALESCE(pc.unit, pc.normalized_unit, pd.canonical_unit) AS unit,
                   pc.claim_method, pc.evidence_grade, pc.review_status,
                   pc.conflict_status, pc.derivation_expression,
                   pc.derivation_notes, pc.uncertainty_text, pc.claim_scope
            FROM parameter_claim pc
            JOIN parameter_definition pd ON pd.id = pc.parameter_definition_id
            ORDER BY pd.domain, pd.code, pc.id
        """),
        "evidence": rows(conn, """
            SELECT e.id AS evidence_id, e.parameter_claim_id, e.evidence_type,
                   e.page_number, e.section_title, e.table_number, e.figure_number,
                   e.locator, e.quoted_text, e.extraction_method,
                   e.extraction_confidence, e.verified_by_human, e.notes AS evidence_notes,
                   sd.title AS source_title, sd.source_type, sd.url, sd.file_path,
                   sd.publication_date, sd.is_official
            FROM evidence e
            JOIN source_document sd ON sd.id = e.source_document_id
            ORDER BY e.parameter_claim_id, sd.title, e.page_number
        """),
        "applicability": rows(conn, """
            SELECT parameter_claim_id, dimension_code, operator, value_real,
                   value_text, range_min, range_max, value_json, unit, notes
            FROM claim_applicability ORDER BY parameter_claim_id, dimension_code
        """),
        "source_documents": rows(conn, """
            SELECT sd.id, sd.title, sd.source_type, sd.url, sd.publication_date,
                   sd.is_official, sd.notes, m.name AS manufacturer_name,
                   (SELECT COUNT(*) FROM evidence e WHERE e.source_document_id = sd.id) AS evidence_count
            FROM source_document sd
            LEFT JOIN manufacturer m ON m.id = sd.manufacturer_id
            ORDER BY sd.is_official DESC, sd.title
        """),
        "term_mappings": rows(conn, """
            SELECT ptm.id, ptm.source_term_original, ptm.source_value_original,
                   ptm.source_unit_original, ptm.mapping_status,
                   ptm.semantic_interpretation, ptm.interpretation_basis,
                   ptm.interpretation_confidence,
                   pd.code AS canonical_code, pd.canonical_name,
                   ptm.parameter_claim_id
            FROM parameter_term_mapping ptm
            LEFT JOIN parameter_definition pd ON pd.id = ptm.canonical_parameter_definition_id
            ORDER BY ptm.source_term_original
        """),
    }

    conn.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    total = sum(len(v) for k, v in data.items() if isinstance(v, list))
    print(f"saved: {OUT} ({OUT.stat().st_size} bytes, {total} records)")


if __name__ == "__main__":
    main()
