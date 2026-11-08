from ..models.state import GameRun
from ..entities import get_relic_name, get_relic_desc
from ..cards import ALL_CARDS

def render_map_select(run: GameRun) -> str:
    p = run.player
    options = run.node_data.get("options", [])
    relics_str = ""
    if p.relics:
        relics_str = "\n🎒 遗物：" + " ".join([f"【{get_relic_name(r)}】" for r in p.relics])
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🗺️ 【第 {p.stage} 关：请选择前进路线】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}" + relics_str,
        ""
    ]
    preview_lines = ["【树状路线预览】"]
    nodes_dict = {}
    nodes_by_stage = {}
    for stage_str, layer in run.map_data.get("nodes", {}).items():
        stg = int(stage_str)
        nodes_by_stage[stg] = layer
        for nd in layer:
            nodes_dict[nd["id"]] = nd
    curr_id = run.map_data.get("current_node_id")
    type_names = {
        "battle": "遭遇战",
        "elite": "精英战",
        "event": "神秘事件",
        "shop": "奇妙商店",
        "rest": "篝火营地",
        "treasure": "古老宝箱房",
        "boss": "首领战",
        "corpse": "尸体"
    }
    max_preview_stage = min(20, p.stage + 3)
    curr_layer_nodes = []
    if not curr_id:
        curr_layer_nodes = nodes_by_stage.get(p.stage, [])
    else:
        curr_node = nodes_dict.get(curr_id)
        if curr_node:
            curr_layer_nodes = [nodes_dict[nid] for nid in curr_node.get("next", []) if nid in nodes_dict]
    if curr_layer_nodes:
        preview_lines.append(f"  📍 当前(第 {p.stage} 层):")
        for idx, nd in enumerate(curr_layer_nodes, 1):
            next_types = []
            for nid in nd.get("next", []):
                next_node = nodes_dict.get(nid)
                if next_node:
                    next_types.append(type_names.get(next_node["type"], next_node["type"]))
            next_str = f" (去往第 {p.stage+1} 层: {', '.join(next_types)})" if next_types else " (终点)"
            preview_lines.append(f"    [{idx}] {type_names.get(nd['type'], nd['type'])}{next_str}")
    for next_s in range(p.stage + 1, max_preview_stage + 1):
        next_layer_nodes = nodes_by_stage.get(next_s, [])
        if not next_layer_nodes:
            continue
        reachable_ids = set()
        prev_layer_nodes = []
        if next_s - 1 == p.stage:
            prev_layer_nodes = curr_layer_nodes
        else:
            prev_layer_nodes = nodes_by_stage.get(next_s - 1, [])
        for pn in prev_layer_nodes:
            for nid in pn.get("next", []):
                reachable_ids.add(nid)
        filtered_nodes = [nd for nd in next_layer_nodes if nd["id"] in reachable_ids]
        if not filtered_nodes:
            filtered_nodes = next_layer_nodes
        layer_title = "🔮 下一步" if next_s == p.stage + 1 else ("🔥 再下一步" if next_s == p.stage + 2 else "🎁 目标")
        preview_lines.append(f"  {layer_title}(第 {next_s} 层):")
        for idx, nd in enumerate(filtered_nodes, 1):
            next_types = []
            for nid in nd.get("next", []):
                next_node = nodes_dict.get(nid)
                if next_node:
                    next_types.append(type_names.get(next_node["type"], next_node["type"]))
            next_str = f" (去往第 {next_s+1} 层: {', '.join(next_types)})" if next_types else " (终点)"
            preview_lines.append(f"    [{idx}] {type_names.get(nd['type'], nd['type'])}{next_str}")
    lines.extend(preview_lines)
    lines.append("")
    lines.append("前方道路出现了分支，请选择你前往的下一个节点：")
    for idx, opt in enumerate(options, 1):
        lines.append(f" [{idx}] {opt.get('desc', '')}")
    if p.fold_guide:
        lines.append("💬 提示：操作指南已折叠。输入 /rogue 折叠 可展开。")
    else:
        lines.append("💬 选择路线指令：/rogue c <分支序号>")
    lines.append("💡 提示：输入 /rogue help 或 help 可查看指令用法帮助。")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_start_ancient(run: GameRun) -> str:
    p = run.player
    options = run.node_data.get("options", [])
    style = run.node_data.get("style", "default")
    style_names = {
        "default": "先古",
        "abyss": "深渊",
        "glacier": "极寒"
    }
    name_str = style_names.get(style, "先古")
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🌌 【第 1 关：{name_str}契约】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}",
        "",
        f"在你面前浮现出了三座石碑，每座石碑上都铭刻着不同的{name_str}契约。选择其中的契约以获取力量，但命运总会索取它的代价：",
        ""
    ]
    for idx, opt in enumerate(options, 1):
        rid = opt["relic"]
        rname = get_relic_name(rid)
        rdesc = get_relic_desc(rid)
        if opt["type"] == "double":
            lines.append(f" [{idx}] ⚖️ {name_str}遗物：【{rname}】\n     效果：{rdesc}")
        else:
            cid = opt["card"]
            cname = ALL_CARDS[cid].name
            cdesc = ALL_CARDS[cid].desc
            lines.append(f" [{idx}] 🕸️ {name_str}卡牌：【{cname}】 ➕ 代价遗物【{rname}】\n     效果：获得该强力卡牌 ({cdesc}) 同时获得其伴随的代价 ({rdesc})")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("💬 选择契约指令：/rogue c <契约序号>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_ancient(run: GameRun) -> str:
    p = run.player
    options = run.node_data.get("options", [])
    style = run.node_data.get("style", "default")
    style_names = {
        "default": "先古",
        "abyss": "深渊",
        "glacier": "极寒"
    }
    name_str = style_names.get(style, "先古")
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🌟 【第 {p.stage} 关：{name_str}赐福】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}",
        "",
        f"空气中浮现出纯净的奥术光辉。{name_str}的意志再次眷顾了你，向你降下丰厚的赐福礼包：",
        ""
    ]
    for idx, opt in enumerate(options, 1):
        rid = opt["relic"]
        rname = get_relic_name(rid)
        rdesc = get_relic_desc(rid)
        if opt.get("type") == "double":
            lines.append(f" [{idx}] ⚖️ {name_str}遗物：【{rname}】\n     效果：{rdesc}")
            continue
        cid = opt["card"]
        cname = ALL_CARDS[cid].name
        cdesc = ALL_CARDS[cid].desc
        lines.append(f" [{idx}] 🎁 赐福包：【{rname}】 ➕ 传奇卡牌【{cname}】\n     效果：获得被动遗物（{rdesc}）与卡牌（{cdesc}）")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("💬 选择赐福指令：/rogue c <赐福序号>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
