"""
E-commerce Price Tracker
------------------------
Scrapes product data (name, price, rating, stock) from an online store,
saves a dated snapshot, and maintains a price history across runs so
price changes can be detected.

Demo target: https://books.toscrape.com  (a public site built for scraping practice)

Usage:
    python tracker.py                 # scrape first 3 pages (default)
    python tracker.py --pages 10      # scrape 10 pages
    python tracker.py --pages 0       # scrape ALL pages
    python tracker.py --out-dir data  # custom output folder

Author: <your name> | github.com/<your-username>
"""

import argparse
import csv
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")

# A clear User-Agent is polite and professional.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PortfolioPriceTracker/1.0; +https://github.com/your-username)"
}

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
REQUEST_DELAY = 1.0  # seconds between requests -> respectful scraping


def get_soup(url: str) -> BeautifulSoup:
    """Fetch a URL and return a parsed BeautifulSoup object."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def clean_price(raw: str) -> float:
    """'£51.77' -> 51.77 (handles stray encoding characters too)."""
    digits = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
    return float(digits) if digits else 0.0


def parse_page(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """Extract all products from one listing page."""
    products = []
    for card in soup.select("article.product_pod"):
        title = card.h3.a.get("title", "").strip()

        price_el = card.select_one("p.price_color")
        price = clean_price(price_el.get_text()) if price_el else 0.0

        rating_el = card.select_one("p.star-rating")
        rating = 0
        if rating_el:
            for cls in rating_el.get("class", []):
                if cls in RATING_MAP:
                    rating = RATING_MAP[cls]
                    break

        stock_el = card.select_one("p.instock.availability")
        in_stock = "In stock" if (stock_el and "In stock" in stock_el.get_text()) else "Out of stock"

        link_el = card.h3.a
        product_url = urljoin(page_url, link_el.get("href", "")) if link_el else ""

        products.append(
            {
                "title": title,
                "price": price,
                "rating": rating,
                "stock": in_stock,
                "url": product_url,
            }
        )
    return products


def scrape(max_pages: int) -> list[dict]:
    """Scrape listing pages, following the 'next' link. max_pages=0 means all."""
    all_products: list[dict] = []
    url = START_URL
    page_num = 1

    while url:
        print(f"[{page_num}] Scraping {url} ...")
        try:
            soup = get_soup(url)
        except requests.RequestException as exc:
            print(f"    ! Request failed: {exc} — stopping here.")
            break

        page_products = parse_page(soup, url)
        all_products.extend(page_products)
        print(f"    -> {len(page_products)} products (total: {len(all_products)})")

        if max_pages and page_num >= max_pages:
            break

        next_link = soup.select_one("li.next a")
        url = urljoin(url, next_link["href"]) if next_link else None
        page_num += 1
        time.sleep(REQUEST_DELAY)

    return all_products


def save_latest(products: list[dict], out_dir: Path) -> Path:
    """Save the freshest snapshot to products_latest.csv."""
    path = out_dir / "products_latest.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "price", "rating", "stock", "url"])
        writer.writeheader()
        writer.writerows(products)
    return path


def append_history(products: list[dict], out_dir: Path) -> Path:
    """Append today's prices to price_history.csv (one row per product per day)."""
    path = out_dir / "price_history.csv"
    today = date.today().isoformat()
    new_file = not path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "title", "price", "stock"])
        if new_file:
            writer.writeheader()
        for p in products:
            writer.writerow(
                {"date": today, "title": p["title"], "price": p["price"], "stock": p["stock"]}
            )
    return path


def detect_changes(history_path: Path) -> list[dict]:
    """Compare the two most recent dates in the history and report price changes."""
    if not history_path.exists():
        return []

    with history_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    dates = sorted({r["date"] for r in rows})
    if len(dates) < 2:
        return []

    prev_date, last_date = dates[-2], dates[-1]
    prev = {r["title"]: float(r["price"]) for r in rows if r["date"] == prev_date}
    last = {r["title"]: float(r["price"]) for r in rows if r["date"] == last_date}

    changes = []
    for title, new_price in last.items():
        old_price = prev.get(title)
        if old_price is not None and old_price != new_price:
            diff = round(new_price - old_price, 2)
            pct = round((diff / old_price) * 100, 1) if old_price else 0
            changes.append(
                {
                    "title": title,
                    "old_price": old_price,
                    "new_price": new_price,
                    "change": diff,
                    "change_pct": pct,
                }
            )
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="E-commerce price tracker")
    parser.add_argument("--pages", type=int, default=3, help="pages to scrape (0 = all)")
    parser.add_argument("--out-dir", default="data", help="output folder")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    products = scrape(args.pages)
    if not products:
        print("No products scraped — check your connection or the target site.")
        return 1

    latest_path = save_latest(products, out_dir)
    history_path = append_history(products, out_dir)

    changes = detect_changes(history_path)
    print("\n===== SUMMARY =====")
    print(f"Products scraped : {len(products)}")
    print(f"Latest snapshot  : {latest_path}")
    print(f"Price history    : {history_path}")
    if changes:
        print(f"Price changes since last run: {len(changes)}")
        for c in changes[:10]:
            print(f"  {c['title'][:40]:40} {c['old_price']:>8.2f} -> {c['new_price']:>8.2f} ({c['change_pct']:+.1f}%)")
    else:
        print("Price changes since last run: none (or first run)")
    print("\nNext step: python report.py --data-dir", args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
