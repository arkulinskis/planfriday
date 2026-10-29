"""Weather check: forecasts from Open-Meteo (open-meteo.com: free, no key; data CC BY 4.0, credited on the page).

The host types a town on the party form; geocode() looks it up once and the party keeps the place name and its
coordinates (wx_place, wx_lat, wx_lon). The server fetches the forecast (so guests' browsers never talk to
Open-Meteo) and caches it on the party (parties.weather) for an hour: 16 days of hourly temperature, chance of rain,
weather code and wind, plus a daily summary. for_party() turns that into one forecast per party slot, at the slot's
time (or the time the host locked in). If Open-Meteo doesn't answer, the old forecast is kept and we retry in 10 minutes.
"""
import datetime as dt

import anvil.http
import anvil.server

from . import common as C

GEO = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
HOURS = {"brunch": 10, "lunch": 12, "afternoon": 15, "dinner": 19, "late": 21}
FRESH, RETRY = 3600, 600


class Unavailable(Exception):
    """Open-Meteo didn't answer (or answered nonsense)."""


def _get(url):
    try:
        return anvil.http.request(url, json=True, timeout=8)
    except Exception as e:
        raise Unavailable(str(e))


def geocode(query):
    """{place, lat, lon} for a town name, None if there's no such place. Raises Unavailable."""
    q = C.text(query, 80).split(",")[0].strip()  # the geocoder wants a bare name: "Montréal", not "Montréal, QC"
    if len(q) < 2:
        return None
    r = _get(GEO + "?count=1&language=en&format=json&name=" + anvil.http.url_encode(q))
    res = (r or {}).get("results") or [] if isinstance(r, dict) else []
    if not res:
        return None
    x = res[0]
    parts = []
    for v in (x.get("name"), x.get("admin1"), x.get("country")):
        if v and v not in parts:
            parts.append(v)
    try:
        return {"place": ", ".join(parts)[:120], "lat": round(float(x["latitude"]), 4), "lon": round(float(x["longitude"]), 4)}
    except (KeyError, TypeError, ValueError):
        return None


def fetch(lat, lon):
    """The next 16 days as {date: {code, tmax, tmin, rain, sunset, hours: {"19": [temp, rain %, code, wind km/h]}}}."""
    r = _get(FORECAST + "?latitude=%s&longitude=%s&timezone=auto&forecast_days=16"
             "&hourly=temperature_2m,precipitation_probability,weather_code,wind_speed_10m"
             "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunset" % (lat, lon))
    try:
        days = {}
        d = r["daily"]
        for i, date in enumerate(d["time"]):
            days[date] = {"code": d["weather_code"][i], "tmax": d["temperature_2m_max"][i], "tmin": d["temperature_2m_min"][i],
                          "rain": d["precipitation_probability_max"][i], "sunset": (d.get("sunset") or [None] * (i + 1))[i], "hours": {}}
        h = r["hourly"]
        for i, stamp in enumerate(h["time"]):
            date, hour = stamp[:10], str(int(stamp[11:13]))
            if date in days:
                days[date]["hours"][hour] = [h["temperature_2m"][i], h["precipitation_probability"][i], h["weather_code"][i],
                                             h["wind_speed_10m"][i]]
        return days
    except (KeyError, TypeError, IndexError, ValueError) as e:
        raise Unavailable("odd forecast: %r" % e)


def _cache(p, refresh=True):
    """The party's cached forecast, refreshed when it's old (and refresh is allowed)."""
    if p["wx_lat"] is None or p["wx_lon"] is None:
        return None
    cache = p["weather"] or {}
    same = cache.get("lat") == p["wx_lat"] and cache.get("lon") == p["wx_lon"]
    age = (C.now() - dt.datetime.fromisoformat(cache["at"])).total_seconds() if cache.get("at") else None
    if refresh and (not same or age is None or age > (RETRY if cache.get("failed") else FRESH)):
        try:
            cache = {"at": C.now().isoformat(), "lat": p["wx_lat"], "lon": p["wx_lon"], "days": fetch(p["wx_lat"], p["wx_lon"])}
        except Unavailable as e:
            print("weather for %s failed: %s" % (p["token"], e))
            cache = {"at": C.now().isoformat(), "lat": p["wx_lat"], "lon": p["wx_lon"], "failed": True,
                     "days": cache.get("days") if same else {}}
        p["weather"] = cache
    return cache if same or refresh else None


def slot_forecast(p, key, cache):
    date, part = key.split("|", 1)
    day = ((cache or {}).get("days") or {}).get(date)
    if not day:
        return None
    hour = HOURS.get(part, 19)
    if key == p["chosen"] and p["chosen_time"]:
        hour = int(p["chosen_time"][:2])
    hours = day.get("hours") or {}
    h = hours.get(str(hour))
    if h is None and hours:
        h = hours[min(hours, key=lambda x: abs(int(x) - hour))]
    if h is None:
        return None
    return {"temp": h[0], "rain": h[1], "code": h[2], "wind": h[3], "tmax": day.get("tmax"), "tmin": day.get("tmin"),
            "day_rain": day.get("rain"), "hour": hour, "sunset": day.get("sunset")}


def for_party(p, refresh=True):
    """The weather check for a party page: the place, and a forecast for each slot that's within range."""
    if p["wx_lat"] is None:
        return None
    cache = _cache(p, refresh)
    slots = {}
    for k in p["slots"] or []:
        f = slot_forecast(p, k, cache)
        if f:
            slots[k] = f
    return {"place": p["wx_place"], "outdoors": bool(p["outdoors"]), "slots": slots,
            "updated": (cache or {}).get("at"), "ok": not (cache or {}).get("failed")}


@anvil.server.callable(require_user=True)
def weather_lookup(query):
    """Check a town for the party form ("Found: Montréal, Quebec, Canada")."""
    C.require_user()
    if C.rate_limited("weather_lookup", 30, 3600):
        return C.fail("That's a lot of look-ups. Please try again in a while.")
    try:
        g = geocode(query)
    except Unavailable:
        return C.fail("The weather service didn't answer. Try again in a minute.")
    if g is None:
        return C.fail("We couldn't find that town. Try just the town name, or a nearby city.")
    return C.ok(place=g["place"])
