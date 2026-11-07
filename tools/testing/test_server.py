"""Server tests against the strict mock of Anvil (tools/testing/mock).

    python -I tools/testing/test_server.py          -> prints ALL OK, or the first failure

call(name, ...) runs a server function the way the browser does: by name, with require_user enforced,
and the reply must be JSON (a datetime or a row in a reply fails here, like it would break the page).
Add tests for every new server function: the happy path, bad input, and someone who isn't allowed.
"""
import datetime as dt
import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
_tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copytree(PROJECT / "server_code", _tmp / "app")
(_tmp / "app" / "__init__.py").write_text("")
os.environ["ANVIL_APP_YAML"] = str(PROJECT / "anvil.yaml")  # the mock's tables follow the app's own schema
sys.path[:0] = [str(HERE / "mock"), str(_tmp)]
import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
from anvil.tables import app_tables as T  # noqa: E402
import anvil.http  # noqa: E402
sys.path.insert(0, str(HERE))
import fake_weather  # noqa: E402
fake_weather.install(anvil.http.REPLIES)  # Open-Meteo without the network

M = {p.stem: importlib.import_module("app." + p.stem) for p in sorted((PROJECT / "server_code").glob("*.py"))}
now = dt.datetime.now(dt.timezone.utc)


def call(name, *args):
    r = anvil.server.call(name, *args)
    json.dumps(r)  # strict: must be JSON-able
    return r


def as_user(row):
    anvil.users.CURRENT[0] = row
    anvil.server.session.use(row.get_id() if row is not None else None)


def denied(name, *args):
    try:
        call(name, *args)
    except anvil.server.PermissionDenied:
        return True
    return False


def ok(r, msg=""):
    assert isinstance(r, dict) and r.get("ok"), (msg, r)
    return r


def bad(r, msg=""):
    assert isinstance(r, dict) and r.get("ok") is False and r.get("error"), (msg, r)
    return r


def person(email, name=None, **kw):
    return T.users.add_row(email=email, enabled=True, signed_up=now, display_name=name, **kw)


# ---------------------------------------------------------------------------------- accounts
admin = person("arkulinskis@gmail.com", "The Admin")
ana = person("ana@example.com", "Ana")
bob = person("bob@example.com")

as_user(None)
assert call("get_me") is None
assert denied("update_profile", "X")
as_user(admin)
assert call("get_me")["is_admin"] is True, "ADMIN_EMAILS become admins on first sign-in"
as_user(ana)
me = call("get_me")
assert me["name"] == "Ana" and me["is_admin"] is False
assert ana["last_seen"] is not None
as_user(bob)
assert call("get_me")["name"] == "Bob", "a name comes from the email when none is set"
bad(call("update_profile", " x "))
assert ok(call("update_profile", "  Bob   Stone "))["me"]["name"] == "Bob Stone"

# ---------------------------------------------------------------------------------- feedback
as_user(None)
bad(call("submit_feedback", "bug", "hi"))
ok(call("submit_feedback", "bug", "The button is broken", "guest@example.com", {"page": "#home", "evil": "x" * 9999}))
fb = T.feedback.search()[0]
assert fb["name"] == "Guest" and fb["email"] == "guest@example.com" and "evil" not in fb["context"] and fb["status"] == "new"
for i in range(4):
    ok(call("submit_feedback", "idea", "Idea number %d" % i))
bad(call("submit_feedback", "idea", "One too many this hour"), "rate limit")
as_user(ana)
ok(call("submit_feedback", "nonsense-kind", "Signed-in feedback"))
assert T.feedback.get(message="Signed-in feedback")["kind"] == "other"
assert denied("list_feedback")
as_user(admin)
lst = call("list_feedback")
assert lst["counts"]["new"] == 6 and len(lst["items"]) == 6
fid = lst["items"][0]["id"]
ok(call("set_feedback_status", fid, "done", "Fixed it"))
assert call("list_feedback", "done")["items"][0]["note"] == "Fixed it"
bad(call("set_feedback_status", fid, "weird"))
bad(call("set_feedback_status", "nope", "done"))
ok(call("delete_feedback", fid))
assert len(call("list_feedback")["items"]) == 5

# ---------------------------------------------------------------------------------- admin
as_user(ana)
for fn, args in [("admin_overview", ()), ("list_users", ()), ("set_admin", (bob.get_id(), True)), ("demo_load", ()), ("demo_remove", ())]:
    assert denied(fn, *args), fn
as_user(admin)
ov = call("admin_overview")
assert ov["users"] == 3 and ov["admins"] == 1 and ov["feedback_new"] == 5
assert len(call("list_users")["users"]) == 3 and len(call("list_users", "bob")["users"]) == 1
ok(call("set_admin", bob.get_id(), True))
assert bob["is_admin"] is True
bad(call("set_admin", admin.get_id(), False), "can't remove your own admin")
ok(call("set_enabled", bob.get_id(), False))
assert bob["enabled"] is False
bad(call("set_enabled", admin.get_id(), False))
ok(call("set_enabled", bob.get_id(), True))
ok(call("set_admin", bob.get_id(), False))
assert bob["is_admin"] is False

# ---------------------------------------------------------------------------------- demo data
DD = M["DemoData"]
as_user(None)
sample = call("party_view", "sample")
assert DD.state() == "loaded" and sample["ok"] and sample["view"]["party"]["demo"], "demo loads on the first visit"
sv = sample["view"]
assert sv["me"] is None and not sv["is_host"] and len(sv["guests"]) == 7 and sv["stats"]["best"] == sv["party"]["slots"][1]
assert "email" not in json.dumps(sv), "the party page never shows emails"
assert sv["party"]["slots"][0].split("|")[0] == DD.weekend_friday().isoformat(), "the sample sits on the coming weekend"
assert sv["stats"]["diets"].get("nutfree") == 1 and sv["stats"]["menu"]["Soup"] == {"wanted": 3, "have": 2}
bad(call("guest_join", "sample", None, "Vandal"), "sample parties can't be changed")
assert call("party_view", "nope-not-a-party")["missing"] is True
assert call("party_view", "<script>")["missing"] is True
assert DD.weekend_friday(dt.date(2026, 10, 28)) == dt.date(2026, 10, 30)   # Wednesday -> this Friday
assert DD.weekend_friday(dt.date(2026, 11, 1)) == dt.date(2026, 10, 30)    # Sunday -> the Friday just gone
C_ = M["common"]
C_.set_setting("demo_week", "2001-01-05")
call("party_view", "sample")
assert C_.get_setting("demo_week") == DD.weekend_friday().isoformat(), "a new week moves the demo to the new weekend"

# ---------------------------------------------------------------------------------- hosting
fri = DD.weekend_friday()


def slot(off, part):
    return "%s|%s" % ((fri + dt.timedelta(days=off)).isoformat(), part)


FORM = {"title": "Taco Saturday", "blurb": "Bring a salsa", "location": "My place", "style": "potluck", "cover": "tacos",
        "cap": 6, "slots": [slot(1, "dinner"), slot(0, "dinner"), slot(1, "dinner"), "2026-13-45|dinner", slot(2, "teatime"), 7],
        "categories": ["Fillings", "Salsa", "salsa", "", "Dessert"], "wanted": {"Fillings": 2, "Salsa": "x", "Dessert": 99}}
assert denied("create_party", FORM)
assert denied("get_home")
as_user(ana)
bad(call("create_party", dict(FORM, title=" ")))
bad(call("create_party", dict(FORM, slots=[])))
bad(call("create_party", dict(FORM, cap=500)))
bad(call("create_party", "nonsense"))
made = ok(call("create_party", FORM))
party = T.parties.get_by_id(made["id"])
assert party["slots"] == [slot(0, "dinner"), slot(1, "dinner")], "slots are cleaned, de-duplicated and sorted"
assert party["categories"] == ["Fillings", "Salsa", "Dessert"] and party["wanted"]["Dessert"] == 20 and party["wanted"]["Salsa"] == 1
assert party["catalog_no"].startswith("No. ") and len(made["token"]) >= 10
TOK, PID = made["token"], made["id"]
home = call("get_home")
assert home["hosting"][0]["title"] == "Taco Saturday" and home["hosting"][0]["heads"] == 1 and home["sample"] == "sample"
v = ok(call("party_view", TOK))["view"]
assert v["is_host"] and v["me"]["is_host"] and v["me"]["rsvp"] == "yes", "the host is on their own guest list"
assert "Something else" in v["party"]["categories"]
form = ok(call("get_party_form", PID))["party"]
assert form["title"] == "Taco Saturday" and "Something else" not in form["categories"]
as_user(bob)
bad(call("get_party_form", PID), "only the host sees the edit form")
bad(call("update_party", PID, FORM))
bad(call("lock_slot", PID, slot(0, "dinner")))
bad(call("remove_party", PID))
bad(call("set_party_status", PID, "closed"))

# ---------------------------------------------------------------------------------- guests without an account
as_user(None)
bad(call("guest_join", TOK, None, "  "), "a guest needs a name")
j = ok(call("guest_join", TOK, None, "Carla", "yes", 2))
SEC = j["secret"]
assert SEC and len(SEC) > 20 and T.guests.get(name="Carla")["secret_hash"] != SEC, "only the secret's hash is stored"
assert j["view"]["me"]["name"] == "Carla" and j["view"]["stats"]["heads"] == 4
assert call("party_view", TOK)["view"]["me"] is None, "without the secret you're a stranger"
assert call("party_view", TOK, "x" * 30)["view"]["me"] is None
assert call("party_view", TOK, SEC)["view"]["me"]["name"] == "Carla"
bad(call("guest_join", TOK, None, "Dora", "yes", 3), "the cap (6) is respected")
dora = ok(call("guest_join", TOK, None, "Dora", "maybe"))
DSEC = dora["secret"]
bad(call("guest_save", TOK, DSEC, {"rsvp": "yes", "plus": 2}), "saying yes with +2 goes over the cap")
ok(call("guest_save", TOK, DSEC, {"rsvp": "yes", "plus": 1}))
bad(call("guest_save", TOK, DSEC, {"rsvp": "sure"}))
bad(call("guest_save", "nope-not-a-party", DSEC, {"rsvp": "yes"}))
bad(call("guest_save", TOK, None, {"rsvp": "no"}), "you need to join first")
s1 = ok(call("guest_save", TOK, SEC, {"avail": {slot(0, "dinner"): "no", slot(1, "dinner"): "yes", "2030-01-01|dinner": "yes"},
                                        "diet": ["veg", "rocks"], "name": "Carla B."}))["view"]
assert s1["me"]["avail"] == {slot(0, "dinner"): "no", slot(1, "dinner"): "yes"} and s1["me"]["diet"] == ["veg"]
assert s1["stats"]["best"] == slot(1, "dinner") and s1["stats"]["slots"][slot(1, "dinner")]["yes"] == [s1["me"]["id"]]
s1 = ok(call("guest_save", TOK, SEC, {"avail": {slot(0, "dinner"): ""}}))["view"]
assert slot(0, "dinner") not in s1["me"]["avail"], "an empty answer clears it"

# ---------------------------------------------------------------------------------- menu + comments
bad(call("dish_add", TOK, SEC, {"category": "Wine", "name": "Rioja"}), "only the party's menu sections")
bad(call("dish_add", TOK, SEC, {"category": "Salsa", "name": "x"}))
bad(call("dish_add", TOK, None, {"category": "Salsa", "name": "Salsa verde"}))
dv = ok(call("dish_add", TOK, SEC, {"category": "Salsa", "name": "Salsa verde", "serves": "999", "tags": ["vegan", "evil"], "note": "mild"}))["view"]
dish = dv["dishes"][0]
assert dish["by"] == "Carla B." and dish["serves"] == 50 and dish["tags"] == ["vegan"] and dish["mine"] and dish["can_remove"]
assert dv["stats"]["menu"]["Salsa"]["have"] == 1 and dv["stats"]["filled"] == 1
ok(call("dish_add", TOK, SEC, {"category": "Something else", "name": "Paper plates"}))
bad(call("dish_remove", TOK, DSEC, dish["id"]), "can't take someone else's dish off the menu")
ok(call("dish_remove", TOK, None, "bogus-id"))
bad(call("comment_add", TOK, SEC, "   "))
bad(call("comment_add", TOK, None, "Hello"), "comments need a name on the list")
cv = ok(call("comment_add", TOK, DSEC, "Can't wait! " + "x" * 900))["view"]
com = cv["comments"][0]
assert com["by"] == "Dora" and len(com["body"]) == 600 and com["mine"]
bad(call("comment_remove", TOK, SEC, com["id"]), "can't delete someone else's comment")

# ---------------------------------------------------------------------------------- the host decides
as_user(ana)
hv = ok(call("party_view", TOK))["view"]
assert all(d["can_remove"] for d in hv["dishes"]) and all(c["can_remove"] for c in hv["comments"])
bad(call("lock_slot", PID, "2030-01-01|dinner"))
lv = ok(call("lock_slot", PID, slot(1, "dinner"), "19:30"))["view"]
assert lv["party"]["chosen"] == slot(1, "dinner") and lv["party"]["chosen_time"] == "19:30"
assert ok(call("lock_slot", PID, slot(1, "dinner"), "25:99"))["view"]["party"]["chosen_time"] is None
ok(call("lock_slot", PID, slot(1, "dinner"), "19:30"))
ok(call("set_party_status", PID, "closed"))
bad(call("set_party_status", PID, "maybe"))
as_user(None)
bad(call("guest_join", TOK, None, "Late Larry"), "closed parties take no new names")
bad(call("guest_save", TOK, DSEC, {"rsvp": "no"}), "closed parties freeze RSVPs")
ok(call("comment_add", TOK, DSEC, "Still allowed to say thanks"))
as_user(ana)
ok(call("set_party_status", PID, "open"))
ok(call("comment_remove", TOK, None, com["id"]), "the host can delete any comment")
edited = dict(FORM, title="Taco Saturday II", slots=[slot(0, "dinner")])
ok(call("update_party", PID, edited))
assert party["title"] == "Taco Saturday II" and party["chosen"] is None, "dropping the chosen slot unlocks the day"
carla = T.guests.get(name="Carla B.")
bad(call("host_remove_guest", PID, T.guests.get(party=party, user=ana).get_id()), "the host stays on the list")
rv = ok(call("host_remove_guest", PID, carla.get_id()))["view"]
assert all(g["name"] != "Carla B." for g in rv["guests"]) and not T.dishes.search(guest=carla), "removing a guest removes their dishes"

# ---------------------------------------------------------------------------------- signed-in guests + forgetting
as_user(bob)
bj = ok(call("guest_join", TOK, None, "Bob", "maybe"))
assert bj["view"]["me"]["member"] and call("party_view", TOK)["view"]["me"]["name"] == "Bob", "accounts are remembered without a secret"
assert any(i["title"] == "Taco Saturday II" for i in call("get_home")["invited"])
as_user(None)
anon = ok(call("guest_join", TOK, None, "Eve", "yes"))["secret"]
as_user(bob)
ok(call("guest_forget", TOK, None))
assert call("party_view", TOK, anon)["view"]["me"]["name"] == "Eve" and T.guests.get(name="Eve")["user"] == bob, \
    "joining as a guest and signing in later keeps your place"
as_user(ana)
bad(call("guest_forget", TOK, None), "the host can't leave their own party")

# ---------------------------------------------------------------------------------- weather check (fake Open-Meteo)
W = M["Weather"]
assert sv["weather"]["place"].startswith("Montréal") and sv["weather"]["slots"], "the sample party has a weather check"
fri_w = sv["weather"]["slots"][sv["party"]["slots"][0]]
assert fri_w["code"] in (0, 1) and fri_w["hour"] == 19 and fri_w["rain"] == 5, "Friday dinner: clear, at 7 pm"
assert call("party_view", "sample-dumplings")["view"]["weather"]["outdoors"] is True
as_user(None)
assert denied("weather_lookup", "Paris")
as_user(ana)
assert ok(call("weather_lookup", "  paris, france "))["place"] == "Paris, Île-de-France, France", "only the town name is looked up"
bad(call("weather_lookup", "Nowhere"))
bad(call("weather_lookup", "Offline"), "a dead weather service is a polite error")
bad(call("weather_lookup", "x"))
bad(call("update_party", PID, dict(edited, wx_place="Nowhere")), "an unknown town is refused")
ok(call("update_party", PID, dict(edited, wx_place="Riga", outdoors=True)))
assert party["wx_place"] == "Riga, Latvia" and party["wx_lat"] == 56.946 and party["outdoors"] is True
n = len(anvil.http.CALLS)
wv = ok(call("party_view", TOK))["view"]["weather"]
assert wv["place"] == "Riga, Latvia" and wv["outdoors"] and wv["ok"] and party["slots"][0] in wv["slots"]
assert len(anvil.http.CALLS) == n + 1, "one forecast fetch"
call("party_view", TOK)
assert len(anvil.http.CALLS) == n + 1, "the forecast is cached for an hour"
ok(call("update_party", PID, dict(edited, wx_place="Riga, Latvia", outdoors=True)))
assert len(anvil.http.CALLS) == n + 1, "an unchanged town isn't looked up again"
party["weather"] = dict(party["weather"], at=(now - dt.timedelta(hours=2)).isoformat())
fake_weather.FAIL["on"] = True
wv = call("party_view", TOK)["view"]["weather"]
assert not wv["ok"] and wv["slots"], "if Open-Meteo is down, the old forecast stays"
fake_weather.FAIL["on"] = False
lock = ok(call("lock_slot", PID, party["slots"][0], "13:30"))["view"]["weather"]
assert lock["slots"][party["slots"][0]]["hour"] == 13, "a locked-in time moves the forecast to that hour"
card = [h for h in call("get_home")["hosting"] if h["id"] == PID][0]
assert card["wx"] and card["wx"]["hour"] == 13, "home cards show the cached forecast for the chosen day"
mk = ok(call("create_party", dict(FORM, wx_place="Offline")))
assert mk["note"] and T.parties.get_by_id(mk["id"])["wx_lat"] is None, "a dead weather service doesn't block a new party"
ok(call("remove_party", mk["id"]))
ok(call("update_party", PID, dict(edited, wx_place="", outdoors=True)))
assert party["wx_lat"] is None and call("party_view", TOK)["view"]["weather"] is None, "clearing the town turns the check off"
ok(call("update_party", PID, dict(edited, wx_place="Riga", outdoors=True)))
assert W.slot_forecast(party, "2001-01-05|dinner", party["weather"]) is None, "days out of range have no forecast"

# ---------------------------------------------------------------------------------- run it again + delete
dup = ok(call("duplicate_party", PID))
copy = T.parties.get_by_id(dup["id"])
assert copy["title"] == "Taco Saturday II" and copy["token"] != TOK and copy["slots"][0] > party["slots"][0]
assert len(T.guests.search(party=copy)) == 1, "a copy starts with just the host"
samp = T.parties.get(token="sample")
sc = T.parties.get_by_id(ok(call("duplicate_party", samp.get_id()))["id"])
def _wk(k, w):  # a slot key moved by w weeks
    return "%s|%s" % ((dt.date.fromisoformat(k.split("|")[0]) + dt.timedelta(weeks=w)).isoformat(), k.split("|")[1])
# on a weekend the sample's Friday may have passed, and then the copy moves to next weekend
assert sc["host"] == ana and not sc["is_demo"] and sc["slots"] in (samp["slots"], [_wk(k, 1) for k in samp["slots"]]), \
    "a sample can be copied into your own party"
as_user(bob)
bad(call("duplicate_party", PID), "only the host runs it again")
bad(call("remove_party", copy.get_id()))
as_user(ana)
ok(call("remove_party", copy.get_id()))
assert T.parties.get_by_id(dup["id"]) is None and not T.guests.search(party=copy)

# ---------------------------------------------------------------------------------- admin: parties + demo data
as_user(ana)
assert denied("admin_parties") and denied("admin_delete_party", PID)
as_user(admin)
ov = call("admin_overview")
assert ov["parties"] == 2 and ov["demo"]["counts"]["parties"] == 3
ap = call("admin_parties")
assert ap["total"] == 5 and ap["parties"][0]["host_email"] and len(call("admin_parties", "taco")["parties"]) == 1
ok(call("demo_remove"))
assert DD.state() == "removed" and not T.parties.search(is_demo=True) and not T.users.search(is_demo=True)
assert T.parties.get(token=TOK) is not None, "removing demo data keeps real parties"
as_user(None)
assert call("party_view", "sample")["missing"] and DD.state() == "removed", "removed demo data doesn't come back by itself"
as_user(admin)
ok(call("demo_load"))
ok(call("demo_load"))
assert len(T.parties.search(is_demo=True)) == 3, "reloading replaces the demo instead of doubling it"
ok(call("admin_delete_party", sc.get_id()))
assert T.parties.get_by_id(sc.get_id()) is None

# ---------------------------------------------------------------------------------- Privacy & Terms
if "legal_server" in M:
    as_user(ana)
    st = call("legal_state")
    assert st["signedIn"] and st["accepted_version"] is None
    ok(call("legal_accept", st["version"], "signup"))
    assert ana["legal_source"] == "signup" and call("legal_state")["accepted_version"] == st["version"]

# ---------------------------------------------------------------------------------- every callable is covered by a permission check
# A callable that changes data without require_user / a C.require_* check is a security hole. List the public ones here.
PUBLIC = {"get_me", "submit_feedback", "legal_state", "legal_accept",
          # the party link works without an account (Guests.py checks the link and the guest's secret)
          "party_view", "guest_join", "guest_save", "guest_forget", "dish_add", "dish_remove", "comment_add", "comment_remove"}
for name, (f, need) in sorted(anvil.server.CALLABLES.items()):
    if name in PUBLIC:
        continue
    assert need, "%s is callable by anyone: add require_user=True (or list it in PUBLIC in test_server.py)" % name

# ---------------------------------------------------------------------------------- dish tags follow the dish's words (allergy safety)
G_ = M["Guests"]
for nm, note, tags, want in [
        ("Green beans with almonds", "", ["veg", "vegan", "gf", "df"], ["veg", "vegan", "gf", "df", "nuts"]),
        ("Basil pesto pasta", "", ["veg", "gf"], ["veg", "nuts"]),
        ("Nut-free pesto pasta", "", ["veg"], ["veg"]),
        ("Coconut rice", "", ["vegan", "gf"], ["vegan", "gf"]),
        ("Peanut butter cookies", "", ["df"], ["df", "nuts"]),
        ("Gluten-free brownies", "made with almond flour", ["gf"], ["gf", "nuts"]),
        ("Garlic bread", "", ["veg", "gf"], ["veg"]),
        ("Mac & cheese", "", ["veg", "df", "vegan"], ["veg"]),
        ("Vegan mac & cheese", "cashew sauce", ["veg", "vegan", "df"], ["veg", "vegan", "df", "nuts"]),
        ("Chilli con carne", "", ["veg", "gf", "spicy"], ["gf", "spicy"]),
        ("Honey carrots", "", ["veg", "vegan", "gf"], ["veg", "gf"]),
        ("Pavlova", "", ["vegan", "gf"], ["gf"]),
        ("Corn on the cob", "", ["vegan", "gf"], ["vegan", "gf"])]:
    assert G_.dish_tags(nm, note, tags) == want, (nm, G_.dish_tags(nm, note, tags), want)
# every dish idea we suggest that names a nut gets "Has nuts"; the demo menus are already consistent
shared_ = (pathlib.Path(__file__).resolve().parents[2] / "client_code" / "pf.py").read_text(encoding="utf-8")
ideas_ = shared_[shared_.index("SUGGEST = ["):shared_.index("def suggest")]
assert "Green beans with almonds" in ideas_ and "nuts" in G_.dish_tags("Green beans with almonds", "", [])
assert len(list(T.dishes.search())) > 5, "the demo menus are loaded"
for d_ in T.dishes.search():
    assert G_.dish_tags(d_["name"], d_["note"], d_["tags"]) == [t for t in G_.TAGS if t in (d_["tags"] or [])], ("demo dish tags", d_["name"], d_["tags"])

print("ALL OK (%d server functions)" % len(anvil.server.CALLABLES))
