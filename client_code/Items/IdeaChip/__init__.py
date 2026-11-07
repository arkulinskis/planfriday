from anvil import *

from ._anvil_designer import IdeaChipTemplate


class IdeaChip(IdeaChipTemplate):
    """A catalogue idea in the party form's "Start from the catalogue" strip. item = {key, name, cover, on}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b = self.dom_nodes["btn"]
        self.dom_nodes["name"].textContent = self.item["name"]
        b.classList.toggle("on", bool(self.item.get("on")))
        b.setAttribute("aria-pressed", "true" if self.item.get("on") else "false")
        b.setAttribute("data-key", self.item["key"])

    def btn_click(self, event):
        if self.parent:
            self.parent.raise_event("x-idea", key=self.item["key"])
