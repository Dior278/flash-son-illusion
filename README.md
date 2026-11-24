# L'illusion flash-son : quand le son change ce que l'on voit

*Projet du cours « Approches expérimentales de la cognition » (HSS, École polytechnique, C. Pallier).*
Réplication en ligne, et extension, de :

> Shams, L., Kamitani, Y. & Shimojo, S. (2000). **What you see is what you hear.** *Nature*, 408, 788. <https://doi.org/10.1038/35048669>

avec la variante « fusion » d'Andersen, Tiippana & Sams (2004) et une manipulation de l'écart entre les bips.

- **Lancer l'expérience :** `https://<votre-compte>.github.io/flash-son-illusion/` (après la mise en ligne : [`docs/DEPLOIEMENT.md`](docs/DEPLOIEMENT.md))
- **Dépôt :** `https://github.com/<votre-compte>/flash-son-illusion`

**Sommaire**

- [Question et hypothèses](#question-et-hypothèses)
- [Déroulement de l'expérience](#déroulement-de-lexpérience)
- [Plan expérimental et stimuli](#plan-expérimental-et-stimuli)
- [Technologie : Python dans le navigateur (Pyodide)](#technologie--python-dans-le-navigateur-pyodide)
- [Timing : ce qui est contrôlé, ce qui ne l'est pas](#timing--ce-qui-est-contrôlé-ce-qui-ne-lest-pas)
- [Lancer l'expérience en local](#lancer-lexpérience-en-local)
- [Collecte automatique des données](#collecte-automatique-des-données)
- [Mise en ligne (GitHub Pages)](#mise-en-ligne-github-pages)
- [Analyse des données](#analyse-des-données)
- [Tests automatiques](#tests-automatiques)
- [Organisation du dépôt](#organisation-du-dépôt)
- [Limites](#limites)
- [Références](#références)

---

## Question et hypothèses

On pense souvent que la **vision domine** nos autres sens. Shams et al. (2000) ont montré l'inverse : quand un flash unique est accompagné de **deux bips** rapprochés, la plupart des gens voient **deux flashs** (illusion de *fission*). Pour compter des événements rapides, le cerveau fait davantage confiance à l'audition, plus précise dans le temps.

Deux variantes permettent d'en apprendre plus sur le fonctionnement du cerveau :
- **Fusion** (Andersen et al., 2004) : deux flashs avec **un seul bip** sont-ils vus comme un seul flash ? Le son peut-il *retirer* un événement visuel, ou seulement en *ajouter* un ?
- **Écart entre les bips** : si les deux bips sont séparés de 200 ms au lieu de 57 ms, le cerveau les associe-t-il encore au flash ? Cela teste l'existence d'une **fenêtre temporelle d'intégration** audio-visuelle.

Hypothèses, fixées avant la collecte des données :

| | Hypothèse | Test |
|---|---|---|
| **H1** | **Fission** : 1 flash + 2 bips (1F2B) est plus souvent vu comme 2 flashs qu'1 flash seul (1F0B) | t de Student apparié |
| **H2** | **Fusion** : 2 flashs + 1 bip (2F1B) sont plus souvent vus comme 1 flash que 2 flashs seuls (2F0B) | t de Student apparié |
| **H3** | **Asymétrie** : l'illusion de fission est plus forte que celle de fusion | t apparié sur les indices d'illusion |
| **H4** | **Interaction** flashs × bips | ANOVA à mesures répétées 2 × 3 (+ modèle mixte) |
| **H5** | **Fenêtre temporelle** : la fission diminue quand les 2 bips sont séparés de 200 ms au lieu de 57 ms | t de Student apparié |

Indices par participant : **fission** = P(« 2 » | 1F2B) − P(« 2 » | 1F0B) ; **fusion** = P(« 1 » | 2F1B) − P(« 1 » | 2F0B). Analyse complémentaire : **détection du signal** (d′, critère c) pour savoir si l'illusion change la *perception* ou seulement le *biais de réponse*.

## Déroulement de l'expérience

Durée : **environ 5 minutes**, dont 4 minutes d'essais. Un écran = une idée, peu de texte, tutoiement.

1. **Accueil** : consentement (18 ans ou plus, réponses anonymes) et case « pas d'épilepsie photosensible ».
2. **Deux questions seulement**, en gros boutons :
   - **tranche d'âge** (18–21, 22–25, 26–35, 36+) : la fenêtre d'intégration audio-visuelle s'élargit avec l'âge, c'est donc une covariable utile ; une tranche suffit et préserve l'anonymat ;
   - **type d'écoute** (casque filaire, haut-parleurs, Bluetooth) : le Bluetooth retarde le son de 100 à 300 ms, ce qui détruit la synchronisation ; c'est un critère d'exclusion. Si « Bluetooth » est choisi, l'écran propose de changer.
3. **Installation** (3 consignes) puis le bouton « Plein écran et son ».
4. **Réglage du volume** avec des bips test.
5. **Mesure automatique de la fréquence de l'écran.**
6. **Test d'écoute** : 3 essais « 1 ou 2 bips ? » sans flash (une seconde tentative est proposée en cas d'erreur).
7. **Consigne** (« Fixe la croix. Compte les flashs : 1 ou 2. Ignore les bips. ») et **3 essais d'entraînement** avec correction.
8. **58 essais principaux** dans un ordre aléatoire, barre de progression, pause à la moitié. Au plus 3 essais identiques d'affilée.
9. **Écran final** : « Merci ! » et le résultat personnel en langage simple, par exemple : « Avec 1 seul flash et 2 bips, tu as vu 2 flashs 6 fois sur 8. Ton cerveau a laissé le son modifier ce que tu voyais. », plus une phrase sur la fusion. Les réponses partent **automatiquement** ; une petite ligne confirme l'envoi.

### Touches

| Touche | Signification |
|---|---|
| `1` (rangée du haut ou pavé numérique) | « J'ai vu 1 flash » (ou 1 bip dans le test d'écoute) |
| `2` | « J'ai vu 2 flashs » (ou 2 bips) |
| `Espace` | Continuer |
| `Échap` | Arrêter (avec confirmation) : les réponses déjà données sont envoyées |

Ce sont les **touches physiques** qui comptent (`event.code`) : sur un clavier AZERTY, la touche `&/1` fonctionne sans Maj.

## Plan expérimental et stimuli

La liste des essais est écrite dans `experiment/trials.csv` par `scripts/create_trial_list.py`, comme `create-experimental-list.py` dans l'exemple du cours. Tous les paramètres sont dans `experiment/config.py`.

| Partie | Conditions | Essais |
|---|---|---|
| Cœur (Shams 2000 + fusion) | 1 ou 2 flashs × 0, 1 ou 2 bips. Écart entre bips 57 ms, entre flashs ≈ 50 ms | 6 × 8 = 48 |
| Écart (fenêtre temporelle) | 1 flash + 2 bips séparés de **200 ms** (`1F2B_gap200`) | 6 |
| Contrôle d'attention | 2 flashs séparés de 150 ms, sans son (réponse évidente : « 2 ») | 4 |
| **Total des essais principaux** | | **58** |
| Avant : test d'écoute + entraînement | | 3 + 3 |

Durée estimée : 58 essais × ≈ 2,1 s + test d'écoute, entraînement et écrans ≈ **4 à 5 minutes**.

Stimuli, d'après Shams et al. (2000, 2002) et la version en ligne de Flanagan et al. (2025) :
- **Flash** : disque blanc uniforme sur fond noir, de diamètre égal à 10 % de la hauteur de l'écran, centré à mi-chemin entre la croix de fixation et le bas de l'écran (environ 2° à 5° sous la fixation pour un portable de 14″ vu à 57 cm). Il dure **1 image à 60 Hz (≈ 17 ms)** ; le nombre d'images est arrondi selon la fréquence mesurée. Deux flashs sont séparés d'environ **50 ms**.
- **Bip** : son pur de **3,5 kHz**, **7 ms**, rampes de 1 ms. Bips séparés de **57 ms** (cœur) ou **200 ms** (écart). Le 1er bip est programmé pour coïncider avec le 1er flash.
- **Essai** : croix de fixation pendant 700 à 1100 ms (durée aléatoire), puis le stimulus, 300 ms de noir et la question « Combien de flashs ? ». Le temps de réponse n'est pas limité ; il est enregistré mais n'est pas la mesure principale.

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

## Collecte automatique des données

**Le participant n'a rien à envoyer.** À la fin, l'expérience envoie le CSV de la session à un petit **Google Apps Script** (gratuit) qui l'ajoute dans un dossier de ton Google Drive. Mode d'emploi pas à pas : **[`docs/DEPLOIEMENT.md`](docs/DEPLOIEMENT.md)**.

Côté navigateur (`experiment/flash_sound.py`) :
1. **Sauvegarde continue** : après chaque essai, la session est copiée dans le `localStorage` du navigateur.
2. **Envoi** : requête `POST` en `text/plain` (pas de requête préalable CORS) contenant `{v, token, session_id, csv}` ; jusqu'à 4 tentatives (attentes de 0, 1, 2 puis 4 s, délai maximal de 15 s chacune).
3. **Repli** : si la réponse est illisible à cause de CORS ou d'une erreur réseau, un dernier envoi en mode `no-cors` est fait (succès probable mais non confirmable, noté `unconfirmed`).
4. **Échec** : seulement dans ce cas, un petit bouton discret « L'envoi n'a pas marché : télécharger mes réponses » apparaît. La session reste aussi dans le navigateur et sera **renvoyée discrètement à la visite suivante** (le serveur ignore les doublons).

Côté serveur (`tools/google_apps_script.gs`) : **écriture seule** (aucune fonction de lecture), portée Drive minimale (`drive.file`), taille maximale de 200 Ko, en-tête et colonnes vérifiés, caractères autorisés, pas de cellule-formule, nom de fichier construit par le serveur (`flashson_<session>.csv`), anti-doublon sous verrou.

**Sécurité et anonymat**
- Aucun secret dans le dépôt. L'URL du script est publique mais ne permet que d'**ajouter** un fichier valide.
- Le jeton optionnel `SHARED_TOKEN` est visible dans le dépôt public : c'est une **obfuscation**, pas une protection.
- Données **anonymes** : code aléatoire par session (`P` + 6 caractères), tranche d'âge, type d'écoute, réponses et mesures techniques (navigateur, taille d'écran, timing). Ni nom ni e-mail.
- `data/raw/` est **ignoré par git** : les vraies données ne partent jamais sur GitHub.

Format : **un fichier par session, une ligne par essai**, y compris le test d'écoute et l'entraînement (colonne `block` : `audiocheck`, `audiocheck2`, `practice`, `main`). Principales colonnes : `participant_id`, `session_id`, `block`, `condition` (par ex. `1F2B`, `1F2B_gap200`, `2F0B_catch`), `part` (`core`, `gap`, `catch`), `n_flashes`, `n_beeps`, `beep_soa_ms`, `response` (1/2), `correct`, `rt_ms`, les diagnostics de timing, `age_bracket`, `audio_device`, `audio_check_score`, `aborted`. Liste complète : `CSV_COLUMNS` dans `config.py`.

## Mise en ligne (GitHub Pages)

Le site est **statique** (HTML, Python, CSV). Résumé (détails dans [`docs/DEPLOIEMENT.md`](docs/DEPLOIEMENT.md)) :

```powershell
git remote add origin https://github.com/<votre-compte>/flash-son-illusion.git
git branch -M main
git push -u origin main
```

Puis, sur GitHub : **Settings → Pages → Source : Deploy from a branch → Branch : `main`, dossier `/ (root)` → Save**. Le fichier `.nojekyll` fait servir les fichiers tels quels. Avant d'envoyer le lien, fais une passation complète sur le site en ligne avec un casque filaire et vérifie l'arrivée du fichier dans le Drive.

## Analyse des données

L'analyse suit la démarche du cours 6 : statistiques descriptives par participant, puis tests inférentiels, dans le notebook **`analysis/analysis.ipynb`** (en français).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook analysis/analysis.ipynb
```

Puis *Kernel → Restart & Run All*. Les figures sont enregistrées dans `analysis/figures/`.

Contenu du notebook :
1. chargement des CSV de `data/raw/` (dédoublonnage) et description des sessions ;
2. **critères d'exclusion**, fixés à l'avance :
   - essais : images perdues, flash en retard de plus d'une demi-image, son programmé trop tard, onglet masqué, temps de réponse < 100 ms ou > 10 s ;
   - sessions : Bluetooth, test d'écoute < 2/3 à la dernière tentative, contrôles ratés (< 75 % de « 2 » sur les 2 flashs bien séparés, ou < 70 % de « 1 » pour 1 flash sans son), écran < 50 Hz, > 20 % d'essais exclus pour le timing, < 80 % des essais faits ;
3. nombre moyen de flashs perçus **par participant et par condition** (figure 1, façon Shams et al.) et indices de fission / fusion ;
4. **H1, H2** : t appariés unilatéraux (d de Cohen, Wilcoxon en contrôle) ;
5. **H3** : fission vs fusion (t apparié sur les indices, figure 2) et corrélation exploratoire ;
6. **H4** : ANOVA à mesures répétées 2 × 3 (pingouin, Greenhouse-Geisser, vérifiée avec statsmodels `AnovaRM`), post hoc (Holm) et modèle linéaire mixte ;
7. **H5** : fission à 57 vs 200 ms (figure 3) ;
8. détection du signal (d′, c) ; diagnostics de timing (figure 4).

> **Données simulées.** Tant que `data/raw/` est vide, le notebook utilise les **faux participants** de `data/simulated/` (`python scripts/simulate_participants.py`). Les figures portent alors la mention **[SIMULÉ]** et le suffixe `_SIMULATED`. **Ces résultats ne doivent jamais être présentés comme des résultats.**

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
├── docs/DEPLOIEMENT.md         # ★ mise en ligne pas à pas (Apps Script + GitHub Pages)
├── data/
│   ├── raw/                    # ← CSV des vrais participants (ignoré par git)
│   └── simulated/              # faux participants (test du notebook uniquement)
├── analysis/
│   ├── analysis.ipynb          # ★ analyse (notebook Jupyter, en français)
│   └── figures/
├── tests/                      # tests automatiques (navigateur, envoi, script Google)
├── requirements.txt            # dépendances de l'analyse
└── LICENSE                     # MIT
```

Pour modifier le plan (répétitions, écart entre bips…), éditez `experiment/config.py`, puis relancez `python scripts/create_trial_list.py`.

## Limites

- **Timing du navigateur** : voir plus haut. Le son et l'image ne sont pas mesurés physiquement, et l'hétérogénéité du matériel ajoute du bruit, ce qui affaiblirait plutôt l'effet qu'il ne le créerait.
- **Peu d'essais par condition** (8 pour le cœur, 6 pour l'écart) pour tenir en 4–5 minutes : les indices individuels sont bruités ; l'analyse de groupe est plus fiable.
- Un seul écart « long » (200 ms) : on teste l'existence d'une fenêtre temporelle, pas sa forme exacte.
- Réponse limitée à 1 ou 2 flashs (comme Flanagan et al., 2025), alors que Shams et al. (2000) allaient jusqu'à 4.
- **Anonymat** : on ne peut pas repérer une personne qui ferait l'expérience deux fois. Demandez aux participants de ne la faire qu'une fois et de ne pas en dévoiler le principe.

## Références

- Shams, L., Kamitani, Y., & Shimojo, S. (2000). What you see is what you hear. *Nature*, 408, 788. https://doi.org/10.1038/35048669
- Shams, L., Kamitani, Y., & Shimojo, S. (2002). Visual illusion induced by sound. *Cognitive Brain Research*, 14, 147–152. https://doi.org/10.1016/S0926-6410(02)00069-1
- Andersen, T. S., Tiippana, K., & Sams, M. (2004). Factors influencing audiovisual fission and fusion illusions. *Cognitive Brain Research*, 21, 301–308. https://doi.org/10.1016/j.cogbrainres.2004.06.004
- Flanagan, L., Zumbrunn, N. M., Hirst, R. J., & McGovern, D. P. (2025). Assessing the reliability of an online measure of the temporal binding window of audiovisual integration. *Behavior Research Methods*. https://doi.org/10.3758/s13428-025-02791-3
- Bridges, D., Pitiot, A., MacAskill, M. R., & Peirce, J. W. (2020). The timing mega-study: comparing a range of experiment generators, both lab-based and online. *PeerJ*, 8, e9414. https://doi.org/10.7717/peerj.9414
- Pallier, C. *Programming for Cognitive and Brain Sciences* (PCBS). https://pcbs.readthedocs.io ; exemple : https://github.com/chrplr/PCBS-LexicalDecision ; ébauche expyriment de cette illusion : `PCBS/experiments/xpy_beep_flash_illusion/beep_flash.py`
- Motulsky, H. *Intuitive Biostatistics* (ouvrage de statistiques partagé par l'enseignant).

## Licence

Code sous licence MIT (voir `LICENSE`).
