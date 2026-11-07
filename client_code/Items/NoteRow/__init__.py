from anvil import *

from ._anvil_designer import NoteRowTemplate
from ... import state


class NoteRow(NoteRowTemplate):
    """A letter to the host (the party's guestbook). Raises x-delnote(id)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.card.classes["host"] = bool(it.get("by_host"))
        self.host_badge.visible = bool(it.get("by_host"))
        self.dom_nodes["by"].textContent = it["by"]
        self.dom_nodes["when"].textContent = state.ago(it.get("created"))
        self.dom_nodes["when"].setAttribute("datetime", it.get("created") or "")
        self.x_button.visible = bool(it.get("removable"))

    @handle("x_button", "click")
    def x_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-delnote", id=self.item["id"])
