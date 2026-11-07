from anvil import *

from ._anvil_designer import LeaderRowTemplate


class LeaderRow(LeaderRowTemplate):
    """A catalogue price line: words ......... value. item = {a, b}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["a"].textContent = str(self.item.get("a", ""))
        self.dom_nodes["b"].textContent = str(self.item.get("b", ""))
