from .relic_handler import RelicTriggerHandler
from .buff_handler import BuffTriggerHandler
from .amulet_handler import AmuletTriggerHandler
from .minion_handler import MinionTriggerHandler
from .enemy_handler import EnemyTriggerHandler
from .card_handler import CardTriggerHandler
from .meta_handlers import RallyTriggerHandler, StatTrackingHandler, AchievementObserver
from .gem_handler import GemTriggerHandler
from .enchantment_handler import EnchantmentTriggerHandler
from .class_handler import ClassPassiveHandler
from .ward_service import WardRedirectHandler
from .mercenary_handler import ChaoticMercenaryRedirectHandler
from .ninja_handler import NinjaEventHandler


def register_default_battle_handlers(event_bus, engine, save_manager):
    """创建默认战斗观察者集合并返回，供引擎保存引用与调试使用。"""
    return {
        "relic": RelicTriggerHandler(event_bus, engine),
        "buff": BuffTriggerHandler(event_bus, engine),
        "amulet": AmuletTriggerHandler(event_bus, engine),
        "rally": RallyTriggerHandler(event_bus, engine),
        "minion": MinionTriggerHandler(event_bus, engine),
        "enemy": EnemyTriggerHandler(event_bus, engine),
        "card": CardTriggerHandler(event_bus, engine),
        "stat_tracking": StatTrackingHandler(event_bus, save_manager),
        "achievement": AchievementObserver(event_bus, engine, save_manager),
        "gem": GemTriggerHandler(event_bus, engine),
        "enchantment": EnchantmentTriggerHandler(event_bus, engine),
        "class_passive": ClassPassiveHandler(event_bus, engine),
        "ward": WardRedirectHandler(event_bus, engine),
        "chaotic_mercenary": ChaoticMercenaryRedirectHandler(event_bus, engine),
        "ninja": NinjaEventHandler(event_bus, engine),
    }
