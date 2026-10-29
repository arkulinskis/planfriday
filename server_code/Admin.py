"""Admin page callables: overview, users (make admin, disable), parties, demo data. Admins only.
Feedback admin calls live in Feedback.py."""
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import DemoData, Feedback, Parties


@anvil.server.callable(require_user=True)
def admin_overview():
    C.require_admin()
    return {"users": len([u for u in app_tables.users.search() if not u["is_demo"]]),
            "admins": len(app_tables.users.search(is_admin=True)),
            "feedback_new": Feedback.new_count(),
            "parties": len([p for p in app_tables.parties.search() if not p["is_demo"]]),
            "guests": len([g for g in app_tables.guests.search() if not g["is_demo"]]),
            "demo": {"state": DemoData.state(), "counts": DemoData.counts()}}


def _user(u):
    return {"id": u.get_id(), "email": u["email"], "name": C.name_of(u), "is_admin": C.is_admin(u),
            "enabled": u["enabled"] is not False, "joined": C.iso(u["signed_up"]), "last_seen": C.iso(u["last_seen"])}


@anvil.server.callable(require_user=True)
def list_users(query=None):
    C.require_admin()
    query = C.text(query, 80).lower()
    rows = [u for u in app_tables.users.search(tables.order_by("signed_up", ascending=False)) if not u["is_demo"]]
    if query:
        rows = [u for u in rows if query in (u["email"] or "").lower() or query in (u["display_name"] or "").lower()]
    return {"users": [_user(u) for u in rows[:200]], "total": len(rows)}


@anvil.server.callable(require_user=True)
def set_admin(user_id, flag):
    me = C.require_admin()
    u = C.row_by_id(app_tables.users, user_id)
    if u is None:
        return C.fail("That account no longer exists.")
    if u == me and not flag:
        return C.fail("You can't remove your own admin rights.")
    u["is_admin"] = bool(flag)
    return C.ok(user=_user(u))


@anvil.server.callable(require_user=True)
def set_enabled(user_id, flag):
    me = C.require_admin()
    u = C.row_by_id(app_tables.users, user_id)
    if u is None:
        return C.fail("That account no longer exists.")
    if u == me:
        return C.fail("You can't disable your own account.")
    u["enabled"] = bool(flag)
    return C.ok(user=_user(u))


@anvil.server.callable(require_user=True)
def demo_load():
    C.require_admin()
    DemoData.load()
    return C.ok(demo={"state": DemoData.state(), "counts": DemoData.counts()})


@anvil.server.callable(require_user=True)
def demo_remove():
    C.require_admin()
    DemoData.remove()
    return C.ok(demo={"state": DemoData.state(), "counts": DemoData.counts()})


@anvil.server.callable(require_user=True)
def admin_parties(query=None):
    """Every party, newest first, with its host and how busy it is (for moderation)."""
    C.require_admin()
    query = C.text(query, 80).lower()
    rows = list(app_tables.parties.search(tables.order_by("created", ascending=False)))
    out = []
    for p in rows:
        host = p["host"]
        if query and query not in (p["title"] or "").lower() and query not in C.name_of(host).lower()                 and query not in ((host["email"] if host else "") or "").lower():
            continue
        out.append({"id": p.get_id(), "token": p["token"], "title": p["title"], "host": C.name_of(host),
                    "host_email": host["email"] if host else None, "created": C.iso(p["created"]),
                    "guests": len(app_tables.guests.search(party=p)), "dishes": len(app_tables.dishes.search(party=p)),
                    "comments": len(app_tables.comments.search(party=p)), "demo": bool(p["is_demo"]),
                    "status": p["status"] or "open"})
    return {"parties": out[:200], "total": len(out)}


@anvil.server.callable(require_user=True)
def admin_delete_party(party_id):
    C.require_admin()
    p = C.row_by_id(app_tables.parties, party_id)
    if p is None:
        return C.ok()
    Parties.delete_party(p)
    return C.ok()
