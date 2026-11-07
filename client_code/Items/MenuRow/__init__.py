from anvil import *

from ._anvil_designer import MenuRowTemplate
from ... import state


class MenuRow(MenuRowTemplate):
    """A menu section in the party form: its name, how many wanted (0-20), remove. item = the form's own dict
    {i, name, wanted}, changed in place; removing raises x-del(i)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        state.set_control_attr(self.name_box, "aria-label", "Menu section")
        state.set_control_attr(self.name_box, "maxlength", 30)
        state.set_control_attr(self.less_button, "aria-label", "Fewer " + self.item["name"])
        state.set_control_attr(self.more_button, "aria-label", "More " + self.item["name"])
        state.set_control_attr(self.del_button, "aria-label", "Remove " + self.item["name"])
        self._show()

    def _show(self):
        self.count.text = str(self.item["wanted"])

    @handle("name_box", "change")
    def name_box_change(self, **event_args):
        self.item["name"] = self.name_box.text or ""

    @handle("less_button", "click")
    def less_button_click(self, **event_args):
        self.item["wanted"] = max(0, self.item["wanted"] - 1)
        self._show()

    @handle("more_button", "click")
    def more_button_click(self, **event_args):
        self.item["wanted"] = min(20, self.item["wanted"] + 1)
        self._show()

    @handle("del_button", "click")
    def del_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-del", i=self.item["i"])
