"""Illusion flash-son (« double flash ») -- expérience en ligne, écrite en Python.

Référence : Shams, L., Kamitani, Y. & Shimojo, S. (2000). What you see is what
you hear. Nature, 408, 788. https://doi.org/10.1038/35048669

Ce script tourne DANS LE NAVIGATEUR du participant grâce à Pyodide (CPython
compilé en WebAssembly). Il pilote directement les API du navigateur :
  * <canvas> + requestAnimationFrame  -> flashs synchronisés au rafraîchissement de l'écran
  * Web Audio API (AudioContext)       -> bips programmés à l'échantillon près
  * Blob / localStorage / fetch        -> sauvegarde des données

Principe de synchronisation audio-visuelle (voir README, section « Timing ») :
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

def js_obj(d):
    """Convertit un dict Python en objet JavaScript."""
    return to_js(d, dict_converter=js.Object.fromEntries)


def url_params():
    p = js.URLSearchParams.new(window.location.search)
    return {k: p.get(k) for k in ("short", "debug", "pid", "mode") if p.has(k)}


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
        d["fullscreen"] = int(document.fullscreenElement is not None)
        d["prompt_visible_ts"] = self.prompt_ts + C.DISPLAY_LATENCY_FRAMES * P
        if not self.fut.done():
            self.fut.set_result(d)

    async def run(self):
        self.exp.frames.run(self.on_frame)
        return await self.fut


# ---------------------------------------------------------------------------
# Écrans HTML
# ---------------------------------------------------------------------------

AUDIO_DEVICES = [
    ("wired_headphones", "Casque / écouteurs filaires (prise jack ou USB)"),
    ("laptop_speakers", "Haut-parleurs intégrés de l'ordinateur"),
    ("external_speakers", "Enceintes externes filaires"),
    ("bluetooth", "Casque / écouteurs / enceinte Bluetooth (AirPods, etc.)"),
    ("other", "Autre / je ne sais pas"),
]


def opts(pairs, placeholder="— choisir —"):
    html = f'<option value="">{placeholder}</option>'
    for v, lab in pairs:
        html += f'<option value="{v}">{esc(lab)}</option>'
    return html


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
        rnd = "".join(random.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(4))
        return f"{stamp}-{rnd}"

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
                if before is not None:
                    ok = before(bid)
                    if ok is False:
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

    # -- écrans -----------------------------------------------------------------
    async def screen_welcome(self):
        set_phase("welcome")
        leftovers = self.find_leftover_sessions()
        left_html = ""
        if leftovers:
            items = "".join(f'<li><button class="link" id="dl-{i}">Télécharger la session {esc(k.split(":", 1)[1])}</button></li>'
                            for i, k in enumerate(leftovers))
            left_html = f'<div class="note">Des données d\'une session précédente sont restées dans ce navigateur :<ul>{items}</ul></div>'
        self.stage.show_html(f"""
        <div class="card">
          <h1>Le flash et le son</h1>
          <p class="lead">Une courte expérience de sciences cognitives sur la perception (≈ 5 minutes).</p>
          <p>Un petit disque blanc va clignoter très brièvement à l'écran, parfois accompagné de bips.
             Ta tâche est simple : <b>compter les flashs</b>. À la fin, tu découvriras à quel point ton cerveau
             mélange la vue et l'ouïe.</p>
          <ul>
            <li>Il te faut un <b>ordinateur</b> (pas de téléphone), un <b>clavier</b> et du <b>son</b>.</li>
            <li>Utilise de préférence un <b>casque filaire</b> ou les <b>haut-parleurs de l'ordinateur</b>
                (le Bluetooth retarde le son et fausse la mesure).</li>
            <li>Les données sont <b>anonymes</b> (un code au choix, aucune donnée nominative) et servent uniquement
                à un projet de cours (École polytechnique, cours de sciences cognitives).</li>
            <li>Tu peux arrêter à tout moment avec la touche <span class="kbd">Échap</span>.</li>
          </ul>
          <label class="check"><input type="checkbox" id="consent"> J'ai lu ces informations et j'accepte de participer.</label>
          <label class="check"><input type="checkbox" id="epilepsy"> Je confirme ne pas souffrir d'épilepsie photosensible
             (l'expérience contient de brefs flashs lumineux).</label>
          <p class="error" id="err"></p>
          <button id="go" class="primary">Continuer</button>
          {left_html}
          <p class="small">Référence : Shams, Kamitani &amp; Shimojo (2000), <i>What you see is what you hear</i>, Nature 408:788.</p>
        </div>""")
        for i, k in enumerate(leftovers):
            node = document.getElementById(f"dl-{i}")
            node.addEventListener("click", create_proxy(lambda ev, k=k: self.download_leftover(k)))

        def check(_):
            if not document.getElementById("consent").checked or not document.getElementById("epilepsy").checked:
                document.getElementById("err").textContent = "Coche les deux cases pour participer."
                return False
            return True
        await self.click(["go"], before=check)

    async def screen_info(self):
        set_phase("info")
        default_pid = PARAMS.get("pid") or ("P" + "".join(random.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(5)))
        self.stage.show_html(f"""
        <div class="card">
          <h2>Quelques informations</h2>
          <div class="form">
            <label>Code participant (pseudonyme, sans nom ni prénom)
              <input id="pid" value="{esc(default_pid)}" maxlength="24"></label>
            <label>Âge <input id="age" type="number" min="16" max="99" placeholder="ex. 21"></label>
            <label>Genre <select id="gender">{opts([("F", "Femme"), ("M", "Homme"), ("O", "Autre"), ("undisclosed", "Je préfère ne pas répondre")])}</select></label>
            <label>Main dominante <select id="handedness">{opts([("right", "Droitier·ère"), ("left", "Gaucher·ère"), ("ambi", "Ambidextre")])}</select></label>
            <label>Avec quoi vas-tu écouter le son ? <select id="audio_device">{opts(AUDIO_DEVICES)}</select></label>
            <label>Vision <select id="vision">{opts([("normal", "Normale"), ("corrected", "Corrigée (lunettes / lentilles portées)"), ("impaired", "Trouble non corrigé")])}</select></label>
            <label>Audition <select id="hearing">{opts([("normal", "Normale"), ("impaired", "Trouble connu de l'audition")])}</select></label>
          </div>
          <p class="error" id="err"></p>
          <button id="go" class="primary">Continuer</button>
        </div>""")

        def check(_):
            g = lambda i: str(document.getElementById(i).value).strip()
            pid = re.sub(r"[^A-Za-z0-9_-]", "", g("pid"))
            missing = [lab for i, lab in (("age", "âge"), ("gender", "genre"), ("handedness", "main dominante"),
                                          ("audio_device", "matériel audio"), ("vision", "vision"), ("hearing", "audition"))
                       if not g(i)]
            if not pid:
                missing.insert(0, "code participant (lettres/chiffres)")
            if missing:
                document.getElementById("err").textContent = "Merci de compléter : " + ", ".join(missing) + "."
                return False
            try:
                age = int(g("age"))
                assert 16 <= age <= 99
            except Exception:
                document.getElementById("err").textContent = "Âge invalide."
                return False
            self.info = dict(participant_id=pid, age=age, gender=g("gender"), handedness=g("handedness"),
                             audio_device=g("audio_device"), vision=g("vision"), hearing=g("hearing"))
            return True
        await self.click(["go"], before=check)

        if self.info["audio_device"] == "bluetooth":
            set_phase("bluetooth")
            self.stage.show_html("""
            <div class="card warn">
              <h2>⚠️ Attention au Bluetooth</h2>
              <p>Les écouteurs Bluetooth retardent le son de 100 à 300 ms. Or l'illusion étudiée ici n'apparaît que si
                 le son et l'image arrivent à quelques dizaines de millisecondes d'écart : <b>avec du Bluetooth,
                 tes données risquent d'être inutilisables</b>.</p>
              <p>Si possible, débranche/désactive le Bluetooth et utilise un casque filaire ou les haut-parleurs de l'ordinateur.</p>
              <button id="changed" class="primary">J'ai changé de matériel</button>
              <button id="keep">Continuer quand même avec le Bluetooth</button>
            </div>""")
            choice = await self.click(["changed", "keep"])
            if choice == "changed":
                self.stage.show_html(f"""
                <div class="card"><h2>Matériel audio utilisé maintenant</h2>
                  <label>Avec quoi vas-tu écouter le son ? <select id="audio_device">{opts([p for p in AUDIO_DEVICES if p[0] != "bluetooth"])}</select></label>
                  <p class="error" id="err"></p><button id="go" class="primary">Continuer</button></div>""")

                def check2(_):
                    v = str(document.getElementById("audio_device").value)
                    if not v:
                        document.getElementById("err").textContent = "Choisis une option."
                        return False
                    self.info["audio_device"] = v
                    return True
                await self.click(["go"], before=check2)

    async def screen_setup(self):
        set_phase("setup")
        self.stage.show_html("""
        <div class="card">
          <h2>Installe-toi</h2>
          <ul>
            <li>Mets-toi dans un endroit <b>calme</b>, si possible avec une lumière tamisée.</li>
            <li>Assieds-toi à environ <b>50–60 cm</b> de l'écran (une longueur de bras), bien en face.</li>
            <li>Ferme les autres onglets et applications, coupe les notifications.</li>
            <li>Mets le volume de l'ordinateur vers <b>70–80 %</b> (tu l'ajusteras juste après).</li>
            <li>Si tu es sur un portable, <b>branche-le sur secteur</b> (l'économie d'énergie peut dégrader l'affichage).</li>
          </ul>
          <p>L'expérience passe en <b>plein écran</b>. Ne change pas d'onglet pendant l'expérience.</p>
          <button id="go" class="primary">Passer en plein écran et activer le son</button>
        </div>""")

        def unlock(_):
            # Ces deux appels DOIVENT être faits pendant le clic (règle des navigateurs).
            try:
                self.audio = Audio()
                self.audio.resume()
            except Exception as e:
                document.getElementById("ui").innerHTML = f"<div class='card warn'><h2>Son indisponible</h2><p>{esc(e)}</p></div>"
                raise
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
          <h2>Réglage du son</h2>
          <p>Clique sur « Jouer le son test » : tu vas entendre une série de petits bips aigus.
             Règle le volume de ton ordinateur pour qu'ils soient <b>bien audibles mais pas désagréables</b>.</p>
          <button id="play">🔊 Jouer le son test</button>
          <p class="small" id="lat"></p>
          <button id="ok" class="primary">J'entends bien les bips</button>
          <button id="none">Je n'entends rien</button>
        </div>""")
        ol, bl = self.audio.latencies()
        document.getElementById("lat").textContent = f"Latence audio annoncée par le navigateur : sortie {fmt(ol, 0)} ms, base {fmt(bl, 0)} ms."

        def play(_):
            self.audio.resume()
            t0 = float(self.audio.ctx.currentTime) + 0.1
            for i in range(8):
                self.audio.schedule(self.audio.beep, t0 + i * 0.35)
            return False  # ne termine pas l'écran
        play_node = document.getElementById("play")
        play_proxy = create_proxy(play)
        play_node.addEventListener("click", play_proxy)
        while True:
            choice = await self.click(["ok", "none"])
            if choice == "ok":
                break
            document.getElementById("lat").innerHTML = ("<b>Vérifie</b> : volume de l'ordinateur, sortie audio sélectionnée, "
                                                        "onglet non mis en sourdine, casque bien branché. Puis rejoue le son.")
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

    # -- enregistrement d'un essai -----------------------------------------------
    def add_row(self, block, idx, t, response, rt, diag):
        self.trial_global += 1
        nf, nb = t["n_flashes"], t["n_beeps"]
        expected = nf if block != "audiocheck" else nb
        row = dict(
            participant_id=self.info.get("participant_id", ""), session_id=self.session_id,
            experiment_version=C.EXPERIMENT_VERSION, timestamp_iso=now_iso(),
            block=block, trial_in_block=idx, trial_global=self.trial_global,
            condition=t["condition"], n_flashes=nf, n_beeps=nb,
            beep_soa_ms=t["beep_soa_ms"], flash_soa_ms_target=t["flash_soa_ms"], is_catch=t["is_catch"], part=t["part"],
            response=response if response is not None else "",
            correct=int(response == expected) if response is not None else "",
            rt_ms=rt,
            age=self.info.get("age", ""), gender=self.info.get("gender", ""), handedness=self.info.get("handedness", ""),
            audio_device=self.info.get("audio_device", ""), vision=self.info.get("vision", ""),
            hearing=self.info.get("hearing", ""), audio_check_score=self.info.get("audio_check_score", ""),
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
            log(json.dumps({k: row[k] for k in ("block", "condition", "response", "rt_ms", "flash_late_ms",
                                                 "n_dropped_frames", "audio_lead_ms", "av_offset_est_ms", "audio_mapping")},
                           default=str))
            dbg = document.getElementById("debug")
            if dbg is not None:
                dbg.textContent = (f"{block} #{idx} {t['condition']} resp={response} rt={fmt(rt, 0)} | "
                                   f"{fmt(diag.get('refresh_hz'), 1)} Hz, retard flash {fmt(diag.get('flash_late_ms'), 1)} ms, "
                                   f"images perdues {diag.get('n_dropped_frames')}, avance son {fmt(diag.get('audio_lead_ms'), 0)} ms, "
                                   f"{diag.get('audio_mapping')}")

    # -- exécution d'un bloc d'essais ---------------------------------------------
    async def run_block(self, block, trials, feedback=False, progress=False, pause_every=None, question="flashs"):
        set_phase(block)
        self.stage.hide_html()
        n = len(trials)
        for i, t in enumerate(trials, start=1):
            if progress:
                self.stage.progress = (i - 1) / n
            gc.disable()  # évite une pause du ramasse-miettes pendant le stimulus
            if question == "bips":
                prompt = ["Combien de BIPS as-tu entendus ?", "1   ou   2"]
            else:
                prompt = ["Combien de FLASHS as-tu vus ?", "1   ou   2"]
            iti = self.rng.uniform(C.ITI_MIN_MS, C.ITI_MAX_MS)
            trial = StimTrial(self, t["n_flashes"], t["n_beeps"], t["beep_soa_ms"], t["flash_soa_ms"], iti, prompt)
            diag = await trial.run()
            gc.enable()
            gc.collect()
            code, ts = await self.keys.wait(list(C.RESPONSE_KEYS) + ["Escape"])
            if code == "Escape":
                if await self.confirm_quit():
                    self.aborted = 1
                    return False
                # on reprend : l'essai interrompu n'est pas enregistré, on le refait
                self.stage.hide_html()
                trial = StimTrial(self, t["n_flashes"], t["n_beeps"], t["beep_soa_ms"], t["flash_soa_ms"], iti, prompt)
                diag = await trial.run()
                code, ts = await self.keys.wait(list(C.RESPONSE_KEYS))
            response = C.RESPONSE_KEYS[code]
            rt = ts - diag["prompt_visible_ts"]
            self.add_row(block, i, t, response, rt, diag)
            if feedback:
                expected = t["n_flashes"]
                ok = response == expected
                self.stage.clear(fixation=False)
                msg = ("✔ Exact !" if ok else "✘ Pas tout à fait…") + f"  Il y avait {expected} flash{'s' if expected > 1 else ''}."
                self.stage.text([msg], color="#7CFC9A" if ok else "#FF9B7C")
                await asyncio.sleep(1.2)
            if pause_every and i % pause_every == 0 and i < n:
                await self.pause_screen(i, n)
        self.stage.progress = None
        return True

    async def confirm_quit(self):
        set_phase("confirm_quit")
        self.stage.show_html("""<div class="card warn"><h2>Arrêter l'expérience ?</h2>
            <p>Les réponses déjà données seront sauvegardées (fichier téléchargé).</p>
            <button id="quit">Oui, arrêter</button> <button id="cont" class="primary">Non, continuer</button></div>""")
        return (await self.click(["quit", "cont"])) == "quit"

    async def pause_screen(self, i, n):
        set_phase("pause")
        pct = int(round(100 * i / n))
        self.stage.show_html(f"""<div class="card"><h2>Pause — {pct} % fait 🎉</h2>
            <div class="bar"><div style="width:{pct}%"></div></div>
            <p>Tu as fait {i} essais sur {n}. Repose tes yeux quelques secondes.</p>
            <p>Rappel : fixe la croix, compte uniquement les <b>flashs</b> (ignore les bips).</p>
            <p>Appuie sur <span class="kbd">Espace</span> pour continuer.</p></div>""")
        await self.keys.wait(["Space"])
        self.stage.hide_html()

    async def instructions_audio_check(self):
        set_phase("audiocheck_instructions")
        self.stage.show_html("""<div class="card"><h2>Petit test d'écoute</h2>
            <p>Tu vas entendre <b>1 ou 2 bips</b> très rapprochés (aucun flash). Après chaque essai, indique combien de
               <b>bips</b> tu as entendus avec les touches <span class="kbd">1</span> ou <span class="kbd">2</span>
               (rangée du haut ou pavé numérique, pas besoin de Maj).</p>
            <p>Garde les yeux sur la croix au centre.</p>
            <p>Appuie sur <span class="kbd">Espace</span> pour commencer (6 essais).</p></div>""")
        await self.keys.wait(["Space"])

    async def instructions_main(self):
        set_phase("instructions")
        self.stage.show_html("""<div class="card"><h2>La tâche</h2>
            <div class="demo"><div class="cross">+</div><div class="dot"></div></div>
            <ol>
              <li>Garde les yeux fixés sur la <b>croix</b> au centre de l'écran, pendant tout l'essai.</li>
              <li>Un disque blanc va <b>flasher</b> très brièvement en dessous, <b>1 ou 2 fois</b>.</li>
              <li>Parfois, tu entendras aussi des bips. <b>Ignore-les</b> : seuls les flashs comptent.</li>
              <li>Réponds ensuite avec <span class="kbd">1</span> (un flash) ou <span class="kbd">2</span> (deux flashs).
                  Il n'y a pas de piège sur la vitesse : réponds selon ce que tu as <b>vu</b>.</li>
            </ol>
            <p>On commence par <b>6 essais d'entraînement</b> avec correction.</p>
            <p>Appuie sur <span class="kbd">Espace</span> pour commencer.</p></div>""")
        await self.keys.wait(["Space"])

    # -- sauvegarde ---------------------------------------------------------------
    def csv_text(self):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=C.CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in self.rows:
            w.writerow({k: fmt(r.get(k, "")) if isinstance(r.get(k, ""), float) else r.get(k, "") for k in C.CSV_COLUMNS})
        return buf.getvalue()

    def filename(self):
        pid = self.info.get("participant_id", "anonyme")
        return f"flashson_{pid}_{self.session_id}.csv"

    def backup(self):
        try:
            window.localStorage.setItem(self.storage_key, self.csv_text())
        except Exception as e:
            log("backup failed", e)

    def find_leftover_sessions(self):
        keys = []
        try:
            ls = window.localStorage
            for i in range(int(ls.length)):
                k = str(ls.key(i))
                if k.startswith(C.EXPERIMENT_NAME + ":") and not k.endswith(":done"):
                    if ls.getItem(k + ":done") is None:
                        keys.append(k)
        except Exception:
            pass
        return keys

    def download_leftover(self, key):
        txt = window.localStorage.getItem(key)
        if txt:
            self.download(str(txt), f"flashson_session_{key.split(':', 1)[1]}.csv")
            window.localStorage.setItem(key + ":done", "1")

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

    async def upload(self):
        """Envoi optionnel vers un service gratuit (configuré dans config.py)."""
        text = self.csv_text()
        results = []
        if C.DATAPIPE_EXPERIMENT_ID:
            try:
                resp = await js.fetch("https://pipe.jspsych.org/api/data/", js_obj({
                    "method": "POST",
                    "headers": js_obj({"Content-Type": "application/json", "Accept": "*/*"}),
                    "body": json.dumps({"experimentID": C.DATAPIPE_EXPERIMENT_ID,
                                        "filename": self.filename(), "data": text}),
                }))
                results.append(("DataPipe", bool(resp.ok)))  # 201 = stocké, 202 = accepté (réessai automatique)
            except Exception as e:
                log("datapipe error", e)
                results.append(("DataPipe", False))
        if C.APPS_SCRIPT_URL:
            try:
                await js.fetch(C.APPS_SCRIPT_URL, js_obj({
                    "method": "POST", "mode": "no-cors",
                    "headers": js_obj({"Content-Type": "text/plain;charset=utf-8"}),
                    "body": json.dumps({"filename": self.filename(), "data": text}),
                }))
                results.append(("Google Drive", None))  # réponse opaque en mode no-cors
            except Exception as e:
                log("apps script error", e)
                results.append(("Google Drive", False))
        return results

    # -- résultats personnels -------------------------------------------------------
    def personal_results(self):
        main = [r for r in self.rows if r["block"] == "main"]

        def rate(cond, resp):
            sel = [r for r in main if r["condition"] == cond]
            return (sum(r["response"] == resp for r in sel) / len(sel)) if sel else None
        res = dict(base=rate("1F0B", 2), fission=rate("1F2B", 2), fusion=rate("2F1B", 1),
                   two_ok=rate("2F0B", 2), catch=rate("2F0B_catch", 2))
        curve = [(C.CORE_BEEP_SOA_MS, res["fission"])]
        for s in C.EXTENSION_BEEP_SOAS_MS:
            curve.append((s, rate(f"1F2B_soa{s}", 2)))
        res["curve"] = [(s, v) for s, v in curve if v is not None]
        window_ms = None
        if res["fission"] is not None and res["base"] is not None and res["fission"] - res["base"] >= 0.2:
            half = res["base"] + 0.5 * (res["fission"] - res["base"])
            window_ms = C.CORE_BEEP_SOA_MS
            for s, v in res["curve"]:
                if v >= half:
                    window_ms = s
        res["window_ms"] = window_ms
        return res

    async def screen_end(self):
        set_phase("end")
        try:
            if document.fullscreenElement is not None:
                document.exitFullscreen()
        except Exception:
            pass
        for r in self.rows:
            r["aborted"] = self.aborted
            r["audio_check_score"] = self.info.get("audio_check_score", "")
        self.backup()
        text = self.csv_text()
        fname = self.filename()
        self.download(text, fname)
        js.window.flashson_csv = text  # accessible au test automatique
        res = self.personal_results()

        def pct(v):
            return "—" if v is None else f"{round(100 * v)} %"
        bars = ""
        for s, v in res["curve"]:
            h = 0 if v is None else int(round(100 * v))
            bars += f'<div class="col"><div class="barv" style="height:{h}%"></div><span>{s} ms</span><b>{h}%</b></div>'
        if res["fission"] is None:
            verdict = "Expérience interrompue avant la fin : pas de résultat personnel."
        elif res["base"] is not None and res["base"] > 0.5:
            verdict = ("Tu as souvent répondu « 2 » même quand il n'y avait qu'un flash et aucun son : "
                       "difficile de mesurer l'illusion chez toi (flash trop bref sur ton écran ?).")
        elif res["window_ms"] is None:
            verdict = ("Ton cerveau a très peu été trompé par les bips : ta vue garde le dessus. "
                       "C'est plus rare que l'inverse !")
        elif res["fission"] >= 0.6:
            verdict = (f"Ton cerveau a « vu » un flash fantôme dans {pct(res['fission'])} des essais avec 1 flash + 2 bips : "
                       f"chez toi, l'ouïe réécrit franchement ce que voient tes yeux. 🤯")
        else:
            verdict = (f"Un flash fantôme est apparu dans {pct(res['fission'])} des essais 1 flash + 2 bips : "
                       f"ton cerveau mélange bien la vue et l'ouïe.")
        win_txt = (f"<p>D'après tes réponses, l'illusion reste forte tant que les deux bips sont espacés de moins de "
                   f"<b>≈ {res['window_ms']} ms</b> : c'est une estimation (grossière) de ta <b>fenêtre d'intégration "
                   f"audio-visuelle</b>.</p>" if res["window_ms"] else "")
        self.stage.show_html(f"""
        <div class="card">
          <h1>Merci ! 🙏</h1>
          <p class="lead">{verdict}</p>
          <table class="res">
            <tr><td>1 flash, sans son → vu « 2 »</td><td>{pct(res['base'])}</td></tr>
            <tr><td>1 flash + 2 bips → vu « 2 » (illusion de fission)</td><td><b>{pct(res['fission'])}</b></td></tr>
            <tr><td>2 flashs + 1 bip → vu « 1 » (illusion de fusion)</td><td>{pct(res['fusion'])}</td></tr>
          </table>
          <h3>Illusion selon l'écart entre les 2 bips</h3>
          <div class="chart">{bars}</div>
          {win_txt}
          <p class="small">Pourquoi ? Pour compter des événements rapides, le cerveau fait davantage confiance à l'oreille,
             plus précise dans le temps que l'œil : il fusionne les deux sens (Shams et al., 2000).</p>
          <div class="note" id="save"><b>Tes données</b> ont été téléchargées dans le fichier <code>{esc(fname)}</code>
             (dossier Téléchargements). <span id="upl"></span><br>
             <button id="again">Télécharger à nouveau</button></div>
          <p class="small">Merci de ne pas dévoiler le principe de l'expérience à tes camarades avant qu'ils l'aient faite !</p>
        </div>""")
        again = document.getElementById("again")
        again.addEventListener("click", create_proxy(lambda ev: self.download(self.csv_text(), fname)))
        upl = document.getElementById("upl")
        if C.DATAPIPE_EXPERIMENT_ID or C.APPS_SCRIPT_URL:
            upl.textContent = "Envoi automatique en cours…"
            results = await self.upload()
            ok = [name for name, s in results if s is not False]
            if ok and all(s is not False for _, s in results):
                upl.textContent = "Elles ont aussi été envoyées automatiquement. Merci !"
                window.localStorage.setItem(self.storage_key + ":done", "1")
            else:
                upl.textContent = "L'envoi automatique a échoué : envoie le fichier téléchargé à l'expérimentateur."
        else:
            upl.textContent = "Merci d'envoyer ce fichier à l'expérimentateur."
            window.localStorage.setItem(self.storage_key + ":done", "1")
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
        await self.screen_welcome()
        await self.screen_info()
        await self.screen_setup()
        await self.screen_sound_check()
        await self.estimate_refresh()
        if self.refresh_info["refresh_hz"] < 50 or self.refresh_info["frac_irregular"] > 0.2:
            set_phase("refresh_warning")
            self.stage.show_html(f"""<div class="card warn"><h2>Affichage irrégulier</h2>
                <p>Ton écran semble rafraîchi à {self.refresh_info['refresh_hz']:.0f} Hz avec des images irrégulières
                ({100 * self.refresh_info['frac_irregular']:.0f} %). Ferme les autres onglets/applications, branche le
                portable sur secteur et reste en plein écran.</p>
                <button id="retry" class="primary">Réessayer la mesure</button> <button id="go">Continuer quand même</button></div>""")
            if await self.click(["retry", "go"]) == "retry":
                await self.estimate_refresh()
        # test d'écoute (1 ou 2 bips, sans flash)
        await self.instructions_audio_check()
        ac = [t for t in self.trials if t["block"] == "audiocheck"]
        self.rng.shuffle(ac)
        if not await self.run_block("audiocheck", ac, question="bips"):
            return await self.screen_end()
        rows_ac = [r for r in self.rows if r["block"] == "audiocheck"]
        score = sum(r["correct"] == 1 for r in rows_ac)
        self.info["audio_check_score"] = f"{score}/{len(rows_ac)}"
        if score < len(rows_ac) - 1:
            set_phase("audiocheck_warning")
            self.stage.show_html(f"""<div class="card warn"><h2>Test d'écoute : {score}/{len(rows_ac)}</h2>
                <p>Tu n'as pas toujours distingué 1 bip de 2 bips. Vérifie le volume et ton casque (pas de Bluetooth).</p>
                <button id="retry" class="primary">Refaire le test d'écoute</button> <button id="go">Continuer</button></div>""")
            if await self.click(["retry", "go"]) == "retry":
                self.rng.shuffle(ac)
                if not await self.run_block("audiocheck2", ac, question="bips"):
                    return await self.screen_end()
                rows_ac2 = [r for r in self.rows if r["block"] == "audiocheck2"]
                score2 = sum(r["correct"] == 1 for r in rows_ac2)
                self.info["audio_check_score"] = f"{score}/{len(rows_ac)};{score2}/{len(rows_ac2)}"
        # entraînement
        await self.instructions_main()
        practice = [t for t in self.trials if t["block"] == "practice"]
        if not await self.run_block("practice", practice, feedback=True):
            return await self.screen_end()
        set_phase("ready")
        main = self.shuffled_main()
        self.stage.show_html(f"""<div class="card"><h2>C'est parti !</h2>
            <p>Maintenant, il n'y aura plus de correction. {len(main)} essais (≈ 4 min), avec une pause au milieu.</p>
            <p>Fixe la croix, compte les <b>flashs</b>, ignore les bips. Réponds selon ce que tu as vu.</p>
            <p>Appuie sur <span class="kbd">Espace</span> pour commencer.</p></div>""")
        await self.keys.wait(["Space"])
        await self.run_block("main", main, progress=True, pause_every=(len(main) + 1) // 2)
        await self.screen_end()

    # -- mode vérification du timing (cf. xpy_check_audio_visual_timing.py du cours) ----
    async def run_timing_check(self):
        set_phase("timing_setup")
        self.info = dict(participant_id="timingcheck")
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
        msg = esc(repr(e))
        exp.stage.show_html(f"""<div class="card warn"><h2>Une erreur est survenue</h2><p><code>{msg}</code></p>
            <p>Tes réponses déjà enregistrées vont être téléchargées. Merci d'envoyer le fichier et ce message à l'expérimentateur.</p></div>""")
        if exp.rows:
            for r in exp.rows:
                r["aborted"] = 1
            exp.download(exp.csv_text(), exp.filename())
        raise
