# Mise en ligne : envoi automatique des données et GitHub Pages

Ce guide se fait **une seule fois**, en 15 minutes environ. À la fin :
- l'expérience est en ligne sur `https://<ton-compte>.github.io/flash-son-illusion/` ;
- chaque participant qui termine envoie **automatiquement** son fichier CSV dans un dossier de **ton** Google Drive, sans rien avoir à faire.

Deux briques gratuites :

| Brique | Rôle |
|---|---|
| **GitHub Pages** (dépôt public) | héberge la page de l'expérience (HTML + Python exécuté par Pyodide) |
| **Google Apps Script** (application Web) | reçoit le CSV et l'ajoute dans un dossier Drive. **Il ne sait rien faire d'autre** : pas de lecture, pas de liste, pas de suppression |

> Utilise de préférence un **compte Google personnel** (Gmail). Les comptes d'établissement (Google Workspace) interdisent souvent l'accès « Tout le monde » aux applications Web.

---

## Étape 1 – Créer le script de collecte (Google Apps Script)

1. Va sur <https://script.google.com> → **Nouveau projet**. Renomme-le (en haut à gauche), par exemple `flash-son-collecte`.
2. **Afficher le fichier manifeste** : roue dentée **Paramètres du projet** (à gauche) → coche **« Afficher le fichier manifeste "appsscript.json" dans l'éditeur »**.
3. Retourne dans l'**Éditeur** (icône `< >`).
   - Ouvre `appsscript.json` et remplace **tout** son contenu par celui de `tools/appsscript.json` :

     ```json
     {
       "timeZone": "Europe/Paris",
       "runtimeVersion": "V8",
       "exceptionLogging": "STACKDRIVER",
       "dependencies": {
         "enabledAdvancedServices": [
           { "userSymbol": "Drive", "serviceId": "drive", "version": "v3" }
         ]
       },
       "oauthScopes": [
         "https://www.googleapis.com/auth/drive.file"
       ],
       "webapp": {
         "executeAs": "USER_DEPLOYING",
         "access": "ANYONE_ANONYMOUS"
       }
     }
     ```

     Ce manifeste active le service avancé **Drive API v3** et limite les droits du script à `drive.file` : il ne peut voir **que les fichiers qu'il a lui-même créés**, pas le reste de ton Drive.
   - Ouvre `Code.gs` et remplace tout son contenu par celui de `tools/google_apps_script.gs`.
   - **Enregistre** (icône disquette ou `Ctrl+S`).
4. **Créer le dossier de collecte** : dans la barre du haut, choisis la fonction **`setup`** puis clique sur **Exécuter**.
   - Google demande une autorisation : **Examiner les autorisations** → choisis ton compte.
   - Un écran « Google n'a pas validé cette application » peut apparaître (normal : c'est ton propre script). Clique sur **Paramètres avancés** → **Accéder à flash-son-collecte (non sécurisé)** → **Autoriser**. La seule permission demandée concerne les fichiers créés par le script.
   - Le **Journal d'exécution** affiche : `Dossier de collecte : https://drive.google.com/drive/folders/...`. C'est là qu'arriveront les CSV (dossier `flash-son-illusion-data` dans ton Drive). **Ne partage pas ce dossier.**
5. **Déployer en application Web** : bouton bleu **Déployer** → **Nouveau déploiement** → roue dentée → **Application Web**.
   - Description : `v1`
   - **Exécuter en tant que : Moi** (le fichier est écrit dans *ton* Drive)
   - **Qui a accès : Tout le monde** (les participants n'ont pas de compte Google à utiliser)
   - **Déployer**, puis **copie l'URL de l'application Web**. Elle se termine par `/exec` :
     `https://script.google.com/macros/s/AKfycb.../exec`

> **Si tu modifies le script plus tard :** Déployer → **Gérer les déploiements** → crayon → Version : **Nouvelle version** → Déployer. L'URL reste la même. (Un « Nouveau déploiement » créerait une autre URL.)

## Étape 2 – Coller l'URL dans l'expérience

Dans `experiment/config.py` :

```python
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycb.../exec"
```

C'est tout. L'URL n'est pas un secret au sens strict (elle sera visible dans le dépôt public et dans le navigateur des participants), mais elle ne permet **que** d'ajouter un fichier : personne ne peut lire les données avec.

**Jeton optionnel.** Tu peux mettre la même chaîne (par ex. `"fs-7k2q"`) dans `SHARED_TOKEN` de `config.py` **et** dans `var SHARED_TOKEN = "..."` du script (puis *Nouvelle version* du déploiement). Le script refusera les envois sans ce jeton. Comme le dépôt est public, le jeton est lisible par tous : c'est un **filtre anti-robots, pas une sécurité**. Tu peux t'en passer.

## Étape 3 – Tester l'envoi

1. Lance l'expérience en local (voir README : `python -m http.server 8000`, puis <http://localhost:8000/?short=1>).
2. Fais la version courte jusqu'au bout. L'écran final doit afficher en petit **« Réponses envoyées. Tu peux fermer la page. »**
3. Vérifie qu'un fichier `flashson_<date>-<heure>-<code>.csv` est apparu dans le dossier Drive. Supprime-le ensuite (c'était un test).

Test sans navigateur (PowerShell), avec le corps d'exemple fourni :

```powershell
$url = "https://script.google.com/macros/s/AKfycb.../exec"
Invoke-RestMethod -Method Post -Uri $url -ContentType "text/plain" -InFile tests\fixtures\sample_payload.json
```

Réponse attendue : `ok=True status=stored` (puis `status=duplicate` si tu relances : l'anti-doublon fonctionne). Si tu as défini un jeton, la réponse est `invalid:token` (le fichier d'exemple contient le jeton `test-token`) : c'est aussi le comportement attendu. Supprime le fichier de test du Drive.

Si l'écran final affiche « L'envoi n'a pas marché : télécharger mes réponses » : vérifie l'URL (elle doit finir par `/exec`), que l'accès est bien **Tout le monde**, et que `setup` a été exécuté (sinon l'erreur `not_set_up` apparaît dans la console du navigateur, touche F12).

## Étape 4 – Publier sur GitHub (dépôt public) et activer GitHub Pages

1. Sur <https://github.com/new> : nom `flash-son-illusion`, **Public**, **sans** README ni licence (ils existent déjà). **Create repository**.
2. Vérifie qu'aucune donnée réelle ne sera publiée :

   ```powershell
   cd "C:\Users\pavel\OneDrive\Documents\L'X\3A\P1\Cognitive Sciences\flash-son-illusion"
   git status
   ```

   Aucun fichier `data/raw/*.csv` ne doit apparaître (le dossier est ignoré par `.gitignore`).
3. Enregistre ta modification de `config.py` puis envoie le dépôt :

   ```powershell
   git add experiment/config.py
   git commit -m "Adresse du script de collecte"
   git remote add origin https://github.com/<ton-compte>/flash-son-illusion.git
   git branch -M main
   git push -u origin main
   ```

4. Sur GitHub : **Settings → Pages → Build and deployment → Source : Deploy from a branch**, **Branch : `main`**, dossier **`/ (root)`**, **Save**.
5. Une à deux minutes plus tard, l'expérience est en ligne sur `https://<ton-compte>.github.io/flash-son-illusion/`. Fais une passation complète sur ce lien, avec un casque filaire, et vérifie l'arrivée du fichier dans le Drive.

## Récupérer les données

Télécharge les CSV du dossier Drive `flash-son-illusion-data` dans `data/raw/` puis lance le notebook `analysis/analysis.ipynb`. Ce dossier n'est **jamais** envoyé sur GitHub.

---

## Sécurité : ce qui est fait, ce qui reste à savoir

**Protections en place**
- **Aucun secret dans le dépôt** : pas de mot de passe, pas de clé. Le script s'exécute avec ton compte côté Google ; le dépôt ne contient que son adresse.
- **Écriture seule** : le script n'a pas de `doGet` ni aucune fonction de lecture. Connaître l'URL ne permet pas de voir les réponses des autres.
- **Moindre privilège** : portée OAuth `drive.file` (le script ne voit que ses propres fichiers).
- **Contrôles côté serveur** : taille maximale (200 Ko), en-tête CSV exact, nombre de colonnes et de lignes, caractères autorisés, pas de cellule pouvant être lue comme une formule par Excel ou Sheets, nom de fichier construit par le serveur à partir d'un identifiant au format strict (impossible d'écrire ailleurs ou d'écraser un fichier), anti-doublon sous verrou.
- **Données anonymes** : code aléatoire, tranche d'âge et type d'écoute seulement ; ni nom, ni e-mail, le script ne reçoit pas l'adresse IP (GitHub et Google, comme tout hébergeur, voient techniquement les connexions). Le CSV contient aussi la signature technique du navigateur (`user_agent`) et la taille de l'écran, utiles pour le contrôle du timing.
- **Données réelles hors de GitHub** : `data/raw/` est ignoré par git.

**Limites (à connaître)**
- Comme l'URL est publique, quelqu'un de mal intentionné pourrait envoyer de **faux fichiers bien formés**. Ils ne peuvent rien écraser et restent faciles à repérer (dates, timing, réponses). En cas d'abus : Déployer → Gérer les déploiements → **Archiver** (l'URL cesse de fonctionner), puis nouveau déploiement et nouvelle URL dans `config.py`.
- Le jeton optionnel est visible dans le dépôt : simple obfuscation.
- À la fin de la collecte, archive le déploiement pour fermer la porte.
