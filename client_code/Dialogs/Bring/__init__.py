import random

from anvil import *

from ._anvil_designer import BringTemplate
from ... import pf, state


class Bring(BringTemplate):
    """"What are you bringing?": section, dish (the dice suggest one), serves, note, tags. "Has nuts" ticks itself
    when the words mention a nut (once, so it can still be unticked; the server re-checks every tag). Closes with the
    dish dict for dish_add, or None."""

    def __init__(self, party=None, category="", **properties):
        super().__init__(**properties)
        party = party or {}
        self.dom_nodes["party"].textContent = (party.get("title") or "") + " · the menu"
        cats = list(party.get("categories") or ["Something else"])
        self.cat_drop.items = cats
        self.cat_drop.selected_value = category if category in cats else cats[0]
        state.set_control_attr(self.cat_drop, "aria-label", "Section")
        ideas = pf.suggest(self.cat_drop.selected_value)
        self.n = random.randrange(len(ideas))
        self.name_box.placeholder = ideas[self.n]
        state.set_control_attr(self.name_box, "maxlength", 80)
        state.set_control_attr(self.note_box, "maxlength", 140)
        state.set_control_attr(self.serves_box, "min", 1)
        state.set_control_attr(self.serves_box, "max", 50)
        self.tags: set = set()
        self.nuts_seen = False
        self.tags_panel.add_event_handler("x-pick", self._tag)
        self._tags()

    def _tags(self):
        self.tags_panel.items = [{"key": k, "text": n, "role": ["pt-tog"], "on": k in self.tags} for k, n in pf.DISH_TAGS]

    def _tag(self, key, **e):
        if key in self.tags:
            self.tags.discard(key)
        else:
            self.tags.add(key)
        self._tags()
        state.refocus(self.tags_panel, key)

    def _check_nuts(self):
        hit = pf.has_nuts((self.name_box.text or "") + " " + (self.note_box.text or ""))
        if hit and not self.nuts_seen:
            self.tags.add("nuts")
            self._tags()
        self.nuts_seen = hit

    @handle("name_box", "change")
    def name_box_change(self, **event_args):
        self._check_nuts()

    @handle("note_box", "change")
    def note_box_change(self, **event_args):
        self._check_nuts()

    @handle("dice_button", "click")
    def dice_button_click(self, **event_args):
        ideas = pf.suggest(self.cat_drop.selected_value)
        self.n = (self.n + 1) % len(ideas)
        self.name_box.text = ideas[self.n]
        self.name_box.focus()
        self._check_nuts()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if len(name) < 2:
            self.message.text, self.message.visible = "Give your dish a name.", True
            self.name_box.focus()
            return
        serves = self.serves_box.text
        try:
            serves = int(float(serves)) if serves not in (None, "") else None
        except (TypeError, ValueError):
            serves = None
        self.raise_event("x-close-alert", value={"category": self.cat_drop.selected_value, "name": name, "serves": serves,
                                                 "note": (self.note_box.text or "").strip(),
                                                 "tags": [k for k, _ in pf.DISH_TAGS if k in self.tags]})
