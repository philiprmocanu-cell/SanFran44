import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]
U = "http://localhost:8080/desk/"
with sync_playwright() as p:
    b = p.chromium.launch()
    jr = b.new_page(viewport={"width": 1500, "height": 940}, device_scale_factor=2)
    jr.goto(U); jr.wait_for_timeout(700)
    jr.get_by_text("Analyst · M&A", exact=True).first.click(); jr.wait_for_timeout(700)
    jr.get_by_text("Ridgeline Partners / Vantage Software").click()
    jr.get_by_role("button", name="Attach to my question").click(); jr.wait_for_timeout(300)
    jr.fill("#q", "Why is the break fee 2.1% during the go-shop but 3.5% after? I didn't want to ask in front of the team.")
    jr.mouse.click(5, 5)
    jr.screenshot(path=f"{S}/shot-ask.png")
    jr.click("#send"); jr.wait_for_timeout(1500)
    sr = b.new_page(viewport={"width": 1500, "height": 940}, device_scale_factor=2)
    sr.goto(U); sr.wait_for_timeout(700)
    sr.get_by_text("Managing Director · Leveraged Finance").click(); sr.wait_for_timeout(1200)
    sr.screenshot(path=f"{S}/shot-senior.png")
    sr.locator("textarea[data-t]").first.fill("The go-shop is the window where the board is supposed to look for a better offer, so the fee is kept low to make that search real. After it closes, the buyer has done the work and wants more protection, so the fee goes up. 2.1% and 3.5% are both normal for a take-private this size. Check whether the lower fee only applies to bidders who show up during the go-shop, that detail often gets missed.")
    sr.locator("button[id^=rb-]").first.click(); sr.wait_for_timeout(15000)
    jr.reload(); jr.wait_for_timeout(1500)
    jr.evaluate("VIEW='mine';renderNav();renderMain(true)"); jr.wait_for_timeout(500)
    jr.screenshot(path=f"{S}/shot-result.png")
    b.close()
