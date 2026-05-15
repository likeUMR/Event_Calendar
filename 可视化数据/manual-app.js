const INDEX_URL = "../数据/活动信息_index.json";
const DATA_DIRS = ["../数据/活动信息_人工", "../数据/活动信息"];
const IMAGE_LAZY_ROOT_MARGIN = "320px";

const TYPE_LABELS = {
  battle_pass: "通行证",
  card_collection: "卡牌收集",
  collection_album: "收集图册",
  dig_event: "挖宝活动",
  expedition: "探索地图",
  expedition_event: "探索地图",
  flash_event: "短时增益",
  leaderboard_tournament: "排行榜赛事",
  main_event_board: "主活动棋盘",
  merge_2_event: "合成活动",
  merge_event: "合成活动",
  mini_event: "小游戏活动",
  mini_game: "小游戏",
  partner_event: "合作活动",
  peg_e: "随机掉落",
  puzzle_event: "解谜活动",
  pve_boss: "PVE Boss",
  pvp_war: "PVP 战争",
  race_event: "竞速活动",
  racer_event: "竞速活动",
  resource_boost_event: "资源增益",
  season_event: "赛季活动",
  season_pass: "赛季通行证",
  solo_tournament: "个人锦标赛",
  sticker_album: "贴纸图册",
  streak_event: "连胜任务",
  team_event: "团队活动",
  team_events: "团队活动",
  tournament: "锦标赛",
  tournament_competition: "锦标赛",
  trade_fest: "交易强化",
  treasure_dig: "挖宝活动",
};

const FAMILY_LABELS = {
  progression: "成长推进",
  leaderboard: "排行竞争",
  pass_track: "通行证/奖励轨",
  collection: "收集图册",
  team_coop: "组队合作",
  pvp: "对抗战争",
  pve: "PVE/Boss",
  minigame: "小游戏/副玩法",
  economy: "资源促活",
  quest_board: "任务链/阶段目标",
  social: "社交交易",
  seasonal: "赛季/节庆包装",
  content: "内容更新/系统扩展",
  catalog: "资料页/活动目录",
  other: "其他",
};

const TYPE_FAMILY_OVERRIDES = {
  albums_stickers: "collection",
  archive_subscription: "catalog",
  battle_pass: "pass_track",
  battle_league: "leaderboard",
  battlefield_pvp: "pvp",
  card_trading_team: "social",
  card_collection: "collection",
  challenge_coop: "team_coop",
  challenge_event: "quest_board",
  challenge_solo: "quest_board",
  challenge_team: "team_coop",
  clan_games: "team_coop",
  clan_war_league: "pvp",
  collection_album: "collection",
  collection_chain_event: "collection",
  collection_milestone: "collection",
  collection_showcase: "collection",
  collection_treasure: "collection",
  competition_solo: "leaderboard",
  competition_team: "team_coop",
  community_boss: "pve",
  daily_bonus: "economy",
  daily_puzzle_drop: "quest_board",
  decoration_redesign: "content",
  dig_event: "minigame",
  dungeon_stage_event: "minigame",
  editorial_hint_companion: "content",
  energy_resource: "economy",
  esports_qualifier: "leaderboard",
  expedition: "minigame",
  expedition_event: "minigame",
  factory_pass: "pass_track",
  flash_event: "economy",
  garden_pass: "pass_track",
  go_fest_tour_live: "seasonal",
  golden_ticket: "pass_track",
  knowledge_quiz: "minigame",
  leaderboard_tournament: "leaderboard",
  legacy_collection_event: "collection",
  legacy_seasonal_event: "seasonal",
  main_event_board: "progression",
  map_pve_invasion: "pve",
  medal_event: "quest_board",
  merge_event: "minigame",
  merge_2_event: "minigame",
  mini_game: "minigame",
  mini_event: "minigame",
  mode_rotation: "content",
  monarch_competition: "leaderboard",
  new_server_path: "progression",
  official_events_catalog: "catalog",
  order_stockpile_cycle: "quest_board",
  partner_event: "team_coop",
  peg_e: "minigame",
  pick_or_risk_minigame: "minigame",
  premium_or_paywalled_track: "pass_track",
  puzzle_mania_publication: "content",
  pve_boss: "pve",
  pvp_war: "pvp",
  puzzle_event: "minigame",
  raid_event: "pvp",
  raid_weekend: "pvp",
  racer_event: "leaderboard",
  race_event: "leaderboard",
  regular_task_event: "quest_board",
  research_day: "seasonal",
  resource_boost_event: "economy",
  restaurant_progression: "progression",
  season_pass: "pass_track",
  season_of_wonders: "seasonal",
  season_pass_reward_track: "pass_track",
  season_challenges: "quest_board",
  season_event: "seasonal",
  seasonal_festival: "seasonal",
  solo_tournament: "leaderboard",
  solo_race_events: "leaderboard",
  solo_competition: "leaderboard",
  special_slot_quest: "minigame",
  spin_multiplier: "economy",
  spin_volume_milestone: "quest_board",
  spotlight_hour: "economy",
  step_goal_events: "quest_board",
  sticker_album: "collection",
  store_offer: "economy",
  streak_booster_events: "economy",
  streak_event: "quest_board",
  streak_stats: "leaderboard",
  subscriber_gating: "pass_track",
  team_event: "team_coop",
  team_alliance: "team_coop",
  team_events: "team_coop",
  team_go_rocket: "team_coop",
  themed_generator_event: "content",
  tournament: "leaderboard",
  tournament_competition: "leaderboard",
  trade_fest: "social",
  treasure_cave: "minigame",
  treasure_dig: "minigame",
  temporary_troop_spell: "economy",
  village_progression: "progression",
  win_streak_bonus: "economy",
  world_championship: "leaderboard",
  source_catalog: "catalog",
  unknown: "other",
};

const state = {
  games: [],
  cards: [],
  filteredCards: [],
};

const els = {
  gameFilter: document.querySelector("#game-filter"),
  familyFilter: document.querySelector("#family-filter"),
  typeFilter: document.querySelector("#type-filter"),
  search: document.querySelector("#manual-search"),
  visualOnly: document.querySelector("#visual-only"),
  meta: document.querySelector("#manual-meta"),
  typeCloud: document.querySelector("#type-cloud"),
  title: document.querySelector("#manual-title"),
  statGames: document.querySelector("#stat-games"),
  statFamilies: document.querySelector("#stat-families"),
  statTypes: document.querySelector("#stat-types"),
  statImages: document.querySelector("#stat-images"),
  selectedRank: document.querySelector("#selected-rank"),
  selectedName: document.querySelector("#selected-name"),
  selectedMethod: document.querySelector("#selected-method"),
  selectedCoverage: document.querySelector("#selected-coverage"),
  resultCount: document.querySelector("#result-count"),
  activityGrid: document.querySelector("#activity-grid"),
  sourceList: document.querySelector("#source-list"),
  visualList: document.querySelector("#visual-list"),
  dialog: document.querySelector("#manual-dialog"),
  dialogGame: document.querySelector("#dialog-game"),
  dialogName: document.querySelector("#dialog-name"),
  dialogBody: document.querySelector("#dialog-body"),
  dialogClose: document.querySelector("#manual-dialog-close"),
};

init();

async function init() {
  bindEvents();
  await loadManualData();
}

function bindEvents() {
  els.gameFilter.addEventListener("change", render);
  els.familyFilter.addEventListener("change", handleFamilyChange);
  els.typeFilter.addEventListener("change", render);
  els.search.addEventListener("input", render);
  els.visualOnly.addEventListener("change", render);
  els.dialogClose.addEventListener("click", () => els.dialog.close());
}

function handleFamilyChange() {
  renderTypeFilter();
  render();
}

async function loadManualData() {
  try {
    els.meta.textContent = "正在加载人工整理数据...";
    const entries = await loadIndexEntries();
    const payloads = await Promise.all(entries.map((entry) => loadGamePayload(entry)));

    state.games = payloads.sort((a, b) => Number(a.rank || 999) - Number(b.rank || 999));
    state.cards = state.games.flatMap((game) => normalizeActivities(game));

    renderGameFilter();
    renderFamilyFilter();
    renderTypeFilter();
    render();

    const familyCount = new Set(state.cards.map((card) => card.family)).size;
    els.meta.textContent = `${state.games.length} 个游戏 · ${state.cards.length} 个活动条目 · ${familyCount} 个机制大类`;
  } catch (error) {
    els.meta.textContent = `数据加载失败：${error.message}`;
    els.activityGrid.innerHTML = '<p class="empty">无法加载 JSON。请从项目根目录启动本地服务后访问页面。</p>';
  }
}

async function loadIndexEntries() {
  const response = await fetch(INDEX_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`活动信息_index.json HTTP ${response.status}`);
  }

  const entries = await readJsonResponse(response);
  if (!Array.isArray(entries)) {
    throw new Error("活动信息_index.json 格式错误");
  }

  return entries
    .map((entry) => ({
      ...entry,
      fileName: fileNameFromPath(entry.file),
    }))
    .filter((entry) => entry.fileName);
}

async function loadGamePayload(entry) {
  const candidates = DATA_DIRS.map((dir) => `${dir}/${entry.fileName}`);
  const errors = [];

  for (const url of candidates) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      errors.push(`${entry.fileName} HTTP ${response.status}`);
      continue;
    }

    const payload = await readJsonResponse(response);
    return {
      ...payload,
      data_source_path: url,
      data_source_kind: url.includes("活动信息_人工") ? "人工整理" : "自动采集",
    };
  }

  throw new Error(errors.join("；"));
}

async function readJsonResponse(response) {
  const text = await response.text();
  return JSON.parse(text.replace(/^\uFEFF/, ""));
}

function fileNameFromPath(path) {
  return String(path || "").split(/[\\/]/).pop();
}

function normalizeActivities(game) {
  if (Array.isArray(game.activity_types) && game.activity_types.length) {
    return game.activity_types.map((activity) => normalizeManualActivity(game, activity));
  }

  if (Array.isArray(game.event_catalog) && game.event_catalog.length) {
    return game.event_catalog.map((activity) => normalizeCatalogActivity(game, activity));
  }

  const types = Array.isArray(game.inferred_event_type_summary) ? game.inferred_event_type_summary : [];
  const images = normalizeImages(game.screenshots_or_images || []);
  if (!types.length && !images.length) {
    return [];
  }

  return [
    normalizeCatalogActivity(game, {
      title: "资料页与视觉参考",
      description: game.source_notes || "本文件没有拆到具体活动条目，先汇总展示已采集到的来源与图片。",
      inferred_event_types: types,
      images,
    }),
  ];
}

function normalizeManualActivity(game, activity) {
  return normalizeCardBase({
    ...activity,
    gameRank: Number(game.rank || 999),
    gameName: game.name,
    gameStatus: game.manual_research_status || game.data_source_kind || "-",
    gameCoverage: game.coverage_notes || game.source_notes || "",
    gameMethod: game.research_method || game.methodology || "",
    type: activity.type || "unknown",
    label: activity.display_name || activity.type || "未命名活动",
    description: activity.description || "",
    notes: activity.market_research_notes || "",
    examples: Array.isArray(activity.examples) ? activity.examples : [],
    images: normalizeImages(activity.images || []),
  });
}

function normalizeCatalogActivity(game, activity) {
  const inferredTypes = Array.isArray(activity.inferred_event_types) ? activity.inferred_event_types : [];
  const primaryType = inferredTypes[0] || activity.type || "source_catalog";
  return normalizeCardBase({
    ...activity,
    gameRank: Number(game.rank || 999),
    gameName: game.name,
    gameStatus: game.data_source_kind || game.source_confidence || "-",
    gameCoverage: game.source_notes || "",
    gameMethod: game.methodology || "",
    type: primaryType,
    label: activity.title || activity.display_name || labelForType(primaryType),
    description: activity.description || activity.meta_description || "",
    notes: activity.discovered_from ? `发现来源：${activity.discovered_from}` : "",
    examples: inferredTypes,
    sourceUrl: activity.url || activity.source_url || activity.fetched_url,
    images: normalizeImages(activity.images || []),
  });
}

function normalizeCardBase(card) {
  const family = familyForType(card.type);
  return {
    ...card,
    family,
    familyLabel: labelForFamily(family),
  };
}

function familyForType(type) {
  const normalized = String(type || "unknown").trim().toLowerCase();
  if (TYPE_FAMILY_OVERRIDES[normalized]) {
    return TYPE_FAMILY_OVERRIDES[normalized];
  }

  const rules = [
    { family: "pass_track", keywords: ["pass", "ticket", "reward_track", "premium", "subscriber"] },
    { family: "collection", keywords: ["album", "sticker", "collection", "card", "treasure"] },
    { family: "team_coop", keywords: ["team", "alliance", "partner", "clan", "coop", "community"] },
    { family: "pvp", keywords: ["war", "duel", "raid", "battlefield", "arena", "capital"] },
    { family: "pve", keywords: ["boss", "pve", "invasion", "monster", "tyrant"] },
    { family: "leaderboard", keywords: ["tournament", "leaderboard", "competition", "race", "racer", "league", "championship"] },
    { family: "minigame", keywords: ["mini", "dig", "peg", "puzzle", "merge", "expedition", "quiz", "slot"] },
    { family: "economy", keywords: ["boost", "bonus", "cash", "store", "offer", "multiplier", "resource", "energy"] },
    { family: "quest_board", keywords: ["task", "quest", "goal", "streak", "milestone", "challenge", "step"] },
    { family: "social", keywords: ["trade", "social", "discussion"] },
    { family: "seasonal", keywords: ["season", "festival", "holiday", "tour", "live"] },
    { family: "content", keywords: ["generator", "redesign", "rotation", "publication", "new_server", "village", "restaurant"] },
    { family: "catalog", keywords: ["catalog", "source"] },
  ];

  for (const rule of rules) {
    if (rule.keywords.some((keyword) => normalized.includes(keyword))) {
      return rule.family;
    }
  }

  return "other";
}

function labelForFamily(family) {
  return FAMILY_LABELS[family] || FAMILY_LABELS.other;
}

function normalizeImages(images) {
  const seen = new Set();
  const normalized = (Array.isArray(images) ? images : [])
    .map((image, originalIndex) => ({
      ...image,
      originalIndex,
      url: image.url || "",
      caption: image.caption || image.alt || image.kind || "",
      source_url: image.source_url || image.sourceUrl || "",
      filterCategory: imageFilterCategory(image),
      hasLongLoad: hasLongLoadMarker(image),
    }))
    .filter((image) => image.filterCategory !== 1)
    .filter((image) => {
      if (!image.url || seen.has(image.url)) {
        return false;
      }
      seen.add(image.url);
      return true;
    });

  if (normalized.some((image) => image.filterCategory !== null)) {
    normalized.sort((a, b) => imageSortRank(a) - imageSortRank(b) || a.originalIndex - b.originalIndex);
  }

  return normalized;
}

function hasLongLoadMarker(image) {
  return Boolean(
    image?.image_load_check?.long_load ||
      image?.remote_load_check?.long_load ||
      image?.load_profile?.long_load,
  );
}

function imageFilterCategory(image) {
  const category = Number(image?.llm_image_filter?.category);
  return Number.isInteger(category) && category >= 1 && category <= 5 ? category : null;
}

function imageSortRank(image) {
  if (image.hasLongLoad) {
    return 100;
  }
  if (image.filterCategory === null) {
    return 4;
  }
  return 5 - image.filterCategory;
}

function renderGameFilter() {
  for (const game of state.games) {
    const option = document.createElement("option");
    option.value = String(game.rank);
    option.textContent = `#${game.rank} ${game.name}`;
    els.gameFilter.append(option);
  }
}

function renderFamilyFilter() {
  const families = [...new Set(state.cards.map((card) => card.family))].sort((a, b) =>
    labelForFamily(a).localeCompare(labelForFamily(b), "zh-CN"),
  );
  const previous = els.familyFilter.value || "all";
  els.familyFilter.innerHTML = '<option value="all">全部大类</option>';

  for (const family of families) {
    const option = document.createElement("option");
    option.value = family;
    option.textContent = labelForFamily(family);
    els.familyFilter.append(option);
  }

  els.familyFilter.value = families.includes(previous) ? previous : "all";
}

function renderTypeFilter() {
  const selectedFamily = els.familyFilter.value;
  const types = [...new Set(
    state.cards
      .filter((card) => selectedFamily === "all" || card.family === selectedFamily)
      .map((card) => card.type),
  )].sort((a, b) => labelForType(a).localeCompare(labelForType(b), "zh-CN"));

  const previous = els.typeFilter.value || "all";
  els.typeFilter.innerHTML = '<option value="all">全部类型</option>';
  for (const type of types) {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = labelForType(type);
    els.typeFilter.append(option);
  }

  els.typeFilter.value = types.includes(previous) ? previous : "all";
}

function render() {
  const selectedGame = els.gameFilter.value;
  const selectedFamily = els.familyFilter.value;
  const selectedType = els.typeFilter.value;
  const keyword = els.search.value.trim().toLowerCase();
  const visualOnly = els.visualOnly.checked;

  state.filteredCards = state.cards.filter((card) => {
    const searchable = [
      card.gameName,
      card.type,
      card.family,
      card.familyLabel,
      card.label,
      card.description,
      card.notes,
      card.examples.join(" "),
    ]
      .join(" ")
      .toLowerCase();

    const matchesGame = selectedGame === "all" || String(card.gameRank) === selectedGame;
    const matchesFamily = selectedFamily === "all" || card.family === selectedFamily;
    const matchesType = selectedType === "all" || card.type === selectedType;
    const matchesKeyword = !keyword || searchable.includes(keyword);
    const matchesVisual = !visualOnly || card.images.length > 0;
    return matchesGame && matchesFamily && matchesType && matchesKeyword && matchesVisual;
  });

  renderSelectedSummary();
  renderStats();
  renderTypeCloud();
  renderActivityCards();
  renderSources();
  renderVisuals();
}

function renderSelectedSummary() {
  const game = selectedGame();
  const selectedFamily = els.familyFilter.value;
  const familyText = selectedFamily === "all" ? "全部机制大类" : labelForFamily(selectedFamily);

  if (game) {
    els.title.textContent = `${game.name} 活动信息看板`;
    els.selectedRank.textContent = `Rank #${game.rank} · ${game.manual_research_status || game.data_source_kind || game.source_confidence || "-"}`;
    els.selectedName.textContent = game.name;
    els.selectedMethod.textContent = game.research_method || game.methodology || "暂无研究方法说明。";
    els.selectedCoverage.textContent = `${game.coverage_notes || game.source_notes || "暂无覆盖说明。"} 当前聚合视角：${familyText}。`;
    return;
  }

  els.title.textContent = "活动信息展示看板";
  els.selectedRank.textContent = "Manual Summary";
  els.selectedName.textContent = "全部游戏活动机制总览";
  els.selectedMethod.textContent =
    "当前在细分 type 之上新增了一层“机制大类”归一化，用于把近义机制先聚合到更稳定的分析口径。";
  els.selectedCoverage.textContent =
    `你现在可以先按机制大类横向比较，再回到具体 type 看细分差异。当前筛选：${familyText}。`;
}

function renderStats() {
  const cards = state.filteredCards;
  const gameRanks = new Set(cards.map((card) => card.gameRank));
  const families = new Set(cards.map((card) => card.family));
  const selectedGames = state.games.filter((game) => gameRanks.has(Number(game.rank || 999)));
  const visualCount =
    cards.reduce((total, card) => total + card.images.length, 0) +
    selectedGames.reduce((total, game) => total + gameVisualsForGame(game).length, 0);

  els.statGames.textContent = gameRanks.size;
  els.statFamilies.textContent = families.size;
  els.statTypes.textContent = cards.length;
  els.statImages.textContent = visualCount;
}

function renderTypeCloud() {
  const counts = new Map();
  for (const card of state.cards) {
    counts.set(card.family, (counts.get(card.family) || 0) + 1);
  }

  els.typeCloud.innerHTML = "";
  for (const [family, count] of [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 14)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = els.familyFilter.value === family ? "type-chip is-active" : "type-chip";
    button.textContent = `${labelForFamily(family)} ${count}`;
    button.addEventListener("click", () => {
      els.familyFilter.value = els.familyFilter.value === family ? "all" : family;
      renderTypeFilter();
      render();
    });
    els.typeCloud.append(button);
  }
}

function renderActivityCards() {
  els.resultCount.textContent = `${state.filteredCards.length} 条`;
  els.activityGrid.innerHTML = "";

  if (!state.filteredCards.length) {
    els.activityGrid.innerHTML = '<p class="empty">没有符合筛选条件的活动类型。</p>';
    return;
  }

  for (const card of state.filteredCards) {
    const article = document.createElement("article");
    article.className = "activity-card";
    article.innerHTML = `
      ${card.images[0] ? '<img class="activity-thumb" alt="">' : ""}
      <div class="activity-card-body">
        <div class="card-kicker">
          <span>#${card.gameRank} ${escapeHtml(card.gameName)}</span>
          <span>${escapeHtml(card.familyLabel)}</span>
          <span>${escapeHtml(labelForType(card.type))}</span>
        </div>
        <h4>${escapeHtml(card.label)}</h4>
        <p>${escapeHtml(card.description)}</p>
        ${renderExamples(card.examples)}
        ${card.notes ? `<p class="research-note">${escapeHtml(card.notes)}</p>` : ""}
      </div>
    `;
    attachImageFallback(article.querySelector(".activity-thumb"), card.images);
    article.addEventListener("click", () => openDialog(card));
    els.activityGrid.append(article);
  }
}

function attachImageFallback(image, candidates) {
  if (!image || !Array.isArray(candidates)) {
    return;
  }
  image.style.visibility = "hidden";
  let nextIndex = 0;

  const useNextImage = () => {
    const next = candidates[nextIndex];
    nextIndex += 1;
    if (next?.url) {
      loadControlledImage(image, next.url, {
        onFailure: useNextImage,
      });
      return;
    }
    image.remove();
  };

  observeLazyImage(image, useNextImage);
}

function hideBrokenImageItem(image, item, url = image?.getAttribute("src")) {
  if (!image || !item) {
    return;
  }
  const hideItem = () => {
    item.hidden = true;
  };
  observeLazyImage(image, () => {
    if (url) {
      loadControlledImage(image, url, { onFailure: hideItem });
    } else {
      hideItem();
    }
  });
}

let lazyImageObserver = null;

function observeLazyImage(image, startLoad) {
  if (!image || typeof startLoad !== "function") {
    return;
  }
  if (!("IntersectionObserver" in window)) {
    startLoad();
    return;
  }
  image.__startControlledLoad = startLoad;
  if (!lazyImageObserver) {
    lazyImageObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) {
            continue;
          }
          lazyImageObserver.unobserve(entry.target);
          const loader = entry.target.__startControlledLoad;
          delete entry.target.__startControlledLoad;
          if (typeof loader === "function") {
            loader();
          }
        }
      },
      { rootMargin: IMAGE_LAZY_ROOT_MARGIN },
    );
  }
  lazyImageObserver.observe(image);
}

function loadControlledImage(image, url, { onFailure } = {}) {
  const token = globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  image.dataset.loadToken = token;
  image.style.visibility = "hidden";
  image.removeAttribute("src");

  const probe = new Image();
  probe.decoding = "async";
  probe.loading = "eager";

  const finish = (failed) => {
    if (image.dataset.loadToken !== token) {
      return;
    }
    probe.onload = null;
    probe.onerror = null;
    if (failed && typeof onFailure === "function") {
      onFailure();
    }
  };

  probe.onload = () => {
    if (image.dataset.loadToken !== token) {
      return;
    }
    if (imageLooksInvalid(probe)) {
      finish(true);
      return;
    }
    image.src = url;
    image.style.visibility = "visible";
    finish(false);
  };
  probe.onerror = () => finish(true);
  probe.src = url;
}

function imageLooksInvalid(image) {
  if (!image.naturalWidth || !image.naturalHeight) {
    return true;
  }
  if (image.naturalWidth < 80 || image.naturalHeight < 60) {
    return true;
  }
  return imageLooksLikePlaceholder(image);
}

function imageLooksLikePlaceholder(image) {
  const canvas = document.createElement("canvas");
  const size = 24;
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) {
    return false;
  }

  try {
    context.drawImage(image, 0, 0, size, size);
    const pixels = context.getImageData(0, 0, size, size).data;
    let visible = 0;
    let neutral = 0;
    let luminanceSum = 0;
    let luminanceSqSum = 0;

    for (let index = 0; index < pixels.length; index += 4) {
      const alpha = pixels[index + 3] / 255;
      if (alpha < 0.2) {
        continue;
      }
      const red = pixels[index] / 255;
      const green = pixels[index + 1] / 255;
      const blue = pixels[index + 2] / 255;
      const max = Math.max(red, green, blue);
      const min = Math.min(red, green, blue);
      const luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue;
      const saturation = max === 0 ? 0 : (max - min) / max;

      visible += 1;
      luminanceSum += luminance;
      luminanceSqSum += luminance * luminance;
      if (saturation < 0.08 && luminance > 0.55) {
        neutral += 1;
      }
    }

    if (!visible) {
      return true;
    }

    const averageLuminance = luminanceSum / visible;
    const variance = luminanceSqSum / visible - averageLuminance * averageLuminance;
    const neutralRatio = neutral / visible;
    return neutralRatio > 0.82 && variance < 0.025;
  } catch (error) {
    return false;
  }
}

function renderExamples(examples) {
  if (!examples.length) {
    return "";
  }
  return `<div class="example-row">${examples
    .slice(0, 5)
    .map((example) => `<span>${escapeHtml(example)}</span>`)
    .join("")}</div>`;
}

function renderSources() {
  const gameRanks = new Set(state.filteredCards.map((card) => card.gameRank));
  const games = state.games.filter((game) => gameRanks.has(Number(game.rank || 999)));
  const sources = games.flatMap((game) => sourcesForGame(game));

  els.sourceList.innerHTML = "";
  if (!sources.length) {
    els.sourceList.innerHTML = '<p class="empty">暂无来源页面。</p>';
    return;
  }

  for (const source of sources) {
    const item = document.createElement("a");
    item.className = "source-item";
    item.href = source.url || "#";
    item.target = "_blank";
    item.rel = "noreferrer";
    item.innerHTML = `
      <span>#${source.rank} ${escapeHtml(source.gameName)}</span>
      <strong>${escapeHtml(source.title || "未命名来源")}</strong>
      <small>${escapeHtml(source.notes || "")}</small>
    `;
    els.sourceList.append(item);
  }
}

function renderVisuals() {
  const gameRanks = new Set(state.filteredCards.map((card) => card.gameRank));
  const games = state.games.filter((game) => gameRanks.has(Number(game.rank || 999)));
  const visuals = [
    ...state.filteredCards.flatMap((card) =>
      card.images.map((image) => ({
        title: card.label,
        caption: image.caption,
        url: image.url,
        sourceUrl: image.source_url,
        gameName: card.gameName,
      })),
    ),
    ...games.flatMap((game) => gameVisualsForGame(game)),
  ].filter((item) => item.url || item.sourceUrl);

  els.visualList.innerHTML = "";
  if (!visuals.length) {
    els.visualList.innerHTML = '<p class="empty">暂无图片或截图参考。</p>';
    return;
  }

  for (const visual of visuals) {
    const item = document.createElement("a");
    item.className = `visual-item${visual.url ? "" : " is-reference"}`;
    item.href = visual.sourceUrl || visual.url;
    item.target = "_blank";
    item.rel = "noreferrer";
    item.innerHTML = `
      ${visual.url ? '<img alt="">' : '<div class="visual-placeholder">Ref</div>'}
      <div>
        <span>${escapeHtml(visual.gameName)}</span>
        <strong>${escapeHtml(visual.title || "视觉参考")}</strong>
        <small>${escapeHtml(visual.caption || "打开来源查看详情")}</small>
      </div>
    `;
    hideBrokenImageItem(item.querySelector("img"), item, visual.url);
    els.visualList.append(item);
  }
}

function sourcesForGame(game) {
  return [
    ...(game.source_pages || []).map((source) => ({
      title: source.title,
      url: source.url,
      notes: source.notes,
      gameName: game.name,
      rank: game.rank,
    })),
    ...(game.sources || []).map((source) => ({
      title: source.source_title || source.title,
      url: source.source_url || source.url || source.fetched_url,
      notes: source.meta_description || source.error || source.source_type || "",
      gameName: game.name,
      rank: game.rank,
    })),
    ...(game.event_detail_pages || []).map((source) => ({
      title: source.source_title || source.title,
      url: source.source_url || source.url || source.fetched_url,
      notes: source.meta_description || source.error || source.source_type || "",
      gameName: game.name,
      rank: game.rank,
    })),
  ].filter((source) => source.url);
}

function gameVisualsForGame(game) {
  return [
    ...(game.screenshot_or_visual_references || []).map((item) => ({
      title: "视觉参考",
      caption: item.description,
      sourceUrl: item.source_url,
      gameName: game.name,
    })),
    ...normalizeImages(game.screenshots_or_images || []).map((item) => ({
      title: "视觉参考",
      caption: item.caption,
      url: item.url,
      sourceUrl: item.source_url,
      gameName: game.name,
    })),
  ];
}

function openDialog(card) {
  els.dialogGame.textContent = `#${card.gameRank} ${card.gameName} · ${card.familyLabel}`;
  els.dialogName.textContent = card.label;
  els.dialogBody.innerHTML = `
    <p>${escapeHtml(card.description)}</p>
    <h4>归类结果</h4>
    <div class="example-row">
      <span>${escapeHtml(card.familyLabel)}</span>
      <span>${escapeHtml(labelForType(card.type))}</span>
    </div>
    ${card.examples.length ? `<h4>样例</h4><div class="example-row">${card.examples
      .map((example) => `<span>${escapeHtml(example)}</span>`)
      .join("")}</div>` : ""}
    ${card.notes ? `<h4>市场研究备注</h4><p>${escapeHtml(card.notes)}</p>` : ""}
    ${card.sourceUrl ? `<h4>来源</h4><p><a href="${escapeAttr(card.sourceUrl)}" target="_blank" rel="noreferrer">${escapeHtml(card.sourceUrl)}</a></p>` : ""}
    ${card.images.length ? `<h4>图片（${card.images.length} 张）</h4><div class="dialog-visuals">${card.images
      .map((image, index) => `<a href="${escapeAttr(image.source_url || image.url)}" target="_blank" rel="noreferrer" data-image-index="${index}"><img alt=""><span>${escapeHtml(image.caption || "打开来源")}</span></a>`)
      .join("")}</div>` : ""}
  `;
  els.dialog.showModal();
  els.dialogBody.querySelectorAll(".dialog-visuals a").forEach((item) => {
    const image = card.images[Number(item.dataset.imageIndex)];
    hideBrokenImageItem(item.querySelector("img"), item, image?.url);
  });
}

function selectedGame() {
  if (els.gameFilter.value === "all") {
    return null;
  }
  return state.games.find((game) => String(game.rank) === els.gameFilter.value) || null;
}

function labelForType(type) {
  const key = String(type || "unknown");
  if (TYPE_LABELS[key]) {
    return TYPE_LABELS[key];
  }
  return key
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}
