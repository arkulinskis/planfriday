from anvil import *

from ._anvil_designer import CatalogueTemplate
from ... import pf, router


class Catalogue(CatalogueTemplate):
    """#catalogue[/tag]: the 13 party ideas (pf.IDEAS) as catalogue items, with a tag filter. "Order this party"
    opens the party form filled in (#new/<idea>); signed-out visitors sign up first (router)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.tag = args[0] if args and args[0] in pf.TAG_NAMES else "all"
        self._buttons = {"all": self.t_all, "cosy": self.t_cosy, "brunch": self.t_brunch, "handson": self.t_handson,
                         "crowd": self.t_crowd, "outdoor": self.t_outdoor}
        self._draw()

    def _draw(self):
        for k, b in self._buttons.items():
            b.classes["on"] = k == self.tag
        self.ideas_panel.items = [dict(i, n=n) for n, i in enumerate(pf.IDEAS) if self.tag == "all" or self.tag in i["tags"]]

    def tag_click(self, event):
        self.tag = str(event.currentTarget.getAttribute("data-tag"))
        if self.tag == "all":
            router.replace("catalogue")
        else:
            router.replace("catalogue", self.tag)
        self._draw()
