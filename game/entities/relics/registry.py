RELIC_CLASS_REGISTRY = {}

def register_relic(relic_id: str):
    """注册遗物 ID 与 RelicImpl 子类，供运行时按遗物 ID 查找实现。"""
    def decorator(cls):
        RELIC_CLASS_REGISTRY[relic_id] = cls
        return cls
    return decorator
