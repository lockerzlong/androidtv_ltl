import requests
import json
from datetime import datetime
from pathlib import Path
import os

# 📂 Đặt thư mục lưu file đầu ra
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Cloudflare Worker URL (để bypass 403)
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL", "")

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
    """Lấy JSON từ URL thông thường"""
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


def fetch_jsonp(url):
    """Lấy JSONP từ URL, sử dụng Cloudflare Worker nếu cần"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*",
            "Referer": "https://socolive.com/",
            "Origin": "https://socolive.com",
        }
        
        # Thử dùng Cloudflare Worker nếu có
        if CLOUDFLARE_WORKER_URL:
            proxy_url = f"{CLOUDFLARE_WORKER_URL}?url={url}"
            print(f"🔄 Dùng Cloudflare Worker proxy...")
            try:
                r = requests.get(proxy_url, timeout=30)
                if r.status_code == 200:
                    text = r.text.strip()
                    # Xử lý JSONP
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end != 0:
                        return json.loads(text[start:end])
            except Exception as e:
                print(f"⚠️ Cloudflare Worker thất bại: {e}")
        
        # Fallback: gọi trực tiếp
        print(f"🔄 Thử gọi trực tiếp...")
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        text = r.text.strip()
        
        # Xử lý JSONP
        if text.startswith("{"):
            return json.loads(text)
        
        start = text.find("(")
        end = text.rfind(")")
        if start != -1 and end != -1:
            return json.loads(text[start + 1:end])
        
        # Tìm JSON thuần trong text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != 0:
            return json.loads(text[start:end])
        
        print(f"❌ Unknown format: {url}")
        return None
        
    except Exception as e:
        print(f"❌ JSONP error {url}: {e}")
        return None


def fetch_stream_links(remote_url):
    """Lấy danh sách link stream từ remote_data"""
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


def process_tamquoc_source(name, url, output_file):
    """Xử lý nguồn TamQuocTV"""
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


def process_socolive_source(name, url, output_file):
    """Xử lý nguồn Socolive"""
    print(f"\n==============================")
    print(f"🛰️ Đang xử lý Socolive")
    print(f"==============================")

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

            detail_url = f"https://json.vnres.co/room/{room_num}/detail.json"
            detail = fetch_jsonp(detail_url)
            
            if not detail:
                continue

            room_data = detail.get("data", {}).get("room", {})
            stream_data = detail.get("data", {}).get("stream", {})

            title = room_data.get("title", "Unknown Match")
            cover = room_data.get("cover")
            blv = room_data.get("anchor", {}).get("nickName", "BLV")

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
    """Xử lý nguồn .m3u trực tiếp"""
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
        print(f"🎉 Đã tạo file M3U: {output_file} ({len(all_entries)} links)")
    else:
        print(f"⚠️ Không có link hợp lệ trong {name}")

    return all_entries


def generate_all_playlist(all_data):
    """Gộp tất cả playlist thành 1 file"""
    print("\n==============================")
    print("🧩 Gộp tất cả nguồn thành all.m3u")
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

    print(f"🎉 Đã tạo file tổng: {ALL_OUTPUT} ({len(all_data)} links)")


def main():
    print("🚀 Bắt đầu tạo playlist IPTV...")
    print(f"📅 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_entries = []

    # Xử lý các nguồn JSON
    for src in SOURCES:
        if src["name"] == "Tamquoc":
            entries = process_tamquoc_source(src["name"], src["url"], src["output"])
        elif src["name"] == "Socolive":
            entries = process_socolive_source(src["name"], src["url"], src["output"])
        else:
            # Nếu có thêm nguồn JSON khác
            entries = []
        
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
        for f in m3u_files:
            size = f.stat().st_size
            print(f"   - {f.name} ({size:,} bytes)")
    else:
        print("⚠️ Không có file nào được tạo trong output/")

    # Lưu thống kê
    stats_file = OUTPUT_DIR / "stats.txt"
    with open(stats_file, "w", encoding="utf-8") as f:
        f.write(f"Total links: {len(all_entries)}\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Sources: {', '.join([s['name'] for s in SOURCES + EXTRA_SOURCES])}\n")


if __name__ == "__main__":
    main()
