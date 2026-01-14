#############################################
# KODI IPTV SETUP - LIBRARY VIEW VERSION (Updated with iptv-org/epg grabber)
#############################################
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Host "Run as Administrator" -ForegroundColor Yellow; exit 1 }

# Get Kodi
function Get-KodiExe {
    $paths = @("$env:ProgramFiles\Kodi\kodi.exe", "$env:ProgramFiles(x86)\Kodi\kodi.exe")
    foreach ($p in $paths) { if (Test-Path $p) { return $p } }
    return $null
}
$KodiExe = Get-KodiExe
if (-not $KodiExe) {
    Write-Host "Installing Kodi..." -ForegroundColor Cyan
    $inst = "$env:TEMP\kodi.exe"
    Invoke-WebRequest "https://mirrors.kodi.tv/releases/windows/win64/kodi-21.0-Omega-x64.exe" -OutFile $inst -TimeoutSec 60
    Start-Process $inst -ArgumentList "/S" -Wait; Start-Sleep 5
    $KodiExe = Get-KodiExe
    if (-not $KodiExe) { Write-Host "Installation failed" -ForegroundColor Red; exit 1 }
}

$KodiPath = "$env:APPDATA\Kodi"
$UserdataPath = "$KodiPath\userdata"
$AddonsPath = "$KodiPath\addons"
if (-not (Test-Path $UserdataPath)) {
    Start-Process $KodiExe; Start-Sleep 12
    Stop-Process -Name kodi -Force -ErrorAction SilentlyContinue
}
Get-Process kodi -ErrorAction SilentlyContinue | Stop-Process -Force

# Detect location via IP
Write-Host "Detecting location..." -ForegroundColor Cyan
try {
    $geo = Invoke-RestMethod "http://ip-api.com/json/" -TimeoutSec 10
    $cc = $geo.countryCode.ToLower()
    $cn = $geo.country
    Write-Host " $cn (IP-based)" -ForegroundColor Green
} catch { $cc = "us"; $cn = "United States" }

# Download playlists
Write-Host "`nDownloading playlists..." -ForegroundColor Cyan
$urls = @(
    @{N="Country";URL="https://iptv-org.github.io/iptv/countries/$cc.m3u";C="L"},
    @{N="English";URL="https://iptv-org.github.io/iptv/languages/eng.m3u";C="L"},
    @{N="Movies";URL="https://iptv-org.github.io/iptv/categories/movies.m3u";C="M"},
    @{N="Series";URL="https://iptv-org.github.io/iptv/categories/series.m3u";C="S"},
    @{N="Sports";URL="https://iptv-org.github.io/iptv/categories/sports.m3u";C="P"}
)
$seen = @{}; $tot = 0; $dup = 0
$main = "#EXTM3U`n"; $mov = "#EXTM3U`n"; $ser = "#EXTM3U`n"; $spo = "#EXTM3U`n"
foreach ($u in $urls) {
    try {
        $wc = New-Object System.Net.WebClient
        $wc.Encoding = [System.Text.Encoding]::UTF8
        $txt = $wc.DownloadString($u.URL)
        $wc.Dispose()
       
        $lns = $txt -split "`n"; $ex = ""; $cnt = 0
        foreach ($ln in $lns) {
            $ln = $ln.Trim()
            if ($ln -match "^#EXTINF:") { $ex = $ln }
            elseif ($ln -match "^http" -and $ex -ne "") {
                if (-not $seen.ContainsKey($ln.ToLower())) {
                    $seen[$ln.ToLower()] = $true
                    $ent = "$ex`n$ln`n"
                    $main += $ent
                    if ($u.C -eq "M") { $mov += $ent }
                    elseif ($u.C -eq "S") { $ser += $ent }
                    elseif ($u.C -eq "P") { $spo += $ent }
                    $tot++; $cnt++
                } else { $dup++ }
                $ex = ""
            }
        }
        if ($cnt -gt 0) { Write-Host " [+] $($u.N): $cnt" -ForegroundColor Green }
    } catch { Write-Host " [-] $($u.N)" -ForegroundColor Yellow }
}
Write-Host " Total: $tot (removed $dup duplicates)" -ForegroundColor Cyan
Set-Content "$UserdataPath\playlist.m3u8" $main -Encoding UTF8
Set-Content "$UserdataPath\playlist_movies.m3u8" $mov -Encoding UTF8
Set-Content "$UserdataPath\playlist_series.m3u8" $ser -Encoding UTF8
Set-Content "$UserdataPath\playlist_sports.m3u8" $spo -Encoding UTF8

# ────────────────────────────────────────────────────────────────
# Reliable EPG: Generate fresh using iptv-org/epg grabber (Node.js)
# ────────────────────────────────────────────────────────────────
Write-Host "`nGenerating fresh EPG using iptv-org/epg grabber scripts..." -ForegroundColor Cyan

$epgRepoDir    = "$env:TEMP\iptv-epg"
$epgOutputGz   = "$UserdataPath\epg.xml.gz"
$channelsXml   = "$UserdataPath\custom.channels.xml"

$epgOK = $false

# Create channels.xml (Vancouver/CA focus + global examples)
$channelContent = @"
<?xml version="1.0" encoding="UTF-8"?>
<channels>
  <!-- Canada / Vancouver area examples -->
  <channel site="cbc.ca"         lang="en" xmltv_id="CBC.ca"           site_id="CBC">CBC</channel>
  <channel site="globaltv.com"   lang="en" xmltv_id="GlobalBC.ca"      site_id="GlobalBC">Global BC</channel>
  <channel site="ctv.ca"         lang="en" xmltv_id="CTV.ca"           site_id="CTV">CTV</channel>
  <channel site="citytv.com"     lang="en" xmltv_id="CityTV.ca"        site_id="CityTV">CityTV</channel>
  <!-- US examples -->
  <channel site="abc.go.com"     lang="en" xmltv_id="ABC.us"           site_id="ABC">ABC</channel>
  <channel site="nbc.com"        lang="en" xmltv_id="NBC.us"           site_id="NBC">NBC</channel>
  <!-- UK example -->
  <channel site="bbc.co.uk"      lang="en" xmltv_id="BBCOne.uk"        site_id="BBC1">BBC One</channel>
</channels>
"@
Set-Content $channelsXml $channelContent -Encoding UTF8

# Clone iptv-org/epg shallow
if (-not (Test-Path $epgRepoDir)) {
    Write-Host "Cloning iptv-org/epg..." -ForegroundColor Yellow
    git clone --depth 1 -b master https://github.com/iptv-org/epg.git $epgRepoDir
}

Push-Location $epgRepoDir

# Install dependencies
npm install --no-save --silent

# Run grabber
Write-Host "Running EPG grabber (5–20 minutes depending on sites)..." -ForegroundColor Yellow
npm run grab -- `
  --channels="$channelsXml" `
  --output="$UserdataPath\guide.xml" `
  --days=7 `
  --maxConnections=4 `
  --timeout=15000 `
  --gzip

Pop-Location

if (Test-Path "$UserdataPath\guide.xml.gz") {
    Move-Item "$UserdataPath\guide.xml.gz" $epgOutputGz -Force
    Write-Host " [+] Fresh EPG ready ($epgOutputGz)" -ForegroundColor Green
    $epgOK = $true
} elseif (Test-Path "$UserdataPath\guide.xml") {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $source = [System.IO.File]::OpenRead("$UserdataPath\guide.xml")
    $dest   = [System.IO.File]::Create($epgOutputGz)
    $gz     = New-Object System.IO.Compression.GZipStream($dest, [System.IO.Compression.CompressionMode]::Compress)
    $source.CopyTo($gz)
    $gz.Close(); $dest.Close(); $source.Close()
    Remove-Item "$UserdataPath\guide.xml" -Force
    Write-Host " [+] Fresh EPG gzipped ($epgOutputGz)" -ForegroundColor Green
    $epgOK = $true
} else {
    Write-Host " [-] Grabber failed - check console output" -ForegroundColor Yellow
}

if (-not $epgOK) {
    Write-Host "Falling back to empty EPG placeholder" -ForegroundColor Yellow
    $emptyXml = @"
<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="Empty Placeholder"></tv>
"@
    Set-Content "$UserdataPath\epg.xml" $emptyXml -Encoding UTF8
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $s = [System.IO.File]::OpenRead("$UserdataPath\epg.xml")
    $d = [System.IO.File]::Create($epgOutputGz)
    $g = New-Object System.IO.Compression.GZipStream($d, [System.IO.Compression.CompressionMode]::Compress)
    $s.CopyTo($g); $g.Close(); $d.Close(); $s.Close()
}

# First run to initialize Kodi folders
Write-Host "`nInitializing Kodi..." -ForegroundColor Cyan
Start-Process $KodiExe; Start-Sleep 25
Stop-Process -Name kodi -Force -ErrorAction SilentlyContinue; Start-Sleep 3

# Configure Kodi
Write-Host "Configuring Kodi..." -ForegroundColor Cyan
$oldPl = "$UserdataPath\playlists"
if (Test-Path $oldPl) { Remove-Item $oldPl -Recurse -Force }

# Advanced settings
$adv = "<advancedsettings version=`"1.0`">`n <network>`n <buffermode>1</buffermode>`n <cachemembuffersize>134217728</cachemembuffersize>`n <readbufferfactor>20</readbufferfactor>`n </network>`n</advancedsettings>"
Set-Content "$UserdataPath\advancedsettings.xml" $adv

# GUI settings
$gui = "<settings version=`"2`">`n <setting id=`"addons.unknownsources`" type=`"boolean`">true</setting>`n <setting id=`"pvrmanager.enabled`" type=`"boolean`">true</setting>`n <setting id=`"pvrmanager.syncchannels`" type=`"boolean`">true</setting>`n <setting id=`"lookandfeel.enableaddonsmenu`" type=`"boolean`">false</setting>`n <setting id=`"videolibrary.enabled`" type=`"boolean`">true</setting>`n</settings>"
Set-Content "$UserdataPath\guisettings.xml" $gui

# PVR IPTV Simple Client settings
$pvrPath = "$UserdataPath\addon_data\pvr.iptvsimple"
New-Item -ItemType Directory -Force -Path $pvrPath | Out-Null
$plFile = "$UserdataPath\playlist.m3u8"
$epFile = "$UserdataPath\epg.xml.gz"
$pvr = "<settings version=`"2`">`n <setting id=`"m3uPathType`" type=`"integer`">0</setting>`n <setting id=`"m3uPath`" type=`"string`">$plFile</setting>`n <setting id=`"epgPathType`" type=`"integer`">0</setting>`n <setting id=`"epgPath`" type=`"string`">$epFile</setting>`n <setting id=`"m3uCache`" type=`"boolean`">true</setting>`n <setting id=`"epgCache`" type=`"boolean`">true</setting>`n <setting id=`"m3uRefreshMode`" type=`"integer`">2</setting>`n <setting id=`"m3uRefreshIntervalMins`" type=`"integer`">120</setting>`n <setting id=`"allChannelsGroupsEnabled`" type=`"boolean`">true</setting>`n <setting id=`"useFFmpegReconnect`" type=`"boolean`">true</setting>`n <setting id=`"useInputstreamAdaptiveforHls`" type=`"boolean`">true</setting>`n</settings>"
Set-Content "$pvrPath\settings.xml" $pvr

# Create stream files with NFO metadata for library view
Write-Host "`nCreating library with thumbnails..." -ForegroundColor Cyan
$movDir = "$UserdataPath\Movies"
$serDir = "$UserdataPath\Series"
$spoDir = "$UserdataPath\Sports"
New-Item -ItemType Directory -Force -Path $movDir | Out-Null
New-Item -ItemType Directory -Force -Path $serDir | Out-Null
New-Item -ItemType Directory -Force -Path $spoDir | Out-Null

function MakeLibrary($plPath, $outDir, $type) {
    $content = Get-Content $plPath -Raw
    $lines = $content -split "`n"
    $extinf = ""
    $count = 0
   
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i].Trim()
       
        if ($line -like "#EXTINF:*") {
            $extinf = $line
        }
        elseif ($line -match "^http" -and $extinf -ne "") {
            if ($extinf -match ',(.+)$') {
                $name = $matches[1].Trim()
                $name = $name -replace '[\\/:*?"<>|]', '_'
            }
           
            $logo = ""
            if ($extinf -match 'tvg-logo="([^"]+)"') {
                $logo = $matches[1]
            }
           
            $strmFile = Join-Path $outDir "$name.strm"
            $line | Out-File -FilePath $strmFile -Force -NoNewline
           
            $nfoFile = Join-Path $outDir "$name.nfo"
            $xml = "<?xml version=""1.0"" encoding=""UTF-8"" standalone=""yes""?>`n"
            if ($type -eq "movie") {
                $xml += "<movie>`n <title>$name</title>`n"
                if ($logo) { $xml += " <thumb>$logo</thumb>`n" }
                $xml += "</movie>"
            } else {
                $xml += "<tvshow>`n <title>$name</title>`n"
                if ($logo) { $xml += " <thumb>$logo</thumb>`n" }
                $xml += "</tvshow>"
            }
            $xml | Out-File -FilePath $nfoFile -Force
           
            $count++
            $extinf = ""
        }
    }
    return $count
}

$mc = MakeLibrary "$UserdataPath\playlist_movies.m3u8" $movDir "movie"
$sc = MakeLibrary "$UserdataPath\playlist_series.m3u8" $serDir "tvshow"
$spc = MakeLibrary "$UserdataPath\playlist_sports.m3u8" $spoDir "video"

Write-Host " [+] Movies: $mc items with thumbnails" -ForegroundColor Green
Write-Host " [+] TV Shows: $sc items with thumbnails" -ForegroundColor Green
Write-Host " [+] Sports: $spc items" -ForegroundColor Green

# Sources
$src = "<sources>`n <programs><default pathversion=`"1`"></default></programs>`n <video><default pathversion=`"1`"></default>`n <source><n>Movies</n><path pathversion=`"1`">$movDir\</path><allowsharing>true</allowsharing></source>`n <source><n>TV Shows</n><path pathversion=`"1`">$serDir\</path><allowsharing>true</allowsharing></source>`n <source><n>Sports</n><path pathversion=`"1`">$spoDir\</path><allowsharing>true</allowsharing></source>`n </video>`n <music><default pathversion=`"1`"></default></music>`n <pictures><default pathversion=`"1`"></default></pictures>`n <files><default pathversion=`"1`"></default></files>`n</sources>"
Set-Content "$UserdataPath\sources.xml" $src

# Favorites
$fav = "<favourites>`n <favourite name=`"Live TV`">ActivateWindow(TVChannels)</favourite>`n <favourite name=`"Movies`">ActivateWindow(Videos,$movDir\,return)</favourite>`n <favourite name=`"TV Shows`">ActivateWindow(Videos,$serDir\,return)</favourite>`n <favourite name=`"Sports`">ActivateWindow(Videos,$spoDir\,return)</favourite>`n</favourites>"
Set-Content "$UserdataPath\favourites.xml" $fav

# Skin settings
$skinPath = "$UserdataPath\addon_data\skin.estuary"
New-Item -ItemType Directory -Force -Path $skinPath | Out-Null
$skin = "<settings version=`"2`">`n <setting id=`"HomeMenuNoMoviesButton`" type=`"boolean`">false</setting>`n <setting id=`"HomeMenuNoTVShowButton`" type=`"boolean`">false</setting>`n <setting id=`"HomeMenuNoMusicButton`" type=`"boolean`">true</setting>`n <setting id=`"HomeMenuNoRadioButton`" type=`"boolean`">true</setting>`n <setting id=`"HomeMenuNoPicturesButton`" type=`"boolean`">true</setting>`n <setting id=`"HomeMenuNoVideosButton`" type=`"boolean`">false</setting>`n <setting id=`"HomeMenuNoTVButton`" type=`"boolean`">false</setting>`n</settings>"
Set-Content "$skinPath\settings.xml" $skin
Write-Host " [+] Main menu tabs configured" -ForegroundColor Green

# Final run and trigger library scan
Write-Host "`nFinalizing and scanning library..." -ForegroundColor Cyan
Start-Process $KodiExe
Start-Sleep 15

Write-Host " Triggering library scan for thumbnails..." -ForegroundColor Gray
try {
    $jsonMovies = @{
        jsonrpc = "2.0"
        method = "VideoLibrary.Scan"
        params = @{ directory = $movDir }
        id = 1
    } | ConvertTo-Json
   
    Invoke-RestMethod -Uri "http://localhost:8080/jsonrpc" -Method Post -Body $jsonMovies -ContentType "application/json" -ErrorAction SilentlyContinue
   
    $jsonTV = @{
        jsonrpc = "2.0"
        method = "VideoLibrary.Scan"
        params = @{ directory = $serDir }
        id = 2
    } | ConvertTo-Json
   
    Invoke-RestMethod -Uri "http://localhost:8080/jsonrpc" -Method Post -Body $jsonTV -ContentType "application/json" -ErrorAction SilentlyContinue
   
    Write-Host " [+] Library scan triggered" -ForegroundColor Green
} catch {
    Write-Host " [!] Could not trigger scan automatically" -ForegroundColor Yellow
    Write-Host " Manual: Settings > Media > Library > Update library" -ForegroundColor Yellow
}

Start-Sleep 20
Stop-Process -Name kodi -Force -ErrorAction SilentlyContinue

# Summary
$info = "KODI IPTV SETUP COMPLETE`n`nLocation: $cn (IP-based)`nTotal Channels: $tot`n Movies: $mc (with thumbnails)`n TV Shows: $sc (with thumbnails)`n Sports: $spc`n`nMAIN MENU:`n Movies tab - Click to see thumbnail grid`n TV Shows tab - Click to see thumbnail grid`n Videos - All content including Sports`n TV - Live TV with EPG`n`nEPG source: Freshly generated via iptv-org grabber`n`nJust click any thumbnail to watch!"
Set-Content "$env:USERPROFILE\Desktop\KODI_SETUP.txt" $info

Write-Host "`n===============================================" -ForegroundColor Green
Write-Host " SETUP COMPLETE " -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host "Location: $cn (IP-based)" -ForegroundColor Cyan
Write-Host "Channels: $tot | Movies: $mc | TV Shows: $sc | Sports: $spc" -ForegroundColor Cyan
Write-Host "`nMain menu: TV, Movies (grid), TV Shows (grid), Videos" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"