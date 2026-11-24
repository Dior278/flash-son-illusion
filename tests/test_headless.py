#! /usr/bin/env python
"""Test automatique de bout en bout de l'expérience dans un vrai navigateur (Chrome headless).

Lance un petit serveur web local, ouvre l'expérience (?debug=1, et ?short=1 sauf --full),
répond aux écrans et aux essais au clavier, récupère le CSV produit et vérifie son contenu.
NE TESTE PAS la synchronisation réelle son/image (impossible sans photodiode ni micro).

Usage :  python tests/test_headless.py [--full] [--out DOSSIER]
Prérequis : pip install playwright  (et Chrome installé, ou `playwright install chromium`)
"""
import argparse
import csv
import functools
import http.server
import io
import os
import random
import socketserver
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "experiment"))
import config as C  # noqa: E402


def serve(directory, port=0):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), functools.partial(Quiet, directory=directory))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def launch(p, headed=False):
    args = ["--autoplay-policy=no-user-gesture-required"]
    try:
        return p.chromium.launch(channel="chrome", headless=not headed, args=args)
    except Exception:
        return p.chromium.launch(headless=not headed, args=args)


def run_session(context, url, out=None, deadline_s=300, answers=("Digit1", "Digit2", "Numpad2"), seed=1):
    """Fait passer une session complète ; retourne un dict de résultats."""
    page = context.new_page()
    errors, logs = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
    shot = (lambda name: page.screenshot(path=os.path.join(out, name))) if out else (lambda name: None)
    t0 = time.time()
    page.goto(url)
    phase = lambda: page.evaluate("document.body.dataset.phase")
    wait_phase = lambda ph, t=60000: page.wait_for_function(f"document.body.dataset.phase === '{ph}'", timeout=t)
    wait_phase("welcome", 120000)
    load_s = time.time() - t0
    shot("01_welcome.png")
    page.check("#consent"); page.check("#epilepsy"); page.click("#go")
    wait_phase("age"); shot("02_age.png"); page.click("#age-1")
    wait_phase("audio_device"); shot("03_audio.png"); page.click("#dev-1")
    wait_phase("setup"); shot("04_setup.png"); page.click("#go")
    wait_phase("soundcheck"); page.click("#play"); time.sleep(0.3); shot("05_soundcheck.png"); page.click("#ok")
    rng = random.Random(seed)
    n_keys, shots = 0, set()
    end = time.time() + deadline_s
    while time.time() < end:
        ph = phase()
        if ph in ("refresh_warning", "audiocheck_warning"):
            shot(f"warn_{ph}.png")
            page.click("#go")
            page.wait_for_function(f"document.body.dataset.phase !== '{ph}'")
            continue
        if ph in ("end", "done", "error"):
            break
        waiting = page.evaluate("document.body.dataset.waiting || ''")
        if not waiting:
            time.sleep(0.03)
            continue
        if "Space" in waiting:
            if ph not in shots:
                shot(f"06_{ph}.png"); shots.add(ph)
            page.keyboard.press("Space")
        elif "Digit1" in waiting:
            if ph + "_prompt" not in shots:
                shot(f"07_{ph}_prompt.png"); shots.add(ph + "_prompt")
            page.keyboard.press(rng.choice(answers))
            n_keys += 1
        time.sleep(0.03)
    page.wait_for_function("['done', 'error'].includes(document.body.dataset.phase)", timeout=90000)
    shot("08_end.png")
    res = dict(page=page, phase=phase(), csv=page.evaluate("window.flashson_csv || ''"),
               upload=page.evaluate("document.body.dataset.upload || ''"),
               dl_visible=page.evaluate("(() => { const b = document.getElementById('dl'); return !!b && b.style.display !== 'none'; })()"),
               end_text=page.inner_text("#ui"), n_keys=n_keys, load_s=load_s, duration_s=time.time() - t0,
               errors=errors, console_errors=[l for l in logs if l.startswith("[error]")], logs=logs)
    return res


def check_csv(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows, "CSV vide"
    assert list(rows[0].keys()) == C.CSV_COLUMNS, "colonnes inattendues"
    assert len({r["session_id"] for r in rows}) == 1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="tous les essais (sinon 1 par condition)")
    ap.add_argument("--out", default=os.path.join(ROOT, "tests", "output"))
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    from playwright.sync_api import sync_playwright

    httpd = serve(ROOT)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html?debug=1" + ("" if args.full else "&short=1")
    with sync_playwright() as p:
        browser = launch(p, args.headed)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        r = run_session(ctx, url, args.out, deadline_s=900 if args.full else 300)
        browser.close()
    httpd.shutdown()
    with open(os.path.join(args.out, "console.log"), "w") as f:
        f.write("\n".join(r["logs"] + r["errors"]))
    path = os.path.join(args.out, "session.csv")
    open(path, "w").write(r["csv"])
    print(f"Chargement : {r['load_s']:.1f} s ; phase finale : {r['phase']} ; touches : {r['n_keys']} ; "
          f"durée totale : {r['duration_s']:.0f} s")
    rows = check_csv(r["csv"])
    blocks = {}
    for row in rows:
        blocks[row["block"]] = blocks.get(row["block"], 0) + 1
    print("Essais par bloc :", blocks)
    main_rows = [x for x in rows if x["block"] == "main"]

    def stat(col):
        vals = [float(x[col]) for x in main_rows if x[col] not in ("", "nan")]
        return (round(min(vals), 2), round(sum(vals) / len(vals), 2), round(max(vals), 2)) if vals else None
    for col in ("refresh_hz", "flash_late_ms", "flash_dur_ms_actual", "flash_soa_ms_actual", "max_frame_interval_ms",
                "n_dropped_frames", "audio_lead_ms", "av_offset_est_ms", "audio_clock_drift_ms", "rt_ms"):
        print(f"  {col:24s} min/moy/max = {stat(col)}")
    print("  audio_mapping :", sorted({x['audio_mapping'] for x in rows}))
    print("Envoi :", r["upload"], "; bouton de secours visible :", r["dl_visible"])
    print("Écran final :", r["end_text"].replace("\n", " | "))
    print("Erreurs JS :", r["errors"] or "aucune", "; erreurs console :", r["console_errors"] or "aucune")
    ok = r["phase"] == "done" and not r["errors"] and not r["console_errors"]
    print("RÉSULTAT :", "OK" if ok else "ÉCHEC")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
