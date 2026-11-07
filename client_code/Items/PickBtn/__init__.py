from anvil import *

from ._anvil_designer import PickBtnTemplate
from ... import state


class PickBtn(PickBtnTemplate):
    """A button in a list of choices (weeks, menu presets, diets, dish tags, filters...).
    item = {key, text, role (list), on (bool), label (aria-label), disabled}; a click raises x-pick(key) on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        self.btn.role = list(it.get("role") or ["btn", "btn-sm"]) + (["on"] if it.get("on") else [])
        self.btn.enabled = not it.get("disabled")
        if "on" in it:
            state.set_control_attr(self.btn, "aria-pressed", "true" if it.get("on") else "false")
        if it.get("label"):
            state.set_control_attr(self.btn, "aria-label", it["label"])
        state.set_control_attr(self.btn, "data-key", it.get("key"))

    @handle("btn", "click")
    def btn_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-pick", key=self.item.get("key"))
