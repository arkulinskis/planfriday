"""Make the party-link preview pictures: theme/assets/covers/<cover>.png, one 1200x630 catalogue card per party picture.

    python -I tools/make_covers.py            all 13 (headless Chrome draws them, like make_icons.py)
    python -I tools/make_covers.py soup pie   just these

server_code/Preview.py puts them in /p/<token> as og:image (<site>/_/theme/covers/<cover>.png), so a party link pasted
into WhatsApp, iMessage or Slack shows the party's own drawing instead of the generic site card. The card is aged
catalogue paper with halftone dots, the red Plan Friday masthead, the drawing on a cream plate in the middle (chat apps
that crop to a square keep the plate), "You're invited!" in script and a starburst. The drawings come straight from
theme/assets/pf.js (PF.art), so a changed or new picture only needs this run again (and the cover added to COVERS in
server_code/Parties.py and client_code/pf.py). Each file must stay under 300 KB.
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "theme" / "assets"
OUT = ASSETS / "covers"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
COVERS = ["classic", "soup", "pancakes", "dumplings", "tacos", "fondue", "pizza", "roast", "salad", "pie", "wine", "bbq", "cake"]
LIMIT = 300 * 1024

BURST = ("50.0% 0.0%, 59.1% 10.0%, 71.7% 5.0%, 75.6% 17.9%, 89.1% 18.8%, 86.9% 32.2%, 98.7% 38.9%, 91.0% 50.0%, 98.7% 61.1%, "
         "86.9% 67.8%, 89.1% 81.2%, 75.6% 82.1%, 71.7% 95.0%, 59.1% 90.0%, 50.0% 100.0%, 40.9% 90.0%, 28.3% 95.0%, 24.4% 82.1%, "
         "10.9% 81.2%, 13.1% 67.8%, 1.3% 61.1%, 9.0% 50.0%, 1.3% 38.9%, 13.1% 32.2%, 10.9% 18.8%, 24.4% 17.9%, 28.3% 5.0%, 40.9% 10.0%")

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Alfa+Slab+One&family=Oswald:wght@500;600;700&family=Yellowtail&display=block" rel="stylesheet">
<style>
:root { --c-bg: #f2e8d3; --c-surface: #fbf6ea; --c-ink: #1f1a14; --c-brand: #c62a1f; --c-accent: #e3a21a; --c-navy: #23416d;
  --c-good: #2c7a3b; --c-muted: #5f5446; }
html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; }
body { position: relative; color: var(--c-ink); font-family: Oswald, sans-serif;
  background: var(--c-bg) radial-gradient(rgba(31, 26, 20, .12) 1.3px, transparent 1.6px) 0 0 / 10px 10px; }
.mast { position: absolute; left: 0; right: 0; top: 0; height: 96px; background: var(--c-brand); color: #fff8ec; border-bottom: 5px solid var(--c-ink);
  display: flex; align-items: center; justify-content: space-between; padding: 0 46px; box-sizing: border-box; }
.mast b { font: 400 50px/1 "Alfa Slab One", Georgia, serif; letter-spacing: .01em; }
.mast span { font: 600 21px/1 Oswald, sans-serif; letter-spacing: .22em; text-transform: uppercase; }
.plate { position: absolute; left: 340px; top: 134px; width: 520px; height: 404px; box-sizing: border-box; background: var(--c-surface);
  border: 5px solid var(--c-ink); box-shadow: 14px 14px 0 rgba(31, 26, 20, .92); display: grid; place-items: center; }
.plate svg { width: 430px; height: auto; display: block; overflow: visible; }
.inv { position: absolute; left: 44px; top: 158px; width: 268px; }
.inv .s { display: block; font: 400 70px/.95 Yellowtail, cursive; color: var(--c-brand); transform: rotate(-7deg); margin: 0 0 30px -4px; }
.inv .l { font: 600 25px/1.3 Oswald, sans-serif; letter-spacing: .13em; text-transform: uppercase; }
.inv .l i { display: block; width: 64px; border-top: 4px solid var(--c-ink); margin: 18px 0 16px; }
.inv .m { font: 500 21px/1.35 Oswald, sans-serif; letter-spacing: .08em; text-transform: uppercase; color: var(--c-muted); }
.burst { position: absolute; right: 52px; top: 178px; width: 236px; height: 236px; background: var(--c-accent); color: #1f1a14;
  clip-path: polygon(""" + BURST + """); display: grid; place-items: center; text-align: center; transform: rotate(9deg);
  font: 700 23px/1.1 Oswald, sans-serif; letter-spacing: .07em; text-transform: uppercase; }
.burst b { display: block; font: 400 50px/1 Yellowtail, cursive; text-transform: none; letter-spacing: 0; margin-bottom: 4px; }
.foot { position: absolute; left: 46px; right: 46px; bottom: 30px; display: flex; align-items: baseline; gap: 14px;
  font: 600 22px/1 Oswald, sans-serif; letter-spacing: .16em; text-transform: uppercase; }
.foot .dots { flex: 1; border-bottom: 4px dotted #6e6250; transform: translateY(-7px); }
.pf-art * { stroke: var(--c-ink); stroke-width: 2.4; stroke-linejoin: round; stroke-linecap: round; fill: none; }
.pf-art .r { fill: var(--c-brand); } .pf-art .y { fill: var(--c-accent); } .pf-art .n { fill: var(--c-navy); }
.pf-art .p { fill: var(--c-surface); } .pf-art .g { fill: var(--c-good); } .pf-art .k { fill: var(--c-ink); }
.pf-art .ns { stroke: none; } .pf-art .thin { stroke-width: 1.6; }
</style></head><body>
<div class="mast"><b>Plan Friday</b><span>The weekend catalogue</span></div>
<div class="inv"><span class="s">You're invited!</span><div class="l">Pick the day.<br>Say what you'll bring.<i></i></div>
  <div class="m">One link, no account</div></div>
<div class="plate" id="art"></div>
<div class="burst"><span><b>Tap</b>to RSVP</span></div>
<div class="foot"><span>Order your weekend</span><span class="dots"></span><span>planfriday.com</span></div>
<script src="PFJS"></script>
<script>document.getElementById('art').innerHTML = PF.art(new URLSearchParams(location.search).get('c'), '');</script>
</body></html>
"""


def render(cover, page, work):
    shot = work / (cover + ".png")
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--allow-file-access-from-files", "--virtual-time-budget=15000", "--window-size=1200,630",
                        "--user-data-dir=" + str(work / "profile"), "--screenshot=" + str(shot), page.as_uri() + "?c=" + cover],
                       capture_output=True, text=True, timeout=120)
    if not shot.exists():
        sys.exit("Chrome didn't make %s:\n%s" % (cover, r.stderr[-800:]))
    size = shot.stat().st_size
    if size > LIMIT:
        sys.exit("%s.png is %d KB (over 300 KB): simplify the card" % (cover, size // 1024))
    OUT.mkdir(exist_ok=True)
    shot.replace(OUT / (cover + ".png"))
    print("wrote covers/%s.png (%d KB)" % (cover, size // 1024))


def main():
    pick = [a for a in sys.argv[1:] if a in COVERS] or COVERS
    work = pathlib.Path(tempfile.mkdtemp(prefix="covers-"))
    page = work / "cover.html"
    page.write_bytes(PAGE.replace("PFJS", (ASSETS / "pf.js").as_uri()).encode("utf-8"))
    for cover in pick:
        render(cover, page, work)


if __name__ == "__main__":
    main()
