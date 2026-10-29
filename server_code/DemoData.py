"""Demo content: three sample parties (fictional hosts and guests), so the app never looks empty.

Anyone can open them at #p/sample, #p/sample-brunch and #p/sample-dumplings (the landing page links the first),
but nobody can change them (Guests.SAMPLE). They always sit on the coming weekend: when the week turns, the
demo reloads itself (ensure_loaded). Removed or reloaded from Admin -> Demo data; removing is remembered.

Demo hosts have is_demo=True and @example.com emails; they can't sign in (no password). Every demo row is
flagged is_demo=True, so remove() deletes exactly what load() added (plus anything attached to a demo party).
"""
import datetime as dt

from anvil.tables import app_tables

from . import common as C

SAMPLE_TOKEN = "sample"
# The sample parties' weather check is for Montréal (stored directly, so loading the demo needs no look-up).
DEMO_PLACE = ("Montréal, Quebec, Canada", 45.5088, -73.5878)
DEMO_HOSTS = [
    ("Maya Chen", "maya.demo@example.com"),
    ("Theo Martin", "theo.demo@example.com"),
    ("Ines Ozola", "ines.demo@example.com"),
]
# Each party: token, host index, catalogue no., fields, slots as (day offset from Friday, part),
# chosen slot index or None, menu [(category, wanted)], guests, dishes, comments.
# Guests: (name, rsvp, plus, diet, answers per slot "y"/"m"/"n"/"-"); the host is guest 0.
# Dishes: (guest index, category, name, serves, tags). Comments: (guest index, hours ago, text).
DEMO_PARTIES = [
    {"token": SAMPLE_TOKEN, "host": 0, "catalog_no": "No. 12F 4108", "title": "Soup Night Supper", "cover": "soup",
     "style": "potluck", "cap": 12, "location": "Maya's flat, 3rd floor (buzz 31)",
     "blurb": "It's getting cold, so: soup. Everyone brings a pot of something, I'll do bread and bowls. "
              "Come hungry, leave with leftovers.",
     "slots": [(0, "dinner"), (1, "dinner"), (2, "lunch")], "chosen": None,
     "menu": [("Soup", 3), ("Bread", 2), ("Salad", 1), ("Dessert", 2), ("Drinks", 2)],
     "guests": [("Maya", "yes", 0, [], "yym"), ("Priya", "yes", 1, ["veg"], "nyy"), ("Sam", "yes", 0, [], "yyn"),
                ("Jonah", "maybe", 0, ["gf"], "myn"), ("Lou", "yes", 0, ["nutfree"], "nym"), ("Bea", "no", 0, [], "---"),
                ("Kofi", "yes", 0, [], "ymy")],
     "dishes": [(0, "Soup", "Roasted tomato & red pepper soup", 8, ["veg", "gf"]),
                (1, "Soup", "Coconut red lentil soup", 6, ["vegan", "gf", "spicy"]),
                (2, "Bread", "Rye sourdough, two loaves", 10, ["vegan"]),
                (4, "Dessert", "Apple & oat crumble", 8, ["veg"]),
                (6, "Drinks", "Hot spiced cider", 10, ["vegan", "gf"]),
                (3, "Salad", "Bitter leaves, pear & walnut", 6, ["veg", "gf", "nuts"])],
     "comments": [(0, 30, "Big pot energy only. I have 12 bowls and exactly 9 spoons, so bring a spoon if you're particular about it."),
                  (1, 26, "Saturday works so much better for me. Bringing a +1 (Dev), he's on bread duty in spirit."),
                  (4, 20, "Heads up: nut allergy here! Not the scary kind, just the itchy kind."),
                  (3, 8, "Noted, Lou: the walnuts go in a separate bowl."),
                  (6, 3, "Is there parking on the street? Asking for my car.")]},
    {"token": "sample-brunch", "host": 1, "catalog_no": "No. 31P 2275", "title": "Sunday Pancake Brunch", "cover": "pancakes",
     "style": "hostcooks", "cap": None, "location": "Theo's place, the blue door on Rue Fabre",
     "blurb": "I'm making pancakes. A lot of pancakes. You bring the toppings and something to drink.",
     "slots": [(1, "brunch"), (2, "brunch")], "chosen": 1, "chosen_time": "10:30",
     "menu": [("Toppings", 3), ("Fruit", 1), ("Coffee & juice", 2)],
     "guests": [("Theo", "yes", 0, [], "my"), ("Marta", "yes", 0, [], "yy"), ("Felix", "yes", 0, ["vegan"], "ny"),
                ("Hana", "maybe", 0, [], "mm"), ("Oskar", "yes", 2, [], "ny")],
     "dishes": [(1, "Toppings", "Whipped maple butter", 8, ["veg", "gf"]),
                (2, "Toppings", "Blueberry compote", 8, ["vegan", "gf"]),
                (4, "Coffee & juice", "Fresh orange juice, 2 litres", 8, ["vegan", "gf"])],
     "comments": [(0, 40, "Pancakes are on me. Forty of them, minimum."),
                  (4, 12, "Bringing my two kids. They will eat thirty of those forty.")]},
    {"token": "sample-dumplings", "host": 2, "catalog_no": "No. 57K 9031", "title": "Dumpling Folding Party", "cover": "dumplings",
     "style": "potluck", "cap": 8, "location": "Ines's kitchen and the back garden", "outdoors": True,
     "blurb": "I'll make the dough and a pork & cabbage filling. Bring a filling, a sauce or a side, and we fold together. Ugly dumplings welcome.",
     "slots": [(0, "late"), (1, "afternoon"), (1, "dinner")], "chosen": None,
     "menu": [("Fillings", 2), ("Dipping sauces", 2), ("Sides", 1), ("Drinks", 2), ("Dessert", 1)],
     "guests": [("Ines", "yes", 0, [], "nyy"), ("Rosa", "yes", 0, ["veg"], "nmy"), ("Dev", "maybe", 0, [], "yny"),
                ("Hugo", "yes", 1, ["halal"], "-yy")],
     "dishes": [(1, "Fillings", "Mushroom & chive filling", 30, ["vegan"]),
                (3, "Dipping sauces", "Black vinegar & chilli oil", 8, ["vegan", "spicy"])],
     "comments": [(2, 6, "I can only do Friday late or Saturday dinner. Dinner please!")]},
]
# Tables that hold demo rows (each has an is_demo column). Children before parents.
DEMO_TABLES = ["comments", "dishes", "guests", "parties"]


def state():
    return C.get_setting("demo", "never")  # "never" | "loaded" | "removed"


def weekend_friday(today=None):
    """The Friday of this weekend (Fri, Sat or Sun) or of the coming one (Mon to Thu)."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    wd = today.weekday()  # Mon 0 ... Fri 4, Sat 5, Sun 6
    return today - dt.timedelta(days=wd - 4) if wd >= 4 else today + dt.timedelta(days=4 - wd)


def ensure_loaded():
    """Call from the app's main data callables: loads the demo once (unless an admin removed it), and moves
    it to the new weekend when the week turns."""
    s = state()
    if s == "never" or (s == "loaded" and C.get_setting("demo_week") != weekend_friday().isoformat()):
        load()


def load():
    remove(remember=False)
    friday = weekend_friday()
    hosts = []
    for name, email in DEMO_HOSTS:
        u = app_tables.users.get(email=email) or app_tables.users.add_row(email=email, enabled=False)
        u.update(display_name=name, is_demo=True, signed_up=C.now() - dt.timedelta(days=30))
        hosts.append(u)
    for d in DEMO_PARTIES:
        slots = ["%s|%s" % ((friday + dt.timedelta(days=off)).isoformat(), part) for off, part in d["slots"]]
        wanted = {c: n for c, n in d["menu"]}
        wanted["Something else"] = 0
        p = app_tables.parties.add_row(
            host=hosts[d["host"]], token=d["token"], catalog_no=d["catalog_no"], title=d["title"], blurb=d["blurb"],
            location=d["location"], style=d["style"], cover=d["cover"], cap=d["cap"], slots=slots,
            chosen=slots[d["chosen"]] if d["chosen"] is not None else None, chosen_time=d.get("chosen_time"),
            categories=[c for c, n in d["menu"]], wanted=wanted, status="open", outdoors=bool(d.get("outdoors")),
            wx_place=DEMO_PLACE[0], wx_lat=DEMO_PLACE[1], wx_lon=DEMO_PLACE[2],
            created=C.now() - dt.timedelta(days=2), updated=C.now() - dt.timedelta(hours=3), is_demo=True)
        guests = []
        for i, (name, rsvp, plus, diet, answers) in enumerate(d["guests"]):
            avail = {slots[j]: {"y": "yes", "m": "maybe", "n": "no"}[a] for j, a in enumerate(answers) if a in "ymn"}
            guests.append(app_tables.guests.add_row(
                party=p, user=hosts[d["host"]] if i == 0 else None, secret_hash=None, name=name, rsvp=rsvp, plus=plus,
                diet=diet, avail=avail, created=C.now() - dt.timedelta(hours=48 - 4 * i), updated=C.now(), is_demo=True))
        for i, (who, cat, name, serves, tags) in enumerate(d["dishes"]):
            app_tables.dishes.add_row(party=p, guest=guests[who], category=cat, name=name, serves=serves, tags=tags, note="",
                                      created=C.now() - dt.timedelta(hours=40 - 5 * i), is_demo=True)
        for who, hours, body in d["comments"]:
            app_tables.comments.add_row(party=p, guest=guests[who], body=body,
                                        created=C.now() - dt.timedelta(hours=hours), is_demo=True)
    C.set_setting("demo", "loaded")
    C.set_setting("demo_week", friday.isoformat())
    return counts()


def remove(remember=True):
    for p in app_tables.parties.search(is_demo=True):  # anything attached to a demo party goes with it
        for t in (app_tables.dishes, app_tables.comments, app_tables.guests):
            for r in t.search(party=p):
                r.delete()
    for name in DEMO_TABLES:
        for r in getattr(app_tables, name).search(is_demo=True):
            r.delete()
    for u in app_tables.users.search(is_demo=True):
        u.delete()
    if remember:
        C.set_setting("demo", "removed")
    return counts()


def counts():
    out = {"users": len(app_tables.users.search(is_demo=True))}
    for name in DEMO_TABLES:
        out[name] = len(getattr(app_tables, name).search(is_demo=True))
    return out
