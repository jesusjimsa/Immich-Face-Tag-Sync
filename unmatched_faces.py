#!/usr/bin/env python3
"""
find_unmatched_faces.py

Finds photos that have a Google Photos person tag (e.g. People/Paul-McCartney)
but are NOT assigned to the matching person in Immich's face recognition.

Usage:
  python find_unmatched_faces.py \
      --tag "People/Paul-McCartney" \
      --person "Paul McCartney" \
      --url "http://your-immich-instance:2283" \
      --key "your_api_key"

  Or run without arguments and the script will prompt for them.
"""

import argparse
import sys
import requests


# ── Helpers ──────────────────────────────────────────────────────────────────

def build_headers(api_key: str) -> dict:
    return {"x-api-key": api_key, "Accept": "application/json"}


def get_all_pages(session: requests.Session, base_url: str, payload: dict) -> list:
    """Paginate through /api/search/metadata and return all asset IDs."""
    assets = []
    page = 1

    while True:
        payload["page"] = page
        resp = session.post(f"{base_url}/api/search/metadata", json=payload)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("assets", {}).get("items", [])
        assets.extend(items)

        # Immich returns nextPage only when there is one
        if not data.get("assets", {}).get("nextPage"):
            break
        page += 1

    return assets


def find_tag_id(session: requests.Session, base_url: str, tag_value: str) -> str | None:
    """Return the Immich tag ID for the given tag value (e.g. 'People/Abuela Angeles')."""
    resp = session.get(f"{base_url}/api/tags")
    resp.raise_for_status()
    tags = resp.json()
    for t in tags:
        if t.get("value", "").strip().lower() == tag_value.strip().lower():
            return t["id"]
    return None


def get_tagged_assets(session: requests.Session, base_url: str, tag: str) -> dict:
    """Return {asset_id: asset} for all assets carrying the given tag value."""
    print(f"  Looking up tag ID for '{tag}' …")
    tag_id = find_tag_id(session, base_url, tag)
    if not tag_id:
        print(f"\n  ✗ Tag '{tag}' not found in Immich.")
        print("    Check the exact tag value under Tags (Immich → Settings → Tags).")
        sys.exit(1)
    print(f"  → Tag ID: {tag_id}")

    print(f"  Fetching assets tagged '{tag}' …")
    payload = {"tagIds": [tag_id], "withExif": False}
    items = get_all_pages(session, base_url, payload)
    result = {item["id"]: item for item in items}
    print(f"  → {len(result)} assets found with that tag")
    return result


def find_person_id(session: requests.Session, base_url: str, person_name: str) -> str | None:
    """Return the Immich person ID for the given display name, or None."""
    resp = session.get(f"{base_url}/api/people")
    resp.raise_for_status()
    people = resp.json().get("people", [])
    for p in people:
        if p.get("name", "").strip().lower() == person_name.strip().lower():
            return p["id"]
    return None


def get_person_asset_ids(session: requests.Session, base_url: str, person_id: str) -> set:
    """Return a set of asset IDs assigned to the given person."""
    print(f"  Fetching assets for person ID {person_id} …")
    payload = {"personIds": [person_id]}
    items = get_all_pages(session, base_url, payload)
    ids = {a["id"] for a in items}
    print(f"  → {len(ids)} assets assigned to that person")
    return ids


def asset_url(base_url: str, asset_id: str) -> str:
    """Direct link to the photo in the Immich web UI."""
    return f"{base_url}/photos/{asset_id}"


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find photos tagged with a person that are missing from Immich face recognition."
    )
    parser.add_argument("--tag",    help="Google Photos tag value, e.g. 'People/Paul-McCartney'")
    parser.add_argument("--person", help="Person name in Immich, e.g. 'Paul McCartney'")
    parser.add_argument("--url",    help="Immich base URL, e.g. 'http://192.168.1.10:2283'")
    parser.add_argument("--key",    help="Immich API key")
    return parser.parse_args()


def prompt_if_missing(args: argparse.Namespace) -> argparse.Namespace:
    import os
    if not args.tag:
        args.tag = input("Person tag (e.g. People/Paul-McCartney): ").strip()
    if not args.person:
        args.person = input("Person name in Immich (e.g. Paul McCartney): ").strip()
    if not args.url:
        if os.path.isfile("url.txt"):
            with open("url.txt") as f:
                args.url = f.read().strip().rstrip("/")
        else:
            args.url = input("Immich base URL (e.g. http://192.168.1.10:2283): ").strip().rstrip("/")
    if not args.key:
        if os.path.isfile("api.txt"):
            with open("api.txt") as f:
                args.key = f.read().strip()
        else:
            import getpass
            args.key = getpass.getpass("Immich API key: ").strip()
    return args


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = prompt_if_missing(parse_args())

    session = requests.Session()
    session.headers.update(build_headers(args.key))

    print(f"\n{'─' * 60}")
    print(f"Tag    : {args.tag}")
    print(f"Person : {args.person}")
    print(f"Server : {args.url}")
    print(f"{'─' * 60}\n")

    # 1. Assets with the tag
    tagged = get_tagged_assets(session, args.url, args.tag)

    if not tagged:
        print("No assets found with that tag. Check the tag value in Immich → Tags.")
        sys.exit(0)

    # 2. Person lookup
    print(f"  Looking up person '{args.person}' …")
    person_id = find_person_id(session, args.url, args.person)
    if not person_id:
        print(f"\n  ✗ Person '{args.person}' not found in Immich.")
        print("    Check the exact name under People, including capitalisation.")
        sys.exit(1)
    print(f"  → Person ID: {person_id}")

    # 3. Assets assigned to that person
    person_ids = get_person_asset_ids(session, args.url, person_id)

    # 4. Difference
    missing_ids = set(tagged.keys()) - person_ids
    print(f"\n{'─' * 60}")
    print(f"Tagged total  : {len(tagged)}")
    print(f"In person     : {len(person_ids & set(tagged.keys()))}")
    print(f"Missing       : {len(missing_ids)}")
    print(f"{'─' * 60}\n")

    if not missing_ids:
        print("✓ All tagged photos are already assigned to this person. Nothing to do!")
        sys.exit(0)

    print("Photos tagged but NOT assigned to the person:\n")
    for asset_id in sorted(missing_ids):
        asset = tagged[asset_id]
        date  = asset.get("fileCreatedAt", "unknown date")[:10]
        name  = asset.get("originalFileName", "")
        url   = asset_url(args.url, asset_id)
        print(f"  {date}  {name:<40}  {url}")

    # Optional: save to file
    print()
    save = input("Save results to a file? (y/N): ").strip().lower()
    if save == "y":
        out_path = f"unmatched_{args.person.replace(' ', '_')}.txt"
        with open(out_path, "w") as f:
            f.write(f"Tag:    {args.tag}\n")
            f.write(f"Person: {args.person}\n")
            f.write(f"Missing {len(missing_ids)} of {len(tagged)} tagged assets\n\n")
            for asset_id in sorted(missing_ids):
                asset = tagged[asset_id]
                date  = asset.get("fileCreatedAt", "unknown date")[:10]
                name  = asset.get("originalFileName", "")
                url   = asset_url(args.url, asset_id)
                f.write(f"{date}  {name:<40}  {url}\n")
        print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
