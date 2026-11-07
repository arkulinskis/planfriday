from anvil import *

from ._anvil_designer import SlotOptTemplate


class SlotOpt(SlotOptTemplate):
    """A slot to tick in the party form (Saturday dinner...). item = {key, label, time, on, off (in the past)}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["time"].textContent = self.item["time"]
        self.opt.classes["off"] = bool(self.item.get("off"))
        self.opt.classes["on"] = bool(self.item.get("on"))
        self.box.enabled = not self.item.get("off")

    @handle("box", "change")
    def box_change(self, **event_args):
        self.opt.classes["on"] = bool(self.box.checked)
        if self.parent:
            self.parent.raise_event("x-slot", key=self.item["key"], on=bool(self.box.checked))
