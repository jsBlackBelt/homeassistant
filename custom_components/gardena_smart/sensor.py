import logging
from datetime import timedelta
import json

import voluptuous as vol

from homeassistant.helpers.entity import Entity
import homeassistant.util as util
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['gardena-smart==0.11b2']


_LOGGER = logging.getLogger(__name__)

CONF_ID = 'id'
CONF_LOCATION_ID = 'location'
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_ID): cv.string,
    vol.Optional(CONF_LOCATION_ID): cv.string
})

SCAN_INTERVAL = timedelta(seconds=300)
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=600)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=120)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    device_id = config.get(CONF_ID)
    location_id = config.get(CONF_LOCATION_ID)
    add_devices([gardena_smart(username, password, location_id, device_id)])


class gardena_smart(Entity):
    """Representation of a Sensor."""
    def __init__(self, username, password, location_id, device_id):
        """Initialize the sensor."""
        _LOGGER.info('Initializing...')
        from gardena_smart import Gardena
        self.gardena = Gardena(email_address=username, password=password)
        #Use first location
        _LOGGER.info('Current Location : ' + str(location_id))
        self.location_id = location_id
        if location_id is not None:
            self.devices = self.gardena.get_devices(locationID=location_id)
        else:
            self.devices = self.gardena.get_devices(locationID=self.gardena.locations[0][0])
        self.device_id = device_id
        self._state = None
        self._attributes = []
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attributes['name']

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ''

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.info('Returning current state...')
        _LOGGER.info('Current dev_id ' + str(self.device_id))
        if self.location_id is not None:
            self.devices = self.gardena.get_devices(locationID=self.location_id)
        else:
            self.devices = self.gardena.get_devices(locationID=self.gardena.locations[0][0])
            _LOGGER.info('Current devices ' + str(self.devices))
        if self.device_id is not None:
            mower_info = self.gardena.get_mower_info(self.device_id)
        else:
            _LOGGER.info("Sileno Using auto dev id: " + self.gardena.get_devices_in_catagory('mower')[0])
            mower_info = self.gardena.get_mower_info(self.gardena.get_devices_in_catagory('mower')[0])
        """_LOGGER.info('Sileno Device Info ID: ' + self.gardena.get_device_abilities('device_info')
        _LOGGER.info('Sileno Battery ID    : ' + self.gardena.get_device_abilities('battery')
        _LOGGER.info('Sileno Radio ID      : ' + self.gardena.get_device_abilities('radio')
        _LOGGER.info('Sileno Firmware ID   : ' + self.gardena.get_device_abilities('firmware')
        _LOGGER.info('Sileno Mower ID      : ' + self.gardena.get_device_abilities('mower')
        _LOGGER.info('Sileno Mower Stats ID: ' + self.gardena.get_device_abilities('mower_stats')
        _LOGGER.info('Sileno Mower Type ID : ' + self.gardena.get_device_abilities('mower_type')"""
        _LOGGER.info('Sileno State: ' + str(mower_info))
        self._state = json.dumps(mower_info['status'])
        self._attributes = mower_info

    @property
    def state_attributes(self):
        """Return the attributes of the entity.

           Provide the parsed JSON data (if any).
        """

        return self._attributes
