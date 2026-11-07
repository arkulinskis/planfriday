from anvil import *

from ... import state
from ._anvil_designer import CoverPickTemplate


class CoverPick(CoverPickTemplate):
    """A picture in the party form's picker. item = {key, name, on}; a click raises x-cover(key)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b = self.dom_nodes["btn"]
        self.dom_nodes["name"].textContent = self.item["name"]
        b.classList.toggle("on", bool(self.item.get("on")))
        b.setAttribute("aria-pressed", "true" if self.item.get("on") else "false")
        b.setAttribute("data-key", self.item["key"])

    def btn_click(self, event):
        if self.parent:
            panel, key = self.parent, self.item["key"]
            panel.raise_event("x-cover", key=key)
            state.refocus(panel, key)
