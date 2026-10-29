"""Make the PNG app icons from gawi/static/icons/logo.svg.

Phones and old browsers want PNG pictures in fixed sizes. Run this again
after changing the logo. It uses Playwright + Microsoft Edge (Windows has
Edge already). Playwright isn't in requirements.txt; the expense_tracker
venv has it:

    ..\\expense_tracker\\.venv\\Scripts\\python docs\\make_icons.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ICONS = Path(__file__).parent.parent / "gawi" / "static" / "icons"
TILE = "#fff4e6"  # the logo's own background colour

# (file, size, background, padding). The home-screen icons get a full tile
# with 14% padding, so Android can crop them into a circle ("maskable").
SIZES = [
    ("icon-32.png", 32, None, 0),
    ("apple-touch-icon.png", 180, TILE, 0.14),
    ("icon-192.png", 192, TILE, 0.14),
    ("icon-512.png", 512, TILE, 0.14),
]


def main():
    svg = (ICONS / "logo.svg").read_text(encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge")
        for name, size, background, padding in SIZES:
            page = browser.new_page(viewport={"width": size, "height": size})
            inner = round(size * (1 - 2 * padding))
            page.set_content(f"""
                <style>
                  html, body {{ margin: 0; background: {background or 'transparent'}; }}
                  div {{ width: {size}px; height: {size}px; display: grid; place-items: center; }}
                  svg {{ width: {inner}px; height: {inner}px; }}
                </style>
                <div>{svg}</div>""")
            page.screenshot(path=ICONS / name, omit_background=background is None)
            page.close()
            print("saved", name)
        browser.close()


if __name__ == "__main__":
    main()
