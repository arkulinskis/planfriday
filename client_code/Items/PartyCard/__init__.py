from anvil import *

from ._anvil_designer import PartyCardTemplate
from ... import pf, router, state


class PartyCard(PartyCardTemplate):
    """A party on the home page (Parties.summary): picture, who hosts, its status stamp, seats, menu, weather."""

    def __init__(self, **properties):
        super().__init__(**properties)
        s = self.item
        past = pf.all_past(s)
        d = self.dom_nodes
        d["card"].setAttribute("href", router.href("p", s["token"]))
        d["card"].classList.toggle("past", past)
        self.cover_box.classes["red"] = bool(s.get("chosen"))
        d["no"].textContent = (s.get("catalog_no") or "") + (" · You host" if s.get("is_host") else " · " + (s.get("host_name") or "")) + (" · Past" if past else "")
        d["title"].textContent = s["title"]
        if s.get("chosen"):
            d["status"].className, d["status"].textContent = "pf-stamp good", "It's on · " + pf.slot_label(s["chosen"])
        elif s.get("best"):
            d["status"].className, d["status"].textContent = "pf-label", "Leading: " + pf.slot_label(s["best"])
        else:
            d["status"].className, d["status"].textContent = "pf-label", "Waiting for answers"
        d["seats"].textContent = state.plural(s["heads"], "seat") + " taken"
        d["maybe"].textContent = "%d maybe" % s["maybe"]
        d["menu"].textContent = "%d of %d filled" % (s["filled"], s["wanted_total"])
        self.wx_row.visible = bool(s.get("wx"))
        self.closed.visible = s.get("status") == "closed"
