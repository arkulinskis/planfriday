"""Guests: everything the party link (#p/<token>) can do, with or without an account.

Anyone with the link can see the party page. To RSVP, say when they're free, bring a dish or leave a comment,
a visitor first joins with a name. Visitors without an account get a random secret back (their browser keeps
it; we store only its SHA-256), and every later call sends it. Signed-in people are linked by their account,
so the party follows them to any device. The host has a guest row too (created with the party).

Sample parties (is_demo) can be looked at but not changed.
Every reply that changes something returns the whole page again (view), so the page is one call per action.

The kitty (2026-11-20): anyone on the guest list adds what they spent ("Wine 30"); kitty_math splits the total
fairly by heads (a guest's +1s count in their share) and works out the fewest payments to settle up. Plan Friday only
does the maths: it never handles money or payment links. The kitty table is new, so view() returns kitty None (the
section stays hidden) until the live database has it.
"""
import hashlib
import re
import secrets

import anvil.server
from anvil.tables import app_tables

from . import common as C
from . import DemoData, Weather

PARTS = ("brunch", "lunch", "afternoon", "dinner", "late")
RSVPS = ("yes", "maybe", "no")
DIETS = ("veg", "vegan", "gf", "df", "nutfree", "halal")
TAGS = ("veg", "vegan", "gf", "df", "nuts", "spicy")

# Allergy safety: what a dish's own words say beats the tags someone ticked. "Has nuts" is added whenever a nut word
# appears; a gluten-free / dairy-free / vegan / veg claim the words contradict is dropped (unless the words say
# "gluten-free", "vegan cheese" and so on). Keep NUT_WORDS in step with PF.NUT_WORDS in web/pages/_shared.html.
NUT_WORDS = (r"almond|walnut|pecan|cashew|hazelnut|pistachio|peanut|pine ?nut|macadamia|brazil nut|pesto|praline|marzipan|"
             r"frangipane|nutella|satay|baklava|nougat|gianduja|amaretti|romesco|dukkah|\bnuts?\b|\bnutty\b")
_NUT_FREE = r"\bnut[- ]free\b|\bno nuts\b|\bwithout nuts\b"
_GLUTEN = (r"bread|focaccia|sourdough|bagel|baguette|croissant|pastry|\bpies?\b|\btarts?\b|cake|brownie|cookie|biscuit|"
           r"scone|cracker|pizza|pasta|lasagne|lasagna|spaghetti|macaroni|mac & cheese|mac and cheese|couscous|bulgur|"
           r"tabbouleh|wheat|flour|barley|\brye\b|seitan|\bbeer\b|dumpling|crouton|cheese straw|crumble|pancake|waffle|"
           r"tiramisu")
_GLUTEN_OK = r"gluten[- ]free|\bgf\b|\bcorn tortilla"
_DAIRY = (r"cheese|cheddar|\bbrie\b|feta|halloumi|mozzarella|parmesan|ricotta|mascarpone|(?<!peanut )(?<!nut )butter|"
          r"\bcream\b|creamy|\bmilk\b|yoghurt|yogurt|\bghee\b|custard|tiramisu|scone|cheesecake|\bmousse\b")
_DAIRY_OK = r"vegan|dairy[- ]free|plant[- ]based|\boat\b|\bsoy\b|coconut"
_MEAT = (r"pork|beef|chicken|turkey|\blamb\b|\bham\b|bacon|sausage|chorizo|salami|prosciutto|pepperoni|\bmince\b|steak|"
         r"meatball|chilli con carne|chili con carne|\bfish\b|salmon|tuna|prawn|shrimp|anchov|\bcrab\b|lobster|gelatin|"
         r"\blard\b|\bduck\b|\bveal\b")
_MEAT_OK = r"vegan|vegetarian|veggie|plant[- ]based|meat[- ]free|meatless|\btofu\b|seitan|quorn|\bvege?\b"
_NOT_VEGAN = r"\beggs?\b|mayo|aioli|meringue|pavlova|devilled|\bhoney\b"


def dish_tags(name, note, tags):
    """The tags a dish should carry, given its name and note (see the comment above NUT_WORDS)."""
    words = ("%s %s" % (name or "", note or "")).lower().replace("\u2019", "'")
    has = lambda pat: re.search(pat, words) is not None
    out = [t for t in TAGS if t in (tags or [])]
    if has(NUT_WORDS) and not has(_NUT_FREE) and "nuts" not in out:
        out.append("nuts")
    drop = set()
    if has(_GLUTEN) and not has(_GLUTEN_OK):
        drop.add("gf")
    if has(_DAIRY) and not has(_DAIRY_OK):
        drop.update(("df", "vegan"))
    if has(_MEAT) and not has(_MEAT_OK):
        drop.update(("veg", "vegan"))
    if has(_NOT_VEGAN) and not has(r"vegan"):
        drop.add("vegan")
    return [t for t in TAGS if t in out and t not in drop]
EXTRA = "Something else"          # a menu section every party has, for whatever doesn't fit
MAX_GUESTS, MAX_DISHES, MAX_COMMENTS = 60, 150, 400
MAX_KITTY, KITTY_MAX_AMOUNT = 100, 5000  # rows per party; one "I spent" line at most 5000 (dollars, euros, pounds)
CURRENCIES = ("$", "€", "£")
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


def money_of(p):
    """The party's suggested chip-in {amount, currency, note}, or None (also while the column is missing)."""
    m = C.col(p, "money")
    if not isinstance(m, dict):
        return None
    try:
        amount = round(float(m.get("amount")), 2)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return {"amount": amount, "currency": m.get("currency") if m.get("currency") in CURRENCIES else "$",
            "note": str(m.get("note") or "")[:60]}


def party_dict(p):
    return {"id": p.get_id(), "token": p["token"], "catalog_no": p["catalog_no"], "title": p["title"],
            "blurb": p["blurb"] or "", "location": p["location"] or "", "style": p["style"] or "potluck",
            "cover": p["cover"] or "classic", "cap": p["cap"], "slots": list(p["slots"] or []), "chosen": p["chosen"],
            "chosen_time": p["chosen_time"], "categories": categories(p), "wanted": dict(p["wanted"] or {}),
            "status": p["status"] or "open", "host_name": C.name_of(p["host"]), "demo": bool(p["is_demo"]),
            "outdoors": bool(p["outdoors"]), "wx_place": p["wx_place"],
            "answer_by": C.col(p, "answer_by"), "money": money_of(p),
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
                    "category": d["category"], "name": d["name"], "serves": d["serves"], "tags": dish_tags(d["name"], d["note"], d["tags"]),
                    "note": d["note"] or "", "mine": g is not None and d["guest"] == g,
                    "can_remove": (g is not None and d["guest"] == g) or is_host or admin} for d in dishes],
        "comments": [{"id": c.get_id(), "by": names.get(c["guest"].get_id(), "A guest") if c["guest"] else "A guest",
                      "by_host": c["guest"] is not None and _is_host_row(c["guest"], p), "body": c["body"],
                      "created": C.iso(c["created"]), "mine": g is not None and c["guest"] == g,
                      "can_remove": (g is not None and c["guest"] == g) or is_host or admin} for c in comments],
        "stats": stats(p, guests, dishes),
        "weather": Weather.for_party(p),
        "kitty": kitty_view(p, g, guests, is_host, admin),
    }


def delete_guest(g):
    kitty = C.table("kitty")
    if kitty is not None:
        try:
            for r in list(kitty.search(guest=g)) + list(kitty.search(to_guest=g)):
                r.delete()
        except Exception:
            pass  # the kitty table isn't in the live database yet
    for d in app_tables.dishes.search(guest=g):
        d.delete()
    for c in app_tables.comments.search(guest=g):
        c.delete()
    g.delete()


# ----------------------------------------------------------------------------------------------- the kitty
def _cents(amount):
    try:
        return int(round(float(amount or 0) * 100))
    except (TypeError, ValueError):
        return 0


def kitty_math(people, rows):
    """A fair split and the fewest payments to settle it, all in whole cents.

    people: [{id, name, rsvp, plus}]. Everyone who said yes pays a share of the total: 1 + their extra people.
    rows: [{kind: "spent" | "paid", by: guest id, to: guest id (paid only), cents}]. A spender who isn't coming is
    still paid back. A "paid" row is money that already went from `by` to `to`.
    Each share is rounded to whole cents so the shares add up to the total exactly (largest remainder), so the
    balances always add up to zero and the transfers settle everyone to the cent.
    Returns {total, heads, balances: [{id, name, spent, share, balance}], transfers: [{from_id, from, to_id, to, cents}]}
    (balance > 0: is owed money; < 0: owes money)."""
    names = {x["id"]: x["name"] for x in people}
    shares = {x["id"]: 1 + int(x.get("plus") or 0) for x in people if x.get("rsvp") == "yes"}
    heads = sum(shares.values())
    total = sum(r["cents"] for r in rows if r["kind"] == "spent" and r.get("by"))
    bal, spent, share = {}, {}, {}
    for r in rows:
        by = r.get("by")
        if not by:
            continue
        if r["kind"] == "spent":
            spent[by] = spent.get(by, 0) + r["cents"]
            bal[by] = bal.get(by, 0) + r["cents"]
        elif r["kind"] == "paid" and r.get("to"):
            bal[by] = bal.get(by, 0) + r["cents"]
            bal[r["to"]] = bal.get(r["to"], 0) - r["cents"]
    if heads and total:
        exact = {i: total * s for i, s in shares.items()}  # each share = exact / heads cents
        share = {i: e // heads for i, e in exact.items()}
        left = total - sum(share.values())
        for i in sorted(shares, key=lambda i: (-(exact[i] % heads), str(names.get(i, "")), str(i)))[:left]:
            share[i] += 1
        for i, c in share.items():
            bal[i] = bal.get(i, 0) - c
    cred = {i: c for i, c in bal.items() if c > 0}
    debt = {i: -c for i, c in bal.items() if c < 0}
    transfers = []
    while cred and debt:  # the biggest debtor pays the biggest creditor, again and again
        ci = max(cred, key=lambda i: (cred[i], str(i)))
        di = max(debt, key=lambda i: (debt[i], str(i)))
        amt = min(cred[ci], debt[di])
        transfers.append({"from_id": di, "from": names.get(di, "A guest"), "to_id": ci, "to": names.get(ci, "A guest"),
                          "cents": amt})
        cred[ci] -= amt
        debt[di] -= amt
        if not cred[ci]:
            del cred[ci]
        if not debt[di]:
            del debt[di]
    ids = [x["id"] for x in people if x["id"] in bal or x["id"] in shares]
    balances = [{"id": i, "name": names.get(i, "A guest"), "spent": spent.get(i, 0), "share": share.get(i, 0),
                 "balance": bal.get(i, 0), "heads": shares.get(i, 0)} for i in ids]
    return {"total": total, "heads": heads, "balances": balances, "transfers": transfers}


def kitty_view(p, g, guests, is_host, admin):
    """The kitty section of the party page, or None while the live database has no kitty table."""
    kitty = C.table("kitty")
    if kitty is None:
        return None
    try:
        rows = _by_created(kitty.search(party=p))
    except Exception:
        return None
    names = {x.get_id(): x["name"] for x in guests}
    my_id = g.get_id() if g is not None else None
    math_rows, out = [], []
    for r in rows:
        by = r["guest"].get_id() if r["guest"] else None
        to = r["to_guest"].get_id() if r["to_guest"] else None
        cents = _cents(r["amount"])
        math_rows.append({"kind": r["kind"], "by": by, "to": to, "cents": cents})
        mine = my_id is not None and (by == my_id or (r["kind"] == "paid" and to == my_id))
        out.append({"id": r.get_id(), "kind": r["kind"], "by_id": by, "by": names.get(by, "A guest"), "to_id": to,
                    "to": names.get(to, "") if to else "", "what": r["what"] or "", "cents": cents,
                    "created": C.iso(r["created"]), "can_remove": mine or is_host or admin})
    people = [{"id": x.get_id(), "name": x["name"], "rsvp": x["rsvp"], "plus": int(x["plus"] or 0)} for x in guests]
    m = kitty_math(people, math_rows)
    m["rows"] = out
    return m


def _kitty_table():
    """(kitty table, error reply)."""
    kitty = C.table("kitty")
    if kitty is None:
        return None, C.fail("The kitty switches on after the next app update. Try again later!")
    return kitty, None


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
                              tags=dish_tags(name, dish.get("note"), dish.get("tags")),
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


@anvil.server.callable
def kitty_add(token, secret, what, amount):
    """"I spent ...": something you paid for the party (the wine, the roast), to be shared out fairly."""
    p, g, err = _load(token, secret)
    if err:
        return err
    kitty, err = _kitty_table()
    if err:
        return err
    what = C.text(what, 60)
    if not what:
        return C.fail("What was it for? The wine, the roast...")
    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError):
        return C.fail("How much was it? Type a number, like 24.50.")
    if not 0.01 <= amount <= KITTY_MAX_AMOUNT:
        return C.fail("An amount from 0.01 to %d, please." % KITTY_MAX_AMOUNT)
    if C.rate_limited("kitty_add", 30, 3600):
        return C.fail("That's a lot of shopping in one hour. Please try again later.")
    if len(kitty.search(party=p)) >= MAX_KITTY:
        return C.fail("This kitty is full (%d lines). Time to settle up!" % MAX_KITTY)
    kitty.add_row(party=p, guest=g, kind="spent", what=what, amount=amount, to_guest=None, created=C.now(), is_demo=False)
    _touch(p)
    return C.ok(view=view(p, g))


@anvil.server.callable
def kitty_remove(token, secret, row_id):
    """Take a line out of the kitty: your own (a payment you made or got), or any line for the host or an admin."""
    p, g, err = _load(token, secret, need_guest=False)
    if err:
        return err
    kitty, err = _kitty_table()
    if err:
        return err
    r = C.row_by_id(kitty, row_id)
    if r is None or r["party"] != p:
        return C.ok(view=view(p, g))
    me = C.me()
    mine = g is not None and (r["guest"] == g or (r["kind"] == "paid" and r["to_guest"] == g))
    if not (mine or (me is not None and me == p["host"]) or C.is_admin(me)):
        return C.fail("Only the person who added it (or the host) can take it out.")
    r.delete()
    _touch(p)
    return C.ok(view=view(p, g))


@anvil.server.callable
def kitty_paid(token, secret, from_id, to_id, amount):
    """Mark a settle-up payment as done ("Jo -> Ana $16"). The payer, the person paid or the host may do it, and it has
    to be one of the payments the page shows right now (so a stale page can't mark the wrong amount)."""
    p, g, err = _load(token, secret)
    if err:
        return err
    kitty, err = _kitty_table()
    if err:
        return err
    me = C.me()
    if g.get_id() not in (from_id, to_id) and not (me is not None and me == p["host"]):
        return C.fail("Only the two people in this payment (or the host) can mark it as paid.")
    guests = list(app_tables.guests.search(party=p))
    k = kitty_view(p, g, guests, False, False) or {"transfers": []}
    cents = _cents(amount)
    if not any(t["from_id"] == from_id and t["to_id"] == to_id and t["cents"] == cents for t in k["transfers"]):
        return C.fail("That payment has changed since the page loaded. Have another look.")
    payer, payee = C.row_by_id(app_tables.guests, from_id), C.row_by_id(app_tables.guests, to_id)
    if payer is None or payee is None:
        return C.fail("That payment has changed since the page loaded. Have another look.")
    kitty.add_row(party=p, guest=payer, kind="paid", what="Paid back", amount=cents / 100.0, to_guest=payee,
                  created=C.now(), is_demo=False)
    _touch(p)
    return C.ok(view=view(p, g))
