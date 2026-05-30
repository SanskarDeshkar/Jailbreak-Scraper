"""Entry point for scraping and parsing Jailbreak vehicle values."""

from __future__ import annotations

import json

from parser import parse_jb_html
from scraper import fetch_url


URL = "https://jbvalues.com/values/"
OUTPUT_FILE = "market_data.json"


def main() -> None:
    html_content = fetch_url(URL)
    if html_content is None:
        print("Failed to fetch page HTML. No vehicle nodes parsed.")
        return

    vehicles = parse_jb_html(html_content)
    vehicles.sort(key=lambda x: x["base_value"], reverse=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as output_file:
        json.dump(vehicles, output_file, indent=2)

    print(f"Successfully filtered and parsed {len(vehicles)} vehicle nodes.")


if __name__ == "__main__":
    main()
