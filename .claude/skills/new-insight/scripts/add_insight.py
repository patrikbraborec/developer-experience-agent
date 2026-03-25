#!/usr/bin/env python3
"""Add a new insight to the DX Framework Notion database."""

import argparse
import json
import os
import sys
from datetime import date

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


def find_category_page(database_id, category_name, headers):
    """Query the Notion database to find the page matching the category name."""
    url = f"{NOTION_API_URL}/databases/{database_id}/query"
    payload = {
        "filter": {
            "property": "Category",
            "title": {
                "equals": category_name,
            },
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        print(f"Error: Category '{category_name}' not found in the database.", file=sys.stderr)
        sys.exit(1)
    return results[0]["id"]


def find_insights_heading_and_last_block(page_id, headers):
    """Find the 'Insights' heading and the last block in the Insights section.

    Returns (heading_id, last_block_id) where last_block_id is the ID of the
    last block before the next heading (or the end of the page). If there are
    no blocks after the heading, last_block_id equals heading_id.
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

    heading_id = None
    last_block_id = None
    for block in all_blocks:
        block_type = block.get("type", "")
        if heading_id is None:
            # Still looking for the Insights heading
            if block_type in ("heading_1", "heading_2", "heading_3"):
                rich_text = block[block_type].get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_text)
                if text.strip().lower() == "insights":
                    heading_id = block["id"]
                    last_block_id = block["id"]
        else:
            # We're past the Insights heading — stop at the next heading
            if block_type in ("heading_1", "heading_2", "heading_3"):
                break
            last_block_id = block["id"]

    return heading_id, last_block_id


def _today_mention():
    """Return a Notion rich_text mention element for @Today."""
    return {
        "type": "mention",
        "mention": {
            "type": "date",
            "date": {"start": date.today().isoformat()},
        },
    }


def make_bullet_block(text):
    """Create a bulleted list item block with plain text."""
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text},
                },
            ]
        },
    }


def make_parent_bullet_block(description, segments):
    """Create a parent bullet with @Today + description and nested sub-bullet children."""
    children = [make_bullet_block(seg) for seg in segments]
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                _today_mention(),
                {
                    "type": "text",
                    "text": {"content": f" {description}"},
                },
            ],
            "children": children,
        },
    }


def make_simple_bullet_block(insight_text):
    """Create a simple bullet with @Today + insight text (no children)."""
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                _today_mention(),
                {
                    "type": "text",
                    "text": {"content": f" {insight_text}"},
                },
            ]
        },
    }


def append_block_after(page_id, after_block_id, block, headers):
    """Append a block to the page, positioned after the given block."""
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    payload = {"children": [block], "after": after_block_id}
    resp = requests.patch(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def append_block_to_page_with_heading(page_id, block, headers):
    """Create the Insights heading and append the block to the page."""
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    payload = {
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Insights"}}]
                },
            },
            block,
        ]
    }
    resp = requests.patch(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Add insight to DX Framework Notion database")
    parser.add_argument("--category", required=True, help="DX Framework category name")
    parser.add_argument("--insight", required=True, help="Insight text (or parent description when using --segments)")
    parser.add_argument("--segments", nargs="+", help="Individual insight segments as sub-bullets under the parent")
    args = parser.parse_args()

    headers = get_headers()
    database_id = get_database_id()

    print(f"Looking for category: {args.category}")
    page_id = find_category_page(database_id, args.category, headers)
    print(f"Found page: {page_id}")

    if args.segments:
        block = make_parent_bullet_block(args.insight, args.segments)
        print(f"Creating parent bullet with {len(args.segments)} sub-bullet(s)")
    else:
        block = make_simple_bullet_block(args.insight)

    heading_id, last_block_id = find_insights_heading_and_last_block(page_id, headers)
    if heading_id:
        print(f"Found 'Insights' heading: {heading_id}")
        print(f"Appending after last block: {last_block_id}")
        append_block_after(page_id, last_block_id, block, headers)
    else:
        print("No 'Insights' heading found — creating one and appending insight.")
        append_block_to_page_with_heading(page_id, block, headers)

    print(f"Successfully added insight to '{args.category}': @Today {args.insight}")
    if args.segments:
        for i, seg in enumerate(args.segments, 1):
            print(f"  Segment {i}: {seg}")


if __name__ == "__main__":
    main()
