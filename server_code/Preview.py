"""Party-link preview cards: /p/<token> is the link hosts send (client_code/pf.py party_url).

Chat apps (WhatsApp, iMessage, Slack, Messenger...) never see the part after "#" in planfriday.com/#p/<token>, so that
link always previewed as the generic site card, which reads like an ad. /p/<token> is a real address: it answers with
the party's own Open Graph tags (its catalogue picture, "Soup Night Supper · hosted by Maya", the days or "It's on:
Saturday 7 pm", how many are coming, what's still wanted, the chip-in) and sends browsers straight on to
/#p/<token>, where the app runs as before. Old #p/ links keep working.

- og:url is this /p/<token> address: pointing it at the # address makes Facebook and WhatsApp fall back to the
  generic card. The pictures are 1200x630 catalogue cards in theme/assets/covers/ (tools/make_covers.py).
- Browsers move on with location.replace() only. No <meta http-equiv="refresh">: some preview bots follow it to the
  bare home page and show the generic card again, and the app needs JavaScript anyway.
- Privacy: the card says only what the invitation says. Never guest names, the place or anyone's email; every value
  is HTML-escaped.
- Search engines: noindex (meta tag + X-Robots-Tag header). robots.txt must NOT disallow /p/, or preview bots skip it.
- Unknown links get the generic card and the same redirect (the app then says it can't find the party).
"""
import datetime as dt
import html
import json
import re
import urllib.parse

import anvil
import anvil.server
from anvil.tables import app_tables

from . import common as C
from . import DemoData, Guests, Parties, seo_routes

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PART_WORDS = {"brunch": "brunch", "lunch": "lunch", "afternoon": "afternoon", "dinner": "dinner", "late": "late supper"}


def clock(hm):
    """'19:00' -> '7 pm', '10:30' -> '10:30 am', '12:00' -> 'noon'."""
    try:
        h, m = int(hm[:2]), int(hm[3:5])
    except (TypeError, ValueError):
        return ""
    if (h, m) == (12, 0):
        return "noon"
    return ("%d" % ((h % 12) or 12)) + (":%02d" % m if m else "") + (" am" if h < 12 else " pm")


def _day(key):
    try:
        return dt.date.fromisoformat(key.split("|")[0])
    except (ValueError, AttributeError):
        return None


def slot_words(key, short=True):
    """'2026-11-21|dinner' -> 'Sat dinner' (or 'Saturday dinner')."""
    d = _day(key)
    if d is None:
        return ""
    name = DAYS[d.weekday()]
    return (name[:3] if short else name) + " " + PART_WORDS.get(key.split("|", 1)[1], "")


def _or_list(words):
    words = [w for w in words if w]
    if len(words) <= 1:
        return "".join(words)
    if len(words) > 3:
        return "%s, %s + %d more" % (words[0], words[1], len(words) - 2)
    return ", ".join(words[:-1]) + " or " + words[-1]


def card(p):
    """(title, description, image file, image alt) for a party's preview card. Only what the invitation itself says."""
    guests = list(app_tables.guests.search(party=p))
    dishes = list(app_tables.dishes.search(party=p))
    st = Guests.stats(p, guests, dishes)
    host = (C.name_of(p["host"]) or "the host").split(" ")[0]
    title = "%s · hosted by %s" % (p["title"], host)
    bits = []
    if p["chosen"]:
        d = _day(p["chosen"])
        part = p["chosen"].split("|", 1)[1] if "|" in p["chosen"] else "dinner"
        when = clock(p["chosen_time"] or Parties.PART_START.get(part, "19:00"))
        bits.append("It's on: %s %s" % (DAYS[d.weekday()] if d else "", when))
    else:
        bits.append(_or_list([slot_words(k) for k in (p["slots"] or [])]) or "This weekend")
        by = C.col(p, "answer_by")
        if by and "|" in by and _day(by):
            bits.append("answer by %s %s" % (DAYS[_day(by).weekday()][:3], clock(by.split("|")[1])))
    if p["status"] == "closed":
        bits.append("RSVPs closed")
    bits.append(("%d coming" % st["heads"]) if st["heads"] else "be the first to say yes")
    gaps = [c.lower() for c in Guests.categories(p) if st["menu"].get(c) and st["menu"][c]["have"] < st["menu"][c]["wanted"]]
    if gaps:
        bits.append("still wanted: " + (", ".join(gaps[:3]) + (" + %d more" % (len(gaps) - 3) if len(gaps) > 3 else "")))
    m = Guests.money_of(p)
    if m:
        cents = int(round(m["amount"] * 100))
        amount = ("%d" % (cents // 100)) if cents % 100 == 0 else "%d.%02d" % (cents // 100, cents % 100)
        bits.append("chip in %s%s%s" % (m["currency"], amount, (" " + m["note"]) if m["note"] else ""))
    desc = " · ".join(bits)
    if len(desc) > 200:
        desc = desc[:197].rstrip() + "..."
    cover = p["cover"] if p["cover"] in Parties.COVERS else "classic"
    return title, desc, "covers/%s.png" % cover, "%s, a party from the Plan Friday weekend catalogue" % p["title"]


def preview_html(origin, token):
    """The whole /p/<token> page: Open Graph tags for preview bots, a straight hop to /#p/<token> for people."""
    o = origin.rstrip("/")
    safe = token if isinstance(token, str) and re.match(r"^[A-Za-z0-9_-]{1,60}$", token) else ""
    p = Guests.find_party(safe) if safe else None
    if p is not None:
        title, desc, image, alt = card(p)
        page_title = p["title"] + " · Plan Friday"
    else:
        s = seo_routes.SEO
        title, desc, image, alt = s["title"], s["description"], "og-image.png", s["tagline"]
        page_title = s["title"]
    path = "/p/" + urllib.parse.quote(safe, safe="-_") if safe else "/"
    target = "/#p/" + urllib.parse.quote(safe, safe="-_") if safe else "/"
    e = html.escape
    img = "%s/_/theme/%s" % (o, image)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(page_title)s</title>
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="%(desc)s">
<meta property="og:type" content="website"><meta property="og:site_name" content="Plan Friday">
<meta property="og:title" content="%(title)s"><meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(url)s">
<meta property="og:image" content="%(img)s"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="%(alt)s">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="%(title)s">
<meta name="twitter:description" content="%(desc)s"><meta name="twitter:image" content="%(img)s">
<link rel="icon" href="%(o)s/_/theme/icon-512.png">
<meta name="theme-color" content="#c62a1f">
<style>
:root{--bg:#f2e8d3;--ink:#1f1a14;--red:#c62a1f;color-scheme:light dark}
@media (prefers-color-scheme: dark){:root{--bg:#1a1611;--ink:#f1e6cf;--red:#ff6a50}}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);
font:18px/1.5 Georgia,"Times New Roman",serif;text-align:center;padding:16px;box-sizing:border-box}
a{color:var(--red);font-weight:700}
</style></head>
<body><p>Opening the invitation to <a href="%(target)s">%(name)s</a>&hellip;</p>
<script>location.replace(%(target_js)s);</script>
</body></html>
""" % {"page_title": e(page_title), "desc": e(desc), "title": e(title), "url": e(o + path), "img": e(img), "alt": e(alt),
       "o": e(o), "target": e(target), "name": e(p["title"] if p is not None else "the party"),
       "target_js": json.dumps(target).replace("</", "<\\/")}


def _token_from_path():
    """The token from the request path, for runtimes that don't pass path parameters as keywords."""
    try:
        path = str(anvil.server.request.path or "")
    except Exception:
        return ""
    m = re.search(r"/p/([^/?#]+)", path)
    return urllib.parse.unquote(m.group(1)) if m else ""


ROUTE = getattr(anvil.server, "route", None)
if ROUTE:  # hosted Anvil (python314) has it; the local App Server 1.18 may not, and then serves nothing here
    @ROUTE("/p/:token")
    def party_preview(**params):
        token = params.get("token") or _token_from_path()
        DemoData.ensure_loaded()  # so the sample parties' links work
        body = preview_html(seo_routes.origin(), token)
        return anvil.server.HttpResponse(200, anvil.BlobMedia("text/html; charset=utf-8", body.encode("utf-8")),
                                         headers={"Cache-Control": "public, max-age=300", "X-Robots-Tag": "noindex"})
