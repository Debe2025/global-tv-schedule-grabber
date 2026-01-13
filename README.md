# 🌍 Global TV Schedule Grabber (EPG by Country)

This repository fetches free **Electronic Program Guides (EPG)** in XMLTV format, organized by country, sourced from the excellent [globetvapp/epg](https://github.com/globetvapp/epg) project.

- **Daily updates** — files refreshed ~3 AM UTC.
- Multiple split files per country (e.g., `unitedkingdom1.xml`, `unitedkingdom2.xml`...) for large channel lists.
- Perfect for IPTV apps, Kodi, Plex DVR, or any XMLTV-compatible player.

**Note:** This repo only downloads and organizes the EPG data — it does **not** include live TV streams (M3U playlists). Pair it with free/public IPTV lists (e.g., from [iptv-org/iptv](https://github.com/iptv-org/iptv)) for full use.

## Features

- Downloads all available country EPG files automatically.
- Organizes into folders like `epg_db/Unitedkingdom/`, `epg_db/Usa/`, etc.
- Creates `index.json` with metadata (files, sizes, counts).
- GitHub Actions workflow for daily auto-updates (optional).

## Requirements

- Python 3.8+ (tested on 3.12)
- `requests` library: `pip install requests`

## Quick Start

1. Clone the repo:
   ```bash
   git clone https://github.com/Debe2025/global-tv-schedule-grabber.git
   cd global-tv-schedule-grabber

Run the downloader:Bash# All available countries
python global_epg_db.py --all

# Or specific ones
python global_epg_db.py --countries Australia Canada France Germany "United Kingdom" "United States"
Files appear in ./epg_db/ (e.g., epg_db/Unitedkingdom/unitedkingdom4.xml).Check epg_db/index.json for what's downloaded.

Usage in Kodi (with PVR IPTV Simple Client)
Kodi uses the PVR IPTV Simple Client addon to load XMLTV EPG files for the TV Guide (EPG). This works best when you also have an M3U playlist for channels — the EPG from this repo can map to channels via tvg-id or names.
Step-by-Step Setup in Kodi (2026)

Install the Addon (if not already):
Kodi Home → Add-ons → Install from repository → Kodi Add-on repository → PVR clients → PVR IPTV Simple Client → Install.

Configure the Addon:
Go to Add-ons → My add-ons → PVR clients → PVR IPTV Simple Client → right-click/context → Configure (or Settings).

General Tab (optional but recommended):
Make sure it's enabled.
Set number of days to grab EPG (e.g., 7–14 days).

EPG Settings Tab (key part):
Location: Choose Local Path (include Local Network).
XMLTV Path: Browse to one (or more) of the downloaded files:
Single file example: F:\OneDrive\global-tv-schedule-grabber\epg_db\Unitedkingdom\unitedkingdom4.xml
For countries with multiple files (recommended): Add them one by one if Kodi allows multiple entries, or merge them manually (see tips below).

Cache XMLTV at local storage: Enable if you want Kodi to keep a copy.
EPG time shift: Adjust if times are off (e.g., +0 or -1 hour for timezone).
Click OK to save.

Clear Cache & Reload:
Go to Kodi Settings → PVR & Live TV → General → Clear data (or Clear cache).
Also under Guide → Clear cache if needed.
Restart Kodi (or force PVR restart via Settings → PVR & Live TV → General → Reset PVR database if issues persist).

View the EPG:
Go to TV in the main menu.
You should see "Starting PVR manager..." briefly.
Open the TV Guide (EPG) — programs should appear for matching channels.
If no data: Ensure your M3U playlist uses matching tvg-id or channel names to the XMLTV files.


Tips for Best Results in Kodi

Multiple files per country — Many countries have split files (e.g., usa1.xml + usa2.xml). You can:
Use only the largest/most relevant one.
Or merge them locally (simple Python script or tools like xmltv-util).

Matching channels — EPG works best when your M3U has tvg-id matching the <channel id="..."> in XMLTV.
Free M3U example — Try https://github.com/iptv-org/iptv (filter by country) for testing.
Large files — If Kodi is slow, limit EPG days or use a smaller country subset.
Updates — Re-run the Python script daily (or let GitHub Actions do it) → re-clear Kodi cache to refresh.

Folder Structure
textglobal-tv-schedule-grabber/
├── global_epg_db.py          # Main downloader script
├── epg_db/                   # Downloaded EPG data
│   ├── Australia/
│   │   └── australia1.xml
│   ├── Unitedkingdom/
│   │   └── unitedkingdom4.xml
│   └── ... (one folder per country)
├── index.json                # Metadata summary
├── .github/workflows/        # Daily auto-update (update-epg.yml)
└── README.md
License
MIT License — feel free to fork, modify, and use.
Data sourced from https://github.com/globetvapp/epg (GPLv3) — thank you to the maintainers!
Contributing

Found a missing country? Add to COUNTRY_MAP in the script and PR.
Issues with downloads? Open an issue with output.
Want auto-merge of split files? Suggest in issues.

Happy watching! 📺
