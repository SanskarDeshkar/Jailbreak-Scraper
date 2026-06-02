"""Analysis helpers for Jailbreak market data."""

from __future__ import annotations

import json
import math
import random

import networkx as nx


def load_data() -> list[dict]:
    """Load parsed market data from disk."""
    with open("market_data.json", "r", encoding="utf-8") as data_file:
        return json.load(data_file)


def build_market_graph(vehicles: list[dict]) -> nx.DiGraph:
    """Build a directed exchange-rate graph from parsed vehicle data."""
    expanded_market = []
    for vehicle in vehicles:
        expanded_market.append(
            {
                "name": f"{vehicle['name']} (Clean)",
                "value": vehicle["base_value"],
                "demand": vehicle["demand"],
                "rarity": vehicle["rarity"],
            }
        )

        if vehicle["duped_value"] < vehicle["base_value"]:
            expanded_market.append(
                {
                    "name": f"{vehicle['name']} (Duped)",
                    "value": vehicle["duped_value"],
                    "demand": vehicle["demand"],
                    "rarity": vehicle["rarity"],
                }
            )

    demand_tiers = {
        "Excellent": 8,
        "High": 7,
        "Above average": 6,
        "Average": 5,
        "Below average": 4,
        "Low": 3,
        "Very low": 2,
        "Minimal": 1,
    }
    rarity_tiers = {"Very Common": 1, "Common": 2, "Uncommon": 3, "Rare": 4, "Very Rare": 5}

    G = nx.DiGraph()

    for vehicle in expanded_market:
        G.add_node(vehicle["name"])

    for u in expanded_market:
        for v in expanded_market:
            if u["name"] == v["name"]:
                continue

            v_value = v["value"]
            if v_value == 0:
                continue

            u_tier = demand_tiers.get(u.get("demand", ""), 5)
            v_tier = demand_tiers.get(v.get("demand", ""), 5)
            tier_diff = u_tier - v_tier
            if tier_diff > 0:
                demand_friction = 1.0 + (tier_diff * 0.05)
            elif tier_diff < 0:
                demand_friction = 1.0 + (tier_diff * 0.05)
            else:
                demand_friction = 1.0

            u_rarity = rarity_tiers.get(u.get("rarity", ""), 2)
            v_rarity = rarity_tiers.get(v.get("rarity", ""), 2)
            rarity_diff = u_rarity - v_rarity
            if rarity_diff > 0:
                rarity_friction = 1.0 + (rarity_diff * 0.05)
            elif rarity_diff < 0:
                rarity_friction = 1.0 + (rarity_diff * 0.05)
            else:
                rarity_friction = 1.0

            total_friction = demand_friction * rarity_friction
            rate = (u["value"] / v_value) * total_friction

            if rate > 7.0:
                continue

            if rate < 0.125:
                continue

            if rate <= 0:
                continue

            weight = -math.log(rate)
            G.add_edge(u["name"], v["name"], weight=weight, rate=rate)

    return G


def _base_item_name(graph_node_name: str) -> str:
    if graph_node_name.endswith(" (Clean)"):
        return graph_node_name.removesuffix(" (Clean)")
    if graph_node_name.endswith(" (Duped)"):
        return graph_node_name.removesuffix(" (Duped)")

    return graph_node_name


def find_trade_adds(rate: float, target_name: str, market_data: list[dict] | None = None) -> list[dict]:
    """Suggest random high-demand adds for decimal trades."""
    if rate <= 0 or rate.is_integer():
        return []

    vehicles = market_data if market_data is not None else load_data()
    target_base_name = _base_item_name(target_name)
    target_item = next((item for item in vehicles if item["name"] == target_base_name), None)
    if target_item is None:
        return []

    decimal_rate = rate % 1
    add_value = round(decimal_rate * target_item["base_value"])
    high_demand_values = {"Excellent", "High", "Above average"}
    candidates = []

    for item in vehicles:
        if item["name"] == target_base_name:
            continue
        if item.get("demand") not in high_demand_values:
            continue

        item_value = item.get("base_value", 0)
        if item_value <= 0 or add_value % item_value != 0:
            continue

        quantity = add_value // item_value
        weight = 5 if item.get("category") == "Vehicle" else 1
        candidates.extend(
            [
                {
                    "name": item["name"],
                    "category": item.get("category", ""),
                    "quantity": quantity,
                    "total_value": add_value,
                }
            ]
            * weight
        )

    if not candidates:
        return []

    return [random.choice(candidates)]


def find_arbitrage_loops(G: nx.DiGraph) -> None:
    """Find and print all profitable negative-weight arbitrage cycles."""
    G_copy = G.copy()
    found_any = False
    market_data = load_data()
    category_by_name = {item["name"]: item.get("category", "") for item in market_data}
    loop_count = 0

    while True:
        try:
            cycle = nx.find_negative_cycle(G_copy, source=list(G_copy.nodes)[0])
            if len(cycle) <= 3:
                G_copy.remove_edge(cycle[0], cycle[1])
                continue

            profit = 1.0
            for index in range(len(cycle) - 1):
                u = cycle[index]
                v = cycle[index + 1]
                rate = G_copy[u][v]["rate"]
                profit *= rate

            if profit > 1.025:  # Only consider cycles with >2.5% profit margin
                loop_count += 1
                print("\nARBITRAGE LOOP FOUND")
                for index in range(len(cycle) - 1):
                    u = cycle[index]
                    v = cycle[index + 1]
                    rate = G_copy[u][v]["rate"]

                    # Scale the trade up if rate is less than 1
                    multiplier = math.ceil(1.0 / rate) if rate < 1.0 else 1
                    scaled_rate = rate * multiplier
                    u_category = category_by_name.get(_base_item_name(u), "Unknown")
                    v_category = category_by_name.get(_base_item_name(v), "Unknown")

                    print(
                        f"  • Trade {multiplier} {u} [{u_category}] "
                        f"➔ Receive {scaled_rate:.2f} {v} [{v_category}]"
                    )
                    for add in find_trade_adds(scaled_rate, v, market_data):
                        print(
                            f"    Adds: {add['quantity']} {add['name']} "
                            f"({add['category']}, ${add['total_value']:,})"
                        )

                print(f"Total Arbitrage Profit: {((profit - 1.0) * 100):.1f}% margin")
                found_any = True
                if loop_count >= 15:
                    break

            G_copy.remove_edge(cycle[0], cycle[1])
        except nx.NetworkXError:
            break

    if not found_any:
        print("No trades found above the 2.5% profit threshold.")


if __name__ == "__main__":
    vehicles = load_data()
    graph = build_market_graph(vehicles)
    find_arbitrage_loops(graph)
