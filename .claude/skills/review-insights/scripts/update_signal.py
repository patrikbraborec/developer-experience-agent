#!/usr/bin/env python3
"""Update the 'Latest signal' section on a DX Framework category page in Notion."""

import argparse
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
            "title": {"equals": category_name},
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        print(f"Error: Category '{category_name}' not found in the database.", file=sys.stderr)
        sys.exit(1)
    return results[0]["id"]


def find_latest_signal_section(page_id, headers):
    """Find the 'Latest signal' heading and all blocks in that section.

    Returns (heading_id, block_ids_to_delete, last_block_before_next_heading).
    If the section doesn't exist, returns (None, [], None).
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
    section_block_ids = []
    in_section = False

    for block in all_blocks:
        block_type = block.get("type", "")
        if not in_section:
            if block_type in ("heading_1", "heading_2", "heading_3"):
                rich_text = block[block_type].get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_text)
                if text.strip().lower() == "latest signal":
                    heading_id = block["id"]
                    in_section = True
            continue

        if block_type in ("heading_1", "heading_2", "heading_3"):
            break

        section_block_ids.append(block["id"])

    return heading_id, section_block_ids


def find_first_heading(page_id, headers):
    """Find the first heading block on the page to insert before it."""
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

    for block in all_blocks:
        block_type = block.get("type", "")
        if block_type in ("heading_1", "heading_2", "heading_3"):
            return block["id"]
    return None


def delete_block(block_id, headers):
    """Delete a block by ID."""
    url = f"{NOTION_API_URL}/blocks/{block_id}"
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()


def make_paragraph_block(text):
    """Create a paragraph block with text."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": text}},
            ]
        },
    }


def make_empty_paragraph():
    """Create an empty paragraph block (spacer)."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": []},
    }


def make_heading_block(text):
    """Create a heading_2 block."""
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def append_blocks_after(page_id, after_block_id, blocks, headers):
    """Append blocks to the page after the given block."""
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    payload = {"children": blocks, "after": after_block_id}
    resp = requests.patch(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def append_blocks_to_page(page_id, blocks, headers):
    """Append blocks to the end of the page."""
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    payload = {"children": blocks}
    resp = requests.patch(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Update 'Latest signal' on a DX Framework category page")
    parser.add_argument("--category", required=True, help="DX Framework category name")
    parser.add_argument("--summary", required=True, help="Summary line (e.g., 'During Q1/2026, we improved...')")
    parser.add_argument("--change", required=True, help="Change description (e.g., 'From \"Requires attention\" to \"Meets expectations\"')")
    parser.add_argument("--signal-date", required=True, help="Date string (e.g., 'Last Thursday', 'March 20, 2026')")
    args = parser.parse_args()

    headers = get_headers()
    database_id = get_database_id()

    # Find or resolve the page
    print(f"Looking for category: {args.category}")
    page_id = find_category_page(database_id, args.category, headers)
    print(f"Found page: {page_id}")

    # Check if 'Latest signal' section already exists
    heading_id, section_block_ids = find_latest_signal_section(page_id, headers)

    # Build the new signal content blocks
    signal_blocks = [
        make_paragraph_block(args.summary),
        make_paragraph_block(f"Change: {args.change}"),
        make_paragraph_block(f"Date: {args.signal_date}"),
        make_empty_paragraph(),
    ]

    if heading_id:
        # Delete old content in the section
        print(f"Found existing 'Latest signal' section, replacing content...")
        for block_id in section_block_ids:
            delete_block(block_id, headers)
        # Append new content after the heading
        append_blocks_after(page_id, heading_id, signal_blocks, headers)
    else:
        # Create the section at the top of the page (before other headings)
        print("No 'Latest signal' section found, creating one...")
        first_heading_id = find_first_heading(page_id, headers)
        new_blocks = [make_heading_block("Latest signal")] + signal_blocks
        if first_heading_id:
            # We can't insert "before" in Notion API easily, so append to end
            # and the user can reorder if needed. But let's try to put it at the top
            # by appending to page (Notion appends at the end).
            # For now, append at the end of the page.
            append_blocks_to_page(page_id, new_blocks, headers)
        else:
            append_blocks_to_page(page_id, new_blocks, headers)

    print(f"Successfully updated 'Latest signal' for '{args.category}'")
    print(f"  Summary: {args.summary}")
    print(f"  Change: {args.change}")
    print(f"  Date: {args.signal_date}")


if __name__ == "__main__":
    main()
