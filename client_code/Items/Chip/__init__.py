from anvil import *

from ._anvil_designer import ChipTemplate
from ... import state


class Chip(ChipTemplate):
    """A guest's initials in a circle. item = {name, kind ("" | "maybe"), me (bool)}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        c = self.dom_nodes["chip"]
        c.className = "pf-chip" + (" " + it["kind"] if it.get("kind") else "") + (" me" if it.get("me") else "")
        c.textContent = state.initials(it.get("name"))
        words = (it.get("name") or "?") + (" (maybe)" if it.get("kind") == "maybe" else "")
        c.setAttribute("title", words)
        c.setAttribute("aria-label", words)
        c.setAttribute("role", "img")
