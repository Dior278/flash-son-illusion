/**
 * Récepteur de données « flash-son-illusion » — Google Apps Script (application Web).
 *
 * RÔLE UNIQUE : recevoir le CSV d'une session et l'AJOUTER comme fichier dans UN dossier
 * Google Drive dédié. Il n'existe aucune fonction pour lire, lister ou supprimer des données
 * (pas de doGet) : connaître l'URL ne permet donc pas de récupérer les réponses.
 *
 * Moindre privilège : le script n'a accès qu'aux fichiers QU'IL a créés (portée OAuth
 * « drive.file », voir appsscript.json) — pas au reste de votre Drive.
 *
 * Contrôles côté serveur :
 *   - taille maximale de la requête (MAX_BYTES) ;
 *   - identifiant de session au format strict, nom de fichier construit par le serveur ;
 *   - en-tête CSV identique à la liste attendue, nombre de colonnes par ligne, nombre de lignes,
 *     caractères autorisés, cellules ne pouvant pas être interprétées comme des formules ;
 *   - anti-doublon : verrou (LockService) + mémoire des sessions déjà reçues ;
 *   - jeton partagé optionnel (SHARED_TOKEN). ATTENTION : le dépôt GitHub étant public, ce jeton
 *     est visible par tous dans experiment/config.py ; c'est un simple filtre, pas une sécurité.
 *
 * Installation pas à pas : docs/DEPLOIEMENT.md
 */

var MAX_BYTES = 200000;          // doit correspondre à UPLOAD_MAX_BYTES (config.py)
var MAX_ROWS = 200;
var SHARED_TOKEN = "";           // optionnel ; même valeur que SHARED_TOKEN dans config.py
var FOLDER_NAME = "flash-son-illusion-data";

// En-tête attendu : doit être IDENTIQUE à CSV_COLUMNS dans experiment/config.py
// (vérifié automatiquement par tests/test_apps_script.js).
var EXPECTED_COLUMNS = [
  "participant_id",
  "session_id",
  "experiment_version",
  "timestamp_iso",
  "block",
  "trial_in_block",
  "trial_global",
  "condition",
  "n_flashes",
  "n_beeps",
  "beep_soa_ms",
  "flash_soa_ms_target",
  "is_catch",
  "part",
  "response",
  "correct",
  "rt_ms",
  "refresh_hz",
  "frame_ms",
  "flash_frames",
  "flash_dur_ms_actual",
  "flash_soa_ms_actual",
  "flash_late_ms",
  "max_frame_interval_ms",
  "n_dropped_frames",
  "audio_lead_ms",
  "audio_scheduled_late",
  "av_offset_est_ms",
  "audio_clock_drift_ms",
  "output_latency_ms",
  "base_latency_ms",
  "audio_sample_rate",
  "audio_mapping",
  "tab_hidden",
  "fullscreen",
  "age_bracket",
  "audio_device",
  "audio_check_score",
  "user_agent",
  "screen_w",
  "screen_h",
  "device_pixel_ratio",
  "random_seed",
  "aborted"
];

var SESSION_RE = /^\d{8}-\d{6}-[a-z0-9]{4}$/;
var CELL_RE = /^[A-Za-z0-9 ._:;\/()+\-]*$/;

/** À exécuter UNE FOIS depuis l'éditeur : crée le dossier de collecte et affiche son lien. */
function setup() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty("FOLDER_ID");
  if (!id) {
    var folder = Drive.Files.create({ name: FOLDER_NAME, mimeType: "application/vnd.google-apps.folder" });
    id = folder.id;
    props.setProperty("FOLDER_ID", id);
  }
  Logger.log("Dossier de collecte : https://drive.google.com/drive/folders/" + id);
  return id;
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function validate_(payload) {
  if (!payload || typeof payload !== "object") return "payload";
  if (SHARED_TOKEN && payload.token !== SHARED_TOKEN) return "token";
  var sid = String(payload.session_id || "");
  if (!SESSION_RE.test(sid)) return "session_id";
  var csv = payload.csv;
  if (typeof csv !== "string" || csv.length === 0) return "csv";
  var lines = csv.replace(/\n+$/, "").split("\n");
  if (lines[0] !== EXPECTED_COLUMNS.join(",")) return "header";
  if (lines.length < 2 || lines.length > MAX_ROWS + 1) return "rows";
  var sidCol = EXPECTED_COLUMNS.indexOf("session_id");
  for (var i = 1; i < lines.length; i++) {
    var cells = lines[i].split(",");
    if (cells.length !== EXPECTED_COLUMNS.length) return "columns@" + i;
    for (var j = 0; j < cells.length; j++) {
      var c = cells[j];
      if (!CELL_RE.test(c)) return "chars@" + i;
      // pas de formule (=, @) ; « + » ou « - » seulement devant un nombre
      if (/^[=@]/.test(c) || (/^[+\-]/.test(c) && !/^[+\-]?\d+(\.\d+)?$/.test(c))) return "cell@" + i;
    }
    if (cells[sidCol] !== sid) return "session_mismatch";
  }
  return null;
}

function doPost(e) {
  try {
    var raw = (e && e.postData && e.postData.contents) || "";
    if (raw.length > MAX_BYTES) return reply_({ ok: false, error: "too_large" });
    var payload;
    try { payload = JSON.parse(raw); } catch (err) { return reply_({ ok: false, error: "json" }); }
    var problem = validate_(payload);
    if (problem) return reply_({ ok: false, error: "invalid:" + problem });

    var sid = payload.session_id;
    var name = "flashson_" + sid + ".csv";        // nom construit par le serveur
    var lock = LockService.getScriptLock();
    if (!lock.tryLock(20000)) return reply_({ ok: false, error: "busy" });
    try {
      var props = PropertiesService.getScriptProperties();
      if (props.getProperty("s_" + sid)) return reply_({ ok: true, status: "duplicate" });
      var folderId = props.getProperty("FOLDER_ID");
      if (!folderId) return reply_({ ok: false, error: "not_set_up" });
      Drive.Files.create({ name: name, mimeType: "text/csv", parents: [folderId] },
                         Utilities.newBlob(payload.csv, "text/csv", name));
      props.setProperty("s_" + sid, String(new Date().getTime()));
    } finally {
      lock.releaseLock();
    }
    return reply_({ ok: true, status: "stored" });
  } catch (err) {
    return reply_({ ok: false, error: "server" });
  }
}
