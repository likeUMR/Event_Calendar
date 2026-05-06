const DAY_MS = 24 * 60 * 60 * 1000;
const COLORS = [
  "#7257ff",
  "#de7a22",
  "#0f9f6e",
  "#d33f6a",
  "#1f7fd1",
  "#7b5b2a",
  "#8d4ac7",
  "#217985",
];

const state = {
  payload: null,
  events: [],
  filteredEvents: [],
  categories: [],
  categoryColors: new Map(),
  lifecycles: [],
  tracks: [],
  trackMeta: new Map(),
};

const els = {
  dataSource: document.querySelector("#data-source"),
  dataMeta: document.querySelector("#data-meta"),
  searchInput: document.querySelector("#search-input"),
  categoryFilter: document.querySelector("#category-filter"),
  rangeFilter: document.querySelector("#range-filter"),
  legend: document.querySelector("#legend"),
  statEvents: document.querySelector("#stat-events"),
  statDays: document.querySelector("#stat-days"),
  statCategories: document.querySelector("#stat-categories"),
  statLongest: document.querySelector("#stat-longest"),
  visibleRange: document.querySelector("#visible-range"),
  calendarScroll: document.querySelector("#calendar-scroll"),
  calendar: document.querySelector("#calendar"),
  eventList: document.querySelector("#event-list"),
  fitRange: document.querySelector("#fit-range"),
  todayJump: document.querySelector("#today-jump"),
  dialog: document.querySelector("#event-dialog"),
  dialogClose: document.querySelector("#dialog-close"),
  dialogCategory: document.querySelector("#dialog-category"),
  dialogTitle: document.querySelector("#dialog-title"),
  dialogStart: document.querySelector("#dialog-start"),
  dialogEnd: document.querySelector("#dialog-end"),
  dialogWindow: document.querySelector("#dialog-window"),
  dialogSource: document.querySelector("#dialog-source"),
  dialogDetail: document.querySelector("#dialog-detail"),
};

init();

async function init() {
  bindEvents();
  await loadData();
}

function bindEvents() {
  els.dataSource.addEventListener("change", loadData);
  els.searchInput.addEventListener("input", render);
  els.categoryFilter.addEventListener("change", render);
  els.rangeFilter.addEventListener("change", render);
  els.fitRange.addEventListener("click", () => {
    els.calendarScroll.scrollTo({ left: 0, behavior: "smooth" });
  });
  els.todayJump.addEventListener("click", jumpToToday);
  els.dialogClose.addEventListener("click", () => els.dialog.close());
}

async function loadData() {
  try {
    els.dataMeta.textContent = "正在加载数据...";
    const response = await fetch(els.dataSource.value, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    state.payload = await response.json();
    state.lifecycles = state.payload.lifecycles || [];
    state.tracks = state.payload.tracks || [];
    state.trackMeta = new Map(state.tracks.map((track) => [track.id, track]));
    state.events = normalizeEvents(state.payload.events || []);
    state.categories = [...new Set(state.events.map((event) => event.category))].sort();
    state.categoryColors = new Map(
      state.categories.map((category, index) => [category, COLORS[index % COLORS.length]]),
    );

    renderCategoryFilter();
    renderLegend();
    render();
    els.dataMeta.textContent = `${state.payload.source || "未知来源"} · ${formatDateTime(
      state.payload.generated_at,
    )}`;
  } catch (error) {
    els.dataMeta.textContent = `数据加载失败：${error.message}`;
    els.calendar.innerHTML = '<p class="empty">无法加载 JSON。请从项目根目录启动本地服务后访问页面。</p>';
  }
}

function normalizeEvents(events) {
  return events
    .map((event) => ({
      ...event,
      category: event.category || "Unknown",
      start: new Date(event.start_time),
      end: new Date(event.end_time),
      durationSeconds: Number(event.duration_seconds || 0),
    }))
    .filter((event) => !Number.isNaN(event.start.valueOf()) && !Number.isNaN(event.end.valueOf()))
    .sort((a, b) => a.start - b.start || a.name.localeCompare(b.name));
}

function renderCategoryFilter() {
  els.categoryFilter.innerHTML = '<option value="all">全部分类</option>';
  for (const category of state.categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    els.categoryFilter.append(option);
  }
}

function renderLegend() {
  els.legend.innerHTML = "";
  for (const category of state.categories) {
    const item = document.createElement("div");
    item.className = "legend-item";
    item.innerHTML = `
      <span class="legend-swatch" style="background:${colorFor(category)}"></span>
      <span>${category}</span>
    `;
    els.legend.append(item);
  }
}

function render() {
  state.filteredEvents = filterEvents(state.events);
  renderStats();
  renderCalendar();
  renderEventList();
}

function filterEvents(events) {
  const keyword = els.searchInput.value.trim().toLowerCase();
  const category = els.categoryFilter.value;
  const rangeDays = els.rangeFilter.value;

  let filtered = events.filter((event) => {
    const matchesKeyword =
      !keyword ||
      event.name.toLowerCase().includes(keyword) ||
      event.category.toLowerCase().includes(keyword);
    const matchesCategory = category === "all" || event.category === category;
    return matchesKeyword && matchesCategory;
  });

  if (rangeDays !== "all" && filtered.length) {
    const latestStart = Math.max(...events.map((event) => event.start.getTime()));
    const minTime = latestStart - (Number(rangeDays) - 1) * DAY_MS;
    filtered = filtered.filter((event) => event.end.getTime() >= minTime);
  }

  return filtered;
}

function renderStats() {
  const events = state.filteredEvents;
  els.statEvents.textContent = events.length;

  if (!events.length) {
    els.statDays.textContent = "-";
    els.statCategories.textContent = "-";
    els.statLongest.textContent = "-";
    return;
  }

  const range = getDateRange(events);
  const categoryCount = new Set(events.map((event) => event.category)).size;
  const longest = events.reduce((current, event) =>
    event.durationSeconds > current.durationSeconds ? event : current,
  );

  els.statDays.textContent = daysBetween(range.start, range.end);
  els.statCategories.textContent = categoryCount;
  els.statLongest.textContent = formatDuration(longest.durationSeconds);
}

function renderCalendar() {
  const events = state.filteredEvents;
  if (!events.length) {
    els.visibleRange.textContent = "";
    els.calendar.innerHTML = '<p class="empty">没有符合筛选条件的活动。</p>';
    return;
  }

  const range = getDateRange(events);
  const days = buildDays(range.start, range.end);
  const groupedSections = groupEventsByTrack(events);
  const rowCount = groupedSections.reduce((total, section) => total + section.tracks.length, 0);
  const totalWidth = days.length * cssNumber("--day-width");
  els.visibleRange.textContent = `${formatDate(range.start)} 至 ${formatDate(range.end)}`;
  els.calendar.style.width = `${totalWidth}px`;

  const header = document.createElement("div");
  header.className = "calendar-header";
  header.style.gridTemplateColumns = `repeat(${days.length}, var(--day-width))`;
  for (const day of days) {
    const cell = document.createElement("div");
    cell.className = `day-cell${isWeekend(day) ? " is-weekend" : ""}`;
    cell.textContent = formatDayHeader(day);
    header.append(cell);
  }

  const body = document.createElement("div");
  body.className = "calendar-body";
  body.style.minHeight = `${
    rowCount * cssNumber("--row-height") + groupedSections.length * cssNumber("--section-height")
  }px`;

  const grid = document.createElement("div");
  grid.className = "grid-lines";
  grid.style.gridTemplateColumns = `repeat(${days.length}, var(--day-width))`;
  for (let index = 0; index < days.length; index += 1) {
    const line = document.createElement("div");
    line.className = "grid-line";
    grid.append(line);
  }
  body.append(grid);

  const rangeStart = startOfDay(range.start).getTime();
  for (const section of groupedSections) {
    const sectionTitle = document.createElement("div");
    sectionTitle.className = "lifecycle-section-title";
    sectionTitle.innerHTML = `
      <div class="lifecycle-section-title-content">
        <span>${section.label}</span>
        <strong>${section.tracks.length} 轨 · ${section.eventCount} 项</strong>
      </div>
    `;
    body.append(sectionTitle);

    for (const track of section.tracks) {
      const row = document.createElement("div");
      row.className = "event-row";
      row.innerHTML = `<div class="track-row-label">${track.label}</div>`;

      for (const event of track.events) {
        const left = ((event.start.getTime() - rangeStart) / DAY_MS) * cssNumber("--day-width");
        const width = Math.max(
          ((event.end.getTime() - event.start.getTime()) / DAY_MS) * cssNumber("--day-width"),
          36,
        );
        const visibleWidth = Math.min(width, totalWidth - Math.max(0, left) - 8);
        const showIconOnly = event.image_url && visibleWidth < estimateTextWidth(event.name);
        const bar = document.createElement("button");
        bar.className = `event-bar${showIconOnly ? " is-icon-only" : ""}`;
        bar.style.left = `${Math.max(4, left)}px`;
        bar.style.width = `${visibleWidth}px`;
        bar.style.background = colorFor(event.category);
        bar.title = `${event.name} · ${formatDateTime(event.start)} - ${formatDateTime(event.end)}`;
        bar.addEventListener("click", () => openEventDialog(event));
        bar.innerHTML = `
          ${event.image_url ? `<img src="${event.image_url}" alt="">` : ""}
          ${showIconOnly ? "" : `<span>${event.name}</span>`}
        `;
        row.append(bar);
      }
      body.append(row);
    }
  }

  els.calendar.replaceChildren(header, body);
}

function groupEventsByTrack(events) {
  const sections = new Map(
    state.lifecycles.map((lifecycle) => [
      lifecycle.id,
      { ...lifecycle, tracks: new Map(), eventCount: 0 },
    ]),
  );

  for (const event of events) {
    const section = sections.get(event.lifecycle);
    if (!section || !event.track) {
      continue;
    }

    const trackId = event.track;
    const trackMeta = state.trackMeta.get(trackId);
    if (!section.tracks.has(trackId)) {
      section.tracks.set(trackId, {
        id: trackId,
        label: trackMeta?.label || event.track_label || trackId,
        groupLabel: trackMeta?.group_label || event.track_group_label || "",
        sort: Number(trackMeta?.sort ?? event.track_sort ?? 9999),
        events: [],
      });
    }
    section.tracks.get(trackId).events.push(event);
    section.eventCount += 1;
  }

  return state.lifecycles
    .map((lifecycle) => sections.get(lifecycle.id))
    .filter((section) => section.eventCount)
    .map((section) => ({
      ...section,
      tracks: [...section.tracks.values()]
        .map((track) => ({ ...track, events: track.events.sort((a, b) => a.start - b.start) }))
        .sort((a, b) => a.sort - b.sort || a.label.localeCompare(b.label)),
    }));
}

function estimateTextWidth(text) {
  return text.length * 8 + 58;
}

function renderEventList() {
  const events = state.filteredEvents;
  els.eventList.innerHTML = "";

  if (!events.length) {
    els.eventList.innerHTML = '<p class="empty">没有符合筛选条件的活动。</p>';
    return;
  }

  for (const event of events) {
    const item = document.createElement("article");
    item.className = "event-item";
    item.innerHTML = `
      <div>
        <h4>${event.name}</h4>
        <p>${formatDateTime(event.start)} - ${formatDateTime(event.end)} · ${event.track_label || ""}</p>
      </div>
      <span class="badge" style="background:${colorFor(event.category)}">${event.category}</span>
    `;
    item.addEventListener("click", () => openEventDialog(event));
    els.eventList.append(item);
  }
}

function openEventDialog(event) {
  els.dialogCategory.textContent = event.category;
  els.dialogTitle.textContent = event.name;
  els.dialogStart.textContent = formatDateTime(event.start);
  els.dialogEnd.textContent = formatDateTime(event.end);
  els.dialogWindow.textContent = `${formatDuration(event.durationSeconds)} · 页面展示 ${
    event.raw?.display_start || "-"
  } - ${event.raw?.display_end || "-"}`;
  els.dialogSource.href = event.source_url;

  if (event.detail_url) {
    els.dialogDetail.href = event.detail_url;
    els.dialogDetail.classList.remove("is-hidden");
  } else {
    els.dialogDetail.classList.add("is-hidden");
  }

  els.dialog.showModal();
}

function jumpToToday() {
  const events = state.filteredEvents;
  if (!events.length) {
    return;
  }

  const range = getDateRange(events);
  const today = startOfDay(new Date());
  const left = ((today.getTime() - startOfDay(range.start).getTime()) / DAY_MS) * cssNumber("--day-width");
  els.calendarScroll.scrollTo({ left: Math.max(0, left - 240), behavior: "smooth" });
}

function getDateRange(events) {
  const min = new Date(Math.min(...events.map((event) => event.start.getTime())));
  const max = new Date(Math.max(...events.map((event) => event.end.getTime())));
  return {
    start: startOfDay(min),
    end: endOfDay(max),
  };
}

function buildDays(start, end) {
  const days = [];
  const cursor = startOfDay(start);
  const last = startOfDay(end);
  while (cursor <= last) {
    days.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

function startOfDay(date) {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  return next;
}

function endOfDay(date) {
  const next = new Date(date);
  next.setHours(23, 59, 59, 999);
  return next;
}

function daysBetween(start, end) {
  return Math.max(1, Math.ceil((endOfDay(end) - startOfDay(start)) / DAY_MS));
}

function isWeekend(date) {
  const day = date.getDay();
  return day === 0 || day === 6;
}

function colorFor(category) {
  return state.categoryColors.get(category) || COLORS[0];
}

function cssNumber(variableName) {
  return Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue(variableName));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  }).format(value);
}

function formatDayHeader(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  }).format(value);
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return "-";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "-";
  }
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days > 0) {
    return `${days}天${hours}小时`;
  }
  return `${Math.max(1, hours)}小时`;
}
