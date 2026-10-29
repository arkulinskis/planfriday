# Plan Friday

Plan Friday (planfriday.com) is for last-minute weekend dinner parties. On Friday, a host makes a party page and sends one link.
Friends open it with no account, put their name down, tick which weekend slot suits them, say what they're bringing
(soup, salad, dessert...) and leave notes. The host locks in the best day. It looks like a 1960s mail-order catalogue.
Built on [Anvil](https://anvil.works).

- **App repo:** github.com/arkulinskis/planfriday (branch `master`). Anvil pulls `master`.
- **Live:** not published yet (meant for https://planfriday.com).

## What it does

**For everyone (no account):**
- **Landing page** (`#`): the promise, how it works, a host column and a guest column, features, FAQ, links to a sample party.
- **The Weekend Catalogue** (`#catalogue`): 13 ready-made party ideas (Soup Night Supper, Taco Saturday, Sunday Pancake Brunch,
  Dumpling Folding Party, Fondue & Fiasco...), each with an item number, a picture, serves / effort / style / best day and a
  suggested menu. Filters: cosy, brunch, hands-on, big crowd, outdoors. "Order this party" opens the party form filled in.
- **A party page** (`#p/<token>`), the page behind the link:
  - The party's picture, catalogue number, host, place, seats taken, the host's note, and the day once it's locked in
    ("It's on!", add to calendar as .ics or Google Calendar).
  - **Order slip:** put your name down ("Count me in" / "Maybe" / "Can't make it"). The browser remembers you (a secret key
    in local storage). Then change your RSVP, bring +0–6 people, and tick diets (vegetarian, vegan, gluten-free, dairy-free,
    nut allergy, halal). "Take me off the guest list" deletes everything you added.
  - **When are you free?** Each slot (Fri dinner, Sat brunch...) shows who's free (initial chips) and who's a maybe; you answer
    ✓ / ~ / ✕. The best slot gets a "Best bet" sticker.
  - **The menu:** sections with how many are wanted (filled tick boxes), a meter ("6 of 10 filled", "Still wanted: 1 × soup"),
    dishes on dotted price lines (who, serves, tags: veg, vegan, GF, dairy-free, has nuts, spicy), "I'll bring one" with a
    dice that suggests a dish. Every party also has "Something else".
  - **Letters to the host:** a guestbook.
  - **The guest list** (coming / maybe / can't, +1s, diets, seat meter) and **At the table** (diet counts, plus warnings such as a
    nut allergy next to a dish with nuts, or vegetarians without veggie dishes).
  - **Pass it on:** copy the link, share, text, WhatsApp, email.
  - It refreshes itself every 30 seconds while you're not typing.
- **Order sheet** (`#sheet/<token>`): a printable page with the day, the facts, every dish by section with tick boxes and the
  "still wanted" gaps, and the guest list.
- **Sample parties:** `#p/sample` (Soup Night), `#p/sample-brunch` (day locked in), `#p/sample-dumplings`. They're look-only and
  always sit on the coming weekend.

**For hosts (free account):**
- **Your weekend** (`#home`): a Friday countdown ("2 days to Friday", "It's Friday!"), a coupon to start a party, the parties you
  host and the ones you're invited to (as cards with the leading day, seats and menu progress), links opened on this device,
  and three daily picks from the catalogue.
- **Host a party** (`#new`, `#new/<idea>`), an order blank in four numbered sections: name and picture (13 drawings), the slots
  (this weekend or next, Fri dinner/late, Sat brunch→late, Sun brunch→dinner), the menu (sections + how many, presets) and
  the particulars (potluck / host cooks / bring your own, place, seat limit, note). On creation the page opens with the link
  ready to copy, plus confetti.
- **Host tools** on the party page: lock in the day (pick a slot and a start time, confetti), change the day, close / reopen RSVPs,
  edit (`#edit/<id>`), order sheet, run it again (a copy moved to next weekend), delete, remove a guest, remove any dish or note.
  Signed-in hosts can copy a sample party into their own.
- Signed-in people who join a party are remembered by their account on any device. If they joined as a guest first, signing in
  keeps their place.

**For admins** (`#admin`; arkulinskis@gmail.com becomes an admin on first sign-in):
- **Overview:** people, admins, new feedback, parties, names on guest lists.
- **Feedback inbox:** New / Read / Done, private notes.
- **Users:** search, make admin, disable an account.
- **Parties:** every party with its host (and email), guests, dishes and notes; open or delete it.
- **Demo data:** the three sample parties; remove or reload them.

## Setting it up in Anvil (once)

1. In the Anvil editor: **Create app → Clone from GitHub**, and paste `https://github.com/arkulinskis/planfriday`.
2. **Users** service: email + password, sign-up allowed (already set in `anvil.yaml`; check it).
3. Open the app in the editor. If it shows a **Schema Mismatch** alert, choose **"The schema of the source code is correct"** so Anvil creates the tables.
4. **Run** it and sign up with **arkulinskis@gmail.com** straight away (that account becomes the admin).
5. **Publish** (Publish → public URL, or your own domain).

## Working on it

See `.claude/skills/planfriday/SKILL.md`. In short:

```
python -I tools/check.py --ui                    # syntax, server tests, headless UI tests → ALL CHECKS PASSED
python -I tools/preview/devserver.py 8765        # the app on in-memory data: http://localhost:8765/  (?as=ana#home, ?as=admin#admin)
python tools/deploy.py                           # dry run (needs PyYAML, so no -I)
python tools/deploy.py --push "Message"          # deploy: commit + push to GitHub, Anvil pulls it
```

## Project layout

```
web/            the interface: core.js/core.css (shared engine + catalogue design), app.js (masthead, footer), pages/*.html
                pages/_shared.html = window.PF: pictures, catalogue ideas, weekend dates, dish ideas, sharing, calendar, confetti
client_code/    Main.py (the only Anvil form: bridge to the server, sign-in), legal.py
server_code/    common.py, Accounts.py, Feedback.py, Admin.py, DemoData.py, legal_server.py,
                Parties.py (hosts), Guests.py (the party link)
assets/         icon.svg + generated PNG icons (served at _/theme/<name>)
tools/          sync_to_anvil.py (settings + table schema), deploy.py, check.py, preview/ (dev server, UI tests, screenshots), testing/
```
