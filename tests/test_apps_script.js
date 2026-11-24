#!/usr/bin/env node
/*
 * Teste tools/google_apps_script.gs HORS de Google : les services Apps Script
 * (PropertiesService, LockService, ContentService, Drive, Utilities, Logger) sont simulés.
 * Vérifie : en-tête identique à CSV_COLUMNS (experiment/config.py), acceptation d'un vrai envoi
 * (tests/fixtures/sample_payload.json, produit par tests/test_upload.py), refus des envois
 * invalides, anti-doublon, absence de doGet.
 * Usage : node tests/test_apps_script.js
 */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..");
const code = fs.readFileSync(path.join(ROOT, "tools", "google_apps_script.gs"), "utf8");
let failures = 0;
function check(cond, msg) {
  console.log((cond ? "  ✔ " : "  ✘ ") + msg);
  if (!cond) failures++;
}

function makeContext(token) {
  const props = {};
  const created = [];
  const ctx = {
    PropertiesService: { getScriptProperties: () => ({
      getProperty: (k) => (k in props ? props[k] : null),
      setProperty: (k, v) => { props[k] = String(v); },
    }) },
    LockService: { getScriptLock: () => ({ tryLock: () => true, releaseLock: () => {} }) },
    ContentService: {
      MimeType: { JSON: "application/json" },
      createTextOutput: (s) => ({ text: s, setMimeType() { return this; } }),
    },
    Utilities: { newBlob: (data, mime, name) => ({ data, mime, name }) },
    Drive: { Files: { create: (meta, blob) => {
      const f = { id: "id" + (created.length + 1), meta, blob };
      created.push(f);
      return f;
    } } },
    Logger: { log: () => {} },
    JSON, String, Date,
  };
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  if (token !== undefined) vm.runInContext("SHARED_TOKEN = " + JSON.stringify(token), ctx);
  return { ctx, props, created };
}
function post(ctx, body) {
  const raw = typeof body === "string" ? body : JSON.stringify(body);
  return JSON.parse(ctx.doPost({ postData: { contents: raw } }).text);
}

// 1. En-tête : identique à config.py
const cfg = fs.readFileSync(path.join(ROOT, "experiment", "config.py"), "utf8");
const block = cfg.match(/CSV_COLUMNS\s*=\s*\[([\s\S]*?)\]/)[1];
const pyCols = [...block.replace(/#.*$/gm, "").matchAll(/"([^"]+)"/g)].map((m) => m[1]);
const { ctx: c0 } = makeContext();
check(JSON.stringify(pyCols) === JSON.stringify(Array.from(c0.EXPECTED_COLUMNS)),
      `EXPECTED_COLUMNS (.gs) == CSV_COLUMNS (config.py) [${pyCols.length} colonnes]`);
check(typeof c0.doGet === "undefined", "pas de doGet (aucune lecture possible par le Web)");
check(c0.MAX_BYTES <= 200000, "taille maximale ≤ 200 Ko");

// 2. Envoi valide (vrai corps produit par le navigateur)
const sample = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "sample_payload.json"), "utf8"));
let { ctx, props, created } = makeContext("test-token");
let r = post(ctx, sample);
check(r.ok === false && r.error === "not_set_up", "refus tant que setup() n'a pas été exécuté");
const folderId = ctx.setup();
check(props.FOLDER_ID === folderId && created[0].meta.mimeType === "application/vnd.google-apps.folder",
      "setup() crée le dossier et mémorise son identifiant");
check(ctx.setup() === folderId && created.length === 1, "setup() relancé : pas de second dossier");
r = post(ctx, sample);
check(r.ok === true && r.status === "stored", "envoi valide accepté (stored)");
const f = created[1];
check(f && f.meta.name === "flashson_" + sample.session_id + ".csv", "nom de fichier construit par le serveur");
check(f && f.meta.parents[0] === folderId && f.blob.data === sample.csv, "CSV écrit tel quel dans le dossier de collecte");
r = post(ctx, sample);
check(r.ok === true && r.status === "duplicate" && created.length === 2, "doublon détecté, rien de réécrit");

// 3. Envois invalides
function bad(label, mutate, expected, tokenCtx) {
  const t = makeContext(tokenCtx === undefined ? "test-token" : tokenCtx);
  t.ctx.setup();
  let body = JSON.parse(JSON.stringify(sample));
  body = mutate(body);
  const res = post(t.ctx, body);
  const ok = res.ok === false && String(res.error).startsWith(expected) && t.created.length === 1;
  check(ok, `${label} → refus (${res.error})`);
}
const lines = sample.csv.replace(/\n+$/, "").split("\n");
const sidCol = pyCols.indexOf("session_id");
const uaCol = pyCols.indexOf("user_agent");
function editCell(b, col, value) {
  const ls = b.csv.replace(/\n+$/, "").split("\n");
  const cells = ls[1].split(",");
  cells[col] = value;
  ls[1] = cells.join(",");
  b.csv = ls.join("\n") + "\n";
  return b;
}
bad("JSON invalide", () => "{pas du json", "json");
bad("trop gros (> MAX_BYTES)", (b) => { b.csv += "x".repeat(210000); return b; }, "too_large");
bad("mauvais jeton", (b) => { b.token = "faux"; return b; }, "invalid:token");
bad("jeton absent", (b) => { delete b.token; return b; }, "invalid:token");
bad("session_id avec chemin", (b) => { b.session_id = "../../etc"; return b; }, "invalid:session_id");
bad("en-tête modifié", (b) => { b.csv = b.csv.replace("participant_id", "nom"); return b; }, "invalid:header");
bad("colonne en trop", (b) => { b.csv = b.csv.replace(/\n(.)/, "\nX,$1"); return b; }, "invalid:columns");
bad("formule (=)", (b) => editCell(b, uaCol, "=HYPERLINK(1)"), "invalid:");
bad("formule (@)", (b) => editCell(b, uaCol, "@SUM(1)"), "invalid:");
bad("cellule « -x » non numérique", (b) => editCell(b, uaCol, "-cmd"), "invalid:cell");
bad("guillemets / caractères interdits", (b) => editCell(b, uaCol, '"a<b>"'), "invalid:chars");
bad("session_id incohérent dans les lignes", (b) => editCell(b, sidCol, "20990101-000000-abcd"), "invalid:session_mismatch");
bad("aucune ligne de données", (b) => { b.csv = lines[0] + "\n"; return b; }, "invalid:rows");
bad("trop de lignes", (b) => { b.csv = lines[0] + "\n" + Array(202).fill(lines[1]).join("\n") + "\n"; return b; }, "invalid:rows");

// 4. Sans jeton configuré, le même envoi passe (jeton ignoré)
const nt = makeContext("");
nt.ctx.setup();
r = post(nt.ctx, sample);
check(r.ok === true && r.status === "stored", "sans jeton configuré : envoi accepté");

console.log(failures === 0 ? "RÉSULTAT : OK" : `RÉSULTAT : ${failures} ÉCHEC(S)`);
process.exit(failures === 0 ? 0 : 1);
