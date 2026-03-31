import asyncio
import math
import re
from playwright.async_api import async_playwright


def _zoom_from_radius(radius_km: float) -> int:
    zoom = round(14 - math.log2(max(radius_km, 0.5) / 2))
    return max(10, min(16, zoom))


def _extract_place_id(url: str) -> str | None:
    # https://www.google.com/maps/place/Name/...
    match = re.search(r"/place/([^/]+)/", url)
    if match:
        return match.group(1)
    # fallback: use chunk of URL
    match = re.search(r"!1s([^!]+)!", url)
    return match.group(1) if match else None


async def scrape_businesses(lat: float, lon: float, radius_km: float) -> list[dict]:
    zoom = _zoom_from_radius(radius_km)
    search_url = (
        f"https://www.google.com/maps/search/negócios+locais/"
        f"@{lat},{lon},{zoom}z?hl=pt-BR"
    )

    results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="pt-BR",
            geolocation={"latitude": lat, "longitude": lon},
            permissions=["geolocation"],
        )
        page = await context.new_page()

        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

        # Dismiss cookie consent if present
        try:
            await page.click('button[aria-label="Aceitar tudo"]', timeout=3000)
        except Exception:
            pass

        # Wait for results feed
        try:
            await page.wait_for_selector('div[role="feed"]', timeout=15000)
        except Exception:
            await browser.close()
            return results

        # Scroll feed to load more results
        feed = page.locator('div[role="feed"]')
        prev_count = 0
        for _ in range(15):  # max 15 scroll attempts
            cards = page.locator('div[role="feed"] a.hfpxzc')
            count = await cards.count()
            if count == prev_count and count > 0:
                break
            prev_count = count
            await feed.evaluate("el => el.scrollBy(0, el.scrollHeight)")
            await asyncio.sleep(1.5)

        cards = page.locator('div[role="feed"] a.hfpxzc')
        total = await cards.count()

        for i in range(total):
            card = cards.nth(i)
            try:
                await card.click(timeout=5000)
                await asyncio.sleep(1.5)

                current_url = page.url
                place_id = _extract_place_id(current_url)

                name = await _safe_inner_text(page, "h1.DUwDvf")
                if not name:
                    name = await card.get_attribute("aria-label") or ""

                category = await _safe_inner_text(page, "button.DkEaL")
                rating_text = await _safe_inner_text(page, "div.F7nice > span[aria-hidden='true']")
                reviews_text = await _safe_attr(page, "div.F7nice > span[aria-label$='reviews']", "aria-label")
                if not reviews_text:
                    reviews_text = await _safe_attr(page, "div.F7nice > span[aria-label$='avaliações']", "aria-label")

                address = await _safe_attr(page, "button[data-item-id='address']", "aria-label")
                phone_raw = await _safe_attr(page, "button[data-item-id^='phone']", "aria-label")
                website = await _safe_attr(page, "a[data-item-id='authority']", "href")

                rating = None
                try:
                    rating = float(rating_text.replace(",", ".")) if rating_text else None
                except ValueError:
                    pass

                review_count = None
                if reviews_text:
                    nums = re.findall(r"[\d.]+", reviews_text.replace(".", "").replace(",", ""))
                    if nums:
                        try:
                            review_count = int(nums[0])
                        except ValueError:
                            pass

                phone = phone_raw.replace("Telefone: ", "").strip() if phone_raw else None
                if address:
                    address = address.replace("Endereço: ", "").strip()

                if not name:
                    continue

                results.append({
                    "place_id": place_id or f"{name}_{address}",
                    "name": name,
                    "category": category,
                    "address": address,
                    "phone": phone,
                    "rating": rating,
                    "review_count": review_count,
                    "website": website,
                    "lat": lat,
                    "lon": lon,
                })
            except Exception:
                continue

        await browser.close()

    return results


async def _safe_inner_text(page, selector: str) -> str | None:
    try:
        el = page.locator(selector).first
        await el.wait_for(timeout=2000)
        return (await el.inner_text()).strip() or None
    except Exception:
        return None


async def _safe_attr(page, selector: str, attr: str) -> str | None:
    try:
        el = page.locator(selector).first
        await el.wait_for(timeout=2000)
        val = await el.get_attribute(attr)
        return val.strip() if val else None
    except Exception:
        return None
