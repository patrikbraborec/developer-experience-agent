#!/usr/bin/env python3
"""Fetch recent insights from all DX Framework categories in Notion."""

import argparse
import json
import os
import sys
from datetime import date, timedelta

import requests

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def get_headers():
    token = os.environ.get("NOTION_API_TOKEN")
    if not token:
        print("Error: NOTION_API_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def get_database_id():
    db_id = os.environ.get("NOTION_DATABASE_ID")
    if not db_id:
        print("Error: NOTION_DATABASE_ID environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return db_id


def fetch_all_pages(database_id, headers):
    """Fetch all pages from the database with their properties."""
    url = f"{NOTION_API_URL}/databases/{database_id}/query"
    pages = []
    payload = {"page_size": 100}
    while True:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return pages


def get_page_title(page):
    """Extract the title (Category name) from a page."""
    props = page.get("properties", {})
    title_prop = props.get("Category", {})
    title_items = title_prop.get("title", [])
    return "".join(item.get("plain_text", "") for item in title_items)


def get_page_properties(page):
    """Extract relevant properties from a page (e.g., Score, Status)."""
    props = page.get("properties", {})
    result = {}
    for prop_name, prop_data in props.items():
        prop_type = prop_data.get("type")
        if prop_type == "select" and prop_data.get("select"):
            result[prop_name] = prop_data["select"]["name"]
        elif prop_type == "status" and prop_data.get("status"):
            result[prop_name] = prop_data["status"]["name"]
        elif prop_type == "number" and prop_data.get("number") is not None:
            result[prop_name] = prop_data["number"]
        elif prop_type == "rich_text":
            text = "".join(rt.get("plain_text", "") for rt in prop_data.get("rich_text", []))
            if text:
                result[prop_name] = text
    return result


def extract_date_from_rich_text(rich_text_items):
    """Extract date from rich_text that contains a date mention."""
    for item in rich_text_items:
        if item.get("type") == "mention" and item.get("mention", {}).get("type") == "date":
            date_info = item["mention"]["date"]
            return date_info.get("start")
    return None


def extract_text_from_rich_text(rich_text_items):
    """Extract plain text from rich_text items."""
    return "".join(item.get("plain_text", "") for item in rich_text_items)


def fetch_insights_from_page(page_id, headers, cutoff_date):
    """Fetch insights from a page that are newer than cutoff_date.

    Returns a list of insight dicts with 'date' and 'text' keys.
    """
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    params = {"page_size": 100}
    all_blocks = []
    while True:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        all_blocks.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        params["start_cursor"] = data["next_cursor"]

    # Find the Insights section
    in_insights = False
    insights = []
    for block in all_blocks:
        block_type = block.get("type", "")
        if not in_insights:
            if block_type in ("heading_1", "heading_2", "heading_3"):
                rich_text = block[block_type].get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_text)
                if text.strip().lower() == "insights":
                    in_insights = True
            continue

        # Stop at next heading
        if block_type in ("heading_1", "heading_2", "heading_3"):
            break

        if block_type == "bulleted_list_item":
            rich_text = block["bulleted_list_item"].get("rich_text", [])
            insight_date = extract_date_from_rich_text(rich_text)
            insight_text = extract_text_from_rich_text(rich_text)

            if insight_date and insight_date >= cutoff_date:
                # Fetch children (sub-bullets) if they exist
                children_text = []
                if block.get("has_children"):
                    children_url = f"{NOTION_API_URL}/blocks/{block['id']}/children"
                    child_resp = requests.get(children_url, headers=headers)
                    child_resp.raise_for_status()
                    for child in child_resp.json().get("results", []):
                        if child.get("type") == "bulleted_list_item":
                            child_rt = child["bulleted_list_item"].get("rich_text", [])
                            children_text.append(extract_text_from_rich_text(child_rt))

                insights.append({
                    "date": insight_date,
                    "text": insight_text.strip(),
                    "segments": children_text,
                })

    return insights


def fetch_latest_signal(page_id, headers):
    """Fetch the current 'Latest signal' section content if it exists."""
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    params = {"page_size": 100}
    all_blocks = []
    while True:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        all_blocks.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        params["start_cursor"] = data["next_cursor"]

    in_signal = False
    signal_lines = []
    for block in all_blocks:
        block_type = block.get("type", "")
        if not in_signal:
            if block_type in ("heading_1", "heading_2", "heading_3"):
                rich_text = block[block_type].get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_text)
                if text.strip().lower() == "latest signal":
                    in_signal = True
            continue

        if block_type in ("heading_1", "heading_2", "heading_3"):
            break

        if block_type == "paragraph":
            rich_text = block["paragraph"].get("rich_text", [])
            signal_lines.append(extract_text_from_rich_text(rich_text))

    return "\n".join(signal_lines).strip() if signal_lines else None


def main():
    parser = argparse.ArgumentParser(description="Fetch recent insights from DX Framework Notion database")
    parser.add_argument("--days", type=int, default=14, help="Number of days to look back (default: 14)")
    args = parser.parse_args()

    headers = get_headers()
    database_id = get_database_id()

    cutoff_date = (date.today() - timedelta(days=args.days)).isoformat()
    print(f"Fetching insights from the last {args.days} days (since {cutoff_date})...", file=sys.stderr)

    pages = fetch_all_pages(database_id, headers)
    print(f"Found {len(pages)} categories", file=sys.stderr)

    results = []
    for page in pages:
        category = get_page_title(page)
        if not category:
            continue

        properties = get_page_properties(page)
        insights = fetch_insights_from_page(page["id"], headers, cutoff_date)
        latest_signal = fetch_latest_signal(page["id"], headers)

        results.append({
            "category": category,
            "page_id": page["id"],
            "properties": properties,
            "latest_signal": latest_signal,
            "recent_insights": insights,
            "recent_insights_count": len(insights),
        })

    # Sort: categories with insights first, then alphabetically
    results.sort(key=lambda x: (-x["recent_insights_count"], x["category"]))

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
