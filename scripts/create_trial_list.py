#! /usr/bin/env python
"""Crée la liste des essais de l'expérience (experiment/trials.csv).

Comme dans l'exemple du cours (PCBS-LexicalDecision/create-experimental-list.py),
le plan expérimental est écrit dans un fichier CSV versionné avec git.
L'expérience lit ce fichier, puis mélange l'ordre des essais pour chaque participant.

Usage :
    python scripts/create_trial_list.py            # écrit experiment/trials.csv
    python scripts/create_trial_list.py -o -       # affiche sur la sortie standard
"""

import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "experiment"))
import config as C  # noqa: E402

FIELDS = ["block", "part", "condition", "n_flashes", "n_beeps",
          "beep_soa_ms", "flash_soa_ms", "is_catch"]


def condition_label(nf, nb, beep_soa, catch=False):
    lab = f"{nf}F{nb}B"
    if catch:
        return lab + "_catch"
    if nb == 2 and nf == 1 and beep_soa != C.CORE_BEEP_SOA_MS:
        return f"{lab}_soa{beep_soa}"
    return lab


def make_rows():
    rows = []
    # Essais d'entraînement (avec feedback)
    for nf, nb, soa, fsoa in C.PRACTICE_TRIALS:
        rows.append(dict(block="practice", part="practice",
                         condition=condition_label(nf, nb, soa), n_flashes=nf, n_beeps=nb,
                         beep_soa_ms=soa if nb == 2 else 0,
                         flash_soa_ms=fsoa if nf == 2 else 0, is_catch=0))
    # Vérification auditive : combien de bips ? (aucun flash)
    for nb, soa in C.AUDIO_CHECK_TRIALS:
        rows.append(dict(block="audiocheck", part="audiocheck", condition=f"0F{nb}B",
                         n_flashes=0, n_beeps=nb, beep_soa_ms=soa if nb == 2 else 0,
                         flash_soa_ms=0, is_catch=0))
    # Cœur du plan : 2 (flashs) x 3 (bips), SOA bips = 57 ms, SOA flashs = 50 ms
    for (nf, nb), reps in C.REPS_CORE.items():
        for _ in range(reps):
            rows.append(dict(block="main", part="core", condition=condition_label(nf, nb, C.CORE_BEEP_SOA_MS),
                             n_flashes=nf, n_beeps=nb,
                             beep_soa_ms=C.CORE_BEEP_SOA_MS if nb == 2 else 0,
                             flash_soa_ms=C.FLASH_SOA_MS if nf == 2 else 0, is_catch=0))
    # Extension : 1 flash + 2 bips à différents écarts entre les bips
    for soa in C.EXTENSION_BEEP_SOAS_MS:
        for _ in range(C.REPS_EXTENSION):
            rows.append(dict(block="main", part="soa", condition=condition_label(1, 2, soa),
                             n_flashes=1, n_beeps=2, beep_soa_ms=soa, flash_soa_ms=0, is_catch=0))
    # Essais de contrôle faciles (attention) : 2 flashs séparés de 150 ms, sans son
    for _ in range(C.REPS_CATCH):
        rows.append(dict(block="main", part="catch", condition=condition_label(2, 0, 0, catch=True),
                         n_flashes=2, n_beeps=0, beep_soa_ms=0,
                         flash_soa_ms=C.CATCH_FLASH_SOA_MS, is_catch=1))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default=os.path.join(HERE, "..", "experiment", "trials.csv"))
    args = parser.parse_args()
    rows = make_rows()
    out = sys.stdout if args.output == "-" else open(args.output, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    if out is not sys.stdout:
        out.close()
        n_main = sum(r["block"] == "main" for r in rows)
        print(f"{len(rows)} lignes écrites dans {os.path.normpath(args.output)} "
              f"(dont {n_main} essais principaux)", file=sys.stderr)


if __name__ == "__main__":
    main()
