"""HTML parsing helpers for Jailbreak barter data."""

from __future__ import annotations

from bs4 import BeautifulSoup


def clean_numeric_string(val_str: str) -> int:
    """Convert a formatted numeric string like '$1,000' into an integer."""
    cleaned = val_str.replace("$", "").replace(",", "").replace(" ", "")
    if cleaned == "":
        return 0

    return int(cleaned)


def _extract_field(card, label: str) -> str:
    def matches_label(text: str | None) -> bool:
        if text is None:
            return False

        normalized = text.strip()
        if label == "Value":
            return "Value" in normalized and "Duped" not in normalized

        return label in normalized

    label_tag = card.find("p", string=matches_label)
    if label_tag is None:
        return ""

    value_tag = label_tag.find_next_sibling("p", class_="font-semibold")
    if value_tag is None:
        return ""

    return value_tag.get_text(strip=True)


def parse_jb_html(html_content: str) -> list[dict]:
    """Parse Jailbreak vehicle cards from HTML into a list of dictionaries."""
    soup = BeautifulSoup(html_content, "html.parser")
    vehicles = []
    allowed_categories = {
        "Vehicle",
        "Spoiler",
        "Texture",
        "Color",
        "Rim",
        "Drift",
        "Horn",
        "Tire Style",
        "Tire Sticker",
        "Furniture",
        "Weapon Skin",
    }

    for card in soup.find_all("div", attrs={"data-slot": "card"}):
        category_span = card.find("span", class_="text-sm")
        category = category_span.get_text(strip=True) if category_span else ""
        if category not in allowed_categories:
            continue

        name_tag = card.find("h4")
        name = name_tag.get_text(strip=True) if name_tag else ""

        metrics = {
            "Value": 0,
            "Duped Value": 0,
            "Rarity": "",
            "Demand": "",
        }

        rows = card.find_all(
            "div",
            attrs={"class": "flex flex-row justify-between"},
        )
        for row in rows:
            ps = row.find_all("p")
            if len(ps) != 2:
                continue

            label = ps[0].get_text(strip=True)
            data = ps[1].get_text(strip=True)

            if "Duped" in label:
                metrics["Duped Value"] = clean_numeric_string(data)
            elif "Value" in label:
                metrics["Value"] = clean_numeric_string(data)
            elif "Rarity" in label:
                metrics["Rarity"] = data
            elif "Demand" in label:
                metrics["Demand"] = data

        if metrics["Value"] < 1000000:
            continue

        if metrics["Duped Value"] == 0:
            metrics["Duped Value"] = metrics["Value"]

        vehicles.append(
            {
                "name": name,
                "category": category,
                "base_value": metrics["Value"],
                "duped_value": metrics["Duped Value"],
                "rarity": metrics["Rarity"],
                "demand": metrics["Demand"],
            }
        )

    return vehicles
