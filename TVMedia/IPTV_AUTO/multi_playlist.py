import requests
import json
from datetime import datetime
from pathlib import Path

# 📂 Đặt thư mục lưu file đầu ra
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

SOURCES = [
    {"name": "LuongSon", "url": "https://api-ls.cdnokvip.com/api/get-livestream-group", "output": OUTPUT_DIR /"luongson.m3u"},    
    {"name": "Tamquoc", "url": "https://sv.tamquoctv.xyz/internal/api/matches", "output": OUTPUT_DIR /"tamquoc.m3u"},
]

#EXTRA_SOURCES = [
#    {"name": "TruyenHinh_2", "url": "https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", "output": OUTPUT_DIR / "nhadai_2.m3u"},
#    {"name": "TruyenHinh_3", "url": "https://raw.githubusercontent.com/HaNoiIPTV/HaNoiIPTV.m3u/refs/heads/master/Danh%20s%C3%A1ch%20k%C3%AAnh/G%C3%B3i%20ch%C3%ADnh%20th%E1%BB%A9c/H%C3%A0%20N%E1%BB%99i%20IPTV.m3u", "output": OUTPUT_DIR / "nhadai_3.m3u"},
#]

ALL_OUTPUT = OUTPUT_DIR / "all.m3u"


def fetch_json(url):
    """Lấy JSON từ URL bằng phương thức GET"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        r = requests.get(url, headers=headers, timeout=15)
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
    

def process_tamquoc_source(name, url, output_file):
    """Xử lý nguồn TamQuocTV"""
    print(f"\n==============================")
    print(f"🛰️  Đang xử lý TamQuocTV: {url}")
    print(f"==============================")

    root = fetch_json(url)
    if not root:
        return []

    matches = root.get("data", [])
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
    else:
        print(f"⚠️ Không có link nào cho {name}")

    return all_entries


def process_luongson_source(name, url, output_file):
    """Xử lý nguồn LuongSonTV"""
    print(f"\n==============================")
    print(f"🛰️  Đang xử lý LuongSonTV: {url}")
    print(f"==============================")

    # Lấy danh sách trận đấu
    root = fetch_json(url)
    if not root:
        return []

    value = root.get("value", {})
    datas = value.get("datas", [])
    
    if not datas:
        print("⚠️ Không có trận đấu nào")
        return []

    all_entries = []
    total_matches = len(datas)
    print(f"📊 Tìm thấy {total_matches} trận đấu")

    for idx, match in enumerate(datas):
        home_name = match.get("homeName", "Unknown")
        away_name = match.get("awayName", "Unknown")
        title = f"{home_name} vs {away_name}"
        
        match_time = match.get("matchTime", 0)
        try:
            if match_time:
                dt = datetime.fromtimestamp(match_time)
                local_time = dt.strftime("%H:%M")
                match_label = f"{title} - {local_time}"
            else:
                match_label = title
        except:
            match_label = title

        commentator = match.get("commentator", "BLV")
        blv = commentator if commentator else "BLV"
        
        home_logo = match.get("homeLogo", "")
        away_logo = match.get("awayLogo", "")
        logo = home_logo or away_logo
        
        league_name = match.get("leagueName", "")
        
        # Lấy slug để gọi API detail
        slug = match.get("slugUrl")
        if not slug:
            print(f"⚠️ [{idx+1}/{total_matches}] Không có slug cho {title}")
            continue
            
        print(f"📺 [{idx+1}/{total_matches}] {match_label}")
        
        # Gọi API match-detail-slug
        detail_url = f"https://api-ls.cdnokvip.com/api/match-detail-slug?slug={slug}"
        detail = fetch_json(detail_url)
        
        if not detail:
            print(f"   ❌ Không lấy được detail")
            continue
            
        # Lấy link stream từ response
        value_detail = detail.get("value", {})
        datas_detail = value_detail.get("datas", {})
        
        # Link stream HLS (m3u8) - ưu tiên dùng linkLive
        stream_url = datas_detail.get("linkLive") or datas_detail.get("linkLiveFlv")
        
        if not stream_url:
            print(f"   ⚠️ Không tìm thấy link stream")
            continue

        # Tạo tên kênh với đầy đủ thông tin
        channel_name = f"{match_label} [{blv}]"
        if league_name:
            channel_name = f"[{league_name}] {channel_name}"

        all_entries.append({
            "source": name,
            "match": match_label,
            "name": channel_name,
            "url": stream_url,
            "referer": None,
            "img": logo
        })
        
        print(f"   ✅ Đã lấy được link stream")

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

        print(f"\n🎉 Đã tạo {output_file} ({len(all_entries)} links)")
    else:
        print(f"\n⚠️ Không có link nào cho {name}")

    return all_entries


def process_source(name, base_url, output_file):
    """Xử lý nguồn JSON có cấu trúc channels"""
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

        time_str = ch.get("start_time") or ch.get("time") or ""
        if time_str:
            try:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                local_time = dt.astimezone().strftime("%H:%M")
                match_label = f"{match_name} - {local_time}"
            except Exception:
                match_label = match_name
        else:
            match_label = match_name

        print(f"\n📺 {match_label}")
        match_entries = []

        for source in ch.get("sources", []):
            for content in source.get("contents", []):
                for stream in content.get("streams", []):
                    blv_name = stream.get("name", "").strip() or "No BLV"
                    img_stream = (stream.get("image") or {}).get("url")

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

    if all_entries:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for e in all_entries:
                attrs = [f'group-title="{e["match"]}"']
                if e["referer"]:
                    f.write(f'#EXTVLCOPT:http-referrer={e["referer"]}\n')
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


def process_m3u_source(name, url, output_file):
    """Xử lý nguồn .m3u có chứa |Referer=..."""
    print(f"\n==============================")
    print(f"🛰️  Đang xử lý M3U nguồn {name}: {url}")
    print(f"==============================")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        lines = r.text.splitlines()
    except Exception as e:
        print(f"❌ Không tải được M3U từ {url}: {e}")
        return []

    all_entries = []
    current_title = "Unknown"

    for line in lines:
        if line.startswith("#EXTINF"):
            current_title = line.split(",", 1)[-1].strip()
        elif line.strip() and not line.startswith("#"):
            link = line.strip()
            ref = None
            if "|Referer=" in link:
                link, ref = link.split("|Referer=", 1)
            all_entries.append({
                "source": name,
                "match": name,
                "name": current_title,
                "url": link,
                "referer": ref,
                "img": None,
            })

    if all_entries:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for e in all_entries:
                if e["referer"]:
                    f.write(f'#EXTVLCOPT:http-referrer={e["referer"]}\n')
                f.write(f'#EXTINF:-1 group-title="{name}",{e["name"]}\n')
                f.write(f'{e["url"]}\n')
        print(f"🎉 Đã tạo file M3U chuẩn VLC: {output_file} ({len(all_entries)} links)")
    else:
        print(f"⚠️ Không có link hợp lệ trong {name}")

    return all_entries


def generate_all_playlist(all_data):
    """Gộp tất cả playlist thành 1 file"""
    print("\n==============================")
    print("🧩 Gộp tất cả nguồn thành all.m3u (group theo nguồn)")
    print("==============================")
    
    with open(ALL_OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in all_data:
            group = e["source"]
            attrs = [f'group-title="{group}"']
            
            if e["referer"]:
                f.write(f'#EXTVLCOPT:http-referrer={e["referer"]}\n')
                attrs.append(f'referer="{e["referer"]}"')
            if e["img"]:
                attrs.append(f'tvg-logo="{e["img"]}"')
            
            attr_line = " ".join(attrs)
            f.write(f'#EXTINF:-1 {attr_line},{e["name"]}\n')
            f.write(f'{e["url"]}\n')

    print(f"🎉 Đã tạo xong file tổng: {ALL_OUTPUT} ({len(all_data)} links)")


def main():
    print("=" * 60)
    print("🚀 IPTV Playlist Generator")
    print("=" * 60)
    print(f"📅 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_entries = []
    Path("./").mkdir(exist_ok=True)

    # Xử lý các nguồn JSON
    for src in SOURCES:
        if src["name"] == "Tamquoc":
            entries = process_tamquoc_source(src["name"], src["url"], src["output"])
        elif src["name"] == "LuongSon":
            entries = process_luongson_source(src["name"], src["url"], src["output"])
        else:
            entries = process_source(src["name"], src["url"], src["output"])

        all_entries.extend(entries)
        print(f"✅ {src['name']}: {len(entries)} links")

    # Xử lý các nguồn M3U
    for src in EXTRA_SOURCES:
        entries = process_m3u_source(src["name"], src["url"], src["output"])
        all_entries.extend(entries)
        print(f"✅ {src['name']}: {len(entries)} links")

    # Tạo file tổng hợp
    if all_entries:
        generate_all_playlist(all_entries)
        print(f"\n🎉 THÀNH CÔNG! Tổng số links: {len(all_entries)}")
    else:
        print("❌ Không có dữ liệu hợp lệ nào để gộp.")

    # Kiểm tra file đầu ra
    m3u_files = list(OUTPUT_DIR.glob("*.m3u"))
    if m3u_files:
        print(f"\n📁 Các file đã tạo ({len(m3u_files)} files):")
        for f in sorted(m3u_files):
            size = f.stat().st_size
            print(f"   - {f.name} ({size:,} bytes)")
    else:
        print("⚠️ Không có file nào được tạo trong output/")

    # Lưu thống kê
    stats_file = OUTPUT_DIR / "stats.txt"
    with open(stats_file, "w", encoding="utf-8") as f:
        f.write(str(len(all_entries)))

    print("\n" + "=" * 60)
    print("✅ Kết thúc!")
    print("=" * 60)


if __name__ == "__main__":
    main()
