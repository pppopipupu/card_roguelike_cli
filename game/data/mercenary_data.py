MERCENARY_HARRY_HIRE_COST = 50
HARRY_VOICE_CHANCE = 0.45
HARRY_MAX_VOICES_PER_TURN = 2

MERCENARY_CONFIG = {
    "harry_du_bois": {
        "id": "harry_du_bois",
        "name": "哈里·杜博阿",
        "aliases": ["harry_du_bois", "harry", "哈里杜博阿", "哈里·杜博阿", "哈里"],
        "hire_cost_gp": MERCENARY_HARRY_HIRE_COST,
        "hp": 72,
        "class_name": "RCM 警探",
        "default_timing": "after",
        "starting_deck": [
            "pale_interference",
            "pale_interference",
            "pale_two_mm_hole",
            "pale_white_noise",
            "pale_white_noise",
            "pale_crossing",
            "pale_lathe_memory",
            "pale_porch_collapse",
            "thought_aces_high",
            "thought_aces_low",
            "thought_actual_art_degree",
            "thought_advanced_race_theory",
            "thought_anti_object_task_force",
            "thought_apricot_chewing_gum",
            "thought_arno_van_eyck",
            "thought_bankruptcy_sequence",
            "thought_boiadeiro",
            "thought_bringing_of_the_law",
            "thought_caustic_echo",
            "thought_cleaning_out_the_rooms",
            "thought_coach_physical_instrument",
            "thought_col_do_ma_ma_daqua",
            "thought_cop_of_the_apocalypse",
        ],
    }
}

HARRY_SKILL_SCENARIOS = (
    "battle_start",
    "turn_start",
    "card_play",
    "take_damage",
    "battle_win",
)

HARRY_SKILL_IDS = (
    "logic",
    "encyclopedia",
    "rhetoric",
    "drama",
    "conceptualization",
    "visual_calculus",
    "volition",
    "inland_empire",
    "empathy",
    "authority",
    "esprit_de_corps",
    "suggestion",
    "endurance",
    "pain_threshold",
    "physical_instrument",
    "electrochemistry",
    "shivers",
    "half_light",
    "hand_eye_coordination",
    "perception",
    "reaction_speed",
    "savoir_faire",
    "interfacing",
    "composure",
)

MERCENARY_TIMING_BEFORE = "before"
MERCENARY_TIMING_AFTER = "after"
