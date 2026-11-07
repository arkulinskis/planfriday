from anvil import *

from ._anvil_designer import GuestRowTemplate
from ... import state


class GuestRow(GuestRowTemplate):
    """A guest on the party page's list: initials, name (+ extra people), host / diet badges, the host's remove."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        d = self.dom_nodes
        d["chip"].className = "pf-chip" + (" maybe" if it.get("kind") else "") + (" me" if it.get("mine") else "")
        d["chip"].textContent = state.initials(it["name"])
        d["name"].textContent = it["name"]
        d["plus"].textContent = (" +%d" % it["plus"]) if it.get("plus") else ""
        d["you"].textContent = " (you)" if it.get("mine") else ""
        self.host_badge.visible = bool(it.get("is_host"))
        diet = it.get("diet") or ""
        self.diet_badge.visible = bool(diet)
        d["diet"].textContent = diet if len(diet) <= 14 else diet[:14] + "…"
        state.set_attr(self.diet_badge, "title", diet)
        self.kick_button.visible = bool(it.get("kick"))
        state.set_control_attr(self.kick_button, "aria-label", "Remove " + it["name"])

    @handle("kick_button", "click")
    def kick_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-kick", id=self.item["id"], name=self.item["name"])
