# Plan expérimental, stimuli et déroulement

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


---
[← Retour au README](../README.md)
