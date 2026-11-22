BUFF_CLASS_REGISTRY = {}

def register_buff(buff_id: str):
    """注册 Buff ID 与 BuffImpl 子类，供 BuffTriggerHandler 派发生命周期钩子。"""
    def decorator(cls):
        BUFF_CLASS_REGISTRY[buff_id] = cls
        return cls
    return decorator
