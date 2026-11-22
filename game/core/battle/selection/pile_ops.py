from ....models.state import ensure_card_state


def pop_selected_pile_cards(pile: list, selected: list[dict]) -> list:
    matched_indices: list[int] = []
    used_indices: set[int] = set()
    for cand in selected:
        src_idx = cand.get("source_idx")
        card_id = cand.get("card_id")
        upgraded = bool(cand.get("upgraded", False))
        gems = list(cand.get("gems", []) or [])
        chosen_idx = None
        if isinstance(src_idx, int) and 0 <= src_idx < len(pile) and src_idx not in used_indices:
            st = ensure_card_state(pile[src_idx])
            if st.id == card_id and bool(st.upgraded) == upgraded and list(st.gems or []) == gems:
                chosen_idx = src_idx
        if chosen_idx is None:
            for i, raw_c in enumerate(pile):
                if i in used_indices:
                    continue
                st = ensure_card_state(raw_c)
                if st.id == card_id and bool(st.upgraded) == upgraded and list(st.gems or []) == gems:
                    chosen_idx = i
                    break
        if chosen_idx is not None:
            used_indices.add(chosen_idx)
            matched_indices.append(chosen_idx)
    items_by_idx = {idx: pile[idx] for idx in matched_indices}
    for idx in sorted(matched_indices, reverse=True):
        pile.pop(idx)
    return [items_by_idx[idx] for idx in matched_indices]
