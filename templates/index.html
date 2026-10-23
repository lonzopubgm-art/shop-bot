<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Stilmen | Mens Wear</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root{--bg:#0e0e10;--card:#18181b;--line:#2a2a2f;--gold:#d4af37;--text:#f4f4f5;--mute:#9a9aa3}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{background:var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI",Roboto,sans-serif;padding-bottom:100px}
body.lock{overflow:hidden}
header{padding:18px 16px 8px;text-align:center}
.brand{font-size:26px;font-weight:800;letter-spacing:4px;color:var(--gold)}
.sub{font-size:12px;letter-spacing:3px;color:var(--mute);margin-top:2px}
.top{position:sticky;top:0;z-index:5;background:var(--bg);padding-bottom:4px}
.search{margin:12px 16px 0}
input,textarea{width:100%;background:var(--card);border:1px solid var(--line);color:var(--text);border-radius:12px;padding:13px 14px;font-size:16px;outline:none;font-family:inherit}
input:focus,textarea:focus{border-color:var(--gold)}
.cats{display:flex;gap:8px;overflow-x:auto;padding:14px 16px 4px;scrollbar-width:none}
.cats::-webkit-scrollbar{display:none}
.chip{flex:none;padding:9px 16px;border-radius:20px;border:1px solid var(--line);background:var(--card);color:var(--text);font-size:14px;cursor:pointer}
.chip.on{background:var(--gold);border-color:var(--gold);color:#111;font-weight:600}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:14px 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;cursor:pointer;transition:transform .15s}
.card:active{transform:scale(.97)}
.pic{aspect-ratio:4/5;background:#232327;display:flex;align-items:center;justify-content:center;font-size:56px}
.pic img{width:100%;height:100%;object-fit:cover}
.info{padding:10px 12px 14px}
.name{font-size:14px;line-height:1.3;min-height:36px}
.price{color:var(--gold);font-weight:700;margin-top:6px}
.empty{grid-column:1/-1;text-align:center;color:var(--mute);padding:40px 0}
.btn{width:100%;border:0;border-radius:14px;padding:15px;font-size:16px;font-weight:700;background:var(--gold);color:#111;cursor:pointer}
.btn:disabled{opacity:.5}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:flex-end;z-index:20}
.overlay.show{display:flex}
.sheet{background:var(--bg);width:100%;max-height:90vh;overflow-y:auto;border-radius:22px 22px 0 0;padding:18px 16px 24px;border-top:1px solid var(--line)}
.sheet h3{font-size:18px;margin-bottom:10px}
.close{float:right;background:var(--card);border:0;color:var(--text);width:34px;height:34px;border-radius:50%;font-size:16px}
.big{aspect-ratio:1.2;border-radius:14px;overflow:hidden;background:#232327;display:flex;align-items:center;justify-content:center;font-size:90px;margin:8px 0 12px}
.big img{width:100%;height:100%;object-fit:cover}
.label{font-size:13px;color:var(--mute);margin:14px 0 8px}
.opts{display:flex;flex-wrap:wrap;gap:8px}
.row{display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid var(--line)}
.row .t{flex:1;font-size:14px}
.row .t small{display:block;color:var(--mute);margin-top:3px}
.qty{display:flex;align-items:center;gap:10px}
.qty button{width:30px;height:30px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--text);font-size:18px}
.total{display:flex;justify-content:space-between;font-size:17px;font-weight:700;margin:16px 0 12px}
.total span:last-child{color:var(--gold)}
.form{display:grid;gap:10px;margin-bottom:14px}
.bar{position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:10;display:none}
.bar.show{display:block}
.bar .btn{display:flex;justify-content:space-between;box-shadow:0 6px 24px rgba(0,0,0,.5)}
.toast{position:fixed;top:16px;left:50%;transform:translateX(-50%);background:var(--gold);color:#111;padding:10px 18px;border-radius:20px;font-weight:600;font-size:14px;z-index:50;display:none;white-space:nowrap}
</style>
</head>
<body>

<header>
  <div class="brand">STILMEN</div>
  <div class="sub">MENS WEAR</div>
</header>
<div class="top">
  <div class="search"><input id="q" placeholder="🔍 Qidirish..."></div>
  <div class="cats" id="cats"></div>
</div>
<div class="grid" id="grid"></div>

<div class="bar" id="bar">
  <button class="btn" onclick="openCart()"><span id="barCount"></span><span id="barTotal"></span></button>
</div>

<div class="overlay" id="pOv" onclick="if(event.target===this)closeAll()"><div class="sheet" id="pSheet"></div></div>
<div class="overlay" id="cOv" onclick="if(event.target===this)closeAll()"><div class="sheet" id="cSheet"></div></div>
<div class="toast" id="toast"></div>

<script>
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready(); tg.expand();
  try { tg.setHeaderColor('#0e0e10'); tg.setBackgroundColor('#0e0e10'); } catch(e){}
  try { tg.BackButton.onClick(() => closeAll()); } catch(e){}
}

let PRODUCTS = [], CATS = ["Hammasi"];
let cat = "Hammasi", cart = [], cur = null, selSize = "", selColor = "";
const CART_KEY = "stilmen_cart_v1";
const $ = id => document.getElementById(id);
const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " so'm";

/* ---------- XAVFSIZLIK: HTML'ni tozalash ---------- */
function esc(s){
  return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}
function safeUrl(u){
  u = String(u || "").trim();
  return /^(https?:\/\/|\/)/i.test(u) && !/^\/\//.test(u) ? u : "";
}
function pic(p){
  const url = safeUrl(p.img);
  if (url) return `<img src="${esc(url)}" alt="" loading="lazy" onerror="this.replaceWith(document.createTextNode('👕'))">`;
  return esc(p.emoji || "👕");
}

/* ---------- Tovarlarni tekshirib olish ---------- */
function cleanProduct(p){
  if (!p || typeof p !== "object") return null;
  const id = Number(p.id), price = Number(p.price);
  if (!Number.isFinite(id) || !Number.isFinite(price) || price < 0) return null;
  const arr = a => Array.isArray(a) ? a.map(String).filter(Boolean) : [];
  return {
    id, price,
    name: String(p.name || "Nomsiz tovar"),
    cat: String(p.cat || "Boshqa"),
    img: p.img || "", emoji: p.emoji || "",
    sizes: arr(p.sizes).length ? arr(p.sizes) : ["Standart"],
    colors: arr(p.colors).length ? arr(p.colors) : ["Standart"]
  };
}

/* ---------- Savatni saqlash ---------- */
function saveCart(){
  try { localStorage.setItem(CART_KEY, JSON.stringify(cart)); } catch(e){}
}
function loadCart(){
  try {
    const raw = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
    if (!Array.isArray(raw)) return;
    cart = raw.map(i => {
      const p = PRODUCTS.find(x => x.id === Number(i.pid));
      if (!p || !p.sizes.includes(i.size) || !p.colors.includes(i.color)) return null;
      const qty = Math.min(99, Math.max(1, parseInt(i.qty) || 1));
      return {key: p.id+"|"+i.size+"|"+i.color, pid:p.id, name:p.name, price:p.price, size:i.size, color:i.color, qty};
    }).filter(Boolean);
  } catch(e){ cart = []; }
}

async function init(){
  try{
    const r = await fetch("/api/products");
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    if (!Array.isArray(data)) throw new Error("bad data");
    PRODUCTS = data.map(cleanProduct).filter(Boolean);
  }catch(e){
    PRODUCTS = [];
    toast("Tovarlarni yuklab bo'lmadi");
  }
  CATS = ["Hammasi", ...new Set(PRODUCTS.map(p => p.cat))];
  loadCart();
  renderCats(); renderGrid(); updateBar();
}

function renderCats(){
  $("cats").innerHTML = CATS.map((c,i) =>
    `<button class="chip ${c===cat?"on":""}" onclick="setCat(${i})">${esc(c)}</button>`).join("");
}
function setCat(i){ cat = CATS[i]; renderCats(); renderGrid(); }

function renderGrid(){
  const s = $("q").value.trim().toLowerCase();
  const list = PRODUCTS.filter(p => (cat==="Hammasi" || p.cat===cat) && p.name.toLowerCase().includes(s));
  $("grid").innerHTML = list.length ? list.map(p =>
    `<div class="card" onclick="openProduct(${p.id})">
       <div class="pic">${pic(p)}</div>
       <div class="info"><div class="name">${esc(p.name)}</div><div class="price">${fmt(p.price)}</div></div>
     </div>`).join("") : '<div class="empty">Tovar topilmadi</div>';
}

function showSheet(id){
  $(id).classList.add("show");
  document.body.classList.add("lock");
  try { tg && tg.BackButton.show(); } catch(e){}
}

function openProduct(id){
  cur = PRODUCTS.find(p => p.id===id);
  if (!cur) return;
  selSize = cur.sizes[0]; selColor = cur.colors[0];
  renderProduct();
  showSheet("pOv");
}
function renderProduct(){
  const p = cur;
  $("pSheet").innerHTML =
    `<button class="close" onclick="closeAll()">✕</button>
     <h3>${esc(p.name)}</h3>
     <div class="big">${pic(p)}</div>
     <div class="price" style="font-size:20px">${fmt(p.price)}</div>
     <div class="label">Razmer</div>
     <div class="opts">${p.sizes.map((s,i)=>`<button class="chip ${s===selSize?"on":""}" onclick="pick('size',${i})">${esc(s)}</button>`).join("")}</div>
     <div class="label">Rang</div>
     <div class="opts">${p.colors.map((c,i)=>`<button class="chip ${c===selColor?"on":""}" onclick="pick('color',${i})">${esc(c)}</button>`).join("")}</div>
     <div style="height:18px"></div>
     <button class="btn" onclick="addToCart()">Savatga qo'shish</button>`;
}
function pick(t,i){
  if (t==="size") selSize = cur.sizes[i]; else selColor = cur.colors[i];
  renderProduct();
}

function addToCart(){
  const key = cur.id + "|" + selSize + "|" + selColor;
  const ex = cart.find(i => i.key===key);
  if (ex) ex.qty = Math.min(99, ex.qty + 1);
  else cart.push({key, pid:cur.id, name:cur.name, price:cur.price, size:selSize, color:selColor, qty:1});
  closeAll(); updateBar(); toast("Savatga qo'shildi ✅");
}

function totalSum(){ return cart.reduce((s,i) => s + i.price*i.qty, 0); }
function updateBar(){
  const n = cart.reduce((s,i) => s + i.qty, 0);
  $("bar").classList.toggle("show", n>0);
  $("barCount").textContent = "🛒 Savat (" + n + ")";
  $("barTotal").textContent = fmt(totalSum());
  saveCart();
}

function openCart(){ renderCart(); showSheet("cOv"); }
function renderCart(){
  $("cSheet").innerHTML =
    `<button class="close" onclick="closeAll()">✕</button><h3>🛒 Savat</h3>` +
    cart.map((i,x) =>
      `<div class="row">
         <div class="t">${esc(i.name)}<small>${esc(i.size)} · ${esc(i.color)} · ${fmt(i.price)}</small></div>
         <div class="qty"><button onclick="chg(${x},-1)">−</button><b>${i.qty}</b><button onclick="chg(${x},1)">+</button></div>
       </div>`).join("") +
    `<div class="total"><span>Jami:</span><span>${fmt(totalSum())}</span></div>
     <div class="form">
       <input id="fName" placeholder="Ismingiz" autocomplete="name" maxlength="60">
       <input id="fPhone" type="tel" placeholder="Telefon: +998 90 123 45 67" autocomplete="tel" maxlength="20">
       <textarea id="fAddr" rows="2" placeholder="Manzil" maxlength="200"></textarea>
     </div>
     <button class="btn" id="sendBtn" onclick="sendOrder()">Buyurtma berish</button>`;
}
function chg(x,d){
  const ids = ["fName","fPhone","fAddr"];
  const v = ids.map(id => $(id).value);
  cart[x].qty = Math.min(99, cart[x].qty + d);
  if (cart[x].qty <= 0) cart.splice(x,1);
  updateBar();
  if (!cart.length){ closeAll(); return; }
  renderCart();
  ids.forEach((id,k) => $(id).value = v[k]);
}

function normPhone(s){
  let d = String(s).replace(/\D/g, "");
  if (d.length === 9) d = "998" + d;
  return /^998\d{9}$/.test(d) ? "+" + d : "";
}

async function sendOrder(){
  const name = $("fName").value.trim(), addr = $("fAddr").value.trim();
  const phone = normPhone($("fPhone").value);
  if (name.length < 2){ toast("Ismingizni kiriting"); return; }
  if (!phone){ toast("Telefon raqam noto'g'ri (+998 XX XXX XX XX)"); return; }
  if (addr.length < 5){ toast("Manzilni to'liq kiriting"); return; }

  const u = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const btn = $("sendBtn");
  btn.disabled = true; btn.textContent = "Yuborilmoqda...";
  try{
    const r = await fetch("/api/order", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        // YANGI: serverda tekshirish uchun
        init_data: tg ? tg.initData : "",
        customer: {name, phone, address: addr},
        items: cart.map(i => ({id:i.pid, size:i.size, color:i.color, qty:i.qty})),
        // ESKI format: server yangilanguncha ishlashi uchun (keyin o'chirasiz)
        cart: cart.map(i => ({name:i.name, qty:i.qty, price:i.price, size:i.size + " / " + i.color})),
        total: totalSum(),
        user: {first_name: name + " | " + phone + " | " + addr, username: u.username || "", id: u.id || "-"}
      })
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const d = await r.json();
    if (d.status !== "success") throw new Error();
    cart = []; updateBar(); closeAll();
    toast("Buyurtma qabul qilindi! ✅");
    setTimeout(() => { if (tg) tg.close(); }, 1500);
  }catch(e){
    btn.disabled = false; btn.textContent = "Buyurtma berish";
    toast("Xatolik, qayta urinib ko'ring");
  }
}

function closeAll(){
  $("pOv").classList.remove("show");
  $("cOv").classList.remove("show");
  document.body.classList.remove("lock");
  try { tg && tg.BackButton.hide(); } catch(e){}
}
function toast(m){
  const t = $("toast"); t.textContent = m; t.style.display = "block";
  clearTimeout(t._h); t._h = setTimeout(() => t.style.display = "none", 2000);
}

let _deb;
$("q").addEventListener("input", () => { clearTimeout(_deb); _deb = setTimeout(renderGrid, 250); });
init();
</script>
</body>
</html>
