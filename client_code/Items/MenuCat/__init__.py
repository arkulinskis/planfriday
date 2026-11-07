from anvil import *
from anvil.js import window

from ._anvil_designer import MenuCatTemplate
from ... import state


class MenuCat(MenuCatTemplate):
    """A menu section on the party page: how many are wanted (tick boxes), the dishes promised, "I'll bring one".
    Raises x-bring(cat); passes x-deldish(id) up from its dishes."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        d = self.dom_nodes
        d["name"].textContent = it["cat"]
        d["need"].textContent = it["need"]
        boxes = d["boxes"]
        for i in range(max(it["wanted"], it["have"])):
            b = window.document.createElement("i")
            if i < it["have"]:
                b.className = "on" if i < it["wanted"] else "over"
            boxes.appendChild(b)
        self.dishes_panel.items = it["dishes"]
        self.dishes_panel.visible = bool(it["dishes"])
        self.empty_part.visible = not it["dishes"]
        d["empty"].textContent = it["empty"]
        self.add_part.visible = bool(it.get("open"))
        self.bring_button.text = it["bring"]
        state.set_control_attr(self.bring_button, "aria-label", "%s: %s" % (it["bring"], it["cat"]))
        self.dishes_panel.add_event_handler("x-deldish", self._del)

    def _del(self, id, **e):
        if self.parent:
            self.parent.raise_event("x-deldish", id=id)

    @handle("bring_button", "click")
    def bring_button_click(self, **event_args):
        if self.parent:
            self.parent.raise_event("x-bring", cat=self.item["cat"])
