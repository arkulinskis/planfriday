"""Parties: what a signed-in host does. Create and edit a party, lock in the day, close RSVPs, run it again,
remove a guest, delete. Plus the home page: the parties you host and the ones you joined while signed in.

A party's `slots` are "YYYY-MM-DD|part" strings (part: brunch, lunch, afternoon, dinner, late). Dates are the
host's local calendar days, worked out in the browser; the server only checks they are real dates.
"""
import datetime as dt
import random
import re
import secrets

import anvil.server
from anvil.tables import app_tables

from . import common as C
from . import DemoData, Guests

STYLES = ("potluck", "hostcooks", "byob")
COVERS = ("classic", "soup", "pancakes", "dumplings", "tacos", "fondue", "pizza", "roast", "salad", "pie", "wine", "bbq", "cake")
MAX_SLOTS, MAX_CATS, MAX_PARTIES = 14, 14, 200


def clean_slots(slots):
    out = []
    for key in slots or []:
        if not isinstance(key, str) or "|" not in key:
            continue
        day, part = key.split("|", 1)
        try:
            day = dt.date.fromisoformat(day)
        except ValueError:
            continue
        if part not in Guests.PARTS:
            continue
        k = day.isoformat() + "|" + part
        if k not in out:
            out.append(k)
    out.sort(key=lambda k: (k.split("|")[0], Guests.PARTS.index(k.split("|")[1])))
    return out[:MAX_SLOTS]


def clean_menu(cats, wanted):
    names, seen = [], set()
    for c in cats or []:
        n = C.text(c, 30)
        if n and n.lower() not in seen and n != Guests.EXTRA:
            seen.add(n.lower())
            names.append(n)
    names = names[:MAX_CATS]
    wanted = wanted if isinstance(wanted, dict) else {}
    w = {}
    for n in names + [Guests.EXTRA]:
        try:
            v = int(wanted.get(n, 0 if n == Guests.EXTRA else 1))
        except (TypeError, ValueError):
            v = 1
        w[n] = max(0, min(20, v))
    return names, w


def _read(data):
    """(fields, error) from the party form."""
    if not isinstance(data, dict):
        return None, "Fill in the form first."
    title = C.text(data.get("title"), 80)
    if len(title) < 2:
        return None, "Give your party a name."
    slots = clean_slots(data.get("slots"))
    if not slots:
        return None, "Pick at least one day and time that could work."
    cats, wanted = clean_menu(data.get("categories"), data.get("wanted"))
    cap = data.get("cap")
    try:
        cap = int(cap) if cap not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        cap = None
    if cap is not None and not 2 <= cap <= 100:
        return None, "A table for 2 to 100 people, please (or leave it empty for no limit)."
    return {"title": title, "blurb": C.text(data.get("blurb"), 1000, multiline=True),
            "location": C.text(data.get("location"), 120),
            "style": data.get("style") if data.get("style") in STYLES else "potluck",
            "cover": data.get("cover") if data.get("cover") in COVERS else "classic",
            "cap": cap, "slots": slots, "categories": cats, "wanted": wanted}, None


def _new_token():
    while True:
        t = secrets.token_urlsafe(9)
        if not app_tables.parties.get(token=t):
            return t


def _catalog_no():
    return "No. %d%s %04d" % (random.randint(10, 99), random.choice("FKPRTW"), random.randint(1000, 9999))


def _own(party_id, allow_admin=False):
    """(party, error) for the signed-in host of party_id."""
    me = C.require_user()
    p = C.row_by_id(app_tables.parties, party_id)
    if p is None:
        return None, C.fail("That party no longer exists.")
    if p["host"] != me and not (allow_admin and C.is_admin(me)):
        return None, C.fail("Only the host can do that.")
    if p["is_demo"] and not C.is_admin(me):
        return None, C.fail(Guests.SAMPLE)
    return p, None


def _host_row(p):
    me = p["host"]
    g = app_tables.guests.get(party=p, user=me)
    if g is None:
        g = app_tables.guests.add_row(party=p, user=me, secret_hash=None, name=C.name_of(me), rsvp="yes", plus=0,
                                      diet=[], avail={}, created=C.now(), updated=C.now(), is_demo=bool(p["is_demo"]))
    return g


def delete_party(p):
    for t in (app_tables.dishes, app_tables.comments, app_tables.guests):
        for r in t.search(party=p):
            r.delete()
    p.delete()


def summary(p, me):
    guests = list(app_tables.guests.search(party=p))
    dishes = list(app_tables.dishes.search(party=p))
    s = Guests.stats(p, guests, dishes)
    mine = [g for g in guests if me is not None and g["user"] == me]
    return {"id": p.get_id(), "token": p["token"], "title": p["title"], "cover": p["cover"] or "classic",
            "catalog_no": p["catalog_no"], "slots": list(p["slots"] or []), "chosen": p["chosen"],
            "chosen_time": p["chosen_time"], "status": p["status"] or "open", "host_name": C.name_of(p["host"]),
            "location": p["location"] or "", "is_host": me is not None and p["host"] == me,
            "my_rsvp": mine[0]["rsvp"] if mine else None, "demo": bool(p["is_demo"]),
            "yes": s["yes"], "maybe": s["maybe"], "heads": s["heads"], "best": s["best"], "filled": s["filled"],
            "wanted_total": s["wanted_total"], "dishes": s["dishes"], "guests": len(guests),
            "updated": C.iso(p["updated"])}


# ----------------------------------------------------------------------------------------------- callables
@anvil.server.callable(require_user=True)
def get_home():
    """The parties you host, the ones you're on the guest list of, and the sample party's link."""
    DemoData.ensure_loaded()
    me = C.require_user()
    hosting = [summary(p, me) for p in app_tables.parties.search(host=me)]
    hosted = {h["id"] for h in hosting}
    invited = []
    for g in app_tables.guests.search(user=me):
        p = g["party"]
        if p is not None and p.get_id() not in hosted:
            invited.append(summary(p, me))
    key = lambda s: s["updated"] or ""
    hosting.sort(key=key, reverse=True)
    invited.sort(key=key, reverse=True)
    sample = app_tables.parties.get(token=DemoData.SAMPLE_TOKEN)
    return {"hosting": hosting, "invited": invited, "sample": DemoData.SAMPLE_TOKEN if sample else None}


@anvil.server.callable(require_user=True)
def get_party_form(party_id):
    """A party's settings, for the edit form. Host only."""
    p, err = _own(party_id)
    if err:
        return err
    d = Guests.party_dict(p)
    d["categories"] = [c for c in d["categories"] if c != Guests.EXTRA]
    d["answers"] = len([g for g in app_tables.guests.search(party=p) if g["avail"]])
    return C.ok(party=d)


@anvil.server.callable(require_user=True)
def create_party(data):
    me = C.require_user()
    f, problem = _read(data)
    if problem:
        return C.fail(problem)
    if C.rate_limited("create_party", 20, 3600):
        return C.fail("That's a lot of parties in one hour! Please try again later.")
    if len(app_tables.parties.search(host=me)) >= MAX_PARTIES:
        return C.fail("You have %d parties already. Delete a few old ones first." % MAX_PARTIES)
    p = app_tables.parties.add_row(host=me, token=_new_token(), catalog_no=_catalog_no(), status="open",
                                   chosen=None, chosen_time=None, created=C.now(), updated=C.now(), is_demo=False, **f)
    _host_row(p)
    return C.ok(id=p.get_id(), token=p["token"])


@anvil.server.callable(require_user=True)
def update_party(party_id, data):
    p, err = _own(party_id)
    if err:
        return err
    f, problem = _read(data)
    if problem:
        return C.fail(problem)
    if p["chosen"] and p["chosen"] not in f["slots"]:
        f["chosen"], f["chosen_time"] = None, None
    p.update(updated=C.now(), **f)
    return C.ok(id=p.get_id(), token=p["token"])


@anvil.server.callable(require_user=True)
def lock_slot(party_id, slot, time=None):
    """Lock in the day (slot) and a start time ("19:00"), or unlock it again (slot None)."""
    p, err = _own(party_id)
    if err:
        return err
    if slot is None:
        p.update(chosen=None, chosen_time=None, updated=C.now())
    else:
        if slot not in (p["slots"] or []):
            return C.fail("Pick one of the party's days.")
        time = time if isinstance(time, str) and re.match(r"^([01]\d|2[0-3]):[0-5]\d$", time) else None
        p.update(chosen=slot, chosen_time=time, updated=C.now())
    return C.ok(view=Guests.view(p, _host_row(p)))


@anvil.server.callable(require_user=True)
def set_party_status(party_id, status):
    p, err = _own(party_id)
    if err:
        return err
    if status not in ("open", "closed"):
        return C.fail("Unknown status.")
    p.update(status=status, updated=C.now())
    return C.ok(view=Guests.view(p, _host_row(p)))


@anvil.server.callable(require_user=True)
def host_remove_guest(party_id, guest_id):
    p, err = _own(party_id)
    if err:
        return err
    g = C.row_by_id(app_tables.guests, guest_id)
    if g is not None and g["party"] == p:
        if g["user"] is not None and g["user"] == p["host"]:
            return C.fail("You can't take yourself off your own party.")
        Guests.delete_guest(g)
        p["updated"] = C.now()
    return C.ok(view=Guests.view(p, _host_row(p)))


@anvil.server.callable(require_user=True)
def duplicate_party(party_id):
    """Run it again: the same party (name, menu, days of the week), moved to the coming weekend, no guests."""
    me = C.require_user()
    src = C.row_by_id(app_tables.parties, party_id)
    if src is None:
        return C.fail("That party no longer exists.")
    if src["host"] != me and not src["is_demo"]:
        return C.fail("Only the host can run this party again.")
    if C.rate_limited("create_party", 20, 3600):
        return C.fail("That's a lot of parties in one hour! Please try again later.")
    today = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)  # a day of slack for time zones
    slots = list(src["slots"] or [])
    first = min(dt.date.fromisoformat(k.split("|")[0]) for k in slots) if slots else today
    weeks = 0
    # A copy of your own party moves on a week at least; a copy of a sample party keeps its weekend if it's still ahead.
    while first + dt.timedelta(weeks=weeks) < today or (weeks == 0 and not src["is_demo"]):
        weeks += 1
    moved = clean_slots(["%s|%s" % ((dt.date.fromisoformat(k.split("|")[0]) + dt.timedelta(weeks=weeks)).isoformat(), k.split("|")[1])
                         for k in slots])
    p = app_tables.parties.add_row(host=me, token=_new_token(), catalog_no=_catalog_no(), status="open",
                                   title=src["title"], blurb=src["blurb"], location=src["location"], style=src["style"],
                                   cover=src["cover"], cap=src["cap"], slots=moved, chosen=None, chosen_time=None,
                                   categories=list(src["categories"] or []), wanted=dict(src["wanted"] or {}),
                                   created=C.now(), updated=C.now(), is_demo=False)
    _host_row(p)
    return C.ok(id=p.get_id(), token=p["token"])


@anvil.server.callable(require_user=True)
def remove_party(party_id):
    """Delete a party with its guest list, menu and comments. The host (or an admin)."""
    p, err = _own(party_id, allow_admin=True)
    if err:
        return err
    delete_party(p)
    return C.ok()
