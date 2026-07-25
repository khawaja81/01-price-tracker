# E-commerce Price Tracker & Excel Reporter

A Python tool that scrapes product data from an online store, tracks prices over time, detects price changes between runs, and generates a **formatted, client-ready Excel report**.

> Demo target: [books.toscrape.com](https://books.toscrape.com) — a public site built specifically for scraping practice. The same architecture works for real e-commerce sites (Amazon, Daraz, Shopify stores, etc.) with adjusted selectors.

## What it does

1. **Scrapes** product name, price, rating, stock status and URL across all listing pages
2. **Tracks history** — every run appends a dated snapshot to `price_history.csv`
3. **Detects changes** — compares the last two runs and reports every price increase/drop with %
4. **Generates an Excel report** with three sheets:
   - **Summary** — key stats with live Excel formulas
   - **Products** — formatted table with autofilter and frozen header
   - **Price Changes** — increases in red, drops in green

## Quick start

```bash
pip install -r requirements.txt

python tracker.py --pages 3      # scrape (0 = all pages)
python report.py                 # build data/price_report.xlsx
```

Run `tracker.py` again tomorrow and the report will show what changed.

## Sample output

See [`sample_output/price_report_sample.xlsx`](sample_output/) for what the client receives.

## Tech stack

`requests` · `BeautifulSoup4` · `openpyxl` · CSV-based history (easily swapped for SQLite/PostgreSQL)

## Built with respect for target sites

- Identifies itself with a clear User-Agent
- 1-second delay between requests
- Demo runs only against a site that explicitly permits scraping

## Possible extensions (available on request)

- Email/Telegram alerts when a price drops below a threshold
- Scheduled daily runs (cron / GitHub Actions / Windows Task Scheduler)
- Dashboard with price history charts
- Multi-store comparison
