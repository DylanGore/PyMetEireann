'''Library to handle communications with the Met Éireann forecast and weather warning APIs.'''
import asyncio
import datetime
import logging
from xml.parsers.expat import ExpatError

import aiohttp
import async_timeout
import pytz
import xmltodict

API_URL = 'http://metwdb-openaccess.ichec.ie/metno-wdb2ts/locationforecast'
WARNING_API_URL = 'https://www.met.ie/Open_Data/json/warning_'

# Map each region code to a region name
REGION_MAP = {
    # Counties
    'EI01': 'Carlow',
    'EI02': 'Cavan',
    'EI03': 'Clare',
    'EI04': 'Cork',
    'EI06': 'Donegal',
    'EI07': 'Dublin',
    'EI10': 'Galway',
    'EI11': 'Kerry',
    'EI12': 'Kildare',
    'EI13': 'Kilkenny',
    'EI15': 'Laois',
    'EI14': 'Leitrim',
    'EI16': 'Limerick',
    'EI18': 'Longford',
    'EI19': 'Louth',
    'EI20': 'Mayo',
    'EI21': 'Meath',
    'EI22': 'Monaghan',
    'EI23': 'Offaly',
    'EI24': 'Roscommon',
    'EI25': 'Sligo',
    'EI26': 'Tipperary',
    'EI27': 'Waterford',
    'EI29': 'Westmeath',
    'EI30': 'Wexford',
    'EI31': 'Wicklow',
    # Marine
    'EI805': 'Malin-Fair',
    'EI806': 'Fair-Belfast',
    'EI807': 'Belfast-Strang',
    'EI808': 'Strang-Carl',
    'EI809': 'Carling-Howth',
    'EI810': 'Howth-Wicklow',
    'EI811': 'Wicklow-Carns',
    'EI812': 'Carns-Hook',
    'EI813': 'Hook-Dungarvan',
    'EI814': 'Dungarvan-Roches',
    'EI815': 'Roches-Mizen',
    'EI816': 'Mizen-Valentia',
    'EI817': 'Valentia-Loop',
    'EI818': 'Loop-Slayne',
    'EI819': 'Slayne-Ennis',
    'EI820': 'Erris-Rossan',
    'EI821': 'Rossan-BloodyF',
    'EI822': 'BloodyF-Malin',
    'EI823': 'IrishSea-South',
    'EI824': 'IrishSea-IOM-S',
    'EI825': 'IrishSea-IOM-N'
}

_LOGGER = logging.getLogger(__name__)


class WarningData:
    '''Representation of Met Éireann warning data.'''

    def __init__(self, websession=None, api_url=WARNING_API_URL, region='Ireland',
                 convert_to_utc=True, ignore_blight=True):
        '''Initialize the warning object.'''
        # pylint: disable=too-many-arguments

        # Set the various option variables
        self._ignore_blight = ignore_blight
        self._convert_to_utc = convert_to_utc

        # Convert region name to region code (if applicable)
        if not region.upper().startswith('EI') and region.upper() != 'IRELAND':
            keys = [k for k, v in REGION_MAP.items() if v == region]
            self._region = keys[0].upper()
        else:
            self._region = region.upper()

        # Set the API URL to include the required region
        self._api_url = f'{api_url}{self._region}.json'

        # Create a new session if one isn't passed in
        if websession is None:
            async def _create_session():
                self.created_session = True
                return aiohttp.ClientSession()

            loop = asyncio.get_event_loop()
            self._websession = loop.run_until_complete(_create_session())
        else:
            self._websession = websession
            self.created_session = False
        self.data = None

    async def fetching_data(self, *_):
        '''Get the latest data from the warning API'''
        try:
            with async_timeout.timeout(10):
                res = await self._websession.get(self._api_url)
            # Log any 400+ HTTP error codes
            if res.status >= 400:
                _LOGGER.error('%s returned %s', self._api_url, res.status)
                return False
            json = await res.json()
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error('%s returned %s', self._api_url, err)
            return False
        try:
            self.data = {
                'count': len(json),
                'warnings': json
            }
        except (ExpatError, IndexError) as err:
            _LOGGER.error('%s returned %s', res.url, err)
            return False
        return True

    def get_warnings(self):
        '''Get the latest warnings from Met Éireann.'''
        if self.data is None:
            return {'count': 0, 'warnings': []}

        # Update the timestamps to datetime objects (and to UTC if required)
        for entry in self.data['warnings']:
            entry['issued'] = format_warning_date(entry['issued'], self._convert_to_utc)
            entry['updated'] = format_warning_date(entry['updated'], self._convert_to_utc)
            entry['onset'] = format_warning_date(entry['onset'], self._convert_to_utc)
            entry['expiry'] = format_warning_date(entry['expiry'], self._convert_to_utc)

        # Remove blight warnings from the list if required
        if self._ignore_blight:
            new_warnings_list = []
            for entry in self.data['warnings']:
                if entry['type'].lower() != 'blight':
                    new_warnings_list.append(entry)
            return {'count': len(new_warnings_list), 'warnings': new_warnings_list}

        return self.data

    async def close_session(self):
        '''Close a session if the user did not pass one in.'''
        if self.created_session:
            await self._websession.close()
            _LOGGER.debug('Closed session (Warnings)')
        else:
            _LOGGER.warning('Cannot close an external session')


class WeatherData:
    '''Representation of Met Éireann weather data.'''

    def __init__(self, websession=None, api_url=API_URL, latitude=54.7210798611, longitude=-8.7237392806, altitude=0):
        '''Initialize the weather object.'''
        # pylint: disable=too-many-arguments

        # Store the forecast parameters
        self._api_url = f'{api_url}?lat={latitude};long={longitude};alt={altitude}'

        # Create a new session if one isn't passed in
        if websession is None:
            async def _create_session():
                self.created_session = True
                return aiohttp.ClientSession()

            loop = asyncio.get_event_loop()
            self._websession = loop.run_until_complete(_create_session())
        else:
            self._websession = websession
            self.created_session = False
        self.data = None

    async def fetching_data(self, *_):
        '''Get the latest data from the API'''
        try:
            with async_timeout.timeout(10):
                resp = await self._websession.get(self._api_url)
            # Log any 400+ HTTP error codes
            if resp.status >= 400:
                _LOGGER.error('%s returned %s', self._api_url, resp.status)
                return False
            text = await resp.text()
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error('%s returned %s', self._api_url, err)
            return False
        try:
            self.data = xmltodict.parse(text)['weatherdata']
        except (ExpatError, IndexError) as err:
            _LOGGER.error('%s returned %s', resp.url, err)
            return False
        return True

    def get_current_weather(self):
        '''Get the current weather data from Met Éireann.'''
        return self.get_weather(datetime.datetime.now(pytz.utc))

    def get_forecast(self, time_zone, hourly=False):
        '''Get the forecast weather data from Met Éireann.'''
        if self.data is None:
            return []

        if hourly:
            now = datetime.datetime.now(time_zone).replace(
                minute=0, second=0, microsecond=0
            )
            times = [now + datetime.timedelta(hours=k) for k in range(1, 25)]
        else:
            now = datetime.datetime.now(time_zone).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
            times = [now + datetime.timedelta(days=k) for k in range(1, 6)]
        return [self.get_weather(_time, hourly=hourly) for _time in times]

    def get_weather(self, time, max_hour=6, hourly=False):
        '''Get the current weather data from Met Éireann.'''
        # pylint: disable=too-many-locals
        if self.data is None:
            return {}

        day = time.date()
        daily_temperatures = []
        daily_precipitation = []
        daily_windspeed = []
        daily_windgust = []
        ordered_entries = []
        for time_entry in self.data['product']['time']:
            valid_from = parse_datetime(time_entry['@from'])
            valid_to = parse_datetime(time_entry['@to'])
            if time > valid_to:
                # Has already passed. Never select this.
                continue

            # Collect all daily values to calculate min/max/sum
            if valid_from.date() == day or valid_to.date() == day:

                if 'temperature' in time_entry['location']:
                    daily_temperatures.append(
                        get_value(time_entry['location']['temperature'], '@value')
                    )
                if 'precipitation' in time_entry['location']:
                    daily_precipitation.append(
                        get_value(time_entry['location']['precipitation'], '@value')
                    )
                if 'windSpeed' in time_entry['location']:
                    daily_windspeed.append(
                        get_value(time_entry['location']['windSpeed'], '@mps')
                    )
                if 'windGust' in time_entry['location']:
                    daily_windgust.append(
                        get_value(time_entry['location']['windGust'], '@mps')
                    )

            average_dist = abs((valid_to - time).total_seconds()) + abs(
                (valid_from - time).total_seconds()
            )

            if average_dist > max_hour * 3600:
                continue

            ordered_entries.append((average_dist, time_entry))

        if not ordered_entries:
            return {}
        ordered_entries.sort(key=lambda item: item[0])
        res = dict()
        res['datetime'] = time
        res['condition'] = get_data('symbol', ordered_entries)
        res['pressure'] = get_data('pressure', ordered_entries)
        res['humidity'] = get_data('humidity', ordered_entries)
        res['wind_bearing'] = get_data('windDirection', ordered_entries)
        if hourly:
            res['temperature'] = get_data('temperature', ordered_entries)
            res['precipitation'] = get_data('precipitation', ordered_entries)
            res['wind_speed'] = get_data('windSpeed', ordered_entries)
            res['wind_gust'] = get_data('windGust', ordered_entries)
            res['cloudiness'] = get_data('cloudiness', ordered_entries)
        else:
            res['temperature'] = (
                None if daily_temperatures == [] else max(daily_temperatures)
            )
            res['templow'] = (
                None if daily_temperatures == [] else min(daily_temperatures)
            )
            res['precipitation'] = (
                None if daily_precipitation == [] else round(sum(daily_precipitation), 1)
            )
            res['wind_speed'] = (
                None if daily_windspeed == [] else max(daily_windspeed)
            )
            res['wind_gust'] = (
                None if daily_windgust == [] else max(daily_windgust)
            )
        return res

    async def close_session(self):
        '''Close a session if the user did not pass one in'''
        if self.created_session:
            await self._websession.close()
            _LOGGER.debug('Closed session (Forecast)')
        else:
            _LOGGER.warning('Cannot close an external session')


def get_value(data, value):
    '''Retrieve weather value.'''
    try:
        if value == '@mps':
            return round(float(data[value]) * 3.6, 1)
        return round(float(data[value]), 1)
    except (ValueError, IndexError, KeyError):
        return None


def get_data(param, data):
    '''Retrieve weather parameter.'''
    try:
        for (_, selected_time_entry) in data:
            loc_data = selected_time_entry['location']
            if param not in loc_data:
                continue
            if param == 'symbol':
                new_state = loc_data[param]['@id']
            elif param in (
                    'temperature',
                    'pressure',
                    'humidity',
                    'dewpointTemperature',
                    'precipitation',
            ):
                new_state = get_value(loc_data[param], '@value')
            elif param in ('windSpeed', 'windGust'):
                new_state = get_value(loc_data[param], '@mps')
            elif param == 'windDirection':
                new_state = get_value(loc_data[param], '@deg')
            elif param in (
                    'fog',
                    'cloudiness',
                    'lowClouds',
                    'mediumClouds',
                    'highClouds',
            ):
                new_state = get_value(loc_data[param], '@percent')
            return new_state
    except (ValueError, IndexError, KeyError):
        return None


def parse_datetime(dt_str):
    '''Parse datetime for forecast data.'''
    date_format = '%Y-%m-%dT%H:%M:%S %z'
    dt_str = dt_str.replace('Z', ' +0000')
    return datetime.datetime.strptime(dt_str, date_format)


def format_warning_date(date_str, convert_to_utc=False):
    '''Convert a timestamp string to datetime and convert to UTC if required.'''
    date_format = '%Y-%m-%dT%H:%M:%S%z'
    new_timestamp = datetime.datetime.strptime(date_str, date_format)
    # Convert the datetime object to UTC if required
    if convert_to_utc:
        return new_timestamp.astimezone(tz=datetime.timezone.utc)
    # Return just the datetime object if UTC isn't required
    return new_timestamp
