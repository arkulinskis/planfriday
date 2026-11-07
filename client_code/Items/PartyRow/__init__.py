from anvil import *

from ._anvil_designer import PartyRowTemplate
from ... import router, state


class PartyRow(PartyRowTemplate):
    """Admin → Parties: one party with its host and how busy it is; Delete (admin_delete_party)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p = self.item
        d = self.dom_nodes
        d["link"].setAttribute("href", router.href("p", p["token"]))
        d["link"].textContent = p["title"]
        self.sample_badge.visible = bool(p.get("demo"))
        self.closed_badge.visible = p.get("status") == "closed"
        d["who"].textContent = " · ".join(x for x in [p.get("host") or "", p.get("host_email") or "", state.short_date(p.get("created"))] if x)
        d["counts"].textContent = " · ".join([state.plural(p["guests"], "guest"), state.plural(p["dishes"], "dish", "dishes"),
                                             state.plural(p["comments"], "note")])

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if confirm("Its guest list, menu and notes go too, and the link stops working.", title="Delete this party?",
                   buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            if state.call("admin_delete_party", self.item["id"]):
                state.toast("Deleted", "ok")
                if self.parent:
                    self.parent.raise_event("x-changed")
