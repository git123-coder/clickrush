import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://localhost:5173")
        
        # Login
        await page.fill("input[type='email']", "click2@clickrush.dev")
        await page.fill("input[type='password']", "apitest123")
        await page.click("button[type='submit']")
        
        # Wait for home page
        await page.wait_for_selector("text=🏆 Leaderboard")
        
        # Click Profile
        await page.click("button#profile-btn")
        
        # Wait for profile page to load (rankings)
        await page.wait_for_selector("text=Current Rankings")
        await page.wait_for_timeout(1000) # Give it a second to render
        
        # Take screenshot
        await page.screenshot(path="../day4_profile.png")
        await browser.close()
        print("Screenshot saved to ../day4_profile.png")

asyncio.run(main())
