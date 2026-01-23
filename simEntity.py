from typing import Any


class simEntity:
    def __init__(self, parent: Any, entityid: str, state: Any = 0, factor: float = 1):
        self.parent = parent
        self.entityid = entityid
        self.data = state * factor
        self.factor = factor

    def update_value(self, value: Any) -> None:
        self.data = value * self.factor

    @property
    def asInt(self) -> int:
        return int(self.data)
    
    @property
    def asNumber(self) -> float:
        return float(self.data)