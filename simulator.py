import base64
from datetime import datetime
from importlib.metadata import distribution
import json
import logging
import traceback
from typing import Any
from const import ManagerMode
from distribution import Distribution, DistributionMode
from simDevice import ZendureDevice

_LOGGER = logging.getLogger(__name__)


class ZendureSimulator:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.devices: dict[str, ZendureDevice] = {}
        self.time = []
        self.p1 = []
        self.homeC = []
        self.homeZ = []
        self.solar = []
        self.offgrid = []
        self.modes = []
        self.sim_home = []
        self.sim_p1 = []

    def load_logfile(self, filename: str, contents: str) -> dict[str, Any]:
        """Load simulation data from a logfile."""
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        self.reset()
        def add(newP1: int) -> None:
            # update time series
            try:
                p1time=datetime.strptime(line[:23],"%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                return

            home_total = 0
            solar_total = 0
            offgrid_total = 0
            for d in self.devices.values():
                d.solar.append(d.solarPower.asInt)
                d.offgrid.append(d.offGrid.asInt)
                if d.startindex == -1 and d.electricLevel.asInt > 0:
                    d.startindex = len(self.time)
                d.levels.append(d.electricLevel.asInt)
                home_total += d.homePower.asInt
                solar_total += d.solarPower.asInt
                offgrid_total += d.offGrid.asInt

            self.time.append(p1time)
            self.p1.append(newP1)
            self.homeZ.append(home_total)
            self.homeC.append(home_total + newP1)
            self.solar.append(solar_total)
            self.offgrid.append(offgrid_total)
        try:
            if filename.endswith('.log'):
                lines = decoded.decode('utf-8').splitlines()

                self.devices.clear()
                for line in lines:
                    line = line if not line.startswith('\x1b[32m') else line[5:]
                    if (idx := line.find('properties/report') + 22) > 22:
                        data = line[line.find('{'):line.rfind('}') + 1].replace("\'", "\"").replace(" True", " true")
                        if len(data) == 0:
                            continue
                        try:
                            payload = json.loads(data)
                        except Exception as ex:
                            _LOGGER.error("JSON decode error in logfile line: %s, error: %s", line, ex)
                            continue
                        if (payload is not None and (deviceid := payload.get('deviceId'))):
                            if (d := self.devices.get(deviceid)) is None:
                                d = ZendureDevice(deviceid, len(self.time))
                                self.devices[deviceid] = d
                            d.readEntities(payload)
                    elif (idx := line.find('P1 ======>') + 14) > 14:
                        add(int(line[idx:line.find(' ', idx)]))
                    elif (idx := line.find('P1 power changed => ') + 20) > 20:
                        add(int(line[idx:line.find('W', idx)]))
                    elif (idx := line.find('Update operation: ') + 18) > 18:
                        operation = line[idx:line.find(' ', idx)]
                        mode = ManagerMode(int(operation)) if operation.isnumeric() else ManagerMode[operation.split(".")[-1]]
                        self.modes.append((mode.value, len(self.time)))

        except Exception as e:
            _LOGGER.error("Error loading logfile: %s", e)
            _LOGGER.error(traceback.format_exc())

        return { }


    def do_simulation(self, data: dict[str, Any], distribution_mode: str, start_power: int, power_tolerance: int) -> dict[str, Any]:
        """Load simulation data from a logfile."""

        if len(self.time) == 0:
            return data

        self.sim_home = []
        self.sim_p1 = []

        match distribution_mode:
            case "Max Solar":
                mode = DistributionMode.MAXSOLAR
            case "Min Buying":
                mode = DistributionMode.MINBUYING
            case _:
                mode = DistributionMode.NEUTRAL

        distribution = Distribution("", mode, start_power, power_tolerance)
        distribution.set_operation(ManagerMode.MATCHING)
        distribution.devices = list(self.devices.values())

        starttime = self.time[0]
        for i, t in enumerate(self.time):
            simhome = 0
            if i == 0:
                simhome = self.homeZ[0]
                simp1 = self.p1[0]
                self.sim_home.append(self.homeZ[0])
                self.sim_p1.append(self.p1[0])
                for d in self.devices.values():
                    d.availableKwh.update_value(d.kWh * (d.levels[d.startindex] - d.minSoc.asNumber) / 100)
                    avail_max = d.kWh * (d.socSet.asNumber - d.minSoc.asNumber) / 100
                    d.level = round(100 * d.availableKwh.asNumber / avail_max)
                    d.homePower.update_value(self.homeZ[d.startindex])
                    d.solarPower.update_value(d.solar[d.startindex])
                    d.offGrid.update_value(d.offgrid[d.startindex])
                    d.sim_level.append(d.levels[d.startindex])
            else:
                timeBetweenUpdates = (t - starttime).total_seconds()
                for d in self.devices.values():
                    # Update the totals
                    d.solarPower.update_value(d.solar[i])
                    d.offGrid.update_value(d.offgrid[i])
                    simhome += d.power_setpoint
                    d.homePower.update_value(d.power_setpoint)

                    # update the running values
                    battery = d.homePower.asInt - d.solarPower.asInt + d.offGrid.asInt
                    avail = d.availableKwh.asNumber - (battery / 3600000) * timeBetweenUpdates
                    avail_max = d.kWh * (d.socSet.asNumber - d.minSoc.asNumber) / 100
                    avail = max(0, min(avail, avail_max))
                    d.availableKwh.update_value(avail)
                    d.level = round(100 * d.availableKwh.asNumber / avail_max)
                    d.sim_level.append(round(100 * avail / d.kWh + d.minSoc.asNumber))

                simp1 = self.homeC[i] - simhome 

            distribution.update(simp1, t)
            self.sim_p1.append(simp1)
            self.sim_home.append(sum(d.power_setpoint for d in self.devices.values()))
            starttime = t

        return data