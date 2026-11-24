#! /usr/bin/env python
"""Génère des données SIMULÉES (faux participants) pour tester le notebook d'analyse.

ATTENTION : ces données sont FAUSSES. Elles servent uniquement à vérifier que la chaîne
d'analyse fonctionne de bout en bout avant d'avoir de vraies données.
Elles sont écrites dans data/simulated/ (jamais dans data/raw/), et tous les
identifiants commencent par « SIM ».

Modèle génératif (ordres de grandeur publiés : Shams et al., 2000 ; Andersen et al., 2004) :
  * fission (1 flash + 2 bips) : P(« 2 ») = base + (1 - base) * amp * exp(-soa² / 2 sigma²),
    donc forte à 57 ms et plus faible à 200 ms (fenêtre de largeur sigma propre à chacun) ;
  * fusion (2 flashs + 1 bip) : P(« 1 ») augmente d'un indice de fusion, en moyenne plus faible
    que la fission et légèrement corrélé à elle ;
  * très bonne performance sans son et sur les essais de contrôle.
Deux participants « à problème » testent les critères d'exclusion :
l'avant-dernier (écouteurs Bluetooth) et le dernier (inattentif, répond au hasard).

Usage : python scripts/simulate_participants.py [-n 20] [--seed 2026]
"""
import argparse
import csv
import math
import os
import random
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "experiment"))
sys.path.insert(0, HERE)
import config as C  # noqa: E402
from create_trial_list import make_rows  # noqa: E402


def simulate_participant(k, rng, kind="normal"):
    pid = f"SIM{k:02d}"
    session = f"SIMULATED-{k:02d}"
    base = rng.uniform(0.02, 0.10)                              # P(« 2 ») avec 1 flash seul
    sigma = min(260, max(80, rng.gauss(160, 40)))               # largeur de la fenêtre (ms)
    amp = min(0.9, max(0.2, rng.gauss(0.60, 0.15)))             # force de la fission
    p1_2f0b = rng.uniform(0.05, 0.25)                           # P(« 1 ») avec 2 flashs seuls
    fusion = min(0.6, max(-0.05, rng.gauss(0.15, 0.10) + 0.3 * (amp - 0.6)))  # indice de fusion
    p2 = {"1F0B": base, "1F1B": min(1, base + rng.uniform(0, 0.05)),
          "2F0B": 1 - p1_2f0b, "2F1B": max(0.02, 1 - p1_2f0b - fusion),
          "2F2B": min(0.99, 1 - p1_2f0b + rng.uniform(0, 0.08)), "2F0B_catch": 0.97}
    audio_device = rng.choice(["wired", "wired", "speakers"])
    if kind == "bluetooth":
        audio_device = "bluetooth"
        amp *= 0.3                                              # son retardé : l'illusion s'effondre
        p2["2F1B"] = p2["2F0B"]

    def prob_two(t):
        if kind == "inattentive":
            return 0.5
        nf, nb, soa = t["n_flashes"], t["n_beeps"], t["beep_soa_ms"]
        if nf == 1 and nb == 2:
            return min(0.98, base + (1 - base) * amp * math.exp(-soa ** 2 / (2 * sigma ** 2)))
        return p2[t["condition"]]

    refresh = rng.choice([60.0, 60.0, 60.0, 120.0, 144.0])
    P = 1000 / refresh
    t0 = datetime(2026, 12, 1, 10, 0) + timedelta(hours=k * 3)
    trials = make_rows()
    main = [t for t in trials if t["block"] == "main"]
    rng.shuffle(main)
    seq = [t for t in trials if t["block"] == "audiocheck"] + [t for t in trials if t["block"] == "practice"] + main
    info = dict(age_bracket=rng.choice(["18-21"] * 5 + ["22-25"] * 4 + ["26-35"]), audio_device=audio_device)
    rows, counters, tg, ac_correct = [], {}, 0, 0
    for t in seq:
        block = t["block"]
        counters[block] = counters.get(block, 0) + 1
        tg += 1
        if block == "audiocheck":
            expected = t["n_beeps"]
            response = expected if rng.random() < 0.96 else 3 - expected
            ac_correct += response == expected
        else:
            expected = t["n_flashes"]
            response = 2 if rng.random() < prob_two(t) else 1
        dropped = 1 if rng.random() < 0.02 else 0
        nf = t["n_flashes"]
        rows.append(dict(
            participant_id=pid, session_id=session, experiment_version=C.EXPERIMENT_VERSION + "-SIMULATED",
            timestamp_iso=(t0 + timedelta(seconds=2.2 * tg)).isoformat() + "Z",
            block=block, trial_in_block=counters[block], trial_global=tg, condition=t["condition"],
            n_flashes=nf, n_beeps=t["n_beeps"], beep_soa_ms=t["beep_soa_ms"], flash_soa_ms_target=t["flash_soa_ms"],
            is_catch=t["is_catch"], part=t["part"], response=response, correct=int(response == expected),
            rt_ms=round(rng.lognormvariate(math.log(650), 0.35), 1),
            refresh_hz=round(refresh, 2), frame_ms=round(P, 2), flash_frames=max(1, round(17 / P)),
            flash_dur_ms_actual=round(max(1, round(17 / P)) * P + rng.gauss(0, 0.2), 2) if nf else "",
            flash_soa_ms_actual=round(round(t["flash_soa_ms"] / P) * P + rng.gauss(0, 0.2), 2) if nf == 2 else "",
            flash_late_ms=round(rng.gauss(-0.4, 0.2) + dropped * P, 2) if nf else "",
            max_frame_interval_ms=round(P * (1 + dropped) + abs(rng.gauss(0, 0.3)), 2),
            n_dropped_frames=dropped,
            audio_lead_ms=round(rng.uniform(220, 240), 2) if t["n_beeps"] else "",
            audio_scheduled_late=0, av_offset_est_ms=round(-dropped * P + rng.gauss(0.4, 0.2), 2) if t["n_beeps"] else "",
            audio_clock_drift_ms=round(rng.gauss(0, 0.1), 2),
            output_latency_ms=round(rng.uniform(150, 250) if audio_device == "bluetooth" else rng.uniform(8, 40), 1),
            base_latency_ms=10.0, audio_sample_rate=48000, audio_mapping="outputTimestamp",
            tab_hidden=0, fullscreen=1, **info, audio_check_score="",
            user_agent="SIMULATED", screen_w=1920, screen_h=1080, device_pixel_ratio=1.0,
            random_seed=rng.randint(0, 2 ** 31), aborted=0))
    score = f"{ac_correct}/{len(C.AUDIO_CHECK_TRIALS)}"
    for r in rows:
        r["audio_check_score"] = score
    return pid, rows, dict(base=base, amp=amp, sigma=sigma, fusion=fusion, kind=kind)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "simulated"))
    args = ap.parse_args()
    rng = random.Random(args.seed)
    os.makedirs(args.out, exist_ok=True)
    for old in os.listdir(args.out):                      # efface les anciennes simulations
        if old.endswith("_SIMULATED.csv") or old == "ground_truth_SIMULATED.txt":
            os.remove(os.path.join(args.out, old))
    truth = []
    for k in range(1, args.n + 1):
        kind = "bluetooth" if k == args.n - 1 else "inattentive" if k == args.n else "normal"
        pid, rows, params = simulate_participant(k, rng, kind)
        path = os.path.join(args.out, f"flashson_{pid}_SIMULATED.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=C.CSV_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        truth.append(dict(participant_id=pid, **params))
    with open(os.path.join(args.out, "ground_truth_SIMULATED.txt"), "w", encoding="utf-8") as f:
        f.write("# Paramètres VRAIS utilisés pour simuler chaque faux participant (pour vérifier l'analyse)\n")
        f.write("participant_id\tkind\tbase\tamp\tsigma_ms\tfusion\n")
        for t in truth:
            f.write(f"{t['participant_id']}\t{t['kind']}\t{t['base']:.3f}\t{t['amp']:.3f}\t{t['sigma']:.1f}"
                    f"\t{t['fusion']:.3f}\n")
    print(f"{args.n} participants simulés écrits dans {os.path.normpath(args.out)}")


if __name__ == "__main__":
    main()
