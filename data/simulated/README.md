# DONNÉES SIMULÉES — NE PAS INTERPRÉTER

Ces fichiers ont été **générés par ordinateur** (`python scripts/simulate_participants.py --seed 2026`). Ils ne proviennent d'aucun participant réel.

Ils servent uniquement à vérifier que le notebook d'analyse fonctionne de bout en bout (chargement, exclusions, statistiques, figures) avant la collecte. Ils ont exactement le même format que les vrais fichiers (plan v2 : 58 essais principaux).

- `SIM01`–`SIM18` : participants « normaux ». Fission forte à 57 ms, plus faible à 200 ms (fenêtre de largeur propre à chacun) ; fusion plus faible que la fission.
- `SIM19` : écouteurs Bluetooth, illusions très affaiblies. Doit être exclu.
- `SIM20` : participant inattentif qui répond au hasard. Doit être exclu par les essais de contrôle.
- `ground_truth_SIMULATED.txt` : les vrais paramètres de simulation (`amp` = force de la fission, `sigma_ms` = largeur de la fenêtre, `fusion` = indice de fusion), pour vérifier que l'analyse les retrouve.
