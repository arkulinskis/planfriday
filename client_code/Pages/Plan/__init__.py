import anvil.js
import anvil.server
from anvil import *

from ._anvil_designer import PlanTemplate
from ... import pf, router, state

PRESETS = ["Starters", "Soup", "Salad", "Mains", "Sides", "Bread", "Dessert", "Drinks", "Cheese", "Snacks", "Supplies"]


def from_idea(i):
    """The form filled in from a catalogue idea: its name, picture, menu and the slots still ahead."""
    st = {"title": "" if i["key"] == "classic" else i["name"], "blurb": "", "location": "", "style": i["style"],
          "cover": i["cover"], "cap": "", "idea": i["key"], "wx_place": pf.get("town", "") or "",
          "outdoors": "outdoor" in i["tags"], "menu": [{"name": m, "wanted": n} for m, n in i["menu"]], "slots": {}}

    def keys(w):
        return [k for k in (pf.slot_key(pf.friday(w), d, p) for d, p in i["slots"]) if not pf.is_past(k)]
    week, k = 0, keys(0)
    if not k:
        week, k = 1, keys(1)
    for x in k:
        st["slots"][x] = True
    st["week"] = week
    return st


class Plan(PlanTemplate):
    """The party form, styled as a mail-order "order blank".
       #new          a blank party (the Classic Potluck menu)
       #new/<idea>   filled in from a catalogue idea (pf.IDEAS)
       #edit/<id>    change a party you host (get_party_form, update_party)
    Creating calls create_party and opens the new party page (it then throws confetti and selects the link)."""

    def __init__(self, args=(), page="new", **properties):
        super().__init__(**properties)
        self.editing = page == "edit"
        self.party_id = args[0] if self.editing and args else None
        self.weeks, self.answers = [0, 1], 0
        self.st: dict = {}
        self.ideas_panel.add_event_handler("x-idea", self._idea)
        self.covers_panel.add_event_handler("x-cover", self._cover)
        self.weeks_panel.add_event_handler("x-pick", self._week)
        self.days_panel.add_event_handler("x-slot", self._slot)
        self.also_panel.add_event_handler("x-pick", self._unslot)
        self.menu_panel.add_event_handler("x-del", self._delcat)
        self.presets_panel.add_event_handler("x-pick", self._preset)
        self.styles_panel.add_event_handler("x-style", self._style)
        state.set_control_attr(self.title_box, "aria-label", "Party name")
        state.set_control_attr(self.town_box, "aria-label", "Town for the weather check")
        state.set_control_attr(self.newcat_box, "aria-label", "New menu section")
        state.set_control_attr(self.cap_box, "min", 2)
        state.set_control_attr(self.cap_box, "max", 100)
        for box, n in ((self.title_box, 80), (self.location_box, 120), (self.town_box, 80), (self.newcat_box, 30)):
            state.set_control_attr(box, "maxlength", n)
        state.set_control_attr(self.blurb_box, "maxlength", 1000)
        if self.editing:
            r = state.call("get_party_form", self.party_id)
            if not r:
                router.go("home")
                return
            p = r["party"]
            self.answers = p.get("answers") or 0
            self.st = {"title": p["title"], "blurb": p["blurb"], "location": p["location"], "style": p["style"], "cover": p["cover"],
                       "cap": p.get("cap") or "", "token": p["token"], "catalog_no": p.get("catalog_no"),
                       "wx_place": p.get("wx_place") or "", "outdoors": bool(p.get("outdoors")),
                       "menu": [{"name": c, "wanted": 1 if p["wanted"].get(c) is None else p["wanted"][c]} for c in p["categories"]],
                       "slots": {k: True for k in p["slots"]}}
            w = 0
            if p["slots"]:
                w = int(round((pf.friday(0, pf.slot(p["slots"][0])[0]) - pf.friday(0)).days / 7.0))
            self.st["week"] = w
            if w not in self.weeks:
                self.weeks = [w] + self.weeks
        else:
            i = pf.idea(args[0]) if args else None
            self.st = from_idea(i or pf.idea("classic"))
            if not i:
                self.st["idea"] = None
        self._draw()

    # ---------------------------------------------------------------- drawing
    def _draw(self):
        st, ed = self.st, self.editing
        d = self.dom_nodes
        d["no"].textContent = ((st.get("catalog_no") or "") + " · Changes to your order") if ed else "Order blank · Form PF-1"
        d["title"].textContent = "Edit your party" if ed else "Host a party"
        d["lead"].textContent = "Guests see the changes as soon as you save." if ed else "Fill it in, send the link, and the weekend plans itself."
        d["submit_note"].textContent = "Everyone with the link sees your changes." if ed else "Next: you get one link to send to everyone."
        self.back_link.visible, self.burst.visible, self.ideas_part.visible = ed, not ed, not ed
        if ed:
            state.set_attr(self.back_link, "href", router.href("p", st.get("token")))
        self.submit_button.text = "Save changes" if ed else "Send my order"
        self.submit_button.role = ["btn", "btn-primary", "btn-lg", "ic-check" if ed else "ic-arrow"]
        self.ideas_panel.items = [{"key": i["key"], "name": i["name"], "cover": i["cover"], "on": st.get("idea") == i["key"]} for i in pf.IDEAS]
        self.title_box.text = st["title"]
        self._covers()
        self._weeks()
        self._days()
        self.answers_note.visible = bool(self.answers)
        self.answers_note.text = "%s answered already. Unticking a slot drops their answers for it." % state.plural(self.answers, "guest has", "guests have")
        self._menu()
        self._styles()
        self.location_box.text = st["location"]
        self.cap_box.text = str(st.get("cap") or "")
        self.town_box.text = st.get("wx_place") or ""
        self.outdoors_box.checked = bool(st.get("outdoors"))
        self.blurb_box.text = st["blurb"]

    def _covers(self):
        self.covers_panel.items = [{"key": k, "name": n, "on": self.st["cover"] == k} for k, n in pf.COVERS]

    def _weeks(self):
        def label(w):
            return ("This weekend" if w == 0 else "Next weekend" if w == 1 else "Weekend of") + " · " + pf.weekend_range(pf.friday(w))
        self.weeks_panel.items = [{"key": w, "text": label(w), "role": ["seg"], "on": self.st["week"] == w} for w in self.weeks]

    def _days(self):
        fri, names = pf.friday(self.st["week"]), ["Friday", "Saturday", "Sunday"]
        cols = []
        for d, parts in enumerate(pf.DAY_PARTS):
            opts = []
            for p in parts:
                key = pf.slot_key(fri, d, p)
                on = bool(self.st["slots"].get(key))
                opts.append({"key": key, "label": pf.part_label(p), "time": pf.time_label(pf.part_time(p)), "on": on,
                             "off": pf.is_past(key) and not on})
            cols.append({"name": names[d], "date": pf.short_date(pf.add_days(fri, d)), "opts": opts})
        self.days_panel.items = cols
        self._picked()

    def _picked(self):
        keys = sorted(k for k, v in self.st["slots"].items() if v)
        self.dom_nodes["count"].textContent = (state.plural(len(keys), "slot") + " ticked") if keys else "Nothing ticked yet"
        fri = pf.friday(self.st["week"])
        first, last = pf.iso(fri), pf.iso(pf.add_days(fri, 2))
        other = [k for k in keys if not first <= k.split("|")[0] <= last]
        self.also_part.visible = bool(other)
        self.also_panel.items = [{"key": k, "text": "%s, %s ✕" % (pf.slot_label(k), pf.short_date(pf.slot(k)[0])),
                                  "label": "Untick %s, %s" % (pf.slot_label(k), pf.short_date(pf.slot(k)[0])), "role": ["btn", "btn-sm"]} for k in other]

    def _menu(self):
        for i, m in enumerate(self.st["menu"]):
            m["i"] = i
        self.menu_panel.items = self.st["menu"]
        self.no_menu.visible = not self.st["menu"]
        have = [m["name"].lower() for m in self.st["menu"]]
        self.presets_panel.items = [{"key": p, "text": "+ " + p, "role": ["btn", "btn-sm"]} for p in PRESETS if p.lower() not in have]

    def _styles(self):
        self.styles_panel.items = [{"key": k, "name": n, "desc": desc, "on": self.st["style"] == k} for k, n, desc in pf.STYLES]

    # ---------------------------------------------------------------- choices
    def _idea(self, key, **e):
        self.st = from_idea(pf.idea(key))
        router.replace("new", key)
        self._draw()

    def _cover(self, key, **e):
        self.st["cover"] = key
        self._covers()

    def _week(self, key, **e):
        self.st["week"] = key
        self._weeks()
        self._days()

    def _slot(self, key, on, **e):
        if on:
            self.st["slots"][key] = True
        else:
            self.st["slots"].pop(key, None)
        self._picked()

    def _unslot(self, key, **e):
        self.st["slots"].pop(key, None)
        self._days()

    def _delcat(self, i, **e):
        self.st["menu"].pop(i)
        self._menu()

    def _add_cat(self, name):
        name = (name or "").strip()[:30]
        if not name:
            return
        if any(m["name"].lower() == name.lower() for m in self.st["menu"]):
            state.toast("That section is already on the menu.")
            return
        if len(self.st["menu"]) >= 14:
            state.toast("That's plenty of sections (14 at most).", "error")
            return
        self.st["menu"].append({"name": name, "wanted": 1})
        self._menu()

    def _preset(self, key, **e):
        self._add_cat(key)

    def _style(self, key, **e):
        self.st["style"] = key
        self._styles()

    @handle("add_button", "click")
    def add_button_click(self, **event_args):
        self._add_cat(self.newcat_box.text)
        self.newcat_box.text = ""
        self.newcat_box.focus()

    @handle("newcat_box", "pressed_enter")
    def newcat_box_pressed_enter(self, **event_args):
        self.add_button_click()

    @handle("wx_button", "click")
    def wx_button_click(self, **event_args):
        q = (self.town_box.text or "").strip()
        if not q:
            self.wx_result.text = "Type a town first."
            return
        r = anvil.server.call("weather_lookup", q)
        self.wx_result.text = ("✓ Found: " + r["place"]) if r.get("ok") else (r.get("error") or "That didn't work.")
        self.wx_result.role = ["ui-hint"] if r.get("ok") else ["ui-hint", "pl-bad"]

    # ---------------------------------------------------------------- save
    @handle("submit_button", "click")
    def submit_button_click(self, **event_args):
        st = self.st
        title = (self.title_box.text or "").strip()
        slots = [k for k, v in st["slots"].items() if v]
        problem = "Give your party a name (section 1)." if len(title) < 2 else "Tick at least one day and time (section 2)." if not slots else None
        if problem:
            self._problem(problem)
            return
        self.msg.visible = False
        wanted, cats = {}, []
        for m in st["menu"]:
            n = (m["name"] or "").strip()
            if n:
                cats.append(n)
                wanted[n] = m["wanted"]
        cap_text = str(self.cap_box.text if self.cap_box.text is not None else "").strip()
        try:
            cap = int(float(cap_text)) if cap_text else None
        except (TypeError, ValueError):
            cap = None
        town = (self.town_box.text or "").strip()
        data = {"title": title, "blurb": self.blurb_box.text or "", "location": self.location_box.text or "", "style": st["style"],
                "cover": st["cover"], "cap": cap, "slots": slots, "categories": cats, "wanted": wanted, "wx_place": town,
                "outdoors": bool(self.outdoors_box.checked)}
        self.submit_button.enabled = False
        try:
            r = anvil.server.call("update_party", self.party_id, data) if self.editing else anvil.server.call("create_party", data)
        finally:
            self.submit_button.enabled = True
        if not r.get("ok"):
            self._problem(r.get("error") or "That didn't work.")
            return
        if not self.editing:
            pf.put("justMade", r["token"])
        if town:
            pf.put("town", town)
        state.toast("Saved. Your guests see the changes." if self.editing else "Your party is in print! Now send the link.", "ok")
        if r.get("note"):
            state.toast(r["note"])
        router.go("p", r["token"])

    def _problem(self, text):
        self.msg.text, self.msg.visible = text, True
        anvil.js.get_dom_node(self.msg).scrollIntoView({"block": "center", "behavior": "smooth"})
