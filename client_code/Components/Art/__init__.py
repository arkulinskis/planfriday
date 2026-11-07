from anvil import *

from ._anvil_designer import ArtTemplate
from ... import pf


class Art(ArtTemplate):
    """A party picture (cover) or, with wx, a weather icon. The SVG comes from pf.js (the drawing engine)."""

    def __init__(self, **properties):
        self._cover, self._label, self._wx, self._ready = "classic", "", None, False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        if not self._ready:
            return
        label = None if not self._label else ("" if self._label == "-" else self._label)
        if self._wx:
            svg = pf.wx_svg(self._wx, label != "")
        else:
            svg = pf.art(self._cover or "classic", label)
        self.dom_nodes["box"].innerHTML = svg

    @property
    def cover(self):
        return self._cover

    @cover.setter
    def cover(self, value):
        self._cover = value or "classic"
        self._draw()

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value or ""
        self._draw()

    @property
    def wx(self):
        return self._wx

    @wx.setter
    def wx(self, value):
        self._wx = value or None
        self._draw()
