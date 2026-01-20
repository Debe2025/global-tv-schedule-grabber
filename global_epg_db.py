#!/usr/bin/env python3
"""
Global EPG Downloader - Multi-source, smarter name matching (Jan 2026)
Downloads per-country EPG → saves in ./epg_db/{NormalizedCountry}/guide.xml(.gz optional)

Usage:
  python global_epg_db.py --all
  python global_epg_db.py --countries "United States" Canada France "United Kingdom"
"""

import argparse
import json
import os
import sys
from pathlib import Path
import requests
from datetime import datetime
from urllib.parse import quote

# ────────────────────────────────────────────────
# SOURCES - ordered by reliability / freshness 2026
# ────────────────────────────────────────────────
SOURCES = [
    {
        "name": "globetvapp",
        "base_raw": "https://raw.githubusercontent.com/globetvapp/epg/main",
        "folder_style": "TitleNoSpace",  # UnitedStates, Canada, France...
        "file_patterns": [
            "{slug_lower}1.xml",
            "{slug_lower}2.xml", "{slug_lower}3.xml", "{slug_lower}4.xml",
            "guide.xml", "epg.xml", "{slug}.xml", "{country_lower}.xml"
        ]
    },
    # Add more sources later, e.g.:
    # {
    #     "name": "catchuptv",
    #     "base_raw": "https://raw.githubusercontent.com/Catch-up-TV-and-More/xmltv/master",
    #     "folder_style": "lowercase",
    #     "file_patterns": ["{slug_lower}_local.xml", "{slug_lower}.xml"]
    # },
]

# ────────────────────────────────────────────────
# Country list (expand as needed - from globetvapp + common others)
# Use display names here; script normalizes
# ────────────────────────────────────────────────
AVAILABLE_COUNTRIES = [
    "Australia", "Canada", "France", "Germany", "United Kingdom", "United States",
    "India", "Italy", "Spain", "Brazil", "Mexico", "Netherlands", "Poland",
    "Sweden", "Norway", "Denmark", "Switzerland", "Belgium", "Austria",
    "Portugal", "Turkey", "Argentina", "Chile", "Uruguay",
    "Albania", "Greece", "Ireland", "New Zealand", "South Africa",
    # Add more from https://github.com/globetvapp/epg/tree/main
]

def normalize_country_name(name: str) -> tuple[str, str]:
    """Return (display, folder_slug)"""
    name = name.strip()
    slug = name.replace(" ", "").replace(".", "")
    lower = slug.lower()
    return name, slug, lower

def try_download(url: str, timeout=12) -> bytes | None:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "EPG-Downloader/1.0"})
        if r.status_code == 200 and len(r.content) > 50_000:  # rough min size filter
            return r.content
        return None
    except Exception:
        return None

def download_for_country(country_display: str, output_dir: Path) -> bool:
    display, slug, lower = normalize_country_name(country_display)
    country_dir = output_dir / slug
    country_dir.mkdir(parents=True, exist_ok=True)
    target = country_dir / "guide.xml"

    print(f"\n=== {display} ({slug}) ===")

    for src in SOURCES:
        base = src["base_raw"]
        style = src["folder_style"]
        patterns = src["file_patterns"]

        folder = slug
        if style == "lowercase":
            folder = lower
        elif style == "TitleNoSpace":
            folder = slug

        for pat in patterns:
            filename = pat.format(
                slug=slug, slug_lower=lower, country_lower=lower, country=display
            )
            url = f"{base}/{quote(folder)}/{quote(filename)}"
            print(f"  Trying {src['name']} → {filename} ... ", end="")

            data = try_download(url)
            if data:
                with open(target, "wb") as f:
                    f.write(data)
                print("✓ saved")
                # Optional: gzip here if you want .gz instead
                return True
            else:
                print("✗")

    print("→ No usable file found across sources.")
    return False

def build_index(output_dir: Path):
    index = {}
    for subdir in output_dir.iterdir():
        if not subdir.is_dir():
            continue
        epg_file = subdir / "guide.xml"
        if not epg_file.exists():
            continue

        size_mb = round(epg_file.stat().st_size / (1024 ** 2), 2)
        index[subdir.name] = {
            "country": subdir.name,
            "file": f"{subdir.name}/guide.xml",
            "size_mb": size_mb,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "source": "multi-source (globetvapp primary)",
            # Later: add channel/program count by parsing XML (needs lxml)
        }

    with open(output_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print(f"\nIndex updated: {output_dir}/index.json ({len(index)} countries)")

def main():
    parser = argparse.ArgumentParser(description="Multi-source Global EPG Downloader")
    parser.add_argument('--countries', nargs='+', help="Country names")
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--output', default="./epg_db", help="Output folder")

    args = parser.parse_args()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(exist_ok=True)

    countries = AVAILABLE_COUNTRIES if args.all else args.countries or []
    if not countries:
        parser.print_help()
        sys.exit(1)

    success = 0
    for c in countries:
        if download_for_country(c, out_dir):
            success += 1

    build_index(out_dir)
    print(f"\nFinished — {success}/{len(countries)} countries saved.")

if __name__ == "__main__":
    main()
