import asyncio
from playwright.async_api import async_playwright
import time

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        print("1. Navigate to http://localhost:5173")
        await page.goto("http://localhost:5173")
        
        # Helper to ensure field is clear
        async def clear_and_type(selector, text):
            await page.click(selector)
            await page.keyboard.press("Meta+A")
            await page.keyboard.press("Backspace")
            await page.fill(selector, text)

        print("2. Login using existing account")
        await clear_and_type("input[type='email']", "click2@clickrush.dev")
        await clear_and_type("input[type='password']", "apitest123")
        await page.click("button[type='submit']")
        
        # Wait for home page to load
        print("Wait for home page...")
        await page.wait_for_selector("text=🏆 Leaderboard", timeout=10000)
        print("Login successful.")
        
        print("3. Start a game")
        await page.click("button.start-btn:has-text('Start Game')")
        
        print("4. Complete a game (waiting 62 seconds...)")
        await page.wait_for_selector("text=Time's Up!", timeout=65000)
        print("Game completed.")
        await page.screenshot(path="../game_completed.png")
        
        print("5. Open Profile")
        await page.click("button#profile-btn")
        await page.wait_for_selector("text=Current Rankings", timeout=5000)
        await page.screenshot(path="../profile_page.png")
        
        print("6-8. Confirm history, PB, ranks exist")
        pb_value = await page.locator(".prof-pb-value").inner_text()
        print(f"Personal Best: {pb_value}")
        history_rows = await page.locator(".prof-history-table .lb-row").count()
        print(f"History Rows: {history_rows}")
        
        print("9. Open public Leaderboard")
        await page.click("button:has-text('Back')")
        await page.click("button#leaderboard-btn")
        await page.wait_for_selector("text=Global Leaderboard", timeout=5000)
        await page.screenshot(path="../leaderboard_page.png")
        
        print("11. Logout")
        await page.click("button:has-text('Back')")
        await page.click("button#logout-btn")
        
        print("12. Login again")
        await page.wait_for_selector("input[type='email']", timeout=5000)
        await clear_and_type("input[type='email']", "click2@clickrush.dev")
        await clear_and_type("input[type='password']", "apitest123")
        await page.click("button[type='submit']")
        await page.wait_for_selector("text=🏆 Leaderboard", timeout=10000)
        
        print("13. Start another game")
        await page.click("button.start-btn:has-text('Start Game')")
        
        print("14. Confirm start-game works (no active session error)")
        await page.wait_for_selector("text=Click!", timeout=5000)
        print("Game started successfully!")
        
        await browser.close()
        print("All steps completed successfully.")

asyncio.run(main())
