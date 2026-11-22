import random
from typing import List
from ...data.text.trash_talk_data import TALKING_ENEMIES, TRASH_TALK_DB

def try_trash_talk(run, enemy, logs: List[str]):
    if enemy.name not in TALKING_ENEMIES:
        return
    
    current_turn = run.node_data.get("turn", 1)
    if getattr(enemy, "_talked_turn", -1) == current_turn:
        return
    
    is_duel_opponent = enemy.name in {
        "NoobSlayer99", "xXx_SniperElite_xXx", "pppopipupu", "【觉醒】pppopipupu", "Gate_Guardian"
    }
    
    if not is_duel_opponent and random.random() >= 0.5:
        return
    
    enemy._talked_turn = current_turn
    
    player = run.player
    hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 1.0
    hand_count = len(player.hand)
    shield = player.shield
    
    enemy_pool = TRASH_TALK_DB.get(enemy.name, {})
    if not enemy_pool:
        return
    
    category = "normal"
    if hp_ratio < 0.35:
        category = "low_hp"
    elif shield > 15:
        category = "high_shield"
    elif hand_count <= 1:
        category = "low_hand"
    elif hand_count > 11:
        category = "high_hand"
        
    candidates = enemy_pool.get(category, [])
    if not candidates:
        candidates = enemy_pool.get("normal", [])
        
    if candidates:
        logs.append(random.choice(candidates))
