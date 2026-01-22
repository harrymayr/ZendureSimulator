import base64
from datetime import datetime
import json
import logging
import traceback
from distribution import Distribution
from simDevice import ZendureDevice

_LOGGER = logging.getLogger(__name__)

@staticmethod
def load_logfile(filename: str, contents: str) -> dict['time': [], 'charge': [], 'p1': [], 'home': [], 'solar': [], 'simp1': [], 'simhome': []]:
    """Load simulation data from a logfile."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    starttime: list[datetime] = []
    time = []
    charge = []
    p1 = []
    home = []
    solar = []
    simp1 = []
    simhome = []
    distribution = Distribution("")
    sim_p1: int = 0

    def add(value: float) -> None:
        # update time series
        try:
            p1time=datetime.strptime(line[:23],"%Y-%m-%d %H:%M:%S.%f")
        except Exception:
            return

        if len(starttime) == 0:
            starttime.append(p1time)
            starttime.append(p1time)
            sim_p1 = value
            for d in devices.values():
                d.sim_avail = d.availableKwh.asNumber
                d.homePower.update_value(d.sim_home_act)
        else:
            # add time point
            time.append((p1time - starttime[0]).total_seconds())
            p1.append(value)
            home_act = 0
            home_org = 0
            solar_tot = 0
            for d in devices.values():
                home_act += d.homePower.asInt
                home_org += d.sim_home_act
                solar_tot += d.solarPower.asInt
            home.append(home_act)
            solar.append(solar_tot)
            sim_p1 = (home_org + int(value)) - home_act
            simp1.append(sim_p1)

            # calculate the simulated values
            timeBetweenUpdates = (p1time - starttime[1]).total_seconds()
            distribution.update(sim_p1, p1time)
            for d in devices.values():
                battery = d.homePower.asInt - d.solarPower.asInt
                d.sim_avail += (battery / 3600000) * timeBetweenUpdates
                d.sim_level = int((d.socSet.asNumber - d.minSoc.asNumber) * d.sim_avail / d.kWh)
                d.level = int(100 * (d.electricLevel.asNumber - d.minSoc.asNumber) / (d.socSet.asNumber - d.minSoc.asNumber))

            simhome.append(home_act)
 
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
                    try:
                        payload = json.loads(data)
                    except Exception as ex:
                        _LOGGER.error("JSON decode error in logfile line: %s", ex)
                        continue
                    if (payload is not None and (deviceid := payload.get('deviceId'))):
                        if (sim := devices.get(deviceid)) is None:
                            sim = ZendureDevice(deviceid)
                            devices[deviceid] = sim
                        sim.readEntities(payload)
                elif (idx := line.find('P1 ======>') + 14) > 14:
                    add(int(line[idx:line.find(' ', idx)]))
                elif (idx := line.find('P1 power changed => ') + 20) > 20:
                    add(int(line[idx:line.find('W', idx)]))
                elif (idx := line.find('Update operation: ') + 18) > 18:
                    operation = line[idx:line.find(' ', idx)]
                    _LOGGER.debug("Update operation: %s", operation)

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
        'simhome': simhome
    }
