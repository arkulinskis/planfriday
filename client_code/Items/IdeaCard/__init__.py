from anvil import *

from ._anvil_designer import IdeaCardTemplate
from ... import pf, router


class IdeaCard(IdeaCardTemplate):
    """One catalogue item: picture, item number, blurb, the price lines and "Order this party" (#new/<key>)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i, n = self.item, self.item.get("n", 0)
        self.cover_box.classes["red"] = n % 3 == 1
        self.cover_box.classes["navy"] = n % 3 == 2
        d = self.dom_nodes
        d["tag"].textContent = pf.TAG_NAMES.get(i["tags"][0], "")
        d["no"].textContent = "No. " + i["no"]
        d["name"].textContent = i["name"]
        d["blurb"].textContent = i["blurb"]
        d["serves"].textContent = i["serves"]
        d["effort"].textContent = pf.effort(i["effort"])
        d["effort"].setAttribute("aria-label", "%d of 3" % i["effort"])
        d["style"].textContent = pf.STYLE_NAMES.get(i["style"], "Potluck")
        day, part = i["slots"][0]
        d["best"].textContent = pf.day_name(pf.add_days(pf.friday(0), day)) + " " + pf.part_label(part).lower()
        d["menu"].textContent = " · ".join(m + (" ×%d" % k if k > 1 else "") for m, k in i["menu"])
        d["order"].setAttribute("href", router.href("new", i["key"]))
        d["order"].setAttribute("aria-label", "Order this party: " + i["name"])
