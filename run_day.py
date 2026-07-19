# -*- coding: utf-8 -*-
# run_day.py -- one command for the weekly routine.
#
#   ecore check -> build_prerace --date -> make_day_html -> copy to a synced folder
#
# It calls the existing scripts as subprocesses; no feature logic, no scoring, and no
# window rule is re-implemented here. Every guard therefore still applies exactly as it
# does when the scripts are run by hand.
#
# The one step that cannot be automated is EveryDB3's own import: its RACE FromTime
# advances to the run time on every update, so this week's entries are silently skipped
# when it sits after the Thursday/Friday delivery. If the date has no races in ecore,
# this script stops and says so instead of producing an empty page.
#
# usage:
#   python run_day.py                     # nearest race day from today, in ecore
#   python run_day.py --date 20260719
#   python run_day.py --list              # what days ecore actually holds
#   python run_day.py --drive "H:\\マイドライブ\\keiba"
#   python run_day.py --publish             # also push to GitHub Pages
#
# --publish copies the HTML into a SEPARATE git working copy (default C:\keiba-view)
# and pushes it. The working copy is deliberately not C:\keiba: slim4.db, the frozen
# measurement artifacts and the handoff records live there and must never be pushed to a
# public repository by accident. Only race_*.html and index.html reach the remote.
import argparse, datetime, os, shutil, sqlite3, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEF_ECORE = r"C:\Users\fi394\AppData\Local\EveryDB3\ecore.db"


def _ro(path):
    return sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)


def race_days(ecore, limit=12):
    """(yyyymmdd, race count) for the most recent days ecore knows about."""
    con = _ro(ecore)
    rows = con.execute(
        "SELECT Year, MonthDay, COUNT(*) FROM N_RACE GROUP BY Year, MonthDay "
        "ORDER BY Year DESC, MonthDay DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    out = []
    for y, md, n in rows:
        y, md = str(y or "").strip(), str(md or "").strip()
        if len(y) == 4 and len(md) == 4 and (y + md).isdigit():
            out.append((y + md, n))
    return out


def pick_date(ecore, today):
    """Nearest race day at or after today; if none ahead, the latest one behind."""
    days = race_days(ecore, 40)
    ahead = sorted(d for d, _ in days if d >= today)
    if ahead:
        return ahead[0], "upcoming"
    if days:
        return days[0][0], "latest available (nothing ahead of today)"
    return None, "ecore holds no races at all"


def run(cmd):
    print("\n$ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=HERE)
    return r.returncode


INDEX_HEAD = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>レース分析器</title>
<style>
 body{margin:0;background:#FBFAF7;color:#1A1D1E;line-height:1.6;
      font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN','Yu Gothic',sans-serif}
 .wrap{max-width:640px;margin:0 auto;padding:24px 20px 60px}
 h1{font-size:22px;margin:0 0 4px}
 .sub{font-size:13px;color:#5A6165;margin-bottom:18px}
 .note{border-left:3px solid #1A1D1E;background:#F2EFE8;padding:10px 14px;
       font-size:12.5px;margin-bottom:22px}
 a.day{display:block;padding:15px 16px;margin-bottom:10px;background:#fff;
       border:1px solid #E2DFD8;border-radius:9px;text-decoration:none;color:#0E7C7B;
       font-family:ui-monospace,Consolas,monospace;font-size:16px}
 a.day span{color:#5A6165;font-size:12px;float:right;font-family:inherit}
</style></head><body><div class="wrap">
<h1>レース分析器</h1>
<div class="sub">モデル評価を並べて見る道具。買い目・妙味・見送りは判定しません。</div>
<a class="day" href="guide.html" style="color:#5560D8">画面の見方<span>はじめに</span></a>
<div class="note">表示されるスコアは <b>pf_model_daily.txt</b> によるものです。
このモデルの市場相対性能は<b>未測定</b>です。旧モデルでの測定では市場相対 β=−0.110
（モデルと市場の評価が割れたとき、平均して市場のほうが正しい）でした。
収益の主張は一切しません。</div>
"""
INDEX_FOOT = "</div></body></html>\n"


def write_index(pages_dir):
    """A plain list of the race days present in the repo. No JavaScript: this page has to
    work in viewers that never run scripts."""
    days = sorted((f for f in os.listdir(pages_dir)
                   if f.startswith("race_") and f.endswith(".html")), reverse=True)
    body = []
    for f in days:
        d = f[5:13]
        label = "%s-%s-%s" % (d[:4], d[4:6], d[6:]) if len(d) == 8 and d.isdigit() else f
        body.append('<a class="day" href="%s">%s<span>開く</span></a>' % (f, label))
    if not body:
        body.append('<div class="sub">まだレースがありません。</div>')
    with open(os.path.join(pages_dir, "index.html"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(INDEX_HEAD + "\n".join(body) + INDEX_FOOT)
    return len(days)


def publish(pages_dir, src_html, html_name):
    """Copy one page into the pages repo, refresh index.html, commit and push."""
    if not os.path.isdir(os.path.join(pages_dir, ".git")):
        print("ABORT: %s is not a git working copy." % pages_dir)
        print("       git clone <your pages repo> \"%s\"" % pages_dir)
        return 5
    shutil.copy2(src_html, os.path.join(pages_dir, html_name))
    # the guide is regenerated from dashboard.html every publish, so it cannot drift
    # away from the palette and layout it is describing
    g = subprocess.run([sys.executable, "make_guide.py", "--out",
                        os.path.join(pages_dir, "guide.html")],
                       cwd=HERE, capture_output=True, text=True)
    print("  " + (g.stdout.strip().splitlines() or ["guide skipped"])[-1])
    n = write_index(pages_dir)
    print("pages: %s + index.html (%d day%s listed)" % (html_name, n, "" if n == 1 else "s"))
    for cmd in (["git", "add", "-A"],
                ["git", "commit", "-m", "publish %s" % html_name],
                ["git", "push"]):
        r = subprocess.run(cmd, cwd=pages_dir, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if r.returncode != 0:
            if cmd[1] == "commit" and "nothing to commit" in out:
                print("  (no change to commit)")
                continue
            print("ABORT: %s failed:\n%s" % (" ".join(cmd), out))
            return 5
        if out: print("  " + out.splitlines()[-1])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="YYYYMMDD (default: nearest race day)")
    ap.add_argument("--ecore", default=DEF_ECORE)
    ap.add_argument("--db", default="slim4.db")
    ap.add_argument("--model", default="pf_model_daily.txt")
    ap.add_argument("--drive", default=None,
                    help="folder to copy the finished HTML into (e.g. Google Drive)")
    ap.add_argument("--list", action="store_true", help="show the race days ecore holds")
    ap.add_argument("--publish", action="store_true",
                    help="copy the HTML into the pages repo and push it")
    ap.add_argument("--pages", default=r"C:\keiba-view",
                    help="git working copy for GitHub Pages (this tool's own repo)")
    a = ap.parse_args()

    if not os.path.exists(a.ecore):
        print("ABORT: ecore not found: %s" % a.ecore); return 2

    if a.list:
        print("race days currently in ecore (newest first):")
        for d, n in race_days(a.ecore):
            print("  %s  %d races" % (d, n))
        return 0

    today = datetime.date.today().strftime("%Y%m%d")
    date = a.date
    if not date:
        date, why = pick_date(a.ecore, today)
        if not date:
            print("ABORT: %s" % why); return 4
        print("date not given; using %s (%s)" % (date, why))
    if not (len(date) == 8 and date.isdigit()):
        print("ABORT: --date must be YYYYMMDD. got %r" % date); return 2

    con = _ro(a.ecore)
    n = con.execute("SELECT COUNT(*) FROM N_RACE WHERE Year=? AND MonthDay=?",
                    (date[:4], date[4:])).fetchone()[0]
    con.close()
    if not n:
        print("ABORT: ecore has no races on %s." % date)
        print("")
        print("  If that day IS a race day, EveryDB3 has not imported it yet.")
        print("  Known cause: the RACE FromTime in EveryDB3's update settings advances to")
        print("  the run time after every update. This week's entries are delivered on")
        print("  Thursday/Friday, so a FromTime later than that skips them silently.")
        print("")
        print("  1. EveryDB3 -> 更新設定(D)")
        print("  2. 更新データ種別 = 通常データと今週データ")
        print("  3. 更新範囲(FromTime) の RACE を配信前の日時に戻す (e.g. %s 00:00:00)"
              % (date[:4] + "/" + date[4:6] + "/" + str(max(int(date[6:]) - 6, 1)).zfill(2)))
        print("  4. 保存 -> 更新処理(R) -> 取得開始")
        print("")
        print("  Then run this again. `python run_day.py --list` shows what ecore holds.")
        return 4
    print("%s: %d race records in ecore" % (date, n))

    for f in (a.db, a.model, "build_prerace.py", "make_day_html.py", "dashboard.html",
              "make_odds_prerace.py", "make_guide.py"):
        if not os.path.exists(os.path.join(HERE, f)) and not os.path.exists(f):
            print("ABORT: not found: %s" % f); return 2

    csv = "prerace_%s.csv" % date
    rc = run([sys.executable, "build_prerace.py", "--ecore", a.ecore,
              "--date", date, "--out", csv])
    if rc != 0:
        print("\nABORT: build_prerace failed (exit %d). Nothing was written." % rc)
        return rc

    # pre-race odds are optional: they only exist while the meeting is live, and the
    # page is complete without them (panel B simply stays empty).
    odds = "odds_%s.csv" % date
    rc = run([sys.executable, "make_odds_prerace.py", "--ecore", a.ecore,
              "--date", date, "--out", odds])
    if rc != 0:
        print("\n(no pre-race odds this run; the page will show no market panel)")
        odds = None

    html = "race_%s.html" % date
    cmd = [sys.executable, "make_day_html.py", "--date", date, "--db", a.db,
           "--model", a.model, "--prerace", csv, "--ecore", a.ecore, "--out", html]
    if odds: cmd += ["--odds", odds]
    rc = run(cmd)
    if rc != 0:
        print("\nABORT: make_day_html failed (exit %d)." % rc)
        return rc

    src = os.path.join(HERE, html)
    print("")
    if a.publish:
        rc = publish(a.pages, src, html)
        if rc:
            print("      The HTML is still here: %s" % src)
            return rc
        user = os.path.basename(os.path.abspath(a.pages))
        print("published. It appears at your GitHub Pages URL within a minute or two:")
        print("  .../%s" % html)
        print("  .../index.html   (list of every day published so far)")
    if a.drive:
        if not os.path.isdir(a.drive):
            print("WARN: --drive folder does not exist: %s" % a.drive)
            print("      The HTML is still here: %s" % src)
            return 0
        dst = os.path.join(a.drive, html)
        shutil.copy2(src, dst)
        print("copied -> %s" % dst)
        print("Open it from the Google Drive app on your phone.")
    else:
        print("done -> %s" % src)
        print("Pass --drive \"<synced folder>\" to have it copied for phone viewing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
