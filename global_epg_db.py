#!/usr/bin/env python3
"""
Corrected Global EPG Downloader for globetvapp/epg (January 2026 structure)
Uses real capitalized folder names from the repo.

Usage:
  python global_epg_db.py --all
  python global_epg_db.py --countries Australia Canada France Germany "Unitedkingdom" Usa India Italy Spain Brazil
"""

import argparse
import json
from pathlib import Path
import requests
import sys

BASE_RAW = "https://raw.githubusercontent.com/globetvapp/epg/main"

# Mapping: Display name → (actual_folder_name, file_prefix_lowercase)
COUNTRY_MAP = {
    "Australia": ("Australia", "australia"),
    "Canada": ("Canada", "canada"),
    "France": ("France", "france"),
    "Germany": ("Germany", "germany"),
    "United Kingdom": ("Unitedkingdom", "unitedkingdom"),
    "United States": ("Usa", "usa"),
    "India": ("India", "india"),
    "Italy": ("Italy", "italy"),
    "Spain": ("Spain", "spain"),
    "Brazil": ("Brazil", "brazil"),
    # You can add more from the repo list, e.g.:
    # "New Zealand": ("Newzealand", "newzealand"),
    # "Netherlands": ("Netherlands", "netherlands"),
}

def download_country_files(display_name: str, output_dir: Path):
    if display_name not in COUNTRY_MAP:
        print(f"Unknown country '{display_name}'. Add it to COUNTRY_MAP with correct folder/prefix.")
        return False

    folder, prefix = COUNTRY_MAP[display_name]
    # Use sanitized folder name for local storage (replace space if any, but none here)
    local_dir_name = display_name.replace(" ", "_")
    country_dir = output_dir / local_dir_name
    country_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for num in range(1, 6):  # Try up to 5 files
        filename = f"{prefix}{num}.xml"
        url = f"{BASE_RAW}/{folder}/{filename}"
        target = country_dir / filename

        print(f"  Trying {display_name} → {filename} ({url}) ... ", end="")
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with open(target, 'wb') as f:
                    f.write(r.content)
                print("saved")
                downloaded.append(filename)
            else:
                print(f"not found (status {r.status_code})")
                # If first file missing, likely no more
                if num == 1 and not downloaded:
                    break
        except Exception as e:
            print(f"error: {e}")
            break

    if downloaded:
        print(f"  Success: Downloaded {len(downloaded)} file(s) for {display_name}")
        return True
    print(f"  No files found for {display_name} – check if folder exists in repo.")
    return False

def build_index(output_dir: Path):
    index = {}
    for subdir in output_dir.iterdir():
        if subdir.is_dir():
            xml_files = list(subdir.glob("*.xml"))
            if xml_files:
                total_size_mb = sum(f.stat().st_size for f in xml_files) / (1024 ** 2)
                index[subdir.name] = {
                    "display_name": subdir.name.replace("_", " "),
                    "files": [f.name for f in xml_files],
                    "count": len(xml_files),
                    "total_size_mb": round(total_size_mb, 1),
                    "source_repo": "globetvapp/epg",
                    "last_known_update": "Daily ~03:00 UTC"
                }
    with open(output_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print("\nIndex created/updated: epg_db/index.json")

def main():
    parser = argparse.ArgumentParser(description="Global EPG by Country Downloader (Fixed for globetvapp/epg)")
    parser.add_argument('--countries', nargs='+', help='Country display names, e.g. Australia Canada "United Kingdom"')
    parser.add_argument('--all', action='store_true', help='Download all mapped countries')
    parser.add_argument('--output', default="./epg_db", help='Output directory')

    args = parser.parse_args()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(exist_ok=True)

    if args.all:
        countries = list(COUNTRY_MAP.keys())
        print(f"Attempting all {len(countries)} mapped countries...")
    elif args.countries:
        countries = args.countries
    else:
        print("Specify --all or --countries ...")
        sys.exit(1)

    success_count = 0
    for country in countries:
        print(f"\n=== {country} ===")
        if download_country_files(country, out_dir):
            success_count += 1

    build_index(out_dir)
    print(f"\nCompleted: {success_count}/{len(countries)} countries had files downloaded.")
    print("Files saved under epg_db/{Country_Name}/ (e.g. epg_db/Unitedkingdom/unitedkingdom*.xml)")
    print("Tip: Many countries split channels across 1–4 files → use all in your IPTV app.")
    print("Repo: https://github.com/globetvapp/epg – files update daily.")

if __name__ == "__main__":
    main()