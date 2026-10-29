"""Guests: everything the party link (#p/<token>) can do, with or without an account.

Anyone with the link can see the party page. To RSVP, say when they're free, bring a dish or leave a comment,
a visitor first joins with a name. Visitors without an account get a random secret back (their browser keeps
it; we store only its SHA-256), and every later call sends it. Signed-in people are linked by their account,
so the party follows them to any device. The host has a guest row too (created with the party).

Sample parties (is_demo) can be looked at but not changed.
Every reply that changes something returns the whole page again (view), so the page is one call per action.
"""
import hashlib
import re
import secrets

import anvil.server
from anvil.tables import app_tables

from . import common as C
from . import DemoData

PARTS = ("brunch", "lunch", "afternoon", "dinner", "late")
RSVPS = ("yes", "maybe", "no")
DIETS = ("veg", "vegan", "gf", "df", "nutfree", "halal")
TAGS = ("veg", "vegan", "gf", "df", "nuts", "spicy")
EXTRA = "Something else"          # a menu section every party has, for whatever doesn't fit
MAX_GUESTS, MAX_DISHES, MAX_COMMENTS = 60, 150, 400
SAMPLE = "This is a sample party, so it can't be changed. Start your own party to try it out!"
CLOSED = "The host has closed RSVPs for this party."


def _hash(secret):
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def find_party(token):
    if not isinstance(token, str) or not re.match(r"^[A-Za-z0-9_-]{3,40}$", token):
        return None
    return app_tables.parties.get(token=token)


def identity(p, secret):
    """The caller's guest row in this party, or None (signed-in account first, then the browser's secret)."""
    me = C.me()
    if me is not None:
        g = app_tables.guests.get(party=p, user=me)
        if g is not None:
            return g
    if isinstance(secret, str) and 16 <= len(secret) <= 80:
        g = app_tables.guests.get(party=p, secret_hash=_hash(secret))
        if g is not None:
            if me is not None and g["user"] is None:
                g["user"] = me  # someone who joined as a guest and then signed in keeps their place
            return g
    return None


def categories(p):
    cats = list(p["categories"] or [])
    if EXTRA not in cats:
        cats.append(EXTRA)
    return cats


def _by_created(rows):
    return sorted(rows, key=lambda r: (r["created"] or C.now()))


def heads(guests, skip=None):
    return sum(1 + int(g["plus"] or 0) for g in guests if g["rsvp"] == "yes" and g != skip)


def stats(p, guests, dishes):
    slots = list(p["slots"] or [])
    tally = {}
    for k in slots:
        tally[k] = {"yes": [], "maybe": [], "no": []}
    for g in guests:
        if g["rsvp"] == "no":
            continue
        for k, v in (g["avail"] or {}).items():
            if k in tally and v in RSVPS:
                tally[k][v].append(g.get_id())
    best, best_score = None, 0
    for k in slots:
        score = 2 * len(tally[k]["yes"]) + len(tally[k]["maybe"])
        if score > best_score:
            best, best_score = k, score
    menu = {}
    wanted = p["wanted"] or {}
    for c in categories(p):
        menu[c] = {"wanted": int(wanted.get(c, 0) or 0), "have": 0}
    for d in dishes:
        if d["category"] in menu:
            menu[d["category"]]["have"] += 1
    diets = {}
    for g in guests:
        if g["rsvp"] in ("yes", "maybe"):
            for k in g["diet"] or []:
                diets[k] = diets.get(k, 0) + 1
    filled = sum(min(m["have"], m["wanted"]) for m in menu.values())
    return {"yes": len([g for g in guests if g["rsvp"] == "yes"]),
            "maybe": len([g for g in guests if g["rsvp"] == "maybe"]),
            "no": len([g for g in guests if g["rsvp"] == "no"]),
            "heads": heads(guests), "slots": tally, "best": best, "menu": menu, "diets": diets,
            "filled": filled, "wanted_total": sum(m["wanted"] for m in menu.values()), "dishes": len(dishes)}


def party_dict(p):
    return {"id": p.get_id(), "token": p["token"], "catalog_no": p["catalog_no"], "title": p["title"],
            "blurb": p["blurb"] or "", "location": p["location"] or "", "style": p["style"] or "potluck",
            "cover": p["cover"] or "classic", "cap": p["cap"], "slots": list(p["slots"] or []), "chosen": p["chosen"],
            "chosen_time": p["chosen_time"], "categories": categories(p), "wanted": dict(p["wanted"] or {}),
            "status": p["status"] or "open", "host_name": C.name_of(p["host"]), "demo": bool(p["is_demo"]),
            "created": C.iso(p["created"]), "updated": C.iso(p["updated"])}


def _is_host_row(g, p):
    return g["user"] is not None and g["user"] == p["host"]


def guest_dict(g, p, mine):
    slots = set(p["slots"] or [])
    return {"id": g.get_id(), "name": g["name"], "rsvp": g["rsvp"], "plus": int(g["plus"] or 0),
            "diet": list(g["diet"] or []), "avail": {k: v for k, v in (g["avail"] or {}).items() if k in slots},
            "is_host": _is_host_row(g, p), "mine": mine, "member": g["user"] is not None, "created": C.iso(g["created"])}


def view(p, g):
    """Everything the party page shows. Never includes anyone's email."""
    me = C.me()
    is_host = me is not None and p["host"] == me
    admin = C.is_admin(me)
    guests = _by_created(app_tables.guests.search(party=p))
    dishes = _by_created(app_tables.dishes.search(party=p))
    comments = _by_created(app_tables.comments.search(party=p))
    names = {x.get_id(): x["name"] for x in guests}
    return {
        "party": party_dict(p), "is_host": is_host, "is_admin": admin, "signed_in": me is not None,
        "suggest_name": C.name_of(me) if me is not None else None,
        "me": guest_dict(g, p, True) if g is not None else None,
        "guests": [guest_dict(x, p, g is not None and x == g) for x in guests],
        "dishes": [{"id": d.get_id(), "guest_id": d["guest"].get_id() if d["guest"] else None,
                    "by": names.get(d["guest"].get_id(), "A guest") if d["guest"] else "A guest",
                    "category": d["category"], "name": d["name"], "serves": d["serves"], "tags": list(d["tags"] or []),
                    "note": d["note"] or "", "mine": g is not None and d["guest"] == g,
                    "can_remove": (g is not None and d["guest"] == g) or is_host or admin} for d in dishes],
        "comments": [{"id": c.get_id(), "by": names.get(c["guest"].get_id(), "A guest") if c["guest"] else "A guest",
                      "by_host": c["guest"] is not None and _is_host_row(c["guest"], p), "body": c["body"],
                      "created": C.iso(c["created"]), "mine": g is not None and c["guest"] == g,
                      "can_remove": (g is not None and c["guest"] == g) or is_host or admin} for c in comments],
        "stats": stats(p, guests, dishes),
    }


def delete_guest(g):
    for d in app_tables.dishes.search(guest=g):
        d.delete()
    for c in app_tables.comments.search(guest=g):
        c.delete()
    g.delete()


def _load(token, secret, need_guest=True):
    """(party, guest, error reply). Checks the link, sample parties and that the caller has joined."""
    p = find_party(token)
    if p is None:
        return None, None, C.fail("We couldn't find that party. The host may have deleted it.")
    if p["is_demo"]:
        return p, None, C.fail(SAMPLE)
    g = identity(p, secret)
    if need_guest and g is None:
        return p, None, C.fail("Add your name to the guest list first.")
    return p, g, None


def _plus(v):
    try:
        return max(0, min(6, int(v or 0)))
    except (TypeError, ValueError):
        return 0


def _full(p, g, rsvp, plus):
    """A reply if saying yes with `plus` extra people would go over the party's cap."""
    cap = p["cap"]
    if not cap or rsvp != "yes":
        return None
    others = heads(app_tables.guests.search(party=p), skip=g)
    if others + 1 + plus > cap:
        left = max(0, int(cap) - others)
        return C.fail("The table is full (%d seats). You can still say maybe." % cap if left == 0
                      else "Only %d seat%s left at the table. Bring fewer people, or say maybe." % (left, "" if left == 1 else "s"))
    return None


def _touch(p):
    p["updated"] = C.now()


# ----------------------------------------------------------------------------------------------- callables
@anvil.server.callable
def party_view(token, secret=None):
    """The party page. Anyone with the link."""
    DemoData.ensure_loaded()
    p = find_party(token)
    if p is None:
        return C.ok(missing=True)
    return C.ok(view=view(p, identity(p, secret)))


@anvil.server.callable
def guest_join(token, secret=None, name="", rsvp="yes", plus=0):
    """Put a name on the guest list. Returns the browser's secret for a new guest."""
    p, g, err = _load(token, secret, need_guest=False)
    if err:
        return err
    name = C.text(name, 40)
    if not name:
        return C.fail("Please tell the host your name.")
    rsvp = rsvp if rsvp in RSVPS else "yes"
    plus = _plus(plus)
    is_host = C.me() is not None and C.me() == p["host"]
    if p["status"] == "closed" and not is_host and g is None:
        return C.fail(CLOSED)
    full = _full(p, g, rsvp, plus)
    if full:
        return full
    if g is not None:
        g.update(name=name, rsvp=rsvp, plus=plus, updated=C.now())
        _touch(p)
        return C.ok(view=view(p, g), secret=None)
    if C.rate_limited("guest_join", 20, 3600):
        return C.fail("That's a lot of RSVPs from one browser. Please try again later.")
    if len(app_tables.guests.search(party=p)) >= MAX_GUESTS:
        return C.fail("This guest list is full (%d names)." % MAX_GUESTS)
    new_secret = secrets.token_urlsafe(24)
    g = app_tables.guests.add_row(party=p, user=C.me(), secret_hash=_hash(new_secret), name=name, rsvp=rsvp, plus=plus,
                                  diet=[], avail={}, created=C.now(), updated=C.now(), is_demo=False)
    _touch(p)
    return C.ok(view=view(p, g), secret=new_secret)


@anvil.server.callable
def guest_save(token, secret, changes):
    """Change your own answers: name, rsvp, plus, diet, avail ({slot: yes|maybe|no|""})."""
    p, g, err = _load(token, secret)
    if err:
        return err
    if not isinstance(changes, dict):
        return C.fail("Nothing to save.")
    upd = {}
    host = _is_host_row(g, p)
    if "name" in changes:
        name = C.text(changes["name"], 40)
        if not name:
            return C.fail("Your name can't be empty.")
        upd["name"] = name
    rsvp, plus = g["rsvp"], int(g["plus"] or 0)
    if "rsvp" in changes:
        if changes["rsvp"] not in RSVPS:
            return C.fail("Choose yes, maybe or no.")
        rsvp = changes["rsvp"]
    if "plus" in changes:
        plus = _plus(changes["plus"])
    if (rsvp != g["rsvp"] or plus != int(g["plus"] or 0)):
        if p["status"] == "closed" and not host:
            return C.fail(CLOSED)
        full = _full(p, g, rsvp, plus)
        if full:
            return full
        upd["rsvp"], upd["plus"] = rsvp, plus
    if "diet" in changes:
        upd["diet"] = [k for k in DIETS if k in (changes["diet"] or [])]
    if "avail" in changes:
        if not isinstance(changes["avail"], dict):
            return C.fail("Those days didn't make sense.")
        avail = dict(g["avail"] or {})
        slots = set(p["slots"] or [])
        for k, v in changes["avail"].items():
            if k not in slots:
                continue
            if v in RSVPS:
                avail[k] = v
            else:
                avail.pop(k, None)
        upd["avail"] = avail
    if upd:
        upd["updated"] = C.now()
        g.update(**upd)
        _touch(p)
    return C.ok(view=view(p, g))


@anvil.server.callable
def guest_forget(token, secret):
    """Take yourself off the guest list, with your dishes and comments."""
    p, g, err = _load(token, secret)
    if err:
        return err
    if _is_host_row(g, p):
        return C.fail("You're the host. To cancel, delete the party instead.")
    delete_guest(g)
    _touch(p)
    return C.ok(view=view(p, None))


@anvil.server.callable
def dish_add(token, secret, dish):
    """Say what you're bringing: {category, name, serves, tags, note}."""
    p, g, err = _load(token, secret)
    if err:
        return err
    dish = dish if isinstance(dish, dict) else {}
    cat = C.text(dish.get("category"), 30)
    if cat not in categories(p):
        return C.fail("Pick one of the menu sections.")
    name = C.text(dish.get("name"), 80)
    if len(name) < 2:
        return C.fail("What are you bringing? Give it a name.")
    serves = dish.get("serves")
    try:
        serves = max(1, min(50, int(serves))) if serves not in (None, "") else None
    except (TypeError, ValueError):
        serves = None
    if C.rate_limited("dish_add", 30, 3600):
        return C.fail("That's a lot of dishes in one hour. Please try again later.")
    if len(app_tables.dishes.search(party=p)) >= MAX_DISHES:
        return C.fail("This menu is full (%d dishes). That's quite the feast." % MAX_DISHES)
    app_tables.dishes.add_row(party=p, guest=g, category=cat, name=name, serves=serves,
                              tags=[t for t in TAGS if t in (dish.get("tags") or [])],
                              note=C.text(dish.get("note"), 140), created=C.now(), is_demo=False)
    _touch(p)
    return C.ok(view=view(p, g))


@anvil.server.callable
def dish_remove(token, secret, dish_id):
    p, g, err = _load(token, secret, need_guest=False)
    if err:
        return err
    d = C.row_by_id(app_tables.dishes, dish_id)
    if d is None or d["party"] != p:
        return C.ok(view=view(p, g))
    me = C.me()
    if not ((g is not None and d["guest"] == g) or (me is not None and me == p["host"]) or C.is_admin(me)):
        return C.fail("Only the person bringing it (or the host) can take it off the menu.")
    d.delete()
    _touch(p)
    return C.ok(view=view(p, g))


@anvil.server.callable
def comment_add(token, secret, body):
    p, g, err = _load(token, secret)
    if err:
        return err
    body = C.text(body, 600, multiline=True)
    if not body:
        return C.fail("Write something first.")
    if C.rate_limited("comment_add", 20, 3600):
        return C.fail("That's a lot of comments in one hour. Please try again later.")
    if len(app_tables.comments.search(party=p)) >= MAX_COMMENTS:
        return C.fail("This guestbook is full.")
    app_tables.comments.add_row(party=p, guest=g, body=body, created=C.now(), is_demo=False)
    _touch(p)
    return C.ok(view=view(p, g))


@anvil.server.callable
def comment_remove(token, secret, comment_id):
    p, g, err = _load(token, secret, need_guest=False)
    if err:
        return err
    c = C.row_by_id(app_tables.comments, comment_id)
    if c is None or c["party"] != p:
        return C.ok(view=view(p, g))
    me = C.me()
    if not ((g is not None and c["guest"] == g) or (me is not None and me == p["host"]) or C.is_admin(me)):
        return C.fail("You can only delete your own comments.")
    c.delete()
    return C.ok(view=view(p, g))
