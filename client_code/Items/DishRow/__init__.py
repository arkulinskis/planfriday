from anvil import *

from ._anvil_designer import DishRowTemplate
from ... import state


class DishRow(DishRowTemplate):
    """A dish someone is bringing: name ..... who, its tags, a note, and remove (theirs, or the host's)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.dom_nodes["name"].textContent = it["name"]
        self.dom_nodes["by"].textContent = it["by"]
        self.x_button.visible = bool(it.get("can_remove"))
        state.set_control_attr(self.x_button, "aria-label", "Take %s off the menu" % it["name"])
        self.tags_panel.items = it["tags"]
        self.tags_panel.visible = bool(it["tags"])
        self.note_part.visible = bool(it.get("note"))
        self.dom_nodes["note"].textContent = it.get("note") or ""

    @handle("x_button", "click")
    def x_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-deldish", id=self.item["id"])
