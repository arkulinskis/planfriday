"""Plan Friday's own toolkit (was window.PF in web/pages/_shared.html): the catalogue of party ideas, weekend dates
and slots, diets and dish tags, dish ideas, sharing and calendar links, the weather words, the parties seen on this
device. The drawing (party pictures, weather icons) and the browser bits (clipboard, downloads, share sheet,
confetti) are JavaScript in theme/assets/pf.js; this module is the only place that calls it.

Dates are the browser's local calendar days (a party's slots are "YYYY-MM-DD|part"). The server keeps the same
lists for checking: PARTS in Guests.py, COVERS in Parties.py, DIETS/TAGS/NUT_WORDS in Guests.py.
"""
import datetime
import json

import anvil.js
from anvil.js import window

# ------------------------------------------------------------------ pictures (pf.js ART)
COVERS = [("classic", "Casserole"), ("soup", "Soup pot"), ("pancakes", "Pancakes"), ("dumplings", "Dumplings"),
          ("tacos", "Tacos"), ("fondue", "Fondue"), ("pizza", "Pizza"), ("roast", "Roast"), ("salad", "Salad bowl"),
          ("pie", "Pie"), ("wine", "Wine"), ("bbq", "Grill"), ("cake", "Cake")]
COVER_NAMES = dict(COVERS)


def art(cover, label=None):
    """The SVG of a party picture. label None = its usual name; "" = decorative."""
    if label is None:
        label = COVER_NAMES.get(cover, "A dish")
    return window.PF.art(cover or "classic", label)


# ------------------------------------------------------------------ the catalogue of party ideas
# slots: [(day 0 Fri / 1 Sat / 2 Sun, part)]; menu: [(section, how many wanted)]
IDEAS: list = [
    {"key": "soupnight", "no": "12F 4108", "name": "Soup Night Supper", "cover": "soup", "tags": ["cosy"], "serves": "6–12", "effort": 1, "style": "potluck",
     "blurb": "Everyone brings a pot. The host does bread and bowls. The coziest potluck there is, and it reheats beautifully.",
     "slots": [(0, "dinner"), (1, "dinner"), (2, "lunch")], "menu": [("Soup", 3), ("Bread", 2), ("Salad", 1), ("Dessert", 2), ("Drinks", 2)]},
    {"key": "pancakes", "no": "31P 2275", "name": "Sunday Pancake Brunch", "cover": "pancakes", "tags": ["brunch"], "serves": "4–10", "effort": 2, "style": "hostcooks",
     "blurb": "You flip, they bring the toppings. Maple, berries, whipped butter, and a very large pot of coffee.",
     "slots": [(1, "brunch"), (2, "brunch")], "menu": [("Toppings", 3), ("Fruit", 1), ("Coffee & juice", 2)]},
    {"key": "dumplings", "no": "57K 9031", "name": "Dumpling Folding Party", "cover": "dumplings", "tags": ["handson"], "serves": "4–8", "effort": 3, "style": "potluck",
     "blurb": "Dough on the table, fillings in bowls, everyone folds. Ugly dumplings taste exactly the same.",
     "slots": [(0, "late"), (1, "afternoon"), (1, "dinner")], "menu": [("Fillings", 2), ("Dipping sauces", 2), ("Sides", 1), ("Drinks", 2), ("Dessert", 1)]},
    {"key": "tacos", "no": "22T 6610", "name": "Taco Saturday", "cover": "tacos", "tags": ["crowd"], "serves": "6–16", "effort": 1, "style": "potluck",
     "blurb": "Tortillas from the host, a salsa from everyone else. Build-your-own means nobody is fussy.",
     "slots": [(0, "dinner"), (1, "dinner")], "menu": [("Fillings", 2), ("Salsas", 3), ("Toppings", 2), ("Sides", 1), ("Drinks", 2), ("Dessert", 1)]},
    {"key": "fondue", "no": "40F 1955", "name": "Fondue & Fiasco", "cover": "fondue", "tags": ["cosy"], "serves": "4–6", "effort": 2, "style": "hostcooks",
     "blurb": "One pot of melted cheese, a dozen forks, and the old rule: drop your bread, you do the dishes.",
     "slots": [(0, "dinner"), (1, "dinner")], "menu": [("Dippers", 3), ("Salad", 1), ("Wine", 2), ("Dessert", 1)]},
    {"key": "pizza", "no": "18R 3030", "name": "Pizza Dough Workshop", "cover": "pizza", "tags": ["handson", "crowd"], "serves": "6–12", "effort": 2, "style": "potluck",
     "blurb": "The host makes the dough the night before. Guests bring toppings. The oven never rests.",
     "slots": [(1, "afternoon"), (1, "dinner"), (2, "lunch")], "menu": [("Toppings", 4), ("Salad", 1), ("Drinks", 2), ("Dessert", 1)]},
    {"key": "roast", "no": "09W 7744", "name": "The Sunday Roast", "cover": "roast", "tags": ["cosy"], "serves": "6–10", "effort": 3, "style": "hostcooks",
     "blurb": "A proper roast from the host. Guests cover the sides, the gravy and the pudding. Seconds compulsory.",
     "slots": [(2, "lunch"), (2, "dinner")], "menu": [("Sides", 3), ("Gravy & sauces", 1), ("Dessert", 1), ("Wine", 2)]},
    {"key": "garden", "no": "64P 1212", "name": "Garden Potluck Picnic", "cover": "salad", "tags": ["outdoor", "crowd"], "serves": "8–20", "effort": 1, "style": "potluck",
     "blurb": "Blankets, big salads and something cold to drink. Rain plan: everyone squeezes into the kitchen.",
     "slots": [(1, "lunch"), (1, "afternoon"), (2, "lunch"), (2, "afternoon")], "menu": [("Salads", 2), ("Mains", 2), ("Sides", 2), ("Dessert", 2), ("Drinks", 2), ("Supplies", 1)]},
    {"key": "pie", "no": "33R 3141", "name": "The Pie Social", "cover": "pie", "tags": ["crowd"], "serves": "8–20", "effort": 2, "style": "potluck",
     "blurb": "Savoury, sweet, store-bought and proud. Everyone brings a pie, everyone goes home with a slice of six.",
     "slots": [(1, "afternoon"), (2, "afternoon")], "menu": [("Savoury pies", 2), ("Sweet pies", 3), ("Ice cream", 1), ("Drinks", 1)]},
    {"key": "grill", "no": "71K 4040", "name": "Backyard Grill-Out", "cover": "bbq", "tags": ["outdoor", "crowd"], "serves": "8–20", "effort": 2, "style": "potluck",
     "blurb": "Light the grill at five. Bring something to throw on it, and something to drink while it cooks.",
     "slots": [(0, "dinner"), (1, "afternoon"), (1, "dinner")], "menu": [("For the grill", 3), ("Sides", 3), ("Buns & bread", 1), ("Drinks", 3), ("Dessert", 1), ("Ice", 1)]},
    {"key": "cheese", "no": "45T 0808", "name": "Cheese & Wine Evening", "cover": "wine", "tags": ["cosy"], "serves": "4–12", "effort": 1, "style": "byob",
     "blurb": "No cooking at all. Everyone brings a cheese and a bottle, and you argue about which is best.",
     "slots": [(0, "dinner"), (0, "late"), (1, "late")], "menu": [("Cheese", 3), ("Crackers & bread", 2), ("Wine", 4), ("Fruit & pickles", 1)]},
    {"key": "birthday", "no": "26W 0101", "name": "Birthday Dinner", "cover": "cake", "tags": ["crowd"], "serves": "6–14", "effort": 2, "style": "potluck",
     "blurb": "A potluck with a purpose. One cake, many candles, and a menu that comes together by itself.",
     "slots": [(0, "dinner"), (1, "dinner")], "menu": [("Starters", 1), ("Mains", 2), ("Sides", 2), ("Cake", 1), ("Drinks", 2)]},
    {"key": "classic", "no": "01F 0001", "name": "The Classic Potluck", "cover": "classic", "tags": ["crowd"], "serves": "Any", "effort": 1, "style": "potluck",
     "blurb": "The original. A little of everything: starter, soup, salad, main, sides, dessert and drinks.",
     "slots": [(0, "dinner"), (1, "dinner"), (2, "lunch")], "menu": [("Starters", 1), ("Soup", 1), ("Salad", 1), ("Mains", 2), ("Sides", 2), ("Dessert", 2), ("Drinks", 2)]},
]
TAGS = [("cosy", "Cosy"), ("brunch", "Brunch"), ("handson", "Hands-on"), ("crowd", "Big crowd"), ("outdoor", "Outdoors")]
TAG_NAMES = dict(TAGS)
STYLES = [("potluck", "Potluck", "Everyone brings a dish"), ("hostcooks", "Host cooks", "The host cooks; guests bring extras"),
          ("byob", "Bring your own", "No cooking: everyone brings their own")]
STYLE_NAMES = {k: n for k, n, _ in STYLES}


def idea(key):
    for i in IDEAS:
        if i["key"] == key:
            return i
    return None


def effort(n):
    return "★★★"[:n] + "☆☆☆"[:3 - n]


# ------------------------------------------------------------------ weekend dates and slots
PARTS = {"brunch": ("Brunch", "10:30"), "lunch": ("Lunch", "12:30"), "afternoon": ("Afternoon", "15:00"),
         "dinner": ("Dinner", "19:00"), "late": ("Late supper", "21:30")}
DAY_PARTS = [["dinner", "late"], ["brunch", "lunch", "afternoon", "dinner", "late"], ["brunch", "lunch", "afternoon", "dinner"]]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def today():
    return datetime.date.today()


def iso(d):
    return "%04d-%02d-%02d" % (d.year, d.month, d.day)


def parse(s):
    y, m, d = str(s)[:10].split("-")
    return datetime.date(int(y), int(m), int(d))


def add_days(d, n):
    return d + datetime.timedelta(days=n)


def friday(weeks=0, frm=None):
    """The Friday of this weekend (Fri/Sat/Sun) or the coming one, plus `weeks`."""
    t = frm or today()
    wd = t.weekday()  # Mon 0 ... Fri 4, Sat 5, Sun 6
    off = {4: 0, 5: -1, 6: -2}.get(wd, 4 - wd)
    return add_days(t, off + 7 * (weeks or 0))


def slot(key):
    """'2026-11-07|dinner' -> (date, 'dinner')."""
    a = str(key).split("|")
    return parse(a[0]), (a[1] if len(a) > 1 else "")


def slot_key(fri, day, part):
    return iso(add_days(fri, day)) + "|" + part


def part_label(p):
    return PARTS.get(p, (p, ""))[0]


def part_time(p):
    return PARTS.get(p, ("", "19:00"))[1]


def day_name(d, short=False):
    n = DAYS[d.weekday()]
    return n[:3] if short else n


def short_date(d):
    return "%s %d" % (MONTHS[d.month - 1], d.day)


def slot_label(key):
    d, part = slot(key)
    return day_name(d, True) + " · " + part_label(part)


def is_past(key):
    return str(key).split("|")[0] < iso(today())


def time_label(t):
    """'19:00' -> '7:00 PM'."""
    if not t:
        return ""
    h, m = int(t[:2]), int(t[3:5])
    return "%d:%02d %s" % ((h % 12) or 12, m, "AM" if h < 12 else "PM")


def when_text(p):
    if not p.get("chosen"):
        return ""
    d, part = slot(p["chosen"])
    return "%s %s, %s · %s" % (day_name(d), part_label(part).lower(), short_date(d), time_label(p.get("chosen_time") or part_time(part)))


def weekend_range(fri):
    return short_date(fri) + " – " + short_date(add_days(fri, 2))


def all_past(p):
    keys = [p["chosen"]] if p.get("chosen") else list(p.get("slots") or [])
    return len(keys) > 0 and all(is_past(k) for k in keys)


def countdown():
    wd = today().weekday()
    if wd == 4:
        return {"big": "It's Friday!", "small": "Perfect timing: plan the weekend right now.", "burst": "Today!", "hot": True}
    if wd == 5:
        return {"big": "It's Saturday", "small": "Tonight still counts. So does tomorrow.", "burst": "Tonight?", "hot": True}
    if wd == 6:
        return {"big": "It's Sunday", "small": "One more feast, or line up next weekend.", "burst": "Lunch?", "hot": True}
    n = 4 - wd
    return {"big": "Friday is tomorrow" if n == 1 else "%d days to Friday" % n,
            "small": "Get a head start: send the link now, decide on Friday.", "burst": "1 day" if n == 1 else "%d days" % n, "hot": False}


def band_title():
    return {4: "It's Friday. Perfect timing.", 5: "There's still time.", 6: "Next weekend, then?"}.get(today().weekday(), "It's nearly Friday.")


# ------------------------------------------------------------------ diets, tags, dish ideas
DIETS = [("veg", "Vegetarian"), ("vegan", "Vegan"), ("gf", "Gluten-free"), ("df", "Dairy-free"), ("nutfree", "Nut allergy"), ("halal", "Halal")]
DISH_TAGS = [("veg", "Veg"), ("vegan", "Vegan"), ("gf", "GF"), ("df", "Dairy-free"), ("nuts", "Has nuts"), ("spicy", "Spicy")]
# Same list as NUT_WORDS in server_code/Guests.py (the server has the final say on every tag). A JavaScript regex.
NUT_WORDS = (r"almond|walnut|pecan|cashew|hazelnut|pistachio|peanut|pine ?nut|macadamia|brazil nut|pesto|praline|marzipan|"
             r"frangipane|nutella|satay|baklava|nougat|gianduja|amaretti|romesco|dukkah|\bnuts?\b|\bnutty\b")
NUT_FREE = r"nut[- ]free|no nuts|without nuts"
# Dish ideas for the dice, matched by words in the menu section's name.
SUGGEST = [
    (["soup"], ["Roasted squash soup", "French onion soup", "Minestrone", "Spicy black bean soup", "Leek & potato soup", "Miso soup with tofu"]),
    (["bread", "bun", "cracker"], ["Garlic bread", "Focaccia with rosemary", "Cornbread", "Seeded sourdough", "Cheese scones"]),
    (["salad"], ["Greek salad", "Crunchy slaw", "Beetroot & feta salad", "Potato salad", "Tabbouleh"]),
    (["dessert", "pie", "cake", "sweet", "pudding"], ["Lemon tart", "Brownies", "Tiramisu", "Apple pie", "Chocolate mousse", "Pavlova", "Rice pudding"]),
    (["drink", "wine", "juice", "coffee"], ["A bottle of red", "Sparkling lemonade", "Craft beer, a six-pack", "Hot mulled wine", "Iced tea", "Fancy soda"]),
    (["main", "grill", "filling"], ["Lasagne", "Chilli con carne", "Mushroom stroganoff", "Roast vegetables", "Pulled pork", "Halloumi skewers"]),
    (["side"], ["Roast potatoes", "Mac & cheese", "Green beans with almonds", "Honey carrots", "Corn on the cob"]),
    (["starter", "snack", "dipper"], ["Hummus & crudités", "Devilled eggs", "Cheese straws", "Olives & pickles", "Bread cubes & apples"]),
    (["topping", "salsa", "sauce", "gravy"], ["Pico de gallo", "Guacamole", "Chilli oil", "Maple syrup", "Garlic yoghurt sauce", "Proper gravy"]),
    (["cheese"], ["A runny brie", "Aged cheddar", "Blue cheese", "Goat cheese log"]),
    (["fruit", "pickle"], ["Grapes & figs", "Fruit salad", "Quince paste", "Cornichons"]),
    (["suppl", "ice"], ["Paper plates & napkins", "A bag of ice", "Folding chairs", "Extra glasses", "A speaker and a playlist"]),
]
SUGGEST_ANY = ["Something homemade", "A family recipe", "Your famous dish", "Something from the bakery"]


def suggest(category):
    c = (category or "").lower()
    for words, ideas in SUGGEST:
        if any(w in c for w in words):
            return ideas
    return SUGGEST_ANY


def has_nuts(text):
    """Does a dish's name/note mention a nut (and not 'nut-free')?"""
    return bool(window.PF.test(NUT_WORDS, text)) and not window.PF.test(NUT_FREE, text)


def diet_label(k):
    return dict(DIETS).get(k, k)


def tag_label(k):
    return dict(DISH_TAGS).get(k, k)


# ------------------------------------------------------------------ sharing and calendars
def party_url(token):
    loc = window.location
    return str(loc.origin) + str(loc.pathname) + "#p/" + str(window.encodeURIComponent(token))


def invite_text(p):
    host = (p.get("host_name") or "the host").split(" ")[0]
    return "You're invited to %s! Tell %s which day suits you and what you'll bring: %s" % (p["title"], host, party_url(p["token"]))


def _times(p):
    d, part = slot(p["chosen"])
    t = p.get("chosen_time") or part_time(part) or "19:00"
    start = datetime.datetime(d.year, d.month, d.day, int(t[:2]), int(t[3:5]))
    end = start + datetime.timedelta(hours=3)
    f = lambda x: "%04d%02d%02dT%02d%02d00" % (x.year, x.month, x.day, x.hour, x.minute)  # noqa: E731
    return f(start), f(end)


def _ics_esc(s):
    return str(s or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def download_ics(p):
    start, end = _times(p)
    utc = str(anvil.js.new(window.Date).toISOString())  # "2026-11-07T16:40:12.345Z" (the browser clock, in UTC)
    stamp = utc[0:4] + utc[5:7] + utc[8:10] + "T" + utc[11:13] + utc[14:16] + "00Z"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Plan Friday//EN", "BEGIN:VEVENT", "UID:" + p["token"] + "@planfriday",
             "DTSTAMP:" + stamp, "DTSTART:" + start, "DTEND:" + end, "SUMMARY:" + _ics_esc(p["title"]),
             "LOCATION:" + _ics_esc(p.get("location")),
             "DESCRIPTION:" + _ics_esc("Hosted by %s. The menu and guest list: %s" % (p.get("host_name"), party_url(p["token"]))),
             "END:VEVENT", "END:VCALENDAR"]
    name = "-".join(w for w in "".join(c if c.isalnum() else " " for c in (p["title"] or "party")).lower().split()) or "party"
    window.PF.download(name + ".ics", "\r\n".join(lines) + "\r\n", "text/calendar")


def google_cal(p):
    start, end = _times(p)
    enc = window.encodeURIComponent
    return ("https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + str(enc(p["title"])) + "&dates=" + start + "/" + end +
            "&location=" + str(enc(p.get("location") or "")) + "&details=" + str(enc("Hosted by %s. %s" % (p.get("host_name"), party_url(p["token"])))))


def copy(text):
    """Copy to the clipboard; True when it worked (the browser decides, asynchronously)."""
    return bool(window.PF.copy(text))


def confetti():
    window.PF.confetti()


def can_share():
    return bool(window.PF.canShare())


def share(title, text, url):
    window.PF.share(title, text, url)


# ------------------------------------------------------------------ weather words (forecasts come from Weather.py)
def wx_kind(code, hour=None):
    """(icon name, words) for a WMO weather code; night icons from 19:00 to 07:00."""
    night = hour is not None and (hour < 7 or hour >= 19)
    if code in (0, 1):
        return ("moon" if night else "sun"), (("Clear night" if night else "Sunny") if code == 0 else "Mostly clear")
    if code == 2:
        return "partly", "Partly cloudy"
    if code == 3:
        return "cloud", "Overcast"
    if code in (45, 48):
        return "fog", "Foggy"
    if code is not None and 51 <= code <= 57:
        return "drizzle", "Drizzle"
    if code is not None and (61 <= code <= 67 or 80 <= code <= 82):
        return "rain", ("Showers" if code >= 80 else "Rain")
    if code is not None and (71 <= code <= 77 or code in (85, 86)):
        return "snow", "Snow"
    if code is not None and code >= 95:
        return "storm", "Thunderstorms"
    return "cloud", "Cloudy"


def wx_svg(w, label=True):
    kind, words = wx_kind(w.get("code"), w.get("hour"))
    return window.PF.wx(kind, words if label else "")


def units():
    return _get("units", "C") or "C"


def set_units(u):
    _set("units", u)


def temp(c):
    if c is None:
        return ""
    return ("%d°F" % round(c * 9 / 5 + 32)) if units() == "F" else ("%d°C" % round(c))


def wind(kmh):
    kmh = kmh or 0
    return ("%d mph" % round(kmh / 1.609)) if units() == "F" else ("%d km/h" % round(kmh))


def advice(w, outdoors):
    k = wx_kind(w.get("code"), w.get("hour"))[0]
    t, rain = w.get("temp") or 0, w.get("rain") or 0
    if k == "storm":
        return "Thunder on the way: move it indoors." if outdoors else "Stormy outside, cosy inside."
    if k == "snow":
        return "Snow! Hot drinks and a quick retreat indoors." if outdoors else "Snow boots by the door."
    if k == "rain" or rain >= 60:
        return "Rain plan needed: everyone into the kitchen!" if outdoors else "Umbrellas by the door."
    if rain >= 30:
        return "Might sprinkle. Have a plan B." if outdoors else "Bring a brolly, just in case."
    if outdoors and (w.get("wind") or 0) >= 35:
        return "Windy: weigh down the napkins."
    if t < 5:
        return "Too cold for the patio. Soup, anyone?" if outdoors else "Proper soup weather."
    if t < 12:
        return "Sweater weather: bring a layer." if outdoors else "Crisp out, cosy in."
    if t >= 30:
        return "A scorcher! Bring ice. Lots of ice."
    if t >= 18 and k in ("sun", "partly", "moon"):
        return "Perfect patio weather." if outdoors else "Lovely for the walk over."
    return "Looks fine for outside." if outdoors else "Nothing to worry about."


def wx_words(w):
    """'Rain, 11°C, 80% chance of rain' (the chip's tooltip and accessible name)."""
    return "%s, %s, %d%% chance of rain" % (wx_kind(w.get("code"), w.get("hour"))[1], temp(w.get("temp")), w.get("rain") or 0)


# ------------------------------------------------------------------ browser storage (same keys as the old app)
def _get(key, default=None):
    """A real Python value from localStorage (UI.store.get returns JavaScript proxies, not dicts/lists)."""
    try:
        raw = window.localStorage.getItem("planfriday." + key)
        return default if raw is None else json.loads(str(raw))
    except Exception:
        return default


def _set(key, value):
    try:
        window.localStorage.setItem("planfriday." + key, json.dumps(value))
    except Exception:
        pass


def secret(token):
    """This browser's guest secret for a party (no account needed)."""
    return _get("g." + token)


def set_secret(token, value):
    _set("g." + token, value)


def get(key, default=None):
    return _get(key, default)


def put(key, value):
    _set(key, value)


def visited():
    """Parties opened on this device (guests have no account), newest first."""
    v = _get("visited", [])
    return v if isinstance(v, list) else []


def remember(p):
    lst = [x for x in visited() if x.get("token") != p["token"]]
    lst.insert(0, {"token": p["token"], "title": p["title"], "cover": p.get("cover"), "host": p.get("host_name"),
                   "at": int(window.Date.now())})
    _set("visited", lst[:12])


def forget(token):
    _set("visited", [x for x in visited() if x.get("token") != token])
