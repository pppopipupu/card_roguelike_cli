from typing import List, Tuple
from .....data.world.room_interact_data import ROOM_NPCS
from ....text.events import LocaleText, RenderedText, TextDocument, TextNode, locale_text
from ....text.pipeline import render_text, render_text_node


def render_crpg_dialog_screen(run, name: str, body_nodes: List[LocaleText | RenderedText], option_texts: List[str]) -> str:
    doc: TextDocument = [
        RenderedText(section="header", text=render_text_node(locale_text("i18n_grid_map.separator"))),
        LocaleText(section="header", key="i18n_room_interact.dialog.title", params={"name": name}),
    ]
    outcomes = list((run.node_data or {}).get("last_outcome_nodes") or [])
    for raw in outcomes:
        if isinstance(raw, dict):
            key = str(raw.get("key", ""))
            params = dict(raw.get("params") or {})
            if key:
                doc.append(LocaleText(section="outcome", key=key, params=params))
            elif raw.get("text"):
                doc.append(RenderedText(section="outcome", text=str(raw["text"])))
        elif isinstance(raw, str) and raw:
            doc.append(RenderedText(section="outcome", text=raw))
        elif isinstance(raw, (LocaleText, RenderedText)):
            raw.section = "outcome"
            doc.append(raw)

    for node in body_nodes:
        node.section = "body"
        doc.append(node)

    for idx, opt_text in enumerate(option_texts, 1):
        doc.append(RenderedText(section="options", text=f" [{idx}] {opt_text}"))

    footer_key = "renderer_explore.guide_folded" if getattr(run.player, "fold_guide", False) else "i18n_room_interact.dialog.footer"
    doc.append(LocaleText(section="footer", key=footer_key))
    doc.append(RenderedText(section="footer", text=render_text_node(locale_text("i18n_grid_map.separator"))))
    return render_text(doc, "room_dialog")


def render_legacy_dialog_screen(run, name: str, text: str, opts: List[str]) -> str:
    return render_crpg_dialog_screen(run, name, [RenderedText(text=text)], opts)


def serialize_outcome_nodes(nodes) -> List[dict]:
    out: List[dict] = []
    for node in nodes or ():
        if isinstance(node, LocaleText):
            out.append(
                {
                    "type": "locale",
                    "key": node.key,
                    "params": serialize_outcome_params(node.params),
                }
            )
        elif isinstance(node, RenderedText):
            out.append({"type": "rendered", "text": node.text})
        elif isinstance(node, TextNode):
            out.append({"type": "rendered", "text": render_text_node(node)})
        elif isinstance(node, str) and node:
            out.append({"type": "rendered", "text": node})
    return out


def serialize_outcome_params(params: dict) -> dict:
    res = {}
    for k, v in (params or {}).items():
        if isinstance(v, TextNode):
            res[k] = render_text_node(v)
        else:
            res[k] = v
    return res


def get_npc_display_name(npc_id: str) -> str:
    cfg = ROOM_NPCS.get(npc_id, {})
    name_key = cfg.get("name_key")
    return render_text_node(locale_text(name_key)) if name_key else npc_id
