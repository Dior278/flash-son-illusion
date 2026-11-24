# Données

| Dossier | Contenu |
|---|---|
| `raw/` | **Données réelles**, un CSV par session (`flashson_<session>.csv`), téléchargé depuis le dossier Google Drive de collecte. Copier les fichiers **sans les modifier**. **Ignoré par git** : jamais publié sur GitHub. |
| `simulated/` | **Données SIMULÉES** (faux participants `SIM01`…`SIM20`) générées par `scripts/simulate_participants.py`, uniquement pour tester le notebook. **Ne jamais les mélanger avec les vraies données ni les présenter comme des résultats.** |

Le notebook `analysis/analysis.ipynb` lit tous les fichiers `raw/*.csv`. Si ce dossier est vide, il passe automatiquement aux données simulées et l'indique en gros.

Format : une ligne par essai (test d'écoute, entraînement et essais principaux, colonne `block`) ; colonnes listées dans `experiment/config.py` (`CSV_COLUMNS`).

Bonnes pratiques :
- garder les fichiers bruts intacts ; toutes les exclusions sont faites dans le notebook, de façon traçable ;
- les données sont anonymes (code aléatoire par session) : une personne qui refait l'expérience apparaît comme une nouvelle session. Demandez aux participants de ne la faire qu'une fois ;
- un même fichier reçu deux fois est dédoublonné automatiquement (côté serveur et dans le notebook).
