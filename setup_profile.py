"""
Quick script to launch Chromium with persistent profile for signing in.
Run this once to sign into your accounts, then close the browser.
"""
import asyncio
from playwright.async_api import async_playwright
from config import Config

async def main():
    print("=" * 80)
    print("CHROMIUM PROFILE SETUP")
    print("=" * 80)
    print(f"\nProfile directory: {Config.BROWSER_USER_DATA_DIR}")
    print("\nThis will open Chromium. Please:")
    print("1. Sign into YouTube/Google")
    print("2. Sign into any other services (Supabase, Notion, etc.)")
    print("3. Close the browser when done")
    print("\nYour login sessions will be saved for future test runs.")
    print("=" * 80)

    input("\nPress Enter to launch Chromium...")

    async with async_playwright() as p:
        print("\nLaunching Chromium...")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=Config.BROWSER_USER_DATA_DIR,
            headless=False,
            channel=Config.BROWSER_CHANNEL if Config.BROWSER_CHANNEL != 'chromium' else None,
            viewport={
                'width': Config.BROWSER_VIEWPORT_WIDTH,
                'height': Config.BROWSER_VIEWPORT_HEIGHT
            }
        )

        # Open a page
        page = await browser.new_page()
        await page.goto('https://youtube.com')

        print("\nBrowser launched! Sign in to your accounts.")
        print("Close the browser window when you're done signing in.")
        print("(Waiting for browser to close...)")

        # Wait for user to close browser
        await browser.wait_for_event('close', timeout=0)

        print("\n" + "=" * 80)
        print("SUCCESS - Your login sessions have been saved!")
        print("=" * 80)
        print(f"Profile location: {Config.BROWSER_USER_DATA_DIR}")
        print("\nYou can now run: python test_agent.py --predefined")
        print("=" * 80)

if __name__ == '__main__':
    asyncio.run(main())
