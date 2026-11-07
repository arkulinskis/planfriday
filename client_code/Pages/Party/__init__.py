import json

import anvil.js
import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import PartyTemplate
from ... import pf, router, state

ANS = [("yes", "✓", "Free"), ("maybe", "~", "Maybe"), ("no", "✕", "Can't")]
GROUPS = [("yes", "Coming"), ("maybe", "Maybe"), ("no", "Can't make it")]


class Party(PartyTemplate):
    """#p/<token>: the page behind the link the host sends. Anyone with the link; no account needed.
    Guests add their name (guest_join; this browser keeps the secret it gets back, pf.secret), then RSVP, tick the
    days they're free, say what they're bringing and write in the guestbook. The host also gets the share box and the
    host tools (lock in the day, close RSVPs, edit, run it again, delete). Every guest action and host tool returns
    the whole view (Guests.view), so the page redraws from one reply. It refreshes itself quietly every 30 seconds
    while nobody is typing and no dialog is open."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.token = args[0] if args else ""
        self.secret = pf.secret(self.token)
        self.V: dict = {}
        self._last, self._timer = "", None
        self.slots_panel.add_event_handler("x-ans", self._answer)
        self.slots_panel.add_event_handler("x-lock", self._lock_key)
        self.cats_panel.add_event_handler("x-bring", self._bring)
        self.cats_panel.add_event_handler("x-deldish", self._deldish)
        self.notes_panel.add_event_handler("x-delnote", self._delnote)
        self.groups_panel.add_event_handler("x-kick", self._kick)
        self.diets_panel.add_event_handler("x-pick", self._diet)
        state.set_control_attr(self.link_box, "readonly", "")
        state.set_control_attr(self.link_box, "aria-label", "Party link")
        state.set_control_attr(self.join_name, "autocomplete", "given-name")
        state.set_control_attr(self.join_name, "maxlength", 40)
        state.set_control_attr(self.note_box, "maxlength", 600)
        self._tick_fn = anvil.js.report_exceptions(self._tick)
        self._load(False)
        if self.V and self.V.get("is_host") and pf.get("justMade") == self.token:
            pf.put("justMade", None)
            pf.confetti()
            self._just_made = True

    # ---------------------------------------------------------------- loading
    def _load(self, quiet):
        try:
            r = (anvil.server.call_s if quiet else anvil.server.call)("party_view", self.token, self.secret)
        except Exception:
            if quiet:
                return
            raise
        if r.get("missing"):
            pf.forget(self.token)
            self.missing_part.visible, self.page_part.visible = True, False
            return
        s = json.dumps(r["view"], sort_keys=True)
        if s == self._last:
            return
        self.V, self._last = r["view"], s
        pf.remember(self.V["party"])
        window.document.title = self.V["party"]["title"] + " · Plan Friday"
        self._draw()

    def _took(self, r):
        if not r:
            return r
        if r.get("secret"):
            self.secret = r["secret"]
            pf.set_secret(self.token, self.secret)
        if r.get("view"):
            self.V = r["view"]
            self._last = json.dumps(self.V, sort_keys=True)
            self._draw()
        return r

    def _call(self, fn, *args):
        """A guest action: the link and this browser's secret go first."""
        return self._took(state.call(fn, self.token, self.secret, *args))

    def _host(self, fn, *args):
        """A host tool: works on the party id and needs the account."""
        return self._took(state.call(fn, self.V["party"]["id"], *args))

    @handle("", "show")
    def form_show(self, **event_args):
        if self._timer is None:
            self._timer = window.setInterval(self._tick_fn, 30000)
        if getattr(self, "_just_made", False):
            self._just_made = False
            node = state.control(self.link_box)
            node.scrollIntoView({"block": "center"})
            getattr(node, "select")()

    @handle("", "hide")
    def form_hide(self, **event_args):
        if self._timer is not None:
            window.clearInterval(self._timer)
            self._timer = None

    def _tick(self):
        if window.document.hidden or window.PF.dialogOpen() or window.PF.typingIn(anvil.js.get_dom_node(self)):
            return
        self._load(True)

    # ---------------------------------------------------------------- drawing
    def _draw(self):
        V = self.V
        p, st, me = V["party"], V["stats"], V.get("me")
        past = pf.all_past(p)
        self.missing_part.visible, self.page_part.visible = False, True
        signed_in = bool(state.me())
        self.sample_bar.visible = bool(p.get("demo"))
        self.copy_sample_button.visible = signed_in
        self.sample_signup.visible = not signed_in
        self._hero(p, st, past)
        self._share(p)
        self._slip(p, me)
        self._when(p, st, me)
        self._menu(p, st)
        self._book(me)
        self._guests(p, st)
        self._table(st)

    def _hero(self, p, st, past):
        d = self.dom_nodes
        self.hero_art.cover = p["cover"]
        self.hero_cover.classes["red"] = bool(p.get("chosen"))
        stamp = "RSVPs closed" if p["status"] == "closed" else "Been & gone" if past else ""
        self.hero_stamp.visible = bool(stamp)
        self.hero_stamp.classes["navy"] = p["status"] != "closed"
        d["stamp_text"].textContent = stamp
        d["hero_no"].textContent = "Catalogue %s · %s" % (p.get("catalog_no") or "", pf.STYLE_NAMES.get(p["style"], "Potluck"))
        d["hero_title"].textContent = p["title"]
        d["meta_host"].textContent = "Hosted by " + (p.get("host_name") or "")
        self.meta_loc_part.visible = bool(p.get("location"))
        d["meta_loc"].textContent = p.get("location") or ""
        d["meta_seats"].textContent = state.plural(st["heads"], "seat") + " taken" + (" of %d" % p["cap"] if p.get("cap") else "")
        self.meta_out.visible = bool(p.get("outdoors"))
        self.blurb.text, self.blurb.visible = p.get("blurb") or "", bool(p.get("blurb"))
        host = self.V.get("is_host")
        self.when_on.visible = bool(p.get("chosen"))
        self.when_tbd.visible = not p.get("chosen")
        if p.get("chosen"):
            d["when_text"].textContent = pf.when_text(p)
            d["gcal_link"].setAttribute("href", pf.google_cal(p))
        else:
            d["tbd_label"].textContent = "Day to be decided · " + state.plural(len(p["slots"]), "option")
            d["tbd_text"].textContent = ("Leading: %s, %s" % (pf.slot_label(st["best"]), pf.short_date(pf.slot(st["best"])[0]))) if st.get("best") else "Waiting for answers"
            self.lock_best_button.visible = bool(host and st.get("best") and not p.get("demo"))
        self._weather(p, st)
        self.again_note.visible = bool(host and past and not p.get("demo"))

    def _weather(self, p, st):
        """The weather check: for the locked-in day, else the leading one, else the first slot with a forecast."""
        w, d = self.V.get("weather"), self.dom_nodes
        host = self.V.get("is_host")
        self.wx_hint.visible = not w and bool(host) and not p.get("demo")
        d["wx_edit_link"].setAttribute("href", router.href("edit", p["id"]))
        self.wx_box.visible = self.wx_credit.visible = bool(w)
        if not w:
            return
        key = p.get("chosen") or st.get("best")
        f = w["slots"].get(key) if key else None
        if not f:
            ahead = [k for k in p["slots"] if w["slots"].get(k) and not pf.is_past(k)]
            key = ahead[0] if ahead else None
            f = w["slots"].get(key) if key else None
        town = (w.get("place") or "").split(",")[0]
        d["wx_updated"].textContent = ((" · updated " + state.ago(w["updated"])) if w.get("updated") else "") + \
            ("" if w.get("ok") else " · the weather service is slow to answer, so this may be a little old")
        self.wx_ic.visible = self.units_seg.visible = bool(f)
        if not f:
            d["wx_label"].textContent = "Weather check · " + town
            d["wx_big"].textContent = ""
            d["wx_small"].textContent = "This weekend has been and gone." if all(pf.is_past(k) for k in p["slots"]) else \
                "The forecast opens about two weeks ahead. Check back closer to the day."
            d["wx_advice"].textContent = ""
            return
        kind = pf.wx_kind(f.get("code"), f.get("hour"))
        self.wx_art.wx = f
        d["wx_label"].textContent = "Weather check · %s · %s" % (pf.slot_label(key), town)
        d["wx_big"].textContent = "%s, %s" % (kind[1], pf.temp(f.get("temp")))
        d["wx_small"].textContent = "%d%% chance of rain · wind %s" % (f.get("rain") or 0, pf.wind(f.get("wind"))) + \
            (" · high %s, low %s" % (pf.temp(f["tmax"]), pf.temp(f.get("tmin"))) if f.get("tmax") is not None else "")
        d["wx_advice"].textContent = pf.advice(f, w.get("outdoors"))
        u = pf.units()
        self.u_c.classes["on"], self.u_f.classes["on"] = u == "C", u == "F"

    def _share(self, p):
        host = bool(self.V.get("is_host"))
        demo = bool(p.get("demo"))
        url, text = pf.party_url(p["token"]), pf.invite_text(p)
        enc = window.encodeURIComponent
        self.share_box.visible = host
        self.pass_card.visible = not host and not demo
        d = self.dom_nodes
        for sms, wa, mail in (("sms_link", "wa_link", "mail_link"), ("sms2_link", "wa2_link", "mail2_link")):
            d[sms].setAttribute("href", "sms:?&body=" + str(enc(text)))
            d[wa].setAttribute("href", "https://wa.me/?text=" + str(enc(text)))
            d[mail].setAttribute("href", "mailto:?subject=" + str(enc("Invitation: " + p["title"])) + "&body=" + str(enc(text)))
        for k in ("sheet_link", "sheet2_link"):
            d[k].setAttribute("href", router.href("sheet", p["token"]))
        self.share_button.visible = self.share2_button.visible = pf.can_share()
        if not host:
            return
        self.link_box.text = url
        closed = p["status"] == "closed"
        self.status_badge.visible = not demo
        self.status_badge.text = "RSVPs closed" if closed else "Taking RSVPs"
        self.status_badge.role = ["badge", "badge-bad" if closed else "badge-good"]
        self.edit_link.visible = not demo
        state.set_attr(self.edit_link, "href", router.href("edit", p["id"]))
        self.lock_button.visible = not demo and not p.get("chosen")
        self.unlock_button.visible = not demo and bool(p.get("chosen"))
        self.status_button.visible = not demo
        self.status_button.text = "Reopen RSVPs" if closed else "Close RSVPs"
        self.status_button.role = ["btn", "btn-sm", "ic-check" if closed else "ic-x"]
        self.delete_button.visible = not demo

    def _slip(self, p, me):
        self.join_slip.visible = not me
        self.mine_slip.visible = bool(me)
        if not me:
            blocked = "This is a sample party, so the guest list is just for show." if p.get("demo") else \
                "The host has closed RSVPs for this party." if p["status"] == "closed" else ""
            self.blocked_note.text, self.blocked_note.visible = blocked, bool(blocked)
            self.join_form.visible = not blocked
            if not self.join_name.text:
                self.join_name.text = self.V.get("suggest_name") or pf.get("name", "") or ""
            self.signin_hint.visible = not state.me() and not p.get("demo")
            return
        closed = p["status"] == "closed" and not self.V.get("is_host")
        head = {"yes": "You're coming, ", "maybe": "Maybe coming, "}.get(me["rsvp"], "Not this time, ")
        self.dom_nodes["mine_title"].textContent = head + me["name"] + ("" if me["rsvp"] == "no" else "!")
        for b, k in ((self.r_yes, "yes"), (self.r_maybe, "maybe"), (self.r_no, "no")):
            b.role = ["seg", "rsvp-" + k] + (["on"] if me["rsvp"] == k else [])
            b.enabled = not closed
            state.set_control_attr(b, "aria-pressed", "true" if me["rsvp"] == k else "false")
        self.plus_n.text = "+%d" % me["plus"]
        self.plus_less.enabled = self.plus_more.enabled = not closed
        state.set_control_attr(self.plus_less, "aria-label", "Fewer extra people")
        state.set_control_attr(self.plus_more, "aria-label", "More extra people")
        self.diets_panel.items = [{"key": k, "text": n, "role": ["pt-tog"], "on": k in me["diet"]} for k, n in pf.DIETS]
        self.closed_note.visible = closed
        self.forget_part.visible = not me.get("is_host")

    def _when(self, p, st, me):
        V = self.V
        host = V.get("is_host")
        can = bool(me) and me["rsvp"] != "no" and not p.get("chosen") and not (p["status"] == "closed" and not host)
        W = (V.get("weather") or {}).get("slots") or {}
        driest = None
        if V.get("weather") and V["weather"].get("outdoors"):
            for k in p["slots"]:
                if W.get(k) and not pf.is_past(k) and (driest is None or (W[k].get("rain") or 0) < (W[driest].get("rain") or 0)):
                    driest = k
            if driest and len([k for k in p["slots"] if W.get(k)]) < 2:
                driest = None
        names = {g["id"]: g["name"] for g in V["guests"]}
        my_id = me["id"] if me else None
        rows = []
        for k in p["slots"]:
            day, part = pf.slot(k)
            t = st["slots"].get(k) or {"yes": [], "maybe": [], "no": []}
            past, chosen = pf.is_past(k), p.get("chosen") == k
            time = pf.time_label(p["chosen_time"]) if chosen and p.get("chosen_time") else pf.time_label(pf.part_time(part))
            sub = "· %s · %d free" % (time, len(t["yes"])) + (", %d maybe" % len(t["maybe"]) if t["maybe"] else "") + (" · past" if past else "")
            chips = [{"name": names.get(i, "?"), "kind": "", "me": i == my_id} for i in t["yes"]] + \
                    [{"name": names.get(i, "?"), "kind": "maybe", "me": i == my_id} for i in t["maybe"]]
            rows.append({"key": k, "day": pf.day_name(day, True), "date": pf.short_date(day), "part": pf.part_label(part), "sub": sub,
                         "wx": W.get(k), "driest": driest == k, "chips": chips, "mine": (me["avail"].get(k) if me else None) or "",
                         "can": can and not past, "chosen": chosen, "best": not p.get("chosen") and st.get("best") == k,
                         "dim": bool(p.get("chosen")) and not chosen, "past": past and not chosen,
                         "lock": bool(host) and not p.get("chosen") and not p.get("demo"), "label": pf.slot_label(k)})
        self.slots_panel.items = rows
        hint = "The host locked in the day. See you there!" if p.get("chosen") else "Put your name down above to answer." if not me else \
            "You said you can't come. Change your RSVP to answer." if me["rsvp"] == "no" else "Tap ✓ free, ~ maybe or ✕ can't for each one."
        self.dom_nodes["when_hint"].textContent = hint

    def _menu(self, p, st):
        V, d = self.V, self.dom_nodes
        menu = st["menu"]
        still = ["%d × %s" % (menu[c]["wanted"] - menu[c]["have"], c.lower()) for c in menu if menu[c]["have"] < menu[c]["wanted"]]
        pct = int(round(100.0 * st["filled"] / st["wanted_total"])) if st["wanted_total"] else 0
        d["dish_count"].textContent = state.plural(st["dishes"], "dish", "dishes") + " promised"
        self.meter_row.visible = bool(st["wanted_total"])
        d["filled"].textContent = "%d of %d filled" % (st["filled"], st["wanted_total"])
        d["still"].textContent = ("Still wanted: " + ", ".join(still[:4]) + ("…" if len(still) > 4 else "")) if still else "Every section is covered. Bravo!"
        d["meter"].setAttribute("aria-valuenow", str(pct))
        d["meter_bar"].style.width = "%d%%" % pct
        open_ = not p.get("demo")
        cats = [c for c in p["categories"] if menu.get(c) and (menu[c]["wanted"] or menu[c]["have"] or c != "Something else")]
        if "Something else" not in cats:
            cats.append("Something else")
        items = []
        for c in cats:
            m = menu.get(c) or {"wanted": 0, "have": 0}
            dishes = []
            for x in V["dishes"]:
                if x["category"] != c:
                    continue
                dishes.append({"id": x["id"], "name": x["name"], "by": x["by"] + (" · serves %d" % x["serves"] if x.get("serves") else ""),
                               "tags": [{"text": pf.tag_label(t), "role": ["badge", "badge-bad" if t == "nuts" else "badge-warn" if t == "spicy" else "badge-good"]} for t in x["tags"]],
                               "note": x.get("note") or "", "can_remove": bool(x.get("can_remove")) and open_})
            need = ("Covered" if m["have"] >= m["wanted"] else "%d wanted" % (m["wanted"] - m["have"])) if m["wanted"] else ""
            items.append({"cat": c, "need": need, "have": m["have"], "wanted": m["wanted"], "dishes": dishes,
                          "empty": "Nobody yet. Could it be you?" if m["wanted"] else "Anything else you'd like to bring.",
                          "open": open_, "bring": "I'll bring " + ("something" if c == "Something else" else "one")})
        self.cats_panel.items = items

    def _book(self, me):
        V = self.V
        demo = V["party"].get("demo")
        self.dom_nodes["note_count"].textContent = state.plural(len(V["comments"]), "note")
        self.note_form.visible = bool(me) and not demo
        self.note_hint.visible = not me and not demo
        notes = list(reversed(V["comments"]))
        for c in notes:
            c["removable"] = bool(c.get("can_remove")) and not demo
        self.notes_panel.items = notes
        self.no_notes.visible = not notes

    def _guests(self, p, st):
        V = self.V
        host, demo = V.get("is_host"), p.get("demo")
        self.seats_part.visible = bool(p.get("cap"))
        if p.get("cap"):
            pct = min(100, int(round(100.0 * st["heads"] / p["cap"])))
            self.dom_nodes["seats_b"].textContent = "%d of %d" % (st["heads"], p["cap"])
            self.dom_nodes["seat_bar"].style.width = "%d%%" % pct
            self.dom_nodes["seat_meter"].setAttribute("aria-valuenow", str(pct))
        groups = []
        for k, label in GROUPS:
            lst = [g for g in V["guests"] if g["rsvp"] == k]
            if not lst:
                continue
            groups.append({"label": "%s · %d" % (label, st["heads"] if k == "yes" else len(lst)),
                           "guests": [{"id": g["id"], "name": g["name"], "kind": "" if k == "yes" else "maybe", "mine": g.get("mine"),
                                       "plus": g.get("plus") or 0, "is_host": g.get("is_host"),
                                       "diet": ", ".join(pf.diet_label(x) for x in g["diet"]),
                                       "kick": bool(host) and not g.get("is_host") and not demo} for g in lst]})
        self.groups_panel.items = groups
        self.no_guests.visible = not V["guests"]

    def _table(self, st):
        V = self.V
        diets, dishes = st["diets"], V["dishes"]
        self.diet_sum_panel.items = [{"a": pf.diet_label(k), "b": str(n)} for k, n in diets.items()]
        self.no_diets.visible = not diets
        warn = []
        nuts = [x for x in dishes if "nuts" in x["tags"]]
        if diets.get("nutfree") and nuts:
            warn.append("%s a nut allergy, and %s %s nuts." % (state.plural(diets["nutfree"], "guest has", "guests have"),
                                                              ", ".join(x["name"] for x in nuts), "has" if len(nuts) == 1 else "have"))
        veg = (diets.get("veg") or 0) + (diets.get("vegan") or 0)
        veg_dishes = len([x for x in dishes if "veg" in x["tags"] or "vegan" in x["tags"]])
        if veg and len(dishes) >= 3 and veg_dishes < 2:
            warn.append("Only %s tagged vegetarian for %s." % (state.plural(veg_dishes, "dish is", "dishes are"), state.plural(veg, "veggie guest")))
        if diets.get("vegan") and dishes and not any("vegan" in x["tags"] for x in dishes):
            warn.append("Nothing on the menu is tagged vegan yet.")
        if diets.get("gf") and len(dishes) >= 3 and not any("gf" in x["tags"] for x in dishes):
            warn.append("Nothing is tagged gluten-free yet.")
        self.warn_panel.items = [{"text": "ⓘ " + w, "role": ["pt-warn"]} for w in warn]

    # ---------------------------------------------------------------- guest actions
    def _need_name(self):
        node = anvil.js.get_dom_node(self.join_slip)
        node.scrollIntoView({"behavior": "smooth", "block": "center"})
        if self.join_form.visible:
            self.join_name.focus()
        state.toast("Put your name down first, then you're in.")

    def _join(self, rsvp):
        name = (self.join_name.text or "").strip()
        if not name:
            self.join_name.focus()
            state.toast("Please tell the host your name.", "error")
            return
        pf.put("name", name)
        if self._call("guest_join", name, rsvp, 0):
            if rsvp == "yes":
                pf.confetti()
            state.toast("Thanks for letting them know." if rsvp == "no" else "You're on the list! Now tick the days you're free.", "ok")

    @handle("join_yes", "click")
    def join_yes_click(self, **event_args):
        self._join("yes")

    @handle("join_maybe", "click")
    def join_maybe_click(self, **event_args):
        self._join("maybe")

    @handle("join_no", "click")
    def join_no_click(self, **event_args):
        self._join("no")

    @handle("join_name", "pressed_enter")
    def join_name_pressed_enter(self, **event_args):
        self._join("yes")

    def _rsvp(self, k):
        me = self.V.get("me")
        if me and me["rsvp"] != k and self._call("guest_save", {"rsvp": k}):
            state.toast("RSVP saved", "ok")

    @handle("r_yes", "click")
    def r_yes_click(self, **event_args):
        self._rsvp("yes")

    @handle("r_maybe", "click")
    def r_maybe_click(self, **event_args):
        self._rsvp("maybe")

    @handle("r_no", "click")
    def r_no_click(self, **event_args):
        self._rsvp("no")

    def _plus(self, n):
        me = self.V.get("me")
        if me:
            self._call("guest_save", {"plus": max(0, min(6, me["plus"] + n))})

    @handle("plus_less", "click")
    def plus_less_click(self, **event_args):
        self._plus(-1)

    @handle("plus_more", "click")
    def plus_more_click(self, **event_args):
        self._plus(1)

    def _diet(self, key, **e):
        me = self.V.get("me")
        if not me:
            return
        diet = list(me["diet"])
        if key in diet:
            diet.remove(key)
        else:
            diet.append(key)
        self._call("guest_save", {"diet": diet})
        state.refocus(self.diets_panel, key)

    def _answer(self, key, ans, **e):
        me = self.V.get("me")
        if not me:
            return
        self._call("guest_save", {"avail": {key: "" if me["avail"].get(key) == ans else ans}})
        state.refocus(self.slots_panel, key + ":" + ans)

    def _bring(self, cat, **e):
        if not self.V.get("me"):
            self._need_name()
            return
        from ...Dialogs.Bring import Bring
        dish = alert(Bring(party=self.V["party"], category=cat), buttons=[], role="app-dialog", dismissible=True)
        if dish and self._call("dish_add", dish):
            state.toast("On the menu. Thank you!", "ok")

    def _deldish(self, id, **e):
        if confirm("", title="Take it off the menu?", buttons=[("Cancel", False), ("Remove", True)], role="app-dialog"):
            self._call("dish_remove", id)

    def _delnote(self, id, **e):
        if confirm("", title="Delete this note?", buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            self._call("comment_remove", id)

    @handle("post_button", "click")
    def post_button_click(self, **event_args):
        body = (self.note_box.text or "").strip()
        if not body:
            return
        if self._call("comment_add", body):
            self.note_box.text = ""
            state.toast("Posted", "ok")

    @handle("rename_button", "click")
    def rename_button_click(self, **event_args):
        from ...Dialogs.Rename import Rename
        name = alert(Rename(name=self.V["me"]["name"]), buttons=[], role="app-dialog", dismissible=True)
        if name and self._call("guest_save", {"name": name}):
            pf.put("name", name)
            state.toast("Saved", "ok")

    @handle("forget_button", "click")
    def forget_button_click(self, **event_args):
        if confirm("Your RSVP, your days, your dishes and your notes are deleted.", title="Take yourself off the list?",
                   buttons=[("Cancel", False), ("Take me off", True)], role="app-dialog"):
            if self._call("guest_forget"):
                pf.set_secret(self.token, None)
                self.secret = None
                state.toast("You're off the list. Maybe next time!")

    # ---------------------------------------------------------------- sharing
    def _copy(self):
        ok = pf.copy(pf.party_url(self.V["party"]["token"]))
        state.toast("Link copied. Paste it anywhere!" if ok else "Select the link and copy it by hand.", "ok" if ok else "error")

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        self._copy()
        getattr(state.control(self.link_box), "select")()

    @handle("copy2_button", "click")
    def copy2_button_click(self, **event_args):
        self._copy()

    def _share_sheet(self):
        p = self.V["party"]
        url = pf.party_url(p["token"])
        pf.share(p["title"], pf.invite_text(p).replace(url, "").strip(), url)

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        self._share_sheet()

    @handle("share2_button", "click")
    def share2_button_click(self, **event_args):
        self._share_sheet()

    @handle("ics_button", "click")
    def ics_button_click(self, **event_args):
        pf.download_ics(self.V["party"])

    def units_click(self, event):
        pf.set_units(str(event.currentTarget.getAttribute("data-u")))
        self._draw()

    # ---------------------------------------------------------------- host tools
    def _lock(self, key):
        from ...Dialogs.LockDay import LockDay
        V = self.V
        pick = alert(LockDay(party=V["party"], stats=V["stats"], pick=key), buttons=[], role="app-dialog", dismissible=True)
        if pick and self._host("lock_slot", pick[0], pick[1]):
            pf.confetti()
            state.toast("It's on! Your guests can see the day now.", "ok")

    def _lock_key(self, key, **e):
        self._lock(key)

    @handle("lock_best_button", "click")
    def lock_best_button_click(self, **event_args):
        self._lock(self.V["stats"].get("best"))

    @handle("lock_button", "click")
    def lock_button_click(self, **event_args):
        self._lock(None)

    @handle("unlock_button", "click")
    def unlock_button_click(self, **event_args):
        if confirm("The day is unlocked and guests can answer again.", title="Change the day?",
                   buttons=[("Cancel", False), ("Unlock", True)], role="app-dialog"):
            self._host("lock_slot", None, None)

    @handle("status_button", "click")
    def status_button_click(self, **event_args):
        to = "open" if self.V["party"]["status"] == "closed" else "closed"
        if self._host("set_party_status", to):
            state.toast("RSVPs closed. The guest list is final." if to == "closed" else "RSVPs are open again.", "ok")

    def _kick(self, id, name, **e):
        if confirm("Their RSVP, dishes and notes are deleted. They can join again with the link.", title="Remove %s?" % name,
                   buttons=[("Cancel", False), ("Remove", True)], role="app-dialog"):
            self._host("host_remove_guest", id)

    def _dup(self):
        r = state.call("duplicate_party", self.V["party"]["id"])
        if r:
            state.toast("A fresh copy is ready. Check the days and send it!", "ok")
            router.go("edit", r["id"])

    @handle("dup_button", "click")
    def dup_button_click(self, **event_args):
        self._dup()

    @handle("again_button", "click")
    def again_button_click(self, **event_args):
        self._dup()

    @handle("copy_sample_button", "click")
    def copy_sample_button_click(self, **event_args):
        self._dup()

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if confirm("The guest list, menu and notes are deleted, and the link stops working. This can't be undone.",
                   title="Delete this party?", buttons=[("Cancel", False), ("Delete the party", True)], role="app-dialog"):
            if state.call("remove_party", self.V["party"]["id"]):
                pf.forget(self.token)
                state.toast("Party deleted.")
                router.go("home")
