#!/usr/bin/env python3
"""
Global EPG Downloader - Multi-source, smarter name matching (Jan 2026)
Downloads per-country EPG → saves in ./epg_db/{NormalizedCountry}/guide.xml(.gz optional)

Usage:
  python global_epg_db.py --all
  python global_epg_db.py --countries "United States" Canada France "United Kingdom"
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import argparse
import json
import os
import sys
from pathlib import Path
import requests
from urllib.parse import quote
import gzip

# ────────────────────────────────────────────────
# SOURCES - ordered by reliability / freshness 2026
# ────────────────────────────────────────────────
SOURCES = [
    {
        "name": "globetvapp",
        "base_raw": "https://raw.githubusercontent.com/globetvapp/epg/main",
        "folder_style": "AsInRepo",  # Mostly TitleNoSpace but some like Unitedkingdom, Usa, Southafrica
        "file_patterns": [
            "{slug_lower}1.xml", "{slug_lower}2.xml", "{slug_lower}3.xml", "{slug_lower}4.xml", "{slug_lower}5.xml", "{slug_lower}6.xml",
            "guide.xml", "epg.xml", "{slug}.xml", "{country_lower}.xml",
            "{slug_lower}.xml.gz", "guide.xml.gz", "epg.xml.gz",  # some repos use gz
        ]
    },
    # Add more sources later, e.g.:
    # {
    #     "name": "iptv-org",
    #     "base_raw": "https://raw.githubusercontent.com/iptv-org/epg/master",
    #     "folder_style": "other",
    #     "file_patterns": ["guides/{slug_lower}.xml", ...]
    # },
]

# ────────────────────────────────────────────────
# Full country list from globetvapp/epg folders (108 countries as of Jan 2026)
# Display names are human-readable; slug_map handles exact folder names
# ────────────────────────────────────────────────
AVAILABLE_COUNTRIES = [
    "Albania", "Argentina", "Australia", "Austria", "Belgium", "Bolivia", "Bosnia and Herzegovina", "Brazil",
    "Bulgaria", "Canada", "Caribbean", "Chile", "China", "Colombia", "Costa Rica", "Croatia", "Cyprus",
    "Czech Republic", "Denmark", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Estonia",
    "Finland", "France", "Georgia", "Germany", "Ghana", "Greece", "Guatemala", "Honduras", "Hong Kong",
    "Hungary", "Iceland", "India", "Indonesia", "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica",
    "Kenya", "Korea", "Latvia", "Lithuania", "Luxembourg", "Macau", "Madagascar", "Malawi", "Malaysia",
    "Malta", "Mauritius", "Mexico", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Namibia",
    "Netherlands", "New Caledonia", "New Zealand", "Nigeria", "Norway", "Pakistan", "Panama", "Paraguay",
    "Peru", "Philippines", "Poland", "Portugal", "Puerto Rico", "Qatar", "Romania", "Russia",
    "Saudi Arabia", "Scotland", "Serbia", "Singapore", "Slovakia", "Slovenia", "South Africa", "Spain",
    "Sweden", "Switzerland", "Taiwan", "Thailand", "Turkey", "UAE", "Uganda", "Ukraine", "United Kingdom",
    "Uruguay", "United States", "Uzbekistan", "Venezuela", "Vietnam", "Zambia"
]

# In normalize_country_name(), expand the slug_map to cover all:
def normalize_country_name(name: str) -> tuple[str, str]:
    """Return (display_name, folder_slug) – slug is the exact folder name in repo"""
    name = name.strip()
    # Full mapping: display → exact repo folder
    slug_map = {
    "Bosnia and Herzegovina": "Bosnia",
    "Costa Rica": "Costarica",
    "Czech Republic": "Czech",
    "Dominican Republic": "Dominican",
    "El Salvador": "Elsalvador",
    "Hong Kong": "Hongkong",
    "Ivory Coast": "Ivorycoast",
    "New Caledonia": "Newcaledonia",
    "New Zealand": "Newzealand",
    "Puerto Rico": "Puertorico",
    "Saudi Arabia": "Saudiarabia",
    "South Africa": "Southafrica",
    "United Arab Emirates": "Uae",  # or "UAE" if you use that display
    "United Kingdom": "Unitedkingdom",
    "United States": "Usa",
    # These usually match automatically but can override if needed:
    # "Korea": "Korea",
    # "Scotland": "Scotland",
}
    slug = slug_map.get(name, name.replace(" ", "").replace(".", ""))
    return name, slug

def try_download(url: str, timeout=12) -> bytes | None:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "EPG-Downloader/1.0"})
        if r.status_code == 200 and len(r.content) > 50_000:  # rough min size filter
            return r.content
        return None
    except Exception:
        return None


def download_for_country(country_display: str, output_dir: Path) -> bool:
    display, slug = normalize_country_name(country_display)
    lower = slug.lower()
    country_dir = output_dir / slug
    country_dir.mkdir(parents=True, exist_ok=True)
    target = country_dir / "guide.xml"

    print(f"\n=== {display} ({slug}) ===")

    for src in SOURCES:
        base = src["base_raw"]
        patterns = src["file_patterns"]
        folder = slug  # globetvapp uses slug directly as folder

        for pat in patterns:
            filename = pat.format(
                slug=slug, slug_lower=lower, country_lower=lower, country=display
            )
            url = f"{base}/{quote(folder)}/{quote(filename)}"
            print(f"  Trying {src['name']} → {filename} ... ", end="")

            data = try_download(url)
            if data is not None:
                print("✓ saved", end="")
                # Handle .gz if applicable
                if filename.lower().endswith('.gz'):
                    try:
                        data = gzip.decompress(data)
                        print(" (decompressed)", end="")
                    except Exception as e:
                        print(f" (gz failed: {e} → skipping)", end="")
                        continue  # skip this file, try next pattern

                # Now data is decompressed bytes (or original if not gz)
                # Safe to write
                with open(target, "wb") as f:
                    f.write(data)
                print()  # newline after success line
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

            if "date" in root.attrib:
                extra_info["generated_date"] = root.attrib["date"]
            if "generator-info-name" in root.attrib:
                extra_info["generator"] = root.attrib["generator-info-name"]

            if programmes:
                start_times = []
                for prog in programmes:
                    start = prog.get("start")
                    if start:
                        dt_str = start.split(" ")[0][:14]
                        try:
                            dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                            start_times.append(dt)
                        except ValueError:
                            pass
                if start_times:
                    max_dt = max(start_times)
                    extra_info["latest_programme_start"] = max_dt.isoformat()
                    age = (datetime.now(timezone.utc) - max_dt).days
                    extra_info["age_days"] = max(age, 0)

        except Exception as e:
            print(f"Warning: Failed to parse {epg_file}: {e}")

        index[country_dir.name] = {
            "country": country_dir.name,
            "file": f"{country_dir.name}/guide.xml",
            "size_mb": size_mb,
            "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "globetvapp/epg (primary)",
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
    parser.add_argument('--countries', nargs='+', help="Country names (use quotes for multi-word)")
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
    for c in sorted(countries):  # sort for nicer output
        if download_for_country(c, out_dir):
            success += 1

    build_index(out_dir)
    print(f"\nFinished — {success}/{len(countries)} countries saved.")


if __name__ == "__main__":
    main()
