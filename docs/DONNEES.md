# Données : collecte, sécurité, analyse

Mise en ligne pas à pas (Apps Script + GitHub Pages) : [DEPLOIEMENT.md](DEPLOIEMENT.md).

## Collecte automatique des données

**Le participant n'a rien à envoyer.** À la fin, l'expérience envoie le CSV de la session à un petit **Google Apps Script** (gratuit) qui l'ajoute dans un dossier de ton Google Drive. Mode d'emploi pas à pas : **[`DEPLOIEMENT.md`](DEPLOIEMENT.md)**.

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

## Analyse des données

L'analyse suit la démarche du cours 6 : statistiques descriptives par participant, puis tests inférentiels, dans le notebook **`analysis/analysis.ipynb`** (en français).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook analysis/analysis.ipynb
```

Puis *Kernel → Restart & Run All*. Les figures sont enregistrées dans `analysis/figures/`.

Contenu du notebook (9 figures, chacune suivie d'une phrase « À retenir ») :
1. données, **critères d'exclusion** fixés à l'avance et participants (figure 1) :
   - essais : images perdues, flash en retard de plus d'une demi-image, son programmé trop tard, onglet masqué, temps de réponse < 100 ms ou > 10 s ;
   - sessions : Bluetooth, test d'écoute < 2/3 à la dernière tentative, contrôles ratés (< 75 % de « 2 » sur les 2 flashs bien séparés, ou < 70 % de « 1 » pour 1 flash sans son), écran < 50 Hz, > 20 % d'essais exclus pour le timing, < 80 % des essais faits ;
2. nombre moyen de flashs perçus par condition, façon Shams et al. (figure 2) ;
3. **H1, H2, H3, H5** : t appariés (unilatéraux), Wilcoxon, d de Cohen, IC 95 % bootstrap (figure 3) ; **H4** : ANOVA à mesures répétées 2 × 3 (Greenhouse-Geisser) ;
4. détection du signal, d′ et critère c (figure 4) ;
5. analyses exploratoires : le son aide à voir 2 vrais flashs et gagne les conflits (figure 5), différences individuelles (figure 6), temps de réponse (figure 7), évolution au cours de la session (figure 8), type de son et âge (figure 9) ;
6. robustesse sans exclusion de session ; 7. timing ; 8. conclusion ; 9. limites.

> **Données publiées.** Les CSV bruts (`data/raw/`) restent privés. `python scripts/anonymize_data.py` en tire `data/processed/trials_anon.csv` (sans code de session, date, heure, navigateur détaillé ni taille d'écran ; participants renommés `P01`…), publié dans le dépôt et lu par le notebook. Le script `scripts/simulate_participants.py` peut encore générer de faux participants dans `data/simulated/` pour tester le code, mais le rapport utilise uniquement les vraies données.

---
[← Retour au README](../README.md)
