from datetime import datetime, timedelta
import enum
import logging
from typing import Any
from const import SmartMode
from simBattery import ZendureBattery
from simEntity import simEntity


_LOGGER = logging.getLogger(__name__)

class DeviceState(enum.Enum):
    CREATED = 0
    OFFLINE = 1
    NOBATTERY = 2
    NOFUSEGROUP = 3
    ACTIVE = 4
    CALIBRATE = 5
    HEMS = 6

class ZendureDevice:
    def __init__(self, deviceid: str):
        from fusegroup import CONST_EMPTY_GROUP, FuseGroup
        self.deviceid = deviceid
        self.name = deviceid
        self.batteries: dict[str, ZendureBattery | None] = {}
        self.kWh = 4.0
        self.limit = [-1200, 1200]
        self.level = 0
        self.fuseGrp: FuseGroup = FuseGroup(self.name, 3200, -3200, devices=[self])  # Default empty fuse group
        self.values = [0, 0, 0, 0]
        self.power_setpoint = 0
        self.power_time = datetime.min
        self.power_offset = 0
        self.power_limit = 0
        self.sim_battery = 0
        self.home_org = 0
        self.batout = 0
        self.status = DeviceState.ACTIVE

        self.simP1 = simEntity(self, "simP1")
        self.simHome = simEntity(self, "simHome")

        self.electricLevel = simEntity(self, "electricLevel")
        self.homePower = simEntity(self, "homePower")
        self.batteryPower = simEntity(self, "batteryPower")
        self.solarPower = simEntity(self, "solarPower")
        self.offGrid = simEntity(self, "offGrid")

        self.socStatus = simEntity(self, "socStatus", state=0)
        self.socLimit = simEntity(self, "socLimit", state=0)

        self.minSoc = simEntity(self, "socMin", state=10, factor=0.1)
        self.socSet = simEntity(self, "socMax", state=90, factor=0.1)
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
            self.batout = 0
            for b in batprops:
                if (sn := b.get("sn", None)) is None:
                    continue

                if (bat := self.batteries.get(sn, None)) is None:
                    self.batteries[sn] = ZendureBattery(self.name, sn)
                    self.kWh = sum(0 if b is None else b.kWh for b in self.batteries.values())
                    self.batteryUpdate()
                elif bat and b:
                    self.batout += bat.entityRead(b)
        self.home_org = -self.values[0] + (self.offGrid.asInt - self.batout) if self.values[0] > 0 and self.offGrid is not None and self.offGrid.asInt > 0 else 0 + self.values[1]

    def batteryUpdate(self) -> None:
        """Update device based on battery status."""

    def entityUpdate(self, key: str, value: Any) -> None:

        match key:
            case "gridInputPower":
                self.values[0] = value
            case "outputHomePower":
                self.values[1] = value
            case "outputPackPower":
                self.values[2] = value
                self.batteryPower.update_value(-value + self.values[3])
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
            case "inverseMaxPower":
                self.setLimits(self.limit[0], value)
            case "chargeLimit" | "chargeMaxLimit":
                self.setLimits(-value, self.limit[1])
            case _:
                if entity := self.__dict__.get(key):
                    entity.update_value(value)

    def setLimits(self, charge: int, discharge: int) -> None:
        try:
            """Set the device limits."""
            self.limit = [charge, discharge]
            self.inputLimit.update_value(charge)
            self.outputLimit.update_value(discharge)
        except Exception:
            _LOGGER.error(f"SetLimits error {self.name} {charge} {discharge}!")

    def distribute(self, power: int, time: datetime) -> int:
        """Set charge/discharge power, but correct for power offset."""
        # if self.power_time != datetime.min and (delta := (self.power_time - time).total_seconds())> 0:
        #     if (delta < 1):
        #         self.homePower.update_value(self.power_setpoint)
        #     else:
        #         return self.power_setpoint

        pwr = power + self.power_offset
        if (delta := abs(pwr - self.homePower.asInt)) <= SmartMode.POWER_TOLERANCE:
            return self.homePower.asInt - self.power_offset
        pwr = min(max(self.limit[0], pwr), self.limit[1])

        # adjust for bypass
        if pwr < 0 and  self.level >= 99.99:
            pwr = 0
        elif self.level == 0:
            pwr = min(self.solarPower.asInt, pwr)

        self.power_setpoint = pwr
        if power != self.power_setpoint:
            self.power_time = time + timedelta(seconds=3 + delta / 250)
        return pwr + self.power_offset
