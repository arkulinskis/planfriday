from anvil import *

from ._anvil_designer import SpendTemplate
from ... import pf, state


class Spend(SpendTemplate):
    """"I spent ...": what for and how much (0.01 to 5000). Closes with {"what", "amount"} or None.
    The server checks everything again (Guests.kitty_add)."""

    def __init__(self, party=None, **properties):
        super().__init__(**properties)
        p = party or {}
        self.dom_nodes["party"].textContent = p.get("title") or ""
        self.dom_nodes["cur"].textContent = pf.currency(p)
        state.set_control_attr(self.what_box, "maxlength", 60)
        state.set_control_attr(self.amount_box, "aria-label", "How much, in " + pf.currency(p))
        state.set_control_attr(self.amount_box, "min", "0.01")
        state.set_control_attr(self.amount_box, "max", "5000")
        state.set_control_attr(self.amount_box, "step", "0.01")
        state.set_control_attr(self.amount_box, "inputmode", "decimal")

    @handle("what_box", "pressed_enter")
    def what_box_pressed_enter(self, **event_args):
        state.focus(self.amount_box)

    @handle("amount_box", "pressed_enter")
    def amount_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    def _say(self, text):
        self.msg.text, self.msg.visible = text, True

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        what = (self.what_box.text or "").strip()
        raw = str(self.amount_box.text if self.amount_box.text is not None else "").strip().replace(",", ".")
        if not what:
            self._say("What was it for? The wine, the roast...")
            return
        try:
            amount = round(float(raw), 2)
        except (TypeError, ValueError):
            self._say("How much was it? Type a number, like 24.50.")
            return
        if not 0.01 <= amount <= 5000:
            self._say("An amount from 0.01 to 5000, please.")
            return
        self.raise_event("x-close-alert", value={"what": what, "amount": amount})
