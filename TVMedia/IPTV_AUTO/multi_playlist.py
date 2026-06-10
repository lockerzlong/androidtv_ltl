import requests
import json
from datetime import datetime
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
    # {"name": "TruyenHinh", "url": "https://raw.githubusercontent.com/lockerzlong/androidtv_ltl/main/TVMedia/update/IPTV", "output": OUTPUT_DIR / "1truyenhinh.m3u"},
    {"name": "Tamquoc", "url": "https://sv.tamquoctv.xyz/internal/api/matches", "output": OUTPUT_DIR /"tamquoc.m3u"},
]
# 🆕 Các nguồn kiểu M3U trực tiếp (ví dụ: Cakhia)
EXTRA_SOURCES = [
    # {"name": "Cakhia", "url": "http://sharing.gotdns.ch:8091/cakhia.php", "output": OUTPUT_DIR / "cakhia.m3u"},# chưa chạy được, chạy với vlc thì ok    
    # {"name": "LuongSon_2", "url": "http://sharing.gotdns.ch:8091/luongsontv.php", "output": OUTPUT_DIR / "luongson_share.m3u"}, 
    # {"name": "Socolive_2", "url": "http://sharing.gotdns.ch:8091/socolive.php", "output": OUTPUT_DIR / "Socolive_share.m3u"},
    # {"name": "TruyenHinh_2", "url": "https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", "output": OUTPUT_DIR / "nhadai_2.m3u"},
    # {"name": "TruyenHinh_3", "url": "https://raw.githubusercontent.com/HaNoiIPTV/HaNoiIPTV.m3u/refs/heads/master/Danh%20s%C3%A1ch%20k%C3%AAnh/G%C3%B3i%20ch%C3%ADnh%20th%E1%BB%A9c/H%C3%A0%20N%E1%BB%99i%20IPTV.m3u", "output": OUTPUT_DIR / "nhadai_3.m3u"},
    {"name": "TruyenHinh", "url": "https://raw.githubusercontent.com/lockerzlong/androidtv_ltl/main/TVMedia/update/IPTV", "output": OUTPUT_DIR / "truyenhinh.m3u"},
    
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

def process_m3u_source(name, url, output_file):
    """Xử lý nguồn M3U và GIỮ NGUYÊN toàn bộ EXTINF"""
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

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_extinf = line

        elif line.startswith("#"):
            continue

        else:
            link = line

            ref = None

            if "|Referer=" in link:
                link, ref = link.split("|Referer=", 1)

            all_entries.append({
                "source": name,
                "extinf": current_extinf,
                "url": link,
                "referer": ref
            })

    if all_entries:
        with open(output_file, "w", encoding="utf-8") as f:

            f.write("#EXTM3U\n")

            for e in all_entries:

                if e["referer"]:
                    f.write(
                        f'#EXTVLCOPT:http-referrer={e["referer"]}\n'
                    )

                f.write(e["extinf"] + "\n")
                f.write(e["url"] + "\n")

        print(
            f"🎉 Đã tạo file M3U chuẩn VLC: {output_file} ({len(all_entries)} links)"
        )

    else:
        print(f"⚠️ Không có link hợp lệ trong {name}")

    return all_entries
    
def generate_all_playlist(all_data):
    print("\n==============================")
    print("🧩 Gộp tất cả nguồn thành all.m3u")
    print("==============================")

    with open(ALL_OUTPUT, "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for e in all_data:

            if "extinf" in e:
                if e["referer"]:
                    f.write(
                        f'#EXTVLCOPT:http-referrer={e["referer"]}\n'
                    )

                f.write(e["extinf"] + "\n")
                f.write(e["url"] + "\n")

            else:
                attrs = [
                    f'group-title="{e["source"]}"'
                ]

                if e["referer"]:
                    f.write(
                        f'#EXTVLCOPT:http-referrer={e["referer"]}\n'
                    )
                    attrs.append(
                        f'referer="{e["referer"]}"'
                    )

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
        f"🎉 Đã tạo xong file tổng: {ALL_OUTPUT} ({len(all_data)} links)"
    )
    
def main():
    all_entries = []
    Path("./").mkdir(exist_ok=True)
    
    # Extra M3U sources
    for src in EXTRA_SOURCES:
        entries = process_m3u_source(
            src["name"],
            src["url"],
            src["output"]
        )
        all_entries.extend(entries)
        
    # JSON/remote data sources
    for src in SOURCES:
        if src["name"] == "Tamquoc":
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
