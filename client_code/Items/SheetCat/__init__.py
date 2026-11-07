from anvil import *

from ._anvil_designer import SheetCatTemplate


class SheetCat(SheetCatTemplate):
    """A menu section on the order sheet, with a tick box per dish and the gaps still wanted."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["cat"].textContent = self.item["cat"]
        self.rows_panel.items = self.item["rows"]
