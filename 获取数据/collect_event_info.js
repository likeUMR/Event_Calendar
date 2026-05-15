const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");
const { URL } = require("url");

const root = path.resolve(__dirname, "..");
const inputPath = path.join(root, "数据", "game_event_info_sources.json");
const outputDir = path.join(root, "数据", "活动信息");
const ACTIVITY_IMAGE_TARGET = 5;

const EVENT_TERMS = [
  "event", "events", "tournament", "challenge", "season", "pass", "cup",
  "race", "treasure", "collection", "album", "quest", "raid", "battle",
  "league", "festival", "adventure", "expedition", "partner", "alliance",
  "team", "reward", "calendar", "limited", "special", "competition",
  "活动", "赛事", "赛季", "通行证", "挑战", "锦标赛", "联盟", "收集"
];

const TYPE_RULES = [
  ["battle_pass", /pass|golden ticket|home pass|factory pass|toon pass|通行证/i],
  ["collection_album", /collection|album|card|sticker|set|pack|badge|收集|卡牌|贴纸/i],
  ["tournament_competition", /tournament|competition|leaderboard|cup|race|league|contest|rank|锦标赛|排行榜|竞赛/i],
  ["team_alliance", /team|alliance|clan|guild|partner|co-op|cooperative|联盟|公会|战队|合作/i],
  ["seasonal_festival", /season|festival|holiday|halloween|christmas|anniversary|easter|ramadan|valentine|节日|周年/i],
  ["merge_event", /merge|generator|energy|item chain|合成/i],
  ["pve_boss", /boss|monster|zombie|beast|raid|pve|bear|tyrant|boss fight/i],
  ["pvp_war", /war|battlefield|kill event|svs|server war|pvp|state of power|战争|跨服/i],
  ["mini_game", /mini-game|minigame|prize drop|wheel|casino|slot|fishing|dig|treasure hunt|小游戏|转盘/i],
  ["store_offer", /offer|store|shop|purchase|paywall|bundle|礼包|商店|充值/i]
];

const IMAGE_EXT_RE = /\.(?:png|jpe?g|webp|gif)(?:[?#].*)?$/i;
const NOISE_URL_RE = /(?:favicon|logo|sprite|avatar|pixel|tracking|blank|placeholder|1x1\.gif|apps\.apple\.com\/assets|supports-|\/tr(?:[?#]|$)|google\.com\/logos)/i;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function slugify(input) {
  return input
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_")
    .slice(0, 80);
}

function decodeEntities(text) {
  return (text || "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/&#x([a-f0-9]+);/gi, (_, n) => String.fromCharCode(parseInt(n, 16)));
}

function stripTags(html) {
  return decodeEntities((html || "").replace(/<[^>]+>/g, " "))
    .replace(/\s+/g, " ")
    .trim();
}

function absolutize(base, maybeUrl) {
  if (!maybeUrl || maybeUrl.startsWith("data:") || maybeUrl.startsWith("javascript:")) return null;
  try {
    return new URL(maybeUrl, base).toString();
  } catch {
    return null;
  }
}

function isCleanImageUrl(url) {
  if (!url || !url.startsWith("http")) return false;
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (NOISE_URL_RE.test(url)) return false;
  if (/facebook\.com|doubleclick|googletagmanager|schema\.org/i.test(parsed.hostname)) return false;
  if (/encrypted-tbn|gstatic\.com|googleusercontent\.com/i.test(parsed.hostname)) return true;
  return IMAGE_EXT_RE.test(parsed.pathname);
}

function imageKey(url) {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    const cleanPath = parsed.pathname.replace(/\/$/, "");
    if (/encrypted-tbn/.test(host) || cleanPath.endsWith("/images")) {
      return `${host}${cleanPath}?${parsed.searchParams.toString()}`;
    }
    return `${host}${cleanPath}`;
  } catch {
    return url || "";
  }
}

function pushUniqueImage(target, seen, image, sourceUrl) {
  if (!image || !isCleanImageUrl(image.url)) return false;
  const key = imageKey(image.url);
  if (!key || seen.has(key)) return false;
  seen.add(key);
  target.push(sourceUrl ? { ...image, source_url: sourceUrl } : image);
  return true;
}

function fetchUrl(url, redirects = 4) {
  return new Promise((resolve) => {
    const lib = url.startsWith("http://") ? http : https;
    const req = lib.get(
      url,
      {
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; EventCalendarResearch/1.0)",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.8"
        },
        timeout: 20000
      },
      (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location && redirects > 0) {
          const next = absolutize(url, res.headers.location);
          res.resume();
          if (next) return resolve(fetchUrl(next, redirects - 1));
        }
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          resolve({ ok: res.statusCode >= 200 && res.statusCode < 400, status: res.statusCode, url, body });
        });
      }
    );
    req.on("timeout", () => {
      req.destroy();
      resolve({ ok: false, status: 0, url, body: "", error: "timeout" });
    });
    req.on("error", (error) => resolve({ ok: false, status: 0, url, body: "", error: error.message }));
  });
}

function removeNoise(html) {
  return (html || "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<svg[\s\S]*?<\/svg>/gi, " ");
}

function extractTitle(html) {
  const h1 = /<h1[^>]*>([\s\S]*?)<\/h1>/i.exec(html);
  if (h1) return stripTags(h1[1]);
  const title = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(html);
  return title ? stripTags(title[1]) : "";
}

function extractMetaDescription(html) {
  const meta = /<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["'][^>]*>/i.exec(html)
    || /<meta[^>]+content=["']([^"']+)["'][^>]+name=["']description["'][^>]*>/i.exec(html);
  return meta ? decodeEntities(meta[1]).trim() : "";
}

function extractTextBlocks(html) {
  const clean = removeNoise(html);
  const blocks = [];
  const re = /<(h2|h3|h4|p|li|figcaption|td|th)[^>]*>([\s\S]*?)<\/\1>/gi;
  let match;
  while ((match = re.exec(clean))) {
    const text = stripTags(match[2]);
    if (text.length >= 20 && text.length <= 700) blocks.push({ tag: match[1].toLowerCase(), text });
  }
  return blocks;
}

function extractImages(html, baseUrl) {
  const images = [];
  const seen = new Set();
  const og = /<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["'][^>]*>/i.exec(html)
    || /<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["'][^>]*>/i.exec(html);
  if (og) {
    const src = absolutize(baseUrl, decodeEntities(og[1]));
    if (isCleanImageUrl(src)) {
      seen.add(imageKey(src));
      images.push({ url: src, alt: "og:image", kind: "preview" });
    }
  }

  const imgRe = /<img\b[^>]*>/gi;
  let match;
  while ((match = imgRe.exec(html)) && images.length < 12) {
    const tag = match[0];
    const srcMatch = /\b(?:src|data-src|data-original|data-image-name)=["']([^"']+)["']/i.exec(tag);
    if (!srcMatch) continue;
    const src = absolutize(baseUrl, decodeEntities(srcMatch[1]));
    if (!isCleanImageUrl(src)) continue;
    const key = imageKey(src);
    if (seen.has(key)) continue;
    const alt = /\balt=["']([^"']*)["']/i.exec(tag);
    seen.add(key);
    images.push({ url: src, alt: alt ? decodeEntities(alt[1]).trim() : "", kind: "page_image" });
  }
  return images;
}

function extractLinks(html, baseUrl) {
  const links = [];
  const seen = new Set();
  const re = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match;
  while ((match = re.exec(html))) {
    const text = stripTags(match[2]);
    if (!text || text.length > 120) continue;
    const url = absolutize(baseUrl, decodeEntities(match[1]));
    if (!url || seen.has(url)) continue;
    seen.add(url);
    links.push({ title: text, url });
  }
  return links;
}

function isEventish(text) {
  const lower = (text || "").toLowerCase();
  return EVENT_TERMS.some((term) => lower.includes(term.toLowerCase()));
}

function scoreLink(link, sourceUrl) {
  const text = `${link.title} ${link.url}`.toLowerCase();
  let score = 0;
  if (isEventish(text)) score += 4;
  if (/\/wiki\/category.*events|\/category:events|\/events?\/?$|tag\/events/i.test(link.url)) score += 5;
  if (/fandom\.com|wiki|support|helpshift|zendesk/i.test(link.url)) score += 1;
  try {
    const a = new URL(link.url);
    const b = new URL(sourceUrl);
    if (a.hostname === b.hostname) score += 1;
  } catch {}
  if (/edit|history|signin|login|register|facebook|twitter|instagram|youtube|privacy|terms/i.test(link.url)) score -= 8;
  return score;
}

function extractEventCandidates(links, sourceUrl) {
  return links
    .map((link) => ({ ...link, score: scoreLink(link, sourceUrl) }))
    .filter((link) => link.score >= 4)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);
}

function selectRelevantBlocks(blocks) {
  const selected = [];
  for (const block of blocks) {
    if (selected.length >= 18) break;
    if (block.tag.startsWith("h") || isEventish(block.text)) selected.push(block.text);
  }
  if (selected.length < 6) {
    for (const block of blocks) {
      if (selected.length >= 10) break;
      if (!selected.includes(block.text)) selected.push(block.text);
    }
  }
  return selected;
}

function classifyEventTypes(text) {
  const found = [];
  for (const [type, re] of TYPE_RULES) {
    if (re.test(text)) found.push(type);
  }
  return found;
}

function summarizePage(source, fetched) {
  const html = fetched.body || "";
  const blocks = extractTextBlocks(html);
  const relevant = selectRelevantBlocks(blocks);
  const textBlob = relevant.join(" ");
  return {
    source_title: source.title,
    source_type: source.type,
    source_url: source.url,
    fetched_url: fetched.url,
    status: fetched.status,
    page_title: extractTitle(html),
    meta_description: extractMetaDescription(html),
    relevant_text_blocks: relevant,
    inferred_event_types: classifyEventTypes(textBlob),
    images: extractImages(html, source.url)
  };
}

async function collectForGame(game) {
  const outputPath = path.join(outputDir, `${String(game.rank).padStart(2, "0")}_${slugify(game.name)}.json`);
  const result = {
    rank: game.rank,
    name: game.name,
    source_confidence: game.confidence,
    source_notes: game.notes || null,
    collected_at: new Date().toISOString(),
    methodology: "Open web HTML fetch from the preselected low-login-risk sources. For each source, extract event-related headings, paragraphs, links, and image URLs; follow a small number of event-like links for detail pages.",
    sources: [],
    event_detail_pages: [],
    event_catalog: [],
    inferred_event_type_summary: [],
    screenshots_or_images: [],
    collection_warnings: []
  };

  const detailLinks = [];
  const detailSeen = new Set();
  const typeSet = new Set();
  const imageSeen = new Set();

  for (const source of game.sources || []) {
    const fetched = await fetchUrl(source.url);
    if (!fetched.ok) {
      result.sources.push({
        source_title: source.title,
        source_type: source.type,
        source_url: source.url,
        status: fetched.status,
        error: fetched.error || "fetch_failed"
      });
      result.collection_warnings.push(`Fetch failed: ${source.url}`);
      await sleep(400);
      continue;
    }

    const pageSummary = summarizePage(source, fetched);
    result.sources.push(pageSummary);
    for (const t of pageSummary.inferred_event_types) typeSet.add(t);
    for (const img of pageSummary.images) {
      pushUniqueImage(result.screenshots_or_images, imageSeen, img, source.url);
    }

    const links = extractLinks(fetched.body, source.url);
    for (const link of extractEventCandidates(links, source.url)) {
      if (!detailSeen.has(link.url) && detailLinks.length < 12) {
        detailSeen.add(link.url);
        detailLinks.push({ ...link, discovered_from: source.url });
      }
    }
    await sleep(500);
  }

  for (const link of detailLinks.slice(0, 6)) {
    const fetched = await fetchUrl(link.url);
    if (!fetched.ok) {
      result.event_detail_pages.push({
        title: link.title,
        url: link.url,
        discovered_from: link.discovered_from,
        status: fetched.status,
        error: fetched.error || "fetch_failed"
      });
      await sleep(400);
      continue;
    }

    const page = summarizePage({ title: link.title, type: "event_detail", url: link.url }, fetched);
    const title = page.page_title || link.title;
    const description = (page.meta_description || page.relevant_text_blocks.find((x) => x.length > 40) || "").slice(0, 500);
    const eventTypes = classifyEventTypes(`${title} ${description} ${page.relevant_text_blocks.join(" ")}`);
    for (const t of eventTypes) typeSet.add(t);
    for (const img of page.images) {
      pushUniqueImage(result.screenshots_or_images, imageSeen, img, link.url);
    }

    const catalogImages = [];
    const catalogImageSeen = new Set();
    for (const image of page.images) {
      pushUniqueImage(catalogImages, catalogImageSeen, image);
      if (catalogImages.length >= ACTIVITY_IMAGE_TARGET) break;
    }

    result.event_detail_pages.push(page);
    result.event_catalog.push({
      title,
      url: link.url,
      discovered_from: link.discovered_from,
      description,
      inferred_event_types: eventTypes,
      images: catalogImages
    });
    await sleep(600);
  }

  result.inferred_event_type_summary = Array.from(typeSet).sort();
  result.screenshots_or_images = result.screenshots_or_images.slice(0, 30);

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf8");
  return outputPath;
}

async function main() {
  ensureDir(outputDir);
  const games = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  const startRank = Number(process.argv[2] || 1);
  const endRank = Number(process.argv[3] || 999);
  for (const game of games) {
    if (game.rank < startRank || game.rank > endRank) continue;
    const file = await collectForGame(game);
    console.log(`saved rank=${game.rank} ${game.name} -> ${path.relative(root, file)}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
