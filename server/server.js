// Bot WhatsApp + menu web pour restaurant.
// Node 18+ sans dépendance. Lancer :  node server.js
// Sans WA_TOKEN, le bot tourne en mode "simulation" : les messages sont affichés dans la console.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const DIR = path.dirname(fileURLToPath(import.meta.url));
loadEnv(path.join(DIR, ".env"));

const {
  WA_TOKEN = "",                 // jeton d'accès permanent (utilisateur système Meta)
  WA_PHONE_NUMBER_ID = "",       // ID du numéro dans WhatsApp Manager
  WA_VERIFY_TOKEN = "change-moi",// mot choisi par vous, à recopier dans la config du webhook Meta
  WA_APP_SECRET = "",            // secret de l'app Meta (vérifie la signature des webhooks)
  PUBLIC_URL = "http://localhost:3000", // adresse publique HTTPS du serveur
  MANAGER_NUMBERS = "",          // numéros des responsables, ex. 2250701020304,2250505060708
  WELCOME_IMAGE_URL = "",        // image facultative en tête du message de bienvenue
  ADMIN_KEY = "",                // mot de passe de la page /admin (bannière du menu)
  GRAPH_VERSION = "v21.0",
  PORT = "3000",
} = process.env;

const MENU_DIR = path.resolve(DIR, "../menu");
const DATA_DIR = process.env.DATA_DIR || path.join(DIR, "data");
fs.mkdirSync(DATA_DIR, { recursive: true });
const MANAGERS = MANAGER_NUMBERS.split(",").map(s => s.replace(/\D/g, "")).filter(Boolean);
const HUMAN_TIMEOUT = 2 * 3600e3;   // un client en conversation avec un responsable revient au bot après 2 h
const LINK_TTL = 12 * 3600e3;       // durée de validité d'un lien de menu

const menu = () => JSON.parse(fs.readFileSync(path.join(MENU_DIR, "menu.json"), "utf8"));
const sessions = new Map(); // tel -> { name, human: timestamp|0 }
const links = new Map();    // jeton -> { phone, exp }
const orders = loadOrders();

/* ---------------- WhatsApp Cloud API ---------------- */
async function wa(to, payload) {
  const body = { messaging_product: "whatsapp", recipient_type: "individual", to, ...payload };
  if (!WA_TOKEN || !WA_PHONE_NUMBER_ID) { console.log("[simulation] →", to, JSON.stringify(payload, null, 1)); return; }
  const r = await fetch(`https://graph.facebook.com/${GRAPH_VERSION}/${WA_PHONE_NUMBER_ID}/messages`, {
    method: "POST", headers: { Authorization: `Bearer ${WA_TOKEN}`, "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) console.error("Erreur WhatsApp", r.status, await r.text());
}
const text = (to, body) => wa(to, { type: "text", text: { body, preview_url: true } });
const toManagers = body => Promise.all(MANAGERS.map(m => text(m, body)));

async function sendWelcome(to, name) {
  const R = menu().restaurant;
  const first = (name || "").split(" ")[0];
  await wa(to, { type: "interactive", interactive: {
    type: "button",
    header: WELCOME_IMAGE_URL ? { type: "image", image: { link: WELCOME_IMAGE_URL } } : { type: "text", text: R.name },
    body: { text: `Bonjour${first ? " " + first : ""} 👋\nBienvenue ${/^chez /i.test(R.name) ? "" : "chez "}*${R.name}* !\n\nVoulez-vous passer une commande ou parler à un responsable ?` },
    footer: { text: R.tagline },
    action: { buttons: [
      { type: "reply", reply: { id: "ORDER", title: "🛒 Commander" } },
      { type: "reply", reply: { id: "HUMAN", title: "💬 Un responsable" } },
    ] },
  } });
}

async function sendMenuLink(to) {
  const token = crypto.randomBytes(12).toString("base64url");
  links.set(token, { phone: to, exp: Date.now() + LINK_TTL });
  const url = `${PUBLIC_URL.replace(/\/$/, "")}/menu?t=${token}`;
  await wa(to, { type: "interactive", interactive: {
    type: "cta_url",
    body: { text: "Voici notre menu 🍽️\nTournez les plats en 3D, retirez ce que vous n'aimez pas, ajoutez des suppléments, puis validez : la commande arrive ici." },
    action: { name: "cta_url", parameters: { display_text: "Ouvrir le menu", url } },
  } });
}

/* ---------------- Messages entrants ---------------- */
async function onMessage(msg, contact) {
  const from = msg.from;
  const name = contact?.profile?.name || "";
  const body = (msg.text?.body || "").trim();
  const button = msg.interactive?.button_reply?.id || msg.button?.payload || "";

  if (MANAGERS.includes(from)) {
    if (msg.type === "image" && /^\/pub\b/i.test(msg.image?.caption || "")) return setPromo(from, msg.image);
    return onManager(from, body);
  }

  const s = sessions.get(from) || { name, human: 0 };
  s.name = name || s.name; sessions.set(from, s);

  // Client en conversation avec un responsable : on transmet, sauf s'il redemande le menu.
  if (s.human && Date.now() - s.human < HUMAN_TIMEOUT && !/^(menu|commander)$/i.test(body) && button !== "ORDER") {
    s.human = Date.now();
    const what = body || `[${msg.type}]`;
    return toManagers(`💬 ${s.name || "Client"} (+${from}) :\n${what}\n\nRépondre : /r ${from} votre message\nTerminer : /fin ${from}`);
  }
  s.human = 0;

  if (button === "ORDER" || /^(commander|menu|carte)$/i.test(body)) return sendMenuLink(from);
  if (button === "HUMAN" || /responsable|humain|conseiller/i.test(body)) {
    s.human = Date.now();
    await text(from, "Très bien 🙏 Un responsable vous répond ici dans quelques instants.\nÉcrivez votre message ci-dessous.");
    return toManagers(`🔔 ${s.name || "Un client"} (+${from}) veut parler à un responsable.\n\nRépondre : /r ${from} votre message\nTerminer : /fin ${from}`);
  }
  return sendWelcome(from, s.name);
}

// Commandes des responsables, envoyées depuis leur WhatsApp au numéro du restaurant.
async function onManager(from, body) {
  const [cmd, arg, ...rest] = body.split(/\s+/);
  const msg = rest.join(" ");
  const STATUS = {
    "/ok": "✅ Votre commande n°{id} est confirmée et part en cuisine.",
    "/pret": "🍽️ Votre commande n°{id} est prête !",
    "/route": "🛵 Votre commande n°{id} est en route.",
    "/livre": "🎉 Commande n°{id} livrée. Bon appétit et merci !",
    "/annule": "❌ Désolé, votre commande n°{id} a été annulée. Un responsable vous contacte.",
  };
  switch ((cmd || "").toLowerCase()) {
    case "/r": {
      const to = (arg || "").replace(/\D/g, "");
      if (!to || !msg) return text(from, "Format : /r 2250700000000 votre message");
      const s = sessions.get(to) || { human: 0 }; s.human = Date.now(); sessions.set(to, s);
      await text(to, msg); return text(from, "✓ envoyé");
    }
    case "/fin": {
      const to = (arg || "").replace(/\D/g, ""); const s = sessions.get(to); if (s) s.human = 0;
      await text(to, "Merci pour votre message 🙏 Écrivez *menu* à tout moment pour commander.");
      return text(from, "✓ conversation terminée, le bot reprend la main");
    }
    case "/pub":
      if (/^(off|stop|retirer|supprimer)$/i.test(arg || "")) { fs.rmSync(PROMO_FILE, { force: true }); return text(from, "✓ bannière retirée, le menu affiche la bannière par défaut"); }
      return text(from, "Pour changer la bannière du menu : envoyez une image avec la légende /pub\nPour la retirer : /pub off");
    default:
      if (STATUS[cmd]) {
        const o = orders.get((arg || "").toUpperCase());
        if (!o) return text(from, `Commande ${arg || "?"} introuvable.`);
        o.status = cmd.slice(1); saveOrder(o);
        await text(o.phone, STATUS[cmd].replace("{id}", o.id));
        return text(from, `✓ client prévenu (${o.id} : ${o.status})`);
      }
      return text(from, "Commandes responsable :\n/r NUMÉRO message : répondre à un client\n/fin NUMÉRO : rendre la main au bot\nImage + légende /pub : changer la bannière du menu (/pub off pour la retirer)\n/ok ID · /pret ID · /route ID · /livre ID · /annule ID : suivi de commande");
  }
}

// Bannière publicitaire en tête du menu : image envoyée par un responsable avec la légende /pub.
const PROMO_FILE = path.join(DATA_DIR, "promo.jpg");
async function setPromo(from, image) {
  if (!WA_TOKEN) { console.log("[simulation] bannière reçue (média", image?.id, ") : non téléchargée sans WA_TOKEN"); return text(from, "(simulation) bannière reçue"); }
  const auth = { Authorization: `Bearer ${WA_TOKEN}` };
  const meta = await (await fetch(`https://graph.facebook.com/${GRAPH_VERSION}/${image.id}`, { headers: auth })).json();
  if (!meta.url) return text(from, "Impossible de récupérer l'image, réessayez.");
  const r = await fetch(meta.url, { headers: auth });
  if (!r.ok) return text(from, "Impossible de télécharger l'image, réessayez.");
  fs.writeFileSync(PROMO_FILE, Buffer.from(await r.arrayBuffer()));
  return text(from, "✓ nouvelle bannière en ligne dans le menu");
}

// Page /admin : le responsable choisit l'image de la bannière depuis son téléphone.
const ADMIN_HTML = `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bannière du menu</title>
<style>body{font:16px system-ui,sans-serif;margin:0;padding:20px;background:#2446a8;color:#fff}main{max-width:520px;margin:auto}h1{font-size:22px}
img{width:100%;border-radius:14px;background:#1b3585;min-height:80px;display:block;margin:12px 0}label,button,input{display:block;width:100%;box-sizing:border-box;margin:10px 0;font:inherit}
input{padding:12px;border-radius:10px;border:0}button{padding:14px;border:0;border-radius:12px;font-weight:700;background:#e5343b;color:#fff}button.alt{background:#f2922e}p{min-height:1.2em}</style></head>
<body><main><h1>Bannière en haut du menu</h1><img id="cur" alt="Bannière actuelle">
<label>Mot de passe<input id="key" type="password" autocomplete="current-password"></label>
<label>Nouvelle image<input id="file" type="file" accept="image/jpeg,image/png,image/webp"></label>
<button id="up">Mettre en ligne</button><button id="rm" class="alt">Retirer la bannière</button><p id="msg"></p></main>
<script>const $=s=>document.querySelector(s),msg=t=>$("#msg").textContent=t;
const load=async()=>{const p=await (await fetch("promo.json",{cache:"no-store"})).json();const m=await (await fetch("menu.json")).json();$("#cur").src=p.img||(m.promo&&m.promo.img)||"";};load();
$("#up").onclick=async()=>{const f=$("#file").files[0];if(!f)return msg("Choisissez une image.");const r=await fetch("api/promo?key="+encodeURIComponent($("#key").value),{method:"POST",headers:{"Content-Type":f.type},body:f});const j=await r.json();msg(r.ok?"✓ Bannière en ligne":j.error);load();};
$("#rm").onclick=async()=>{const r=await fetch("api/promo?key="+encodeURIComponent($("#key").value),{method:"DELETE"});const j=await r.json();msg(r.ok?"✓ Bannière retirée (bannière par défaut)":j.error);load();};</script></body></html>`;

/* ---------------- Commandes ---------------- */
function price(order) {
  const M = menu(), dishes = Object.fromEntries(M.dishes.map(d => [d.id, d]));
  const lines = [];
  for (const it of order.items || []) {
    const d = dishes[it.id]; if (!d) throw new Error("Plat inconnu : " + it.id);
    const qty = Math.max(1, Math.min(20, parseInt(it.qty) || 1));
    const removed = (it.removed || []).map(r => d.ingredients.find(i => i.id === r && !i.required)).filter(Boolean);
    const extras = Object.entries(it.extras || {}).map(([k, q]) => [d.extras?.find(e => e.id === k), Math.max(0, Math.min(3, parseInt(q) || 0))]).filter(([e, q]) => e && q);
    const size = d.sizes.find(z => z.id === it.size) || d.sizes[0];
    const exPrice = e => typeof e.price === "number" ? e.price : (e.price[size.id] ?? Object.values(e.price)[0]);
    const unit = size.price + extras.reduce((s, [e, q]) => s + exPrice(e) * q, 0);
    lines.push({ name: d.name + (d.sizes.length > 1 && size.label ? ` (${size.label})` : ""), qty, unit, total: unit * qty, removed: removed.map(i => i.name), extras: extras.map(([e, q]) => ({ name: e.name, qty: q })), note: String(it.note || "").slice(0, 140) });
  }
  if (!lines.length) throw new Error("Panier vide");
  const subtotal = lines.reduce((s, l) => s + l.total, 0);
  const fee = order.mode === "livraison" ? M.restaurant.deliveryFee || 0 : 0;
  return { lines, subtotal, fee, total: subtotal + fee };
}
const F = n => n.toLocaleString("fr-FR").replace(/[  ]/g, " ") + " F";
function receipt(o) {
  const L = [];
  for (const l of o.lines) {
    L.push(`*${l.qty}× ${l.name}* — ${F(l.total)}`);
    const m = [...l.removed.map(r => "sans " + r.toLowerCase()), ...l.extras.map(e => `+ ${e.qty > 1 ? e.qty + "× " : ""}${e.name.toLowerCase()}`)];
    if (l.note) m.push(`« ${l.note} »`);
    if (m.length) L.push("   _" + m.join(", ") + "_");
  }
  L.push("", `Sous-total : ${F(o.subtotal)}`); if (o.fee) L.push(`Livraison : ${F(o.fee)}`); L.push(`*Total : ${F(o.total)}*`);
  return L.join("\n");
}

async function createOrder(body) {
  const link = links.get(body.t);
  if (!link || link.exp < Date.now()) { const e = new Error("Ce lien a expiré. Écrivez « menu » sur WhatsApp pour en recevoir un nouveau."); e.status = 410; throw e; }
  const name = String(body.name || "").trim().slice(0, 60);
  const address = String(body.address || "").trim().slice(0, 200);
  const mode = body.mode === "emporter" ? "emporter" : "livraison";
  if (!name) throw Object.assign(new Error("Nom manquant"), { status: 400 });
  if (mode === "livraison" && address.length < 4) throw Object.assign(new Error("Adresse manquante"), { status: 400 });
  const p = price({ ...body, mode });
  const id = nextId();
  const o = { id, phone: link.phone, name, mode, address, note: String(body.note || "").slice(0, 200), ...p, status: "recue", at: new Date().toISOString() };
  saveOrder(o);
  const where = mode === "livraison" ? `📍 Livraison : ${address}` : "🏃 À emporter";
  await text(o.phone, `🧾 Commande *n°${id}* reçue, merci ${name.split(" ")[0]} !\n\n${receipt(o)}\n\n${where}\n\nNous vous confirmons très vite ici.`);
  await toManagers(`🆕 *Commande n°${id}*\n👤 ${name} (+${o.phone})\n${where}${o.note ? "\n📝 " + o.note : ""}\n\n${receipt(o)}\n\nConfirmer : /ok ${id}`);
  return o;
}
function nextId() { let id; do id = "A" + Math.floor(100 + Math.random() * 900); while (orders.has(id)); return id; }
function loadOrders() {
  const m = new Map(), f = path.join(DATA_DIR, "orders.jsonl");
  if (fs.existsSync(f)) for (const l of fs.readFileSync(f, "utf8").split("\n")) if (l) { try { const o = JSON.parse(l); m.set(o.id, o); } catch {} }
  return m;
}
function saveOrder(o) { orders.set(o.id, o); fs.appendFileSync(path.join(DATA_DIR, "orders.jsonl"), JSON.stringify(o) + "\n"); }

/* ---------------- HTTP ---------------- */
const pageHtml = () => `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><base href="/"></head><body>${fs.readFileSync(path.join(MENU_DIR, "index.html"), "utf8")}</body></html>`;

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  const send = (code, data, type = "application/json") => { res.writeHead(code, { "Content-Type": type + "; charset=utf-8", "Cache-Control": "no-store" }); res.end(type === "application/json" ? JSON.stringify(data) : data); };
  try {
    if (req.method === "GET" && url.pathname === "/webhook") {
      const ok = url.searchParams.get("hub.mode") === "subscribe" && url.searchParams.get("hub.verify_token") === WA_VERIFY_TOKEN;
      return ok ? send(200, url.searchParams.get("hub.challenge"), "text/plain") : send(403, "forbidden", "text/plain");
    }
    if (req.method === "POST" && url.pathname === "/webhook") {
      const raw = await readBody(req);
      if (WA_APP_SECRET) {
        const sig = req.headers["x-hub-signature-256"] || "";
        const expected = "sha256=" + crypto.createHmac("sha256", WA_APP_SECRET).update(raw).digest("hex");
        if (sig.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return send(401, { error: "signature" });
      }
      send(200, { ok: true }); // Meta attend une réponse rapide
      const data = JSON.parse(raw.toString() || "{}");
      for (const entry of data.entry || []) for (const ch of entry.changes || []) {
        const v = ch.value || {};
        for (const m of v.messages || []) onMessage(m, (v.contacts || []).find(c => c.wa_id === m.from)).catch(e => console.error(e));
      }
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/order") {
      try { const o = await createOrder(JSON.parse((await readBody(req)).toString())); return send(200, { id: o.id, total: o.total }); }
      catch (e) { return send(e.status || 400, { error: e.message }); }
    }
    if (req.method === "GET" && (url.pathname === "/" || url.pathname === "/menu")) return send(200, pageHtml(), "text/html");
    if (req.method === "GET" && url.pathname === "/menu.json") return send(200, menu());
    const img = url.pathname.match(/^\/img\/([a-z0-9-]+\.(jpg|png|webp))$/);
    if (req.method === "GET" && img) {
      const f = path.join(MENU_DIR, "img", img[1]);
      if (!fs.existsSync(f)) return send(404, { error: "not found" });
      res.writeHead(200, { "Content-Type": "image/" + (img[2] === "jpg" ? "jpeg" : img[2]), "Cache-Control": "public, max-age=86400" });
      return res.end(fs.readFileSync(f));
    }
    if (url.pathname === "/admin" && req.method === "GET") return send(200, ADMIN_HTML, "text/html");
    if (url.pathname === "/api/promo" && (req.method === "POST" || req.method === "DELETE")) {
      if (!ADMIN_KEY || url.searchParams.get("key") !== ADMIN_KEY) return send(403, { error: "mot de passe incorrect" });
      if (req.method === "DELETE") { fs.rmSync(PROMO_FILE, { force: true }); return send(200, { ok: true }); }
      if (!/^image\/(jpeg|png|webp)$/.test(req.headers["content-type"] || "")) return send(400, { error: "image JPG, PNG ou WebP attendue" });
      fs.writeFileSync(PROMO_FILE, await readBody(req, 8e6)); return send(200, { ok: true });
    }
    if (req.method === "GET" && url.pathname === "/promo.json") {
      return send(200, fs.existsSync(PROMO_FILE) ? { img: "promo.jpg?v=" + Math.round(fs.statSync(PROMO_FILE).mtimeMs), alt: "Offre du moment" } : {});
    }
    if (req.method === "GET" && url.pathname === "/promo.jpg" && fs.existsSync(PROMO_FILE)) {
      res.writeHead(200, { "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=300" });
      return res.end(fs.readFileSync(PROMO_FILE));
    }
    if (req.method === "GET" && url.pathname === "/health") return send(200, { ok: true, simulation: !WA_TOKEN });
    send(404, { error: "not found" });
  } catch (e) { console.error(e); if (!res.headersSent) send(500, { error: "erreur serveur" }); }
});
function readBody(req, max = 1e6) { return new Promise((ok, ko) => { const c = []; let n = 0; req.on("data", d => { n += d.length; if (n > max) { ko(new Error("trop gros")); req.destroy(); } else c.push(d); }); req.on("end", () => ok(Buffer.concat(c))); req.on("error", ko); }); }
function loadEnv(f) { if (!fs.existsSync(f)) return; for (const l of fs.readFileSync(f, "utf8").split(/\r?\n/)) { const m = l.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/); if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, ""); } }
setInterval(() => { const now = Date.now(); for (const [k, v] of links) if (v.exp < now) links.delete(k); }, 3600e3).unref();

server.listen(+PORT, () => console.log(`Serveur prêt sur :${PORT}${WA_TOKEN ? "" : " (simulation : aucun message réellement envoyé)"}  menu → ${PUBLIC_URL}/menu`));
