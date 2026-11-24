# ⚠️ DONNÉES SIMULÉES — NE PAS INTERPRÉTER

Ces fichiers ont été **générés par ordinateur** (`python scripts/simulate_participants.py --seed 2026`). Ils ne proviennent d'aucun participant réel.

Ils servent uniquement à vérifier que le notebook d'analyse fonctionne de bout en bout (chargement, exclusions, statistiques, figures) avant la collecte. Ils ont exactement le même format que les vrais fichiers.

- `SIM01`–`SIM13` : participants « normaux ». L'illusion de fission décroît avec l'écart entre les bips selon une demi-gaussienne de largeur propre à chacun.
- `SIM14` : écouteurs Bluetooth, illusion très affaiblie. Il doit être exclu.
- `SIM15` : participant inattentif qui répond au hasard. Il doit être exclu par les essais de contrôle.
- `ground_truth_SIMULATED.txt` : les vrais paramètres de simulation, pour vérifier que l'ajustement des courbes les retrouve.
