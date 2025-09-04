import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://edition.cnn.com/markets/fear-and-greed"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until='networkidle', timeout=60000)
            content = await page.content()
            with open("cnn_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            await browser.close()
            print("Successfully saved cnn_page.html")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
