META_NPC_GRAPHS = {
    "pppopipupu_dungeon": {
        "initial_affinity": 1,
        "cross_run_memory": True,
        "cycle_aware": True,
        "service_quotas": {"supply": 1, "meta_story": 1, "meta_enchant": 1},
        "greetings": [
            "i18n_npc_crpg_meta.pppo.greet_1",
            "i18n_npc_crpg_meta.pppo.greet_2",
        ],
        "spar_yield_key": "i18n_npc_crpg_meta.pppo.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_meta.pppo.spar_lost",
        "spar_execute_key": "i18n_npc_crpg_meta.pppo.spar_execute",
        "entry_rules": [
            {"when": {"quest_ready": "quest_cycle_meta"}, "node": "cycle_quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_revived_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "pppo_ask_cycle", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_meta.pppo.opt_ask_cycle", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "meta_cycle_truth", "unique_token": "meta_cycle_truth"}}, {"type": "message", "key": "i18n_npc_crpg_meta.pppo.res_ask_cycle"}], "next_node": "root"},
                    {"id": "pppo_meta_talk", "category": "topic", "visible_if": {"service_available": "meta_story"}, "service_key": "meta_story", "text_key": "i18n_npc_crpg_meta.pppo.opt_meta_talk", "next_node": "meta_branch"},
                    {"id": "pppo_insight_stash", "category": "topic", "visible_if": {"all": [{"service_available": "supply"}, {"check_not_tried": "pppo_stash_check"}]}, "text_key": "i18n_npc_crpg_meta.pppo.opt_insight_stash", "check": {"check_id": "pppo_stash_check", "kind": "insight", "dc": 13, "modifiers": [{"cond": {"cycle_flag": "asked_cycle_truth"}, "bonus": 2, "reason_key": "i18n_npc_crpg_meta.pppo.mod_cycle"}], "on_success": {"next_node": "root", "effects": [{"type": "consume_service", "service": "supply"}, {"type": "give_item", "item_id": "glowing_runestone"}, {"type": "reveal_rooms", "count": 1, "key": "i18n_npc_crpg_meta.pppo.res_stash_ok", "empty_key": "i18n_npc_crpg_meta.pppo.res_stash_item"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "consume_service", "service": "supply"}, {"type": "give_item", "item_id": "sugar_cube_pack", "key": "i18n_npc_crpg_meta.pppo.res_stash_fail"}]}}},
                    {"id": "pppo_cycle_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_cycle_meta"}, "text_key": "i18n_npc_crpg_meta.pppo.opt_cycle_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_cycle_meta"}], "next_node": "root"},
                    {"id": "pppo_spar", "category": "challenge", "text_key": "i18n_npc_crpg_meta.pppo.opt_spar", "effects": [{"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "meta_spar_pppo", "unique_token": "meta_spar_pppo"}}, {"type": "start_combat", "non_lethal": True, "intro_key": "i18n_npc_crpg_meta.pppo.res_spar"}]},
                    {"id": "pppo_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "meta_branch": {
                "text_key": "i18n_npc_crpg_meta.pppo.meta_branch_text",
                "options": [
                    {"id": "pppo_meta_npc_rework", "category": "topic", "text_key": "i18n_npc_crpg_meta.pppo.opt_meta_rework", "effects": [{"type": "message", "key": "i18n_npc_crpg_meta.pppo.res_meta_rework"}], "next_node": "root"},
                    {"id": "pppo_meta_vibe", "category": "topic", "text_key": "i18n_npc_crpg_meta.pppo.opt_meta_vibe", "effects": [{"type": "message", "key": "i18n_npc_crpg_meta.pppo.res_meta_vibe"}], "next_node": "root"},
                    {"id": "pppo_meta_json", "category": "topic", "text_key": "i18n_npc_crpg_meta.pppo.opt_meta_json", "effects": [{"type": "message", "key": "i18n_npc_crpg_meta.pppo.res_meta_json"}], "next_node": "root"},
                    {"id": "pppo_meta_enchants", "category": "topic", "text_key": "i18n_npc_crpg_meta.pppo.opt_meta_enchants", "effects": [{"type": "message", "key": "i18n_npc_crpg_meta.pppo.res_meta_enchants"}], "next_node": "root"},
                    {"id": "pppo_meta_show_enchant", "category": "service", "visible_if": {"all": [{"has_enchanted_card": True}, {"service_available": "meta_enchant"}]}, "service_key": "meta_enchant", "text_key": "i18n_npc_crpg_meta.pppo.opt_meta_show_enchant", "effects": [{"type": "affinity", "delta": 1}, {"type": "enchant_random_card", "key": "i18n_npc_crpg_meta.pppo.res_meta_show_enchant"}], "next_node": "root"},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_meta.pppo.cycle_revived_text",
                "options": [
                    {"id": "pppo_rev_ask", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_meta.pppo.opt_revive_talk", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "meta_reunion_seen", "unique_token": "meta_reunion_seen"}}, {"type": "message", "key": "i18n_npc_crpg_meta.pppo.res_revive_talk"}], "next_node": "root"},
                    {"id": "pppo_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_quest_turnin": {
                "text_key": "i18n_npc_crpg_meta.pppo.cycle_turnin_text",
                "options": [
                    {"id": "pppo_turnin_cycle", "category": "quest", "text_key": "i18n_npc_crpg_meta.pppo.opt_turnin_cycle", "effects": [{"type": "complete_quest", "quest_id": "quest_cycle_meta"}, {"type": "affinity", "delta": 4}], "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_meta.pppo.exhausted_text", "options": []},
        },
    },
}
