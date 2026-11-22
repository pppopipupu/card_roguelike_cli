CORE_NPC_GRAPHS = {
    "wandering_smith": {
        "initial_affinity": 0,
        "cross_run_memory": False,
        "cycle_aware": False,
        "service_quotas": {"forge": 1, "gem": 1, "pickaxe": 1, "bellows": 1, "bow_part": 1},
        "greetings": [
            "i18n_npc_crpg_core.smith.greet_1",
            "i18n_npc_crpg_core.smith.greet_2",
            "i18n_npc_crpg_core.smith.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_core.smith.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_core.smith.spar_lost",
        "entry_rules": [
            {"when": {"quest_ready": "quest_smith_temper"}, "node": "quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_dejavu_root"},
            {"when": {"met_count_gte": 2}, "node": "reunion_root"},
        ],
        "nodes": {
            "root": {
                "text_variants": [
                    {"when": {"known_flag": "smith_old_customer"}, "key": "i18n_npc_crpg_core.smith.reunion_text"},
                ],
                "text_key": "",
                "options": [
                    {"id": "smith_talk_craft", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.smith.opt_talk_craft", "next_node": "craft_talk"},
                    {"id": "smith_open_services", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.smith.opt_services", "next_node": "services"},
                    {"id": "smith_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_smith_temper"}, "text_key": "i18n_npc_crpg_core.smith.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "smith_scout_bow", "category": "quest", "once_per_run": True, "visible_if": {"all": [{"world_flag": "scout_needs_bow_part"}, {"service_available": "bow_part"}]}, "text_key": "i18n_npc_crpg_core.smith.opt_scout_bow", "cost": {"gold": 10}, "effects": [{"type": "consume_service", "service": "bow_part"}, {"type": "set_world_flag", "flag": "smith_forged_bow_part"}, {"type": "affinity", "delta": 2}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_bow_part"}], "next_node": "root"},
                    {"id": "smith_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_dejavu_root": {
                "text_key": "i18n_npc_crpg_core.smith.cycle_dejavu_text",
                "options": [
                    {"id": "smith_dejavu_calm", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.smith.opt_dejavu_calm", "effects": [{"type": "affinity", "delta": 1}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_dejavu_calm"}], "next_node": "root"},
                    {"id": "smith_dejavu_services", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.smith.opt_services", "next_node": "services"},
                    {"id": "smith_dejavu_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "reunion_root": {
                "text_key": "i18n_npc_crpg_core.smith.reunion_text",
                "options": [
                    {"id": "smith_reunion_services", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.smith.opt_services", "next_node": "services"},
                    {"id": "smith_reunion_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_smith_temper"}, "text_key": "i18n_npc_crpg_core.smith.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "smith_reunion_bow", "category": "quest", "once_per_run": True, "visible_if": {"all": [{"world_flag": "scout_needs_bow_part"}, {"service_available": "bow_part"}]}, "text_key": "i18n_npc_crpg_core.smith.opt_scout_bow", "cost": {"gold": 10}, "effects": [{"type": "consume_service", "service": "bow_part"}, {"type": "set_world_flag", "flag": "smith_forged_bow_part"}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_bow_part"}], "next_node": "reunion_root"},
                    {"id": "smith_reunion_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "return_root": {
                "text_key": "i18n_npc_crpg_core.smith.return_text",
                "options": [
                    {"id": "smith_ret_craft", "category": "topic", "once_per_encounter": True, "visible_if": {"not": {"local_flag": "smith_chatted"}}, "text_key": "i18n_npc_crpg_core.smith.opt_talk_craft", "next_node": "craft_talk"},
                    {"id": "smith_ret_services", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.smith.opt_services", "next_node": "services"},
                    {"id": "smith_ret_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_smith_temper"}, "text_key": "i18n_npc_crpg_core.smith.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "smith_ret_bow", "category": "quest", "once_per_run": True, "visible_if": {"all": [{"world_flag": "scout_needs_bow_part"}, {"service_available": "bow_part"}]}, "text_key": "i18n_npc_crpg_core.smith.opt_scout_bow", "cost": {"gold": 10}, "effects": [{"type": "consume_service", "service": "bow_part"}, {"type": "set_world_flag", "flag": "smith_forged_bow_part"}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_bow_part"}], "next_node": "return_root"},
                    {"id": "smith_ret_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "craft_talk": {
                "text_key": "i18n_npc_crpg_core.smith.craft_text",
                "options": [
                    {"id": "smith_praise", "category": "topic", "exclusive_group": "smith_stance", "text_key": "i18n_npc_crpg_core.smith.opt_praise", "effects": [{"type": "set_local_flag", "flag": "smith_chatted"}, {"type": "set_local_flag", "flag": "praised_craft"}, {"type": "affinity", "delta": 2}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_praise"}], "next_node": "services"},
                    {"id": "smith_warrior_spar_talk", "category": "topic", "exclusive_group": "smith_stance", "visible_if": {"player_class": "战士"}, "tag_key": "i18n_npc_crpg_core.tags.warrior", "text_key": "i18n_npc_crpg_core.smith.opt_warrior_talk", "effects": [{"type": "set_local_flag", "flag": "smith_chatted"}, {"type": "set_local_flag", "flag": "praised_craft"}, {"type": "affinity", "delta": 2}, {"type": "sp", "amount": 1, "key": "i18n_npc_crpg_core.smith.res_warrior_talk"}], "next_node": "services"},
                    {"id": "smith_mock", "category": "topic", "exclusive_group": "smith_stance", "text_key": "i18n_npc_crpg_core.smith.opt_mock", "effects": [{"type": "set_local_flag", "flag": "smith_chatted"}, {"type": "affinity", "delta": -2}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_mock"}], "next_node": "root"},
                ],
            },
            "services": {
                "text_variants": [
                    {"when": {"local_flag": "smith_discount"}, "key": "i18n_npc_crpg_core.smith.services_discount_text"},
                    {"when": {"local_flag": "smith_surcharge"}, "key": "i18n_npc_crpg_core.smith.services_surcharge_text"},
                ],
                "text_key": "i18n_npc_crpg_core.smith.services_text",
                "options": [
                    {"id": "smith_forge_disc", "category": "service", "visible_if": {"all": [{"service_available": "forge"}, {"local_flag": "smith_discount"}]}, "text_key": "i18n_npc_crpg_core.smith.opt_forge", "cost": {"gold": 15, "need_unupgraded_card": True}, "defer_cost": True, "defer_service": True, "service_key": "forge", "effects": [{"type": "start_upgrade", "cost": 15, "service": "forge", "return_node": "after_forge"}]},
                    {"id": "smith_forge_sur", "category": "service", "visible_if": {"all": [{"service_available": "forge"}, {"local_flag": "smith_surcharge"}]}, "text_key": "i18n_npc_crpg_core.smith.opt_forge", "cost": {"gold": 30, "need_unupgraded_card": True}, "defer_cost": True, "defer_service": True, "service_key": "forge", "effects": [{"type": "start_upgrade", "cost": 30, "service": "forge", "return_node": "after_forge"}]},
                    {"id": "smith_forge_std", "category": "service", "visible_if": {"all": [{"service_available": "forge"}, {"not": {"local_flag": "smith_discount"}}, {"not": {"local_flag": "smith_surcharge"}}]}, "text_key": "i18n_npc_crpg_core.smith.opt_forge", "cost": {"gold": 25, "need_unupgraded_card": True}, "defer_cost": True, "defer_service": True, "service_key": "forge", "effects": [{"type": "start_upgrade", "cost": 25, "service": "forge", "return_node": "after_forge"}]},
                    {"id": "smith_gem_disc", "category": "service", "visible_if": {"all": [{"service_available": "gem"}, {"local_flag": "smith_discount"}]}, "text_key": "i18n_npc_crpg_core.smith.opt_gem", "cost": {"gold": 25}, "defer_cost": True, "defer_service": True, "service_key": "gem", "effects": [{"type": "start_gem", "cost": 25, "service": "gem", "return_node": "after_forge"}]},
                    {"id": "smith_gem_std", "category": "service", "visible_if": {"all": [{"service_available": "gem"}, {"not": {"local_flag": "smith_discount"}}]}, "text_key": "i18n_npc_crpg_core.smith.opt_gem", "cost": {"gold": 35}, "defer_cost": True, "defer_service": True, "service_key": "gem", "effects": [{"type": "start_gem", "cost": 35, "service": "gem", "return_node": "after_forge"}]},
                    {"id": "smith_pickaxe", "category": "service", "visible_if": {"service_available": "pickaxe"}, "text_key": "i18n_npc_crpg_core.smith.opt_pickaxe", "cost": {"gold": 30}, "service_key": "pickaxe", "effects": [{"type": "give_item", "item_id": "rusty_pickaxe", "key": "i18n_npc_crpg_core.smith.res_pickaxe"}], "next_node": "services"},
                    {"id": "smith_bellows", "category": "service", "visible_if": {"service_available": "bellows"}, "text_key": "i18n_npc_crpg_core.smith.opt_bellows", "service_key": "bellows", "effects": [{"type": "sp", "amount": 2, "key": "i18n_npc_crpg_core.smith.res_bellows"}], "next_node": "services"},
                    {
                        "id": "smith_haggle",
                        "category": "topic",
                        "visible_if": {"all": [{"check_not_tried": "smith_haggle_check"}, {"not": {"local_flag": "smith_discount"}}, {"not": {"local_flag": "smith_surcharge"}}, {"any": [{"service_available": "forge"}, {"service_available": "gem"}]}]},
                        "text_key": "i18n_npc_crpg_core.smith.opt_haggle",
                        "check": {
                            "check_id": "smith_haggle_check",
                            "kind": "haggle",
                            "dc": 13,
                            "modifiers": [
                                {"cond": {"local_flag": "praised_craft"}, "bonus": 3, "reason_key": "i18n_npc_crpg_core.smith.mod_craft"},
                                {"cond": {"player_class": "战士"}, "bonus": 2, "reason_key": "i18n_npc_crpg_core.smith.mod_warrior"},
                                {"cond": {"has_item": "rusty_pickaxe"}, "bonus": 2, "reason_key": "i18n_npc_crpg_core.smith.mod_pickaxe"},
                            ],
                            "auto_pass_cond": {"affinity_gte": 6},
                            "auto_pass_reason_key": "i18n_npc_crpg_core.smith.auto_trusted",
                            "on_success": {"next_node": "services", "effects": [{"type": "set_local_flag", "flag": "smith_discount"}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_haggle_ok"}]},
                            "on_fail": {"next_node": "services", "effects": [{"type": "set_local_flag", "flag": "smith_surcharge"}, {"type": "affinity", "delta": -1}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_haggle_fail"}]},
                        },
                    },
                    {"id": "smith_services_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "return_root"},
                ],
            },
            "after_forge": {
                "text_key": "i18n_npc_crpg_core.smith.after_forge_text",
                "options": [
                    {"id": "smith_after_more", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.smith.opt_more_services", "next_node": "services"},
                    {"id": "smith_after_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "quest_offer": {
                "text_key": "i18n_npc_crpg_core.smith.quest_offer_text",
                "options": [
                    {"id": "smith_accept_quest", "category": "quest", "text_key": "i18n_npc_crpg_core.smith.opt_accept_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_smith_temper"}], "next_node": "return_root"},
                    {"id": "smith_decline_quest", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.common.opt_decline_quest", "next_node": "return_root"},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_core.smith.quest_turnin_text",
                "options": [
                    {"id": "smith_turnin_ok", "category": "quest", "text_key": "i18n_npc_crpg_core.smith.opt_turnin", "effects": [{"type": "complete_quest", "quest_id": "quest_smith_temper"}, {"type": "affinity", "delta": 3}, {"type": "set_known_flag", "flag": "smith_old_customer"}], "next_node": "return_root"},
                ],
            },
            "hostile_root": {
                "text_key": "i18n_npc_crpg_core.smith.hostile_text",
                "options": [
                    {"id": "smith_apologize", "category": "topic", "visible_if": {"check_not_tried": "smith_apology"}, "text_key": "i18n_npc_crpg_core.common.opt_apologize", "check": {"check_id": "smith_apology", "kind": "persuade", "dc": 12, "on_success": {"next_node": "return_root", "effects": [{"type": "affinity", "delta": 4}, {"type": "message", "key": "i18n_npc_crpg_core.smith.res_apology_ok"}]}, "on_fail": {"next_node": "hostile_root", "effects": [{"type": "message", "key": "i18n_npc_crpg_core.smith.res_apology_fail"}]}}},
                    {"id": "smith_hostile_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {
                "text_key": "i18n_npc_crpg_core.smith.exhausted_text",
                "options": [],
            },
        },
    },
    "smuggler_broker": {
        "initial_affinity": 0,
        "cross_run_memory": False,
        "cycle_aware": False,
        "service_quotas": {"gamble": 1, "intel": 1, "black_market": 1, "token_gift": 1},
        "greetings": [
            "i18n_npc_crpg_core.broker.greet_1",
            "i18n_npc_crpg_core.broker.greet_2",
            "i18n_npc_crpg_core.broker.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_core.broker.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_core.broker.spar_lost",
        "entry_rules": [
            {"when": {"quest_ready": "quest_broker_ledger"}, "node": "quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_dejavu_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "broker_probe", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.broker.opt_probe", "next_node": "rumor_talk"},
                    {"id": "broker_biz", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.broker.opt_business", "next_node": "business"},
                    {"id": "broker_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_broker_ledger"}, "text_key": "i18n_npc_crpg_core.broker.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "broker_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_dejavu_root": {
                "text_key": "i18n_npc_crpg_core.broker.cycle_dejavu_text",
                "options": [
                    {"id": "broker_dejavu_biz", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.broker.opt_business", "next_node": "business"},
                    {"id": "broker_dejavu_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "return_root": {
                "text_key": "i18n_npc_crpg_core.broker.return_text",
                "options": [
                    {"id": "broker_ret_probe", "category": "topic", "once_per_encounter": True, "visible_if": {"not": {"local_flag": "broker_probed"}}, "text_key": "i18n_npc_crpg_core.broker.opt_probe", "next_node": "rumor_talk"},
                    {"id": "broker_ret_biz", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.broker.opt_business", "next_node": "business"},
                    {"id": "broker_ret_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_broker_ledger"}, "text_key": "i18n_npc_crpg_core.broker.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "broker_ret_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "rumor_talk": {
                "text_key": "i18n_npc_crpg_core.broker.rumor_text",
                "options": [
                    {"id": "broker_show_token", "category": "topic", "once_per_encounter": True, "visible_if": {"all": [{"has_item": "smuggler_token"}, {"service_available": "token_gift"}]}, "service_key": "token_gift", "text_key": "i18n_npc_crpg_core.broker.opt_show_token", "effects": [{"type": "set_local_flag", "flag": "broker_probed"}, {"type": "affinity", "delta": 3}, {"type": "reveal_rooms", "count": 1, "recap_id": "broker_token_intel", "key": "i18n_npc_crpg_core.broker.res_show_token", "empty_key": "i18n_npc_crpg_core.broker.res_intel_empty"}], "next_node": "business"},
                    {"id": "broker_flash_gold", "category": "topic", "exclusive_group": "broker_probe_stance", "visible_if": {"gold_gte": 60}, "text_key": "i18n_npc_crpg_core.broker.opt_flash_gold", "effects": [{"type": "set_local_flag", "flag": "broker_probed"}, {"type": "set_local_flag", "flag": "broker_vip"}, {"type": "affinity", "delta": 2}, {"type": "message", "key": "i18n_npc_crpg_core.broker.res_flash_gold"}], "next_node": "business"},
                    {
                        "id": "broker_inspect_dice",
                        "category": "topic",
                        "exclusive_group": "broker_probe_stance",
                        "visible_if": {"check_not_tried": "broker_dice_insight"},
                        "text_key": "i18n_npc_crpg_core.broker.opt_inspect_dice",
                        "check": {
                            "check_id": "broker_dice_insight",
                            "kind": "insight",
                            "dc": 12,
                            "modifiers": [
                                {"cond": {"has_item": "smuggler_token"}, "bonus": 2, "reason_key": "i18n_npc_crpg_core.broker.mod_token"},
                            ],
                            "on_success": {"next_node": "business", "effects": [{"type": "set_local_flag", "flag": "broker_probed"}, {"type": "set_local_flag", "flag": "dice_exposed"}, {"type": "gold", "amount": 10}, {"type": "message", "key": "i18n_npc_crpg_core.broker.res_dice_ok"}]},
                            "on_fail": {"next_node": "business", "effects": [{"type": "set_local_flag", "flag": "broker_probed"}, {"type": "set_local_flag", "flag": "gamble_surcharge"}, {"type": "affinity", "delta": -1}, {"type": "message", "key": "i18n_npc_crpg_core.broker.res_dice_fail"}]},
                        },
                    },
                    {"id": "broker_rumor_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "return_root"},
                ],
            },
            "business": {
                "text_key": "i18n_npc_crpg_core.broker.business_text",
                "options": [
                    {"id": "broker_gamble_std", "category": "service", "visible_if": {"all": [{"service_available": "gamble"}, {"not": {"local_flag": "gamble_surcharge"}}]}, "text_key": "i18n_npc_crpg_core.broker.opt_gamble", "cost": {"gold": 20}, "service_key": "gamble", "effects": [{"type": "gamble", "cost": 20, "win_chance": 0.55, "rigged_exposed_flag": "dice_exposed", "exposed_chance": 0.80, "win_item": "smuggler_token", "lose_item": "sugar_cube_pack", "win_key": "i18n_room_interact.dialog.broker_gamble_win", "lose_key": "i18n_room_interact.dialog.broker_gamble_lose"}], "next_node": "business"},
                    {"id": "broker_gamble_sur", "category": "service", "visible_if": {"all": [{"service_available": "gamble"}, {"local_flag": "gamble_surcharge"}]}, "text_key": "i18n_npc_crpg_core.broker.opt_gamble", "cost": {"gold": 25}, "service_key": "gamble", "effects": [{"type": "gamble", "cost": 25, "win_chance": 0.55, "win_item": "smuggler_token", "lose_item": "sugar_cube_pack", "win_key": "i18n_room_interact.dialog.broker_gamble_win", "lose_key": "i18n_room_interact.dialog.broker_gamble_lose"}], "next_node": "business"},
                    {"id": "broker_intel", "category": "service", "visible_if": {"service_available": "intel"}, "text_key": "i18n_npc_crpg_core.broker.opt_intel", "cost": {"gold": 18}, "service_key": "intel", "effects": [{"type": "reveal_rooms", "count": 2, "recap_id": "broker_intel_coords", "key": "i18n_room_interact.dialog.broker_intel_ok", "empty_key": "i18n_npc_crpg_core.broker.res_intel_empty"}], "next_node": "business"},
                    {"id": "broker_buy_potion", "category": "service", "visible_if": {"service_available": "black_market"}, "text_key": "i18n_npc_crpg_core.broker.opt_buy_potion", "cost": {"gold": 28}, "service_key": "black_market", "effects": [{"type": "give_item", "random_potion": True, "key": "i18n_npc_crpg_core.broker.res_buy_item"}], "next_node": "business"},
                    {"id": "broker_buy_key", "category": "service", "visible_if": {"service_available": "black_market"}, "text_key": "i18n_npc_crpg_core.broker.opt_buy_key", "cost": {"gold": 30}, "service_key": "black_market", "effects": [{"type": "give_item", "item_id": "skeleton_key", "key": "i18n_npc_crpg_core.broker.res_buy_item"}], "next_node": "business"},
                    {"id": "broker_biz_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "return_root"},
                ],
            },
            "quest_offer": {
                "text_key": "i18n_npc_crpg_core.broker.quest_offer_text",
                "options": [
                    {"id": "broker_accept_q", "category": "quest", "text_key": "i18n_npc_crpg_core.broker.opt_accept_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_broker_ledger"}], "next_node": "return_root"},
                    {"id": "broker_decline_q", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.common.opt_decline_quest", "next_node": "return_root"},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_core.broker.quest_turnin_text",
                "options": [
                    {"id": "broker_turnin_honest", "category": "quest", "text_key": "i18n_npc_crpg_core.broker.opt_turnin_honest", "effects": [{"type": "complete_quest", "quest_id": "quest_broker_ledger"}, {"type": "affinity", "delta": 3}], "next_node": "return_root"},
                    {
                        "id": "broker_turnin_press",
                        "category": "quest",
                        "visible_if": {"check_not_tried": "broker_split_check"},
                        "text_key": "i18n_npc_crpg_core.broker.opt_turnin_press",
                        "check": {
                            "check_id": "broker_split_check",
                            "kind": "persuade",
                            "dc": 14,
                            "modifiers": [{"cond": {"local_flag": "dice_exposed"}, "bonus": 3, "reason_key": "i18n_npc_crpg_core.broker.mod_dice"}],
                            "on_success": {"next_node": "return_root", "effects": [{"type": "complete_quest", "quest_id": "quest_broker_ledger"}, {"type": "gold", "amount": 30}, {"type": "reveal_rooms", "count": 1, "key": "i18n_npc_crpg_core.broker.res_split_ok"}]},
                            "on_fail": {"next_node": "return_root", "effects": [{"type": "complete_quest", "quest_id": "quest_broker_ledger"}, {"type": "gold", "amount": -10}, {"type": "affinity", "delta": -2}, {"type": "message", "key": "i18n_npc_crpg_core.broker.res_split_fail"}]},
                        },
                    },
                ],
            },
            "hostile_root": {
                "text_key": "i18n_npc_crpg_core.broker.hostile_text",
                "options": [
                    {"id": "broker_apology", "category": "topic", "visible_if": {"check_not_tried": "broker_apology"}, "text_key": "i18n_npc_crpg_core.common.opt_apologize", "check": {"check_id": "broker_apology", "kind": "persuade", "dc": 12, "on_success": {"next_node": "return_root", "effects": [{"type": "affinity", "delta": 4}, {"type": "message", "key": "i18n_npc_crpg_core.broker.res_apology_ok"}]}, "on_fail": {"next_node": "hostile_root", "effects": [{"type": "message", "key": "i18n_npc_crpg_core.broker.res_apology_fail"}]}}},
                    {"id": "broker_hostile_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_core.broker.exhausted_text", "options": []},
        },
    },
    "lost_scholar": {
        "initial_affinity": 0,
        "cross_run_memory": False,
        "cycle_aware": False,
        "service_quotas": {"study_spell": 1, "notes_exchange": 1, "ritual_clue": 1},
        "greetings": [
            "i18n_npc_crpg_core.scholar.greet_1",
            "i18n_npc_crpg_core.scholar.greet_2",
            "i18n_npc_crpg_core.scholar.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_core.scholar.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_core.scholar.spar_lost",
        "entry_rules": [
            {"when": {"quest_ready": "quest_scholar_rubbing"}, "node": "quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_dejavu_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "scholar_discuss", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.scholar.opt_discuss", "next_node": "inscription_talk"},
                    {"id": "scholar_desk", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.scholar.opt_desk", "next_node": "research_desk"},
                    {"id": "scholar_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_scholar_rubbing"}, "text_key": "i18n_npc_crpg_core.scholar.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "scholar_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_dejavu_root": {
                "text_key": "i18n_npc_crpg_core.scholar.cycle_dejavu_text",
                "options": [
                    {"id": "scholar_dejavu_ask", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.scholar.opt_dejavu_ask", "effects": [{"type": "message", "key": "i18n_npc_crpg_core.scholar.res_dejavu_ask"}], "next_node": "root"},
                    {"id": "scholar_dejavu_desk", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.scholar.opt_desk", "next_node": "research_desk"},
                    {"id": "scholar_dejavu_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "return_root": {
                "text_key": "i18n_npc_crpg_core.scholar.return_text",
                "options": [
                    {"id": "scholar_ret_discuss", "category": "topic", "once_per_encounter": True, "visible_if": {"not": {"local_flag": "scholar_chatted"}}, "text_key": "i18n_npc_crpg_core.scholar.opt_discuss", "next_node": "inscription_talk"},
                    {"id": "scholar_ret_desk", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.scholar.opt_desk", "next_node": "research_desk"},
                    {"id": "scholar_ret_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_scholar_rubbing"}, "text_key": "i18n_npc_crpg_core.scholar.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "scholar_ret_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "inscription_talk": {
                "text_key": "i18n_npc_crpg_core.scholar.inscription_text",
                "options": [
                    {"id": "scholar_punctuate", "category": "topic", "exclusive_group": "scholar_stance", "text_key": "i18n_npc_crpg_core.scholar.opt_punctuate", "effects": [{"type": "set_local_flag", "flag": "scholar_chatted"}, {"type": "set_local_flag", "flag": "scholar_low_cost"}, {"type": "affinity", "delta": 2}, {"type": "message", "key": "i18n_npc_crpg_core.scholar.res_punctuate"}], "next_node": "research_desk"},
                    {"id": "scholar_wizard_hint", "category": "topic", "exclusive_group": "scholar_stance", "visible_if": {"player_class": "法师"}, "tag_key": "i18n_npc_crpg_core.tags.wizard", "text_key": "i18n_npc_crpg_core.scholar.opt_wizard_hint", "effects": [{"type": "set_local_flag", "flag": "scholar_chatted"}, {"type": "set_local_flag", "flag": "scholar_low_cost"}, {"type": "affinity", "delta": 3}, {"type": "add_buff", "buff_id": "arcane_clarity", "stacks": 1, "key": "i18n_npc_crpg_core.scholar.res_wizard_hint"}], "next_node": "research_desk"},
                    {"id": "scholar_safety", "category": "topic", "exclusive_group": "scholar_stance", "text_key": "i18n_npc_crpg_core.scholar.opt_safety", "effects": [{"type": "set_local_flag", "flag": "scholar_chatted"}, {"type": "affinity", "delta": 1}, {"type": "message", "key": "i18n_npc_crpg_core.scholar.res_safety"}], "next_node": "research_desk"},
                ],
            },
            "research_desk": {
                "text_key": "i18n_npc_crpg_core.scholar.desk_text",
                "options": [
                    {"id": "scholar_study_low", "category": "service", "visible_if": {"all": [{"service_available": "study_spell"}, {"local_flag": "scholar_low_cost"}]}, "text_key": "i18n_npc_crpg_core.scholar.opt_study", "cost": {"hp": 2}, "service_key": "study_spell", "effects": [{"type": "add_card", "pool": "npc_scholar", "fallback": "fireball", "key": "i18n_room_interact.dialog.scholar_study_ok"}], "next_node": "research_desk"},
                    {"id": "scholar_study_std", "category": "service", "visible_if": {"all": [{"service_available": "study_spell"}, {"not": {"local_flag": "scholar_low_cost"}}]}, "text_key": "i18n_npc_crpg_core.scholar.opt_study", "cost": {"hp": 4}, "service_key": "study_spell", "effects": [{"type": "add_card", "pool": "npc_scholar", "fallback": "fireball", "key": "i18n_room_interact.dialog.scholar_study_ok"}], "next_node": "research_desk"},
                    {"id": "scholar_tidy_notes", "category": "service", "visible_if": {"service_available": "notes_exchange"}, "text_key": "i18n_npc_crpg_core.scholar.opt_tidy_notes", "service_key": "notes_exchange", "effects": [{"type": "give_item", "item_id": "ancient_notes", "key": "i18n_npc_crpg_core.scholar.res_tidy_notes"}], "next_node": "research_desk"},
                    {"id": "scholar_ritual_ask", "category": "service", "visible_if": {"service_available": "ritual_clue"}, "text_key": "i18n_npc_crpg_core.scholar.opt_ritual", "service_key": "ritual_clue", "effects": [{"type": "reveal_ritual", "recap_id": "scholar_ritual", "key": "i18n_room_interact.dialog.scholar_lore_clue", "empty_key": "i18n_room_interact.dialog.scholar_lore_none"}], "next_node": "research_desk"},
                    {
                        "id": "scholar_insight_margin",
                        "category": "topic",
                        "visible_if": {"check_not_tried": "scholar_margin_check"},
                        "text_key": "i18n_npc_crpg_core.scholar.opt_insight_margin",
                        "check": {
                            "check_id": "scholar_margin_check",
                            "kind": "insight",
                            "dc": 11,
                            "modifiers": [{"cond": {"player_class": "法师"}, "bonus": 2, "reason_key": "i18n_npc_crpg_core.scholar.mod_wizard"}],
                            "on_success": {"next_node": "research_desk", "effects": [{"type": "sp", "amount": 2}, {"type": "reveal_ritual", "recap_id": "scholar_ritual", "key": "i18n_npc_crpg_core.scholar.res_margin_ok", "empty_key": "i18n_npc_crpg_core.scholar.res_margin_sp"}]},
                            "on_fail": {"next_node": "research_desk", "effects": [{"type": "message", "key": "i18n_npc_crpg_core.scholar.res_margin_fail"}]},
                        },
                    },
                    {"id": "scholar_desk_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "return_root"},
                ],
            },
            "quest_offer": {
                "text_key": "i18n_npc_crpg_core.scholar.quest_offer_text",
                "options": [
                    {"id": "scholar_accept_q", "category": "quest", "text_key": "i18n_npc_crpg_core.scholar.opt_accept_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_scholar_rubbing"}], "next_node": "return_root"},
                    {"id": "scholar_decline_q", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.common.opt_decline_quest", "next_node": "return_root"},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_core.scholar.quest_turnin_text",
                "options": [
                    {"id": "scholar_turnin_spell", "category": "quest", "text_key": "i18n_npc_crpg_core.scholar.opt_turnin_spell", "effects": [{"type": "complete_quest", "quest_id": "quest_scholar_rubbing"}, {"type": "affinity", "delta": 3}], "next_node": "return_root"},
                    {"id": "scholar_turnin_map", "category": "quest", "text_key": "i18n_npc_crpg_core.scholar.opt_turnin_map", "effects": [{"type": "complete_quest", "quest_id": "quest_scholar_rubbing"}, {"type": "reveal_rooms", "count": 2, "key": "i18n_npc_crpg_core.scholar.res_turnin_map"}, {"type": "affinity", "delta": 3}], "next_node": "return_root"},
                ],
            },
            "hostile_root": {
                "text_key": "i18n_npc_crpg_core.scholar.hostile_text",
                "options": [
                    {"id": "scholar_apology", "category": "topic", "visible_if": {"check_not_tried": "scholar_apology"}, "text_key": "i18n_npc_crpg_core.common.opt_apologize", "check": {"check_id": "scholar_apology", "kind": "persuade", "dc": 11, "on_success": {"next_node": "return_root", "effects": [{"type": "affinity", "delta": 4}, {"type": "message", "key": "i18n_npc_crpg_core.scholar.res_apology_ok"}]}, "on_fail": {"next_node": "hostile_root", "effects": [{"type": "message", "key": "i18n_npc_crpg_core.scholar.res_apology_fail"}]}}},
                    {"id": "scholar_hostile_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_core.scholar.exhausted_text", "options": []},
        },
    },
    "wounded_scout": {
        "initial_affinity": -1,
        "cross_run_memory": False,
        "cycle_aware": False,
        "service_quotas": {"field_aid": 1, "share_ration": 1},
        "greetings": [
            "i18n_npc_crpg_core.scout.greet_1",
            "i18n_npc_crpg_core.scout.greet_2",
            "i18n_npc_crpg_core.scout.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_core.scout.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_core.scout.spar_lost",
        "entry_rules": [
            {"when": {"quest_ready": "quest_scout_echo"}, "node": "quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_dejavu_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "scout_calm", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.scout.opt_calm", "next_node": "approach_talk"},
                    {"id": "scout_deliver_bow", "category": "quest", "once_per_run": True, "visible_if": {"world_flag": "smith_forged_bow_part"}, "text_key": "i18n_npc_crpg_core.scout.opt_deliver_bow", "effects": [{"type": "affinity", "delta": 3}, {"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1}, {"type": "gold", "amount": 20}, {"type": "message", "key": "i18n_npc_crpg_core.scout.res_deliver_bow"}], "next_node": "return_root"},
                    {"id": "scout_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_scout_echo"}, "text_key": "i18n_npc_crpg_core.scout.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "scout_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_dejavu_root": {
                "text_key": "i18n_npc_crpg_core.scout.cycle_dejavu_text",
                "options": [
                    {"id": "scout_dejavu_calm", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.scout.opt_calm", "next_node": "approach_talk"},
                    {"id": "scout_dejavu_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "return_root": {
                "text_key": "i18n_npc_crpg_core.scout.return_text",
                "options": [
                    {"id": "scout_ret_approach", "category": "topic", "once_per_encounter": True, "visible_if": {"not": {"local_flag": "scout_helped"}}, "text_key": "i18n_npc_crpg_core.scout.opt_calm", "next_node": "approach_talk"},
                    {"id": "scout_ret_bow", "category": "quest", "once_per_run": True, "visible_if": {"world_flag": "smith_forged_bow_part"}, "text_key": "i18n_npc_crpg_core.scout.opt_deliver_bow", "effects": [{"type": "affinity", "delta": 3}, {"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1}, {"type": "gold", "amount": 20}, {"type": "message", "key": "i18n_npc_crpg_core.scout.res_deliver_bow"}], "next_node": "return_root"},
                    {"id": "scout_ret_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_scout_echo"}, "text_key": "i18n_npc_crpg_core.scout.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "scout_ret_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "approach_talk": {
                "text_key": "i18n_npc_crpg_core.scout.approach_text",
                "options": [
                    {"id": "scout_give_bandage", "category": "service", "exclusive_group": "scout_aid_group", "visible_if": {"all": [{"has_item": "field_bandage"}, {"service_available": "field_aid"}]}, "cost": {"item": "field_bandage"}, "service_key": "field_aid", "text_key": "i18n_npc_crpg_core.scout.opt_give_bandage", "effects": [{"type": "set_local_flag", "flag": "scout_helped"}, {"type": "set_world_flag", "flag": "scout_needs_bow_part"}, {"type": "affinity", "delta": 4}, {"type": "give_item", "item_id": "glowing_runestone"}, {"type": "reveal_rooms", "count": 2, "recap_id": "scout_route", "key": "i18n_npc_crpg_core.scout.res_bandage", "empty_key": "i18n_npc_crpg_core.scout.res_bandage_no_map"}], "next_node": "return_root"},
                    {"id": "scout_aid_gold", "category": "service", "exclusive_group": "scout_aid_group", "visible_if": {"service_available": "field_aid"}, "cost": {"gold": 25}, "service_key": "field_aid", "text_key": "i18n_npc_crpg_core.scout.opt_aid_gold", "effects": [{"type": "set_local_flag", "flag": "scout_helped"}, {"type": "set_world_flag", "flag": "scout_needs_bow_part"}, {"type": "affinity", "delta": 3}, {"type": "give_item", "item_id": "glowing_runestone"}, {"type": "reveal_rooms", "count": 2, "recap_id": "scout_route", "key": "i18n_room_interact.dialog.scout_aid_ok"}], "next_node": "return_root"},
                    {"id": "scout_share_water", "category": "service", "exclusive_group": "scout_aid_group", "visible_if": {"service_available": "share_ration"}, "service_key": "share_ration", "text_key": "i18n_npc_crpg_core.scout.opt_share_water", "effects": [{"type": "set_local_flag", "flag": "scout_helped"}, {"type": "set_world_flag", "flag": "scout_needs_bow_part"}, {"type": "affinity", "delta": 2}, {"type": "sp", "amount": 2}, {"type": "give_item", "item_id": "sugar_cube_pack", "key": "i18n_room_interact.dialog.scout_supply_ok"}], "next_node": "return_root"},
                    {
                        "id": "scout_intimidate",
                        "category": "challenge",
                        "exclusive_group": "scout_aid_group",
                        "visible_if": {"check_not_tried": "scout_intimidate_check"},
                        "text_key": "i18n_npc_crpg_core.scout.opt_intimidate",
                        "check": {
                            "check_id": "scout_intimidate_check",
                            "kind": "intimidate",
                            "dc": 13,
                            "modifiers": [{"cond": {"player_class": "战士"}, "bonus": 2, "reason_key": "i18n_npc_crpg_core.scout.mod_warrior"}],
                            "on_success": {"next_node": "return_root", "effects": [{"type": "set_local_flag", "flag": "scout_helped"}, {"type": "affinity", "delta": -4}, {"type": "gold", "amount": 25}, {"type": "message", "key": "i18n_npc_crpg_core.scout.res_intimidate_ok"}]},
                            "on_fail": {"effects": [{"type": "affinity", "delta": -4}, {"type": "start_combat", "non_lethal": True, "intro_key": "i18n_npc_crpg_core.scout.res_intimidate_fail"}]},
                        },
                    },
                ],
            },
            "quest_offer": {
                "text_key": "i18n_npc_crpg_core.scout.quest_offer_text",
                "options": [
                    {"id": "scout_accept_q", "category": "quest", "text_key": "i18n_npc_crpg_core.scout.opt_accept_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_scout_echo"}], "next_node": "return_root"},
                    {"id": "scout_decline_q", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.common.opt_decline_quest", "next_node": "return_root"},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_core.scout.quest_turnin_text",
                "options": [
                    {"id": "scout_turnin_ok", "category": "quest", "text_key": "i18n_npc_crpg_core.scout.opt_turnin", "effects": [{"type": "complete_quest", "quest_id": "quest_scout_echo"}, {"type": "affinity", "delta": 3}], "next_node": "return_root"},
                ],
            },
            "hostile_root": {
                "text_key": "i18n_npc_crpg_core.scout.hostile_text",
                "options": [
                    {"id": "scout_hostile_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_core.scout.exhausted_text", "options": []},
        },
    },
    "shrine_keeper": {
        "initial_affinity": 0,
        "cross_run_memory": False,
        "cycle_aware": True,
        "service_quotas": {"blood_blessing": 1, "relic_tribute": 1, "omen_reveal": 1},
        "greetings": [
            "i18n_npc_crpg_core.keeper.greet_1",
            "i18n_npc_crpg_core.keeper.greet_2",
            "i18n_npc_crpg_core.keeper.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_core.keeper.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_core.keeper.spar_lost",
        "spar_execute_key": "i18n_npc_crpg_core.keeper.spar_execute",
        "entry_rules": [
            {"when": {"quest_ready": "quest_keeper_vigil"}, "node": "quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_truth_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "keeper_oath", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.keeper.opt_oath", "next_node": "oath_talk"},
                    {"id": "keeper_ritual_menu", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.keeper.opt_ritual_menu", "next_node": "ritual_menu"},
                    {"id": "keeper_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_keeper_vigil"}, "text_key": "i18n_npc_crpg_core.keeper.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "keeper_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_truth_root": {
                "text_key": "i18n_npc_crpg_core.keeper.cycle_truth_text",
                "options": [
                    {"id": "keeper_ask_cycle", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.keeper.opt_ask_cycle", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "meta_keeper_cycle", "unique_token": "meta_keeper_cycle"}}, {"type": "message", "key": "i18n_npc_crpg_core.keeper.res_ask_cycle"}], "next_node": "root"},
                    {"id": "keeper_cycle_ritual", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.keeper.opt_ritual_menu", "next_node": "ritual_menu"},
                    {"id": "keeper_cycle_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "return_root": {
                "text_key": "i18n_npc_crpg_core.keeper.return_text",
                "options": [
                    {"id": "keeper_ret_oath", "category": "topic", "once_per_encounter": True, "visible_if": {"not": {"local_flag": "keeper_chatted"}}, "text_key": "i18n_npc_crpg_core.keeper.opt_oath", "next_node": "oath_talk"},
                    {"id": "keeper_ret_ritual", "category": "service", "submenu_only": True, "text_key": "i18n_npc_crpg_core.keeper.opt_ritual_menu", "next_node": "ritual_menu"},
                    {"id": "keeper_ret_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_keeper_vigil"}, "text_key": "i18n_npc_crpg_core.keeper.opt_quest_ask", "next_node": "quest_offer"},
                    {"id": "keeper_ret_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "oath_talk": {
                "text_key": "i18n_npc_crpg_core.keeper.oath_text",
                "options": [
                    {"id": "keeper_revere", "category": "topic", "exclusive_group": "keeper_stance", "text_key": "i18n_npc_crpg_core.keeper.opt_revere", "effects": [{"type": "set_local_flag", "flag": "keeper_chatted"}, {"type": "affinity", "delta": 2}, {"type": "consume_service", "service": "omen_reveal"}, {"type": "reveal_boss", "recap_id": "keeper_boss", "key": "i18n_room_interact.dialog.keeper_boss_reveal"}], "next_node": "ritual_menu"},
                    {"id": "keeper_question", "category": "topic", "exclusive_group": "keeper_stance", "text_key": "i18n_npc_crpg_core.keeper.opt_question", "effects": [{"type": "set_local_flag", "flag": "keeper_chatted"}], "next_node": "oath_debate"},
                ],
            },
            "oath_debate": {
                "text_key": "i18n_npc_crpg_core.keeper.debate_text",
                "options": [
                    {
                        "id": "keeper_persuade_ember",
                        "category": "topic",
                        "visible_if": {"check_not_tried": "keeper_ember_check"},
                        "text_key": "i18n_npc_crpg_core.keeper.opt_persuade_ember",
                        "check": {
                            "check_id": "keeper_ember_check",
                            "kind": "persuade",
                            "dc": 14,
                            "modifiers": [{"cond": {"known_flag": "keeper_sworn"}, "bonus": 3, "reason_key": "i18n_npc_crpg_core.keeper.mod_sworn"}],
                            "auto_pass_cond": {"affinity_gte": 6},
                            "auto_pass_reason_key": "i18n_npc_crpg_core.keeper.auto_sworn",
                            "on_success": {"next_node": "ritual_menu", "effects": [{"type": "set_local_flag", "flag": "keeper_free_ritual"}, {"type": "affinity", "delta": 3}, {"type": "message", "key": "i18n_npc_crpg_core.keeper.res_debate_ok"}]},
                            "on_fail": {"next_node": "ritual_menu", "effects": [{"type": "affinity", "delta": -2}, {"type": "message", "key": "i18n_npc_crpg_core.keeper.res_debate_fail"}]},
                        },
                    },
                    {"id": "keeper_respect_silence", "category": "topic", "text_key": "i18n_npc_crpg_core.keeper.opt_respect", "effects": [{"type": "affinity", "delta": 1}, {"type": "message", "key": "i18n_npc_crpg_core.keeper.res_respect"}], "next_node": "ritual_menu"},
                ],
            },
            "ritual_menu": {
                "text_key": "i18n_npc_crpg_core.keeper.ritual_text",
                "options": [
                    {"id": "keeper_bless_free", "category": "service", "visible_if": {"all": [{"service_available": "blood_blessing"}, {"local_flag": "keeper_free_ritual"}]}, "service_key": "blood_blessing", "text_key": "i18n_npc_crpg_core.keeper.opt_bless", "effects": [{"type": "sp", "amount": 5}, {"type": "exhaustion", "amount": -1, "key": "i18n_room_interact.dialog.keeper_bless_ok"}], "next_node": "ritual_menu"},
                    {"id": "keeper_bless_std", "category": "service", "visible_if": {"all": [{"service_available": "blood_blessing"}, {"not": {"local_flag": "keeper_free_ritual"}}]}, "cost": {"hp": 6}, "service_key": "blood_blessing", "text_key": "i18n_npc_crpg_core.keeper.opt_bless", "effects": [{"type": "sp", "amount": 5}, {"type": "exhaustion", "amount": -1, "key": "i18n_room_interact.dialog.keeper_bless_ok"}], "next_node": "ritual_menu"},
                    {"id": "keeper_relic_disc", "category": "service", "visible_if": {"all": [{"service_available": "relic_tribute"}, {"local_flag": "keeper_free_ritual"}]}, "cost": {"gold": 20}, "service_key": "relic_tribute", "text_key": "i18n_npc_crpg_core.keeper.opt_relic", "effects": [{"type": "grant_relic", "key": "i18n_explore_core.relic_gained", "fallback_item": "glowing_runestone", "fallback_key": "i18n_npc_crpg_core.keeper.res_relic_fallback"}], "next_node": "ritual_menu"},
                    {"id": "keeper_relic_std", "category": "service", "visible_if": {"all": [{"service_available": "relic_tribute"}, {"not": {"local_flag": "keeper_free_ritual"}}]}, "cost": {"gold": 35}, "service_key": "relic_tribute", "text_key": "i18n_npc_crpg_core.keeper.opt_relic", "effects": [{"type": "grant_relic", "key": "i18n_explore_core.relic_gained", "fallback_item": "glowing_runestone", "fallback_key": "i18n_npc_crpg_core.keeper.res_relic_fallback"}], "next_node": "ritual_menu"},
                    {"id": "keeper_omen", "category": "service", "visible_if": {"service_available": "omen_reveal"}, "service_key": "omen_reveal", "text_key": "i18n_npc_crpg_core.keeper.opt_omen", "effects": [{"type": "reveal_boss", "recap_id": "keeper_boss", "key": "i18n_room_interact.dialog.keeper_boss_reveal"}], "next_node": "ritual_menu"},
                    {"id": "keeper_ritual_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "return_root"},
                ],
            },
            "quest_offer": {
                "text_key": "i18n_npc_crpg_core.keeper.quest_offer_text",
                "options": [
                    {"id": "keeper_accept_q", "category": "quest", "text_key": "i18n_npc_crpg_core.keeper.opt_accept_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_keeper_vigil"}], "next_node": "return_root"},
                    {"id": "keeper_decline_q", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_core.common.opt_decline_quest", "next_node": "return_root"},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_core.keeper.quest_turnin_text",
                "options": [
                    {"id": "keeper_turnin_ok", "category": "quest", "text_key": "i18n_npc_crpg_core.keeper.opt_turnin", "effects": [{"type": "complete_quest", "quest_id": "quest_keeper_vigil"}, {"type": "set_known_flag", "flag": "keeper_sworn"}, {"type": "affinity", "delta": 4}], "next_node": "return_root"},
                ],
            },
            "hostile_root": {
                "text_key": "i18n_npc_crpg_core.keeper.hostile_text",
                "options": [
                    {"id": "keeper_apology", "category": "topic", "visible_if": {"check_not_tried": "keeper_apology"}, "text_key": "i18n_npc_crpg_core.common.opt_apologize", "check": {"check_id": "keeper_apology", "kind": "persuade", "dc": 13, "on_success": {"next_node": "return_root", "effects": [{"type": "affinity", "delta": 4}, {"type": "message", "key": "i18n_npc_crpg_core.keeper.res_apology_ok"}]}, "on_fail": {"next_node": "hostile_root", "effects": [{"type": "message", "key": "i18n_npc_crpg_core.keeper.res_apology_fail"}]}}},
                    {"id": "keeper_hostile_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_core.keeper.exhausted_text", "options": []},
        },
    },
}
