from anvil import *

from ._anvil_designer import TransferRowTemplate
from ... import state


class TransferRow(TransferRowTemplate):
    """One settle-up payment: Jo → Ana  $12  [Paid]. The Paid button shows for the payer, the person paid and the
    host. item = {from_id, from, to_id, to, cents, amount (text), can_mark}. Raises x-paid(from_id, to_id, cents)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.dom_nodes["frm"].textContent = it["from"]
        self.dom_nodes["to"].textContent = it["to"]
        self.dom_nodes["amt"].textContent = it["amount"]
        self.paid_button.visible = bool(it.get("can_mark"))
        state.set_control_attr(self.paid_button, "aria-label", "Mark %s paying %s %s as paid" % (it["from"], it["to"], it["amount"]))

    @handle("paid_button", "click")
    def paid_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-paid", from_id=self.item["from_id"], to_id=self.item["to_id"], cents=self.item["cents"],
                                    words="%s → %s %s" % (self.item["from"], self.item["to"], self.item["amount"]))
