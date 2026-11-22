from typing import Callable

from ..core.world.grid_map_generator import coord_to_xy, xy_to_coord
from ..data.text.locale_data import get_locale_text

VIEWPORT_WIDTH = 10
VIEWPORT_HEIGHT = 10


def format_floor_number(floor: int | float | str) -> str:
    if isinstance(floor, bool):
        return str(int(floor))
    if isinstance(floor, int):
        return str(floor)
    if isinstance(floor, float):
        if floor.is_integer():
            return str(int(floor))
        text = f"{floor:.10f}".rstrip("0").rstrip(".")
        return "0" if text == "-0" else text
    raw = str(floor).strip()
    try:
        num = float(raw)
    except ValueError:
        return raw
    if num.is_integer():
        return str(int(num))
    text = f"{num:.10f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def render_grid_header(floor: int | float | str, floor_name: str, coord: str = "") -> str:
    floor_str = format_floor_number(floor)
    if coord:
        return get_locale_text("i18n_grid_map.header_title", floor=floor_str, floor_name=floor_name, coord=coord)
    return get_locale_text("i18n_world_grid.floor_title", floor=floor_str, floor_name=floor_name)


def get_run_coord(run) -> str:
    if run is None:
        return ""
    coord = str((getattr(run, "node_data", None) or {}).get("coord") or "")
    if coord:
        return coord
    fm = getattr(run, "floor_map", None)
    if fm is not None:
        return str((getattr(fm, "player_coords", None) or {}).get(getattr(run, "user_id", ""), "") or "")
    return ""


def get_run_coord_prefix(run) -> str:
    coord = get_run_coord(run)
    return f"{coord} " if coord else ""


def compute_viewport(width: int, height: int, viewer_coord: str, view_width: int = VIEWPORT_WIDTH, view_height: int = VIEWPORT_HEIGHT) -> tuple[int, int, int, int]:
    px, py = coord_to_xy(viewer_coord)
    if px < 0:
        px, py = 0, 0
    span_w = max(1, min(width, view_width))
    span_h = max(1, min(height, view_height))
    if width <= span_w:
        x0 = 0
    else:
        x0 = min(max(0, px - span_w // 2), width - span_w)
    if height <= span_h:
        y0 = 0
    else:
        y0 = min(max(0, py - span_h // 2), height - span_h)
    return x0, y0, x0 + span_w - 1, y0 + span_h - 1


def is_scrolling(width: int, height: int, view_width: int = VIEWPORT_WIDTH, view_height: int = VIEWPORT_HEIGHT) -> bool:
    return width > view_width or height > view_height


def viewport_text(width: int, height: int, viewport: tuple[int, int, int, int], view_width: int = VIEWPORT_WIDTH, view_height: int = VIEWPORT_HEIGHT) -> str:
    if not is_scrolling(width, height, view_width, view_height):
        return ""
    x0, y0, x1, y1 = viewport
    return get_locale_text(
        "i18n_world_grid.viewport",
        start=xy_to_coord(x0, y0),
        end=xy_to_coord(x1, y1),
        width=width,
        height=height,
    )


def render_grid_view(
    width: int,
    height: int,
    viewer_coord: str,
    icon_for: Callable[[str], str],
    view_width: int = VIEWPORT_WIDTH,
    view_height: int = VIEWPORT_HEIGHT,
    show_viewport: bool = True,
    floor: int | float | str | None = None,
    floor_name: str = "",
) -> tuple[list[str], set[str]]:
    viewport = compute_viewport(width, height, viewer_coord, view_width, view_height)
    x0, y0, x1, y1 = viewport
    lines: list[str] = []
    if floor is not None:
        lines.append(render_grid_header(floor, floor_name, viewer_coord))
    lines.append("   " + " ".join(chr(ord("A") + x) for x in range(x0, x1 + 1)))
    seen: set[str] = set()
    for y in range(y0, y1 + 1):
        cells = []
        for x in range(x0, x1 + 1):
            icon = icon_for(xy_to_coord(x, y))
            seen.add(icon)
            cells.append(icon)
        lines.append(f"{y + 1:>2} " + "".join(cells))
    if show_viewport:
        note = viewport_text(width, height, viewport, view_width, view_height)
        if note:
            lines.append(note)
    return lines, seen
