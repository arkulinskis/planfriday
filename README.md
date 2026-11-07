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
  - **Weather check:** if the host gave a town, every slot shows a forecast chip (icon, temperature, chance of rain), and a
    "Weather check" sticker covers the locked-in day (or the leading one) with wind, high/low and advice in script
    ("Rain plan needed: everyone into the kitchen!", "Perfect patio weather", "Proper soup weather"). Outdoor parties
    get a "Driest" badge on the slot least likely to rain. °C/°F switch (remembered). Forecasts come from
    [Open-Meteo](https://open-meteo.com/) (free, no key) through our server and are cached for an hour; the forecast reaches
    about 16 days ahead. Also on home cards and the order sheet.
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
  the particulars (potluck / host cooks / bring your own, place, seat limit, note, the town for the weather check with a
  "Check" button, and "It's outdoors", ticked for outdoor catalogue ideas). On creation the page opens with the link
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
2. **Users** service: email + password and "Continue with Google", sign-up allowed (already set in `anvil.yaml`; check it).
3. Open the app in the editor. If it shows a **Schema Mismatch** alert, choose **"The schema of the source code is correct"** so Anvil creates the tables.
4. **Run** it and sign up with **arkulinskis@gmail.com** straight away (that account becomes the admin).
5. **Publish** (Publish → public URL, or your own domain).

<!-- libraries:start -->
## Libraries and outside services

What this project uses besides its own code. Generated by `APP_MAKER/tools/libraries.py`; to change it, edit `APP_MAKER/libraries/catalog.py` and re-run the script.

| Name | How it gets in | Used here for |
|---|---|---|
| [Open-Meteo](https://open-meteo.com) | Outside web service | Friday-night weather for the party's town |
| [YouTube embeds](https://developers.google.com/youtube/player_parameters) | Outside web service | Plays a YouTube video inside the page (the privacy-friendlier youtube-nocookie address). |
| [Google Fonts](https://fonts.google.com) | Loaded from a CDN | Alfa Slab One, Oswald, Source Serif 4, Yellowtail |

**Built into the browser:** Web Share, localStorage, Clipboard, File downloads (Blob).

**Anvil platform:** Anvil, Anvil Data Tables, Anvil Google service, Anvil JS bridge (anvil.js), Anvil Users, Anvil HTTP.

**Build and test tools (not shipped):** Node.js, PyYAML, Headless Chrome (DevTools Protocol).

<!-- libraries:end -->

## Working on it

Native Anvil Forms (branch `forms`, Nov 2026): this folder *is* the Anvil app; pushing is the deploy. Code map: `APP_MAP.md`.

```
python tools/check.py                            # Anvil's validator, JS syntax, asset hashes, server tests -> ALL CHECKS PASSED
python -I tools/ui_test.py                       # smoke test in the Anvil App Server (Docker): every page, signed out / member / admin
python -I tools/ui_test.py --stop                # stop the local App Server
```

## Project layout

```
anvil.yaml      tables (db_schema), services, head_html (fonts, SEO, Prepsto, theme assets with ?v=)
client_code/    startup.py, router.py (#addresses), state.py, auth.py, legal.py, pf.py (ideas, dates, slots, diets, weather words)
                Layouts/Shell (masthead, footer, tab bar), Pages/ (Landing, Catalogue, Home, Plan, Party, Sheet, Auth, Profile, Admin),
                Items/ (RepeatingPanel rows), Components/ (Art, WxChip: the SVG pictures), Dialogs/ (Bring, LockDay, Rename)
server_code/    common.py, Accounts.py, Feedback.py, Admin.py, DemoData.py, legal_server.py, seo_routes.py, SchemaCheck.py,
                Parties.py (hosts), Guests.py (the party link), Weather.py (Open-Meteo look-up + forecast cache)
theme/assets/   app.css (tokens + catalogue skin + pages + role layer), pf.js (party pictures, weather icons, clipboard, confetti),
                app-kit.js, icons.css (generated), legal-kit.js, theme.css (spinner), icon.svg + PNGs
tools/          check.py, assets.py, build_icons.py, make_icons.py, ui_test.py + ui/ (smoke.js, a11y.js, design.js), live/, testing/
```
