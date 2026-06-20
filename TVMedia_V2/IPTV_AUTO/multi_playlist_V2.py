import requests
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 📂 Đặt thư mục lưu file đầu ra
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

SOURCES = [
    # {"name": "BunCha", "url": "https://hxcv.site/buncha", "output": OUTPUT_DIR /"buncha.m3u"}, # chưa chạy được
    # {"name": "KhanDaiA", "url": "https://hxcv.site/khandaia", "output": OUTPUT_DIR /"khandaia.m3u"}, # chưa chạy được, chạy với vlc thì ok    
    # {"name": "GaVang", "url": "https://hxcv.site/gavang", "output": OUTPUT_DIR /"gavang.m3u"}, # chưa chạy được, chạy với vlc thì ok
    # {"name": "Socolive", "url": "https://hxcv.site/socolive", "output": OUTPUT_DIR /"socolive.m3u"},
    # {"name": "Hoadao", "url": "https://hxcv.site/hoadao", "output": OUTPUT_DIR /"hoadao.m3u"},
    # {"name": "Vankhanh", "url": "https://hxcv.site/vankhanh", "output": OUTPUT_DIR /"vankhanh.m3u"},
    # {"name": "Chuoichien", "url": "https://hxcv.site/chuoichien", "output": OUTPUT_DIR /"chuoichien.m3u"},
    # {"name": "LuongSon", "url": "https://hxcv.site/luongson", "output": OUTPUT_DIR /"luongson.m3u"},    
    {"name": "Tieulam", "url": "https://api.tlap17062026.com", "output": OUTPUT_DIR / "tieulam.m3u"},
    {"name": "Tamquoc", "url": "https://sv.tamquoctv.xyz/internal/api/matches", "output": OUTPUT_DIR /"tamquoc.m3u"},
]
# 🆕 Các nguồn kiểu M3U trực tiếp (ví dụ: Cakhia)
EXTRA_SOURCES = [
    # {"name": "Cakhia", "url": "http://sharing.gotdns.ch:8091/cakhia.php", "output": OUTPUT_DIR / "cakhia.m3u"},# chưa chạy được, chạy với vlc thì ok    
    # {"name": "LuongSon_2", "url": "http://sharing.gotdns.ch:8091/luongsontv.php", "output": OUTPUT_DIR / "luongson_share.m3u"}, 
    # {"name": "Socolive_2", "url": "http://sharing.gotdns.ch:8091/socolive.php", "output": OUTPUT_DIR / "Socolive_share.m3u"},
    # {"name": "TruyenHinh_2", "url": "https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", "output": OUTPUT_DIR / "nhadai_2.m3u"},
    # {"name": "TruyenHinh_3", "url": "https://raw.githubusercontent.com/HaNoiIPTV/HaNoiIPTV.m3u/refs/heads/master/Danh%20s%C3%A1ch%20k%C3%AAnh/G%C3%B3i%20ch%C3%ADnh%20th%E1%BB%A9c/H%C3%A0%20N%E1%BB%99i%20IPTV.m3u", "output": OUTPUT_DIR / "nhadai_3.m3u"},
    {"name": "TruyenHinh", "url": "https://raw.githubusercontent.com/lockerzlong/androidtv_ltl/main/TVMedia_V2/IPTV", "output": OUTPUT_DIR / "truyenhinh.m3u"},
    
]
ALL_OUTPUT = OUTPUT_DIR / "all_V2.m3u"

TIEULAM_API_URL      = "https://api.tlap17062026.com/matches/graph"
TIEULAM_DETAIL_URL   = "https://api.tlap17062026.com/matches/{match_id}"
TIEULAM_STREAM_DOMAINS = [
    "https://live.secufun.xyz/live/",
    "https://sv1.tieulamlive.org/live/",
]

# Danh sách headers thử lần lượt cho đến khi thành công
TIEULAM_HEADER_CANDIDATES = [
    # 1. okhttp — thường dùng trong Android Java (Volley/OkHttp)
    {
        "Content-Type": "application/json; charset=utf-8",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/4.12.0",
    },
    # 2. Web browser với Referer tieulamlive.org
    {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://tieulamlive.org",
        "Referer": "https://tieulamlive.org/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    },
    # 3. Referer domain tlap
    {
        "Content-Type": "application/json",
        "Accept": "application/json, */*",
        "Origin": "https://tlap17062026.com",
        "Referer": "https://tlap17062026.com/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    },
    # 4. Android WebView
    {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "X-Requested-With": "com.androidtv.getm3u",
    },
    # 5. Bare minimum
    {
        "Content-Type": "application/json",
    },
]


def fetch_json(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ Lỗi lấy JSON từ {url}: {e}")
        return None


def fetch_stream_links(remote_url):
    """Lấy danh sách link stream từ remote_data (dành cho nguồn cũ)."""
    data = fetch_json(remote_url)
    if not data or "stream_links" not in data:
        return []
    links = []
    for s in data.get("stream_links", []):
        if not s.get("url"):
            continue
        headers = {h["key"]: h["value"] for h in s.get("request_headers", [])}
        links.append({
            "name": s.get("name", "Unnamed"),
            "url": s["url"],
            "referer": headers.get("Referer")
        })
    return links


def extract_channels(data):
    """Tìm toàn bộ channel trong JSON, dù nằm trong group hoặc root."""
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


def _tieulam_http_post(payload, timeout=20):
    """Thử lần lượt từng bộ headers cho đến khi thành công."""
    session = requests.Session()
    for i, headers in enumerate(TIEULAM_HEADER_CANDIDATES):
        try:
            r = session.post(TIEULAM_API_URL, json=payload, headers=headers, timeout=timeout)
            if r.status_code == 200:
                print(f"   ✅ Headers [{i+1}] thành công")
                return r.json()
            else:
                print(f"   ⚠️ Headers [{i+1}] → {r.status_code}: {r.text[:120]}")
        except Exception as e:
            print(f"   ❌ Headers [{i+1}] → Exception: {e}")
    print("❌ Tất cả headers đều thất bại cho POST Tieulam")
    return None


def _tieulam_http_get(url, timeout=10):
    """GET với retry headers."""
    for headers in TIEULAM_HEADER_CANDIDATES:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 404:
                return None
        except Exception:
            continue
    return None


def _tieulam_check_url(url, timeout=5):
    for headers in TIEULAM_HEADER_CANDIDATES[:2]:
        try:
            r = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            if r.status_code < 400:
                return True
        except Exception:
            continue
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
            total_pages = -(-data["total"] // limit)  # ceiling division
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

    # Fallback dùng stream_key nếu chưa có stream_url
    if not md["stream_url"] and md["stream_key"]:
        for domain in TIEULAM_STREAM_DOMAINS:
            test_url = f"{domain}{md['stream_key']}/playlist.m3u8"
            if _tieulam_check_url(test_url):
                md["stream_url"] = test_url
                break
        if not md["stream_url"]:
            md["stream_url"] = f"{TIEULAM_STREAM_DOMAINS[0]}{md['stream_key']}/playlist.m3u8"

    # Thử lấy từ mảng streams
    for s in (raw.get("streams") or []):
        url   = s.get("url", "")
        stype = s.get("type", "")
        if url and (stype in ("hls", "m3u8") or ".m3u8" in url):
            md["stream_url"] = url
            break

    return md


def _tieulam_fetch_detail_links(match_id, match_title):
    """Gọi API detail để lấy hd_1, hd_2, hd_3, source_live..."""
    url = TIEULAM_DETAIL_URL.format(match_id=match_id)
    data = _tieulam_http_get(url)
    if not data:
        print(f"   ❌ Không lấy được detail {match_title}")
        return []

    match_obj = data.get("data") or data
    links = []

    # Các field link Java đề cập
    for field, label in [("hd_1", "HD1"), ("hd_2", "HD2"), ("hd_3", "HD3"), ("source_live", "Source")]:
        val = match_obj.get(field, "")
        if val and isinstance(val, str) and val.startswith("http"):
            links.append({"name": label, "url": val})

    # Mảng streams nếu có
    for s in (match_obj.get("streams") or []):
        u = s.get("url", "")
        n = s.get("name") or s.get("type") or "Stream"
        if u:
            links.append({"name": n, "url": u})

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
    """UTC string → giờ Việt Nam UTC+7 dạng HH:MM"""
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

            if m["stream_links"]:
                for lnk in m["stream_links"]:
                    lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{base_name} [{lnk["name"]}]')
                    lines.append(lnk["url"])
            elif m["stream_url"]:
                lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}",{base_name}')
                lines.append(m["stream_url"])
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# TIEULAM: hàm chính (thay thế process_source cho nguồn Tieulam)
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

    # Chỉ lấy FOOTBALL
    football = [m for m in raw_all if (m.get("desc") or "").strip().upper() == "FOOTBALL"]
    print(f"⚽ FOOTBALL: {len(football)}/{len(raw_all)} trận")

    parsed = [_tieulam_parse_match(r, i) for i, r in enumerate(football)]

    # Lọc cửa sổ thời gian: 12h trước → 3h sau
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

    # Phân loại LIVE / UPCOMING
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

    # Gọi API detail với trận sắp/đang diễn ra (≤ 10 phút)
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

    # Ghi file M3U
    m3u_content = _tieulam_build_m3u(live_matches, upcoming_matches)
    Path(output_file).write_text(m3u_content, encoding="utf-8")
    total = len(live_matches) + len(upcoming_matches)
    print(f"🎉 Đã tạo {output_file} ({total} trận)")

    # Trả về entries tương thích generate_all_playlist()
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

    matches = (
        root.get("data")
        or root.get("matches")
        or []
    )
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

        blv = (
            commentator.get("nickname")
            or commentator.get("username")
            or "BLV"
        )

        logo = (
            match.get("homeClub", {})
            .get("logoUrl")
        )

        streams = [
            commentator.get("streamSourceFhd"),
            commentator.get("streamSourceHd"),
            commentator.get("streamSourceSd")
        ]

        qualities = [
            "FHD",
            "HD",
            "SD"
        ]

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
                attrs = [
                    f'group-title="{e["match"]}"'
                ]

                if e["img"]:
                    attrs.append(
                        f'tvg-logo="{e["img"]}"'
                    )

                attr_line = " ".join(attrs)

                f.write(
                    f'#EXTINF:-1 {attr_line},{e["name"]}\n'
                )

                f.write(
                    f'{e["url"]}\n'
                )

        print(
            f"🎉 Đã tạo {output_file} ({len(all_entries)} links)"
        )

    return all_entries

def process_source(name, base_url, output_file):
    print(f"\n==============================")
    print(f"🛰️  Đang xử lý nguồn {name}: {base_url}")
    print(f"==============================")

    root = fetch_json(base_url)
    if not root:
        print(f"❌ Không lấy được dữ liệu từ {base_url}")
        return []

    channels = extract_channels(root)
    if not channels:
        print(f"⚠️  Không tìm thấy channel nào trong {name}")
        return []

    all_entries = []

    for ch in channels:
        match_name = ch.get("name", "NoName")
        img = (ch.get("image") or {}).get("url")

        # Giờ thi đấu
        time_str = ch.get("start_time") or ch.get("time") or ""
        if time_str:
            try:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                local_time = dt.astimezone().strftime("%H:%M")
            except Exception:
                local_time = time_str
            match_label = f"{match_name} - {local_time}"
        else:
            match_label = match_name

        print(f"\n📺 {match_label}")
        match_entries = []

        for source in ch.get("sources", []):
            for content in source.get("contents", []):
                for stream in content.get("streams", []):
                    blv_name = stream.get("name", "").strip() or "No BLV"
                    img_stream = (stream.get("image") or {}).get("url")

                    # --- 1️⃣ Xử lý kiểu cũ: có remote_data ---
                    remote_data = stream.get("remote_data")
                    if remote_data and isinstance(remote_data, dict):
                        remote_url = remote_data.get("url")
                        if remote_url:
                            links = fetch_stream_links(remote_url)
                            for link in links:
                                match_entries.append({
                                    "source": name,
                                    "match": match_label,
                                    "name": f"{match_label} [{blv_name} - {link['name']}]",
                                    "url": link["url"],
                                    "referer": link["referer"],
                                    "img": img or img_stream
                                })

                    # --- 2️⃣ Xử lý kiểu mới: có stream_links trực tiếp ---
                    elif "stream_links" in stream:
                        for s in stream["stream_links"]:
                            url = s.get("url")
                            if not url:
                                continue
                            match_entries.append({
                                "source": name,
                                "match": match_label,
                                "name": f"{match_label} [{s.get('name', blv_name)}]",
                                "url": url,
                                "referer": None,
                                "img": img or img_stream
                            })

        if not match_entries:
            print("   ⚠️  Không có stream hợp lệ.")
            continue

        all_entries.extend(match_entries)

    # Viết file riêng
    if all_entries:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for e in all_entries:
                attrs = [f'group-title="{e["match"]}"']

                # Bổ sung tùy chọn referer cho VLC
                if e["referer"]:
                    f.write(f'#EXTVLCOPT:http-referrer={e["referer"]}\n')
                    # Tùy chọn referer (KHÔNG phải http-referrer) vẫn được giữ trong EXTINF
                    attrs.append(f'referer="{e["referer"]}"')
                if e["img"]:
                    attrs.append(f'tvg-logo="{e["img"]}"')
                attr_line = " ".join(attrs)
                f.write(f'#EXTINF:-1 {attr_line},{e["name"]}\n')
                f.write(f'{e["url"]}\n')
        print(f"🎉 Đã tạo xong file: {output_file} ({len(all_entries)} links)")
    else:
        print(f"⚠️ Không có link hợp lệ cho {name}")

    return all_entries

def process_m3u_source(name, url, output_file, keep_original=False):
    """Xử lý nguồn M3U và GIỮ NGUYÊN toàn bộ nội dung"""
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
    
    # Biến để lưu trạng thái
    current_extinf = None
    current_options = []  # Lưu các #EXTVLCOPT
    current_comments = []  # Lưu các comment
    current_url = None
    
    # Biến đếm để theo dõi
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
            
        if line.startswith("#EXTM3U"):
            all_entries.append({
                "type": "header",
                "line": line
            })
            i += 1
            continue
            
        # Lưu các dòng #EXTVLCOPT
        if line.startswith("#EXTVLCOPT"):
            current_options.append(line)
            i += 1
            continue
            
        # Lưu các dòng comment (không phải EXTINF)
        if line.startswith("#") and not line.startswith("#EXTINF"):
            current_comments.append(line)
            i += 1
            continue
            
        # Xử lý #EXTINF
        if line.startswith("#EXTINF"):
            current_extinf = line
            i += 1
            continue
            
        # Xử lý URL
        if not line.startswith("#") and current_extinf:
            current_url = line
            i += 1
            
            # Tạo entry với đầy đủ thông tin
            entry = {
                "type": "stream",
                "extinf": current_extinf,
                "url": current_url,
                "options": current_options.copy(),
                "comments": current_comments.copy()
            }
            
            # Reset cho entry tiếp theo
            all_entries.append(entry)
            current_extinf = None
            current_url = None
            current_options = []
            current_comments = []
            continue
        
        i += 1

    # Nếu có EXTINF nhưng không có URL (ít xảy ra)
    if current_extinf:
        entry = {
            "type": "stream",
            "extinf": current_extinf,
            "url": None,
            "options": current_options,
            "comments": current_comments
        }
        all_entries.append(entry)

    # Ghi file riêng (giữ nguyên hoàn toàn)
    if all_entries:
        with open(output_file, "w", encoding="utf-8") as f:
            for entry in all_entries:
                if entry["type"] == "header":
                    f.write(entry["line"] + "\n")
                elif entry["type"] == "stream":
                    # Ghi comment
                    for comment in entry["comments"]:
                        f.write(comment + "\n")
                    # Ghi EXTINF
                    f.write(entry["extinf"] + "\n")
                    # Ghi options (nếu có)
                    for opt in entry["options"]:
                        f.write(opt + "\n")
                    # Ghi URL
                    if entry["url"]:
                        f.write(entry["url"] + "\n")
        
        print(f"🎉 Đã tạo file M3U: {output_file} ({len([e for e in all_entries if e['type'] == 'stream'])} links)")
    else:
        print(f"⚠️ Không có link hợp lệ trong {name}")

    return all_entries
    
def generate_all_playlist(all_data):
    print("\n==============================")
    print("🧩 Gộp tất cả nguồn thành all.m3u")
    print("==============================")

    with open(ALL_OUTPUT, "w", encoding="utf-8") as f:
        # Không thêm #EXTM3U ở đây nếu đã có trong các entry
        has_header = False
        
        for e in all_data:
            # ✅ Nếu là header, ghi nguyên
            if e.get("type") == "header":
                f.write(e["line"] + "\n")
                has_header = True
                continue
            
            # ✅ Nếu là stream với extinf gốc
            if "extinf" in e and e["extinf"]:
                # Ghi comments (nếu có)
                for comment in e.get("comments", []):
                    f.write(comment + "\n")
                
                # Ghi EXTINF gốc
                f.write(e["extinf"] + "\n")
                
                # Ghi options (nếu có)
                for opt in e.get("options", []):
                    f.write(opt + "\n")
                
                # Ghi URL
                if e.get("url"):
                    f.write(e["url"] + "\n")
            
            # ❌ Không có extinf (dữ liệu từ JSON) - xử lý thông thường
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
    
    # Nếu không có header, thêm vào đầu file
    if not has_header:
        with open(ALL_OUTPUT, "r+", encoding="utf-8") as f:
            content = f.read()
            f.seek(0, 0)
            f.write("#EXTM3U\n" + content)

    print(f"🎉 Đã tạo xong file tổng: {ALL_OUTPUT} ({len(all_data)} links)")
    
def main():
    all_entries = []
    Path("./").mkdir(exist_ok=True)
    
    # Extra M3U sources
    for src in EXTRA_SOURCES:
        keep_original = src.get("keep_original", False)
        entries = process_m3u_source(
            src["name"],
            src["url"],
            src["output"],
            keep_original=keep_original
        )
        all_entries.extend(entries)
        
    # JSON/remote data sources
    for src in SOURCES:
        if src["name"] == "Tieulam":
            entries = process_tieulam_source(
                src["name"],
                src["url"],
                src["output"]
            )
        elif src["name"] == "Tamquoc":
            entries = process_tamquoc_source(
                src["name"],
                src["url"],
                src["output"]
            )
        else:
            entries = process_source(
                src["name"],
                src["url"],
                src["output"]
            )
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
