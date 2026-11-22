CARD_CLASS_REGISTRY = {}

def register_card(cid, **kwargs):
    """注册卡牌 ID 与实现类，装饰器参数写入注册表供卡牌实例化时使用。"""
    def decorator(cls):
        CARD_CLASS_REGISTRY[cid] = (cls, kwargs)
        return cls
    return decorator
