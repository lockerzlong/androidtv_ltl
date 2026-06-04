import requests
import json
from datetime import datetime
from pathlib import Path

# 📂 Đặt thư mục lưu file đầu ra
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

SOURCES = [
    {"name": "Socolive", "url": "https://json.vnres.co/all_live_rooms.json", "output": OUTPUT_DIR /"socolive.m3u"},
    {"name": "Tamquoc", "url": "https://sv.tamquoctv.xyz/internal/api/matches", "output": OUTPUT_DIR /"tamquoc.m3u"},
]

EXTRA_SOURCES = [
    {"name": "TruyenHinh_2", "url": "https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", "output": OUTPUT_DIR / "nhadai_2.m3u"},
    {"name": "TruyenHinh_3", "url": "https://raw.githubusercontent.com/HaNoiIPTV/HaNoiIPTV.m3u/refs/heads/master/Danh%20s%C3%A1ch%20k%C3%AAnh/G%C3%B3i%20ch%C3%ADnh%20th%E1%BB%A9c/H%C3%A0%20N%E1%BB%99i%20IPTV.m3u", "output": OUTPUT_DIR / "nhadai_3.m3u"},
]

ALL_OUTPUT = OUTPUT_DIR / "all.m3u"


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


def fetch_jsonp(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.google.com/",
            "Origin": "https://json.vnres.co",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        # Thử dùng session
        session = requests.Session()
        session.headers.update(headers)
        
        # Thêm cookie nếu cần
        session.cookies.set("__cf_bm", "dummy_value")
        
        r = session.get(url, timeout=30, allow_redirects=True)
        
        if r.status_code == 403:
            print(f"⚠️ Vẫn bị 403, thử phương pháp khác...")
            # Thử dùng requests với tham số khác
            r = requests.get(url, headers=headers, timeout=30, verify=False)
        
        r.raise_for_status()
        
        text = r.text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        
        if start != -1 and end != 0:
            json_text = text[start:end]
            return json.loads(json_text)
        
        return None
        
    except Exception as e:
        print(f"❌ JSONP error {url}: {e}")
        return None
        
def process_socolive_source(name, url, output_file):
    print(f"\n==============================")
    print(f"🛰️ Đang xử lý Socolive")
    print(f"==============================")

    # Lấy dữ liệu JSONP
    root = fetch_jsonp(url)
    
    if not root:
        print("❌ Không lấy được dữ liệu từ Socolive")
        return []

    data = root.get("data", {})
    print(f"📊 Tìm thấy {len(data)} groups")
    
    all_entries = []

    for group_name, group in data.items():
        if not isinstance(group, list):
            continue
            
        print(f"📁 Group {group_name}: {len(group)} rooms")
        
        for room in group:
            room_num = room.get("roomNum")
            if not room_num:
                continue

            # Lấy chi tiết stream từ mỗi room
            detail_url = f"https://json.vnres.co/room/{room_num}/detail.json"
            detail = fetch_jsonp(detail_url)
            
            if not detail:
                print(f"⚠️ Không lấy được detail cho room {room_num}")
                continue

            room_data = detail.get("data", {}).get("room", {})
            stream_data = detail.get("data", {}).get("stream", {})

            title = room_data.get("title", "Unknown Match")
            cover = room_data.get("cover")
            blv = room_data.get("anchor", {}).get("nickName", "BLV")

            # Lấy các quality stream
            streams = [
                ("FHD", stream_data.get("fhdM3u8")),
                ("HD", stream_data.get("hdM3u8")),
                ("SD", stream_data.get("m3u8"))
            ]

            for quality, stream_url in streams:
                if not stream_url:
                    continue

                all_entries.append({
                    "source": name,
                    "match": title,
                    "name": f"{title} [{blv} - {quality}]",
                    "url": stream_url,
                    "referer": None,
                    "img": cover
                })

    print(f"📊 Tổng số links Socolive: {len(all_entries)}")
    
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
    """Xử lý nguồn .m3u có chứa |Referer=..."""
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
    print("🚀 Bắt đầu tạo playlist IPTV...")
    all_entries = []

    # Xử lý các nguồn JSON
    for src in SOURCES:
        if src["name"] == "Tamquoc":
            entries = process_tamquoc_source(src["name"], src["url"], src["output"])
        elif src["name"] == "Socolive":
            entries = process_socolive_source(src["name"], src["url"], src["output"])
        else:
            entries = process_source(src["name"], src["url"], src["output"])
        
        all_entries.extend(entries)
        print(f"✅ Đã xử lý xong {src['name']}: {len(entries)} links")

    # Xử lý các nguồn M3U
    for src in EXTRA_SOURCES:
        entries = process_m3u_source(src["name"], src["url"], src["output"])
        all_entries.extend(entries)
        print(f"✅ Đã xử lý xong {src['name']}: {len(entries)} links")

    # Tạo file tổng hợp
    if all_entries:
        generate_all_playlist(all_entries)
        print(f"\n🎉 THÀNH CÔNG! Tổng số links: {len(all_entries)}")
    else:
        print("❌ Không có dữ liệu hợp lệ nào để gộp.")

    # Kiểm tra file đầu ra
    m3u_files = list(OUTPUT_DIR.glob("*.m3u"))
    if m3u_files:
        print(f"\n📁 Các file đã tạo:")
        for f in m3u_files:
            print(f"   - {f.name}")
    else:
        print("⚠️ Không có file nào được tạo trong output/")

    # Lưu thống kê
    stats_file = OUTPUT_DIR / "stats.txt"
    with open(stats_file, "w", encoding="utf-8") as f:
        f.write(f"Total links: {len(all_entries)}\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


if __name__ == "__main__":
    main()
