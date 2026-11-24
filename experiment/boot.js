// Amorçage minimal : charge Pyodide, copie les fichiers de l'expérience dans son
// système de fichiers virtuel, puis lance la fonction Python flash_sound.main().
// Toute la logique de l'expérience est en Python (experiment/flash_sound.py).
"use strict";
(async function boot() {
  const status = (msg) => {
    const el = document.getElementById("boot-status");
    if (el) el.innerHTML = msg;
  };
  const params = new URLSearchParams(window.location.search);
  if (params.get("debug") === "1") document.body.classList.add("debug");
  try {
    if (typeof loadPyodide === "undefined") {
      throw new Error("Impossible de charger Pyodide (connexion Internet requise, ou CDN bloqué).");
    }
    const pyodide = await loadPyodide();
    status("Chargement de l'expérience…");
    const version = Date.now();  // évite les vieux fichiers en cache
    for (const f of ["config.py", "flash_sound.py", "trials.csv"]) {
      const resp = await fetch(`experiment/${f}?v=${version}`);
      if (!resp.ok) throw new Error(`Fichier introuvable : experiment/${f} (${resp.status})`);
      pyodide.FS.writeFile(`/home/pyodide/${f}`, await resp.text());
    }
    pyodide.runPython("import os, sys; os.chdir('/home/pyodide'); sys.path.insert(0, '/home/pyodide')");
    await pyodide.runPythonAsync("import flash_sound\nawait flash_sound.main()");
  } catch (err) {
    console.error(err);
    document.body.dataset.phase = "error";
    status(`<span class="error">Erreur au chargement : ${String(err.message || err).replace(/</g, "&lt;")}</span><br>
            Essaie avec Chrome, Edge ou Firefox récent, sur ordinateur, puis recharge la page.`);
  }
})();
