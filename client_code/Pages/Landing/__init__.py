from anvil import *

from ._anvil_designer import LandingTemplate
from ... import pf, state

# The app's video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json), shown in the Watch section.
YT_VIDEO = "d7Gj5GCfeOc"


class Landing(LandingTemplate):
    """#landing (Persuade): the catalogue-cover hero (the headline's last words roll through four party ideas and the
    cover dish changes with them, one 12 s CSS loop), parties opened on this device, the Watch section, how it works,
    host and guest columns, features, questions. Static copy lives in the template; only the signed-in variations,
    today's band title and the device list are set here."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me()
        self.guest_cta.visible = not me
        self.member_cta.visible = bool(me)
        self.host_signup.visible = not me
        self.host_new.visible = bool(me)
        sat = pf.add_days(pf.friday(0), 1)
        self.dom_nodes["slip_day"].textContent = pf.day_name(sat, True) + " · Dinner"
        self.dom_nodes["band_title"].textContent = pf.band_title()
        if me:
            self.dom_nodes["band_link"].setAttribute("href", "#new")
            self.dom_nodes["band_link"].textContent = "Host a party"
        device = [v for v in pf.visited() if not str(v.get("token", "")).startswith("sample")]
        self.device_sec.visible = bool(device) and not me
        self.device_panel.items = device
        self.dom_nodes["yt_cover"].addEventListener("click", self._play)

    def _play(self, event):
        """Swap the video's cover for YouTube's player (privacy-enhanced); nothing loads from YouTube before this click."""
        self.dom_nodes["yt_frame"].innerHTML = (
            '<iframe src="https://www.youtube-nocookie.com/embed/' + YT_VIDEO + '?autoplay=1&rel=0&playsinline=1" '
            'title="Plan Friday video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>')
