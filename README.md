# Global TV EPG Grabber

Free daily-updated **XMLTV EPG files** for ~100 countries  
Sourced from https://github.com/globetvapp/epg

This repo downloads and organizes the files into `./epg_db/` and keeps them fresh via daily GitHub Actions.

## Get country EPG directly from GitHub (no script needed)

All files are publicly available on GitHub raw URLs.  
Replace `{country}` with the folder name (case-sensitive).

Examples:

- United States:  
  https://github.com/Debe2025/global-tv-schedule-grabber/raw/main/epg_db/Usa/guide.xml

- United Kingdom:  
  https://github.com/Debe2025/global-tv-schedule-grabber/raw/main/epg_db/Unitedkingdom/guide.xml

- Canada:  
  https://github.com/Debe2025/global-tv-schedule-grabber/raw/main/epg_db/Canada/guide.xml

- Australia:  
  https://github.com/Debe2025/global-tv-schedule-grabber/raw/main/epg_db/Australia/guide.xml

- France:  
  https://github.com/Debe2025/global-tv-schedule-grabber/raw/main/epg_db/France/guide.xml

Full list of available countries/folders:  
→ Open https://github.com/Debe2025/global-tv-schedule-grabber/tree/main/epg_db  
(every subfolder is a country or region)

## Quick local usage (if you want to run the script)

```bash
# Download all countries
python global_epg_db.py --all

# Or just a few
python global_epg_db.py --countries "United States" "United Kingdom" Canada Australia
Files appear in ./epg_db/
Notes

EPG updates daily (~3 AM UTC) via GitHub Actions
Files are plain XMLTV — works with Kodi, Plex, TVHeadend, Jellyfin, etc.
No live streams included — only schedules

Enjoy your free global TV guide! 📺
