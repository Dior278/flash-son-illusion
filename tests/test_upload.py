#! /usr/bin/env python
"""Teste l'envoi automatique des données avec un faux serveur local (tests/mock_upload_server.py).

Pour chaque mode du faux serveur, une session courte (?short=1) est jouée dans Chrome headless
avec une copie temporaire du projet dont APPS_SCRIPT_URL pointe vers le faux serveur. On vérifie :
  * le corps de la requête (JSON : v, token, session_id, csv ; en-tête CSV ; Content-Type text/plain),
  * l'absence de requête préalable CORS (OPTIONS),
  * les nouvelles tentatives, le repli no-cors, le bouton de secours en cas d'échec,
  * le renvoi discret d'une session restée en attente lors de la visite suivante.
Usage : python tests/test_upload.py [--out DOSSIER]
"""
import argparse
import csv
import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "experiment"))
import config as C  # noqa: E402
from mock_upload_server import MockUpload  # noqa: E402
from test_headless import serve, launch, run_session, check_csv  # noqa: E402

failures = []


def expect(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        failures.append(msg)


def check_body(req, label):
    body = json.loads(req["body"])
    expect(set(body) == {"v", "token", "session_id", "csv"}, f"{label} : champs JSON v/token/session_id/csv")
    expect(req["headers"].get("Content-Type", "").startswith("text/plain"), f"{label} : Content-Type text/plain")
    rows = check_csv(body["csv"])
    expect(body["csv"].split("\n")[0] == ",".join(C.CSV_COLUMNS), f"{label} : en-tête CSV attendu")
    expect(all(r["session_id"] == body["session_id"] for r in rows), f"{label} : session_id cohérent")
    expect(re.fullmatch(r"\d{8}-\d{6}-[a-z0-9]{4}", body["session_id"]) is not None, f"{label} : format session_id")
    expect(len(req["body"].encode()) < C.UPLOAD_MAX_BYTES, f"{label} : taille {len(req['body'])} o < {C.UPLOAD_MAX_BYTES}")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "tests", "output_upload"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    from playwright.sync_api import sync_playwright

    mock = MockUpload()
    tmp = tempfile.mkdtemp(prefix="flashson-upload-")
    proj = os.path.join(tmp, "proj")
    shutil.copytree(ROOT, proj, ignore=shutil.ignore_patterns(".git", "tests", "data", "analysis", "__pycache__"))
    cfg = os.path.join(proj, "experiment", "config.py")
    txt = open(cfg, encoding="utf-8").read()
    txt = txt.replace('APPS_SCRIPT_URL = ""', f'APPS_SCRIPT_URL = "{mock.url}"').replace('SHARED_TOKEN = ""', 'SHARED_TOKEN = "test-token"')
    open(cfg, "w", encoding="utf-8").write(txt)
    web = serve(proj)
    url = f"http://127.0.0.1:{web.server_address[1]}/index.html?short=1&debug=1"

    with sync_playwright() as p:
        browser = launch(p)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)

        def session(mode, label):
            mock.mode = mode
            n0 = len(mock.requests)
            r = run_session(ctx, url)
            reqs = mock.requests[n0:]
            print(f"\n[{label}] mode={mode} statut={r['upload']} requêtes={len(reqs)} bouton={r['dl_visible']} "
                  f"texte final : {r['end_text'].splitlines()[-1] if r['end_text'] else ''}")
            expect(not r["errors"], f"{label} : pas d'erreur JS")
            expect(all(q["method"] == "POST" for q in reqs), f"{label} : aucune requête OPTIONS (pas de preflight)")
            return r, reqs

        r, reqs = session("ok", "succès")
        expect(r["upload"] == "confirmed" and len(reqs) == 1, "succès : 1 requête, envoi confirmé")
        body = check_body(reqs[0], "succès")
        expect(body["token"] == "test-token", "succès : jeton transmis")
        expect(body["csv"] == r["csv"], "succès : CSV envoyé = CSV de la session")
        expect(not r["dl_visible"] and "Réponses envoyées" in r["end_text"], "succès : pas de bouton, message discret")
        r["page"].close()

        mock.flaky_count = 0
        r, reqs = session("flaky", "serveur instable")
        expect(r["upload"] == "confirmed" and len(reqs) == 3, "instable : 2 échecs HTTP 500 puis succès (3 requêtes)")
        expect(len({q["body"] for q in reqs}) == 1, "instable : corps identique à chaque tentative")
        r["page"].close()

        r, reqs = session("nocors", "réponse sans CORS")
        modes = [q["headers"].get("Content-Type", "") for q in reqs]
        expect(r["upload"] == "unconfirmed" and len(reqs) == len(C.UPLOAD_RETRY_DELAYS_S) + 1,
               f"sans CORS : {len(C.UPLOAD_RETRY_DELAYS_S)} essais + 1 repli no-cors, statut « non confirmé »")
        expect(not r["dl_visible"], "sans CORS : pas de bouton (données reçues par le serveur)")
        r["page"].close()

        r, reqs = session("reject", "refus du serveur")
        expect(r["upload"] == "rejected" and len(reqs) == 1, "refus : pas de nouvelle tentative")
        expect(r["dl_visible"], "refus : bouton de secours affiché")
        r["page"].close()

        r, reqs = session("down", "serveur injoignable")
        expect(r["upload"] == "failed" and len(reqs) == len(C.UPLOAD_RETRY_DELAYS_S) + 1, "injoignable : toutes les tentatives échouent")
        expect(r["dl_visible"], "injoignable : bouton de secours affiché")
        page = r["page"]
        with page.expect_download() as dl:
            page.click("#dl")
        path = os.path.join(args.out, dl.value.suggested_filename)
        dl.value.save_as(path)
        down_csv = open(path, encoding="utf-8").read()
        down_sid = check_csv(down_csv)[0]["session_id"]
        expect(down_csv == r["csv"], f"injoignable : le bouton télécharge le CSV ({dl.value.suggested_filename})")
        page.close()

        # visite suivante : la session restée en attente doit être renvoyée discrètement
        mock.mode = "ok"
        n0 = len(mock.requests)
        page = ctx.new_page()
        page.goto(url)
        page.wait_for_function("document.body.dataset.phase === 'welcome'", timeout=120000)
        page.wait_for_timeout(4000)
        sids = [json.loads(q["body"])["session_id"] for q in mock.requests[n0:]]
        expect(down_sid in sids, "visite suivante : la session non envoyée est renvoyée automatiquement")
        status = page.evaluate(f"localStorage.getItem('{C.EXPERIMENT_NAME}:{down_sid}:status')")
        expect(status == "confirmed", "visite suivante : session marquée comme envoyée")
        page.close()
        # garder un corps réel pour le test du script Apps Script
        ok_body = [q for q in mock.requests if q["mode"] == "ok"][0]["body"]
        open(os.path.join(args.out, "sample_payload.json"), "w", encoding="utf-8").write(ok_body)
        browser.close()
    web.shutdown(); mock.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nRÉSULTAT :", "OK" if not failures else f"ÉCHEC ({len(failures)})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
