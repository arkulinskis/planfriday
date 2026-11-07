from anvil import *

from ._anvil_designer import PickCardTemplate
from ... import router


class PickCard(PickCardTemplate):
    """One of today's catalogue picks on the home page: opens the party form filled in (#new/<key>)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i = self.item
        self.dom_nodes["card"].setAttribute("href", router.href("new", i["key"]))
        self.dom_nodes["name"].textContent = i["name"]
        self.dom_nodes["meta"].textContent = "No. %s · serves %s" % (i["no"], i["serves"])
