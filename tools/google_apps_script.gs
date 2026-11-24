/**
 * Récepteur de données GRATUIT avec Google Apps Script (alternative à DataPipe).
 *
 * Chaque participant qui termine l'expérience envoie son CSV ; ce script l'enregistre
 * comme un fichier dans un dossier de VOTRE Google Drive.
 *
 * Mise en place (5 minutes) :
 *  1. Créez un dossier dans Google Drive (ex. « flash-son-data ») et copiez son identifiant
 *     (la fin de l'URL : https://drive.google.com/drive/folders/<IDENTIFIANT>).
 *  2. Allez sur https://script.google.com -> Nouveau projet, collez ce fichier, remplacez FOLDER_ID.
 *  3. Déployer -> Nouveau déploiement -> type « Application Web »
 *       - Exécuter en tant que : Moi
 *       - Qui a accès : Tout le monde
 *     Autorisez l'accès à Drive, puis copiez l'URL qui se termine par /exec.
 *  4. Collez cette URL dans experiment/config.py :  APPS_SCRIPT_URL = "https://script.google.com/macros/s/.../exec"
 *  5. Faites un essai complet et vérifiez que le fichier apparaît dans le dossier.
 *
 * Remarque : l'URL /exec est publique ; n'importe qui la connaissant peut y déposer un fichier.
 * Désactivez le déploiement quand la collecte est terminée.
 */
var FOLDER_ID = "REMPLACER_PAR_L_IDENTIFIANT_DU_DOSSIER";

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var name = String(payload.filename || ("flashson_" + new Date().getTime() + ".csv"))
                 .replace(/[^A-Za-z0-9_.-]/g, "_");
    var data = String(payload.data || "");
    if (data.length > 5 * 1024 * 1024) throw new Error("fichier trop gros");
    var folder = DriveApp.getFolderById(FOLDER_ID);
    if (folder.getFilesByName(name).hasNext()) name = name.replace(/\.csv$/, "") + "_" + new Date().getTime() + ".csv";
    folder.createFile(name, data, MimeType.CSV);
    return ContentService.createTextOutput(JSON.stringify({ ok: true, filename: name }))
                         .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
                         .setMimeType(ContentService.MimeType.JSON);
  }
}
