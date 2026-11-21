from anvil import *

from ._anvil_designer import KittyRowTemplate
from ... import state


class KittyRow(KittyRowTemplate):
    """A line in the kitty: what ......... who · $30 ("spent"), or "Paid back: Jo → Ana ..... $12" ("paid", muted).
    item = {id, kind, what, by, to, amount (text), can_remove}. Remove raises x-delkitty(id, what)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        paid = it.get("kind") == "paid"
        self.row.classes["paid"] = paid
        self.dom_nodes["what"].textContent = ("Paid back: %s → %s" % (it["by"], it["to"])) if paid else it["what"]
        self.dom_nodes["by"].textContent = it["amount"] if paid else "%s · %s" % (it["by"], it["amount"])
        self.x_button.visible = bool(it.get("can_remove"))
        state.set_control_attr(self.x_button, "aria-label", ("Undo the payment from %s" % it["by"]) if paid
                               else "Take %s out of the kitty" % it["what"])

    @handle("x_button", "click")
    def x_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-delkitty", id=self.item["id"], paid=self.item.get("kind") == "paid")
