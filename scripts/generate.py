#!/usr/bin/env python3
"""Generates gruvbox-themed SVG stat cards for the profile README.
No third-party services: reads github.com contribution calendar + REST API."""
import json, os, re, sys, urllib.request, html as H
from datetime import date, timedelta

USER = os.environ.get("GH_USER", "mshareef-git")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT_DIR", "assets/gen")
os.makedirs(OUT, exist_ok=True)

BG, BG1, BG2, BG3 = "#282828", "#3c3836", "#504945", "#1d2021"
FG, GRAY = "#ebdbb2", "#928374"
RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, AQUA = "#fb4934", "#fe8019", "#fabd2f", "#b8bb26", "#83a598", "#d3869b", "#8ec07c"
LEVELS = [BG1, "#79740e", "#98971a", GREEN, YELLOW]
FONT = "font-family=\"'JetBrains Mono','Fira Code',Menlo,Consolas,monospace\""
PROMPT = (f'<tspan fill="{GREEN}">shareef@gruvbox</tspan><tspan fill="{GRAY}">:</tspan>'
          f'<tspan fill="{BLUE}">~</tspan><tspan fill="{ORANGE}">$ </tspan>')

def get(url, accept=None):
    h = {"User-Agent": "Mozilla/5.0 profile-readme-generator"}
    if accept: h["Accept"] = accept
    if TOKEN and "api.github.com" in url: h["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def api(path):
    try: return json.loads(get("https://api.github.com" + path, "application/vnd.github+json"))
    except Exception as e:
        print("api fail", path, e, file=sys.stderr); return None

# ---------------- contribution calendar ----------------
def calendar():
    page = os.environ.get("CAL_FILE")
    page = open(page).read() if page else get(f"https://github.com/users/{USER}/contributions")
    tips = {m.group(1): m.group(2) for m in re.finditer(r'for="(contribution-day-component-\d+-\d+)"[^>]*>\s*([^<]*)', page)}
    days = []
    for t in re.finditer(r'<td[^>]*ContributionCalendar-day[^>]*>', page):
        tag = t.group(0)
        d = re.search(r'data-date="([\d-]+)"', tag); l = re.search(r'data-level="(\d)"', tag); i = re.search(r'id="([^"]+)"', tag)
        if not (d and l): continue
        n = re.match(r"(\d+) contribution", tips.get(i.group(1), "").strip()) if i else None
        days.append((date.fromisoformat(d.group(1)), int(l.group(1)), int(n.group(1)) if n else 0))
    days.sort()
    tot = re.search(r"([\d,]+)\s+contributions\s+in the last year", page)
    total = int(tot.group(1).replace(",", "")) if tot else sum(c for _, _, c in days)
    return days, total

def streaks(days):
    today = date.today(); best = cur = run = 0
    for d, _, c in days:
        run = run + 1 if c > 0 else 0; best = max(best, run)
    # current streak: walk back from latest day (today may still be empty)
    seq = [c for d, _, c in days if d <= today]
    i = len(seq) - 1
    if i >= 0 and seq[i] == 0: i -= 1
    while i >= 0 and seq[i] > 0: cur += 1; i -= 1
    return cur, best

def frame(w, h, title, body, sub=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<title>{H.escape(title)}</title><defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" x2="{w}" y1="0" y2="0">'
            f'<stop offset="0" stop-color="{RED}"/><stop offset=".25" stop-color="{ORANGE}"/><stop offset=".5" stop-color="{YELLOW}"/>'
            f'<stop offset=".75" stop-color="{GREEN}"/><stop offset="1" stop-color="{BLUE}"/></linearGradient></defs>'
            f'<rect width="{w}" height="{h}" rx="14" fill="{BG}"/><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="13" fill="none" stroke="{BG2}" stroke-width="2"/>'
            f'<rect x="1" y="1" width="{w-2}" height="4" rx="2" fill="url(#g)"/>'
            f'<text x="28" y="40" font-size="15" {FONT}>{PROMPT}<tspan fill="{FG}">{H.escape(sub or title)}</tspan></text>{body}</svg>')

# ---------------- heatmap ----------------
def heatmap(days, total):
    cell, gap, x0, y0 = 14, 3, 64, 84
    first = days[0][0]; shift = (first.weekday() + 1) % 7  # sunday-first
    cols = (len(days) + shift + 6) // 7
    w = x0 + cols * (cell + gap) + 28; h = y0 + 7 * (cell + gap) + 62
    b = ""
    for lbl, r in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        b += f'<text x="28" y="{y0 + r*(cell+gap) + 11}" font-size="11" fill="{GRAY}" {FONT}>{lbl}</text>'
    lastm = None; lastx = -99
    for k, (d, lvl, c) in enumerate(days):
        idx = k + shift; col, row = idx // 7, idx % 7
        x, y = x0 + col * (cell + gap), y0 + row * (cell + gap)
        if row == 0 and d.month != lastm and (lastm is None or d.day <= 7):
            if x - lastx >= 40:
                b += f'<text x="{x}" y="{y0-10}" font-size="11" fill="{GRAY}" {FONT}>{d.strftime("%b")}</text>'; lastx = x
            lastm = d.month
        b += (f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{LEVELS[lvl]}" opacity="0">'
              f'<title>{c} contributions on {d.isoformat()}</title>'
              f'<animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{col*0.025:.3f}s" fill="freeze"/></rect>')
    ly = y0 + 7 * (cell + gap) + 30
    b += f'<text x="28" y="{ly+11}" font-size="12" fill="{GRAY}" {FONT}>{total:,} contributions in the last year</text>'
    lx = w - 28 - 5 * (cell + 4) - 70
    b += f'<text x="{lx}" y="{ly+11}" font-size="11" fill="{GRAY}" {FONT}>less</text>'
    for i, c in enumerate(LEVELS):
        b += f'<rect x="{lx+34+i*(cell+4)}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>'
    b += f'<text x="{lx+34+5*(cell+4)+4}" y="{ly+11}" font-size="11" fill="{GRAY}" {FONT}>more</text>'
    return frame(w, h, "Contribution heatmap", b, "git log --heatmap --since=1y")

# ---------------- 30-day activity ----------------
def activity(days):
    last = days[-30:]; w, h = 900, 300; x0, x1, y0, y1 = 64, w - 36, 84, h - 52
    mx = max([c for _, _, c in last] + [4]); mx = ((mx + 3) // 4) * 4
    step = (x1 - x0) / len(last); bw = step * 0.62
    b = ""
    for i in range(5):
        v = mx * i // 4; y = y1 - (y1 - y0) * i / 4
        b += f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{BG1}" stroke-width="1"/><text x="{x0-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{GRAY}" {FONT}>{v}</text>'
    pts = []
    for i, (d, _, c) in enumerate(last):
        bh = (y1 - y0) * c / mx; x = x0 + i * step + (step - bw) / 2
        col = YELLOW if c >= mx * 0.75 else GREEN if c >= mx * 0.4 else "#98971a" if c else BG1
        if c:
            b += (f'<rect x="{x:.1f}" y="{y1}" width="{bw:.1f}" height="0" rx="3" fill="{col}"><title>{c} on {d.isoformat()}</title>'
                  f'<animate attributeName="height" from="0" to="{bh:.1f}" dur="0.6s" begin="{i*0.03:.2f}s" fill="freeze"/>'
                  f'<animate attributeName="y" from="{y1}" to="{y1-bh:.1f}" dur="0.6s" begin="{i*0.03:.2f}s" fill="freeze"/></rect>')
        else:
            b += f'<rect x="{x:.1f}" y="{y1-3}" width="{bw:.1f}" height="3" rx="1.5" fill="{BG1}"/>'
        pts.append((x + bw / 2, y1 - bh))
        if i % 5 == 0 or i == len(last) - 1:
            b += f'<text x="{x+bw/2:.1f}" y="{y1+20}" text-anchor="middle" font-size="11" fill="{GRAY}" {FONT}>{d.strftime("%d %b")}</text>'
    path = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    b += (f'<path d="{path}" fill="none" stroke="{ORANGE}" stroke-width="2" stroke-linejoin="round" stroke-dasharray="2400" stroke-dashoffset="2400" opacity=".9">'
          f'<animate attributeName="stroke-dashoffset" from="2400" to="0" dur="1.6s" begin="0.3s" fill="freeze"/></path>')
    tot = sum(c for _, _, c in last)
    b += f'<text x="{x1}" y="40" text-anchor="end" font-size="13" fill="{AQUA}" {FONT}>{tot} contributions · last 30 days</text>'
    return frame(w, h, "Activity, last 30 days", b, "git shortlog --last 30d")

# ---------------- stat tiles ----------------
def stats(total, cur, best, user):
    items = [("contributions", f"{total:,}", "last year", YELLOW), ("current streak", str(cur), "days", ORANGE), ("longest streak", str(best), "days", RED),
             ("public repos", str(user.get("public_repos", "–")), "owned", GREEN), ("stars earned", str(user.get("stars", "–")), "all repos", AQUA),
             ("followers", str(user.get("followers", "–")), "people", PURPLE)]
    w, h = 900, 250; tw, th, gx, gy = 272, 78, 14, 14; b = ""
    for i, (lab, val, sub, col) in enumerate(items):
        x = 28 + (i % 3) * (tw + gx); y = 66 + (i // 3) * (th + gy)
        b += (f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{i*0.12:.2f}s" fill="freeze"/>'
              f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="10" fill="{BG3}" stroke="{BG2}" stroke-width="1.5"/>'
              f'<rect x="{x}" y="{y+14}" width="4" height="{th-28}" rx="2" fill="{col}"/>'
              f'<text x="{x+22}" y="{y+30}" font-size="12" fill="{GRAY}" {FONT}>{lab}</text>'
              f'<text x="{x+22}" y="{y+62}" font-size="30" font-weight="700" fill="{col}" {FONT}>{val}</text>'
              f'<text x="{x+tw-16}" y="{y+62}" text-anchor="end" font-size="12" fill="{GRAY}" {FONT}>{sub}</text></g>')
    return frame(w, h, "GitHub stats", b, "gh stats --user " + USER)

# ---------------- languages ----------------
def langs(data):
    w = 900; palette = [RED, ORANGE, YELLOW, GREEN, AQUA, BLUE, PURPLE, "#a89984"]
    items = sorted(data.items(), key=lambda kv: -kv[1])[:8]; tot = sum(v for _, v in items) or 1
    h = 150 + ((len(items) + 1) // 2) * 30; b = ""; x = 28; bw = w - 56
    b += f'<clipPath id="r"><rect x="{x}" y="70" width="0" height="22" rx="6"><animate attributeName="width" from="0" to="{bw}" dur="1.2s" begin="0.2s" fill="freeze"/></rect></clipPath><g clip-path="url(#r)">'
    for i, (n, v) in enumerate(items):
        seg = bw * v / tot
        b += f'<rect x="{x:.1f}" y="70" width="{seg+1:.1f}" height="22" fill="{palette[i]}"/>'; x += seg
    b += "</g>"
    for i, (n, v) in enumerate(items):
        cx = 28 + (i % 2) * 440; cy = 128 + (i // 2) * 30
        b += (f'<circle cx="{cx+6}" cy="{cy-4}" r="6" fill="{palette[i]}"/><text x="{cx+22}" y="{cy}" font-size="14" fill="{FG}" {FONT}>{H.escape(n)}</text>'
              f'<text x="{cx+400}" y="{cy}" text-anchor="end" font-size="14" fill="{GRAY}" {FONT}>{100*v/tot:.1f}%</text>')
    return frame(w, h, "Top languages", b, "tokei --sort lines")

def main():
    days, total = calendar()
    cur, best = streaks(days)
    u = api(f"/users/{USER}") or {}
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner&sort=pushed") or []
    info = {"followers": u.get("followers", "–"), "public_repos": u.get("public_repos", "–"),
            "stars": sum(r.get("stargazers_count", 0) for r in repos) if repos else "–"}
    ld = {}
    for r in [r for r in repos if not r.get("fork")][:40]:
        l = api(f"/repos/{USER}/{r['name']}/languages") or {}
        for k, v in l.items(): ld[k] = ld.get(k, 0) + v
    if not ld: ld = {"Python": 1}
    for name, svg in (("heatmap", heatmap(days, total)), ("activity", activity(days)), ("stats", stats(total, cur, best, info)), ("langs", langs(ld))):
        open(f"{OUT}/{name}.svg", "w").write(svg)
    print("ok", total, cur, best, info, list(ld)[:5])

if __name__ == "__main__": main()
