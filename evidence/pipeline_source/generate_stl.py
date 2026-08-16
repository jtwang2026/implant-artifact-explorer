"""
参数化生成任意 (thread_depth, thread_pitch) 的种植体 STL。

复用 dental_implant_kb 的 build_osstem_level2_parametric_v020.py 几何内核，
修改 assumptions JSON 中的螺纹深度/螺距后生成网格。

用法:
  from cbct_simulation.explore.generate_stl import generate_stl_for_params

  stl_path = generate_stl_for_params(thread_depth_mm=0.5, thread_pitch_mm=1.4, out_dir=...)
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from scripts.project_config import (
    KB_GEOM_BUILDER,
    KB_ASSUMPTIONS,
    EXPLORE_DIR,
)

BUILDER_PATH = KB_GEOM_BUILDER
ASSUMPTION_PATH = KB_ASSUMPTIONS


def _load_builder():
    """加载 build 脚本模块（复用几何内核）"""
    spec = importlib.util.spec_from_file_location("osstem_builder", BUILDER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def generate_stl_for_params(
    thread_depth_mm: float,
    thread_pitch_mm: float,
    out_dir: Path,
    stl_name: str | None = None,
) -> Path:
    """
    生成指定螺纹深度/螺距的 STL。

    Returns: 生成的 STL 路径
    """
    builder = _load_builder()

    # 读取假设 JSON
    config = json.loads(ASSUMPTION_PATH.read_text(encoding="utf-8"))

    # 校验
    if config["assumption_set_identity"]["product_ref"] != builder.EXPECTED_REF:
        raise RuntimeError("Unexpected product REF")
    if config.get("validation", {}).get("status") != "passed":
        raise RuntimeError("Assumption set not validated")

    # 修改螺纹深度/螺距
    eng = config["engineering_assumptions"]
    if "thread_depth_mm" in eng:
        eng["thread_depth_mm"]["value"] = float(thread_depth_mm)
    if "thread_pitch_mm" in eng:
        eng["thread_pitch_mm"]["value"] = float(thread_pitch_mm)

    # 解析官方/假设参数
    total_length = builder.official_value(config, "implant_length_mm")
    nominal_diameter = builder.official_value(config, "implant_nominal_diameter_mm")
    apex_length = builder.assumption_value(config, "apex_length_mm")
    apex_diameter = builder.assumption_value(config, "apex_diameter_mm")
    thread_start_z = builder.assumption_value(config, "thread_start_z_mm")
    thread_end_z = builder.assumption_value(config, "thread_end_z_mm")
    thread_depth = builder.assumption_value(config, "thread_depth_mm")
    thread_pitch = builder.assumption_value(config, "thread_pitch_mm")
    thread_included_angle = builder.assumption_value(config, "thread_included_angle_deg")
    thread_start_count = int(builder.assumption_value(config, "thread_start_count"))
    thread_apical_runout = builder.assumption_value(config, "thread_apical_runout_mm")
    thread_coronal_runout = builder.assumption_value(config, "thread_coronal_runout_mm")

    # 生成表面网格（复用核心函数）→ 返回 (triangles, rings)
    triangles, _rings = builder.build_surface_mesh(
        total_length_mm=total_length,
        nominal_radius_mm=nominal_diameter / 2.0,
        apex_radius_mm=apex_diameter / 2.0,
        apex_length_mm=apex_length,
        thread_start_z_mm=thread_start_z,
        thread_end_z_mm=thread_end_z,
        apical_runout_mm=thread_apical_runout,
        coronal_runout_mm=thread_coronal_runout,
        thread_pitch_mm=thread_pitch,
        thread_depth_mm=thread_depth,
        thread_start_count=thread_start_count,
        theta_segments=builder.THETA_SEGMENTS,
        z_segments=builder.Z_SEGMENTS,
    )

    # 写 STL
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if stl_name is None:
        stl_name = f"stl_d{thread_depth_mm:.2f}_p{thread_pitch_mm:.2f}.stl"
    stl_path = out_dir / stl_name
    builder.write_binary_stl(stl_path, triangles, header_text="CI-MAS explore")

    return stl_path


if __name__ == "__main__":
    import tempfile
    p = generate_stl_for_params(0.5, 1.4, Path(tempfile.gettempdir()) / "stl_test")
    print(f"生成: {p}")
