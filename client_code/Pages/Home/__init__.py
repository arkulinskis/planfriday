from anvil import *

from ._anvil_designer import HomeTemplate
from ... import pf, router, state


class Home(HomeTemplate):
    """#home, "Your weekend": a Friday countdown, a coupon to start a party, the parties you host and the ones
    you're invited to (get_home), parties opened on this device, and three catalogue picks that change daily."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me() or {}
        cd, fri = pf.countdown(), pf.friday(0)
        d = self.dom_nodes
        d["cd_big"].textContent = cd["big"]
        d["cd_small"].textContent = "Hello, %s. %s" % ((me.get("name") or "there").split(" ")[0], cd["small"])
        d["cd_week"].textContent = ("This weekend" if cd["hot"] else "The weekend") + ": " + pf.weekend_range(fri)
        d["cd_burst"].textContent = cd["burst"]
        seed, ideas = pf.today().day, pf.IDEAS
        self.picks_panel.items = [ideas[seed % len(ideas)], ideas[(seed + 4) % len(ideas)], ideas[(seed + 9) % len(ideas)]]

        h: dict = state.call("get_home") or {"hosting": [], "invited": [], "sample": None}
        upcoming = [s for s in h["hosting"] if not pf.all_past(s)]
        d["hosting_count"].textContent = state.plural(len(upcoming), "party", "parties") + " coming up"
        self.hosting_panel.items = h["hosting"]
        self.hosting_panel.visible = bool(h["hosting"])
        self.hosting_empty.visible = not h["hosting"]
        self.sample_line.visible = bool(h.get("sample"))
        if h.get("sample"):
            d["sample_link"].setAttribute("href", router.href("p", h["sample"]))
        self.invited_panel.items = h["invited"]
        self.invited_block.visible = bool(h["invited"])
        mine = set(s["token"] for s in h["hosting"] + h["invited"])
        device = [dict(v, small=True) for v in pf.visited()
                  if v.get("token") not in mine and not str(v.get("token", "")).startswith("sample")]
        self.device_panel.items = device
        self.device_block.visible = bool(device)
