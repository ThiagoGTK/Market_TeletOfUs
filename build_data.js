const fs = require('fs');
const items = require('./ip_array.json');

const mapNames = {
  plains: "Planície",
  forest: "Floresta Sombria",
  swamp: "Pântano",
  grave: "Cemitério Antigo",
  desert: "Deserto Escaldante",
  mountain: "Montanhas Gélidas",
  abyss: "Abismo",
  deep_forest: "Floresta Profunda",
  oasis: "Oásis Perdido",
};

function inferClass(s) {
  if (s.class_req) return s.class_req;
  const u = `${s.key} ${s.name}`.toLowerCase();
  if (s.slot === "consumable" || s.slot === "key") return null;
  if (s.slot === "quiver") return "arqueiro";
  if (s.slot === "shield") {
    if (u.includes("tomo") || u.includes("livro") || u.includes("grimório") || u.includes("grimo") || u.includes("orbe") || u.includes("orb")) return "mago";
    if (u.includes("escudo")) return "guerreiro";
  }
  if (u.includes("arco") || u.includes("bow") || u.includes("besta") || u.includes("crossbow") || u.includes("lança") || u.includes("lance") || u.includes("algibeira")) return "arqueiro";
  if (u.includes("cajado") || u.includes("báculo") || u.includes("baculo") || u.includes("varinha") || u.includes("wand") || u.includes("staff") || u.includes("rod") || u.includes("tomo") || u.includes("livro") || u.includes("grimório") || u.includes("grimo") || u.includes("orbe") || u.includes("orb")) return "mago";
  if (u.includes("machado") || u.includes("axe") || u.includes("espada") || u.includes("blade") || u.includes("sabre") || u.includes("escudo") || u.includes("armadura") || u.includes("couraça") || u.includes("cota")) return "guerreiro";
  return null;
}

function attrs(y) {
  if (y.description) return y.description;
  const v = [];
  if (y.atk_min || y.atk_max) v.push(`ATK ${y.atk_min}–${y.atk_max}`);
  if (y.def_min || y.def_max) v.push(`DEF ${y.def_min}–${y.def_max}`);
  if (y.hp_min || y.hp_max) v.push(`HP ${y.hp_min}–${y.hp_max}`);
  if (y.crit_min || y.crit_max) v.push(`CRIT ${y.crit_min}–${y.crit_max}%`);
  if (y.inventory_slots_bonus !== undefined) v.push(`SLOTS +${y.inventory_slots_bonus}`);
  if (v.length === 0) {
    if (y.key === "health_potion") return "Cura 100% HP";
    if (y.key === "energy_potion") return "+5 Energia";
    if (y.key.includes("tonic")) return "Buff Temporário (30 min)";
    if (y.key === "dungeon_key") return "Acesso à Masmorra";
    if (y.key === "bone_key") return "Acesso à Masmorra Especial";
  }
  return v.join(", ") || "—";
}

function location(y) {
  let loc = y.map_key ? (mapNames[y.map_key] || y.map_key) : "Global/Lojas";
  const tags = [];
  if (y.boss_only) tags.push("Boss");
  if (y.boss_dungeon_only) tags.push("Boss DG");
  if (tags.length) loc += ` (${tags.join(", ")})`;
  return loc;
}

const relevantSlots = ["weapon", "armor", "shield", "ring", "amulet", "boots", "quiver", "backpack", "consumable", "key", "skin"];

const SEASONAL_KEYS = new Set(["chocolate_magico", "ovo_de_ouro", "ev_ring_sap_ancestral"]);

function isSeasonal(y) {
  if (SEASONAL_KEYS.has(y.key)) return true;
  if (y.rarity === "event") return true;
  if (y.key.startsWith("ev_")) return true;
  const d = (y.description || "").toLowerCase();
  return d.includes("páscoa") || d.includes("outono") || d.includes("só aparece") || d.includes("evento de");
}

const marketPricesPath = __dirname + '/telegram_market/market_prices.json';
const marketPrices = fs.existsSync(marketPricesPath) ? JSON.parse(fs.readFileSync(marketPricesPath, 'utf8')) : {};

const bonusItems = JSON.parse(fs.readFileSync(__dirname + '/bonus_items.json', 'utf8'))
  .map(y => ({ ...y, market: marketPrices[y.key] || null }));

const out = items
  .filter(y => relevantSlots.includes(y.slot))
  .map(y => ({
    key: y.key,
    name: y.name.includes("�") ? y.name.replace(/[�️]+\s*/, "🗺️ ") : y.name,
    slot: y.slot,
    rarity: y.rarity,
    class: inferClass(y),
    level: y.slot === "skin" ? (y.level_req ?? null) : (y.level_req || 1),
    location: location(y),
    attrs: attrs(y),
    dropRate: y.drop_rate ? `${(y.drop_rate * 100).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}%` : null,
    tradeable: y.tradeable !== false,
    twoHanded: !!y.two_handed,
    seasonal: isSeasonal(y),
    market: marketPrices[y.key] || null,
  }))
  .concat(bonusItems)
  .sort((a, b) => (a.level ?? 9999) - (b.level ?? 9999) || a.name.localeCompare(b.name, "pt-BR"));

fs.writeFileSync(__dirname + '/items_final.json', JSON.stringify(out, null, 2));
console.log("Total:", out.length, `(${bonusItems.length} especiais)`);
console.log("By class:", out.reduce((acc, x) => { acc[x.class || "universal"] = (acc[x.class || "universal"] || 0) + 1; return acc; }, {}));
console.log("Com preco de mercado:", out.filter(x => x.market).length);
