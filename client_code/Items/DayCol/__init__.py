from anvil import *

from ._anvil_designer import DayColTemplate


class DayCol(DayColTemplate):
    """One day of the weekend in the party form, with its slots. item = {name, date, opts}; passes x-slot up."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["name"].textContent = self.item["name"]
        self.dom_nodes["date"].textContent = self.item["date"]
        self.opts_panel.items = self.item["opts"]
        self.opts_panel.add_event_handler("x-slot", self._slot)

    def _slot(self, key, on, **e):
        if self.parent:
            self.parent.raise_event("x-slot", key=key, on=on)
