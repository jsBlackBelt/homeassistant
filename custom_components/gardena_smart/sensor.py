import logging
import json
import requests
import os
from datetime import datetime, timedelta
import pickle

import voluptuous as vol

import homeassistant.util as util
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

#REQUIREMENTS = ['gardena-smart==0.11b2']

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

#def setup(hass, config, add_devices, discovery_info=None):
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
        #from gardena_smart import Gardena
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

class Gardena(object):
    """Class to take care of cummunication with Gardena Smart system"""
    def __init__(self, email_address=None, password=None, device_id=None):
        if email_address ==None or password==None:
            raise ValueError('Please provice, email, password')
        self.debug=True
        self.s = requests.session()
        self.email_address = email_address
        self.password = password
        self.device_id = device_id
        self.update()
    def update(self):
        self.update_authtokens()
        self.get_locations()
    def update_authtokens(self):
        """Get authentication token from servers"""
        data = '{"sessions":{"email":"' + self.email_address + '","password":"' + self.password + '"}}'
        url = 'https://smart.gardena.com/sg-1/sessions'
        headers = self.create_header()
        response = self.s.post(url, headers=headers, data=data)
        response_data = json.loads(response.content.decode('utf-8'))
        self.AuthToken = response_data['sessions']['token']
        self.refreshToken = response_data['sessions']['refresh_token']
        self.userID = response_data['sessions']['user_id']
    def get_locations(self):
        url = "https://smart.gardena.com/sg-1/locations/"
        params = (
            ('user_id', self.userID),
        )
        headers = self.create_header(Token=self.AuthToken)
        response = self.s.get(url, headers=headers, params=params)
        response_data = json.loads(response.content.decode('utf-8'))
        self.raw_locations_resp = response
        self.raw_locations = response_data
        self.locations = [(i['id'],i['name']) for i in response_data['locations']]
    def get_devices(self, locationID):
        url = "https://smart.gardena.com/sg-1/devices"
        params = (
            ('locationId', locationID),
        )
        headers = self.create_header(Token=self.AuthToken)
        response = self.s.get(url, headers=headers, params=params)
        response_data = json.loads(response.content.decode('utf-8'))
        self.raw_devices = response_data
        device_info = {}
        for i in self.raw_devices['devices']:
            device_info[i['id']]=i
        self.device_info = device_info

    def get_properties_from_abilities(self, json_object, ability):
        _LOGGER.info('Parsing 1 - ability: ' + ability)
        for mlist in json_object:
            _LOGGER.info('Parsing 1 - ability list: ' + mlist)
            for dict in mlist:
                _LOGGER.info('Parsing for 1 - ability list element: ' + dict)
                if dict['name'] == ability:
                    return dict
    def get_value_from_property(self, json_object, property1, property2):
        pickle.dump(json_object, open("json_object.json", wb))

        _LOGGER.info('Parsing for 2 : ' + property1)
        for mylist in json_object['abilities']:
            if mylist['name'] == property1:
               for mylist2 in mylist:
                   if mylist2['name'] == property2:
                       _LOGGER.info('Result 2 b: ' + mylist2['value'])
                       return mylist2['value']

#        for dict in json_object:
#            if dict["name"] == property:
#                _LOGGER.info('Result 2 : ' + dict['value'])
#                return dict['value']
    def get_devices_in_catagory(self, category):
        """Return devices matching a category, should be mower, gateway, sensor """
        return [i['id'] for i in self.raw_devices['devices']  if i['category']==category]
    def get_mower_name(self, id):
        return self.device_info[id]['name']
    def get_mower_device_state(self, id):
        return self.device_info[id]['device_state']
    def get_mower_last_online(self, id):
        return self.device_info[id]['abilities'][0]['properties'][5]['value']
    def get_mower_battery_level(self, id):
        return self.get_value_from_property(self.device_info[id], 'battery', 'level')
#        return self.get_value_from_property(self.get_properties_from_abilities(self.device_info[id], 'mower'), 'battery')
#        return self.device_info[id]['abilities'][1]['properties'][0]['value']
    def get_mower_charging_status(self, id):
        return self.device_info[id]['abilities'][1]['properties'][1]['value']
    def get_mower_radio_quality(self, id):
        return self.device_info[id]['abilities'][2]['properties'][0]['value']
    def get_mower_radio_status(self, id):
        return self.device_info[id]['abilities'][2]['properties'][2]['value']
    def get_mower_radio_connection_status(self, id):
        return self.device_info[id]['abilities'][2]['properties'][1]['value']
    def get_mower_manual_mode(self, id):
        return self.device_info[id]['abilities'][3]['properties'][0]['value']
    def get_mower_status(self, id):
        return self.device_info[id]['abilities'][3]['properties'][1]['value']
    def get_mower_error(self, id):
        """Return error and last ts"""
        error = self.device_info[id]['abilities'][3]['properties']
#        return (error[2]['value'], error[7]['value'])
        return (error[2]['value'], "")
    def get_mower_last_error(self, id):
        return self.device_info[id]['abilities'][3]['properties'][3]['value']
    def get_mower_next_source_start(self, id):
        return self.device_info[id]['abilities'][3]['properties'][4]['value']
    def get_mower_next_start(self, id):
        return self.device_info[id]['abilities'][3]['properties'][5]['value']
    def get_mower_cutting_time(self, id):
        return self.device_info[id]['abilities'][4]['properties'][0]['value']
    def get_mower_charging_cycles(self, id):
        return self.device_info[id]['abilities'][4]['properties'][1]['value']
    def get_mower_collisions(self, id):
        return self.device_info[id]['abilities'][4]['properties'][2]['value']
    def get_mower_running_time(self, id):
        return self.device_info[id]['abilities'][4]['properties'][3]['value']
    def get_mower_info(self, id):
        mower_info = {}
        mower_info['name'] = self.get_mower_name(id)
        mower_info['dev_state'] = self.get_mower_device_state(id)
#        mower_info['last_online'] = self.convert_python_dt(self.get_mower_last_online(id))
        mower_info['battery_level']  = self.get_mower_battery_level(id)
#        mower_info['charging_satus'] = self.get_mower_charging_status(id)
#        mower_info['radio_quality'] = self.get_mower_radio_quality(id)
#        mower_info['radio_status'] = self.get_mower_radio_status(id)
#        mower_info['radio_connection_status'] = self.get_mower_radio_connection_status(id)
#        mower_info['in_manual_mode'] = self.get_mower_manual_mode(id)
#        mower_info['status'] = self.get_mower_status(id)
#        mower_info['error'] = self.get_mower_error(id)[0]
#        mower_info['error_time'] = self.convert_python_dt(self.get_mower_error(id)[1])
#        mower_info['last_error_msg'] = self.get_mower_last_error(id)
#        mower_info['next_source_for_start']=self.get_mower_next_source_start(id)
#        mower_info['next_start'] = self.convert_python_dt(self.get_mower_next_start(id))
#        mower_info['cutting_time'] = self.get_mower_cutting_time(id)
#        mower_info['charge_cycles'] = self.get_mower_charging_cycles(id)
#        mower_info['collisions'] = self.get_mower_collisions(id)
#        mower_info['running_time'] = self.get_mower_running_time(id)
        return mower_info
    def create_header(self, Token=None, ETag=None):
        headers={
        'Content-Type': 'application/json',
        }
        if Token is not None:
            headers['X-Session']=Token
        if ETag is not None:
            headers['If-None-Match'] = ETag
        return headers
    def convert_python_dt(self, dt_str):
        from dateutil import tz
        import datetime as dt
        from_zone = tz.tzutc()
        to_zone = tz.tzlocal()
        #We have different formats:
#        if len(dt_str) == 24:
#            assert dt_str[-1] == 'Z'
#            dt_str = dt_str[:-1] + '000UTC'
#            gardena_dt = dt.datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f%Z')
#        elif len(dt_str) == 20:
#            assert dt_str[-1] == 'Z'
#            dt_str = dt_str[:-1] + 'UTC'
#            gardena_dt = dt.datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S%Z')
#        elif len(dt_str) == 17:
#            assert dt_str[-1] == 'Z'
#            dt_str = dt_str[:-1] + 'UTC'
#            gardena_dt = dt.datetime.strptime(dt_str, '%Y-%m-%dT%H:%M%Z')
#        else:
#            raise ValueError('Invalid date format : ' + dt_str)
#        utc_dt = gardena_dt.replace(tzinfo=from_zone)
#        local_dt = utc_dt.astimezone(to_zone)
#        return local_dt
        return dt_str
    def debug_print(self, string):
        if self.debug:
            print(string)
