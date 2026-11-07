from anvil import *

from ._anvil_designer import SheetRowTemplate


class SheetRow(SheetRowTemplate):
    """One line on the order sheet: [ ] dish (tags) note ...... who · serves. item["want"] = a gap still wanted."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.row.classes["want"] = bool(it.get("want"))
        d = self.dom_nodes
        d["name"].textContent = it["name"]
        d["tags"].textContent = "(%s)" % it["tags"] if it.get("tags") else ""
        d["note"].textContent = it.get("note") or ""
        d["who"].textContent = it.get("who") or ""
