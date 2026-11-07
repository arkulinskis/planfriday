from anvil import *

from ._anvil_designer import SheetGuestTemplate


class SheetGuest(SheetGuestTemplate):
    """A guest on the order sheet: ☐ name +n · diet."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.row.classes["muted"] = bool(self.item.get("maybe"))
        self.dom_nodes["text"].textContent = self.item["text"]
        self.dom_nodes["diet"].textContent = ("· " + self.item["diet"]) if self.item.get("diet") else ""
