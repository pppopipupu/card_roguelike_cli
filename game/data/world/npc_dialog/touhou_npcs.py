TOUHOU_NPC_GRAPHS = {
    "hakurei_reimu": {
        "initial_affinity": 0,
        "cross_run_memory": True,
        "cycle_aware": True,
        "service_quotas": {"donate": 1, "chireiden_rumor": 1},
        "greetings": [
            "i18n_npc_crpg_touhou.reimu.greet_1",
            "i18n_npc_crpg_touhou.reimu.greet_2",
            "i18n_npc_crpg_touhou.reimu.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_touhou.reimu.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_touhou.reimu.spar_lost",
        "spar_execute_key": "i18n_npc_crpg_touhou.reimu.spar_execute",
        "entry_rules": [
            {"when": {"quest_ready": "quest_cycle_touhou"}, "node": "cycle_quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_revived_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "reimu_donate", "category": "service", "visible_if": {"service_available": "donate"}, "cost": {"gold": 10}, "service_key": "donate", "text_key": "i18n_npc_crpg_touhou.reimu.opt_donate", "effects": [{"type": "set_local_flag", "flag": "reimu_donated"}, {"type": "affinity", "delta": 2}, {"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1}, {"type": "sp", "amount": 2, "key": "i18n_chaos_expansion.npcs.hakurei_reimu.res_donate"}], "next_node": "root"},
                    {"id": "reimu_beg", "category": "topic", "visible_if": {"check_not_tried": "reimu_beg_check"}, "text_key": "i18n_npc_crpg_touhou.reimu.opt_beg", "check": {"check_id": "reimu_beg_check", "kind": "persuade", "dc": 13, "modifiers": [{"cond": {"local_flag": "reimu_donated"}, "bonus": 3, "reason_key": "i18n_npc_crpg_touhou.reimu.mod_donated"}], "auto_pass_cond": {"affinity_gte": 6}, "auto_pass_reason_key": "i18n_npc_crpg_touhou.reimu.auto_trusted", "on_success": {"next_node": "root", "effects": [{"type": "give_item", "item_id": "yin_yang_orb", "key": "i18n_chaos_expansion.npcs.hakurei_reimu.res_beg"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "hp", "amount": -2, "min_hp": 1}, {"type": "sp", "amount": 2, "key": "i18n_npc_crpg_touhou.reimu.res_beg_kick"}]}}},
                    {"id": "reimu_rumor", "category": "topic", "visible_if": {"service_available": "chireiden_rumor"}, "service_key": "chireiden_rumor", "text_key": "i18n_npc_crpg_touhou.reimu.opt_rumor", "effects": [{"type": "record_achievement", "stat": "chireiden_rumors_heard", "delta": 1}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "touhou_chireiden_rumor", "unique_token": "touhou_chireiden_rumor"}}, {"type": "message", "key": "i18n_chireiden.rumors.reimu_hint"}], "next_node": "root"},
                    {"id": "reimu_cycle_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_cycle_touhou"}, "text_key": "i18n_npc_crpg_touhou.reimu.opt_cycle_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_cycle_touhou"}], "next_node": "root"},
                    {"id": "reimu_marisa_clue", "category": "topic", "once_per_run": True, "visible_if": {"world_flag": "marisa_helped_cover"}, "text_key": "i18n_npc_crpg_touhou.reimu.opt_marisa_clue", "effects": [{"type": "affinity", "delta": 1}, {"type": "message", "key": "i18n_npc_crpg_touhou.reimu.res_marisa_clue"}], "next_node": "root"},
                    {"id": "reimu_provoke", "category": "challenge", "text_key": "i18n_npc_crpg_touhou.reimu.opt_provoke", "effects": [{"type": "affinity", "delta": -3}, {"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.hakurei_reimu.res_provoke"}]},
                    {"id": "reimu_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_touhou.reimu.cycle_revived_text",
                "options": [
                    {"id": "reimu_revive_talk", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_touhou.reimu.opt_revive_talk", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "message", "key": "i18n_npc_crpg_touhou.reimu.res_revive_talk"}], "next_node": "root"},
                    {"id": "reimu_revive_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_quest_turnin": {
                "text_key": "i18n_npc_crpg_touhou.reimu.cycle_turnin_text",
                "options": [
                    {"id": "reimu_turnin_cycle", "category": "quest", "text_key": "i18n_npc_crpg_touhou.reimu.opt_turnin_cycle", "effects": [{"type": "complete_quest", "quest_id": "quest_cycle_touhou"}, {"type": "affinity", "delta": 4}], "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_touhou.reimu.exhausted_text", "options": []},
        },
    },
    "kirisame_marisa": {
        "initial_affinity": 0,
        "cross_run_memory": True,
        "cycle_aware": False,
        "service_quotas": {"trade": 1, "mushroom": 1, "chireiden_rumor": 1},
        "greetings": [
            "i18n_npc_crpg_touhou.marisa.greet_1",
            "i18n_npc_crpg_touhou.marisa.greet_2",
            "i18n_npc_crpg_touhou.marisa.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_touhou.marisa.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_touhou.marisa.spar_lost",
        "entry_rules": [
            {"when": {"killed_before": True}, "node": "cycle_revived_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "marisa_trade_menu", "category": "service", "submenu_only": True, "visible_if": {"service_available": "trade"}, "text_key": "i18n_npc_crpg_touhou.marisa.opt_trade_menu", "next_node": "trade_menu"},
                    {"id": "marisa_mushroom", "category": "service", "visible_if": {"service_available": "mushroom"}, "service_key": "mushroom", "text_key": "i18n_npc_crpg_touhou.marisa.opt_mushroom", "effects": [{"type": "give_item", "item_id": "magic_mushroom", "key": "i18n_chaos_expansion.npcs.kirisame_marisa.res_mushroom_win"}], "next_node": "root"},
                    {"id": "marisa_rumor", "category": "topic", "visible_if": {"service_available": "chireiden_rumor"}, "service_key": "chireiden_rumor", "text_key": "i18n_npc_crpg_touhou.marisa.opt_rumor", "effects": [{"type": "record_achievement", "stat": "chireiden_rumors_heard", "delta": 1}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "touhou_chireiden_rumor", "unique_token": "touhou_chireiden_rumor"}}, {"type": "message", "key": "i18n_chireiden.rumors.marisa_hint"}], "next_node": "root"},
                    {"id": "marisa_library_stance", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_touhou.marisa.opt_library_stance", "next_node": "library_talk"},
                    {"id": "marisa_provoke", "category": "challenge", "text_key": "i18n_npc_crpg_touhou.marisa.opt_provoke", "effects": [{"type": "affinity", "delta": -3}, {"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.kirisame_marisa.res_spark_angry"}]},
                    {"id": "marisa_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_touhou.marisa.cycle_revived_text",
                "options": [
                    {"id": "marisa_rev_cont", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_touhou.marisa.opt_revive_talk", "effects": [{"type": "message", "key": "i18n_npc_crpg_touhou.marisa.res_revive_talk"}], "next_node": "root"},
                    {"id": "marisa_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "library_talk": {
                "text_key": "i18n_npc_crpg_touhou.marisa.library_text",
                "options": [
                    {"id": "marisa_cover", "category": "topic", "exclusive_group": "marisa_lib", "text_key": "i18n_npc_crpg_touhou.marisa.opt_cover", "effects": [{"type": "set_world_flag", "flag": "marisa_helped_cover"}, {"type": "affinity", "delta": 2}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "touhou_marisa_cover", "unique_token": "touhou_marisa_cover"}}, {"type": "message", "key": "i18n_npc_crpg_touhou.marisa.res_cover"}], "next_node": "root"},
                    {"id": "marisa_scold", "category": "topic", "exclusive_group": "marisa_lib", "text_key": "i18n_npc_crpg_touhou.marisa.opt_scold", "effects": [{"type": "set_world_flag", "flag": "marisa_scolded"}, {"type": "affinity", "delta": -1}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "touhou_marisa_report", "unique_token": "touhou_marisa_report"}}, {"type": "message", "key": "i18n_npc_crpg_touhou.marisa.res_scold"}], "next_node": "root"},
                ],
            },
            "trade_menu": {
                "text_key": "i18n_npc_crpg_touhou.marisa.trade_text",
                "options": [
                    {"id": "marisa_buy_hakkero_disc", "category": "service", "visible_if": {"all": [{"service_available": "trade"}, {"local_flag": "marisa_discount"}]}, "cost": {"gold": 10}, "service_key": "trade", "text_key": "i18n_npc_crpg_touhou.marisa.opt_buy_attack", "effects": [{"type": "give_item", "item_id": "mini_hakkero", "key": "i18n_chaos_expansion.npcs.kirisame_marisa.res_trade"}], "next_node": "root"},
                    {"id": "marisa_buy_key_disc", "category": "service", "visible_if": {"all": [{"service_available": "trade"}, {"local_flag": "marisa_discount"}]}, "cost": {"gold": 10}, "service_key": "trade", "text_key": "i18n_npc_crpg_touhou.marisa.opt_buy_utility", "effects": [{"type": "give_item", "item_id": "skeleton_key", "key": "i18n_chaos_expansion.npcs.kirisame_marisa.res_trade"}], "next_node": "root"},
                    {"id": "marisa_buy_hakkero", "category": "service", "visible_if": {"all": [{"service_available": "trade"}, {"not": {"local_flag": "marisa_discount"}}]}, "cost": {"gold": 20}, "service_key": "trade", "text_key": "i18n_npc_crpg_touhou.marisa.opt_buy_attack", "effects": [{"type": "give_item", "item_id": "mini_hakkero", "key": "i18n_chaos_expansion.npcs.kirisame_marisa.res_trade"}], "next_node": "root"},
                    {"id": "marisa_buy_key", "category": "service", "visible_if": {"all": [{"service_available": "trade"}, {"not": {"local_flag": "marisa_discount"}}]}, "cost": {"gold": 20}, "service_key": "trade", "text_key": "i18n_npc_crpg_touhou.marisa.opt_buy_utility", "effects": [{"type": "give_item", "item_id": "skeleton_key", "key": "i18n_chaos_expansion.npcs.kirisame_marisa.res_trade"}], "next_node": "root"},
                    {"id": "marisa_haggle", "category": "topic", "visible_if": {"all": [{"check_not_tried": "marisa_haggle_check"}, {"not": {"local_flag": "marisa_discount"}}]}, "text_key": "i18n_npc_crpg_touhou.marisa.opt_haggle", "check": {"check_id": "marisa_haggle_check", "kind": "haggle", "dc": 12, "modifiers": [{"cond": {"has_item": "ancient_notes"}, "bonus": 2, "reason_key": "i18n_npc_crpg_touhou.marisa.mod_notes"}], "on_success": {"next_node": "trade_menu", "effects": [{"type": "set_local_flag", "flag": "marisa_discount"}, {"type": "message", "key": "i18n_npc_crpg_touhou.marisa.res_haggle_ok"}]}, "on_fail": {"next_node": "trade_menu", "effects": [{"type": "give_item", "item_id": "magic_mushroom", "key": "i18n_npc_crpg_touhou.marisa.res_haggle_fail"}]}}},
                    {"id": "marisa_trade_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_touhou.marisa.exhausted_text", "options": []},
        },
    },
    "patchouli_knowledge": {
        "initial_affinity": -1,
        "cross_run_memory": True,
        "cycle_aware": True,
        "service_quotas": {"tidy": 1, "study": 1, "chireiden_rumor": 1},
        "greetings": [
            "i18n_npc_crpg_touhou.patchouli.greet_1",
            "i18n_npc_crpg_touhou.patchouli.greet_2",
            "i18n_npc_crpg_touhou.patchouli.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_touhou.patchouli.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_touhou.patchouli.spar_lost",
        "entry_rules": [
            {"when": {"quest_ready": "quest_cycle_touhou"}, "node": "cycle_quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_revived_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "patch_tidy", "category": "service", "visible_if": {"service_available": "tidy"}, "service_key": "tidy", "text_key": "i18n_npc_crpg_touhou.patchouli.opt_tidy", "effects": [{"type": "affinity", "delta": 2}, {"type": "gold", "amount": 20}, {"type": "sp", "amount": 2, "key": "i18n_chaos_expansion.npcs.patchouli_knowledge.res_tidy"}], "next_node": "root"},
                    {"id": "patch_study", "category": "service", "visible_if": {"all": [{"service_available": "study"}, {"affinity_gte": 0}]}, "service_key": "study", "text_key": "i18n_npc_crpg_touhou.patchouli.opt_study", "effects": [{"type": "add_buff", "buff_id": "arcane_clarity", "stacks": 1}, {"type": "add_card", "pool": "npc_scholar", "fallback": "fireball", "key": "i18n_chaos_expansion.npcs.patchouli_knowledge.res_study"}], "next_node": "root"},
                    {"id": "patch_insight", "category": "topic", "visible_if": {"check_not_tried": "patch_elements_check"}, "text_key": "i18n_npc_crpg_touhou.patchouli.opt_insight", "check": {"check_id": "patch_elements_check", "kind": "insight", "dc": 12, "auto_pass_cond": {"player_class": "法师"}, "auto_pass_reason_key": "i18n_npc_crpg_touhou.patchouli.auto_wizard", "on_success": {"next_node": "root", "effects": [{"type": "affinity", "delta": 3}, {"type": "add_buff", "buff_id": "arcane_clarity", "stacks": 1, "key": "i18n_npc_crpg_touhou.patchouli.res_insight_ok"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "affinity", "delta": -1}, {"type": "message", "key": "i18n_npc_crpg_touhou.patchouli.res_insight_fail"}]}}},
                    {"id": "patch_rumor", "category": "topic", "visible_if": {"service_available": "chireiden_rumor"}, "service_key": "chireiden_rumor", "text_key": "i18n_npc_crpg_touhou.patchouli.opt_rumor", "effects": [{"type": "record_achievement", "stat": "chireiden_rumors_heard", "delta": 1}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "touhou_chireiden_rumor", "unique_token": "touhou_chireiden_rumor"}}, {"type": "message", "key": "i18n_chireiden.rumors.patchouli_hint"}], "next_node": "root"},
                    {"id": "patch_report_marisa", "category": "topic", "once_per_run": True, "visible_if": {"world_flag": "marisa_scolded"}, "text_key": "i18n_npc_crpg_touhou.patchouli.opt_report_marisa", "effects": [{"type": "affinity", "delta": 2}, {"type": "set_world_flag", "flag": "patch_helped"}, {"type": "gold", "amount": 25}, {"type": "message", "key": "i18n_npc_crpg_touhou.patchouli.res_report_marisa"}], "next_node": "root"},
                    {"id": "patch_cycle_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_cycle_touhou"}, "text_key": "i18n_npc_crpg_touhou.patchouli.opt_cycle_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_cycle_touhou"}], "next_node": "root"},
                    {"id": "patch_provoke", "category": "challenge", "text_key": "i18n_npc_crpg_touhou.patchouli.opt_provoke", "effects": [{"type": "affinity", "delta": -3}, {"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.patchouli_knowledge.res_provoke"}]},
                    {"id": "patch_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_touhou.patchouli.cycle_revived_text",
                "options": [
                    {"id": "patch_rev_ask", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_touhou.patchouli.opt_revive_talk", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "message", "key": "i18n_npc_crpg_touhou.patchouli.res_revive_talk"}], "next_node": "root"},
                    {"id": "patch_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_quest_turnin": {
                "text_key": "i18n_npc_crpg_touhou.patchouli.cycle_turnin_text",
                "options": [
                    {"id": "patch_turnin_cycle", "category": "quest", "text_key": "i18n_npc_crpg_touhou.patchouli.opt_turnin_cycle", "effects": [{"type": "complete_quest", "quest_id": "quest_cycle_touhou"}, {"type": "affinity", "delta": 4}], "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_touhou.patchouli.exhausted_text", "options": []},
        },
    },
    "izayoi_sakuya": {
        "initial_affinity": 0,
        "cross_run_memory": True,
        "cycle_aware": True,
        "service_quotas": {"tea": 1, "knives": 1},
        "greetings": [
            "i18n_npc_crpg_touhou.sakuya.greet_1",
            "i18n_npc_crpg_touhou.sakuya.greet_2",
        ],
        "spar_yield_key": "i18n_npc_crpg_touhou.sakuya.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_touhou.sakuya.spar_lost",
        "entry_rules": [{"when": {"killed_before": True}, "node": "cycle_revived_root"}],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "sakuya_tea", "category": "service", "visible_if": {"service_available": "tea"}, "service_key": "tea", "text_key": "i18n_npc_crpg_touhou.sakuya.opt_tea", "effects": [{"type": "hp", "amount": 8}, {"type": "sp", "amount": 2, "key": "i18n_npc_crpg_touhou.sakuya.res_tea"}], "next_node": "root"},
                    {"id": "sakuya_time_talk", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_touhou.sakuya.opt_time_talk", "effects": [{"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "touhou_sakuya_time", "unique_token": "touhou_sakuya_time"}}, {"type": "message", "key": "i18n_npc_crpg_touhou.sakuya.res_time_talk"}], "next_node": "root"},
                    {"id": "sakuya_homura_link", "category": "topic", "once_per_run": True, "visible_if": {"cycle_flag": "met_homura"}, "text_key": "i18n_npc_crpg_touhou.sakuya.opt_homura_link", "effects": [{"type": "affinity", "delta": 2}, {"type": "set_cycle_flag", "flag": "sakuya_noted_homura"}, {"type": "message", "key": "i18n_npc_crpg_touhou.sakuya.res_homura_link"}], "next_node": "root"},
                    {"id": "sakuya_persuade_knife", "category": "topic", "visible_if": {"all": [{"service_available": "knives"}, {"check_not_tried": "sakuya_knife_check"}]}, "text_key": "i18n_npc_crpg_touhou.sakuya.opt_persuade_knife", "check": {"check_id": "sakuya_knife_check", "kind": "persuade", "dc": 13, "modifiers": [{"cond": {"world_flag": "patch_helped"}, "bonus": 3, "reason_key": "i18n_npc_crpg_touhou.sakuya.mod_patch"}], "on_success": {"next_node": "root", "effects": [{"type": "consume_service", "service": "knives"}, {"type": "give_item", "item_id": "skeleton_key", "key": "i18n_npc_crpg_touhou.sakuya.res_knife_ok"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "affinity", "delta": -1}, {"type": "message", "key": "i18n_npc_crpg_touhou.sakuya.res_knife_fail"}]}}},
                    {"id": "sakuya_provoke", "category": "challenge", "text_key": "i18n_npc_crpg_touhou.sakuya.opt_provoke", "effects": [{"type": "affinity", "delta": -3}, {"type": "start_combat", "non_lethal": True, "intro_key": "i18n_npc_crpg_touhou.sakuya.res_provoke"}]},
                    {"id": "sakuya_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_touhou.sakuya.cycle_revived_text",
                "options": [
                    {"id": "sakuya_rev_talk", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_touhou.sakuya.opt_revive_talk", "effects": [{"type": "message", "key": "i18n_npc_crpg_touhou.sakuya.res_revive_talk"}], "next_node": "root"},
                    {"id": "sakuya_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_touhou.sakuya.exhausted_text", "options": []},
        },
    },
    "komeiji_koishi": {
        "initial_affinity": 1,
        "cross_run_memory": True,
        "cycle_aware": True,
        "service_quotas": {"game": 1, "chireiden_rumor": 1},
        "greetings": [
            "i18n_npc_crpg_touhou.koishi.greet_1",
            "i18n_npc_crpg_touhou.koishi.greet_2",
        ],
        "spar_yield_key": "i18n_npc_crpg_touhou.koishi.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_touhou.koishi.spar_lost",
        "spar_execute_key": "i18n_npc_crpg_touhou.koishi.spar_execute",
        "entry_rules": [{"when": {"killed_before": True}, "node": "cycle_revived_root"}],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "koishi_game", "category": "service", "visible_if": {"service_available": "game"}, "text_key": "i18n_npc_crpg_touhou.koishi.opt_game", "next_node": "hat_game"},
                    {"id": "koishi_rhyme", "category": "topic", "visible_if": {"check_not_tried": "koishi_rhyme_check"}, "text_key": "i18n_npc_crpg_touhou.koishi.opt_rhyme", "check": {"check_id": "koishi_rhyme_check", "kind": "insight", "dc": 13, "on_success": {"next_node": "root", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "touhou_koishi_rhyme", "unique_token": "touhou_koishi_rhyme"}}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "meta_koishi_cycle", "unique_token": "meta_koishi_cycle"}}, {"type": "reveal_ritual", "recap_id": "koishi_ritual", "key": "i18n_npc_crpg_touhou.koishi.res_rhyme_ok", "empty_key": "i18n_npc_crpg_touhou.koishi.res_rhyme_empty"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "message", "key": "i18n_npc_crpg_touhou.koishi.res_rhyme_fail"}]}}},
                    {"id": "koishi_rumor", "category": "topic", "visible_if": {"service_available": "chireiden_rumor"}, "service_key": "chireiden_rumor", "text_key": "i18n_npc_crpg_touhou.koishi.opt_rumor", "effects": [{"type": "record_achievement", "stat": "chireiden_rumors_heard", "delta": 1}, {"type": "message", "key": "i18n_npc_crpg_touhou.koishi.res_rumor"}], "next_node": "root"},
                    {"id": "koishi_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "hat_game": {
                "text_key": "i18n_npc_crpg_touhou.koishi.hat_text",
                "options": [
                    {"id": "koishi_left_hand", "category": "service", "exclusive_group": "koishi_guess", "service_key": "game", "text_key": "i18n_npc_crpg_touhou.koishi.opt_left", "effects": [{"type": "give_item", "item_id": "sugar_cube_pack", "key": "i18n_npc_crpg_touhou.koishi.res_left"}], "next_node": "root"},
                    {"id": "koishi_right_hand", "category": "service", "exclusive_group": "koishi_guess", "service_key": "game", "text_key": "i18n_npc_crpg_touhou.koishi.opt_right", "effects": [{"type": "sp", "amount": 2}, {"type": "gold", "amount": 18, "key": "i18n_npc_crpg_touhou.koishi.res_right"}], "next_node": "root"},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_touhou.koishi.cycle_revived_text",
                "options": [
                    {"id": "koishi_rev_play", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_touhou.koishi.opt_revive_talk", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "message", "key": "i18n_npc_crpg_touhou.koishi.res_revive_talk"}], "next_node": "root"},
                    {"id": "koishi_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_touhou.koishi.exhausted_text", "options": []},
        },
    },
}
