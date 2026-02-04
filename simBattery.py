"""Devices for Zendure Integration."""

from datetime import datetime

from const import DOMAIN
from simEntity import simEntity


class ZendureBattery:
    """Representation of a Zendure battery."""

    def __init__(self, parent: str, device_sn: str) -> None:
        """Initialize the Zendure battery."""
        self.kWh = 0.0
        match device_sn[0]:
            case "A":
                if device_sn[3] == "3":
                    model = "AIO2400"
                    self.kWh = 2.4
                else:
                    model = "AB1000"
                    self.kWh = 0.96
            case "B":
                model = "AB1000S"
                self.kWh = 0.96
            case "C":
                model = "AB2000" + ("S" if device_sn[3] == "F" else "X" if device_sn[3] == "E" else "")
                self.kWh = 1.92
            case "F":
                model = "AB3000"
                self.kWh = 2.88
            case _:
                model = "Unknown"
                self.kWh = 0.0

        self.lastseen = datetime.min

        # Create the battery entities."""
        self.state = simEntity(self, "packState")
        self.socLevel = simEntity(self, "socLevel")
        self.state = simEntity(self, "state")
        self.power = simEntity(self, "power")
        self.maxTemp = simEntity(self, "maxTemp")
        self.totalVol = simEntity(self, "totalVol")
        self.batcur = simEntity(self, "batcur")
        self.maxVol = simEntity(self, "maxVol")
        self.minVol = simEntity(self, "minVol")
        
    def entityRead(self, payload: dict) -> int:
        """Handle incoming MQTT message for the battery."""
        for key, value in payload.items():
            entity = self.__dict__.get(key)
            if key != "sn" and (entity := self.__dict__.get(key)):
                entity.update_value(value)
        return self.power.asInt
