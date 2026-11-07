from anvil import *

from ... import state
from ._anvil_designer import StyleChoiceTemplate


class StyleChoice(StyleChoiceTemplate):
    """Potluck / Host cooks / Bring your own. item = {key, name, desc, on}; a click raises x-style(key)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b = self.dom_nodes["btn"]
        self.dom_nodes["name"].textContent = self.item["name"]
        self.dom_nodes["desc"].textContent = self.item["desc"]
        b.classList.toggle("on", bool(self.item.get("on")))
        b.setAttribute("aria-pressed", "true" if self.item.get("on") else "false")
        b.setAttribute("data-key", self.item["key"])

    def btn_click(self, event):
        if self.parent:
            panel, key = self.parent, self.item["key"]
            panel.raise_event("x-style", key=key)
            state.refocus(panel, key)
