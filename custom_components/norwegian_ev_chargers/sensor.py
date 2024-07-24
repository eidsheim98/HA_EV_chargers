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


def get_token(self):
    url = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key=AIzaSyBGIYse3GTN_s5Ssd_Qnd8Q3_6azHvQ8qA"
    headers = {
        "Accept-Encoding": "gzip",
        "Accept-Language": "en-US",
        "Connection": "Keep-Alive",
        "Content-Type": "application/json",
        "Host": "www.googleapis.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; sdk_gphone64_x86_64 Build/SE1A.220826.008)",
        "X-Android-Cert": "073B265A6A68A563CE70F1A15F41146630F583D7",
        "X-Android-Package": "no.vg.lab.zapp",
        "X-Client-Version": "Android/Fallback/X22003001/FirebaseCore-Android",
        "X-Firebase-AppCheck": "eyJlcnJvciI6IlVOS05PV05fRVJST1IifQ==",
        "X-Firebase-Client": "H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA",
        "X-Firebase-GMPID": "1:311678904626:android:5712a54a28c8e40342cf2b"
    }

    body = json.loads('{"clientType": "CLIENT_TYPE_ANDROID"}')

    response = requests.post(url, json=body, headers=headers)
    j = response.json()
    token = j["idToken"]
    return token


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor platform"""
    charger = ""

    ent_list = config.get(CONF_NAME)
    for e in ent_list:
        charger = e
        _LOGGER.debug("Charger type: " + e)

    _LOGGER.debug("Created URL: " + URL)

    ApiRequest().call(URL)
    devices = []

    json_obj = ReadJson().json_data()

    # _LOGGER.debug(json_obj)
    for station in json_obj:
        if station["id"] in favourites:            

            _LOGGER.debug("New sensor: " + str(name))

            devices.append(
                SensorDevice(
                    station.name, station.lat, station.long, station.operator, station.facilities, station.power, station.time, None
                )
            )

            _LOGGER.info("Adding sensor: " + str(station.name))

    add_devices(devices)


class SensorDevice(Entity): #Normal station
    def __init__(self, name, lat, long, operator, facilities, power, time, res):

        self._device_id = "charger_" + name
        self._state = name
        self._latitude = lat
        self._longitude = long
        self._operator = operator
        self._facilities = facilities
        self._power = power
        self._time = time
        self._price = None
        self._unique_id = name
        self._poller = id

        # self.update()

    @Throttle(UPDATE_INTERVAL)
    def update(self):
        ApiRequest().call(URL)

        chargers = ReadJson().json_data()
        # _LOGGER.debug(json_obj)
        for station in chargers:
            self._power = station.power

            _LOGGER.info("Updating sensor: " + str(self.name))

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


class ReadJson:
    def __init__(self):
        self.update()

    def get_full_info(self, s_data):
        print("Getting full station info")
        data = []

        fastest_time = 1000000000
        fastest_charger = None
        lowest_price = 1000000000
        cheapest_charger = None

        for s in s_data:
            s_id = s["id"]
            info_response = self._get_station_info(s_id)

            if info_response.status_code != 200:
                print("Error getting full station info")
                continue

            info = info_response.content.decode()
            info = json.loads(info)

            for i in range(len(info["chargers"])):
                charger = info["chargers"][i]
                c = Charger(
                    info["name"],
                    info["coordinates"][0],
                    info["coordinates"][1],
                    info["operator"],
                    info["facilities"],
                    charger["voltage"],
                    charger["estimated"]["time"],
                )

                if "price" in charger["estimated"].keys():
                    c.price = charger["estimated"]["price"]
                    if charger["estimated"]["price"] <= lowest_price:
                        fastest_time = charger["estimated"]["time"]
                        cheapest_charger = i

                if charger["estimated"]["time"] <= fastest_time:
                    fastest_time = charger["estimated"]["time"]
                    fastest_charger = i

                data.append(c)

        return data
        

    @Throttle(UPDATE_INTERVAL)
    def update(self):
        _LOGGER.debug("Getting stations")

        token = get_token()

        url = f"https://stations.elton.app/pins?plugs=eyJJRUNfNjIxOTZfVDJfQ09NQk8iOjE4MCwiSUVDXzYyMTk2X1QyIjoxMSwiQ0hBREVNTyI6NjB9&capacity=80&best=false&canChargeWithElton=false&latitudeCenter={lat}&longitudeCenter={long}&longitudeDelta=3&latitudeDelta=3&maxLimit=10"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept-Encoding": "gzip",
            "Accept-Language": "en-US",
            "Connection": "Keep-Alive",
            "Credentials": "include",
            "Host": "stations.elton.app"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            _LOGGER.error("Unable to get stations")
            quit()

        data = response.content.decode()
        j = json.loads(data)


        self._full_info = self.get_full_info(j)

    def json_data(self):
        return self._full_info
