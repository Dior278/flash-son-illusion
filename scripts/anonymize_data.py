"""Prépare le jeu de données ANONYME publié dans le dépôt.

Lit les CSV bruts de data/raw/ (un fichier par session, jamais publiés), puis écrit
data/processed/trials_anon.csv, qui est le fichier lu par le notebook d'analyse.

Ce que fait le script :
- ignore les fichiers de test (session_id finissant par « test » ou version « SIMULATED ») ;
- supprime les doublons (même session, même essai) ;
- remplace le code de session par un numéro P01, P02… (ordre fixé par une empreinte
  du code de session : il ne suit donc pas l'ordre de passage) ;
- retire les colonnes qui pourraient aider à reconnaître quelqu'un : codes de session,
  date et heure, navigateur complet (user agent), taille d'écran, graine aléatoire.
  Seule la famille du navigateur (Chrome, Firefox, Safari, Edge) est gardée.

Usage (depuis la racine du dépôt) :  python scripts/anonymize_data.py
"""
import glob
import hashlib
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "processed", "trials_anon.csv")

DROP = ["participant_id", "session_id", "timestamp_iso", "user_agent", "screen_w", "screen_h",
        "device_pixel_ratio", "random_seed"]


def browser_family(ua):
    ua = str(ua)
    if "Edg/" in ua:
        return "Edge"
    if "Firefox/" in ua:
        return "Firefox"
    if "Chrome/" in ua:
        return "Chrome"
    if "Safari/" in ua:
        return "Safari"
    return "Autre"


def main():
    files = sorted(glob.glob(os.path.join(RAW_DIR, "flashson_*.csv")))
    if not files:
        raise SystemExit(f"Aucun fichier flashson_*.csv dans {RAW_DIR}")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    test = df.session_id.astype(str).str.endswith("test") | \
        df.experiment_version.astype(str).str.contains("SIMULATED")
    print(f"{len(files)} fichiers ; sessions de test ignorées : {sorted(df[test].session_id.unique())}")
    df = df[~test].drop_duplicates(subset=["session_id", "block", "trial_global"])

    sessions = sorted(df.session_id.unique(), key=lambda s: hashlib.sha256(s.encode()).hexdigest())
    code = {s: f"P{i:02d}" for i, s in enumerate(sessions, start=1)}
    df.insert(0, "participant", df.session_id.map(code))
    df.insert(1, "browser", df.user_agent.map(browser_family))
    df = df.drop(columns=DROP).sort_values(["participant", "trial_global"])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False, lineterminator="\n")
    print(f"{df.participant.nunique()} participants, {len(df)} lignes -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
