from anvil import *

from ._anvil_designer import BadgeTemplate


class Badge(BadgeTemplate):
    """A small label in a list (dish tags, diet warnings). item = {text, role (list), title}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.lbl.role = list(self.item.get("role") or ["badge"])
        if self.item.get("title"):
            self.lbl.tooltip = self.item["title"]
