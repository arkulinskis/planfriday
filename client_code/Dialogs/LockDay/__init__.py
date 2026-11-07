from anvil import *

from ._anvil_designer import LockDayTemplate
from ... import pf, state


class LockDay(LockDayTemplate):
    """The host picks the slot (with how many are free) and a start time. Closes with (slot, "HH:MM") or None."""

    def __init__(self, party=None, stats=None, pick=None, **properties):
        super().__init__(**properties)
        self.p, self.st = party or {}, stats or {}
        self.pick = pick or self.st.get("best") or (self.p.get("slots") or [None])[0]
        self.dom_nodes["party"].textContent = self.p.get("title") or ""
        state.control(self.time_box).setAttribute("type", "time")  # the App Server's TextBox has no type="time"
        self.slots_panel.add_event_handler("x-pick", self._pick)
        self._draw(True)

    def _draw(self, reset_time):
        rows = []
        for k in self.p.get("slots") or []:
            t = (self.st.get("slots") or {}).get(k) or {"yes": [], "maybe": []}
            rows.append({"key": k, "on": k == self.pick, "role": ["lock-opt"],
                         "text": "%s, %s · %d free · %d maybe%s" % (pf.slot_label(k), pf.short_date(pf.slot(k)[0]), len(t["yes"]),
                                                                  len(t["maybe"]), " · best" if k == self.st.get("best") else "")})
        self.slots_panel.items = rows
        if reset_time and self.pick:
            self.time_box.text = pf.part_time(pf.slot(self.pick)[1])

    def _pick(self, key, **e):
        self.pick = key
        self._draw(True)
        state.refocus(self.slots_panel, key)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        if self.pick:
            self.raise_event("x-close-alert", value=(self.pick, (self.time_box.text or "").strip() or None))
