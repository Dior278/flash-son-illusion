"""Paramètres de l'expérience « Illusion flash-son » (Shams, Kamitani & Shimojo, 2000).

Tous les paramètres modifiables sont regroupés ici. Ce fichier est lu à la fois
par l'expérience (dans le navigateur, via Pyodide) et par les scripts Python
du dossier `scripts/` (création de la liste d'essais, simulation).
"""

EXPERIMENT_NAME = "flash-son-illusion"
EXPERIMENT_VERSION = "2.0.0"

# ---------------------------------------------------------------------------
# Stimuli visuels (unités « hauteur d'écran », comme la version en ligne
# PsychoPy/Pavlovia de Flanagan et al., 2025)
# ---------------------------------------------------------------------------
BACKGROUND_COLOR = "#000000"     # fond noir (Shams et al., 2000)
DISK_COLOR = "#FFFFFF"           # disque blanc uniforme
FIXATION_COLOR = "#B0B0B0"
DISK_DIAMETER_H = 0.10           # diamètre = 10 % de la hauteur de l'écran (~2° à ~57 cm sur un portable 14")
DISK_Y_OFFSET_H = 0.25           # centre du disque à mi-chemin entre la croix et le bas de l'écran (~5° sous la fixation)
FIXATION_SIZE_H = 0.025

FLASH_DURATION_MS = 17           # 17 ms = 1 image à 60 Hz (Shams et al., 2002)
FLASH_SOA_MS = 50                # 50 ms entre deux flashs (Shams et al., 2000)
CATCH_FLASH_SOA_MS = 150         # essais « contrôle facile » : 2 flashs bien séparés

# ---------------------------------------------------------------------------
# Stimuli auditifs
# ---------------------------------------------------------------------------
BEEP_FREQ_HZ = 3500              # 3,5 kHz (Shams et al., 2002)
BEEP_DURATION_MS = 7             # 7 ms (Shams et al., 2002)
BEEP_RAMP_MS = 1                 # rampes cosinus de 1 ms (évite les clics)
BEEP_GAIN = 0.5                  # amplitude (0-1) ; le volume se règle sur l'ordinateur
CORE_BEEP_SOA_MS = 57            # 57 ms entre deux bips (Shams et al., 2000)

# Variante « écart » : dans la condition 1 flash + 2 bips, on écarte aussi les
# 2 bips de 200 ms (au lieu de 57 ms) pour montrer que l'illusion dépend du timing.
GAP_BEEP_SOA_MS = 200

# ---------------------------------------------------------------------------
# Plan expérimental (nombre de répétitions par condition) -- v2 : 58 essais
# ---------------------------------------------------------------------------
REPS_CORE = {          # (n_flashes, n_beeps) : répétitions (SOA bips = 57 ms)
    (1, 0): 8,
    (1, 1): 8,
    (1, 2): 8,         # illusion de FISSION (Shams et al., 2000)
    (2, 0): 8,
    (2, 1): 8,         # illusion de FUSION (Andersen, Tiippana & Sams, 2004)
    (2, 2): 8,
}
REPS_GAP = 6           # 1 flash + 2 bips séparés de 200 ms
REPS_CATCH = 4         # 2 flashs séparés de 150 ms, sans son (contrôle d'attention)

PRACTICE_TRIALS = [    # (n_flashes, n_beeps, beep_soa_ms, flash_soa_ms) avec correction
    (1, 0, 0, 0),
    (2, 0, 0, FLASH_SOA_MS),
    (2, 2, CORE_BEEP_SOA_MS, FLASH_SOA_MS),
]
AUDIO_CHECK_TRIALS = [  # (n_beeps, beep_soa_ms) : « combien de bips ? » (pas de flash)
    (2, CORE_BEEP_SOA_MS), (1, 0), (2, CORE_BEEP_SOA_MS),
]
MAX_SAME_CONDITION_IN_A_ROW = 3

# ---------------------------------------------------------------------------
# Questions posées (réduites au strict nécessaire pour l'analyse)
# ---------------------------------------------------------------------------
# Tranche d'âge : la fenêtre temporelle d'intégration audio-visuelle s'élargit avec
# l'âge (Setti et al., 2011 ; McGovern et al., 2014) -> covariable utile, sans être identifiante.
AGE_BRACKETS = [("18-21", "18–21 ans"), ("22-25", "22–25 ans"), ("26-35", "26–35 ans"), ("36+", "36 ans et +")]
# Matériel audio : le Bluetooth retarde le son de 100–300 ms -> critère d'exclusion.
AUDIO_DEVICES = [("wired", "Casque ou écouteurs filaires"), ("speakers", "Haut-parleurs"),
                 ("bluetooth", "Bluetooth (AirPods…)")]

# ---------------------------------------------------------------------------
# Déroulement temporel d'un essai
# ---------------------------------------------------------------------------
ITI_MIN_MS = 700       # croix de fixation seule avant le stimulus (durée tirée au hasard)
ITI_MAX_MS = 1100
AUDIO_LEAD_MS = 250    # le son est programmé (Web Audio) ~250 ms avant le flash
POST_STIM_MS = 300     # écran noir après le stimulus, avant la question
RESPONSE_KEYS = {"Digit1": 1, "Numpad1": 1, "Digit2": 2, "Numpad2": 2}  # touches physiques (QWERTY/AZERTY)

# Latence d'affichage supposée : une image dessinée dans le rappel
# requestAnimationFrame de timestamp t est affichée vers t + N périodes.
# 1 est une valeur typique ; à ajuster avec tools/timing-check (photodiode + micro).
DISPLAY_LATENCY_FRAMES = 1

# ---------------------------------------------------------------------------
# Contrôles de qualité enregistrés (les exclusions sont faites dans le notebook)
# ---------------------------------------------------------------------------
DROPPED_FRAME_FACTOR = 1.5   # une image est « perdue » si l'écart entre 2 rafraîchissements > 1,5 période
REFRESH_ESTIMATE_FRAMES = 120

# ---------------------------------------------------------------------------
# Envoi des données
# ---------------------------------------------------------------------------
# Les réponses sont envoyées AUTOMATIQUEMENT à la fin, vers une petite application
# Google Apps Script déployée par l'expérimentateur (tools/google_apps_script.gs,
# guide : docs/DEPLOIEMENT.md). Elle ne fait qu'AJOUTER un fichier CSV dans un dossier
# Google Drive dédié ; elle ne permet pas de lire ou lister les données.
# Tant que l'URL n'est pas renseignée, rien n'est envoyé et un petit bouton
# de téléchargement apparaît à la fin (pratique pour tester en local).
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzIqniiY6nsk2GHrFk-aI83w0wplFrhWN3yvnbYtzoD-RtkIEaXiRtWzkjFdalZHL2auw/exec"

# Jeton partagé optionnel (doit être identique dans le script Apps Script).
# ATTENTION : le dépôt est public, donc ce jeton est lisible par tous. Ce n'est
# qu'un filtre contre les envois automatiques « au hasard », PAS une sécurité.
SHARED_TOKEN = ""

UPLOAD_RETRY_DELAYS_S = [0, 1, 2, 4]   # tentatives et attentes entre elles (s)
UPLOAD_TIMEOUT_S = 15
UPLOAD_MAX_BYTES = 200_000            # même limite côté serveur

# Copie de secours dans le navigateur (localStorage) après chaque essai ; les
# sessions non envoyées sont renvoyées discrètement à la visite suivante.

# Colonnes du fichier CSV (une ligne par essai), dans l'ordre.
CSV_COLUMNS = [
    # identification / session
    "participant_id", "session_id", "experiment_version", "timestamp_iso",
    # essai
    "block", "trial_in_block", "trial_global", "condition", "n_flashes", "n_beeps",
    "beep_soa_ms", "flash_soa_ms_target", "is_catch", "part",
    # réponse
    "response", "correct", "rt_ms",
    # diagnostics de timing (mesurés par le navigateur)
    "refresh_hz", "frame_ms", "flash_frames", "flash_dur_ms_actual", "flash_soa_ms_actual",
    "flash_late_ms", "max_frame_interval_ms", "n_dropped_frames",
    "audio_lead_ms", "audio_scheduled_late", "av_offset_est_ms", "audio_clock_drift_ms",
    "output_latency_ms", "base_latency_ms", "audio_sample_rate", "audio_mapping",
    "tab_hidden", "fullscreen",
    # informations participant / matériel (répétées sur chaque ligne)
    "age_bracket", "audio_device",
    "audio_check_score", "user_agent", "screen_w", "screen_h", "device_pixel_ratio",
    "random_seed", "aborted",
]
