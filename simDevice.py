from datetime import datetime, timedelta
import logging
from typing import Any
from const import SmartMode
from simBattery import ZendureBattery
from simEntity import simEntity


_LOGGER = logging.getLogger(__name__)


class ZendureDevice:
    def __init__(self, deviceid: str):
        from fusegroup import CONST_EMPTY_GROUP, FuseGroup
        self.deviceid = deviceid
        self.name = deviceid
        self.batteries: dict[str, ZendureBattery | None] = {}
        self.kWh = 4.0
        self.limit = [0, 0]
        self.level = 0
        self.fuseGrp: FuseGroup = FuseGroup(self.name, 3200, -3200, devices=[self])  # Default empty fuse group
        self.values = [0, 0, 0, 0]
        self.power_setpoint = 0
        self.power_time = datetime.min
        self.power_offset = 0
        self.power_limit = 0
        self.sim_avail = 0.0
        self.sim_pass = False
        self.sim_battery = 0
        self.sim_level = 0
        self.sim_home_act = 0

        self.simP1 = simEntity(self, "simP1")
        self.simHome = simEntity(self, "simHome")

        self.electricLevel = simEntity(self, "electricLevel")
        self.homePower = simEntity(self, "homePower")
        self.batteryPower = simEntity(self, "batteryPower")
        self.solarPower = simEntity(self, "solarPower")
        self.offGrid = simEntity(self, "offGrid")

        self.socStatus = simEntity(self, "socStatus", state=0)
        self.socLimit = simEntity(self, "socLimit", state=0)

        self.minSoc = simEntity(self, "socMin", state=10)
        self.socSet = simEntity(self, "socMax", state=90)
        self.inputLimit = simEntity(self, "inputLimit")
        self.outputLimit = simEntity(self, "outputLimit")

        self.availableKwh = simEntity(self, "available_kwh")
        self.connectionStatus = simEntity(self, "connectionStatus", state=0)
        self.byPass = simEntity(self, "pass")
        self.fuseGroup = simEntity(self, "fuseGroup")
        
    def readEntities(self, payload: dict):
        if (properties := payload.get("properties")) and len(properties) > 0:
            for key, value in properties.items():
                self.entityUpdate(key, value)

        if batprops := payload.get("packData"):
            for b in batprops:
                if (sn := b.get("sn", None)) is None:
                    continue

                if (bat := self.batteries.get(sn, None)) is None:
                    self.batteries[sn] = ZendureBattery(self.name, sn)
                    self.kWh = sum(0 if b is None else b.kWh for b in self.batteries.values())
                    self.batteryUpdate()
                elif bat and b:
                    bat.entityRead(b)

    def batteryUpdate(self) -> None:
        """Update device based on battery status."""

    def entityUpdate(self, key: str, value: Any) -> None:
        def home(value: int) -> None:
            if self.power_time > datetime.min and abs(value - self.power_setpoint) < 20:
                self.power_time = datetime.min
            self.sim_home_act = value
            # self.homePower.update_value(value)

        match key:
            case "gridInputPower":
                self.values[0] = value
                self.homePower.update_value(-value + self.values[1])
            case "outputHomePower":
                self.values[1] = value
                home(-self.values[0] + value)
            case "outputPackPower":
                self.values[2] = value
                home(-value + self.values[3])
            case "packInputPower":
                self.values[3] = value
                self.batteryPower.update_value(-self.values[2] + value)
            case "solarInputPower":
                self.solarPower.update_value(value)
            case "gridOffPower":
                if self.offGrid is not None:
                    self.offGrid.update_value(value)
            case "electricLevel":
                self.electricLevel.update_value(value)
                self.level = int(100 * (self.electricLevel.asNumber - self.minSoc.asNumber) / (self.socSet.asNumber - self.minSoc.asNumber))
                self.availableKwh.update_value(round(self.kWh * self.level / 100, 2))
            case "inverseMaxPower":
                self.setLimits(self.inputLimit.asInt, value)
            case "chargeLimit" | "chargeMaxLimit":
                self.setLimits(-value, self.outputLimit.asInt)
            case _:
                if entity := self.__dict__.get(key):
                    entity.update_value(value)

    def setLimits(self, charge: int, discharge: int) -> None:
        try:
            """Set the device limits."""
            self.limit = [charge, discharge]
        except Exception:
            _LOGGER.error(f"SetLimits error {self.name} {charge} {discharge}!")

    def distribute(self, power: int, time: datetime) -> int:
        """Set charge/discharge power, but correct for power offset."""
        if (delta := time - self.power_time)> 0:
            if (delta < 1):
                self.homePower.update_value(self.power_setpoint)
            return self.power_setpoint

        pwr = power - self.power_offset
        if (delta := abs(pwr - self.homePower.asInt)) <= SmartMode.POWER_TOLERANCE:
            return self.homePower.asInt + self.power_offset

        pwr = min(max(self.limit[0], pwr), self.limit[1])
        self.power_setpoint = pwr
        self.power_time = time + timedelta(seconds=3 + delta / 250)
        return pwr + self.power_offset
