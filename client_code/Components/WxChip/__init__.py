from anvil import *

from ._anvil_designer import WxChipTemplate
from ... import pf


class WxChip(WxChipTemplate):
    """The weather pill on slots and party cards: icon, temperature, chance of rain."""

    def __init__(self, **properties):
        self._w, self._ready = None, False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        if not self._ready:
            return
        w = self._w
        self.visible = bool(w)
        if not w:
            return
        rain = w.get("rain") or 0
        chip = self.dom_nodes["chip"]
        chip.className = "pf-wx" + (" wet" if rain >= 50 else " dry" if rain <= 10 else "")
        chip.setAttribute("title", pf.wx_words(w))
        chip.setAttribute("aria-label", pf.wx_words(w))
        self.dom_nodes["icon"].innerHTML = pf.wx_svg(w, False)
        self.dom_nodes["words"].textContent = "%s · %d%%" % (pf.temp(w.get("temp")), rain)
        self.dom_nodes["words"].setAttribute("aria-hidden", "true")

    @property
    def forecast(self):
        return self._w

    @forecast.setter
    def forecast(self, value):
        self._w = value or None
        self._draw()
