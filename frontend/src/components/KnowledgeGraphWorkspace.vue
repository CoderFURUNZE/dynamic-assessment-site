<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";

type GraphKp = {
  id: number;
  code: string;
  title: string;
  description: string;
  chapter?: string;
  knowledge_tag?: string;
  ability_tag?: string;
  literacy_tag?: string;
  importance?: number;
  difficulty?: number;
  pos_x?: number | null;
  pos_y?: number | null;
};

type GraphEdge = {
  prereq_id: number;
  next_id: number;
  relation_type: string;
};

type ChapterEdge = {
  id: string;
  source_chapter: string;
  target_chapter: string;
  relation_type: string;
};

type OverlayNode = {
  kp_id: number;
  mastery: number;
  status: string;
  recommended?: boolean;
  blocked_reason?: string | null;
  knowledge_enabled?: boolean;
  ability_enabled?: boolean;
  literacy_enabled?: boolean;
  knowledge_status?: string;
  ability_status?: string;
  literacy_status?: string;
  knowledge_label?: string;
  ability_labels?: string[];
  literacy_labels?: string[];
  evidence?: Record<string, any>;
};

type RelationNode = {
  id: number;
  code: string;
  title: string;
};

type NodeDetail = {
  kp: GraphKp;
  overlay?: OverlayNode | null;
  prerequisites: RelationNode[];
  downstream: RelationNode[];
  related: RelationNode[];
  resource_list: Array<{ id: number; kp_id: number; type: string; title: string; url: string }>;
  task_list: Array<{ id: number; kp_id: number; type: string; title: string; description: string; link_url: string; sort_order: number }>;
  practice_list: Array<{ id: number; kp_id: number; type: string; prompt: string; difficulty: number }>;
  quiz_or_exam_list: Array<{ kind: string; id: number; title: string; item_count: number; pass_accuracy?: number | null; description?: string; link_url?: string }>;
};

type CategoryNode = {
  key: string;
  title: string;
  total: number;
};

type Point = { x: number; y: number };

type DragNode = {
  type: "kp" | "category";
  id: number | string;
  origin: Point;
};

type StudentWorkspaceLayout = {
  kpPositions: Record<number, Point>;
  categoryPositions: Record<string, Point>;
};

type StudentWorkspaceViewState = {
  canvasScale: number;
  panX: number;
  panY: number;
  activeChapter: string;
  search: string;
  drawerOpen: boolean;
  sidebarOpen: boolean;
  showAllKps: boolean;
  selectedType: "kp" | "category";
  selectedId: number | null;
  selectedCategory: string | null;
};

const CANVAS_WIDTH = 60000;
const CANVAS_HEIGHT = 40000;
const INITIAL_CENTER_X = 30000;
const INITIAL_CENTER_Y = 20000;
const DEFAULT_CANVAS_SCALE = 0.7;
const MIN_CANVAS_SCALE = 0.5;
const MAX_CANVAS_SCALE = 4;
const SCALE_STEP = 0.2;

const props = defineProps<{
  subject: string;
  grade: string;
  currentKpId?: number | null;
  recommendedKpId?: number | null;
  highlightedKpIds?: number[] | null;
}>();

const emit = defineEmits<{
  (e: "select-kp", id: number): void;
  (e: "open-content", id: number): void;
  (
    e: "state-change",
    payload: {
      kpCount: number;
      categoryCount: number;
      filteredCount: number;
      selectedType: "kp" | "category";
      selectedKpId: number | null;
      selectedCategory: string | null;
    },
  ): void;
}>();

const loading = ref(false);
const search = ref("");
const activeChapter = ref("全部");
const kps = ref<GraphKp[]>([]);
const edges = ref<GraphEdge[]>([]);
const overlay = ref<OverlayNode[]>([]);
const selectedType = ref<"kp" | "category">("kp");
const selectedId = ref<number | null>(null);
const selectedCategory = ref<string | null>(null);
const showAllKps = ref(false);
const nodeDetail = ref<NodeDetail | null>(null);
const drawerOpen = ref(true);
const sidebarOpen = ref(true);
const canvasScale = ref(DEFAULT_CANVAS_SCALE);
const panX = ref(0);
const panY = ref(0);
const stageRef = ref<HTMLElement | null>(null);
const draggingCanvas = ref(false);
const draggingNode = ref<DragNode | null>(null);
const dragStartX = ref(0);
const dragStartY = ref(0);
const dragOriginX = ref(0);
const dragOriginY = ref(0);
const kpPositions = ref<Record<number, Point>>({});
const categoryPositions = ref<Record<string, Point>>({});
const mutingLayoutPersist = ref(false);
const layoutRestored = ref(false);
const useLegacyFallbackLayout = ref(false);

const overlayMap = computed(() => new Map(overlay.value.map((item) => [item.kp_id, item])));
const effectiveOverlayMap = computed(() => {
  const map = new Map(overlayMap.value);
  if (props.recommendedKpId) {
    const current = map.get(props.recommendedKpId);
    map.set(props.recommendedKpId, {
      kp_id: props.recommendedKpId,
      mastery: current?.mastery ?? 0,
      status: current?.status ?? "not_started",
      recommended: true,
      blocked_reason: current?.blocked_reason ?? null,
    });
  }
  return map;
});

function splitLabels(value?: string | null) {
  return String(value || "")
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildLabelColorMap(labels: string[], palette: string[]) {
  const map = new Map<string, string>();
  labels.forEach((label, index) => {
    map.set(label, palette[index % palette.length]);
  });
  return map;
}

const abilityColorMap = computed(() =>
  buildLabelColorMap(
    Array.from(new Set(overlay.value.flatMap((item) => item.ability_labels ?? []).concat(kps.value.flatMap((kp) => splitLabels(kp.ability_tag))))),
    ["#f0b429", "#5bb98c", "#4f7fe7", "#e28a49", "#7d72e9", "#39a0a4"],
  ),
);

const literacyColorMap = computed(() =>
  buildLabelColorMap(
    Array.from(new Set(overlay.value.flatMap((item) => item.literacy_labels ?? []).concat(kps.value.flatMap((kp) => splitLabels(kp.literacy_tag))))),
    ["#2f6fed", "#2ea96b", "#e0a128", "#8b7cf6", "#2f9ab6", "#de7465"],
  ),
);

const chapterSummary = computed(() => {
  const bucket = new Map<string, number>();
  for (const kp of kps.value) {
    const key = kp.chapter || "未分章";
    bucket.set(key, (bucket.get(key) ?? 0) + 1);
  }
  return Array.from(bucket.entries()).map(([chapter, total]) => ({ chapter, total }));
});

const categoryNodes = computed<CategoryNode[]>(() => chapterSummary.value.map((item) => ({ key: item.chapter, title: item.chapter, total: item.total })));

const filteredKps = computed(() => {
  const kw = search.value.trim().toLowerCase();
  return kps.value.filter((kp) => {
    const chapterOk = activeChapter.value === "全部" || (kp.chapter || "未分章") === activeChapter.value;
    if (!chapterOk) return false;
    if (!kw) return true;
    return `${kp.code} ${kp.title} ${kp.description} ${kp.chapter || ""}`.toLowerCase().includes(kw);
  });
});

const visibleKps = computed(() => {
  if (showAllKps.value) return filteredKps.value;
  const activeChapterKey =
    selectedType.value === "category"
      ? selectedCategory.value
      : (selectedKp.value?.chapter || selectedCategory.value || null);
  if (!activeChapterKey) return [] as GraphKp[];
  return filteredKps.value.filter((kp) => (kp.chapter || "未分章") === activeChapterKey);
});

const treeNodes = computed(() => {
  const kw = search.value.trim().toLowerCase();
  return categoryNodes.value
    .map((chapterNode) => {
      const children = kps.value.filter((kp) => (kp.chapter || "未分章") === chapterNode.key).filter((kp) => {
        if (!kw) return true;
        return `${kp.code} ${kp.title} ${kp.description}`.toLowerCase().includes(kw) || chapterNode.title.toLowerCase().includes(kw);
      });
      return {
        ...chapterNode,
        children,
      };
    })
    .filter((item) => item.children.length > 0 || item.title.toLowerCase().includes(kw));
});

const stageStats = computed(() => {
  let mastered = 0;
  let learning = 0;
  let risk = 0;
  let idle = 0;
  for (const kp of visibleKps.value) {
    const status = overlayMap.value.get(kp.id)?.status ?? "not_started";
    if (status === "mastered") mastered += 1;
    else if (status === "learning") learning += 1;
    else if (status === "risk") risk += 1;
    else idle += 1;
  }
  return { mastered, learning, risk, idle };
});

const hasGraphData = computed(() => kps.value.length > 0);

const defaultCategoryPositions = computed<Record<string, Point>>(() => {
  const entries: Record<string, Point> = {};
  const list = categoryNodes.value;
  const total = Math.max(list.length, 1);
  const spread = Math.min(480, Math.max(220, (total - 1) * 170));
  const startX = INITIAL_CENTER_X - spread / 2;
  const endX = INITIAL_CENTER_X + spread / 2;
  const step = total === 1 ? 0 : spread / (total - 1);
  list.forEach((item, index) => {
    entries[item.key] = {
      x: startX + step * index,
      y: INITIAL_CENTER_Y - 360 + (index % 2 === 0 ? 0 : 26),
    };
  });
  return entries;
});

const defaultKpPositions = computed<Record<number, Point>>(() => {
  const entries: Record<number, Point> = {};
  const groups = new Map<string, GraphKp[]>();
  for (const kp of visibleKps.value) {
    const key = kp.chapter || "未分章";
    const arr = groups.get(key) ?? [];
    arr.push(kp);
    groups.set(key, arr);
  }

  for (const [chapter, items] of groups.entries()) {
    const anchor = categoryPositions.value[chapter] ?? defaultCategoryPositions.value[chapter] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
    const ordered = [...items].sort((a, b) => String(a.code || "").localeCompare(String(b.code || ""), "zh-Hans-CN"));
    const columns = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(ordered.length))));
    const gapX = 220;
    const gapY = 170;
    const startX = anchor.x - ((columns - 1) * gapX) / 2;
    ordered.forEach((kp, index) => {
      const col = index % columns;
      const row = Math.floor(index / columns);
      entries[kp.id] = {
        x: startX + col * gapX + (row % 2 === 0 ? 0 : 18),
        y: anchor.y + 250 + row * gapY,
      };
    });
  }

  return entries;
});

function isLegacyCoordinateLayout(rows: GraphKp[]) {
  const withPos = rows.filter((kp) => kp.pos_x != null && kp.pos_y != null);
  if (withPos.length === 0) return false;
  const nearOriginCount = withPos.filter((kp) => Number(kp.pos_x) < 12000 && Number(kp.pos_y) < 12000).length;
  return nearOriginCount / withPos.length >= 0.5;
}

function normalizePersistedKpPositions(rows: GraphKp[]) {
  const entries: Record<number, Point> = {};
  const withPos = rows.filter((kp) => kp.id && kp.pos_x != null && kp.pos_y != null);
  if (withPos.length === 0) return entries;

  const legacyRows = withPos.filter((kp) => Number(kp.pos_x) < 12000 && Number(kp.pos_y) < 12000);
  const useLegacy = isLegacyCoordinateLayout(rows);
  useLegacyFallbackLayout.value = useLegacy;

  if (!useLegacy) {
    for (const kp of withPos) {
      entries[kp.id] = { x: Number(kp.pos_x), y: Number(kp.pos_y) };
    }
    return entries;
  }

  const minX = Math.min(...legacyRows.map((kp) => Number(kp.pos_x)));
  const maxX = Math.max(...legacyRows.map((kp) => Number(kp.pos_x)));
  const minY = Math.min(...legacyRows.map((kp) => Number(kp.pos_y)));
  const maxY = Math.max(...legacyRows.map((kp) => Number(kp.pos_y)));
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const scale = 2.2;

  for (const kp of withPos) {
    const rawX = Number(kp.pos_x);
    const rawY = Number(kp.pos_y);
    const legacyLike = rawX < 12000 && rawY < 12000;
    if (!legacyLike) {
      entries[kp.id] = { x: rawX, y: rawY };
      continue;
    }
    const mappedX = INITIAL_CENTER_X + (rawX - centerX) * scale;
    const mappedY = (INITIAL_CENTER_Y + 180) + (rawY - centerY) * scale;
    entries[kp.id] = {
      x: Math.max(96, Math.min(CANVAS_WIDTH - 96, mappedX)),
      y: Math.max(96, Math.min(CANVAS_HEIGHT - 96, mappedY)),
    };
  }
  return entries;
}

const visibleEdges = computed(() => {
  const ids = new Set(visibleKps.value.map((kp) => kp.id));
  return edges.value.filter((edge) => ids.has(edge.prereq_id) && ids.has(edge.next_id));
});

const visibleChapterEdges = computed<ChapterEdge[]>(() => {
  const seen = new Set<string>();
  const list: ChapterEdge[] = [];
  for (const edge of visibleEdges.value) {
    const source = kps.value.find((item) => item.id === edge.prereq_id)?.chapter || "未分章";
    const target = kps.value.find((item) => item.id === edge.next_id)?.chapter || "未分章";
    if (source === target) continue;
    const key = `${source}->${target}:${edge.relation_type || "prerequisite"}`;
    if (seen.has(key)) continue;
    seen.add(key);
    list.push({
      id: key,
      source_chapter: source,
      target_chapter: target,
      relation_type: edge.relation_type || "prerequisite",
    });
  }
  return list;
});

const selectedKp = computed(() => {
  if (selectedType.value !== "kp") return null;
  return kps.value.find((kp) => kp.id === selectedId.value) ?? null;
});

const selectedCategoryNode = computed(() => {
  if (selectedType.value !== "category") return null;
  return categoryNodes.value.find((item) => item.key === selectedCategory.value) ?? null;
});

const activeOverlay = computed(() => {
  if (nodeDetail.value?.overlay) return nodeDetail.value.overlay;
  if (!selectedKp.value) return null;
  return effectiveOverlayMap.value.get(selectedKp.value.id) ?? null;
});

const selectedCategoryOverview = computed(() => {
  if (!selectedCategoryNode.value) return null;
  const chapter = selectedCategoryNode.value.key;
  const items = kps.value.filter((kp) => (kp.chapter || "未分章") === chapter);
  const mastered = items.filter((kp) => effectiveOverlayMap.value.get(kp.id)?.status === "mastered").length;
  const learning = items.filter((kp) => effectiveOverlayMap.value.get(kp.id)?.status === "learning").length;
  const risk = items.filter((kp) => effectiveOverlayMap.value.get(kp.id)?.status === "risk").length;
  const recommended = items.find((kp) => effectiveOverlayMap.value.get(kp.id)?.recommended);
  return {
    total: items.length,
    mastered,
    learning,
    risk,
    idle: Math.max(0, items.length - mastered - learning - risk),
    items,
    recommended,
  };
});

function categoryPoint(key: string) {
  return categoryPositions.value[key] ?? defaultCategoryPositions.value[key] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
}

function kpPoint(id: number) {
  return kpPositions.value[id] ?? defaultKpPositions.value[id] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y };
}

function edgeLine(edge: GraphEdge) {
  const from = kpPoint(edge.prereq_id);
  const to = kpPoint(edge.next_id);
  const fromKp = kps.value.find((item) => item.id === edge.prereq_id);
  const toKp = kps.value.find((item) => item.id === edge.next_id);
  const fromRadius = fromKp ? nodeRadius(fromKp) + 8 : 72;
  const toRadius = toKp ? nodeRadius(toKp) + 8 : 72;
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  return {
    x1: from.x + ux * fromRadius,
    y1: from.y + uy * fromRadius,
    x2: to.x - ux * toRadius,
    y2: to.y - uy * toRadius,
  };
}

function categoryKpLine(kp: GraphKp) {
  const from = categoryPoint(kp.chapter || "未分章");
  const to = kpPoint(kp.id);
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  const categoryOut = 58;
  const kpOut = nodeRadius(kp) + 12;
  return {
    x1: from.x + ux * categoryOut,
    y1: from.y + uy * categoryOut,
    x2: to.x - ux * kpOut,
    y2: to.y - uy * kpOut,
  };
}

function centerOnPoint(point: Point) {
  if (!stageRef.value) return;
  const centerX = stageRef.value.clientWidth / 2;
  const centerY = stageRef.value.clientHeight / 2;
  panX.value = centerX - point.x * canvasScale.value;
  panY.value = centerY - point.y * canvasScale.value;
}

function studentActorKey() {
  return localStorage.getItem("da_last_user") || "guest";
}

function studentLayoutStorageKey() {
  if (!props.subject) return "";
  return `da_student_graph_layout_v4_${studentActorKey()}_${props.subject}_${props.grade}`;
}

function studentViewStateStorageKey() {
  if (!props.subject) return "";
  return `da_student_graph_view_v4_${studentActorKey()}_${props.subject}_${props.grade}`;
}

function teacherCategoryPositionStorageKey() {
  if (!props.subject) return "";
  return `da_teacher_category_pos_v2_${props.subject}_${props.grade}`;
}

function persistStudentLayout() {
  return;
}

function persistStudentViewState() {
  if (mutingLayoutPersist.value) return;
  const key = studentViewStateStorageKey();
  if (!key) return;
  const payload: StudentWorkspaceViewState = {
    canvasScale: canvasScale.value,
    panX: panX.value,
    panY: panY.value,
    activeChapter: activeChapter.value,
    search: search.value,
    drawerOpen: drawerOpen.value,
    sidebarOpen: sidebarOpen.value,
    selectedType: selectedType.value,
    selectedId: selectedId.value,
    selectedCategory: selectedCategory.value,
    showAllKps: showAllKps.value,
  };
  localStorage.setItem(key, JSON.stringify(payload));
}

function restoreStudentLayout() {
  return false;
}

function restoreTeacherCategoryPositions() {
  const key = teacherCategoryPositionStorageKey();
  if (!key) return;
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : {};
    if (!parsed || typeof parsed !== "object") return;
    const next: Record<string, Point> = {};
    for (const [key, point] of Object.entries(parsed)) {
      const x = Number((point as any)?.x);
      const y = Number((point as any)?.y);
      if (Number.isFinite(x) && Number.isFinite(y)) {
        next[key] = { x, y };
      }
    }
    categoryPositions.value = next;
  } catch {
    categoryPositions.value = {};
  }
}

function restoreStudentViewState() {
  const key = studentViewStateStorageKey();
  if (!key) return false;
  const raw = localStorage.getItem(key);
  if (!raw) return false;
  try {
    const parsed = JSON.parse(raw) as Partial<StudentWorkspaceViewState>;
    mutingLayoutPersist.value = true;
    const nextScale = Number(parsed.canvasScale ?? DEFAULT_CANVAS_SCALE);
    const nextPanX = Number(parsed.panX ?? 0);
    const nextPanY = Number(parsed.panY ?? 0);
    canvasScale.value = Math.min(MAX_CANVAS_SCALE, Math.max(MIN_CANVAS_SCALE, nextScale));
    panX.value = Number.isFinite(nextPanX) ? nextPanX : 0;
    panY.value = Number.isFinite(nextPanY) ? nextPanY : 0;
    activeChapter.value = typeof parsed.activeChapter === "string" && parsed.activeChapter ? parsed.activeChapter : "全部";
    search.value = typeof parsed.search === "string" ? parsed.search : "";
    drawerOpen.value = true;
    sidebarOpen.value = true;
    selectedType.value = parsed.selectedType === "category" ? "category" : "kp";
    selectedId.value = Number.isFinite(Number(parsed.selectedId)) ? Number(parsed.selectedId) : null;
    selectedCategory.value = typeof parsed.selectedCategory === "string" ? parsed.selectedCategory : null;
    showAllKps.value = parsed.showAllKps === true;
    return true;
  } catch {
    return false;
  } finally {
    mutingLayoutPersist.value = false;
  }
}

function normalizeStudentSelectionState() {
  let changed = false;
  const chapterKeySet = new Set(categoryNodes.value.map((item) => item.key));
  const firstChapter = categoryNodes.value[0]?.key || null;
  const kpMap = new Map(kps.value.map((kp) => [kp.id, kp]));
  const currentSelectedKp = selectedId.value != null ? kpMap.get(selectedId.value) ?? null : null;

  if (currentSelectedKp) {
    selectedType.value = "kp";
    selectedCategory.value = currentSelectedKp.chapter || "未分章";
    if (!chapterKeySet.has(selectedCategory.value)) {
      selectedCategory.value = firstChapter;
      changed = true;
    }
    if (selectedCategory.value) activeChapter.value = selectedCategory.value;
  } else {
    if (selectedId.value != null) changed = true;
    selectedId.value = null;
    if (selectedType.value === "kp") {
      selectedType.value = "category";
      changed = true;
    }
  }

  if (!selectedCategory.value && activeChapter.value !== "全部" && chapterKeySet.has(activeChapter.value)) {
    selectedCategory.value = activeChapter.value;
    changed = true;
  }

  if (selectedCategory.value && !chapterKeySet.has(selectedCategory.value)) {
    selectedCategory.value = null;
    changed = true;
  }

  if (activeChapter.value !== "全部" && !chapterKeySet.has(activeChapter.value)) {
    activeChapter.value = "全部";
    changed = true;
  }

  if (!showAllKps.value && !selectedId.value && !selectedCategory.value) {
    selectedType.value = "category";
    selectedCategory.value = firstChapter;
    activeChapter.value = firstChapter || "全部";
    changed = true;
  }
  return changed;
}

function syncCategoryPositions() {
  const next: Record<string, Point> = {};
  for (const item of categoryNodes.value) {
    next[item.key] = categoryPositions.value[item.key] ?? defaultCategoryPositions.value[item.key];
  }
  categoryPositions.value = next;
}

function syncKpPositions() {
  const next: Record<number, Point> = {};
  for (const kp of kps.value) {
    if (kpPositions.value[kp.id]) {
      next[kp.id] = kpPositions.value[kp.id];
      continue;
    }
    next[kp.id] = defaultKpPositions.value[kp.id];
  }
  kpPositions.value = next;
}

function nodeLabel(status?: string) {
  if (status === "mastered" || status === "achieved") return "已达成";
  if (status === "learning" || status === "in_progress") return "进行中";
  if (status === "risk") return "风险";
  return "未开始";
}

function isRecommended(kpId: number) {
  return effectiveOverlayMap.value.get(kpId)?.recommended === true;
}

const highlightedKpSet = computed(() => new Set((props.highlightedKpIds ?? []).filter((id) => Number.isFinite(Number(id))).map(Number)));

function isPathNode(kpId: number) {
  return highlightedKpSet.value.has(kpId);
}

function isPathEdge(edge: GraphEdge) {
  return highlightedKpSet.value.has(edge.prereq_id) && highlightedKpSet.value.has(edge.next_id);
}

function edgeStroke(edge: GraphEdge) {
  if (isPathEdge(edge)) return "#5a8ef0";
  if (edge.relation_type === "support") return "#46a57b";
  if (edge.relation_type === "contains") return "#db9d37";
  if (edge.relation_type === "related") return "rgba(74,120,213,0.6)";
  return "rgba(100,116,139,0.5)";
}

function edgeDasharray(edge: GraphEdge) {
  if (isPathEdge(edge)) return "8 5";
  if (edge.relation_type === "support") return "10 6";
  if (edge.relation_type === "contains") return "2 6";
  return undefined;
}

function edgeWidth(edge: GraphEdge) {
  if (isPathEdge(edge)) return 2.8;
  if (edge.relation_type === "contains") return 2.2;
  if (edge.relation_type === "support") return 2.1;
  return 1.6;
}

function edgeMarker(edge: GraphEdge) {
  if (edge.relation_type === "related") return undefined;
  if (isPathEdge(edge)) return "url(#student-edge-arrow-path)";
  if (edge.relation_type === "support") return "url(#student-edge-arrow-triangle)";
  if (edge.relation_type === "contains") return "url(#student-edge-arrow-open)";
  return "url(#student-edge-arrow)";
}

function chapterEdgeStroke(edge: ChapterEdge) {
  if (edge.relation_type === "related") return "rgba(74,120,213,0.42)";
  if (edge.relation_type === "support") return "rgba(70,165,123,0.5)";
  return "rgba(75,94,130,0.52)";
}

function nodeRadius(kp: GraphKp) {
  const base = 62 + Math.round((kp.importance ?? 0.5) * 16);
  if (kp.id === selectedKp.value?.id) return base + 10;
  if (isRecommended(kp.id)) return base + 6;
  return base;
}

function ringColor(level: "knowledge" | "ability" | "literacy", status?: string, labels?: string[]) {
  if (level === "ability") {
    const label = labels?.[0];
    if (label && abilityColorMap.value.has(label)) return abilityColorMap.value.get(label) as string;
  }
  if (level === "literacy") {
    const label = labels?.[0];
    if (label && literacyColorMap.value.has(label)) return literacyColorMap.value.get(label) as string;
  }
  const palette = {
    knowledge: { achieved: "#2ea96b", in_progress: "#86cfa8", not_started: "#d7e7dd" },
    ability: { achieved: "#f0b429", in_progress: "#f6d67a", not_started: "#efe4bf" },
    literacy: { achieved: "#2f6fed", in_progress: "#8db0f6", not_started: "#d7e3fb" },
  };
  const key = status === "achieved" || status === "in_progress" ? status : "not_started";
  return palette[level][key];
}

async function openResource(item: { id: number; kp_id: number; url: string }, action: "visit" | "download" = "visit") {
  try {
    await api.post("/content/resource/visit", {
      kp_id: item.kp_id,
      resource_id: item.id,
      action,
    });
  } catch {
    // ignore tracking failure
  }
  window.open(item.url, "_blank", "noopener,noreferrer");
}

function metricPercent(value?: number | null) {
  return Math.round((value ?? 0) * 100);
}

function emitState() {
  emit("state-change", {
    kpCount: kps.value.length,
    categoryCount: categoryNodes.value.length,
    filteredCount: visibleKps.value.length,
    selectedType: selectedType.value,
    selectedKpId: selectedType.value === "kp" ? selectedId.value : null,
    selectedCategory: selectedType.value === "category" ? selectedCategory.value : null,
  });
}

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const res = await api.get(`/graph/map?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
    kps.value = res.data.base?.kps ?? [];
    edges.value = res.data.base?.edges ?? [];
    overlay.value = res.data.overlay ?? [];

    const normalizedPersisted = normalizePersistedKpPositions(kps.value);

    const restoredView = restoreStudentViewState();
    layoutRestored.value = restoredView;
    kpPositions.value = normalizedPersisted;
    restoreTeacherCategoryPositions();

    syncCategoryPositions();
    syncKpPositions();
    const valid = props.currentKpId && kps.value.some((item) => item.id === props.currentKpId);
    if (valid) {
      selectedType.value = "kp";
      selectedId.value = props.currentKpId ?? null;
      selectedCategory.value = kps.value.find((item) => item.id === props.currentKpId)?.chapter || null;
    }
    const normalizedChanged = normalizeStudentSelectionState();
    if (normalizedChanged) {
      layoutRestored.value = false;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识图谱失败");
  } finally {
    loading.value = false;
  }
}

function applyInitialCenterAfterLoad() {
  if (layoutRestored.value) return;
  if (selectedId.value) {
    centerOnPoint(kpPoint(selectedId.value));
  } else if (selectedCategory.value) {
    centerOnPoint(categoryPoint(selectedCategory.value));
  }
}

watch(
  () => [props.subject, props.grade],
  async () => {
    await load();
    applyInitialCenterAfterLoad();
  },
  { immediate: true }
);

watch(
  () => props.currentKpId,
  (value, oldValue) => {
    if (!value || value === oldValue) return;
    if (layoutRestored.value) return;
    selectedType.value = "kp";
    selectedId.value = value;
    selectedCategory.value = null;
    centerOnPoint(kpPoint(value));
  }
);

async function loadNodeDetail(id: number | null) {
  if (!id) {
    nodeDetail.value = null;
    return;
  }
  try {
    const res = await api.get(`/graph/node/${id}`);
    nodeDetail.value = res.data;
  } catch (e: any) {
    nodeDetail.value = null;
    ElMessage.error(e?.response?.data?.detail ?? "加载节点详情失败");
  }
}

function selectKp(id: number) {
  showAllKps.value = false;
  selectedType.value = "kp";
  selectedId.value = id;
  selectedCategory.value = selectedKp.value?.chapter || kps.value.find((item) => item.id === id)?.chapter || null;
  drawerOpen.value = true;
  emit("select-kp", id);
  centerOnPoint(kpPoint(id));
}

function openContentFromSelected() {
  if (!selectedKp.value) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  const blockedReason = activeOverlay.value?.blocked_reason;
  if (blockedReason) {
    ElMessage.warning(blockedReason);
    return;
  }
  emit("open-content", selectedKp.value.id);
}

function selectCategory(chapter: string) {
  showAllKps.value = false;
  selectedType.value = "category";
  selectedCategory.value = chapter;
  selectedId.value = null;
  nodeDetail.value = null;
  activeChapter.value = chapter;
  drawerOpen.value = true;
  centerOnPoint(categoryPoint(chapter));
}

function toggleAllKps() {
  showAllKps.value = !showAllKps.value;
  if (showAllKps.value) {
    activeChapter.value = "全部";
  }
}

function zoomIn() {
  canvasScale.value = Math.min(MAX_CANVAS_SCALE, Number((canvasScale.value + SCALE_STEP).toFixed(2)));
}

function zoomOut() {
  canvasScale.value = Math.max(MIN_CANVAS_SCALE, Number((canvasScale.value - SCALE_STEP).toFixed(2)));
}

function resetViewport() {
  canvasScale.value = DEFAULT_CANVAS_SCALE;
  activeChapter.value = "全部";
  search.value = "";
  syncCategoryPositions();
  syncKpPositions();
  nextTick(() => {
    if (selectedType.value === "kp" && selectedId.value) {
      centerOnPoint(kpPoint(selectedId.value));
      return;
    }
    if (selectedType.value === "category" && selectedCategory.value) {
      centerOnPoint(categoryPoint(selectedCategory.value));
      return;
    }
    if (props.currentKpId && kps.value.some((item) => item.id === props.currentKpId)) {
      centerOnPoint(kpPoint(props.currentKpId));
      return;
    }
    centerOnPoint({ x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y });
  });
}

function onStageWheel(event: WheelEvent) {
  if (!stageRef.value) return;
  event.preventDefault();
  const stageRect = stageRef.value.getBoundingClientRect();
  if (event.ctrlKey || event.metaKey || event.altKey || event.deltaZ !== 0) {
    const pointerX = event.clientX - stageRect.left;
    const pointerY = event.clientY - stageRect.top;
    const worldX = (pointerX - panX.value) / canvasScale.value;
    const worldY = (pointerY - panY.value) / canvasScale.value;
    const scaleFactor = Math.exp(-event.deltaY * 0.002);
    const nextScale = Math.min(MAX_CANVAS_SCALE, Math.max(MIN_CANVAS_SCALE, Number((canvasScale.value * scaleFactor).toFixed(4))));
    canvasScale.value = nextScale;
    panX.value = pointerX - worldX * nextScale;
    panY.value = pointerY - worldY * nextScale;
    return;
  }
  panX.value -= event.deltaX;
  panY.value -= event.deltaY;
}

function onStageMouseDown(event: MouseEvent) {
  const target = event.target as HTMLElement | null;
  if (target?.closest(".workspace-node") || target?.closest(".workspace-category-node")) return;
  draggingCanvas.value = true;
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
  dragOriginX.value = panX.value;
  dragOriginY.value = panY.value;
}

function onNodeMouseDown(event: MouseEvent, type: "kp" | "category", id: number | string) {
  event.stopPropagation();
}

function onWindowMouseMove(event: MouseEvent) {
  if (!draggingCanvas.value) return;
  panX.value = dragOriginX.value + (event.clientX - dragStartX.value);
  panY.value = dragOriginY.value + (event.clientY - dragStartY.value);
}

function stopDragging() {
  draggingCanvas.value = false;
  draggingNode.value = null;
}

watch(
  [kps, categoryNodes, visibleKps, selectedType, selectedId, selectedCategory],
  () => {
    emitState();
  },
  { immediate: true },
);

watch(selectedId, (value) => {
  if (selectedType.value === "kp") {
    loadNodeDetail(value ?? null);
  }
});

watch(visibleKps, () => {
  syncCategoryPositions();
  syncKpPositions();
  normalizeStudentSelectionState();
});

watch(
  [canvasScale, panX, panY, activeChapter, search, drawerOpen, sidebarOpen, selectedType, selectedId, selectedCategory, showAllKps],
  () => {
    persistStudentViewState();
  },
);

window.addEventListener("mousemove", onWindowMouseMove);
window.addEventListener("mouseup", stopDragging);

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", stopDragging);
});
</script>

<template>
  <div class="workspace-shell" v-loading="loading">
    <div class="workspace-header">
      <div class="workspace-heading">
        <h1 class="workspace-title">知识图谱</h1>
        <p class="workspace-subtitle">左侧找分类，中间看图谱，右侧看内容。</p>
      </div>
      <div class="workspace-controls">
        <el-input v-model="search" placeholder="搜索知识点" clearable class="workspace-search" />
        <button class="workspace-btn" @click="resetViewport">重置画布</button>
      </div>
    </div>

    <div class="workspace-guide">
      <span>图谱说明</span>
      <HoverTip content="先在左边找分类，再点中间节点，最后在右边看资源和前后关系。" />
    </div>

    <div class="workspace-content">
      <aside class="workspace-sidebar">
        <div class="workspace-tree">
          <div v-if="treeNodes.length === 0" class="workspace-tree__empty">
            <strong>左边现在没有可选内容</strong>
            <span>可以先清空搜索词，或换一门课程再查看。</span>
          </div>
          <div v-for="item in treeNodes" :key="item.key" class="workspace-tree__group">
            <div class="workspace-tree__summary" :class="{ active: activeChapter === item.key }" @click="selectCategory(item.key)">
              <span>{{ item.title }}</span>
              <span class="workspace-tree__count">{{ item.children.length }}</span>
            </div>
            <div class="workspace-tree__children" v-if="activeChapter === item.key || activeChapter === '全部'">
              <button
                v-for="kp in item.children"
                :key="kp.id"
                class="workspace-tree__child"
                :class="{ active: kp.id === selectedKp?.id }"
                @click="selectKp(kp.id)"
              >
                {{ kp.title }}
              </button>
            </div>
          </div>
        </div>
      </aside>

      <section
        ref="stageRef"
        class="workspace-stage"
        :class="{ 'workspace-stage--dragging': draggingCanvas }"
        @mousedown="onStageMouseDown"
        @wheel.prevent="onStageWheel"
      >
        <div class="workspace-stage__top">
          <div class="workspace-stage__top-main">
            <div class="workspace-stage__stats">
              <span class="workspace-stage__pill">分类 {{ categoryNodes.length }}</span>
              <span class="workspace-stage__pill">知识点 {{ visibleKps.length }}</span>
              <span class="workspace-stage__pill">{{ selectedType === "kp" ? "当前知识点" : "当前分类" }}</span>
            </div>
            <div class="workspace-stage__legend">
              <span class="workspace-stage__legend-item">
                <i class="workspace-stage__legend-line workspace-stage__legend-line--solid"></i>
                实线箭头：前置 / 顺序关系
              </span>
              <span class="workspace-stage__legend-item">
                <i class="workspace-stage__legend-line workspace-stage__legend-line--dashed"></i>
                虚线 / 三角箭头：支撑、包含、分类归属
              </span>
              <span class="workspace-stage__legend-item">
                <i class="workspace-stage__legend-line workspace-stage__legend-line--path"></i>
                蓝色虚线：推荐路径，同色环表示同类能力或素养
              </span>
            </div>
          </div>
          <div class="workspace-stage__focus">
            <span>
              {{ selectedType === "kp" ? (selectedKp?.title || "未选择知识点") : (selectedCategoryNode?.title || "未选择分类") }}
            </span>
            <button class="workspace-stage__learn-btn workspace-stage__learn-btn--ghost" @click.stop="toggleAllKps">
              {{ showAllKps ? "仅看分类" : "显示全部节点" }}
            </button>
            <button v-if="selectedType === 'kp' && selectedKp" class="workspace-stage__learn-btn" @click.stop="openContentFromSelected">
              去学习
            </button>
          </div>
        </div>
        <svg
          class="workspace-canvas"
          :width="CANVAS_WIDTH"
          :height="CANVAS_HEIGHT"
          :style="{ transform: `translate(${panX}px, ${panY}px) scale(${canvasScale})` }"
        >
          <rect x="0" y="0" :width="CANVAS_WIDTH" :height="CANVAS_HEIGHT" fill="#f8fbff" />
          <defs>
            <marker id="student-edge-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(100,116,139,0.55)" />
            </marker>
            <marker id="student-edge-arrow-path" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#5a8ef0" />
            </marker>
            <marker id="student-edge-arrow-triangle" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 1 1 L 9 5 L 1 9 z" fill="#46a57b" />
            </marker>
            <marker id="student-edge-arrow-open" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 1 1 L 9 5 L 1 9" fill="none" stroke="#db9d37" stroke-width="1.5" />
            </marker>
            <marker id="student-chapter-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(75,94,130,0.55)" />
            </marker>
          </defs>

          <line
            v-for="edge in visibleChapterEdges"
            :key="`chapter-${edge.id}`"
            :x1="categoryPoint(edge.source_chapter).x"
            :y1="categoryPoint(edge.source_chapter).y"
            :x2="categoryPoint(edge.target_chapter).x"
            :y2="categoryPoint(edge.target_chapter).y"
            :stroke="chapterEdgeStroke(edge)"
            stroke-width="2.2"
            stroke-dasharray="6 6"
            :marker-end="edge.relation_type === 'related' ? undefined : 'url(#student-chapter-arrow)'"
          />

          <line
            v-for="edge in visibleEdges"
            :key="`${edge.prereq_id}-${edge.next_id}-${edge.relation_type}`"
            :x1="edgeLine(edge).x1"
            :y1="edgeLine(edge).y1"
            :x2="edgeLine(edge).x2"
            :y2="edgeLine(edge).y2"
            :stroke="edgeStroke(edge)"
            :stroke-width="edgeWidth(edge)"
            stroke-linecap="round"
            :stroke-dasharray="edgeDasharray(edge)"
            :marker-end="edgeMarker(edge)"
          />

          <line
            v-for="kp in visibleKps"
            :key="`cat-${kp.id}`"
            :x1="categoryKpLine(kp).x1"
            :y1="categoryKpLine(kp).y1"
            :x2="categoryKpLine(kp).x2"
            :y2="categoryKpLine(kp).y2"
            stroke="rgba(100,116,139,0.4)"
            stroke-width="1.2"
            stroke-linecap="round"
            stroke-dasharray="3 4"
          />

          <g
            v-for="category in categoryNodes"
            :key="category.key"
            class="workspace-category-node"
            :transform="`translate(${categoryPoint(category.key).x}, ${categoryPoint(category.key).y})`"
            @click="selectCategory(category.key)"
            @mousedown="onNodeMouseDown($event, 'category', category.key)"
          >
            <rect x="-112" y="-44" width="224" height="88" rx="20" :fill="selectedCategory === category.key ? '#edf4ff' : '#ffffff'" :stroke="selectedCategory === category.key ? '#7fb0ff' : '#d7e2f0'" stroke-width="1.8" />
            <text class="workspace-category-node__title" text-anchor="middle" y="-6">{{ category.title }}</text>
            <text class="workspace-category-node__meta" text-anchor="middle" y="22">{{ category.total }} 个知识点</text>
          </g>

          <g
            v-for="kp in visibleKps"
            :key="kp.id"
            class="workspace-node"
            :transform="`translate(${kpPoint(kp.id).x}, ${kpPoint(kp.id).y})`"
            @click="selectKp(kp.id)"
            @mousedown="onNodeMouseDown($event, 'kp', kp.id)"
          >
            <circle :r="nodeRadius(kp) + 18" :fill="'transparent'" :stroke="ringColor('literacy', effectiveOverlayMap.get(kp.id)?.literacy_status, effectiveOverlayMap.get(kp.id)?.literacy_labels || splitLabels(kp.literacy_tag))" :stroke-width="effectiveOverlayMap.get(kp.id)?.literacy_enabled ? 5 : 0" />
            <circle :r="nodeRadius(kp) + 10" :fill="'transparent'" :stroke="ringColor('ability', effectiveOverlayMap.get(kp.id)?.ability_status, effectiveOverlayMap.get(kp.id)?.ability_labels || splitLabels(kp.ability_tag))" :stroke-width="effectiveOverlayMap.get(kp.id)?.ability_enabled ? 5 : 0" />
            <circle :r="nodeRadius(kp) + 2" :fill="'transparent'" :stroke="ringColor('knowledge', effectiveOverlayMap.get(kp.id)?.knowledge_status)" :stroke-width="4" />
            <circle :r="nodeRadius(kp) + 22" :fill="isRecommended(kp.id) || isPathNode(kp.id) ? 'rgba(70, 122, 235, 0.14)' : 'rgba(96,139,232,0.08)'" />
            <circle
              :r="nodeRadius(kp)"
              :fill="kp.id === selectedKp?.id ? '#eef5ff' : ((isRecommended(kp.id) || isPathNode(kp.id)) ? '#f4f8ff' : '#ffffff')"
              :stroke="kp.id === selectedKp?.id ? '#7ca9f3' : ((isRecommended(kp.id) || isPathNode(kp.id)) ? '#5a8ef0' : '#d7e2f0')"
              :stroke-width="isRecommended(kp.id) ? 2.6 : (isPathNode(kp.id) ? 2.3 : 2)"
            />
            <text class="workspace-node__code" text-anchor="middle" y="-8">{{ kp.code }}</text>
            <text class="workspace-node__title" text-anchor="middle" y="16">{{ kp.title.slice(0, 10) }}</text>
            <g v-if="isRecommended(kp.id)">
              <rect x="-24" y="-50" width="48" height="20" rx="10" fill="#5a8ef0" />
              <text class="workspace-node__badge" text-anchor="middle" y="-36">推荐</text>
            </g>
            <g v-else-if="isPathNode(kp.id)">
              <rect x="-24" y="-50" width="48" height="20" rx="10" fill="#89aef5" />
              <text class="workspace-node__badge" text-anchor="middle" y="-36">路径</text>
            </g>
          </g>
        </svg>

        <div class="workspace-bottom">
          <div class="workspace-zoom">
            <button @click="zoomOut">-</button>
            <span>缩放 {{ Math.round(canvasScale * 100) }}%</span>
            <button @click="zoomIn">+</button>
          </div>
        </div>

        <div v-if="!loading && !hasGraphData" class="workspace-stage__empty">
          <strong>这门课还没有知识图谱</strong>
          <span>请先让老师创建知识点和关系，再回来查看。</span>
        </div>
      </section>

      <aside class="workspace-drawer" v-if="selectedKp || selectedCategoryNode">
        <div class="workspace-drawer__header">
          <h3 class="workspace-drawer__title">{{ selectedType === 'kp' ? selectedKp?.title : selectedCategoryNode?.title }}</h3>
        </div>

        <div class="workspace-drawer__content">
          <template v-if="selectedType === 'kp' && selectedKp">
            <div class="workspace-drawer__meta">{{ selectedKp.code }} · {{ selectedKp.chapter || "未分章" }}</div>
            <div class="workspace-drawer__status">{{ nodeLabel(activeOverlay?.status) }}</div>
            <div class="workspace-drawer__guide-inline">
              <span>知识点说明</span>
              <HoverTip content="这里会显示这个知识点的学习状态、学习资源和前面要先学的内容。" />
            </div>
            <div v-if="activeOverlay?.recommended" class="workspace-drawer__recommend">
              这是系统当前推荐你优先学习的知识点。
            </div>
            <div v-if="activeOverlay?.blocked_reason" class="workspace-drawer__blocked">
              前置阻塞：{{ activeOverlay.blocked_reason }}
            </div>

            <div class="workspace-drawer__section">
              <h4 class="workspace-drawer__section-title">知识点详细内容</h4>
              <div class="workspace-drawer__detail-grid">
                <div class="workspace-drawer__detail-item">
                  <span>章节</span>
                  <strong>{{ selectedKp.chapter || "未分章" }}</strong>
                </div>
                <div class="workspace-drawer__detail-item">
                  <span>知识目标</span>
                  <strong>{{ activeOverlay?.knowledge_label || selectedKp.knowledge_tag || selectedKp.title }}</strong>
                </div>
                <div class="workspace-drawer__detail-item">
                  <span>能力目标</span>
                  <strong>{{ (activeOverlay?.ability_labels ?? []).join("、") || selectedKp.ability_tag || "暂未设置" }}</strong>
                </div>
                <div class="workspace-drawer__detail-item">
                  <span>素养目标</span>
                  <strong>{{ (activeOverlay?.literacy_labels ?? []).join("、") || selectedKp.literacy_tag || "暂未设置" }}</strong>
                </div>
              </div>
              <div class="workspace-drawer__desc">
                {{ selectedKp.description || "暂未填写描述" }}
              </div>
            </div>

            <div class="workspace-drawer__metrics">
              <div class="workspace-drawer__metric">
                <span>掌握度</span>
                <strong>{{ metricPercent(activeOverlay?.mastery) }}%</strong>
              </div>
              <div class="workspace-drawer__metric">
                <span>难度</span>
                <strong>{{ metricPercent(selectedKp.difficulty) }}</strong>
              </div>
            </div>

            <div class="workspace-drawer__section">
              <h4 class="workspace-drawer__section-title">知识 / 能力 / 素养</h4>
              <div class="workspace-drawer__tags">
                <span class="workspace-drawer__tag workspace-drawer__tag--knowledge">
                  知识：{{ activeOverlay?.knowledge_label || selectedKp.knowledge_tag || selectedKp.title }}
                </span>
                <span v-for="item in activeOverlay?.ability_labels ?? []" :key="`a-${item}`" class="workspace-drawer__tag workspace-drawer__tag--ability">
                  能力：{{ item }}
                </span>
                <span v-for="item in activeOverlay?.literacy_labels ?? []" :key="`l-${item}`" class="workspace-drawer__tag workspace-drawer__tag--literacy">
                  素养：{{ item }}
                </span>
              </div>
              <div class="workspace-drawer__status-grid">
                <div class="workspace-drawer__mini-metric">
                  <span>知识达成</span>
                  <strong>{{ nodeLabel(activeOverlay?.knowledge_status || 'not_started') }}</strong>
                </div>
                <div class="workspace-drawer__mini-metric">
                  <span>能力达成</span>
                  <strong>{{ nodeLabel(activeOverlay?.ability_status || 'not_started') }}</strong>
                </div>
                <div class="workspace-drawer__mini-metric">
                  <span>素养达成</span>
                  <strong>{{ nodeLabel(activeOverlay?.literacy_status || 'not_started') }}</strong>
                </div>
              </div>
            </div>

            <div class="workspace-drawer__section">
              <h4 class="workspace-drawer__section-title">学习资源</h4>
              <button class="workspace-drawer__learn-btn" @click="openContentFromSelected">资源内容 / 去学习</button>
              <div v-if="(nodeDetail?.resource_list?.length ?? 0) === 0" class="workspace-drawer__empty">暂无资源</div>
              <button
                v-for="item in nodeDetail?.resource_list ?? []"
                :key="item.id"
                type="button"
                class="workspace-drawer__link workspace-drawer__link-btn"
                @click="openResource(item)"
              >
                {{ item.title }}
              </button>
            </div>

            <div class="workspace-drawer__section">
              <h4 class="workspace-drawer__section-title">前置知识</h4>
              <div v-if="(nodeDetail?.prerequisites?.length ?? 0) === 0" class="workspace-drawer__empty">无前置要求</div>
              <div v-else class="workspace-drawer__tags">
                <button v-for="item in nodeDetail?.prerequisites ?? []" :key="item.id" class="workspace-drawer__tag" @click="selectKp(item.id)">
                  {{ item.title }}
                </button>
              </div>
            </div>
            <div v-if="isPathNode(selectedKp.id)" class="workspace-drawer__recommend">
              当前知识点位于系统推荐路径中，可按路径顺序继续学习。
            </div>
          </template>

          <template v-else-if="selectedCategoryNode && selectedCategoryOverview">
            <div class="workspace-drawer__meta">共 {{ selectedCategoryOverview.total }} 个知识点</div>
            <div class="workspace-drawer__guide-inline">
              <span>分类说明</span>
              <HoverTip content="这里是这个分类的总览。先看整体情况，再点下面的知识点进入具体内容。" />
            </div>

            <div class="workspace-drawer__metrics">
              <div class="workspace-drawer__metric"><span>已掌握</span><strong>{{ selectedCategoryOverview.mastered }}</strong></div>
              <div class="workspace-drawer__metric"><span>学习中</span><strong>{{ selectedCategoryOverview.learning }}</strong></div>
              <div class="workspace-drawer__metric"><span>风险</span><strong>{{ selectedCategoryOverview.risk }}</strong></div>
              <div class="workspace-drawer__metric"><span>未开始</span><strong>{{ selectedCategoryOverview.idle }}</strong></div>
            </div>

            <div class="workspace-drawer__section">
              <h4 class="workspace-drawer__section-title">知识点</h4>
              <div v-if="selectedCategoryOverview.recommended" class="workspace-drawer__recommend">
                当前分类推荐先学：{{ selectedCategoryOverview.recommended.title }}
              </div>
              <div class="workspace-drawer__tags">
                <button v-for="item in selectedCategoryOverview.items" :key="item.id" class="workspace-drawer__tag" @click="selectKp(item.id)">
                  {{ item.title }}
                </button>
              </div>
            </div>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.workspace-shell {
  min-height: calc(100vh - 190px);
  background: #ffffff;
  overflow: hidden;
  border-radius: 28px;
  box-shadow: 0 26px 54px rgba(15, 23, 42, 0.16);
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 22px;
  border-bottom: 1px solid #e1eaf1;
  background: #ffffff;
}

.workspace-guide {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 22px 0;
  background: #ffffff;
}

.workspace-guide span {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid #dbe6f2;
  background: #f4f8fc;
  color: #536883;
  font-size: 12px;
  font-weight: 700;
}

.workspace-drawer__guide-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: #617792;
  font-size: 12px;
  font-weight: 700;
}

.workspace-heading {
  display: grid;
  gap: 4px;
}

.workspace-title {
  font-size: 22px;
  font-weight: 800;
  color: #243449;
  margin: 0;
}

.workspace-subtitle {
  margin: 0;
  color: #718097;
  font-size: 13px;
}

.workspace-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.workspace-search {
  width: 220px;
}

.workspace-search :deep(.el-input__wrapper) {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px #d8e2ef;
}

.workspace-search :deep(.el-input__inner) {
  color: #243449;
}

.workspace-search :deep(.el-input__inner::placeholder) {
  color: #90a0b6;
}

.workspace-btn {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid #d8e2ef;
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
  color: #35507f;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-shadow: var(--app-shadow-soft);
}

.workspace-btn:hover {
  background: #eff5ff;
}

.workspace-btn--primary {
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  border-color: var(--app-green);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
}

.workspace-content {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 320px;
  gap: 16px;
  height: calc(100vh - 262px);
  padding: 16px;
}

.workspace-content--sidebar-collapsed {
  grid-template-columns: 88px minmax(0, 1fr) 320px;
}

.workspace-content--drawer-collapsed {
  grid-template-columns: 260px minmax(0, 1fr);
}

.workspace-sidebar {
  padding: 14px;
  border-radius: 24px;
  background: #f8fbff;
  border: 1px solid #dce6f2;
  overflow-y: auto;
}

.workspace-sidebar--collapsed {
  overflow: hidden;
  padding: 14px 10px;
}

.workspace-sidebar__collapsed {
  display: grid;
  place-items: start;
}

.workspace-sidebar__toggle {
  width: 100%;
  min-height: 44px;
  border: 1px solid #dce6f2;
  border-radius: 16px;
  background: #ffffff;
  color: #35507f;
  cursor: pointer;
}

.workspace-tree {
  display: grid;
  gap: 12px;
}

.workspace-tree__empty {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 18px;
  border: 1px dashed #d7e2ef;
  background: #ffffff;
  color: #617792;
}

.workspace-tree__empty strong {
  color: #243449;
  font-size: 14px;
}

.workspace-tree__empty span {
  font-size: 12px;
  line-height: 1.6;
}

.workspace-tree__summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-radius: 16px;
  background: #ffffff;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.workspace-tree__summary:hover {
  background: #eff5ff;
}

.workspace-tree__summary.active {
  background: #e3f2fd;
  color: #1565c0;
}

.workspace-tree__count {
  font-size: 12px;
  color: #94a3b8;
}

.workspace-tree__children {
  margin-top: 8px;
  display: grid;
  gap: 8px;
}

.workspace-tree__child {
  display: block;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e1eaf1;
  border-radius: 14px;
  background: #ffffff;
  color: #475569;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
  margin-bottom: 4px;
}

.workspace-tree__child:hover {
  background: #f8fafc;
}

.workspace-tree__child.active {
  background: #e3f2fd;
  border-color: #90caf9;
  color: #1565c0;
}

.workspace-stage {
  position: relative;
  overflow: hidden;
  cursor: grab;
  user-select: none;
  touch-action: none;
  border-radius: 28px;
  background: #f8fbff;
  border: 1px solid #dce6f2;
}

.workspace-stage--dragging {
  cursor: grabbing;
}

.workspace-stage__top {
  position: absolute;
  top: 16px;
  left: 18px;
  right: 18px;
  z-index: 3;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.workspace-stage__top-main {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.workspace-stage__stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.workspace-stage__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.workspace-stage__legend-item {
  min-height: 34px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #dce6f2;
  color: #51657f;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.workspace-stage__legend-line {
  width: 28px;
  height: 0;
  border-top: 2px solid #64748b;
  flex: 0 0 auto;
}

.workspace-stage__legend-line--dashed {
  border-top-style: dashed;
  opacity: 0.72;
}

.workspace-stage__legend-line--path {
  border-top-color: #5a8ef0;
  border-top-style: dashed;
  border-top-width: 3px;
}

.workspace-stage__pill,
.workspace-stage__focus {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dce6f2;
  color: #35507f;
  font-size: 12px;
  font-weight: 700;
}

.workspace-stage__focus {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  max-width: 420px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-stage__focus span {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-stage__learn-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid #cde0fb;
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 18px rgba(47, 111, 237, 0.16);
}

.workspace-stage__learn-btn:hover {
  transform: translateY(-1px);
}

.workspace-stage__learn-btn--ghost {
  background: #ffffff;
  border-color: #dce6f2;
  color: #35507f;
  box-shadow: none;
}

.workspace-stage__learn-btn--ghost:hover {
  background: #f8fbff;
}

.workspace-canvas {
  display: block;
  transform-origin: 0 0;
  transition: transform 0.08s ease;
  cursor: grab;
  position: relative;
  z-index: 1;
}

.workspace-node,
.workspace-category-node {
  cursor: pointer;
}

.workspace-node__title,
.workspace-category-node__title,
.workspace-category-node__meta,
.workspace-node__code {
  fill: #243449;
  font-weight: 500;
  pointer-events: none;
}

.workspace-node__title,
.workspace-category-node__title {
  font-size: 15px;
  font-weight: 700;
}

.workspace-category-node__meta,
.workspace-node__code {
  font-size: 12px;
  fill: #718097;
}

.workspace-bottom {
  position: absolute;
  bottom: 16px;
  right: 16px;
  z-index: 10;
}

.workspace-stage__empty {
  position: absolute;
  inset: 50% auto auto 50%;
  transform: translate(-50%, -50%);
  display: grid;
  gap: 8px;
  width: min(360px, calc(100% - 48px));
  padding: 24px 22px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #dbe5f1;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
  text-align: center;
  color: #5f738f;
  z-index: 4;
}

.workspace-stage__empty strong {
  color: #243449;
  font-size: 16px;
}

.workspace-stage__empty span {
  font-size: 13px;
  line-height: 1.7;
}

.workspace-zoom {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dce6f2;
  box-shadow: none;
}

.workspace-zoom button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: #eff5ff;
  color: #35507f;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.workspace-zoom button:hover {
  background: #dfefff;
}

.workspace-zoom span {
  font-size: 12px;
  color: #35507f;
  min-width: 70px;
  text-align: center;
}

.workspace-drawer {
  padding: 14px;
  border-radius: 24px;
  background: #f8fbff;
  border: 1px solid #dce6f2;
  overflow-y: auto;
  color: #475569;
}

.workspace-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 1px solid #e1eaf1;
}

.workspace-drawer__title {
  font-size: 16px;
  font-weight: 700;
  color: #243449;
  margin: 0;
}

.workspace-drawer__close {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: #eff5ff;
  color: #35507f;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.workspace-drawer__close:hover {
  background: #dfefff;
}

.workspace-drawer__content {
  padding-top: 16px;
}

.workspace-drawer__guide {
  padding: 12px 14px;
  border-radius: 16px;
  background: #f4f8fc;
  border: 1px solid #dde7f2;
  color: #617792;
  font-size: 12px;
  line-height: 1.7;
  margin-bottom: 14px;
}

.workspace-drawer__meta {
  font-size: 12px;
  color: #718097;
  margin-bottom: 8px;
}

.workspace-drawer__status {
  display: inline-block;
  padding: 8px 12px;
  border-radius: 999px;
  background: #edf4ff;
  color: #2459ab;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 16px;
}

.workspace-drawer__metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 20px;
}

.workspace-drawer__metric {
  padding: 12px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid #e1eaf1;
}

.workspace-drawer__metric span {
  display: block;
  font-size: 11px;
  color: #728299;
  margin-bottom: 4px;
}

.workspace-drawer__metric strong {
  font-size: 20px;
  color: #233447;
  font-weight: 700;
}

.workspace-drawer__status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.workspace-drawer__mini-metric {
  padding: 10px;
  border-radius: 14px;
  background: #fafcff;
  border: 1px solid #e1eaf1;
}

.workspace-drawer__mini-metric span {
  display: block;
  font-size: 11px;
  color: #728299;
  margin-bottom: 4px;
}

.workspace-drawer__mini-metric strong {
  font-size: 13px;
  color: #233447;
}

.workspace-drawer__section {
  margin-bottom: 20px;
}

.workspace-drawer__detail-grid {
  display: grid;
  gap: 8px;
  margin-bottom: 10px;
}

.workspace-drawer__detail-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: #fafcff;
  border: 1px solid #e1eaf1;
  display: grid;
  gap: 4px;
}

.workspace-drawer__detail-item span {
  font-size: 11px;
  color: #728299;
}

.workspace-drawer__detail-item strong {
  font-size: 13px;
  color: #233447;
  line-height: 1.6;
}

.workspace-drawer__desc {
  padding: 12px 14px;
  border-radius: 16px;
  background: #fafcff;
  border: 1px solid #e1eaf1;
  color: #51657f;
  font-size: 13px;
  line-height: 1.7;
}

.workspace-drawer__section-title {
  font-size: 13px;
  font-weight: 700;
  color: #314661;
  margin: 0 0 8px 0;
}

.workspace-drawer__learn-btn {
  margin-bottom: 8px;
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid var(--app-green);
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
}

.workspace-drawer__learn-btn:hover {
  transform: translateY(-1px);
}

.workspace-drawer__empty {
  font-size: 12px;
  color: #90a0b6;
}

.workspace-drawer__link {
  display: block;
  color: #35507f;
  text-decoration: none;
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 4px;
}

.workspace-drawer__link-btn {
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.workspace-drawer__link:hover {
  text-decoration: underline;
}

.workspace-drawer__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.workspace-drawer__tag {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #dce6f2;
  border-radius: 999px;
  background: #ffffff;
  color: #35507f;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.2s ease;
  display: inline-flex;
  align-items: center;
}

.workspace-drawer__tag:hover {
  background: #eff5ff;
}

.workspace-drawer__tag--knowledge {
  border-color: #b8dfc9;
  background: #f1fbf5;
  color: #1e7e4f;
}

.workspace-drawer__tag--ability {
  border-color: #eed28c;
  background: #fff8e5;
  color: #a26d00;
}

.workspace-drawer__tag--literacy {
  border-color: #bcd0fb;
  background: #f2f6ff;
  color: #2f6fed;
}

@media (max-width: 1200px) {
  .workspace-content {
    grid-template-columns: 200px 1fr;
  }

  .workspace-drawer {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 280px;
    box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
    z-index: 20;
  }
}

@media (max-width: 768px) {
  .workspace-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .workspace-controls {
    width: 100%;
    justify-content: space-between;
  }

  .workspace-search {
    flex: 1;
  }

  .workspace-content {
    grid-template-columns: 1fr;
    height: calc(100vh - 280px);
  }

  .workspace-stage__top {
    position: static;
    padding: 14px 14px 0;
    flex-direction: column;
    align-items: stretch;
  }

  .workspace-stage__focus {
    max-width: none;
  }

  .workspace-sidebar {
    display: none;
  }

  .workspace-content--sidebar-collapsed,
  .workspace-content--drawer-collapsed {
    grid-template-columns: 1fr;
  }
}
</style>
