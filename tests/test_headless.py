#! /usr/bin/env python
"""Test automatique de bout en bout de l'expérience dans un vrai navigateur (Chrome headless).

Lance un petit serveur web local, ouvre l'expérience en mode court (?short=1&debug=1),
remplit les formulaires, répond aux essais avec le clavier, récupère le CSV téléchargé
et vérifie son contenu. NE TESTE PAS la synchronisation réelle son/image (impossible
sans photodiode ni micro) : seulement que tout s'exécute et que les données sont complètes.

Usage :  python tests/test_headless.py [--full] [--out DOSSIER]
Prérequis : pip install playwright  (et un Chrome/Chromium installé, ou `playwright install chromium`)
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


def serve(port):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="tous les essais (sinon 1 par condition)")
    ap.add_argument("--out", default=os.path.join(ROOT, "tests", "output"))
    ap.add_argument("--port", type=int, default=0, help="0 = port libre choisi automatiquement")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    from playwright.sync_api import sync_playwright

    httpd = serve(args.port)
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/index.html?debug=1&pid=TEST01" + ("" if args.full else "&short=1")
    errors, logs = [], []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=not args.headed,
                                        args=["--autoplay-policy=no-user-gesture-required"])
        except Exception:
            browser = p.chromium.launch(headless=not args.headed,
                                        args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
        t0 = time.time()
        import atexit
        atexit.register(lambda: open(os.path.join(args.out, "console.log"), "w").write("\n".join(logs + errors)))
        page.goto(url)
        phase = lambda: page.evaluate("document.body.dataset.phase")
        page.wait_for_function("document.body.dataset.phase === 'welcome'", timeout=120000)
        print(f"Pyodide + expérience chargés en {time.time() - t0:.1f} s")
        page.screenshot(path=os.path.join(args.out, "01_welcome.png"))
        page.check("#consent"); page.check("#epilepsy"); page.click("#go")
        page.wait_for_function("document.body.dataset.phase === 'info'")
        page.fill("#age", "21"); page.select_option("#gender", "undisclosed"); page.select_option("#handedness", "right")
        page.select_option("#audio_device", "laptop_speakers"); page.select_option("#vision", "normal")
        page.select_option("#hearing", "normal")
        page.screenshot(path=os.path.join(args.out, "02_info.png"))
        page.click("#go")
        page.wait_for_function("document.body.dataset.phase === 'setup'")
        page.click("#go")
        page.wait_for_function("document.body.dataset.phase === 'soundcheck'")
        page.click("#play"); time.sleep(0.5)
        page.screenshot(path=os.path.join(args.out, "03_soundcheck.png"))
        page.click("#ok")
        rng = random.Random(1)
        n_keys = 0
        shots = set()
        download = None
        deadline = time.time() + (900 if args.full else 300)
        while time.time() < deadline:
            ph = phase()
            if ph in ("refresh_warning", "audiocheck_warning"):
                page.screenshot(path=os.path.join(args.out, f"warn_{ph}.png"))
                page.click("#go")
                page.wait_for_function(f"document.body.dataset.phase !== '{ph}'")
                continue
            if ph in ("end", "done", "error"):
                break
            waiting = page.evaluate("document.body.dataset.waiting || ''")
            if not waiting:
                time.sleep(0.05)
                continue
            if "Space" in waiting:
                if ph not in shots:
                    page.screenshot(path=os.path.join(args.out, f"04_{ph}.png")); shots.add(ph)
                page.keyboard.press("Space")
            elif "Digit1" in waiting:
                if ph + "_prompt" not in shots:
                    page.screenshot(path=os.path.join(args.out, f"05_{ph}_prompt.png")); shots.add(ph + "_prompt")
                page.keyboard.press(rng.choice(["Digit1", "Digit2", "Numpad2"]))
                n_keys += 1
            time.sleep(0.05)
        with page.expect_download(timeout=60000) as dl_info:
            page.wait_for_function("document.body.dataset.phase === 'done' || document.body.dataset.phase === 'error'",
                                   timeout=60000)
            page.click("#again")
        download = dl_info.value
        path = os.path.join(args.out, download.suggested_filename)
        download.save_as(path)
        page.screenshot(path=os.path.join(args.out, "06_end.png"), full_page=True)
        final_phase = phase()
        browser.close()
    httpd.shutdown()

    print(f"Phase finale : {final_phase} ; touches envoyées : {n_keys} ; durée : {time.time() - t0:.0f} s")
    print(f"CSV : {path}")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    assert rows, "CSV vide"
    assert list(rows[0].keys()) == C.CSV_COLUMNS, "colonnes inattendues"
    blocks = {}
    for r in rows:
        blocks[r["block"]] = blocks.get(r["block"], 0) + 1
    print("Essais par bloc :", blocks)
    main_rows = [r for r in rows if r["block"] == "main"]
    def stat(col):
        vals = [float(r[col]) for r in main_rows if r[col] not in ("", "nan")]
        return (min(vals), sum(vals) / len(vals), max(vals)) if vals else None
    for col in ("refresh_hz", "flash_late_ms", "flash_dur_ms_actual", "flash_soa_ms_actual", "max_frame_interval_ms",
                "n_dropped_frames", "audio_lead_ms", "av_offset_est_ms", "audio_clock_drift_ms", "rt_ms"):
        print(f"  {col:24s} min/moy/max = {stat(col)}")
    print("  audio_mapping :", sorted({r['audio_mapping'] for r in rows}))
    page_errors = [e for e in errors]
    py_errors = [l for l in logs if l.startswith("[error]")]
    print("Erreurs JS :", page_errors or "aucune"); print("Erreurs console :", py_errors or "aucune")
    with open(os.path.join(args.out, "console.log"), "w") as f:
        f.write("\n".join(logs))
    ok = final_phase == "done" and not page_errors and not py_errors
    print("RÉSULTAT :", "OK" if ok else "ÉCHEC")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
