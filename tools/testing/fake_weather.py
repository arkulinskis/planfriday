"""A fake Open-Meteo for the tests and the dev server (no network): install(anvil.http.REPLIES).

Geocoding knows a few towns ("Montréal", "Paris", "Riga"); "Nowhere" has no results and "Offline" fails like a
dead service. The forecast is the same every week, so screenshots are stable:
Friday clear and crisp, Saturday rainy, Sunday partly cloudy and mild, other days overcast.
"""
import datetime as dt
import math

TOWNS = {"montreal": ("Montréal", "Quebec", "Canada", 45.5088, -73.5878), "montréal": ("Montréal", "Quebec", "Canada", 45.5088, -73.5878),
         "paris": ("Paris", "Île-de-France", "France", 48.8534, 2.3488), "riga": ("Riga", "Riga", "Latvia", 56.946, 24.1059)}
# weekday -> (code, base temp °C, chance of rain %, wind km/h)
DAYS = {4: (1, 11, 5, 9), 5: (63, 9, 80, 22), 6: (2, 15, 20, 12)}
FAIL = {"on": False}  # set FAIL["on"] = True to make the forecast fail


def geo(url, method, data):
    from urllib.parse import unquote
    name = unquote(url.split("name=")[1].split("&")[0]).strip().lower()
    if name == "offline":
        import anvil.http
        return anvil.http.HttpError(503, "down")
    t = TOWNS.get(name)
    if not t:
        return {"generationtime_ms": 0.2}
    return {"results": [{"name": t[0], "admin1": t[1], "country": t[2], "latitude": t[3], "longitude": t[4]}]}


def forecast(url, method, data):
    import anvil.http
    if FAIL["on"]:
        return anvil.http.HttpError(502, "bad gateway")
    start = dt.datetime.now(dt.timezone.utc).date()
    if start.weekday() >= 5:  # on Sat/Sun start at this weekend's Friday, so the tests pass on any day of the week
        start -= dt.timedelta(days=start.weekday() - 4)
    daily = {"time": [], "weather_code": [], "temperature_2m_max": [], "temperature_2m_min": [], "precipitation_probability_max": [], "sunset": []}
    hourly = {"time": [], "temperature_2m": [], "precipitation_probability": [], "weather_code": [], "wind_speed_10m": []}
    for i in range(16):
        d = start + dt.timedelta(days=i)
        code, base, rain, wind = DAYS.get(d.weekday(), (3, 10, 35, 15))
        temps = [round(base + 4 * math.sin((h - 9) / 24 * 2 * math.pi), 1) for h in range(24)]
        daily["time"].append(d.isoformat())
        daily["weather_code"].append(code)
        daily["temperature_2m_max"].append(max(temps))
        daily["temperature_2m_min"].append(min(temps))
        daily["precipitation_probability_max"].append(rain)
        daily["sunset"].append(d.isoformat() + "T17:52")
        for h in range(24):
            hourly["time"].append("%sT%02d:00" % (d.isoformat(), h))
            hourly["temperature_2m"].append(temps[h])
            hourly["precipitation_probability"].append(rain if 8 <= h <= 22 else max(0, rain - 20))
            hourly["weather_code"].append(code if code not in (0, 1) or 7 <= h <= 18 else 0)
            hourly["wind_speed_10m"].append(wind)
    return {"timezone": "America/Toronto", "daily": daily, "hourly": hourly}


def install(replies):
    replies["https://geocoding-api.open-meteo.com/"] = geo
    replies["https://api.open-meteo.com/"] = forecast
