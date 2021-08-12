import meteireann
import asyncio
import datetime

weather_data = meteireann.WeatherData()
warning_data = meteireann.WarningData()


async def fetch_data():
    """Fetch data from API - (current weather and forecast)."""
    await weather_data.fetching_data()
    current_weather_data = weather_data.get_current_weather()
    print('current:', current_weather_data)

    await warning_data.fetching_data()
    current_warning_data = warning_data.get_warnings()
    print('warnings:', current_warning_data)

    time_zone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    daily_forecast = weather_data.get_forecast(time_zone, False)
    print('daily:', daily_forecast)
    hourly_forecast = weather_data.get_forecast(time_zone, True)
    print('hourly:', hourly_forecast)
    return True


async def main():
    await fetch_data()
    await weather_data.close_session()
    await warning_data.close_session()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
