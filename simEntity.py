from typing import Any


class simEntity:
    def __init__(self, parent: Any, entityid: str, state: Any = 0):
        self.parent = parent
        self.entityid = entityid
        self.data = state

    def update_value(self, value: Any) -> None:
        self.data = value

    @property
    def asInt(self) -> int:
        return int(self.data)
    
    @property
    def asNumber(self) -> float:
        return float(self.data)