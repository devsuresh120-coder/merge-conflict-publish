"""Turn Merge Conflict post-kit markdown files into queue/schedule.csv rows.

  python3 publish/kit_to_schedule.py --kits kit1.md kit2.md --episodes 2 3 4 8 --out queue/schedule.csv [--append]
      [--skip 1:youtube]        # episode:platform pairs already posted by hand
      [--start 2026-10-20]      # pin exact times: 2 episodes/day, same day on all 3 platforms (Europe/Berlin)
Without --start the rows go to Buffer's queue (addToQueue) and Buffer's posting schedule decides.

Kit format (one block per episode, as produced by the project):
  ## Ep N — ...
  **YouTube title:** ...
  **Description:** ...
  **TikTok:** ...
  **IG/FB:** ... (+ base hashtags #a #b)
  **Pinned comment:** ...
Videos are expected at videos/epNN.mp4.
"""
import re, csv, argparse, os

SLOTS = {"youtube": ("08:00", "18:00"), "tiktok": ("12:00", "19:30"), "facebook": ("08:30", "19:00")}  # Europe/Berlin

BASE_TAGS = "#programming #coding #programmerhumor #devlife #softwareengineer #codinglife #programmingmemes"
FOOT = "\\nMerge Conflict — Episode {n}. New episode every day."

def parse(text):
    eps = {}
    for block in re.split(r"^## Ep ", text, flags=re.M)[1:]:
        m = re.match(r"(\d+)", block)
        if not m: continue
        n = int(m.group(1)); d = {}
        ALIASES = {"yt_title": ("YouTube title", "YT title", "YT"), "yt_desc": ("Description", "YouTube description", "Desc"),
                   "tiktok": ("TikTok",), "fb": ("IG/FB", "FB/IG", "Facebook"), "comment": ("Pinned comment", "Pinned")}
        for name, keys in ALIASES.items():
            d[name] = ""
            for key in keys:
                mm = re.search(r"\*\*" + re.escape(key) + r":\*\*[ \t]*(.+(?:\n(?![ \t]*[-*]?[ \t]*\*\*)[ \t]+\S.*)*)", block)
                if mm: d[name] = " ".join(l.strip() for l in mm.group(1).splitlines()).strip(); break
        fb = d["fb"]
        mm = re.search(r"\(\+ ?base(?: hashtags)?,?\s*([^)]*)\)", fb)
        if mm:
            fb = fb[:mm.start()].strip() + "\\n" + BASE_TAGS + " " + mm.group(1).strip() + " #reels"
        d["fb"] = fb
        eps[n] = d
    return eps

def rows_for(n, d, skip, due=None):
    """due: (date, slot) -> exact Berlin times per platform, or None for addToQueue."""
    out = []
    if f"{n}:youtube" not in skip:
        out.append(dict(episode=n, file=f"videos/ep{n:02d}.mp4", platform="youtube", due_at="",
                        title=d["yt_title"], text=d["yt_desc"] + FOOT.format(n=n), comment=""))
    if f"{n}:tiktok" not in skip:
        out.append(dict(episode=n, file=f"videos/ep{n:02d}.mp4", platform="tiktok", due_at="",
                        title="", text=d["tiktok"], comment=""))
    if f"{n}:facebook" not in skip:
        out.append(dict(episode=n, file=f"videos/ep{n:02d}.mp4", platform="facebook", due_at="",
                        title="", text=d["fb"], comment=d["comment"]))
    if due:
        for r in out: r["due_at"] = f"{due[0]} {SLOTS[r['platform']][due[1]]}"
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kits", nargs="+", required=True); ap.add_argument("--episodes", nargs="+", type=int, required=True)
    ap.add_argument("--out", default="queue/schedule.csv"); ap.add_argument("--append", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("--start", default="", help="YYYY-MM-DD: first episode's day; 2 per day, exact times")
    a = ap.parse_args()
    import datetime as dt
    start = dt.date.fromisoformat(a.start) if a.start else None
    eps = {}
    for k in a.kits: eps.update(parse(open(k, encoding="utf-8").read()))
    rows = []
    for n in a.episodes:
        if n not in eps: raise SystemExit(f"episode {n} not found in kits")
        due = None
        if start:
            i = a.episodes.index(n); due = ((start + dt.timedelta(days=i // 2)).isoformat(), i % 2)
        rows += rows_for(n, eps[n], set(a.skip), due)
    mode = "a" if a.append and os.path.exists(a.out) else "w"
    with open(a.out, mode, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["episode", "file", "platform", "due_at", "title", "text", "comment"])
        if mode == "w": w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {a.out}")
