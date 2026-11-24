# L'illusion flash-son : quand le son change ce que l'on voit

*Projet du cours « Approches expérimentales de la cognition » (HSS, École polytechnique, C. Pallier).*
Réplication en ligne, et extension, de :

> Shams, L., Kamitani, Y. & Shimojo, S. (2000). **What you see is what you hear.** *Nature*, 408, 788. <https://doi.org/10.1038/35048669>

- **Lancer l'expérience :** `https://<votre-compte>.github.io/flash-son-illusion/` (après déploiement, voir plus bas)
- **Dépôt :** `https://github.com/<votre-compte>/flash-son-illusion`

**Sommaire**

- [Question et hypothèses](#question-et-hypothèses)
- [Déroulement de l'expérience](#déroulement-de-lexpérience)
- [Plan expérimental et stimuli](#plan-expérimental-et-stimuli)
- [Technologie : Python dans le navigateur (Pyodide)](#technologie--python-dans-le-navigateur-pyodide)
- [Timing : ce qui est contrôlé, ce qui ne l'est pas](#timing--ce-qui-est-contrôlé-ce-qui-ne-lest-pas)
- [Lancer l'expérience en local](#lancer-lexpérience-en-local)
- [Mettre l'expérience en ligne (GitHub Pages)](#mettre-lexpérience-en-ligne-github-pages)
- [Collecte des données](#collecte-des-données)
- [Analyse des données](#analyse-des-données)
- [Organisation du dépôt](#organisation-du-dépôt)
- [Limites](#limites)
- [Références](#références)

---

## Question et hypothèses

On pense souvent que la **vision domine** nos autres sens. Shams et al. (2000) ont montré l'inverse : quand un flash unique est accompagné de **deux bips** rapprochés, la plupart des gens voient **deux flashs**. Le son modifie qualitativement une perception visuelle pourtant non ambiguë. Pour compter des événements rapides, le cerveau fait davantage confiance à l'audition, plus précise dans le temps.

Hypothèses, fixées avant la collecte des données :

| | Hypothèse | Test |
|---|---|---|
| **H1** | **Fission** : on rapporte plus de flashs pour 1 flash + 2 bips (1F2B) que pour 1 flash sans son (1F0B) ou avec 1 bip (1F1B) | t de Student apparié |
| **H2** | **Fusion**, plus faible : 2 flashs + 1 bip (2F1B) sont parfois vus comme 1 flash (comparaison avec 2F0B) | t de Student apparié |
| **H3** | **Interaction** flashs × bips | ANOVA à mesures répétées 2 × 3 (+ modèle mixte) |
| **H4** | **Fenêtre d'intégration** (extension) : l'illusion décroît quand l'écart entre les 2 bips passe de 57 à 300 ms. La largeur de cette fenêtre (TBW) varie selon les individus | ANOVA (effet de l'écart) + ajustement d'une demi-gaussienne par participant |

Analyse complémentaire : une analyse de **détection du signal** (d′, critère), comme chez Flanagan et al. (2025), pour savoir si l'illusion change la *perception* (d′) ou seulement le *biais de réponse*.

## Déroulement de l'expérience

Durée totale : **environ 5 à 6 minutes**, dont 4 minutes d'essais.

1. **Accueil et consentement**, avec un filtre sur l'épilepsie photosensible.
2. **Informations** : code pseudonyme, âge, genre, main dominante, **matériel audio** (une alerte s'affiche si le participant déclare du Bluetooth), vision, audition.
3. **Installation** : endroit calme, 50 à 60 cm de l'écran, volume à 70–80 %. Le clic sur le bouton passe en plein écran et active le son.
4. **Réglage du volume** avec une série de bips test.
5. **Mesure automatique de la fréquence de l'écran** sur 120 images.
6. **Test d'écoute** : 6 essais « 1 ou 2 bips ? » sans flash. Il vérifie que les deux bips sont bien distincts (critère d'exclusion).
7. **Consignes et 6 essais d'entraînement** avec correction (sans essais « illusion »).
8. **98 essais principaux** dans un ordre aléatoire, avec une barre de progression et une pause au milieu. Au plus 3 essais identiques d'affilée.
9. **Écran final** : le participant voit son taux personnel d'illusion, un histogramme selon l'écart entre les bips et une estimation de sa « fenêtre d'intégration ». Le CSV se télécharge automatiquement.

### Touches

| Touche | Signification |
|---|---|
| `1` (rangée du haut ou pavé numérique) | « J'ai vu 1 flash » (ou 1 bip dans le test d'écoute) |
| `2` | « J'ai vu 2 flashs » (ou 2 bips) |
| `Espace` | Continuer (consignes, pause) |
| `Échap` | Arrêter : les réponses déjà données sont sauvegardées |

Ce sont les **touches physiques** qui comptent (`event.code`). Sur un clavier AZERTY, il n'est donc pas nécessaire d'appuyer sur Maj : la touche `&/1` fonctionne directement.

## Plan expérimental et stimuli

La liste des essais est écrite dans `experiment/trials.csv` par `scripts/create_trial_list.py`, comme `create-experimental-list.py` dans l'exemple du cours. Tous les paramètres se trouvent dans `experiment/config.py`.

| Partie | Conditions | Essais |
|---|---|---|
| Cœur (Shams 2000) | 1 ou 2 flashs × 0, 1 ou 2 bips. Écart entre bips 57 ms, entre flashs ≈ 50 ms | 10 par condition, 12 pour 1F2B (62) |
| Extension TBW | 1 flash + 2 bips, écart entre bips de 100, 150, 200 ou 300 ms (57 ms vient du cœur) | 8 × 4 (32) |
| Contrôle d'attention | 2 flashs séparés de 150 ms, sans son (réponse évidente : « 2 ») | 4 |
| **Total** | | **98** |

Stimuli, d'après Shams et al. (2000, 2002) et la version en ligne de Flanagan et al. (2025) :
- **Flash** : disque blanc uniforme sur fond noir, de diamètre égal à 10 % de la hauteur de l'écran. Il est centré à mi-chemin entre la croix de fixation et le bas de l'écran, soit environ 2° à 5° sous la fixation pour un portable de 14″ vu à environ 57 cm. Il dure **1 image à 60 Hz (≈ 17 ms)** : le nombre d'images est arrondi selon la fréquence mesurée, par exemple 2 images à 120 Hz. Deux flashs sont séparés d'environ **50 ms**, soit 3 images à 60 Hz.
- **Bip** : son pur de **3,5 kHz** durant **7 ms**, avec des rampes de 1 ms. Les bips sont séparés de **57 ms** dans le cœur du plan. Le 1er bip est programmé pour coïncider avec le 1er flash.
- **Essai** : croix de fixation pendant 700 à 1100 ms (durée aléatoire), puis le stimulus, 300 ms de noir et la question « Combien de flashs ? ». Le temps de réponse n'est pas limité ; il est enregistré, mais ce n'est pas la mesure principale.

## Technologie : Python dans le navigateur (Pyodide)

L'exemple Python du cours (`PCBS-LexicalDecision`) utilise **expyriment**, qui tourne sur l'ordinateur de l'expérimentateur. Ici, il faut faire passer l'expérience **à distance, dans le navigateur des participants**, tout en programmant **en Python**. Nous avons choisi **[Pyodide](https://pyodide.org)**, l'interpréteur CPython officiel compilé en WebAssembly, chargé depuis un CDN (version figée : 0.29.5).

- **Toute la logique de l'expérience est en Python** (`experiment/flash_sound.py`). Le seul code JavaScript est `experiment/boot.js` (30 lignes) : il charge Pyodide et lance `flash_sound.main()`.
- Le Python pilote **directement les API du navigateur** qui donnent le meilleur timing audio-visuel possible sur le web :
  - `requestAnimationFrame` et `<canvas>` : chaque flash est dessiné de façon synchrone avec le rafraîchissement de l'écran, et sa durée se compte en images ;
  - **Web Audio API** : les bips sont programmés **à l'avance, à l'échantillon près**, sur l'horloge audio (`AudioBufferSourceNode.start(t)`). Les sons sont générés en mémoire, ce qui évite tout chargement de fichier. Une fois programmé, le son ne dépend plus de la vitesse de Python.
- Aucune bibliothèque Python supplémentaire n'est requise (seulement la bibliothèque standard), d'où un chargement de quelques secondes.

Les alternatives écartées :
- **pygame + pygbag** : pygame tourne dans le navigateur, mais le son y passe par une émulation de SDL_mixer avec des tampons dont la latence n'est pas maîtrisée. C'est rédhibitoire pour une illusion qui se joue à quelques dizaines de millisecondes.
- **PsychoPy → PsychoJS / Pavlovia** : c'est la solution utilisée par Flanagan et al. (2025), mais l'expérience en ligne est alors du JavaScript généré automatiquement (pas du Python), et Pavlovia est payant au-delà d'un quota.
- **jsPsych** : excellent, mais c'est du JavaScript.

## Timing : ce qui est contrôlé, ce qui ne l'est pas

Soyons honnêtes : **un navigateur ne garantit pas la synchronisation physique du son et de l'image.** Voici ce que fait le programme et ce qu'il enregistre.

**Ce qui est fait :**
1. On estime la période de rafraîchissement de l'écran, par la médiane de 120 intervalles entre images.
2. Environ 250 ms avant le flash, on cale l'instant du flash sur la grille des rafraîchissements, avec T = t + k × période.
3. On convertit l'instant prévu d'affichage, T plus une image de latence d'affichage (`DISPLAY_LATENCY_FRAMES`), dans l'horloge audio avec `AudioContext.getOutputTimestamp()`. Cette fonction tient compte de la latence de sortie audio annoncée par le système. À défaut, on utilise `currentTime` corrigé de `outputLatency`. Les bips sont programmés à cet instant précis.
4. Le flash est dessiné dans le rappel `requestAnimationFrame` prévu. Le ramasse-miettes Python est suspendu pendant le stimulus, pour éviter toute pause.

**Ce qui est enregistré à chaque essai** (colonnes du CSV) : fréquence estimée (`refresh_hz`, `frame_ms`), durée réelle du flash et intervalle réel entre flashs, retard du flash sur l'image prévue (`flash_late_ms`), intervalle maximal entre images et **images perdues** (`n_dropped_frames`), avance avec laquelle le son a été programmé (`audio_lead_ms`), décalage son-image estimé (`av_offset_est_ms`), **dérive** entre l'horloge audio et l'horloge de la page (`audio_clock_drift_ms`), latences audio annoncées (`output_latency_ms`, `base_latency_ms`), méthode de conversion (`audio_mapping`), onglet masqué (`tab_hidden`) et plein écran (`fullscreen`). Ces mesures alimentent les **critères d'exclusion** (voir le notebook).

**Ce qui n'est pas contrôlé :**
- Le délai entre la fin du dessin et l'apparition des photons, qui dépend du compositeur du navigateur, de l'OS et de l'écran (de 0 à 2 images selon les machines), ainsi que la latence réelle de la carte son et du casque. Les études de référence sur le timing en ligne (par ex. Bridges et al., 2020) montrent des décalages son-image **de quelques ms à plusieurs dizaines de ms** selon le couple navigateur/OS.
- **Le Bluetooth** ajoute 100 à 300 ms de retard au son, souvent mal annoncé au navigateur. C'est pourquoi on le demande, on l'enregistre et on l'exclut.
- La taille réelle du disque en degrés (pas de calibration de l'écran) et la distance à l'écran.

Ces imprécisions de quelques dizaines de ms restent compatibles avec l'illusion, qui persiste tant que le son et l'image sont à moins d'environ 100 ms l'un de l'autre (Shams et al., 2000). Flanagan et al. (2025) ont d'ailleurs **validé une version en ligne** de ce paradigme : on y retrouve l'effet de labo et sa dépendance à l'écart temporel.

**Vérification possible avec du matériel :** la page `timing-check.html` reprend l'idée de `xpy_check_audio_visual_timing.py` du cours. Elle affiche un carré blanc et joue un son de 440 Hz toutes les 500 ms, avec le même moteur. On peut ainsi mesurer le vrai décalage avec une photodiode et un micro, ou simplement en filmant l'écran au ralenti (240 images/s) avec un téléphone, puis ajuster `DISPLAY_LATENCY_FRAMES` dans `config.py`.

## Lancer l'expérience en local

Il faut **Python 3** (pour le petit serveur web) et un navigateur récent (Chrome, Edge ou Firefox). La première fois, une connexion Internet est nécessaire pour charger Pyodide.

Sous **Windows** (PowerShell) :

```powershell
cd "C:\Users\pavel\OneDrive\Documents\L'X\3A\P1\Cognitive Sciences\flash-son-illusion"
python -m http.server 8000
```

Ouvrir ensuite <http://localhost:8000> dans Chrome ou Edge. Arrêter le serveur avec `Ctrl+C`.

> Ouvrir directement `index.html` par double-clic **ne marche pas** : le navigateur interdit alors de charger les fichiers `.py` (sécurité `file://`). Il faut passer par le petit serveur.

Options d'URL utiles pour tester :

| URL | Effet |
|---|---|
| `http://localhost:8000/?short=1` | Version courte : 1 essai par condition (11 essais principaux) |
| `http://localhost:8000/?debug=1` | Affiche les mesures de timing de chaque essai en bas de l'écran et dans la console (F12) |
| `http://localhost:8000/?pid=P01` | Pré-remplit le code participant (pratique pour envoyer un lien personnalisé) |
| `http://localhost:8000/timing-check.html` | Mode vérification du timing (carré + son toutes les 500 ms) |

**Test automatique** (facultatif) : `tests/test_headless.py` lance l'expérience dans un Chrome sans fenêtre, répond au clavier et vérifie le CSV produit :

```powershell
pip install playwright
python tests/test_headless.py            # version courte
python tests/test_headless.py --full     # les 110 essais
```

## Mettre l'expérience en ligne (GitHub Pages)

Le site est **statique** (HTML, Python, CSV), sans serveur à payer. Comme dans la diapositive du cours 6 :

```powershell
cd flash-son-illusion
git remote add origin https://github.com/<votre-compte>/flash-son-illusion.git
git branch -M main
git push -u origin main
```

Ensuite, sur GitHub, aller dans **Settings → Pages → Build and deployment → Source : Deploy from a branch**, choisir **Branch : `main`** et le dossier **`/ (root)`**, puis **Save**. Au bout d'une à deux minutes, l'expérience est en ligne à l'adresse `https://<votre-compte>.github.io/flash-son-illusion/`.

Le fichier `.nojekyll` indique à GitHub de servir les fichiers tels quels. Avant d'envoyer le lien, faites au moins une passation complète sur votre propre ordinateur, sur le site en ligne, avec un casque filaire.

## Collecte des données

Trois mécanismes se complètent, et aucun ne nécessite de serveur payant :

1. **Sauvegarde au fur et à mesure dans le navigateur** : après chaque essai, toutes les données sont copiées dans le `localStorage`. Si le navigateur plante, le participant peut récupérer ses données en revenant sur la page : un lien « Télécharger la session… » apparaît sur l'écran d'accueil.
2. **Téléchargement automatique d'un CSV à la fin**, avec un bouton « Télécharger à nouveau » : le fichier `flashson_<code>_<date>-<id>.csv` arrive dans le dossier Téléchargements. **Le participant l'envoie ensuite à l'expérimentateur** (mail, Teams, dépôt sur un Drive partagé…).
3. **Envoi automatique (optionnel, gratuit)** : il suffit de remplir **une** des deux lignes de `experiment/config.py`.
   - `DATAPIPE_EXPERIMENT_ID` : [DataPipe](https://pipe.jspsych.org), un service gratuit des créateurs de jsPsych, enregistre chaque fichier dans **votre Google Drive** (ou Zenodo / Dataverse). Pour l'activer : créer un compte, connecter Google Drive (*Account Settings → Storage Providers*), créer une expérience (*New Experiment*), activer *Accept new data*, puis copier l'identifiant dans `config.py`. ⚠️ DataPipe n'écrit plus vers OSF depuis le 16/11/2026 : choisissez Google Drive.
   - `APPS_SCRIPT_URL` : un petit script Google Apps Script, fourni dans `tools/google_apps_script.gs` avec son mode d'emploi, enregistre les CSV dans un dossier de votre Drive.

   En cas d'échec de l'envoi, le participant en est informé et le fichier téléchargé reste disponible.

**Où mettre les fichiers ?** Tous les CSV reçus vont dans **`data/raw/`** (voir `data/README.md`). Le format est le même quel que soit le mode de collecte : **un fichier par participant, une ligne par essai**, y compris les essais du test d'écoute et de l'entraînement (colonne `block`).

Principales colonnes : `participant_id`, `session_id`, `block` (`audiocheck`, `practice`, `main`), `trial_in_block`, `condition` (par ex. `1F2B`, `1F2B_soa150`, `2F0B_catch`), `n_flashes`, `n_beeps`, `beep_soa_ms`, `response` (1/2), `correct`, `rt_ms`, `timestamp_iso`, les diagnostics de timing (voir plus haut), puis `age`, `gender`, `handedness`, `audio_device`, `vision`, `hearing`, `audio_check_score`, `user_agent`, `screen_w`, `screen_h`, `refresh_hz`, `random_seed` et `aborted`. La liste complète se trouve dans `CSV_COLUMNS` (`config.py`).

**Éthique et RGPD** : les données sont pseudonymes (code choisi, aucun nom), le consentement est recueilli à l'écran et le participant peut arrêter à tout moment. Ne demandez pas de noms dans le code participant.

## Analyse des données

L'analyse suit la démarche du cours 6 : statistiques descriptives par participant, puis tests inférentiels. Elle se trouve dans le notebook **`analysis/analysis.ipynb`**, commenté en français.

Sous **Windows** :

```powershell
cd flash-son-illusion
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook analysis/analysis.ipynb
```

Puis *Kernel → Restart & Run All*. Les figures sont enregistrées dans `analysis/figures/`.

Contenu du notebook :
1. chargement de tous les CSV de `data/raw/` ;
2. **critères d'exclusion**, fixés à l'avance et détaillés dans le notebook :
   - au niveau des essais : images perdues, flash en retard de plus d'une demi-image, son programmé trop tard, onglet masqué, temps de réponse inférieur à 100 ms ou supérieur à 10 s ;
   - au niveau des participants : Bluetooth, test d'écoute réussi à moins de 5/6, contrôles ratés (moins de 75 % de réussite sur les essais faciles à 2 flashs, ou moins de 70 % sur 1 flash sans son), écran à moins de 50 Hz, plus de 20 % d'essais exclus pour le timing, session incomplète ;
3. nombre moyen de flashs perçus **par participant et par condition**, avec un tableau et des graphiques façon figure 1 de Shams et al. ;
4. **t appariés** 1F2B vs 1F0B (H1, avec le contrôle 1F2B vs 1F1B) et 2F1B vs 2F0B (H2), avec d de Cohen, IC 95 %, BF10 et Wilcoxon ;
5. **ANOVA à mesures répétées** 2 × 3 (pingouin, avec correction de Greenhouse-Geisser, vérifiée avec statsmodels `AnovaRM`), comparaisons post-hoc (Holm) et **modèle linéaire mixte** essai par essai ;
6. extension : illusion en fonction de l'écart entre les bips, ANOVA, **ajustement d'une demi-gaussienne** par participant et pour le groupe, puis **fenêtre d'intégration TBW50** et corrélation avec la force de l'illusion ;
7. **détection du signal** (d′, critère c) avec et sans bips ;
8. tableau et graphiques des **diagnostics de timing** par session.

> **Données simulées.** Tant que `data/raw/` est vide, le notebook utilise automatiquement les **faux participants** de `data/simulated/`, produits par `python scripts/simulate_participants.py`. Ils servent à vérifier que tout fonctionne. Toutes les figures portent alors la mention **[SIMULÉ]**, et leurs fichiers le suffixe `_SIMULATED`. **Ces résultats ne doivent jamais être présentés comme des résultats.** Dès qu'un vrai CSV est placé dans `data/raw/`, seules les vraies données sont utilisées.

## Organisation du dépôt

```
flash-son-illusion/
├── index.html                  # page de l'expérience (GitHub Pages)
├── timing-check.html           # mode vérification du timing (photodiode/micro)
├── .nojekyll
├── experiment/
│   ├── flash_sound.py          # ★ l'expérience, en Python (exécutée par Pyodide)
│   ├── config.py               # ★ tous les paramètres (stimuli, plan, collecte)
│   ├── trials.csv              # liste des essais (générée par scripts/create_trial_list.py)
│   ├── boot.js                 # amorçage : charge Pyodide et lance flash_sound.main()
│   └── style.css
├── scripts/
│   ├── create_trial_list.py    # écrit experiment/trials.csv à partir de config.py
│   └── simulate_participants.py# génère des données SIMULÉES dans data/simulated/
├── data/
│   ├── README.md
│   ├── raw/                    # ← mettre ici les CSV des vrais participants
│   └── simulated/              # faux participants (test du notebook uniquement)
├── analysis/
│   ├── analysis.ipynb          # ★ analyse (notebook Jupyter, en français)
│   └── figures/
├── tests/test_headless.py      # test automatique de bout en bout (Chrome headless)
├── tools/google_apps_script.gs # option : collecte gratuite vers Google Drive
├── requirements.txt            # dépendances de l'analyse
└── LICENSE                     # MIT
```

Pour modifier le plan (par exemple les écarts entre bips ou le nombre de répétitions), éditez `experiment/config.py`, puis relancez :

```powershell
python scripts/create_trial_list.py
```

## Limites

- **Timing du navigateur** : voir plus haut. Le son et l'image ne sont pas mesurés physiquement, et l'hétérogénéité du matériel ajoute du bruit, ce qui affaiblirait plutôt l'effet qu'il ne le créerait.
- **Peu d'essais par condition** (8 à 12) pour tenir en 5 minutes : les estimations individuelles de la fenêtre d'intégration sont bruitées, et l'analyse de groupe est plus fiable.
- La demi-gaussienne est un **modèle descriptif** de la décroissance entre 57 et 300 ms ; elle n'est pas faite pour extrapoler en dessous de 57 ms, où les deux bips fusionneraient.
- Dans l'extension, seul l'écart entre les bips varie (le son suit toujours le flash). L'asymétrie son-avant/son-après de Flanagan et al. (2025) n'est pas testée.
- Réponse limitée à 1 ou 2 flashs (comme Flanagan et al., 2025), alors que Shams et al. (2000) allaient jusqu'à 4.
- **Échantillon** : des étudiants volontaires, pas forcément naïfs. Demandez-leur de ne pas dévoiler le principe de l'expérience.

## Références

- Shams, L., Kamitani, Y., & Shimojo, S. (2000). What you see is what you hear. *Nature*, 408, 788. https://doi.org/10.1038/35048669
- Shams, L., Kamitani, Y., & Shimojo, S. (2002). Visual illusion induced by sound. *Cognitive Brain Research*, 14, 147–152. https://doi.org/10.1016/S0926-6410(02)00069-1
- Flanagan, L., Zumbrunn, N. M., Hirst, R. J., & McGovern, D. P. (2025). Assessing the reliability of an online measure of the temporal binding window of audiovisual integration. *Behavior Research Methods*. https://doi.org/10.3758/s13428-025-02791-3 ([texte intégral](https://pmc.ncbi.nlm.nih.gov/articles/PMC12361292/))
- Stevenson, R. A., Zemtsov, R. K., & Wallace, M. T. (2012). Individual differences in the multisensory temporal binding window predict susceptibility to audiovisual illusions. *JEP: HPP*, 38(6), 1517. https://doi.org/10.1037/a0027339
- Bridges, D., Pitiot, A., MacAskill, M. R., & Peirce, J. W. (2020). The timing mega-study: comparing a range of experiment generators, both lab-based and online. *PeerJ*, 8, e9414. https://doi.org/10.7717/peerj.9414
- Pallier, C. *Programming for Cognitive and Brain Sciences* (PCBS). https://pcbs.readthedocs.io ; exemple : https://github.com/chrplr/PCBS-LexicalDecision ; ébauche expyriment de cette illusion : `PCBS/experiments/xpy_beep_flash_illusion/beep_flash.py`
- Motulsky, H. *Intuitive Biostatistics* (ouvrage de statistiques partagé par l'enseignant).

## Licence

Code sous licence MIT (voir `LICENSE`).
