import base64
from datetime import datetime
import json
import logging
import traceback
from const import ManagerMode
from distribution import Distribution
from simDevice import ZendureDevice

_LOGGER = logging.getLogger(__name__)

@staticmethod
def load_logfile(filename: str, contents: str) -> dict['time': [], 'charge': [], 'p1': [], 'home': [], 'solar': [], 'simp1': [], 'simhome': [], 'setpoint': []]:
    """Load simulation data from a logfile."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    starttime: list[datetime] = []
    time = []
    charge = []
    p1 = []
    home = []
    solar = []
    offgrid = []
    simp1 = []
    simhome = []
    setpoint = []
    distribution = Distribution("")
    distribution.set_operation(ManagerMode.MATCHING)

    def add(newP1: int) -> None:
        # update time series
        try:
            p1time=datetime.strptime(line[:23],"%Y-%m-%d %H:%M:%S.%f")
        except Exception:
            return

        sim_home = 0
        home_org = 0
        off_grid = 0
        solar_tot = 0
        charges = []
        if len(starttime) == 0:
            starttime.append(p1time)
            starttime.append(p1time)
            sim_p1 = newP1
            for d in devices.values():
                d.availableKwh.update_value(d.kWh * (d.electricLevel.asNumber - d.minSoc.asNumber) / 100)
                d.level = int((d.socSet.asNumber - d.minSoc.asNumber) * d.availableKwh.asNumber / d.kWh)
                d.homePower.update_value(d.home_org)
                sim_home += d.home_org
                home_org += d.home_org
                solar_tot += d.solarPower.asInt
                off_grid += d.offGrid.asInt
                charges.append(d.electricLevel.asNumber)

            distribution.devices = list(devices.values())
        else:
            # calculate the totals
            distribution.seconds = (p1time - starttime[0]).total_seconds()
            time.append(distribution.seconds)
            timeBetweenUpdates = (p1time - starttime[1]).total_seconds()
            for d in devices.values():
                # Update the totals
                d.homePower.update_value(d.power_setpoint)
                sim_home += d.power_setpoint
                home_org += d.home_org
                solar_tot += d.solarPower.asInt
                off_grid += d.offGrid.asInt

                # update the level
                battery = d.homePower.asInt - d.solarPower.asInt + d.offGrid.asInt
                avail = d.availableKwh.asNumber + (battery / 3600000) * timeBetweenUpdates
                avail_max = d.kWh * (d.socSet.asNumber - d.minSoc.asNumber) / 100
                avail = max(0, min(avail, avail_max))
                d.availableKwh.update_value(avail)
                d.level = avail / avail_max * 100 if avail_max > 0 else 0
                charges.append(d.electricLevel.asNumber)

            sim_p1 = (home_org + newP1) - sim_home + off_grid

            p1.append(newP1)
            home.append(home_org + newP1)
            solar.append(solar_tot)
            offgrid.append(off_grid)
            simp1.append(sim_p1)
            charge.append(charges)
            simhome.append(sum(d.power_setpoint for d in devices.values()))

        distribution.update(sim_p1, p1time)

        # update the distribution
        starttime[1] = p1time

    try:
        if filename.endswith('.log'):
            lines = decoded.decode('utf-8').splitlines()

            devices: dict[str, ZendureDevice] = {}
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
                        if (sim := devices.get(deviceid)) is None:
                            sim = ZendureDevice(deviceid)
                            distribution.devices.append(sim)
                            devices[deviceid] = sim
                        sim.readEntities(payload)
                elif (idx := line.find('P1 ======>') + 14) > 14:
                    add(int(line[idx:line.find(' ', idx)]))
                    idx = line.find('setpoint:', idx)
                    if idx > 0:
                        setpoint.append(int(line[idx + 9:line.find('W', idx)]))
                elif (idx := line.find('P1 power changed => ') + 20) > 20:
                    add(int(line[idx:line.find('W', idx)]))
                    idx = line.find('actual:', idx)
                    if idx > 0:
                        setpoint.append(int(line[idx + 8:line.find('W', idx)]))
                elif (idx := line.find('Update operation: ') + 18) > 18:
                    operation = line[idx:line.find(' ', idx)]
                    distribution.set_operation(ManagerMode(int(operation)) if operation.isnumeric() else ManagerMode[operation.split(".")[-1]])

    except Exception as e:
        _LOGGER.error("Error loading logfile: %s", e)
        _LOGGER.error(traceback.format_exc())

    if len(starttime) == 0:
        _LOGGER.error("No valid data found in logfile.")

    return {
        'time': time,
        'charge': charge,
        'p1': p1,
        'home': home,
        'solar': solar,
        'simp1': simp1,
        'simhome': simhome,
        'offgrid': offgrid,
        'setpoint': setpoint
    }
