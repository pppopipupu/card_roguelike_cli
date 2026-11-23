MADOKA_NANOHA_NPC_GRAPHS = {
    "kyubey": {
        "initial_affinity": 0,
        "cross_run_memory": True,
        "cycle_aware": True,
        "service_quotas": {"contract": 1, "grief_seed": 1},
        "greetings": [
            "i18n_npc_crpg_crossover.kyubey.greet_1",
            "i18n_npc_crpg_crossover.kyubey.greet_2",
            "i18n_npc_crpg_crossover.kyubey.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_crossover.kyubey.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_crossover.kyubey.spar_lost",
        "spar_execute_key": "i18n_npc_crpg_crossover.kyubey.spar_execute",
        "entry_rules": [
            {"when": {"all": [{"quest_ready": "quest_cycle_madoka"}, {"cycle_flag": "madoka_kyubey_ally"}]}, "node": "cycle_quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_revived_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "kyubey_read_contract", "category": "topic", "visible_if": {"service_available": "contract"}, "text_key": "i18n_npc_crpg_crossover.kyubey.opt_read_contract", "next_node": "contract_clauses"},
                    {"id": "kyubey_grief", "category": "service", "visible_if": {"service_available": "grief_seed"}, "service_key": "grief_seed", "text_key": "i18n_npc_crpg_crossover.kyubey.opt_grief", "effects": [{"type": "exhaustion", "amount": -1}, {"type": "give_item", "item_id": "grief_seed", "key": "i18n_chaos_expansion.npcs.kyubey.res_grief"}], "next_node": "root"},
                    {"id": "kyubey_attack", "category": "challenge", "text_key": "i18n_npc_crpg_crossover.kyubey.opt_attack", "effects": [{"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.kyubey.res_atk"}]},
                    {"id": "kyubey_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_crossover.kyubey.cycle_revived_text",
                "options": [
                    {"id": "kyubey_rev_ask", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_crossover.kyubey.opt_revive_talk", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "message", "key": "i18n_npc_crpg_crossover.kyubey.res_revive_talk"}], "next_node": "root"},
                    {"id": "kyubey_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "contract_clauses": {
                "text_key": "i18n_npc_crpg_crossover.kyubey.clauses_text",
                "options": [
                    {"id": "kyubey_sign", "category": "service", "exclusive_group": "kyubey_decision", "service_key": "contract", "text_key": "i18n_npc_crpg_crossover.kyubey.opt_sign", "effects": [{"type": "set_world_flag", "flag": "signed_kyubey_contract"}, {"type": "set_cycle_flag", "flag": "signed_kyubey_contract"}, {"type": "set_cycle_flag", "flag": "madoka_kyubey_ally"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "madoka_sign_kyubey", "unique_token": "madoka_sign_kyubey"}}, {"type": "max_hp", "amount": -3, "min_max_hp": 12, "key": "i18n_npc_crpg_crossover.kyubey.res_sign_hp"}, {"type": "gold", "amount": 50}, {"type": "give_item", "item_id": "kyubey_contract", "key": "i18n_npc_crpg_crossover.kyubey.res_sign_item"}], "next_node": "root"},
                    {"id": "kyubey_reject", "category": "topic", "exclusive_group": "kyubey_decision", "service_key": "contract", "text_key": "i18n_npc_crpg_crossover.kyubey.opt_reject", "effects": [{"type": "set_world_flag", "flag": "rejected_kyubey"}, {"type": "set_cycle_flag", "flag": "rejected_kyubey"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "madoka_reject_kyubey", "unique_token": "madoka_reject_kyubey"}}, {"type": "message", "key": "i18n_npc_crpg_crossover.kyubey.res_reject"}], "next_node": "root"},
                    {
                        "id": "kyubey_loophole",
                        "category": "topic",
                        "visible_if": {"check_not_tried": "kyubey_loophole_check"},
                        "text_key": "i18n_npc_crpg_crossover.kyubey.opt_loophole",
                        "check": {
                            "check_id": "kyubey_loophole_check",
                            "kind": "insight",
                            "dc": 14,
                            "modifiers": [{"cond": {"cycle_flag": "rejected_kyubey"}, "bonus": 2, "reason_key": "i18n_npc_crpg_crossover.kyubey.mod_experience"}],
                            "on_success": {"next_node": "contract_clauses", "effects": [{"type": "gold", "amount": 25}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "madoka_kyubey_loophole", "unique_token": "madoka_kyubey_loophole"}}, {"type": "message", "key": "i18n_npc_crpg_crossover.kyubey.res_loophole_ok"}]},
                            "on_fail": {"next_node": "contract_clauses", "effects": [{"type": "message", "key": "i18n_npc_crpg_crossover.kyubey.res_loophole_fail"}]},
                        },
                    },
                    {"id": "kyubey_clauses_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "root"},
                ],
            },
            "cycle_quest_turnin": {
                "text_key": "i18n_npc_crpg_crossover.kyubey.cycle_turnin_text",
                "options": [
                    {"id": "kyubey_turnin_cycle", "category": "quest", "text_key": "i18n_npc_crpg_crossover.kyubey.opt_turnin_cycle", "effects": [{"type": "complete_quest", "quest_id": "quest_cycle_madoka"}], "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_crossover.kyubey.exhausted_text", "options": []},
        },
    },
    "tomoe_mami": {
        "initial_affinity": 1,
        "cross_run_memory": True,
        "cycle_aware": False,
        "service_quotas": {"tea": 1, "tutor": 1},
        "greetings": [
            "i18n_npc_crpg_crossover.mami.greet_1",
            "i18n_npc_crpg_crossover.mami.greet_2",
            "i18n_npc_crpg_crossover.mami.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_crossover.mami.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_crossover.mami.spar_lost",
        "entry_rules": [
            {"when": {"world_flag": "signed_kyubey_contract"}, "node": "contract_warn_root"},
            {"when": {"killed_before": True}, "node": "cycle_revived_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "mami_tea", "category": "service", "visible_if": {"service_available": "tea"}, "service_key": "tea", "text_key": "i18n_npc_crpg_crossover.mami.opt_tea", "effects": [{"type": "affinity", "delta": 2}, {"type": "hp", "amount": 12}, {"type": "sp", "amount": 4}, {"type": "exhaustion", "amount": -1}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "madoka_mami_tea", "unique_token": "madoka_mami_tea"}}, {"type": "message", "key": "i18n_npc_crpg_crossover.mami.res_tea"}], "next_node": "root"},
                    {"id": "mami_tutor", "category": "service", "visible_if": {"service_available": "tutor"}, "service_key": "tutor", "text_key": "i18n_npc_crpg_crossover.mami.opt_tutor", "effects": [{"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1}, {"type": "give_item", "item_id": "sugar_cube_pack", "key": "i18n_chaos_expansion.npcs.tomoe_mami.res_tutor"}], "next_node": "root"},
                    {"id": "mami_heart", "category": "topic", "visible_if": {"check_not_tried": "mami_comfort_check"}, "text_key": "i18n_npc_crpg_crossover.mami.opt_comfort", "check": {"check_id": "mami_comfort_check", "kind": "persuade", "dc": 11, "auto_pass_cond": {"any": [{"cycle_flag": "rejected_kyubey"}, {"world_flag": "rejected_kyubey"}]}, "auto_pass_reason_key": "i18n_npc_crpg_crossover.mami.auto_rejected_qb", "on_success": {"next_node": "root", "effects": [{"type": "affinity", "delta": 4}, {"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1, "key": "i18n_npc_crpg_crossover.mami.res_comfort_ok"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "message", "key": "i18n_npc_crpg_crossover.mami.res_comfort_fail"}]}}},
                    {"id": "mami_spar", "category": "challenge", "text_key": "i18n_npc_crpg_crossover.mami.opt_spar", "effects": [{"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.tomoe_mami.res_spar"}]},
                    {"id": "mami_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "contract_warn_root": {
                "text_key": "i18n_npc_crpg_crossover.mami.contract_warn_text",
                "options": [
                    {"id": "mami_warn_ack", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_crossover.mami.opt_warn_ack", "effects": [{"type": "message", "key": "i18n_npc_crpg_crossover.mami.res_warn_ack"}], "next_node": "root"},
                    {"id": "mami_warn_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_crossover.mami.cycle_revived_text",
                "options": [
                    {"id": "mami_rev_talk", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_crossover.mami.opt_revive_talk", "effects": [{"type": "message", "key": "i18n_npc_crpg_crossover.mami.res_revive_talk"}], "next_node": "root"},
                    {"id": "mami_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_crossover.mami.exhausted_text", "options": []},
        },
    },
    "akemi_homura": {
        "initial_affinity": -1,
        "cross_run_memory": True,
        "cycle_aware": True,
        "service_quotas": {"supply": 1, "scout": 1, "purge": 1, "trust_gift": 1},
        "greetings": [
            "i18n_npc_crpg_crossover.homura.greet_1",
            "i18n_npc_crpg_crossover.homura.greet_2",
        ],
        "spar_yield_key": "i18n_npc_crpg_crossover.homura.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_crossover.homura.spar_lost",
        "spar_execute_key": "i18n_npc_crpg_crossover.homura.spar_execute",
        "entry_rules": [
            {"when": {"quest_ready": "quest_cycle_madoka"}, "node": "cycle_quest_turnin"},
            {"when": {"killed_before": True}, "node": "cycle_revived_root"},
        ],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "homura_cycle_talk", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_crossover.homura.opt_cycle_talk", "effects": [{"type": "set_cycle_flag", "flag": "met_homura"}, {"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "meta_homura_cycle", "unique_token": "meta_homura_cycle"}}, {"type": "message", "key": "i18n_npc_crpg_crossover.homura.res_cycle_talk"}], "next_node": "root"},
                    {"id": "homura_prove", "category": "topic", "visible_if": {"check_not_tried": "homura_trust_check"}, "text_key": "i18n_npc_crpg_crossover.homura.opt_prove", "check": {"check_id": "homura_trust_check", "kind": "persuade", "dc": 14, "modifiers": [{"cond": {"any": [{"cycle_flag": "rejected_kyubey"}, {"world_flag": "rejected_kyubey"}]}, "bonus": 4, "reason_key": "i18n_npc_crpg_crossover.homura.mod_rejected_qb"}, {"cond": {"cycle_flag": "sakuya_noted_homura"}, "bonus": 2, "reason_key": "i18n_npc_crpg_crossover.homura.mod_sakuya"}], "on_success": {"next_node": "root", "effects": [{"type": "affinity", "delta": 4}, {"type": "set_cycle_flag", "flag": "homura_trust_loop"}, {"type": "advance_quest", "event_type": "cycle_event", "payload": {"token": "madoka_homura_promise", "unique_token": "madoka_homura_promise"}}, {"type": "message", "key": "i18n_npc_crpg_crossover.homura.res_prove_ok"}]}, "on_fail": {"effects": [{"type": "affinity", "delta": -2}, {"type": "message", "key": "i18n_npc_crpg_crossover.homura.res_prove_fail"}]}}},
                    {"id": "homura_supply", "category": "service", "visible_if": {"all": [{"service_available": "supply"}, {"affinity_gte": 1}]}, "service_key": "supply", "text_key": "i18n_npc_crpg_crossover.homura.opt_supply", "effects": [{"type": "give_item", "item_id": "grief_seed", "key": "i18n_npc_crpg_crossover.homura.res_supply"}], "next_node": "root"},
                    {"id": "homura_scout", "category": "service", "visible_if": {"all": [{"service_available": "scout"}, {"affinity_gte": 1}]}, "service_key": "scout", "text_key": "i18n_npc_crpg_crossover.homura.opt_scout", "effects": [{"type": "reveal_rooms", "count": 2, "recap_id": "homura_rooms", "key": "i18n_npc_crpg_crossover.homura.res_scout", "empty_key": "i18n_npc_crpg_crossover.homura.res_scout_empty"}], "next_node": "root"},
                    {"id": "homura_time_branch", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_crossover.homura.opt_time_branch", "next_node": "time_branch"},
                    {"id": "homura_cycle_quest", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_cycle_madoka"}, "text_key": "i18n_npc_crpg_crossover.homura.opt_cycle_quest", "effects": [{"type": "accept_quest", "quest_id": "quest_cycle_madoka"}], "next_node": "root"},
                    {"id": "homura_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_revived_root": {
                "text_key": "i18n_npc_crpg_crossover.homura.cycle_revived_text",
                "options": [
                    {"id": "homura_rev_talk", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_crossover.homura.opt_revive_talk", "effects": [{"type": "set_cycle_flag", "flag": "asked_cycle_truth"}, {"type": "message", "key": "i18n_npc_crpg_crossover.homura.res_revive_talk"}], "next_node": "root"},
                    {"id": "homura_rev_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "cycle_quest_turnin": {
                "text_key": "i18n_npc_crpg_crossover.homura.cycle_turnin_text",
                "options": [
                    {"id": "homura_turnin_cycle", "category": "quest", "text_key": "i18n_npc_crpg_crossover.homura.opt_turnin_cycle", "effects": [{"type": "complete_quest", "quest_id": "quest_cycle_madoka"}, {"type": "affinity", "delta": 4}], "next_node": "root"},
                ],
            },
            "time_branch": {
                "text_key": "i18n_npc_crpg_crossover.homura.time_branch_text",
                "options": [
                    {"id": "homura_purge_curse", "category": "service", "visible_if": {"all": [{"service_available": "purge"}, {"has_curse_card": True}]}, "service_key": "purge", "text_key": "i18n_npc_crpg_crossover.homura.opt_homura_purge", "effects": [{"type": "remove_random_curse", "key": "i18n_npc_crpg_crossover.homura.res_homura_purge"}], "next_node": "root"},
                    {"id": "homura_trust_talk", "category": "topic", "visible_if": {"all": [{"cycle_flag": "homura_trust_loop"}, {"service_available": "trust_gift"}]}, "service_key": "trust_gift", "text_key": "i18n_npc_crpg_crossover.homura.opt_homura_trust_talk", "effects": [{"type": "affinity", "delta": 2}, {"type": "give_item", "item_id": "grief_seed", "key": "i18n_npc_crpg_crossover.homura.res_homura_trust_talk"}], "next_node": "root"},
                    {"id": "homura_time_back", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_back", "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_crossover.homura.exhausted_text", "options": []},
        },
    },
    "takamachi_nanoha": {
        "initial_affinity": 0,
        "cross_run_memory": False,
        "cycle_aware": False,
        "service_quotas": {"gift": 1, "charge": 1},
        "greetings": [
            "i18n_npc_crpg_crossover.nanoha.greet_1",
            "i18n_npc_crpg_crossover.nanoha.greet_2",
            "i18n_npc_crpg_crossover.nanoha.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_crossover.nanoha.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_crossover.nanoha.spar_lost",
        "entry_rules": [{"when": {"quest_ready": "quest_nanoha_suppress"}, "node": "quest_turnin"}],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "nanoha_gift", "category": "service", "visible_if": {"service_available": "gift"}, "service_key": "gift", "text_key": "i18n_npc_crpg_crossover.nanoha.opt_gift", "effects": [{"type": "gold", "amount": 18}, {"type": "give_item", "item_id": "mana_cartridge", "key": "i18n_npc_crpg_crossover.nanoha.res_gift"}], "next_node": "root"},
                    {"id": "nanoha_charge", "category": "service", "visible_if": {"service_available": "charge"}, "service_key": "charge", "text_key": "i18n_npc_crpg_crossover.nanoha.opt_charge", "effects": [{"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1}, {"type": "sp", "amount": 3, "key": "i18n_chaos_expansion.npcs.takamachi_nanoha.res_charge"}], "next_node": "root"},
                    {"id": "nanoha_lower_staff", "category": "topic", "visible_if": {"check_not_tried": "nanoha_staff_check"}, "text_key": "i18n_npc_crpg_crossover.nanoha.opt_lower_staff", "check": {"check_id": "nanoha_staff_check", "kind": "persuade", "dc": 12, "on_success": {"next_node": "root", "effects": [{"type": "affinity", "delta": 2}, {"type": "gold", "amount": 10}, {"type": "message", "key": "i18n_npc_crpg_crossover.nanoha.res_staff_ok"}]}, "on_fail": {"next_node": "staff_warn", "effects": [{"type": "affinity", "delta": -1}, {"type": "message", "key": "i18n_npc_crpg_crossover.nanoha.res_staff_fail"}]}}},
                    {"id": "nanoha_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_nanoha_suppress"}, "text_key": "i18n_npc_crpg_crossover.nanoha.opt_quest_ask", "effects": [{"type": "accept_quest", "quest_id": "quest_nanoha_suppress"}, {"type": "set_world_flag", "flag": "nanoha_msg_for_fate"}], "next_node": "root"},
                    {"id": "nanoha_canon", "category": "challenge", "text_key": "i18n_npc_crpg_crossover.nanoha.opt_canon", "effects": [{"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.takamachi_nanoha.res_canon"}]},
                    {"id": "nanoha_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "staff_warn": {
                "text_key": "i18n_npc_crpg_crossover.nanoha.staff_warn_text",
                "options": [
                    {"id": "nanoha_soothe", "category": "topic", "text_key": "i18n_npc_crpg_crossover.nanoha.opt_soothe", "effects": [{"type": "affinity", "delta": 1}, {"type": "message", "key": "i18n_npc_crpg_crossover.nanoha.res_soothe"}], "next_node": "root"},
                    {"id": "nanoha_warn_fight", "category": "challenge", "text_key": "i18n_npc_crpg_crossover.nanoha.opt_canon", "effects": [{"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.takamachi_nanoha.res_canon"}]},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_crossover.nanoha.quest_turnin_text",
                "options": [
                    {"id": "nanoha_turnin_ok", "category": "quest", "text_key": "i18n_npc_crpg_crossover.nanoha.opt_turnin", "effects": [{"type": "complete_quest", "quest_id": "quest_nanoha_suppress"}, {"type": "affinity", "delta": 3}], "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_crossover.nanoha.exhausted_text", "options": []},
        },
    },
    "fate_testarossa": {
        "initial_affinity": 0,
        "cross_run_memory": False,
        "cycle_aware": False,
        "service_quotas": {"intel": 1, "sonic": 1},
        "greetings": [
            "i18n_npc_crpg_crossover.fate.greet_1",
            "i18n_npc_crpg_crossover.fate.greet_2",
            "i18n_npc_crpg_crossover.fate.greet_3",
        ],
        "spar_yield_key": "i18n_npc_crpg_crossover.fate.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_crossover.fate.spar_lost",
        "entry_rules": [{"when": {"quest_ready": "quest_fate_wavelength"}, "node": "quest_turnin"}],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "fate_intel", "category": "service", "visible_if": {"service_available": "intel"}, "service_key": "intel", "text_key": "i18n_npc_crpg_crossover.fate.opt_intel", "effects": [{"type": "gold", "amount": 18}, {"type": "reveal_rooms", "count": 2, "recap_id": "fate_rooms", "key": "i18n_chaos_expansion.npcs.fate_testarossa.res_intel", "empty_key": "i18n_npc_crpg_crossover.fate.res_intel_empty"}], "next_node": "root"},
                    {"id": "fate_sonic", "category": "service", "visible_if": {"service_available": "sonic"}, "service_key": "sonic", "text_key": "i18n_npc_crpg_crossover.fate.opt_sonic", "effects": [{"type": "sp", "amount": 3}, {"type": "give_item", "item_id": "mana_cartridge", "key": "i18n_chaos_expansion.npcs.fate_testarossa.res_sonic"}], "next_node": "root"},
                    {"id": "fate_pet_arf", "category": "topic", "once_per_encounter": True, "text_key": "i18n_npc_crpg_crossover.fate.opt_pet_arf", "effects": [{"type": "set_local_flag", "flag": "fate_petted_arf"}, {"type": "affinity", "delta": 2}, {"type": "message", "key": "i18n_npc_crpg_crossover.fate.res_pet_arf"}], "next_node": "root"},
                    {"id": "fate_nanoha_msg", "category": "quest", "once_per_run": True, "visible_if": {"world_flag": "nanoha_msg_for_fate"}, "text_key": "i18n_npc_crpg_crossover.fate.opt_nanoha_msg", "effects": [{"type": "affinity", "delta": 2}, {"type": "advance_quest", "event_type": "deliver_message", "payload": {"token": "nanoha_to_fate", "unique_token": "nanoha_to_fate"}}, {"type": "message", "key": "i18n_npc_crpg_crossover.fate.res_nanoha_msg"}], "next_node": "root"},
                    {"id": "fate_share_burden", "category": "topic", "visible_if": {"check_not_tried": "fate_burden_check"}, "text_key": "i18n_npc_crpg_crossover.fate.opt_share_burden", "check": {"check_id": "fate_burden_check", "kind": "persuade", "dc": 12, "modifiers": [{"cond": {"local_flag": "fate_petted_arf"}, "bonus": 2, "reason_key": "i18n_npc_crpg_crossover.fate.mod_arf"}], "auto_pass_cond": {"world_flag": "nanoha_msg_for_fate"}, "auto_pass_reason_key": "i18n_npc_crpg_crossover.fate.auto_nanoha", "on_success": {"next_node": "root", "effects": [{"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1}, {"type": "reveal_rooms", "count": 1, "key": "i18n_npc_crpg_crossover.fate.res_burden_ok", "empty_key": "i18n_npc_crpg_crossover.fate.res_burden_buff"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "message", "key": "i18n_npc_crpg_crossover.fate.res_burden_fail"}]}}},
                    {"id": "fate_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_fate_wavelength"}, "text_key": "i18n_npc_crpg_crossover.fate.opt_quest_ask", "effects": [{"type": "accept_quest", "quest_id": "quest_fate_wavelength"}], "next_node": "root"},
                    {"id": "fate_duel", "category": "challenge", "text_key": "i18n_npc_crpg_crossover.fate.opt_duel", "effects": [{"type": "start_combat", "non_lethal": True, "intro_key": "i18n_chaos_expansion.npcs.fate_testarossa.res_duel"}]},
                    {"id": "fate_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_crossover.fate.quest_turnin_text",
                "options": [
                    {"id": "fate_turnin_ok", "category": "quest", "text_key": "i18n_npc_crpg_crossover.fate.opt_turnin", "effects": [{"type": "complete_quest", "quest_id": "quest_fate_wavelength"}, {"type": "affinity", "delta": 3}], "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_crossover.fate.exhausted_text", "options": []},
        },
    },
    "yagami_hayate": {
        "initial_affinity": 1,
        "cross_run_memory": False,
        "cycle_aware": False,
        "service_quotas": {"tome_tidy": 1, "ward_teach": 1},
        "greetings": [
            "i18n_npc_crpg_crossover.hayate.greet_1",
            "i18n_npc_crpg_crossover.hayate.greet_2",
        ],
        "spar_yield_key": "i18n_npc_crpg_crossover.hayate.spar_yield",
        "spar_lost_key": "i18n_npc_crpg_crossover.hayate.spar_lost",
        "entry_rules": [{"when": {"quest_ready": "quest_hayate_tome"}, "node": "quest_turnin"}],
        "nodes": {
            "root": {
                "text_key": "",
                "options": [
                    {"id": "hayate_tidy", "category": "service", "visible_if": {"service_available": "tome_tidy"}, "service_key": "tome_tidy", "text_key": "i18n_npc_crpg_crossover.hayate.opt_tidy", "effects": [{"type": "affinity", "delta": 2}, {"type": "give_item", "item_id": "ancient_notes", "key": "i18n_npc_crpg_crossover.hayate.res_tidy"}], "next_node": "root"},
                    {"id": "hayate_ward", "category": "service", "visible_if": {"service_available": "ward_teach"}, "service_key": "ward_teach", "text_key": "i18n_npc_crpg_crossover.hayate.opt_ward", "effects": [{"type": "add_buff", "buff_id": "ancient_ward", "stacks": 1}, {"type": "sp", "amount": 2, "key": "i18n_npc_crpg_crossover.hayate.res_ward"}], "next_node": "root"},
                    {"id": "hayate_decipher", "category": "topic", "visible_if": {"check_not_tried": "hayate_tome_check"}, "text_key": "i18n_npc_crpg_crossover.hayate.opt_decipher", "check": {"check_id": "hayate_tome_check", "kind": "insight", "dc": 12, "auto_pass_cond": {"player_class": "法师"}, "auto_pass_reason_key": "i18n_npc_crpg_crossover.hayate.auto_wizard", "on_success": {"next_node": "root", "effects": [{"type": "add_buff", "buff_id": "arcane_clarity", "stacks": 1, "key": "i18n_npc_crpg_crossover.hayate.res_decipher_ok"}]}, "on_fail": {"next_node": "root", "effects": [{"type": "message", "key": "i18n_npc_crpg_crossover.hayate.res_decipher_fail"}]}}},
                    {"id": "hayate_quest_ask", "category": "quest", "visible_if": {"can_accept_npc_quest": "quest_hayate_tome"}, "text_key": "i18n_npc_crpg_crossover.hayate.opt_quest_ask", "effects": [{"type": "accept_quest", "quest_id": "quest_hayate_tome"}], "next_node": "root"},
                    {"id": "hayate_spar", "category": "challenge", "text_key": "i18n_npc_crpg_crossover.hayate.opt_spar", "effects": [{"type": "start_combat", "non_lethal": True, "intro_key": "i18n_npc_crpg_crossover.hayate.res_spar"}]},
                    {"id": "hayate_leave", "category": "leave", "text_key": "i18n_npc_crpg_core.common.opt_leave", "tag_key": "i18n_npc_crpg_core.tags.leave", "effects": [{"type": "close_dialog"}]},
                ],
            },
            "quest_turnin": {
                "text_key": "i18n_npc_crpg_crossover.hayate.quest_turnin_text",
                "options": [
                    {"id": "hayate_turnin_ok", "category": "quest", "text_key": "i18n_npc_crpg_crossover.hayate.opt_turnin", "effects": [{"type": "complete_quest", "quest_id": "quest_hayate_tome"}, {"type": "affinity", "delta": 3}], "next_node": "root"},
                ],
            },
            "exhausted_root": {"text_key": "i18n_npc_crpg_crossover.hayate.exhausted_text", "options": []},
        },
    },
}
