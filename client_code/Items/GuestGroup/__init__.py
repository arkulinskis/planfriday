from anvil import *

from ._anvil_designer import GuestGroupTemplate


class GuestGroup(GuestGroupTemplate):
    """Coming / Maybe / Can't make it, with the guests in it. Passes x-kick(id, name) up."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["label"].textContent = self.item["label"]
        self.guests_panel.items = self.item["guests"]
        self.guests_panel.add_event_handler("x-kick", self._kick)

    def _kick(self, id, name, **e):
        if self.parent:
            self.parent.raise_event("x-kick", id=id, name=name)
