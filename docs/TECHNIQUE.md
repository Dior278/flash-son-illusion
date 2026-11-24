# Technique : Python dans le navigateur, timing, tests

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

Il faut **Python 3** (pour le petit serveur web) et un navigateur récent (Chrome, Edge ou Firefox). Une connexion Internet est nécessaire pour charger Pyodide.

Sous **Windows** (PowerShell) :

```powershell
cd "C:\Users\pavel\OneDrive\Documents\L'X\3A\P1\Cognitive Sciences\flash-son-illusion"
python -m http.server 8000
```

Ouvrir ensuite <http://localhost:8000> dans Chrome ou Edge. Arrêter le serveur avec `Ctrl+C`.

> Ouvrir directement `index.html` par double-clic **ne marche pas** : le navigateur interdit alors de charger les fichiers `.py` (sécurité `file://`).

| URL | Effet |
|---|---|
| `http://localhost:8000/?short=1` | Version courte : 1 essai par condition (8 essais principaux) |
| `http://localhost:8000/?debug=1` | Affiche les mesures de timing de chaque essai (écran et console F12) |
| `http://localhost:8000/timing-check.html` | Mode vérification du timing (carré + son toutes les 500 ms) |

Tant que `APPS_SCRIPT_URL` est vide dans `config.py`, rien n'est envoyé : l'écran final propose seulement un petit bouton « Télécharger mes réponses ».

## Tests automatiques

```powershell
pip install playwright numpy
python -m playwright install chromium   # ou utiliser Chrome déjà installé
python tests/test_headless.py            # expérience complète en version courte dans Chrome sans fenêtre
python tests/test_headless.py --full     # les 64 essais
python tests/test_upload.py              # envoi vers un faux serveur local : corps, tentatives, repli, bouton, renvoi
node tests/test_apps_script.js           # script Google simulé : validation, refus, anti-doublon, en-tête = config.py
```

## Organisation du dépôt

```
flash-son-illusion/
├── index.html                  # page de l'expérience (GitHub Pages)
├── timing-check.html           # mode vérification du timing (photodiode/micro)
├── .nojekyll
├── experiment/
│   ├── flash_sound.py          # ★ l'expérience, en Python (exécutée par Pyodide)
│   ├── config.py               # ★ tous les paramètres (stimuli, plan, URL de collecte)
│   ├── trials.csv              # liste des essais (générée par scripts/create_trial_list.py)
│   ├── boot.js                 # amorçage : charge Pyodide et lance flash_sound.main()
│   └── style.css
├── scripts/
│   ├── create_trial_list.py    # écrit experiment/trials.csv à partir de config.py
│   └── simulate_participants.py# génère des données SIMULÉES dans data/simulated/
├── tools/
│   ├── google_apps_script.gs   # récepteur des données (Google Apps Script, écriture seule)
│   └── appsscript.json         # son manifeste (droits minimaux)
├── docs/                       # documentation détaillée
│   ├── PLAN.md                 # hypothèses, plan, stimuli, déroulement, limites, références
│   ├── TECHNIQUE.md            # Pyodide, timing, lancement local, tests (ce fichier)
│   ├── DONNEES.md              # collecte automatique, sécurité, format, analyse
│   └── DEPLOIEMENT.md          # mise en ligne pas à pas (Apps Script + GitHub Pages)
├── data/
│   ├── raw/                    # ← CSV des vrais participants (ignoré par git)
│   └── simulated/              # faux participants (test du notebook uniquement)
├── analysis/
│   ├── analysis.ipynb          # ★ analyse (notebook Jupyter, en français)
│   ├── analysis.html           # le même notebook exporté en HTML (rapport)
│   └── figures/
├── tests/                      # tests automatiques (navigateur, envoi, script Google)
├── requirements.txt            # dépendances de l'analyse
└── LICENSE                     # MIT
```

Pour modifier le plan (répétitions, écart entre bips…), éditez `experiment/config.py`, puis relancez `python scripts/create_trial_list.py`.


---
[← Retour au README](../README.md)
