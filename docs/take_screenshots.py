"""Take the README screenshots (docs/screenshots/*.png).

It logs in with "Try the demo", so no real habits show. It uses Microsoft
Edge, which Windows already has, through Playwright. Playwright is only a
tool for this script, so it is not in requirements.txt; the expense_tracker
venv has it:

    .venv\\Scripts\\flask --app gawi reset-demo           (fresh sample data)
    .venv\\Scripts\\flask --app gawi run --port 5004      (in another terminal)
    ..\\expense_tracker\\.venv\\Scripts\\python docs\\take_screenshots.py

Add a line to PAGES when a page is added.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5004"
OUT = Path(__file__).parent / "screenshots"
DESKTOP = {"width": 1280, "height": 800}
PHONE = {"width": 390, "height": 844}

# (file name, address, theme, screen size). "habit:Pray" opens that habit's page.
PAGES = [
    ("today.png", "/", "light", DESKTOP),
    ("today-dark.png", "/", "dark", DESKTOP),
    ("habit.png", "habit:Pray", "light", DESKTOP),
    ("habits.png", "/habits", "light", DESKTOP),
    ("new-habit.png", "/habits/new", "light", DESKTOP),
    ("phone.png", "/", "light", PHONE),
    ("phone-habit.png", "habit:Pray", "dark", PHONE),
]


def open_demo(browser, size, theme):
    page = browser.new_page(viewport=size, color_scheme=theme)
    page.goto(f"{BASE}/login")
    page.get_by_role("button", name="Try the demo").click()
    page.locator("[data-close-flash]").first.click()  # the welcome message
    return page


def shoot(browser, name, path, theme, size):
    page = open_demo(browser, size, theme)
    if path.startswith("habit:"):
        page.goto(f"{BASE}/habits")
        page.locator(".habit-name", has_text=path.split(":", 1)[1]).first.click()
    else:
        page.goto(f"{BASE}{path}")
    page.wait_for_load_state("networkidle")  # fonts and emoji are in
    if size is DESKTOP:
        # Make the window as tall as the page. (A "full page" screenshot would
        # cut the sidebar, which sticks to the screen, at the first screenful.)
        height = page.evaluate("document.documentElement.scrollHeight")
        page.set_viewport_size({"width": size["width"], "height": max(size["height"], height)})
    page.wait_for_timeout(600)  # let the rings finish filling
    page.screenshot(path=OUT / name)
    page.close()
    print("saved", name)


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge")

        page = browser.new_page(viewport=DESKTOP, color_scheme="light")
        page.goto(f"{BASE}/login")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=OUT / "login.png")
        page.close()
        print("saved login.png")

        for name, path, theme, size in PAGES:
            shoot(browser, name, path, theme, size)
        browser.close()


if __name__ == "__main__":
    main()
