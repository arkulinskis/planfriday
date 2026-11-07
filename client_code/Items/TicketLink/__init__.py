from anvil import *

from ._anvil_designer import TicketLinkTemplate
from ... import router


class TicketLink(TicketLinkTemplate):
    """A party opened on this device (guests have no account). item = {token, title, small (bool)}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        a = self.dom_nodes["link"]
        a.setAttribute("href", router.href("p", self.item["token"]))
        if self.item.get("small"):
            a.classList.add("sm")
        self.dom_nodes["words"].textContent = self.item.get("title") or "A party"
