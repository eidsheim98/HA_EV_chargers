import logging
import json
from click import edit
import voluptuous as vol
import datetime
import requests
import traceback
import os

from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = datetime.timedelta(minutes=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.ensure_list,
    }
)

BASE_URL = "https://api.drivstoffappen.no/"
INIT_URL = "api/stations?stationType=0&includeDeleted=true&minLastUpdated=2022-04-18T01%3A01%3A25GMT%2B02%3A00"
URL = BASE_URL + INIT_URL
PERS_JSON = ".fuel_integration.json"
filepath = os.path.dirname(__file__) + "/" + PERS_JSON
host = "api.drivstoffappen.no"
user_agent = "okhttp/4.7.2"
accept_encoding = "gzip"
connection = "Keep-Alive"
content_type = "application/json"
key = "2CD114509703F6E0A976C32FCB79C4F62966EEC6"

headers = {
    "Host": host,
    "User-Agent": user_agent,
    "Accept-Encoding": accept_encoding,
    "Connection": connection,
    "Content-Type": content_type,
    "x-api-key": key,
}


def get_gas_data(gas_data, gastype):
    found = False
    for data in gas_data:
        _type = data["type"]
        if _type == gastype:
            found = True
            break
    if found:
        lastupdated = data["lastUpdated"] / 1000
        now = datetime.datetime.now().timestamp()
        minutes_since_update = (now - lastupdated) / 60
        hours_since_update = minutes_since_update / 60

        # _LOGGER.debug(data["price"])
        # _LOGGER.debug(hours_since_update)

        if hours_since_update > 1:
            return data["price"], "Oppdatert for {:.0f} timer siden".format(
                hours_since_update
            )
        else:
            return data["price"], "Oppdatert for {:.0f} minutter siden".format(
                minutes_since_update
            )
    else:
        return None, None


def edit_name(name):
    name = (
        name.lower()
        .replace(" ", "_")
        .replace("å", "a")
        .replace("æ", "a")
        .replace("ø", "o")
        .replace("-", "_")
        .replace(".", "")
        .replace("å", "a")
        .replace("æ", "a")
        .replace("ø", "o")
    )
    return name


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor platform"""
    path = ""
    favourites = []

    ent_list = config.get(CONF_NAME)
    for e in ent_list:
        path = path + str(e) + ","
        favourites.append(int(e))
        _LOGGER.debug("Entity from list: " + e)

    _LOGGER.debug("Created URL: " + URL)

    ApiRequest().call(URL)
    devices = []

    json_obj = ReadJson().json_data()
    # _LOGGER.debug(json_obj)
    for station in json_obj:
        if station["id"] in favourites:
            sensor_id = station["id"]
            name = station["name"]

            try:
                brand = station["brand"]
                name = brand + " " + name
            except:
                pass

            station_details = station["stationDetails"]
            price_diesel, updated_diesel = get_gas_data(station_details, "D")
            price_98, updated_98 = get_gas_data(station_details, "98")
            price_95, updated_95 = get_gas_data(station_details, "95")

            res = {"98": price_98, "95": price_95}

            friendly_name = name
            name = edit_name(name)

            _LOGGER.debug("New sensor: " + str(name))

            devices.append(
                SensorDevice(
                    sensor_id, price_diesel, updated_diesel, name, friendly_name, res
                )
            )

            _LOGGER.info("Adding sensor: " + str(name))

    add_devices(devices)


class SensorDevice(Entity):
    def __init__(self, id, fuel_price, timestamp, name, friendly_name, res):
        self._device_id = "fuel_" + name
        self._state = fuel_price
        self._timestamp = timestamp
        self._friendly_name = friendly_name
        self._poller = id
        self._res = res
        self._unique_id = name

        # self.update()

    @Throttle(UPDATE_INTERVAL)
    def update(self):
        ApiRequest().call(URL)

        json_obj = ReadJson().json_data()
        # _LOGGER.debug(json_obj)
        for station in json_obj:
            if station["id"] == self._poller:
                sensor_id = station["id"]
                name = station["name"]
                station_details = station["stationDetails"]
                self.fuel_price, updated_diesel = get_gas_data(station_details, "D")
                price_98, updated_98 = get_gas_data(station_details, "98")
                price_95, updated_95 = get_gas_data(station_details, "95")

                self._res = {"98": price_98, "95": price_95}

                friendly_name = name
                name = edit_name(name)

                _LOGGER.info("Updating sensor: " + str(name))

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "kr"

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._friendly_name

    @property
    def state(self):
        """Return the state of the sensor"""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor"""
        return "mdi:gas-station"

    @property
    def device_class(self):
        """Return the device class of the sensor"""
        return "monetary"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._res


class ApiRequest:
    def call(self, url):
        try:
            """Temperature"""

            traceback.print_exc()

            response = requests.get(url, headers=headers)
            _LOGGER.debug(response)

            if response.status_code == 200:
                stations_json = json.loads(response.text)
                _LOGGER.debug(
                    "Sending API request to: "
                    + url
                    + " Printing result to "
                    + PERS_JSON
                )

                _LOGGER.debug(filepath)
                with open(filepath, "w+") as json_file:
                    json_file.write(response.text)

                # _LOGGER.debug("Here")
                return True

            else:
                _LOGGER.debug("API CALL FAILED")
                return False
        except Exception as e:
            _LOGGER.debug(e.with_traceback())


class ReadJson:
    def __init__(self):
        self.update()

    @Throttle(UPDATE_INTERVAL)
    def update(self):
        """Temperature"""
        _LOGGER.debug("Reading " + PERS_JSON + " for device")
        with open(filepath, "r") as json_file:
            json_datas = json.load(json_file)
        self._json_response = json_datas

    def json_data(self):
        """Keep json data"""
        return self._json_response
