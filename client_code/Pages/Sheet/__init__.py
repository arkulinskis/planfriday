import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import SheetTemplate
from ... import pf, router, state


class Sheet(SheetTemplate):
    """#sheet/<token>: the printable order sheet of a party. Who's coming, the day, and the menu by section with tick
    boxes, ready to stick on the fridge. Anyone with the link (party_view)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        token = args[0] if args else ""
        r = anvil.server.call("party_view", token, pf.secret(token))
        self.missing_part.visible = bool(r.get("missing"))
        self.page_part.visible = not r.get("missing")
        if r.get("missing"):
            return
        V = r["view"]
        p, st = V["party"], V["stats"]
        d = self.dom_nodes
        d["back_link"].setAttribute("href", router.href("p", token))
        d["no"].textContent = "Order sheet · " + (p.get("catalog_no") or "")
        d["title"].textContent = p["title"]
        d["when"].textContent = pf.when_text(p) if p.get("chosen") else \
            "Day to be decided" + (" · leading: " + pf.slot_label(st["best"]) if st.get("best") else "")
        self.art.cover = p["cover"]
        coming = [g for g in V["guests"] if g["rsvp"] == "yes"]
        maybe = [g for g in V["guests"] if g["rsvp"] == "maybe"]
        facts = [{"a": "Host", "b": p.get("host_name") or ""}, {"a": "Where", "b": p.get("location") or "Ask the host"},
                 {"a": "Seats taken", "b": str(st["heads"]) + (" of %d" % p["cap"] if p.get("cap") else "")},
                 {"a": "Maybe", "b": str(len(maybe))}]
        w = V.get("weather")
        key = p.get("chosen") or st.get("best")
        f = w["slots"].get(key) if w and key else None
        if f:
            facts.append({"a": "Weather", "b": "%s · %s" % (pf.wx_words(f), pf.advice(f, w.get("outdoors")))})
        facts += [{"a": pf.diet_label(k), "b": str(n)} for k, n in st["diets"].items()]
        self.facts_panel.items = facts
        cats = []
        for c in p["categories"]:
            m = st["menu"].get(c) or {"wanted": 0, "have": 0}
            ds = [x for x in V["dishes"] if x["category"] == c]
            if not m["wanted"] and not ds:
                continue
            rows = [{"name": x["name"], "tags": ", ".join(pf.tag_label(t) for t in x["tags"]), "note": x.get("note") or "",
                     "who": x["by"] + (" · serves %d" % x["serves"] if x.get("serves") else "")} for x in ds]
            rows += [{"want": True, "name": "Still wanted", "who": "—"} for _ in range(len(ds), m["wanted"])]
            cats.append({"cat": c, "rows": rows})
        self.cats_panel.items = cats
        d["coming"].textContent = "Coming (%d)" % st["heads"]
        self.guests_panel.items = [{"text": "☐ " + g["name"] + (" +%d" % g["plus"] if g.get("plus") else ""),
                                    "diet": ", ".join(pf.diet_label(x) for x in g["diet"])} for g in coming] + \
                                  [{"text": "☐ %s (maybe)" % g["name"], "maybe": True} for g in maybe]
        d["foot"].textContent = "Printed from Plan Friday · " + pf.party_url(token).split("://", 1)[-1]

    @handle("print_button", "click")
    def print_button_click(self, **event_args):
        window.print()
