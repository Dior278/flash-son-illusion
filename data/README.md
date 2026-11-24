# Données

| Dossier | Contenu |
|---|---|
| `raw/` | **Données réelles.** Un fichier CSV par participant, tel que téléchargé à la fin de l'expérience (`flashson_<code>_<date>-<id>.csv`) ou reçu via DataPipe / Google Apps Script. Copier les fichiers ici **sans les modifier**. |
| `simulated/` | **Données SIMULÉES** (faux participants `SIM01`…`SIM15`) générées par `scripts/simulate_participants.py`, uniquement pour tester le notebook. **Ne jamais les mélanger avec les vraies données ni les présenter comme des résultats.** |

Le notebook `analysis/analysis.ipynb` lit tous les fichiers `raw/*.csv`. Si ce dossier est vide, il passe automatiquement aux données simulées et l'indique en gros.

Format : une ligne par essai, colonnes décrites dans le README principal (section « Collecte des données ») et dans `experiment/config.py` (`CSV_COLUMNS`).

Bonnes pratiques :
- garder les fichiers bruts intacts ; toutes les exclusions sont faites dans le notebook, de façon traçable ;
- si un participant a fait l'expérience deux fois, ne garder que la première passation (le notebook regroupe par `participant_id`) ;
- les fichiers sont pseudonymes, mais vérifiez qu'aucun code participant ne contient de nom avant de les publier sur GitHub. Si besoin, retirez `data/raw/*.csv` du dépôt public (décommentez la ligne correspondante dans `.gitignore`).
