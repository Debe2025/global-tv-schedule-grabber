#!/usr/bin/env python3
"""
Global EPG Downloader - Builds country-grouped database from globetvapp/epg (January 2026)
Saves files in ./epg_db/{COUNTRY}/guide.xml

Usage:
  python global_epg_db.py --all                  # Download everything
  python global_epg_db.py --countries US CA GB FR DE  # Only specific countries
"""

import argparse
import json
import os
import sys
from pathlib import Path
import requests

# Base raw GitHub URL
BASE_RAW = "https://raw.githubusercontent.com/globetvapp/epg/main"

# List of countries (from current repo - add more as needed)
AVAILABLE_COUNTRIES = [
    "Australia", "Canada", "France", "Germany", "United Kingdom", "United States",
    "India", "Italy", "Spain", "Brazil", "Mexico", "Netherlands", "Poland",
    "Sweden", "Norway", "Denmark", "Switzerland", "Belgium", "Austria",
    "Portugal", "Turkey", "Argentina", "Chile", "Uruguay"  # and many more in repo
]

def download_country_epg(country: str, output_dir: Path):
    country_slug = country.replace(" ", "")  # e.g. "United States" → "UnitedStates"
    country_dir = output_dir / country_slug
    country_dir.mkdir(parents=True, exist_ok=True)
    target = country_dir / "guide.xml"

    # Most countries have one main file like australia1.xml, france1.xml, etc.
    # Fallback to first numbered file if multiple exist
    possible_files = [f"{country_slug.lower()}1.xml", f"{country_slug.lower()}2.xml"]
    for filename in possible_files:
        url = f"{BASE_RAW}/{country_slug}/{filename}"
        print(f"Trying {country} → {filename} ... ", end="")
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with open(target, 'wb') as f:
                    f.write(r.content)
                print("saved!")
                return True
            else:
                print("not found")
        except Exception as e:
            print(f"error: {e}")
    print(f"No EPG file found for {country}. Check repo for exact name.")
    return False

def build_index(output_dir: Path):
    index = {}
    for country_dir in output_dir.iterdir():
        if country_dir.is_dir():
            epg_file = country_dir / "guide.xml"
            if epg_file.exists():
                size_mb = round(epg_file.stat().st_size / (1024 * 1024), 1)
                index[country_dir.name] = {
                    "country": country_dir.name,
                    "file": f"{country_dir.name}/guide.xml",
                    "size_mb": size_mb,
                    "last_updated": "Daily (from globetvapp/epg)"
                }
    with open(output_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print("\nIndex created: epg_db/index.json")

def main():
    parser = argparse.ArgumentParser(description="Build Global EPG Database by Country")
    parser.add_argument('--countries', nargs='+', help="Country names e.g. Canada UnitedStates France")
    parser.add_argument('--all', action='store_true', help="Download all available countries")
    parser.add_argument('--output', default="./epg_db", help="Output folder")

    args = parser.parse_args()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(exist_ok=True)

    if args.all:
        countries = AVAILABLE_COUNTRIES
        print(f"Downloading {len(countries)} countries...")
    elif args.countries:
        countries = args.countries
    else:
        parser.print_help()
        sys.exit(1)

    success_count = 0
    for country in countries:
        print(f"\n=== {country} ===")
        if download_country_epg(country, out_dir):
            success_count += 1

    build_index(out_dir)
    print(f"\nDone! {success_count} countries saved in: {out_dir}")
    print("Next: Push to GitHub. Add GitHub Actions for daily auto-update if you want.")

if __name__ == "__main__":
    main()
