#!/usr/bin/env python3
"""
Global EPG Downloader - Multi-source, smarter name matching (Jan 2026)
Downloads per-country EPG → saves in ./epg_db/{NormalizedCountry}/guide.xml(.gz optional)

Usage:
  python global_epg_db.py --all
  python global_epg_db.py --countries "United States" Canada France "United Kingdom"
"""
import xml.etree.ElementTree as ET
from datetime import datetime
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
    for country_dir in output_dir.iterdir():
        if not country_dir.is_dir():
            continue
        epg_file = country_dir / "guide.xml"
        if not epg_file.exists() or epg_file.stat().st_size < 50_000:
            continue

        size_mb = round(epg_file.stat().st_size / (1024 * 1024), 2)

        # Parse for rich info
        extra_info = {
            "channels_count": 0,
            "programmes_count": 0,
            "generated_date": "Unknown",
            "latest_programme_start": "Unknown",
            "age_days": "N/A",
            "generator": "Unknown",
        }
        try:
            tree = ET.parse(epg_file)
            root = tree.getroot()

            extra_info["channels_count"] = len(root.findall("channel"))

            programmes = root.findall("programme")
            extra_info["programmes_count"] = len(programmes)

            # Generated date if present
            if "date" in root.attrib:
                extra_info["generated_date"] = root.attrib["date"]

            # Generator info
            if "generator-info-name" in root.attrib:
                extra_info["generator"] = root.attrib["generator-info-name"]

            # Freshness from max programme start
            if programmes:
                start_times = []
                for prog in programmes:
                    start = prog.get("start")
                    if start:
                        # Parse YYYYMMDDHHMMSS (ignore tz offset for simplicity)
                        dt_str = start.split(" ")[0][:14]  # e.g., 20260119120000
                        try:
                            dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
                            start_times.append(dt)
                        except ValueError:
                            pass
                if start_times:
                    max_dt = max(start_times)
                    extra_info["latest_programme_start"] = max_dt.isoformat()
                    age = (datetime.utcnow() - max_dt).days
                    extra_info["age_days"] = max(age, 0)  # no negative

        except Exception as e:
            print(f"Warning: Failed to parse {epg_file}: {e}")

        index[country_dir.name] = {
            "country": country_dir.name,
            "file": f"{country_dir.name}/guide.xml",
            "size_mb": size_mb,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "source": "globetvapp/epg (primary)",  # update if multi-source
            "channels": extra_info["channels_count"],
            "programmes": extra_info["programmes_count"],
            "generated_date": extra_info["generated_date"],
            "latest_programme_start": extra_info["latest_programme_start"],
            "age_days": extra_info["age_days"],
            "generator": extra_info["generator"],
        }

    with open(output_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print(f"\nRich index created: {output_dir}/index.json ({len(index)} countries)")


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
