from anvil import *

from ._anvil_designer import RenameTemplate
from ... import state


class Rename(RenameTemplate):
    """A guest's name on this party. Closes with the new name, or None."""

    def __init__(self, name="", **properties):
        super().__init__(**properties)
        self.name_box.text = name
        state.set_control_attr(self.name_box, "maxlength", 40)
        state.set_control_attr(self.name_box, "autocomplete", "given-name")

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if name:
            self.raise_event("x-close-alert", value=name)
