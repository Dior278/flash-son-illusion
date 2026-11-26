# L'illusion flash-son : quand le son change ce que l'on voit

### ▶ [Participer à l'expérience](https://dior278.github.io/flash-son-illusion/) (≈ 5 min, ordinateur + casque filaire)

- Dépôt : <https://github.com/Dior278/flash-son-illusion>
- Rapport d'analyse : [analysis.html](https://dior278.github.io/flash-son-illusion/analysis/analysis.html) (notebook : [`analysis/analysis.ipynb`](analysis/analysis.ipynb))

## Objectif du projet

Réplication en ligne de **Shams, L., Kamitani, Y. & Shimojo, S. (2000). What you see is what you hear. *Nature*, 408, 788.** <https://doi.org/10.1038/35048669>

Un flash bref accompagné de **deux bips** est souvent vu comme **deux flashs** : le son modifie ce que l'on voit. Le participant compte les flashs (1 ou 2) en ignorant les bips. On teste :
- la **fission** (1 flash + 2 bips → « 2 ») et la **fusion** (2 flashs + 1 bip → « 1 »), et laquelle est la plus forte ;
- l'effet de l'**écart entre les bips** (57 vs 200 ms) : le cerveau n'associe son et image que s'ils sont proches dans le temps.

58 essais (2 × 3 conditions flashs × bips, essais « écart » et essais de contrôle). L'expérience est écrite en **Python**, exécuté dans le navigateur grâce à Pyodide ; les réponses, anonymes, sont envoyées automatiquement.

## Installer et lancer l'expérience sur son ordinateur

Il faut Python 3 et Chrome, Edge ou Firefox :

```
git clone https://github.com/Dior278/flash-son-illusion.git
cd flash-son-illusion
python -m http.server 8000
```

Puis ouvrir <http://localhost:8000>. Options : `?short=1` (version courte, 8 essais), `?debug=1` (mesures de timing).

Pour refaire l'analyse (les données anonymisées sont dans le dépôt, [`data/processed/trials_anon.csv`](data/processed/trials_anon.csv)) :

```
pip install -r requirements.txt
jupyter notebook analysis/analysis.ipynb
```

## Résultats

**24 sessions reçues, 6 exclues** (écran trop lent, timing raté, Bluetooth, contrôle d'attention raté ; critères fixés à l'avance), **18 participants analysés**. Détails : [rapport d'analyse](https://dior278.github.io/flash-son-illusion/analysis/analysis.html).

- **Fission :** 1 flash + 2 bips est vu comme 2 flashs dans **54 %** des essais, contre 3 % sans son (p < 0,001).
- **Fusion :** 2 flashs + 1 bip sont vus comme 1 seul dans 89 % des essais, contre 72 % sans son (p = 0,002). Elle est plus faible que la fission.
- **Fenêtre temporelle :** avec 200 ms entre les bips au lieu de 57 ms, l'illusion tombe à 12 %.
- **En plus des articles :** les 2 bips aident aussi à voir 2 vrais flashs (78 % contre 28 % sans son), et en cas de conflit la réponse suit le son 71 % du temps.

Conclusion : pour compter des événements rapides, le cerveau fait surtout confiance à l'oreille, à condition que le son tombe au bon moment.

## Documentation détaillée

[Plan et hypothèses](docs/PLAN.md) · [Technique et timing](docs/TECHNIQUE.md) · [Données et sécurité](docs/DONNEES.md) · [Mise en ligne](docs/DEPLOIEMENT.md)

## Mon expérience de programmation

*(À compléter par l'auteur, quelques lignes suffisent.)*
- **Avant le cours :** *(langages déjà utilisés, niveau, projets éventuels)* …
- **Ce que j'ai appris** *(pendant le cours, en codant ce projet ou seul : Python, expérience en ligne, git/GitHub, statistiques…)* : …
- **Ce qui m'a manqué dans le cours :** …

---
Licence MIT. Cours « Approches expérimentales de la cognition » (HSS, École polytechnique, C. Pallier).
