"""Illusion flash-son (« double flash ») -- expérience en ligne, écrite en Python.

Référence : Shams, L., Kamitani, Y. & Shimojo, S. (2000). What you see is what
you hear. Nature, 408, 788. https://doi.org/10.1038/35048669

Ce script tourne DANS LE NAVIGATEUR du participant grâce à Pyodide (CPython
compilé en WebAssembly). Il pilote directement les API du navigateur :
  * <canvas> + requestAnimationFrame  -> flashs synchronisés au rafraîchissement de l'écran
  * Web Audio API (AudioContext)       -> bips programmés à l'échantillon près
  * localStorage / fetch               -> copie de secours + envoi automatique des données
                                         (Google Apps Script, voir docs/DEPLOIEMENT.md)

Principe de synchronisation audio-visuelle (voir docs/TECHNIQUE.md, section « Timing ») :
  1. on estime la période de rafraîchissement de l'écran (médiane de 120 images) ;
  2. ~250 ms avant le flash, dans un rappel requestAnimationFrame de timestamp t,
     on fixe l'image du flash sur la grille des rafraîchissements : T = t + k * période ;
  3. on convertit l'instant d'affichage prévu (T + latence d'affichage) dans
     l'horloge audio (AudioContext.getOutputTimestamp) et on programme les bips à
     l'avance (AudioBufferSourceNode.start(t_audio)) : pas de gigue liée à Python ;
  4. le flash est dessiné dans le rappel requestAnimationFrame correspondant, et on
     enregistre ce qui s'est réellement passé (retard du flash, images perdues,
     avance de programmation du son, dérive des horloges...).

Comme dans le script « beep_flash.py » du cours (PCBS), un essai est décrit par
une liste d'événements (instant, stimulus) relatifs au premier flash.
"""

import asyncio
import csv
import gc
import io
import json
import math
import random
import re
import statistics
import time

import js
from js import document, window, performance
from pyodide.ffi import create_proxy, create_once_callable, to_js

import config as C


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def is_null(x):
    """Vrai pour None, JavaScript null (pyodide.ffi.jsnull, Pyodide >= 0.27) ou undefined."""
    return x is None or type(x).__name__ == "JsNull"


def js_obj(d):
    """Convertit un dict Python en objet JavaScript."""
    return to_js(d, dict_converter=js.Object.fromEntries)


def url_params():
    p = js.URLSearchParams.new(window.location.search)
    return {k: p.get(k) for k in ("short", "debug", "mode") if p.has(k)}


PARAMS = url_params()
DEBUG = PARAMS.get("debug") == "1"


def log(*args):
    if DEBUG:
        js.console.log("[flash-son]", *[str(a) for a in args])


def set_phase(name):
    """Expose la phase en cours (utilisé par le test automatique headless)."""
    document.body.dataset.phase = name


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def now_iso():
    return js.Date.new().toISOString()


def fmt(x, nd=2):
    if x is None:
        return ""
    if isinstance(x, float):
        if math.isnan(x):
            return ""
        return f"{x:.{nd}f}"
    return x


def loop():
    return asyncio.get_event_loop()


# ---------------------------------------------------------------------------
# Écran : canvas plein écran (stimuli) + calque HTML (consignes, formulaires)
# ---------------------------------------------------------------------------

class Stage:
    def __init__(self):
        self.canvas = document.getElementById("stage")
        self.ui = document.getElementById("ui")
        self.ctx = self.canvas.getContext("2d", js_obj({"alpha": False}))
        self.progress = None
        self._resize_proxy = create_proxy(lambda *a: self.resize())
        window.addEventListener("resize", self._resize_proxy)
        self.resize()

    def resize(self):
        self.dpr = window.devicePixelRatio or 1
        self.W = window.innerWidth
        self.H = window.innerHeight
        self.canvas.width = int(self.W * self.dpr)
        self.canvas.height = int(self.H * self.dpr)
        self.canvas.style.width = f"{self.W}px"
        self.canvas.style.height = f"{self.H}px"
        self.ctx.setTransform(self.dpr, 0, 0, self.dpr, 0, 0)
        self.clear()

    # --- calque HTML ---
    def show_html(self, html):
        self.ui.innerHTML = html
        self.ui.style.display = "flex"
        self.ui.scrollTop = 0
        document.body.classList.remove("task")

    def hide_html(self):
        self.ui.style.display = "none"
        self.ui.innerHTML = ""
        document.body.classList.add("task")

    # --- dessin sur le canvas (unités : pixels CSS ; tailles en fraction de hauteur) ---
    def clear(self, fixation=True):
        c = self.ctx
        c.fillStyle = C.BACKGROUND_COLOR
        c.fillRect(0, 0, self.W, self.H)
        if self.progress is not None:
            c.fillStyle = "#1c1c1c"
            c.fillRect(0, 0, self.W, 4)
            c.fillStyle = "#3a3a3a"
            c.fillRect(0, 0, self.W * self.progress, 4)
        if fixation:
            self.fixation()

    def fixation(self):
        c = self.ctx
        s = C.FIXATION_SIZE_H * self.H / 2
        cx, cy = self.W / 2, self.H / 2
        c.strokeStyle = C.FIXATION_COLOR
        c.lineWidth = max(2, self.H * 0.004)
        c.beginPath()
        c.moveTo(cx - s, cy)
        c.lineTo(cx + s, cy)
        c.moveTo(cx, cy - s)
        c.lineTo(cx, cy + s)
        c.stroke()

    def disk(self):
        c = self.ctx
        r = C.DISK_DIAMETER_H * self.H / 2
        c.fillStyle = C.DISK_COLOR
        c.beginPath()
        c.arc(self.W / 2, self.H / 2 + C.DISK_Y_OFFSET_H * self.H, r, 0, 2 * math.pi)
        c.fill()

    def text(self, lines, y_frac=0.5, size_frac=0.045, color="#e8e8e8"):
        c = self.ctx
        c.fillStyle = color
        c.textAlign = "center"
        c.textBaseline = "middle"
        size = max(16, int(self.H * size_frac))
        c.font = f"{size}px system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
        y0 = self.H * y_frac - (len(lines) - 1) * size * 0.75
        for i, line in enumerate(lines):
            c.fillText(line, self.W / 2, y0 + i * size * 1.5)


# ---------------------------------------------------------------------------
# Boucle d'images (requestAnimationFrame) : le gestionnaire Python est appelé
# de façon SYNCHRONE dans chaque rappel rAF, au rythme de l'écran.
# ---------------------------------------------------------------------------

class FrameLoop:
    def __init__(self):
        self.handler = None
        self.pending = False      # une seule chaîne de rappels rAF à la fois
        self._proxy = create_proxy(self._on_frame)

    def run(self, handler):
        """handler(ts) -> True pour continuer, False pour s'arrêter."""
        self.handler = handler
        if not self.pending:
            self.pending = True
            window.requestAnimationFrame(self._proxy)

    def _on_frame(self, ts):
        self.pending = False
        h = self.handler
        if h is None:
            return
        try:
            keep = h(ts)
        except Exception as e:  # on ne veut jamais bloquer la boucle silencieusement
            js.console.error("Erreur dans la boucle d'images : " + repr(e))
            keep = False
        if keep:
            self.pending = True
            window.requestAnimationFrame(self._proxy)
        elif self.handler is h:
            self.handler = None


# ---------------------------------------------------------------------------
# Clavier
# ---------------------------------------------------------------------------

class Keyboard:
    def __init__(self):
        self.waiter = None
        self._proxy = create_proxy(self._on_key)
        document.addEventListener("keydown", self._proxy)

    def _on_key(self, ev):
        if self.waiter is None:
            return
        fut, codes = self.waiter
        code = ev.code
        if code in codes or (code == "" and ev.key in codes):
            ev.preventDefault()
            self.waiter = None
            document.body.dataset.waiting = ""
            if not fut.done():
                fut.set_result((code, float(ev.timeStamp)))

    async def wait(self, codes):
        fut = loop().create_future()
        self.waiter = (fut, set(codes))
        document.body.dataset.waiting = ",".join(sorted(codes))  # utilisé par le test automatique
        return await fut


# ---------------------------------------------------------------------------
# Audio : Web Audio API
# ---------------------------------------------------------------------------

class Audio:
    def __init__(self):
        AC = getattr(window, "AudioContext", None) or getattr(window, "webkitAudioContext", None)
        if AC is None:
            raise RuntimeError("Ce navigateur ne gère pas la Web Audio API.")
        try:
            self.ctx = AC.new(js_obj({"latencyHint": "interactive"}))
        except Exception:
            self.ctx = AC.new()
        self.out = self.ctx.createGain()
        self.out.gain.value = 1.0
        self.out.connect(self.ctx.destination)
        self.sample_rate = float(self.ctx.sampleRate)
        self.beep = self.make_tone(C.BEEP_FREQ_HZ, C.BEEP_DURATION_MS, C.BEEP_RAMP_MS, C.BEEP_GAIN)
        self.timing_tone = self.make_tone(440, 100, 5, 0.4)

    def make_tone(self, freq, dur_ms, ramp_ms, amp):
        sr = self.sample_rate
        n = max(1, int(round(sr * dur_ms / 1000)))
        nr = max(1, int(round(sr * ramp_ms / 1000)))
        samples = []
        for i in range(n):
            env = 1.0
            if i < nr:
                env = 0.5 * (1 - math.cos(math.pi * i / nr))
            elif i >= n - nr:
                env = 0.5 * (1 - math.cos(math.pi * (n - 1 - i) / nr))
            samples.append(amp * env * math.sin(2 * math.pi * freq * i / sr))
        buf = self.ctx.createBuffer(1, n, sr)
        buf.copyToChannel(js.Float32Array.new(to_js(samples)), 0)
        return buf

    def resume(self):
        """À appeler pendant un clic (geste utilisateur), sinon le son reste bloqué."""
        try:
            self.ctx.resume()
        except Exception:
            pass

    def latencies(self):
        out_lat = getattr(self.ctx, "outputLatency", None)
        base_lat = getattr(self.ctx, "baseLatency", None)
        return (float(out_lat) * 1000 if out_lat is not None else float("nan"),
                float(base_lat) * 1000 if base_lat is not None else float("nan"))

    def clock_offset(self):
        """Relation entre l'horloge audio et l'horloge de la page (ms).

        Retourne (offset_ms, méthode) avec : t_audio_s = (t_perf_ms + offset_ms) / 1000,
        où t_audio_s est l'instant à programmer pour que le son SORTE à t_perf_ms.
        """
        try:
            ots = self.ctx.getOutputTimestamp()
            ct, pt = float(ots.contextTime), float(ots.performanceTime)
            if ct > 0 and pt > 0:
                return ct * 1000 - pt, "outputTimestamp"
        except Exception:
            pass
        out_lat, base_lat = self.latencies()
        lat = out_lat if not math.isnan(out_lat) else (base_lat if not math.isnan(base_lat) else 0.0)
        return float(self.ctx.currentTime) * 1000 - float(performance.now()) - lat, "currentTime-latency"

    def schedule(self, buf, t_audio_s):
        src = self.ctx.createBufferSource()
        src.buffer = buf
        src.connect(self.out)
        src.start(t_audio_s)
        return src


# ---------------------------------------------------------------------------
# Un essai audio-visuel, exécuté image par image dans requestAnimationFrame
# ---------------------------------------------------------------------------

class StimTrial:
    """Présente n flashs et n bips, puis affiche la question.

    Événements relatifs à l'instant d'affichage du 1er flash (t = 0) :
      flashs : 0 et, si 2 flashs, k images plus tard (k = arrondi(SOA / période))
      bips   : 0 et, si 2 bips, beep_soa_ms plus tard
    """

    def __init__(self, exp, n_flashes, n_beeps, beep_soa_ms, flash_soa_ms, iti_ms, prompt_lines):
        self.exp, self.stage, self.audio = exp, exp.stage, exp.audio
        self.nf, self.nb = n_flashes, n_beeps
        self.beep_soa = beep_soa_ms
        self.flash_soa_target = flash_soa_ms
        self.iti = iti_ms
        self.prompt_lines = prompt_lines
        P = exp.frame_ms
        self.P = P
        self.flash_frames = max(1, int(round(C.FLASH_DURATION_MS / P)))
        self.flash_gap_frames = max(self.flash_frames + 1, int(round(flash_soa_ms / P))) if n_flashes == 2 else 0
        self.fut = loop().create_future()
        self.t_start = None
        self.T_draw = None            # timestamp rAF prévu pour le 1er flash
        self.flash_on = []            # timestamps rAF réels d'apparition des flashs
        self.flash_off = []
        self.frames_in_window = []
        self.disk_visible = False
        self.disk_frames_left = 0
        self.next_flash = 0
        self.end_ts = None
        self.diag = {}
        self.hidden_at_start = exp.hidden_count

    # -- planification ------------------------------------------------------
    def plan(self, ts):
        P = self.P
        lead_frames = max(2, int(round(C.AUDIO_LEAD_MS / P)))
        self.T_draw = ts + lead_frames * P
        T_vis = self.T_draw + C.DISPLAY_LATENCY_FRAMES * P  # instant prévu d'affichage
        offset_ms, method = self.audio.clock_offset()
        self.offset_at_plan = offset_ms
        self.diag["audio_mapping"] = method
        self.beep_audio_times = []
        if self.nb > 0:
            beep_times = [0.0] + ([float(self.beep_soa)] if self.nb == 2 else [])
            now_ctx = float(self.audio.ctx.currentTime)
            for bt in beep_times:
                t_audio = (T_vis + bt + offset_ms) / 1000.0
                self.audio.schedule(self.audio.beep, t_audio)
                self.beep_audio_times.append(t_audio)
            lead = (self.beep_audio_times[0] - now_ctx) * 1000
            self.diag["audio_lead_ms"] = lead
            self.diag["audio_scheduled_late"] = int(lead < 5)
        else:
            self.diag["audio_lead_ms"] = float("nan")
            self.diag["audio_scheduled_late"] = 0
        flash_ends = (self.flash_gap_frames + self.flash_frames) * P if self.nf == 2 else self.flash_frames * P
        if self.nf == 0:
            flash_ends = 0
        beep_ends = (self.beep_soa if self.nb == 2 else 0) + C.BEEP_DURATION_MS if self.nb else 0
        self.end_ts = self.T_draw + max(flash_ends, beep_ends) + C.POST_STIM_MS

    # -- rappel par image ------------------------------------------------------
    def on_frame(self, ts):
        st = self.stage
        P = self.P
        if self.t_start is None:
            self.t_start = ts
            st.clear()
            self.plan_at = ts + max(0, self.iti - C.AUDIO_LEAD_MS)
            return True
        if self.T_draw is None:
            if ts >= self.plan_at:
                self.plan(ts)
            return True
        if ts >= self.T_draw - 2.5 * P and (not self.end_ts or ts <= self.end_ts + P):
            self.frames_in_window.append(ts)
        # extinction du disque après le bon nombre d'images
        if self.disk_visible:
            self.disk_frames_left -= 1
            if self.disk_frames_left <= 0:
                st.clear()
                self.disk_visible = False
                self.flash_off.append(ts)
        # apparition des flashs
        if self.next_flash < self.nf:
            target = self.T_draw + (0 if self.next_flash == 0 else self.flash_gap_frames * P)
            if ts >= target - P / 2 and not self.disk_visible:
                st.clear()
                st.disk()
                self.disk_visible = True
                self.disk_frames_left = self.flash_frames
                self.flash_on.append(ts)
                self.next_flash += 1
        # fin de l'essai : affichage de la question
        if ts >= self.end_ts and not self.disk_visible and self.next_flash >= self.nf:
            st.clear(fixation=False)
            st.text(self.prompt_lines)
            self.prompt_ts = ts
            self.finish()
            return False
        return True

    def finish(self):
        P = self.P
        d = self.diag
        d["frame_ms"] = P
        d["refresh_hz"] = 1000.0 / P
        d["flash_frames"] = self.flash_frames
        if self.flash_on:
            d["flash_late_ms"] = self.flash_on[0] - self.T_draw
            durs = [off - on for on, off in zip(self.flash_on, self.flash_off)]
            d["flash_dur_ms_actual"] = statistics.mean(durs) if durs else float("nan")
            d["flash_soa_ms_actual"] = (self.flash_on[1] - self.flash_on[0]) if len(self.flash_on) > 1 else float("nan")
        else:
            d["flash_late_ms"] = float("nan")
            d["flash_dur_ms_actual"] = float("nan")
            d["flash_soa_ms_actual"] = float("nan")
        fr = self.frames_in_window
        ints = [b - a for a, b in zip(fr[:-1], fr[1:])]
        d["max_frame_interval_ms"] = max(ints) if ints else float("nan")
        d["n_dropped_frames"] = sum(max(0, int(round(i / P)) - 1) for i in ints if i > C.DROPPED_FRAME_FACTOR * P)
        # décalage estimé son - image pour le 1er événement (négatif = son en avance)
        if self.nb > 0:
            ref = self.flash_on[0] if self.flash_on else self.T_draw
            d["av_offset_est_ms"] = self.T_draw - ref
        else:
            d["av_offset_est_ms"] = float("nan")
        offset_after, _ = self.audio.clock_offset()
        d["audio_clock_drift_ms"] = offset_after - self.offset_at_plan
        out_lat, base_lat = self.audio.latencies()
        d["output_latency_ms"], d["base_latency_ms"] = out_lat, base_lat
        d["audio_sample_rate"] = self.audio.sample_rate
        d["tab_hidden"] = int(self.exp.hidden_count > self.hidden_at_start or document.visibilityState != "visible")
        d["fullscreen"] = int(not is_null(document.fullscreenElement))
        d["prompt_visible_ts"] = self.prompt_ts + C.DISPLAY_LATENCY_FRAMES * P
        if not self.fut.done():
            self.fut.set_result(d)

    async def run(self):
        self.exp.frames.run(self.on_frame)
        return await self.fut


# ---------------------------------------------------------------------------
# Écrans HTML (textes courts : une idée par écran)
# ---------------------------------------------------------------------------

SAFE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def clean_cell(v):
    """Valeur CSV « sûre » : uniquement lettres, chiffres et . _ : ; / ( ) + - espace.
    Donc jamais de virgule, guillemet ni retour à la ligne (même règle que le serveur)."""
    if isinstance(v, float):
        v = fmt(v)
    return re.sub(r"[^A-Za-z0-9 ._:;/()+\-]", " ", str(v))


def choice_buttons(prefix, pairs):
    return "".join(f'<button class="choice" id="{prefix}-{i}">{esc(lab)}</button>' for i, (_, lab) in enumerate(pairs))


class Experiment:
    def __init__(self, trials_csv_text):
        self.stage = Stage()
        self.frames = FrameLoop()
        self.keys = Keyboard()
        self.audio = None
        self.rows = []
        self.info = {}
        self.frame_ms = 1000 / 60
        self.hidden_count = 0
        self.trial_global = 0
        self.aborted = 0
        self.session_id = self._make_session_id()
        # code participant aléatoire : aucune donnée nominative n'est demandée
        self.participant_id = "P" + "".join(random.choice(SAFE_ALPHABET.upper()) for _ in range(6))
        self.seed = int(js.Math.floor(js.Math.random() * 2 ** 31))
        self.rng = random.Random(self.seed)
        self.trials = list(csv.DictReader(io.StringIO(trials_csv_text)))
        for t in self.trials:
            for k in ("n_flashes", "n_beeps", "beep_soa_ms", "flash_soa_ms", "is_catch"):
                t[k] = int(t[k])
        self._vis_proxy = create_proxy(self._on_visibility)
        document.addEventListener("visibilitychange", self._vis_proxy)
        self.storage_key = f"{C.EXPERIMENT_NAME}:{self.session_id}"

    @staticmethod
    def _make_session_id():
        d = js.Date.new()
        stamp = f"{d.getFullYear():04d}{d.getMonth() + 1:02d}{d.getDate():02d}-{d.getHours():02d}{d.getMinutes():02d}{d.getSeconds():02d}"
        return stamp + "-" + "".join(random.choice(SAFE_ALPHABET) for _ in range(4))

    def _on_visibility(self, *args):
        if document.visibilityState != "visible":
            self.hidden_count += 1

    # -- attente d'un clic sur un bouton -----------------------------------------
    async def click(self, ids, before=None):
        fut = loop().create_future()
        proxies = []
        for bid in ids:
            node = document.getElementById(bid)

            def handler(ev, bid=bid):
                if before is not None and before(bid) is False:
                    return
                if not fut.done():
                    fut.set_result(bid)
            p = create_proxy(handler)
            proxies.append((node, p))
            node.addEventListener("click", p)
        res = await fut
        for node, p in proxies:
            try:
                node.removeEventListener("click", p)
            except Exception:
                pass
            p.destroy()
        return res

    async def choose(self, title, pairs, prefix, extra=""):
        self.stage.show_html(f'<div class="card"><h2>{title}</h2>{extra}<div class="choices">{choice_buttons(prefix, pairs)}</div></div>')
        bid = await self.click([f"{prefix}-{i}" for i in range(len(pairs))])
        return pairs[int(bid.rsplit("-", 1)[1])][0]

    # -- écrans -----------------------------------------------------------------
    async def screen_welcome(self):
        set_phase("welcome")
        self.stage.show_html("""
        <div class="card">
          <h1>Le flash et le son</h1>
          <p class="lead">Un petit jeu de perception : compte des flashs.<br>
             ≈ 4 minutes, sur ordinateur, avec du son.</p>
          <label class="check"><input type="checkbox" id="consent"> J'ai 18 ans ou plus et j'accepte de participer.
             Mes réponses sont <b>anonymes</b> (ni nom, ni e-mail).</label>
          <label class="check"><input type="checkbox" id="epilepsy"> Je ne suis pas sujet·te à l'épilepsie photosensible
             (il y a de brefs flashs).</label>
          <p class="error" id="err"></p>
          <button id="go" class="primary">Commencer</button>
          <p class="small">Projet de cours de sciences cognitives (École polytechnique). Tu peux arrêter à tout moment avec Échap.</p>
        </div>""")

        def check(_):
            if not document.getElementById("consent").checked or not document.getElementById("epilepsy").checked:
                document.getElementById("err").textContent = "Coche les deux cases pour participer."
                return False
            return True
        await self.click(["go"], before=check)

    async def screen_info(self):
        set_phase("age")
        self.info["age_bracket"] = await self.choose("Ton âge ?", C.AGE_BRACKETS, "age")
        set_phase("audio_device")
        dev = await self.choose("Tu écoutes le son avec…", C.AUDIO_DEVICES, "dev")
        if dev == "bluetooth":
            set_phase("bluetooth")
            dev = await self.choose(
                "Le Bluetooth retarde le son",
                [("wired", "Je passe en filaire"), ("speakers", "Je passe aux haut-parleurs"), ("bluetooth", "Je reste en Bluetooth")],
                "bt", extra="<p class='lead'>L'illusion risque de disparaître. Si tu peux, change.</p>")
        self.info["audio_device"] = dev

    async def screen_setup(self):
        set_phase("setup")
        self.stage.show_html("""
        <div class="card">
          <h2>Installe-toi</h2>
          <ul class="big">
            <li>Endroit calme</li>
            <li>À une longueur de bras de l'écran</li>
            <li>Volume vers 70–80 %</li>
          </ul>
          <button id="go" class="primary">Plein écran et son</button>
        </div>""")

        def unlock(_):
            # Ces deux appels DOIVENT être faits pendant le clic (règle des navigateurs).
            self.audio = Audio()
            self.audio.resume()
            try:
                el = document.documentElement
                if hasattr(el, "requestFullscreen"):
                    el.requestFullscreen()
                elif hasattr(el, "webkitRequestFullscreen"):
                    el.webkitRequestFullscreen()
            except Exception:
                pass
            return True
        await self.click(["go"], before=unlock)
        await asyncio.sleep(0.6)  # laisser le temps au plein écran de s'installer
        self.stage.resize()

    async def screen_sound_check(self):
        set_phase("soundcheck")
        self.stage.show_html("""
        <div class="card">
          <h2>Règle le volume</h2>
          <p class="lead">Les bips doivent être nets, pas désagréables.</p>
          <button id="play">▶ Écouter</button>
          <p class="small" id="hint"></p>
          <button id="ok" class="primary">C'est bon</button>
          <button id="none" class="link">Je n'entends rien</button>
        </div>""")

        def play(_):
            self.audio.resume()
            t0 = float(self.audio.ctx.currentTime) + 0.1
            for i in range(6):
                self.audio.schedule(self.audio.beep, t0 + i * 0.35)
            return False
        play_node = document.getElementById("play")
        play_proxy = create_proxy(play)
        play_node.addEventListener("click", play_proxy)
        while (await self.click(["ok", "none"])) != "ok":
            document.getElementById("hint").textContent = ("Vérifie le volume, la sortie audio et que l'onglet n'est pas en sourdine, "
                                                           "puis réécoute.")
        play_node.removeEventListener("click", play_proxy)
        play_proxy.destroy()

    async def estimate_refresh(self):
        set_phase("refresh")
        self.stage.hide_html()
        self.stage.clear(fixation=False)
        self.stage.text(["Préparation…"], size_frac=0.035, color="#888")
        stamps = []
        fut = loop().create_future()

        def h(ts):
            stamps.append(ts)
            if len(stamps) >= C.REFRESH_ESTIMATE_FRAMES:
                fut.set_result(True)
                return False
            return True
        self.frames.run(h)
        await fut
        ints = sorted(b - a for a, b in zip(stamps[:-1], stamps[1:]))
        med = statistics.median(ints)
        self.frame_ms = med
        self.refresh_info = dict(refresh_hz=1000 / med, frame_ms=med,
                                 frame_sd=statistics.pstdev(ints),
                                 frac_irregular=sum(abs(i - med) > 0.25 * med for i in ints) / len(ints))
        log("refresh", self.refresh_info)

    async def message(self, phase, html, after="pour continuer"):
        set_phase(phase)
        self.stage.show_html(f'<div class="card">{html}<p class="key"><span class="kbd">Espace</span> {after}</p></div>')
        await self.keys.wait(["Space"])

    # -- enregistrement d'un essai -----------------------------------------------
    def add_row(self, block, idx, t, response, rt, diag):
        self.trial_global += 1
        nf, nb = t["n_flashes"], t["n_beeps"]
        expected = nf if not block.startswith("audiocheck") else nb
        row = dict(
            participant_id=self.participant_id, session_id=self.session_id,
            experiment_version=C.EXPERIMENT_VERSION, timestamp_iso=now_iso(),
            block=block, trial_in_block=idx, trial_global=self.trial_global,
            condition=t["condition"], n_flashes=nf, n_beeps=nb,
            beep_soa_ms=t["beep_soa_ms"], flash_soa_ms_target=t["flash_soa_ms"], is_catch=t["is_catch"], part=t["part"],
            response=response if response is not None else "",
            correct=int(response == expected) if response is not None else "",
            rt_ms=rt,
            age_bracket=self.info.get("age_bracket", ""), audio_device=self.info.get("audio_device", ""),
            audio_check_score=self.info.get("audio_check_score", ""),
            user_agent=str(window.navigator.userAgent), screen_w=int(window.screen.width), screen_h=int(window.screen.height),
            device_pixel_ratio=float(window.devicePixelRatio or 1), random_seed=self.seed, aborted=0,
        )
        for k in ("refresh_hz", "frame_ms", "flash_frames", "flash_dur_ms_actual", "flash_soa_ms_actual", "flash_late_ms",
                  "max_frame_interval_ms", "n_dropped_frames", "audio_lead_ms", "audio_scheduled_late",
                  "av_offset_est_ms", "audio_clock_drift_ms", "output_latency_ms", "base_latency_ms",
                  "audio_sample_rate", "audio_mapping", "tab_hidden", "fullscreen"):
            row[k] = diag.get(k, "")
        self.rows.append(row)
        self.backup()
        if DEBUG:
            dbg = document.getElementById("debug")
            if not is_null(dbg):
                dbg.textContent = (f"{block} #{idx} {t['condition']} resp={response} rt={fmt(rt, 0)} | "
                                   f"{fmt(diag.get('refresh_hz'), 1)} Hz, retard flash {fmt(diag.get('flash_late_ms'), 1)} ms, "
                                   f"images perdues {diag.get('n_dropped_frames')}, avance son {fmt(diag.get('audio_lead_ms'), 0)} ms, "
                                   f"{diag.get('audio_mapping')}")

    # -- exécution d'un bloc d'essais ---------------------------------------------
    async def run_block(self, block, trials, feedback=False, progress=False, pause_every=None, question="flashs"):
        set_phase(block)
        self.stage.hide_html()
        n = len(trials)
        prompt = ["Combien de " + ("BIPS ?" if question == "bips" else "FLASHS ?"), "1   ou   2"]
        for i, t in enumerate(trials, start=1):
            if progress:
                self.stage.progress = (i - 1) / n
            iti = self.rng.uniform(C.ITI_MIN_MS, C.ITI_MAX_MS)
            while True:
                gc.disable()  # évite une pause du ramasse-miettes pendant le stimulus
                trial = StimTrial(self, t["n_flashes"], t["n_beeps"], t["beep_soa_ms"], t["flash_soa_ms"], iti, prompt)
                diag = await trial.run()
                gc.enable()
                gc.collect()
                code, ts = await self.keys.wait(list(C.RESPONSE_KEYS) + ["Escape"])
                if code != "Escape":
                    break
                if await self.confirm_quit():
                    self.aborted = 1
                    return False
                self.stage.hide_html()   # on reprend : l'essai interrompu est refait
            response = C.RESPONSE_KEYS[code]
            self.add_row(block, i, t, response, ts - diag["prompt_visible_ts"], diag)
            if feedback:
                expected = t["n_flashes"]
                self.stage.clear(fixation=False)
                if response == expected:
                    self.stage.text(["Exact !"], color="#7CFC9A")
                else:
                    self.stage.text([f"Raté : il y avait {expected} flash{'s' if expected > 1 else ''}"], color="#FF9B7C")
                await asyncio.sleep(1.0)
            if pause_every and i % pause_every == 0 and i < n:
                set_phase("pause")
                pct = int(round(100 * i / n))
                self.stage.show_html(f"""<div class="card"><h2>Pause</h2>
                    <div class="bar"><div style="width:{pct}%"></div></div>
                    <p class="lead">La moitié est faite.</p>
                    <p class="key"><span class="kbd">Espace</span> pour continuer</p></div>""")
                await self.keys.wait(["Space"])
                set_phase(block)
                self.stage.hide_html()
        self.stage.progress = None
        return True

    async def confirm_quit(self):
        set_phase("confirm_quit")
        self.stage.show_html("""<div class="card"><h2>Arrêter ?</h2>
            <p class="lead">Tes réponses déjà données seront gardées.</p>
            <button id="quit">Arrêter</button> <button id="cont" class="primary">Continuer</button></div>""")
        return (await self.click(["quit", "cont"])) == "quit"

    # -- données : CSV, copie de secours, envoi -------------------------------------
    def csv_text(self):
        lines = [",".join(C.CSV_COLUMNS)]
        for r in self.rows:
            lines.append(",".join(clean_cell(r.get(k, "")) for k in C.CSV_COLUMNS))
        return "\n".join(lines) + "\n"

    def backup(self):
        try:
            window.localStorage.setItem(self.storage_key, self.csv_text())
        except Exception as e:
            log("backup failed", e)

    @staticmethod
    def download(text, filename):
        blob = js.Blob.new(to_js([text]), js_obj({"type": "text/csv;charset=utf-8"}))
        url = js.URL.createObjectURL(blob)
        a = document.createElement("a")
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()

    @staticmethod
    async def _fetch(body, no_cors=False):
        ctrl = js.AbortController.new()
        timer = js.setTimeout(create_once_callable(lambda: ctrl.abort()), int(C.UPLOAD_TIMEOUT_S * 1000))
        opts = {"method": "POST", "body": body, "redirect": "follow", "signal": ctrl.signal,
                # text/plain = « requête simple » : pas de requête préalable CORS (preflight)
                "headers": js_obj({"Content-Type": "text/plain;charset=utf-8"})}
        if no_cors:
            opts["mode"] = "no-cors"
        try:
            return await js.fetch(C.APPS_SCRIPT_URL, js_obj(opts))
        finally:
            js.clearTimeout(timer)

    async def upload_csv(self, session_id, text):
        """Envoie le CSV à l'application Apps Script. Retourne :
        'confirmed' (le serveur a répondu ok), 'unconfirmed' (envoyé en mode no-cors, réponse illisible),
        'rejected' (refusé par le serveur), 'failed' (réseau) ou 'not_configured'."""
        if not C.APPS_SCRIPT_URL:
            return "not_configured"
        body = json.dumps({"v": 2, "token": C.SHARED_TOKEN, "session_id": session_id, "csv": text})
        if len(body.encode("utf-8")) > C.UPLOAD_MAX_BYTES:
            return "rejected"
        network_error = False
        for delay in C.UPLOAD_RETRY_DELAYS_S:
            if delay:
                await asyncio.sleep(delay)
            try:
                resp = await self._fetch(body)
            except Exception as e:
                log("upload network/CORS error", e)
                network_error = True
                continue
            if not resp.ok:
                log("upload HTTP", resp.status)
                continue
            try:
                answer = (await resp.json()).to_py()
            except Exception:
                return "unconfirmed"
            if answer.get("ok"):
                return "confirmed"
            log("upload rejected", answer)
            return "rejected"
        if network_error:   # peut-être un blocage CORS : dernier essai « à l'aveugle »
            try:
                await self._fetch(body, no_cors=True)
                return "unconfirmed"
            except Exception as e:
                log("upload no-cors error", e)
        return "failed"

    def mark(self, key, status):
        try:
            window.localStorage.setItem(key + ":status", status)
        except Exception:
            pass

    async def retry_pending(self):
        """Renvoie discrètement les sessions restées dans ce navigateur (ex. connexion coupée)."""
        try:
            await self._retry_pending()
        except Exception as e:
            js.console.warn("retry_pending: " + repr(e))

    async def _retry_pending(self):
        try:
            ls = window.localStorage
            keys = [str(ls.key(i)) for i in range(int(ls.length))]
        except Exception:
            return
        for k in keys:
            if not k.startswith(C.EXPERIMENT_NAME + ":") or k.endswith(":status") or k == self.storage_key:
                continue
            if not is_null(window.localStorage.getItem(k + ":status")):
                continue
            text = window.localStorage.getItem(k)
            if is_null(text) or not str(text):
                continue
            status = await self.upload_csv(k.split(":", 1)[1], str(text))
            log("pending", k, status)
            if status in ("confirmed", "unconfirmed", "rejected"):
                self.mark(k, status)

    # -- résultats personnels -------------------------------------------------------
    def count(self, cond, resp):
        sel = [r for r in self.rows if r["block"] == "main" and r["condition"] == cond]
        return sum(r["response"] == resp for r in sel), len(sel)

    def result_sentences(self):
        x, y = self.count("1F2B", 2)
        base, nb = self.count("1F0B", 2)
        fx, fy = self.count("2F1B", 1)
        if y == 0:
            return ["L'expérience a été interrompue avant la fin."]
        out = [f"Avec 1 seul flash et 2 bips, tu as vu 2 flashs {x} fois sur {y}."]
        fission = x / y - (base / nb if nb else 0) >= 0.25
        if fission:
            out[0] += " Ton cerveau a laissé le son modifier ce que tu voyais."
        else:
            out[0] += " Chez toi, le son a peu changé ce que tu voyais."
        if fy:
            s = f"Avec 2 flashs et 1 seul bip, tu n'as vu qu'un flash {fx} fois sur {fy}"
            if fx / fy >= 0.3:
                s += " : là aussi, le son a pris le dessus." if fission else " : là, le son a pris le dessus."
            else:
                s += " : dans ce sens-là, tes yeux ont mieux résisté." if fission else " : là aussi, tes yeux ont résisté."
            out.append(s)
        return out

    async def screen_end(self, error=None):
        set_phase("end")
        try:
            if not is_null(document.fullscreenElement):
                document.exitFullscreen()
        except Exception:
            pass
        for r in self.rows:
            r["aborted"] = self.aborted or (1 if error else 0)
            r["audio_check_score"] = self.info.get("audio_check_score", "")
        self.backup()
        text = self.csv_text()
        js.window.flashson_csv = text  # accessible au test automatique
        if error:
            lines = ["Une erreur est survenue. Merci quand même !"]
        else:
            lines = self.result_sentences()
        paras = "".join(f'<p class="lead">{esc(l)}</p>' for l in lines)
        self.stage.show_html(f"""
        <div class="card">
          <h1>Merci !</h1>
          {paras}
          <p class="tiny" id="upl">Envoi de tes réponses…</p>
          <button id="dl" class="tiny-btn" style="display:none"></button>
        </div>""")
        if not self.rows:
            document.getElementById("upl").textContent = ""
            set_phase("done")
            return
        status = await self.upload_csv(self.session_id, text)
        document.body.dataset.upload = status
        upl, dl = document.getElementById("upl"), document.getElementById("dl")
        if status in ("confirmed", "unconfirmed"):
            upl.textContent = "Réponses envoyées. Tu peux fermer la page."
            self.mark(self.storage_key, status)
        else:
            upl.textContent = ""
            dl.textContent = ("Télécharger mes réponses" if status == "not_configured"
                              else "L'envoi n'a pas marché : télécharger mes réponses")
            dl.style.display = "inline-block"
            fname = f"flashson_{self.session_id}.csv"
            dl.addEventListener("click", create_proxy(lambda ev: self.download(self.csv_text(), fname)))
            if status == "rejected":
                self.mark(self.storage_key, status)
        set_phase("done")

    # -- déroulement complet --------------------------------------------------------
    def shuffled_main(self):
        main = [t for t in self.trials if t["block"] == "main"]
        best = None
        for _ in range(2000):
            self.rng.shuffle(main)
            run, worst = 1, 1
            for a, b in zip(main[:-1], main[1:]):
                run = run + 1 if a["condition"] == b["condition"] else 1
                worst = max(worst, run)
            if worst <= C.MAX_SAME_CONDITION_IN_A_ROW:
                best = list(main)
                break
        if best is None:
            best = list(main)
        if PARAMS.get("short") == "1":   # mode test rapide : 1 essai par condition
            seen, short = set(), []
            for t in best:
                if t["condition"] not in seen:
                    seen.add(t["condition"])
                    short.append(t)
            best = short
        return best

    async def run(self):
        if C.APPS_SCRIPT_URL:   # garder une référence : asyncio ne garde les tâches que faiblement
            self._pending_task = asyncio.ensure_future(self.retry_pending())
        await self.screen_welcome()
        await self.screen_info()
        await self.screen_setup()
        await self.screen_sound_check()
        await self.estimate_refresh()
        if self.refresh_info["refresh_hz"] < 50 or self.refresh_info["frac_irregular"] > 0.2:
            set_phase("refresh_warning")
            self.stage.show_html("""<div class="card"><h2>Affichage saccadé</h2>
                <p class="lead">Ferme les autres onglets et branche ton ordinateur.</p>
                <button id="retry" class="primary">Réessayer</button> <button id="go">Continuer</button></div>""")
            if await self.click(["retry", "go"]) == "retry":
                await self.estimate_refresh()
        # test d'écoute (1 ou 2 bips, sans flash)
        ac = [t for t in self.trials if t["block"] == "audiocheck"]
        await self.message("audiocheck_instructions",
                           "<h2>Test d'écoute</h2><p class='lead'>1 ou 2 bips ?<br>Réponds avec la touche "
                           "<span class='kbd'>1</span> ou <span class='kbd'>2</span>.</p>", "pour commencer")
        attempt, scores = 1, []
        while True:
            self.rng.shuffle(ac)
            block = "audiocheck" if attempt == 1 else "audiocheck2"
            if not await self.run_block(block, ac, question="bips"):
                return await self.screen_end()
            rows_ac = [r for r in self.rows if r["block"] == block]
            score = sum(r["correct"] == 1 for r in rows_ac)
            scores.append(f"{score}/{len(rows_ac)}")
            self.info["audio_check_score"] = ";".join(scores)
            if score == len(rows_ac) or attempt == 2:
                break
            set_phase("audiocheck_warning")
            self.stage.show_html(f"""<div class="card"><h2>Test d'écoute : {score}/{len(rows_ac)}</h2>
                <p class="lead">Vérifie le volume et ton casque.</p>
                <button id="retry" class="primary">Refaire</button> <button id="go">Continuer</button></div>""")
            if await self.click(["retry", "go"]) == "go":
                break
            attempt += 1
        # consignes + entraînement
        await self.message("instructions", """<h2>Ta mission</h2>
            <div class="demo"><div class="cross">+</div><div class="dot"></div></div>
            <ul class="big"><li>Fixe la croix.</li><li>Compte les flashs du disque : <b>1 ou 2</b>.</li>
            <li><b>Ignore les bips.</b></li></ul>""", "pour t'entraîner (3 essais)")
        practice = [t for t in self.trials if t["block"] == "practice"]
        if not await self.run_block("practice", practice, feedback=True):
            return await self.screen_end()
        main = self.shuffled_main()
        await self.message("ready", "<h2>C'est parti !</h2><p class='lead'>Plus de correction.<br>"
                                    "Réponds selon ce que tu as <b>vu</b>.</p>", "pour commencer")
        await self.run_block("main", main, progress=True, pause_every=(len(main) + 1) // 2)
        await self.screen_end()

    # -- mode vérification du timing (cf. xpy_check_audio_visual_timing.py du cours) ----
    async def run_timing_check(self):
        set_phase("timing_setup")
        self.stage.show_html("""<div class="card"><h2>Vérification du timing audio-visuel</h2>
          <p>Ce mode affiche un carré blanc en haut à gauche pendant ~100 ms et joue un son de 440 Hz de 100 ms,
             toutes les 500 ms, en utilisant exactement le même moteur que l'expérience.
             Placer une photodiode sur le carré et un micro (ou la sortie casque) sur un oscilloscope / une carte son
             permet de mesurer le décalage réel son-image (ex. Black Box ToolKit, ou un smartphone filmant à 240 im/s).</p>
          <p>Échap pour arrêter.</p><button id="go" class="primary">Démarrer (plein écran)</button></div>""")

        def unlock(_):
            self.audio = Audio()
            self.audio.resume()
            try:
                document.documentElement.requestFullscreen()
            except Exception:
                pass
            return True
        await self.click(["go"], before=unlock)
        await asyncio.sleep(0.6)
        self.stage.resize()
        await self.estimate_refresh()
        set_phase("timing_run")
        P = self.frame_ms
        n_on = max(1, int(round(100 / P)))
        state = dict(next_plan=None, T=None, on=0, k=0, stop=False, late=[], drops=0, last=None)

        def h(ts):
            st = self.stage
            if state["last"] is not None and ts - state["last"] > 1.5 * P:
                state["drops"] += int(round((ts - state["last"]) / P)) - 1
            state["last"] = ts
            if state["next_plan"] is None:
                state["next_plan"] = ts
            if state["T"] is None and ts >= state["next_plan"]:
                state["T"] = ts + max(2, int(round(C.AUDIO_LEAD_MS / P))) * P
                off, _ = self.audio.clock_offset()
                self.audio.schedule(self.audio.timing_tone, (state["T"] + C.DISPLAY_LATENCY_FRAMES * P + off) / 1000)
            if state["T"] is not None and state["on"] == 0 and ts >= state["T"] - P / 2:
                st.clear(fixation=False)
                st.ctx.fillStyle = "#FFFFFF"
                st.ctx.fillRect(0, 0, st.H * 0.25, st.H * 0.25)
                state["late"].append(ts - state["T"])
                state["on"] = n_on
            elif state["on"] > 0:
                state["on"] -= 1
                if state["on"] == 0:
                    st.clear(fixation=False)
                    st.text([f"{1000 / P:.1f} Hz | cycles {len(state['late'])} | images perdues {state['drops']} | "
                             f"retard moyen du carré {statistics.mean(state['late']):.1f} ms | Échap pour arrêter"],
                            y_frac=0.9, size_frac=0.025, color="#777")
                    state["next_plan"] = state["T"] + 500 - C.AUDIO_LEAD_MS
                    state["T"] = None
            return not state["stop"]
        self.frames.run(h)
        await self.keys.wait(["Escape"])
        state["stop"] = True
        self.stage.show_html(f"""<div class="card"><h2>Fin de la vérification</h2>
            <p>{len(state['late'])} cycles, fréquence estimée {1000 / P:.2f} Hz, {state['drops']} images perdues.</p>
            <p>Recharger la page pour recommencer.</p></div>""")
        set_phase("done")



async def main():
    trials_text = open("trials.csv", encoding="utf-8").read()
    exp = Experiment(trials_text)
    js.window.flashson_exp_ready = True
    try:
        if PARAMS.get("mode") == "timing":
            await exp.run_timing_check()
        else:
            await exp.run()
    except Exception as e:
        js.console.error("Erreur : " + repr(e))
        set_phase("error")
        if PARAMS.get("mode") != "timing":
            await exp.screen_end(error=e)
            set_phase("error")
        raise
