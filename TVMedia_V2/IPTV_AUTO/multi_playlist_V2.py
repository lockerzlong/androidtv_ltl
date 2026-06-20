import requests
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Bypass Cloudflare: dùng curl_cffi ──
try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_FFI = True
    print("✅ curl_cffi available")
except ImportError:
    HAS_CURL_FFI = False
    print("❌ curl_cffi not available")

# 📂 Đặt thư mục lưu file đầu ra
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

SOURCES = [
    {"name": "Tieulam", "url": "https://api.tlap17062026.com", "output": OUTPUT_DIR / "tieulam.m3u"},
    {"name": "Tamquoc", "url": "https://sv.tamquoctv.xyz/internal/api/matches", "output": OUTPUT_DIR /"tamquoc.m3u"},
]

EXTRA_SOURCES = [
    {"name": "TruyenHinh", "url": "https://raw.githubusercontent.com/lockerzlong/androidtv_ltl/main/TVMedia_V2/IPTV", "output": OUTPUT_DIR / "truyenhinh.m3u"},
]

ALL_OUTPUT = OUTPUT_DIR / "all_V2.m3u"

TIEULAM_API_URL      = "https://api.tlap17062026.com/matches/graph"
TIEULAM_DETAIL_URL   = "https://api.tlap17062026.com/matches/{match_id}"
TIEULAM_STREAM_DOMAINS = [
    "https://live.secufun.xyz/live/",
    "https://sv1.tieulamlive.org/live/",
]

TIEULAM_POST_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://sv1.tieulamlive.org",
    "Referer": "https://sv1.tieulamlive.org/trang-chu",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}

TIEULAM_GET_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://sv1.tieulamlive.org",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

def fetch_json(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ Lỗi lấy JSON từ {url}: {e}")
        return None

def extract_channels(data):
    channels = []
    def walk(node):
        if isinstance(node, dict):
            if "channels" in node:
                channels.extend(node["channels"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(data)
    return channels

# ─────────────────────────────────────────────
# TIEULAM: helpers nội bộ
# ─────────────────────────────────────────────

def _tieulam_get_yesterday():
    dt = datetime.now(timezone.utc) - timedelta(days=1)
    return dt.strftime("%Y-%m-%d") + " 00:00:00"

def _tieulam_get_future(days=7):
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.strftime("%Y-%m-%d") + " 23:59:59"

def _tieulam_build_query(page=1, limit=200):
    return {
        "queries": [
            {"field": "start_date", "type": "gte", "value": _tieulam_get_yesterday()},
            {"field": "start_date", "type": "lte", "value": _tieulam_get_future(7)},
        ],
        "limit": limit,
        "page": page,
        "order_asc": "start_date",
    }

def _tieulam_http_post(payload, timeout=30):
    """POST với curl_cffi"""
    try:
        if not HAS_CURL_FFI:
            print("   ❌ curl_cffi not available")
            return None
            
        r = cf_requests.post(
            TIEULAM_API_URL,
            json=payload,
            headers=TIEULAM_POST_HEADERS,
            timeout=timeout,
            impersonate="chrome120"
        )
        print(f"   📡 POST → {r.status_code}")
        if r.status_code == 200:
            return json.loads(r.text)
        else:
            print(f"   ❌ {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"   ❌ POST exception: {e}")
        return None

def _tieulam_http_get(url, referer=None, timeout=15):
    """GET với curl_cffi"""
    try:
        if not HAS_CURL_FFI:
            print("   ❌ curl_cffi not available")
            return None
            
        headers = dict(TIEULAM_GET_HEADERS)
        if referer:
            headers["Referer"] = referer
        r = cf_requests.get(
            url,
            headers=headers,
            timeout=timeout,
            impersonate="chrome120"
        )
        print(f"   📡 GET {url} → {r.status_code}")
        if r.status_code == 200:
            return json.loads(r.text)
        else:
            print(f"   ❌ {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"   ❌ GET exception: {e}")
        return None

def _tieulam_check_url(url, timeout=5):
    try:
        r = requests.head(url, headers=TIEULAM_GET_HEADERS, timeout=timeout, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def _tieulam_fetch_all_pages(limit=200, max_pages=20):
    all_matches = []
    page = 1
    total_pages = 1

    while page <= total_pages and page <= max_pages:
        data = _tieulam_http_post(_tieulam_build_query(page=page, limit=limit))
        if not data or "data" not in data:
            break

        matches = data["data"]
        if not matches:
            break

        if page == 1 and "total" in data:
            total_pages = -(-data["total"] // limit)
            print(f"   📊 Tổng: {data['total']} trận, {total_pages} trang")

        all_matches.extend(matches)
        print(f"   📄 Trang {page}/{total_pages}: {len(matches)} trận")
        page += 1

    return all_matches

def _tieulam_parse_match(raw, idx=0):
    md = {
        "id":           raw.get("id", ""),
        "title":        raw.get("title", f"Trận đấu {idx+1}"),
        "is_live":      raw.get("is_live", False),
        "is_hot":       raw.get("is_hot", False),
        "league":       raw.get("league", ""),
        "desc":         raw.get("desc", ""),
        "team1_logo":   raw.get("team_1_logo", ""),
        "team1_score":  raw.get("team_1_score", 0),
        "team2_score":  raw.get("team_2_score", 0),
        "blv":          raw.get("blv", "") or "",
        "start_date":   raw.get("start_date", ""),
        "stream_url":   raw.get("source_live", "") or "",
        "stream_key":   raw.get("stream_key", "") or "",
        "stream_links": [],
    }

    if not md["stream_url"] and md["stream_key"]:
        for domain in TIEULAM_STREAM_DOMAINS:
            test_url = f"{domain}{md['stream_key']}/playlist.m3u8"
            if _tieulam_check_url(test_url):
                md["stream_url"] = test_url
                break
        if not md["stream_url"]:
            md["stream_url"] = f"{TIEULAM_STREAM_DOMAINS[0]}{md['stream_key']}/playlist.m3u8"

    for s in (raw.get("streams") or []):
        url   = s.get("url", "")
        stype = s.get("type", "")
        if url and (stype in ("hls", "m3u8") or ".m3u8" in url):
            md["stream_url"] = url
            break

    return md

def _tieulam_create_slug(title, match_id):
    import unicodedata, re as _re
    if not title:
        return match_id
    s = title.lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('đ', 'd')
    s = _re.sub(r'\s+vs\s+', '-vs-', s)
    s = _re.sub(r'[^a-z0-9\s-]', '', s)
    s = _re.sub(r'\s+', '-', s)
    s = _re.sub(r'-+', '-', s).strip('-')
    return f'{s}-{match_id}' if s else match_id

def _tieulam_fetch_detail_links(match_id, match_title):
    if not match_id:
        return []

    slug = _tieulam_create_slug(match_title, match_id)
    api_url = f'https://api.tlap17062026.com/match/{match_id}/live'
    referer = f'https://sv1.tieulamlive.org/truc-tiep/{slug}'

    print(f"   📡 GET {api_url}")
    print(f"   📡 Referer: {referer}")

    data = _tieulam_http_get(api_url, referer=referer)
    if not data:
        print(f"   ❌ Không lấy được stream links cho {match_title}")
        return []

    links = []
    for field, label in [("source", "Source"), ("hd_1", "HD1"), ("hd_2", "HD2"), ("hd_3", "HD3")]:
        val = data.get(field, '')
        if val and val != 'null' and val.startswith('http'):
            links.append({'name': label, 'url': val})
            print(f"   ✅ {label}: {val}")

    if not links:
        val = data.get('url', '')
        if val and val != 'null':
            links.append({'name': 'Source', 'url': val})

    print(f"   🔗 {match_title}: {len(links)} link")
    return links

def _tieulam_has_blv(match):
    return bool(match.get("blv") and match["blv"].strip() not in ("", "null"))

def _tieulam_sort_live(matches):
    return sorted(matches, key=lambda m: (not _tieulam_has_blv(m), not m["is_hot"]))

def _tieulam_sort_upcoming(matches):
    def key(m):
        try:
            t = datetime.fromisoformat(m["start_date"])
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
        except Exception:
            t = datetime.max.replace(tzinfo=timezone.utc)
        return (t, not _tieulam_has_blv(m), not m["is_hot"])
    return sorted(matches, key=key)

def _tieulam_format_time_vn(start_date_str):
    try:
        t = datetime.fromisoformat(start_date_str)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (t + timedelta(hours=7)).strftime("%H:%M")
    except Exception:
        return ""

def _tieulam_build_m3u(live_matches, upcoming_matches):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "#EXTM3U",
        "# Playlist from TieuLamLive",
        f"# Total: {len(live_matches) + len(upcoming_matches)} trận",
        f"# 🔴 LIVE: {len(live_matches)}",
        f"# ⏳ UPCOMING: {len(upcoming_matches)}",
        f"# Updated: {now_str}",
        "",
    ]

    for category, matches in [("LIVE", live_matches), ("UPCOMING", upcoming_matches)]:
        if not matches:
            continue
        icon = "🔴" if category == "LIVE" else "⏳"
        label = "ĐANG DIỄN RA" if category == "LIVE" else "SẮP DIỄN RA"
        lines.append(f"# === {icon} TRẬN {label} ({category}) ({len(matches)} trận) ===")
        lines.append("")
        for m in matches:
            time_str   = _tieulam_format_time_vn(m["start_date"])
            time_label = f" {time_str}" if time_str else ""
            score_label = (f" [{m['team1_score']}-{m['team2_score']}]"
                           if m["is_live"] and (m["team1_score"] or m["team2_score"]) else "")
            blv_label  = f" (BLV: {m['blv']})" if _tieulam_has_blv(m) else ""
            hot_label  = " 🔥" if m["is_hot"] else ""
            base_name  = f"{m['title']}{score_label}{time_label}{blv_label}{hot_label}"
            group      = f"{category} - {m.get('league', 'Football')}"
            logo       = m.get("team1_logo", "")

            write_links = []
            if m["stream_links"]:
                write_links = m["stream_links"]
            elif m["stream_url"]:
                write_links = [{"name": "Source", "url": m["stream_url"]}]

            for lnk in write_links:
                entry_name = f'{base_name} [{lnk["name"]}]' if lnk.get('name') else base_name
                lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{entry_name}')
                lines.append('#EXTVLCOPT:http-referrer=https://sv1.tieulamlive.org/')
                lines.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                if m.get('id'):          lines.append(f'# ID: {m["id"]}')
                if m.get('stream_key'):  lines.append(f'# StreamKey: {m["stream_key"]}')
                if m.get('start_date'):  lines.append(f'# Date: {m["start_date"]}')
                if m.get('league'):      lines.append(f'# League: {m["league"]}')
                if _tieulam_has_blv(m):  lines.append(f'# BLV: {m["blv"]}')
                if m['is_hot']:          lines.append('# Hot: Yes')
                lines.append(lnk['url'])
                lines.append('')
        lines.append("")

    return "\n".join(lines)

# ─────────────────────────────────────────────
# TIEULAM: hàm chính
# ─────────────────────────────────────────────

def process_tieulam_source(name, base_url, output_file):
    print(f"\n{'='*30}")
    print(f"🛰️  Đang xử lý TieulamTV: {base_url}")
    print(f"{'='*30}")

    now = datetime.now(timezone.utc)
    twelve_h_before = now - timedelta(hours=12)
    three_h_after   = now + timedelta(hours=3)

    print("📡 Đang gọi API...")
    raw_all = _tieulam_fetch_all_pages()

    if not raw_all:
        print("❌ Không lấy được dữ liệu từ API")
        return []

    football = [m for m in raw_all if (m.get("desc") or "").strip().upper() == "FOOTBALL"]
    print(f"⚽ FOOTBALL: {len(football)}/{len(raw_all)} trận")

    parsed = [_tieulam_parse_match(r, i) for i, r in enumerate(football)]

    filtered = []
    for m in parsed:
        if not m["start_date"]:
            continue
        try:
            t = datetime.fromisoformat(m["start_date"])
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if twelve_h_before <= t <= three_h_after:
                filtered.append(m)
        except Exception:
            filtered.append(m)

    print(f"🕐 Sau lọc thời gian: {len(filtered)} trận")

    live_matches, upcoming_matches = [], []
    for m in filtered:
        if m["is_live"]:
            live_matches.append(m)
        else:
            try:
                t = datetime.fromisoformat(m["start_date"])
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                if t > now:
                    upcoming_matches.append(m)
            except Exception:
                pass

    live_matches     = _tieulam_sort_live(live_matches)
    upcoming_matches = _tieulam_sort_upcoming(upcoming_matches)
    print(f"🔴 LIVE: {len(live_matches)}  |  ⏳ UPCOMING: {len(upcoming_matches)}")

    if not live_matches and not upcoming_matches:
        print("⚠️ Không có trận đấu nào phù hợp")
        return []

    for m in live_matches + upcoming_matches:
        try:
            t = datetime.fromisoformat(m["start_date"])
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            diff_minutes = (t - now).total_seconds() / 60

            if diff_minutes < -120:
                print(f"⏩ Bỏ qua (kết thúc lâu): {m['title']}")
                continue
            if diff_minutes <= 10:
                print(f"✅ Lấy stream chi tiết: {m['title']}")
                links = _tieulam_fetch_detail_links(m["id"], m["title"])
                if links:
                    m["stream_links"] = links
            else:
                print(f"⏳ Còn {diff_minutes:.0f} phút: {m['title']}")
        except Exception as e:
            print(f"❌ Lỗi xử lý {m['title']}: {e}")

    m3u_content = _tieulam_build_m3u(live_matches, upcoming_matches)
    Path(output_file).write_text(m3u_content, encoding="utf-8")
    total = len(live_matches) + len(upcoming_matches)
    print(f"🎉 Đã tạo {output_file} ({total} trận)")

    entries = []
    for m in live_matches + upcoming_matches:
        group      = f"{'LIVE' if m['is_live'] else 'UPCOMING'} - {m.get('league', 'Football')}"
        time_label = _tieulam_format_time_vn(m["start_date"])
        base_name  = f"{m['title']} {time_label}".strip()

        if m["stream_links"]:
            for lnk in m["stream_links"]:
                entries.append({
                    "source": name, "match": group,
                    "name": f"{base_name} [{lnk['name']}]",
                    "url": lnk["url"], "referer": None,
                    "img": m.get("team1_logo", ""),
                })
        elif m["stream_url"]:
            entries.append({
                "source": name, "match": group,
                "name": base_name, "url": m["stream_url"],
                "referer": None, "img": m.get("team1_logo", ""),
            })

    return entries

def process_tamquoc_source(name, url, output_file):
    print(f"\n==============================")
    print(f"🛰️  Đang xử lý TamQuocTV: {url}")
    print(f"==============================")

    root = fetch_json(url)
    if not root:
        return []

    matches = root.get("data") or root.get("matches") or []
    if not matches:
        print("⚠️ Không có trận đấu nào")
        return []

    all_entries = []

    for match in matches:
        title = match.get("title", "Unknown Match")
        start_time = match.get("startTime", "")

        try:
            dt = datetime.fromisoformat(start_time)
            local_time = dt.strftime("%H:%M")
            match_label = f"{title} - {local_time}"
        except:
            match_label = title

        commentator = match.get("commentator") or {}
        blv = commentator.get("nickname") or commentator.get("username") or "BLV"
        logo = match.get("homeClub", {}).get("logoUrl")

        streams = [
            commentator.get("streamSourceFhd"),
            commentator.get("streamSourceHd"),
            commentator.get("streamSourceSd")
        ]
        qualities = ["FHD", "HD", "SD"]

        for quality, stream_url in zip(qualities, streams):
            if not stream_url:
                continue
            all_entries.append({
                "source": name,
                "match": match_label,
                "name": f"{match_label} [{blv} - {quality}]",
                "url": stream_url,
                "referer": None,
                "img": logo
            })

    if all_entries:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for e in all_entries:
                attrs = [f'group-title="{e["match"]}"']
                if e["img"]:
                    attrs.append(f'tvg-logo="{e["img"]}"')
                attr_line = " ".join(attrs)
                f.write(f'#EXTINF:-1 {attr_line},{e["name"]}\n')
                f.write(f'{e["url"]}\n')
        print(f"🎉 Đã tạo {output_file} ({len(all_entries)} links)")

    return all_entries

def process_m3u_source(name, url, output_file):
    """Xử lý nguồn M3U và giữ nguyên nội dung"""
    print(f"\n==============================")
    print(f"🛰️  Đang xử lý M3U nguồn {name}: {url}")
    print(f"==============================")

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        lines = r.text.splitlines()
    except Exception as e:
        print(f"❌ Không tải được M3U từ {url}: {e}")
        return []

    all_entries = []
    current_extinf = None
    current_options = []
    current_comments = []
    current_url = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
            
        if line.startswith("#EXTM3U"):
            all_entries.append({"type": "header", "line": line})
            i += 1
            continue
            
        if line.startswith("#EXTVLCOPT"):
            current_options.append(line)
            i += 1
            continue
            
        if line.startswith("#") and not line.startswith("#EXTINF"):
            current_comments.append(line)
            i += 1
            continue
            
        if line.startswith("#EXTINF"):
            current_extinf = line
            i += 1
            continue
            
        if not line.startswith("#") and current_extinf:
            current_url = line
            i += 1
            entry = {
                "type": "stream",
                "extinf": current_extinf,
                "url": current_url,
                "options": current_options.copy(),
                "comments": current_comments.copy()
            }
            all_entries.append(entry)
            current_extinf = None
            current_url = None
            current_options = []
            current_comments = []
            continue
        
        i += 1

    if current_extinf:
        entry = {
            "type": "stream",
            "extinf": current_extinf,
            "url": None,
            "options": current_options,
            "comments": current_comments
        }
        all_entries.append(entry)

    if all_entries:
        with open(output_file, "w", encoding="utf-8") as f:
            for entry in all_entries:
                if entry["type"] == "header":
                    f.write(entry["line"] + "\n")
                elif entry["type"] == "stream":
                    for comment in entry["comments"]:
                        f.write(comment + "\n")
                    f.write(entry["extinf"] + "\n")
                    for opt in entry["options"]:
                        f.write(opt + "\n")
                    if entry["url"]:
                        f.write(entry["url"] + "\n")
        print(f"🎉 Đã tạo file M3U: {output_file} ({len([e for e in all_entries if e['type'] == 'stream'])} links)")
    
    return all_entries

def generate_all_playlist(all_data):
    print("\n==============================")
    print("🧩 Gộp tất cả nguồn thành all.m3u")
    print("==============================")

    with open(ALL_OUTPUT, "w", encoding="utf-8") as f:
        has_header = False
        
        for e in all_data:
            if e.get("type") == "header":
                f.write(e["line"] + "\n")
                has_header = True
                continue
            
            if "extinf" in e and e["extinf"]:
                for comment in e.get("comments", []):
                    f.write(comment + "\n")
                f.write(e["extinf"] + "\n")
                for opt in e.get("options", []):
                    f.write(opt + "\n")
                if e.get("url"):
                    f.write(e["url"] + "\n")
            else:
                attrs = [f'group-title="{e.get("source", "Unknown")}"']
                if e.get("referer"):
                    f.write(f'#EXTVLCOPT:http-referrer={e["referer"]}\n')
                    attrs.append(f'referer="{e["referer"]}"')
                if e.get("img"):
                    attrs.append(f'tvg-logo="{e["img"]}"')
                attr_line = " ".join(attrs)
                f.write(f'#EXTINF:-1 {attr_line},{e.get("name", "Unknown")}\n')
                f.write(f'{e.get("url", "")}\n')
    
    if not has_header:
        with open(ALL_OUTPUT, "r+", encoding="utf-8") as f:
            content = f.read()
            f.seek(0, 0)
            f.write("#EXTM3U\n" + content)

    print(f"🎉 Đã tạo xong file tổng: {ALL_OUTPUT}")

def main():
    all_entries = []
    
    # Extra M3U sources
    for src in EXTRA_SOURCES:
        entries = process_m3u_source(src["name"], src["url"], src["output"])
        all_entries.extend(entries)
        
    # JSON/remote data sources
    for src in SOURCES:
        if src["name"] == "Tieulam":
            entries = process_tieulam_source(src["name"], src["url"], src["output"])
        elif src["name"] == "Tamquoc":
            entries = process_tamquoc_source(src["name"], src["url"], src["output"])
        else:
            entries = []
        all_entries.extend(entries)

    if all_entries:
        generate_all_playlist(all_entries)
    else:
        print("❌ Không có dữ liệu hợp lệ nào để gộp.")

    if not any(OUTPUT_DIR.glob("*.m3u")):
        print("⚠️ Không có file nào được tạo trong output/. Kiểm tra nguồn dữ liệu!")

    stats_file = OUTPUT_DIR / "stats.txt"
    with open(stats_file, "w", encoding="utf-8") as f:
        f.write(str(len(all_entries)))

if __name__ == "__main__":
    main()
