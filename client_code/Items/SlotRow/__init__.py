from anvil import *

from ._anvil_designer import SlotRowTemplate
from ... import state


class SlotRow(SlotRowTemplate):
    """One weekend slot on the party page: who's free, the forecast, my ✓ ~ ✕ answer, the host's Lock button.
    Raises x-ans(key, ans) and x-lock(key) on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        for c in ("chosen", "best", "dim", "past"):
            self.row.classes[c] = bool(it.get(c))
        self.best_burst.visible = bool(it.get("best"))
        d = self.dom_nodes
        d["day"].textContent, d["date"].textContent = it["day"], it["date"]
        d["part"].textContent, d["sub"].textContent = it["part"], it["sub"]
        self.wx_row.visible = bool(it.get("wx")) or bool(it.get("driest"))
        self.driest.visible = bool(it.get("driest"))
        self.chips_panel.items = it["chips"]
        self.chips_panel.visible = bool(it["chips"])
        self.ans_part.visible = bool(it.get("can"))
        state.set_attr(self.ans_part, "aria-label", "Are you free: " + it["label"])
        for b, k, words in ((self.a_yes, "yes", "Free"), (self.a_maybe, "maybe", "Maybe"), (self.a_no, "no", "Can't")):
            on = it.get("mine") == k
            b.role = ["ans", "ans-" + k] + (["on"] if on else [])
            state.set_control_attr(b, "aria-label", "%s for %s" % (words, it["label"]))
            state.set_control_attr(b, "aria-pressed", "true" if on else "false")
            state.set_control_attr(b, "data-key", it["key"] + ":" + k)
            b.tooltip = words
        self.on_stamp.visible = bool(it.get("chosen")) and not it.get("can")
        self.lock_button.visible = bool(it.get("lock"))
        state.set_control_attr(self.lock_button, "aria-label", "Lock in " + it["label"])

    def _ans(self, k):
        if self.parent:
            self.parent.raise_event("x-ans", key=self.item["key"], ans=k)

    @handle("a_yes", "click")
    def a_yes_click(self, **event_args):
        self._ans("yes")

    @handle("a_maybe", "click")
    def a_maybe_click(self, **event_args):
        self._ans("maybe")

    @handle("a_no", "click")
    def a_no_click(self, **event_args):
        self._ans("no")

    @handle("lock_button", "click")
    def lock_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-lock", key=self.item["key"])
