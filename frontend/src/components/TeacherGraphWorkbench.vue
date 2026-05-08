<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import {
  buildDeterministicGraphLayout,
  mergeChapterLayout,
  deterministicDraftPosition,
  CANVAS_WIDTH,
  CANVAS_HEIGHT,
  INITIAL_CENTER_X,
  INITIAL_CENTER_Y,
} from "../graph/graphLayout";
import HoverTip from "./HoverTip.vue";
import QueryToolbar from "./QueryToolbar.vue";

type KP = {
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
  is_terminal?: boolean;
  pos_x?: number | null;
  pos_y?: number | null;
};

function runTeacherSearch() {
  const keyword = search.value.trim();
  if (!keyword) {
    ElMessage.info("请输入知识点名称、编码或章节");
    return;
  }
  const kw = keyword.toLowerCase();
  const matches = kps.value.filter((kp) =>
    `${kp.code} ${kp.title} ${kp.description || ""} ${kp.chapter || ""}`.toLowerCase().includes(kw),
  );
  showAllKps.value = true;
  activeChapter.value = "全部";
  if (matches.length === 0) {
    ElMessage.warning("未找到匹配的知识点");
    return;
  }
  const first = matches[0];
  selectKp(first.id);
  nextTick(() => {
    viewportFitRetryCount.value = 0;
    fitVisibleToViewport();
  });
}

function resetTeacherSearch() {
  search.value = "";
}

type Edge = {
  id: number;
  prereq_id: number;
  next_id: number;
  relation_type: string;
};

type Point = { x: number; y: number };

type CategoryNode = {
  key: string;
  title: string;
  total: number;
};

type ChapterEdge = {
  id: number;
  source_chapter: string;
  target_chapter: string;
  relation_type: string;
};

type DragNode = {
  type: "kp" | "category";
  id: number | string;
  origin: Point;
};

type WorkbenchViewState = {
  canvasScale: number;
  panX: number;
  panY: number;
  activeChapter: string;
  search: string;
  showAllKps: boolean;
  selectedType: "kp" | "category";
  selectedId: number | null;
  selectedCategory: string | null;
  drawerOpen: boolean;
  detailTab: "overview" | "relations" | "content";
};

type GraphExpansionMode = "collapsed" | "chapter" | "all";

const props = withDefaults(defineProps<{ subject: string; grade: string; fullscreen?: boolean; readonly?: boolean; embedded?: boolean }>(), {
  fullscreen: false,
  readonly: false,
  embedded: false,
});
const router = useRouter();
const emit = defineEmits<{
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
  (e: "open-fullscreen"): void;
}>();

const loading = ref(false);
const saving = ref(false);
const search = ref("");
const activeChapter = ref("全部");
const selectedType = ref<"kp" | "category">("kp");
const selectedId = ref<number | null>(null);
const selectedCategory = ref<string | null>(null);
const showAllKps = ref(false);
const graphEditorOpen = ref(false);
const linkSelectionMode = ref<null | "forward" | "backward" | "related" | "support" | "contains">(null);
const categoryLinkMode = ref<null | "prerequisite" | "related" | "support">(null);
const drawerOpen = ref(true);
const detailTab = ref<"overview" | "relations" | "content">("overview");
const DEFAULT_CANVAS_SCALE = 0.58;
const MIN_CANVAS_SCALE = 0.2;
const MAX_CANVAS_SCALE = 4;
const SCALE_STEP = 0.2;
const canvasScale = ref(DEFAULT_CANVAS_SCALE);
const panX = ref(0);
const panY = ref(0);
const viewportFitRetryCount = ref(0);
const stageRef = ref<HTMLElement | null>(null);
const viewportWidth = ref(0);
const viewportHeight = ref(0);
let stageResizeObserver: ResizeObserver | null = null;
let stageResizeFrame = 0;
const draggingCanvas = ref(false);
const draggingNode = ref<DragNode | null>(null);
const dragStartX = ref(0);
const dragStartY = ref(0);
const dragOriginX = ref(0);
const dragOriginY = ref(0);
const kpPositions = ref<Record<number, Point>>({});
const categoryPositions = ref<Record<string, Point>>({});
const manualKpPositionIds = ref<Set<number>>(new Set());
const kps = ref<KP[]>([]);
const edges = ref<Edge[]>([]);
const chapterEdges = ref<ChapterEdge[]>([]);
const kpCoverageMap = ref<
  Record<number, { resource_count: number; question_count: number; task_count: number; has_quiz: boolean }>
>({});
const showIncompleteOnly = ref(false);
const fullscreenRelationFilter = ref<"all" | "prerequisite" | "related" | "support" | "contains">("all");
const fullscreenFocusFilter = ref<"all" | "important" | "difficult" | "incomplete">("all");
const mutingViewStatePersist = ref(false);
const useLegacyFallbackLayout = ref(false);
const hoveredKpId = ref<number | null>(null);

const form = reactive({
  id: 0,
  code: "",
  title: "",
  description: "",
  chapter: "",
  knowledge_tag: "",
  ability_tag: "",
  literacy_tag: "",
  importance: 0.5,
  difficulty: 0.5,
  is_terminal: false,
});

const chapterSummary = computed(() => {
  const bucket = new Map<string, number>();
  for (const kp of kps.value) {
    const key = kp.chapter || "未分章";
    bucket.set(key, (bucket.get(key) ?? 0) + 1);
  }
  return Array.from(bucket.entries()).map(([chapter, total]) => ({ chapter, total }));
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
    Array.from(new Set(kps.value.flatMap((kp) => splitLabels(kp.ability_tag)))),
    ["#2f9f7f", "#47b089", "#65bf98", "#1f7a63", "#89ceb1", "#a3dcc3"],
  ),
);

const literacyColorMap = computed(() =>
  buildLabelColorMap(
    Array.from(new Set(kps.value.flatMap((kp) => splitLabels(kp.literacy_tag)))),
    ["#b88f46", "#c79c54", "#d4ad6d", "#9d7840", "#dfbd84", "#e8cb99"],
  ),
);

function chapterSortScore(chapter: string) {
  const scores = kps.value
    .filter((kp) => (kp.chapter || "未分章") === chapter)
    .map((kp) => Number(String(kp.code || "").match(/(\d+)/)?.[1] ?? Number.MAX_SAFE_INTEGER));
  return scores.length ? Math.min(...scores) : Number.MAX_SAFE_INTEGER;
}

const categoryNodes = computed<CategoryNode[]>(() =>
  chapterSummary.value
    .map((item) => ({ key: item.chapter, title: item.chapter, total: item.total }))
    .sort((a, b) => {
      const scoreA = chapterSortScore(a.key);
      const scoreB = chapterSortScore(b.key);
      if (scoreA !== scoreB) return scoreA - scoreB;
      return a.key.localeCompare(b.key, "zh-Hans-CN");
    }),
);

const filteredKps = computed(() => {
  const kw = search.value.trim().toLowerCase();
  return kps.value.filter((kp) => {
    const chapterOk = activeChapter.value === "全部" || (kp.chapter || "未分章") === activeChapter.value;
    if (!chapterOk) return false;
    if (!kw) return true;
    return `${kp.code} ${kp.title} ${kp.description || ""} ${kp.chapter || ""}`.toLowerCase().includes(kw);
  });
});

const visibleKps = computed(() => {
  if (!showAllKps.value) return [];
  let list: KP[] = filteredKps.value;
  if (props.fullscreen) {
    if (fullscreenFocusFilter.value === "important") {
      list = list.filter((kp) => (kp.importance ?? 0.5) >= 0.72);
    } else if (fullscreenFocusFilter.value === "difficult") {
      list = list.filter((kp) => (kp.difficulty ?? 0.5) >= 0.68);
    } else if (fullscreenFocusFilter.value === "incomplete") {
      list = list.filter((kp) => {
        const c = kpCoverageMap.value[kp.id];
        const rc = c?.resource_count ?? 0;
        const qc = c?.question_count ?? 0;
        return rc === 0 || qc === 0;
      });
    }
  }
  if (showIncompleteOnly.value) {
    list = list.filter((kp) => {
      const c = kpCoverageMap.value[kp.id];
      const rc = c?.resource_count ?? 0;
      const qc = c?.question_count ?? 0;
      return rc === 0 || qc === 0;
    });
  }
  if (selectedType.value === "kp" && selectedId.value != null && !list.some((k) => k.id === selectedId.value)) {
    const pinned = kps.value.find((k) => k.id === selectedId.value);
    if (pinned) list = [...list, pinned];
  }
  return list;
});

const treeNodes = computed(() => {
  const kw = search.value.trim().toLowerCase();
  return categoryNodes.value
    .map((item) => {
      const children = kps.value
        .filter((kp) => (kp.chapter || "未分章") === item.key)
        .filter((kp) => {
          if (!kw) return true;
          return `${kp.code} ${kp.title} ${kp.description || ""}`.toLowerCase().includes(kw) || item.title.toLowerCase().includes(kw);
        });
      return {
        ...item,
        children,
      };
    })
    .filter((item) => item.children.length > 0 || item.title.toLowerCase().includes(kw));
});

const selectedKp = computed(() => (selectedType.value === "kp" ? kps.value.find((kp) => kp.id === selectedId.value) ?? null : null));
const selectedCategoryNode = computed(() =>
  selectedType.value === "category" ? categoryNodes.value.find((item) => item.key === selectedCategory.value) ?? null : null,
);
const showSidebar = computed(() => !props.fullscreen && !props.embedded);
const showInspector = computed(() => !props.fullscreen && !props.embedded);
const inlineEditorEnabled = computed(() => showInspector.value);
const graphExpansionMode = computed<GraphExpansionMode>(() => {
  if (!showAllKps.value) return "collapsed";
  return activeChapter.value === "全部" ? "all" : "chapter";
});
const expansionToggleLabel = computed(() => (graphExpansionMode.value === "all" ? "仅显示章节" : "展开全部节点"));
const drawerVisible = computed(
  () => showInspector.value && drawerOpen.value && (graphEditorOpen.value || selectedKp.value != null || selectedCategoryNode.value != null),
);
const drawerTitle = computed(() => {
  if (graphEditorOpen.value) return form.id ? "编辑知识点" : "新建知识点";
  if (selectedType.value === "kp") return selectedKp.value?.title || "知识点详情";
  return selectedCategoryNode.value?.title || "分类详情";
});

const selectedConnections = computed(() => {
  if (!selectedKp.value) return { incoming: [], outgoing: [], related: [] as KP[], support: [] as KP[], contains: [] as KP[] };
  const currentId = selectedKp.value.id;
  const incomingIds = edges.value.filter((edge) => edge.next_id === currentId && edge.relation_type === "prerequisite").map((edge) => edge.prereq_id);
  const outgoingIds = edges.value.filter((edge) => edge.prereq_id === currentId && edge.relation_type === "prerequisite").map((edge) => edge.next_id);
  const relatedIds = edges.value
    .filter((edge) => edge.relation_type === "related" && (edge.prereq_id === currentId || edge.next_id === currentId))
    .map((edge) => (edge.prereq_id === currentId ? edge.next_id : edge.prereq_id));
  const supportIds = edges.value
    .filter((edge) => edge.relation_type === "support" && (edge.prereq_id === currentId || edge.next_id === currentId))
    .map((edge) => (edge.prereq_id === currentId ? edge.next_id : edge.prereq_id));
  const containsIds = edges.value
    .filter((edge) => edge.relation_type === "contains" && (edge.prereq_id === currentId || edge.next_id === currentId))
    .map((edge) => (edge.prereq_id === currentId ? edge.next_id : edge.prereq_id));

  return {
    incoming: kps.value.filter((kp) => incomingIds.includes(kp.id)),
    outgoing: kps.value.filter((kp) => outgoingIds.includes(kp.id)),
    related: kps.value.filter((kp) => relatedIds.includes(kp.id)),
    support: kps.value.filter((kp) => supportIds.includes(kp.id)),
    contains: kps.value.filter((kp) => containsIds.includes(kp.id)),
  };
});

const deletableEdges = computed(() => {
  if (!selectedKp.value) return [] as Array<{
    edge: Edge;
    relationLabel: string;
    summary: string;
    detail: string;
  }>;
  const currentId = selectedKp.value.id;
  const currentTitle = selectedKp.value.title;
  const kpMap = new Map(kps.value.map((kp) => [kp.id, kp]));
  return edges.value
    .filter((edge) => edge.prereq_id === currentId || edge.next_id === currentId)
    .map((edge) => {
      const from = kpMap.get(edge.prereq_id);
      const to = kpMap.get(edge.next_id);
      const isIncoming = edge.next_id === currentId;
      const relationLabel = edge.relation_type === "related" ? "关联关系" : isIncoming ? "前置关系" : "后续关系";
      const summary =
        edge.relation_type === "related"
          ? `${from?.title || "未知节点"} 与 ${to?.title || "未知节点"}`
          : `${from?.title || "未知节点"} -> ${to?.title || "未知节点"}`;
      const detail =
        edge.relation_type === "related"
          ? `当前节点“${currentTitle}”与“${(edge.prereq_id === currentId ? to?.title : from?.title) || "未知节点"}”互相关联`
          : isIncoming
            ? `删除后，“${from?.title || "未知节点"}”将不再作为当前节点的前置知识点`
            : `删除后，当前节点将不再指向“${to?.title || "未知节点"}”这个后续知识点`;
      return { edge, relationLabel, summary, detail };
    });
});

const categoryOverview = computed(() => {
  if (!selectedCategoryNode.value) return null;
  const items = kps.value.filter((kp) => (kp.chapter || "未分章") === selectedCategoryNode.value?.key);
  return {
    total: items.length,
    items,
    abilityTags: Array.from(new Set(items.map((kp) => kp.ability_tag).filter(Boolean))),
    literacyTags: Array.from(new Set(items.map((kp) => kp.literacy_tag).filter(Boolean))),
  };
});

const filteredEdgeCount = computed(() => {
  const ids = new Set(filteredKps.value.map((kp) => kp.id));
  return edges.value.filter((edge) => ids.has(edge.prereq_id) && ids.has(edge.next_id)).length;
});

const stageStats = computed(() => ({
  points: filteredKps.value.length,
  edges: filteredEdgeCount.value + visibleChapterEdges.value.length,
  categories: categoryNodes.value.length,
}));

const hasGraphData = computed(() => kps.value.length > 0);
const categoryKeys = computed(() => new Set(categoryNodes.value.map((item) => item.key)));
const visibleChapterEdges = computed(() => {
  const edgeKey = (source: string, target: string) => `${source}\u001f${target}`;
  const explicitKeys = new Set(chapterEdges.value.map((edge) => edgeKey(edge.source_chapter, edge.target_chapter)));
  const derived = new Map<string, ChapterEdge>();
  const pointMap = new Map(kps.value.map((kp) => [kp.id, kp]));
  const relationPriority: Record<string, number> = { prerequisite: 3, support: 2, related: 1, contains: 0 };
  let syntheticId = -1;

  for (const edge of edges.value) {
    const from = pointMap.get(edge.prereq_id);
    const to = pointMap.get(edge.next_id);
    const source = from?.chapter || "未分章";
    const target = to?.chapter || "未分章";
    if (!from || !to || source === target || explicitKeys.has(edgeKey(source, target))) continue;

    const key = edgeKey(source, target);
    const current = derived.get(key);
    if (!current) {
      derived.set(key, {
        id: syntheticId--,
        source_chapter: source,
        target_chapter: target,
        relation_type: edge.relation_type,
      });
      continue;
    }
    if ((relationPriority[edge.relation_type] ?? 0) > (relationPriority[current.relation_type] ?? 0)) {
      current.relation_type = edge.relation_type;
    }
  }

  return [...chapterEdges.value, ...derived.values()].filter((edge) => {
    if (!categoryKeys.value.has(edge.source_chapter) || !categoryKeys.value.has(edge.target_chapter)) return false;
    if (!props.fullscreen || fullscreenRelationFilter.value === "all") return true;
    return edge.relation_type === fullscreenRelationFilter.value;
  });
});
function chapterPositionStorageKey() {
  return `da_teacher_category_pos_v2_${props.subject}_${props.grade}`;
}

function manualKpPositionStorageKey() {
  return `da_teacher_manual_kp_pos_v1_${props.subject}_${props.grade}`;
}

function loadManualKpPositionIds() {
  try {
    const raw = localStorage.getItem(manualKpPositionStorageKey());
    const parsed = raw ? JSON.parse(raw) : [];
    manualKpPositionIds.value = new Set(Array.isArray(parsed) ? parsed.map(Number).filter(Number.isFinite) : []);
  } catch {
    manualKpPositionIds.value = new Set();
  }
}

function saveManualKpPositionIds() {
  localStorage.setItem(manualKpPositionStorageKey(), JSON.stringify(Array.from(manualKpPositionIds.value)));
}

function markKpPositionManual(kpId: number) {
  manualKpPositionIds.value = new Set([...manualKpPositionIds.value, kpId]);
}

function syncManualKpPositionIdsFromRows(rows: KP[]) {
  const ids = new Set(manualKpPositionIds.value);
  for (const kp of rows) {
    if (!kp.id || kp.pos_x == null || kp.pos_y == null) continue;
    const x = Number(kp.pos_x);
    const y = Number(kp.pos_y);
    if (Number.isFinite(x) && Number.isFinite(y) && (x >= 12000 || y >= 12000)) {
      ids.add(kp.id);
    }
  }
  manualKpPositionIds.value = ids;
}

function viewStateStorageKey() {
  if (!props.subject) return "";
  return `da_teacher_graph_view_v4_${props.subject}_${props.grade}`;
}

function persistViewState() {
  if (mutingViewStatePersist.value || props.embedded) return;
  const key = viewStateStorageKey();
  if (!key) return;
  const payload: WorkbenchViewState = {
    canvasScale: canvasScale.value,
    panX: panX.value,
    panY: panY.value,
    activeChapter: activeChapter.value,
    search: search.value,
    showAllKps: showAllKps.value,
    selectedType: selectedType.value,
    selectedId: selectedId.value,
    selectedCategory: selectedCategory.value,
    drawerOpen: drawerOpen.value,
    detailTab: detailTab.value,
  };
  localStorage.setItem(key, JSON.stringify(payload));
}

function disconnectStageResizeObserver() {
  if (stageResizeObserver) {
    stageResizeObserver.disconnect();
    stageResizeObserver = null;
  }
  if (stageResizeFrame) {
    cancelAnimationFrame(stageResizeFrame);
    stageResizeFrame = 0;
  }
}

function fitStageToViewport() {
  viewportFitRetryCount.value = 0;
  if (showAllKps.value && visibleKps.value.length > 0) {
    fitVisibleToViewport();
    return;
  }
  fitCategoryNodesToViewport();
}

function scheduleStageAutoFit() {
  if (loading.value) return;
  if (stageResizeFrame) cancelAnimationFrame(stageResizeFrame);
  stageResizeFrame = requestAnimationFrame(() => {
    stageResizeFrame = 0;
    fitStageToViewport();
  });
}

function connectStageResizeObserver(target: HTMLElement | null) {
  disconnectStageResizeObserver();
  if (!target) return;
  viewportWidth.value = target.clientWidth || 0;
  viewportHeight.value = target.clientHeight || 0;
  if (typeof ResizeObserver === "undefined") return;
  stageResizeObserver = new ResizeObserver((entries) => {
    const entry = entries[0];
    if (!entry) return;
    viewportWidth.value = entry.contentRect.width;
    viewportHeight.value = entry.contentRect.height;
    if (entry.contentRect.width < 48 || entry.contentRect.height < 48) return;
    scheduleStageAutoFit();
  });
  stageResizeObserver.observe(target);
}

function restoreViewState() {
  if (props.embedded) return false;
  const key = viewStateStorageKey();
  if (!key) return false;
  const raw = localStorage.getItem(key);
  if (!raw) return false;
  try {
    const parsed = JSON.parse(raw) as Partial<WorkbenchViewState>;
    mutingViewStatePersist.value = true;
    canvasScale.value = Math.min(
      MAX_CANVAS_SCALE,
      Math.max(MIN_CANVAS_SCALE, Number(parsed.canvasScale ?? DEFAULT_CANVAS_SCALE)),
    );
    panX.value = Number(parsed.panX ?? 0);
    panY.value = Number(parsed.panY ?? 0);
    activeChapter.value = typeof parsed.activeChapter === "string" && parsed.activeChapter ? parsed.activeChapter : "全部";
    search.value = typeof parsed.search === "string" ? parsed.search : "";
    showAllKps.value = parsed.showAllKps !== false;
    selectedType.value = parsed.selectedType === "category" ? "category" : "kp";
    selectedId.value = Number.isFinite(Number(parsed.selectedId)) ? Number(parsed.selectedId) : null;
    selectedCategory.value = typeof parsed.selectedCategory === "string" ? parsed.selectedCategory : null;
    drawerOpen.value = parsed.drawerOpen !== false;
    detailTab.value = parsed.detailTab === "relations" || parsed.detailTab === "content" ? parsed.detailTab : "overview";
    return true;
  } catch {
    return false;
  } finally {
    mutingViewStatePersist.value = false;
  }
}

function normalizeWorkbenchSelectionState() {
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
    if (selectedCategory.value && activeChapter.value !== "全部") activeChapter.value = selectedCategory.value;
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

  if (showAllKps.value && activeChapter.value !== "全部" && !chapterKeySet.has(activeChapter.value)) {
    activeChapter.value = "全部";
    changed = true;
  }

  if (!drawerVisible.value) {
    drawerOpen.value = true;
    changed = true;
  }
  return changed;
}

const deterministicLayout = computed(() =>
  buildDeterministicGraphLayout(kps.value.map((kp) => ({ id: kp.id, code: kp.code, chapter: kp.chapter }))),
);
const defaultCategoryPositions = computed<Record<string, Point>>(() => deterministicLayout.value.categoryPositions);
const defaultKpPositions = computed<Record<number, Point>>(() => deterministicLayout.value.kpPositions);

function isLegacyCoordinateLayout(rows: KP[]) {
  const withPos = rows.filter((kp) => kp.pos_x != null && kp.pos_y != null);
  if (withPos.length === 0) return false;
  const nearOriginCount = withPos.filter((kp) => Number(kp.pos_x) < 12000 && Number(kp.pos_y) < 12000).length;
  return nearOriginCount / withPos.length >= 0.5;
}

function normalizePersistedKpPositions(rows: KP[]) {
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
  const ids = renderedKpIds.value;
  return edges.value.filter((edge) => {
    if (!ids.has(edge.prereq_id) || !ids.has(edge.next_id)) return false;
    if (!props.fullscreen || fullscreenRelationFilter.value === "all") return true;
    return edge.relation_type === fullscreenRelationFilter.value;
  });
});

const teacherSearchMatchIds = computed(() => {
  const kw = search.value.trim().toLowerCase();
  if (!kw) return new Set<number>();
  return new Set(
    kps.value
      .filter((kp) => `${kp.code} ${kp.title} ${kp.description || ""} ${kp.chapter || ""}`.toLowerCase().includes(kw))
      .map((kp) => kp.id),
  );
});

function isTeacherSearchMatch(kp: KP) {
  return teacherSearchMatchIds.value.has(kp.id);
}

const viewportWorldBounds = computed(() => {
  const scale = canvasScale.value || 1;
  const buffer = Math.max(240, 180 / scale);
  return {
    minX: (0 - panX.value) / scale - buffer,
    maxX: (viewportWidth.value - panX.value) / scale + buffer,
    minY: (0 - panY.value) / scale - buffer,
    maxY: (viewportHeight.value - panY.value) / scale + buffer,
  };
});

function pointInsideViewport(point: Point, radius = 96) {
  const bounds = viewportWorldBounds.value;
  return (
    point.x + radius >= bounds.minX
    && point.x - radius <= bounds.maxX
    && point.y + radius >= bounds.minY
    && point.y - radius <= bounds.maxY
  );
}

function hasVisibleGraphNodeInViewport() {
  if (categoryNodes.value.some((item) => pointInsideViewport(categoryPoint(item.key), 150))) return true;
  if (showAllKps.value && visibleKps.value.some((kp) => pointInsideViewport(displayKpPoint(kp.id), nodeRadius(kp) + 48))) return true;
  return false;
}

const renderedKps = computed(() => {
  if (!showAllKps.value) return [];
  if (viewportWidth.value <= 0 || viewportHeight.value <= 0) return visibleKps.value;
  return visibleKps.value.filter((kp) => {
    if (kp.id === selectedId.value) return true;
    if (draggingNode.value?.type === "kp" && Number(draggingNode.value.id) === kp.id) return true;
    return pointInsideViewport(displayKpPoint(kp.id), nodeRadius(kp) + 48);
  });
});

const renderedKpIds = computed(() => new Set(renderedKps.value.map((kp) => kp.id)));
const renderedCategoryKpLines = computed(() => (showAllKps.value ? renderedKps.value : []));
const showDenseGraphDetails = computed(() => !draggingCanvas.value && !draggingNode.value && canvasScale.value >= 0.72 && renderedKps.value.length <= 90);

const kpById = computed(() => new Map(kps.value.map((kp) => [kp.id, kp])));

const readableLabelScale = computed(() => {
  const scale = canvasScale.value || 1;
  if (scale >= 0.9) return 1;
  return Math.min(4.2, Math.max(1, 0.88 / scale));
});

function shouldRenderNodeDetails(kp: KP) {
  return kp.id === selectedKp.value?.id || showDenseGraphDetails.value;
}

function shouldRenderNodeCode(kp: KP) {
  return kp.id === selectedKp.value?.id || canvasScale.value >= 0.48;
}

function shouldRenderCategoryMeta() {
  return canvasScale.value >= 0.48;
}

function readableLabelTransform() {
  return `scale(${readableLabelScale.value})`;
}

function compactTitle(value: string, limit: number) {
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}

function kpNodeTitle(kp: KP) {
  const limit = canvasScale.value < 0.38 && kp.id !== selectedKp.value?.id ? 8 : 10;
  return compactTitle(kp.title, limit);
}

function categoryNodeTitle(title: string) {
  const limit = canvasScale.value < 0.38 ? 10 : 14;
  return compactTitle(title, limit);
}

const selectedLayout = computed(() => {
  if (!selectedKp.value) return null;
  return displayKpPoint(selectedKp.value.id);
});

const selectedMenuStyle = computed(() => {
  if (!selectedLayout.value || !stageRef.value) return {};
  const stageWidth = stageRef.value.clientWidth || 0;
  const stageHeight = stageRef.value.clientHeight || 0;
  const nodeScreenX = selectedLayout.value.x * canvasScale.value + panX.value;
  const nodeScreenY = selectedLayout.value.y * canvasScale.value + panY.value;
  const left = Math.max(12, Math.min(stageWidth - 220, nodeScreenX + 14));
  const top = Math.max(12, Math.min(stageHeight - 90, nodeScreenY - 18));
  return { left: `${left}px`, top: `${top}px` };
});

const selectedMenuBelow = computed(() => {
  if (!selectedLayout.value || !stageRef.value) return false;
  const nodeScreenY = selectedLayout.value.y * canvasScale.value + panY.value;
  return nodeScreenY < 120;
});

function categoryPoint(key: string) {
  return categoryPositions.value[key] ?? defaultCategoryPositions.value[key] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
}

function sanitizeCategoryPositions(positions: Record<string, Point>) {
  const next: Record<string, Point> = {};
  for (const item of categoryNodes.value) {
    const fallback = defaultCategoryPositions.value[item.key] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
    const point = positions[item.key] ?? fallback;
    const x = Number(point.x);
    const y = Number(point.y);
    next[item.key] = {
      x: Number.isFinite(x) && x >= 0 && x <= CANVAS_WIDTH ? x : fallback.x,
      y: Number.isFinite(y) && y >= 0 && y <= CANVAS_HEIGHT ? y : fallback.y,
    };
  }

  const values = Object.values(next);
  if (values.length >= 2) {
    const minX = Math.min(...values.map((point) => point.x));
    const maxX = Math.max(...values.map((point) => point.x));
    const minY = Math.min(...values.map((point) => point.y));
    const maxY = Math.max(...values.map((point) => point.y));
    const chapterColumns = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(values.length * 1.35))));
    const chapterRows = Math.ceil(values.length / chapterColumns);
    const tooWide = maxX - minX > 5200 || maxY - minY > 3600;
    const tooCompact = values.length >= 5 && (maxX - minX < 1200 || (chapterRows > 1 && maxY - minY < 500));
    if (tooWide || tooCompact) {
      return { ...defaultCategoryPositions.value };
    }
  }

  return next;
}

function kpPoint(id: number) {
  return kpPositions.value[id] ?? defaultKpPositions.value[id] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y };
}

function focusedKpPoint(kp: KP) {
  const chapter = kp.chapter || "未分章";
  if (!showAllKps.value) return kpPoint(kp.id);
  if (draggingNode.value?.type === "kp" && Number(draggingNode.value.id) === kp.id) return kpPoint(kp.id);
  const persisted = kpPoint(kp.id);
  if (manualKpPositionIds.value.has(kp.id)) return persisted;
  const anchor = categoryPoint(chapter);
  const siblings = kps.value
    .filter((item) => (item.chapter || "未分章") === chapter)
    .sort((a, b) => String(a.code || "").localeCompare(String(b.code || ""), "zh-Hans-CN"));
  const index = Math.max(0, siblings.findIndex((item) => item.id === kp.id));
  const columns = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(siblings.length * 0.9))));
  const gapX = 290;
  const gapY = 216;
  const col = index % columns;
  const row = Math.floor(index / columns);
  return {
    x: anchor.x - ((columns - 1) * gapX) / 2 + col * gapX + (row % 2 === 0 ? 0 : 24),
    y: anchor.y + 220 + row * gapY,
  };
}

function displayKpPoint(id: number) {
  const kp = kpById.value.get(id);
  return kp ? focusedKpPoint(kp) : kpPoint(id);
}

function edgeLine(edge: Edge) {
  const from = displayKpPoint(edge.prereq_id);
  const to = displayKpPoint(edge.next_id);
  const fromKp = kpById.value.get(edge.prereq_id);
  const toKp = kpById.value.get(edge.next_id);
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

function categoryKpLine(kp: KP) {
  const from = categoryPoint(kp.chapter || "未分章");
  const to = displayKpPoint(kp.id);
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
    next[kp.id] = kpPositions.value[kp.id] ?? defaultKpPositions.value[kp.id];
  }
  kpPositions.value = next;
}

function nodeRadius(kp: KP) {
  const base = 62 + Math.round((kp.importance ?? 0.5) * 16);
  return kp.id === selectedKp.value?.id ? base + 10 : base;
}

function dimensionBadgeFill(level: "knowledge" | "ability" | "literacy", kp: KP) {
  if (level === "ability") {
    const label = splitLabels(kp.ability_tag)[0];
    return (label && abilityColorMap.value.get(label)) || "#24a36f";
  }
  if (level === "literacy") {
    const label = splitLabels(kp.literacy_tag)[0];
    return (label && literacyColorMap.value.get(label)) || "#d58b2a";
  }
  return "#3978d8";
}

function dimensionBadgeOpacity(level: "knowledge" | "ability" | "literacy", kp: KP) {
  if (level === "knowledge") return kp.knowledge_tag || kp.title ? 1 : 0.28;
  if (level === "ability") return splitLabels(kp.ability_tag).length ? 1 : 0.28;
  return splitLabels(kp.literacy_tag).length ? 1 : 0.28;
}

function edgeTouchesHover(edge: Edge) {
  const h = hoveredKpId.value;
  if (h == null) return false;
  return edge.prereq_id === h || edge.next_id === h;
}

function isCrossChapterEdge(edge: Edge) {
  const from = kpById.value.get(edge.prereq_id);
  const to = kpById.value.get(edge.next_id);
  if (!from || !to) return false;
  return (from.chapter || "未分章") !== (to.chapter || "未分章");
}

function edgeStroke(edge: Edge) {
  if (edgeTouchesHover(edge)) return "#355a28";
  if (isCrossChapterEdge(edge)) return "rgba(34, 105, 210, 0.78)";
  if (edge.relation_type === "support") return "rgba(71,176,137,0.62)";
  if (edge.relation_type === "contains") return "rgba(213,162,83,0.62)";
  if (edge.relation_type === "related") return "rgba(184,143,70,0.58)";
  return "rgba(103,121,154,0.6)";
}

function edgeDasharray(edge: Edge) {
  if (edge.relation_type === "support") return "10 6";
  if (edge.relation_type === "contains") return "2 6";
  return undefined;
}

function edgeWidth(edge: Edge) {
  if (edgeTouchesHover(edge)) return 3.2;
  if (isCrossChapterEdge(edge)) return 2.8;
  if (edge.relation_type === "contains") return 2.2;
  if (edge.relation_type === "support") return 2.1;
  return 1.6;
}

function edgeMarker(edge: Edge) {
  if (edge.relation_type === "related") return undefined;
  if (edge.relation_type === "support") return "url(#teacher-edge-arrow-triangle)";
  if (edge.relation_type === "contains") return "url(#teacher-edge-arrow-open)";
  return "url(#teacher-edge-arrow)";
}

function syncFormFromSelected() {
  if (!selectedKp.value) return;
  Object.assign(form, {
    id: selectedKp.value.id,
    code: selectedKp.value.code,
    title: selectedKp.value.title,
    description: selectedKp.value.description || "",
    chapter: selectedKp.value.chapter || "",
    knowledge_tag: selectedKp.value.knowledge_tag || "",
    ability_tag: selectedKp.value.ability_tag || "",
    literacy_tag: selectedKp.value.literacy_tag || "",
    importance: selectedKp.value.importance ?? 0.5,
    difficulty: selectedKp.value.difficulty ?? 0.5,
    is_terminal: Boolean(selectedKp.value.is_terminal),
  });
}

function resetCreateForm(chapter = "") {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (props.embedded || props.fullscreen) {
    openCreateWorkspaceInNewTab(chapter);
    return;
  }
  selectedType.value = "kp";
  selectedId.value = null;
  selectedCategory.value = null;
  graphEditorOpen.value = true;
  drawerOpen.value = true;
  Object.assign(form, {
    id: 0,
    code: "",
    title: "",
    description: "",
    chapter,
    knowledge_tag: "",
    ability_tag: "",
    literacy_tag: "",
    importance: 0.5,
    difficulty: 0.5,
    is_terminal: false,
  });
}

function selectKp(id: number) {
  if (linkSelectionMode.value && selectedId.value && id !== selectedId.value) {
    createEdgeFromCanvas(id);
    return;
  }
  categoryLinkMode.value = null;
  selectedType.value = "kp";
  selectedId.value = id;
  const chapter = selectedKp.value?.chapter || kps.value.find((kp) => kp.id === id)?.chapter || null;
  selectedCategory.value = chapter;
  if (!showAllKps.value) {
    showAllKps.value = true;
    activeChapter.value = chapter || activeChapter.value;
  } else if (activeChapter.value !== "全部" && chapter) {
    activeChapter.value = chapter;
  }
  drawerOpen.value = true;
  detailTab.value = "overview";
  syncFormFromSelected();
  centerOnPoint(displayKpPoint(id));
}

function selectCategory(chapter: string) {
  if (categoryLinkMode.value && selectedCategory.value && chapter !== selectedCategory.value) {
    createChapterEdge(selectedCategory.value, chapter);
    return;
  }
  selectedType.value = "category";
  selectedCategory.value = chapter;
  selectedId.value = null;
  graphEditorOpen.value = false;
  drawerOpen.value = !props.fullscreen;
  detailTab.value = "overview";
  const collapseCurrentChapter = graphExpansionMode.value === "chapter" && activeChapter.value === chapter;
  if (collapseCurrentChapter) {
    showAllKps.value = false;
    activeChapter.value = "全部";
    nextTick(() => {
      viewportFitRetryCount.value = 0;
      fitCategoryNodesToViewport();
    });
    return;
  }
  activeChapter.value = chapter;
  showAllKps.value = true;
  if (props.fullscreen || props.embedded) {
    search.value = "";
    showIncompleteOnly.value = false;
    fullscreenFocusFilter.value = "all";
  }
  nextTick(() => {
    viewportFitRetryCount.value = 0;
    if (visibleKps.value.length > 0) fitVisibleToViewport();
    else centerOnPoint(categoryPoint(chapter));
  });
}

function toggleAllKps() {
  const expandAll = graphExpansionMode.value !== "all";
  showAllKps.value = expandAll;
  if (expandAll) activeChapter.value = "全部";
  ElMessage.success(expandAll ? "已展开全部节点" : "已仅显示章节节点");
  nextTick(() => {
    fitViewportRetryCount = 0;
    if (expandAll) {
      fitVisibleToViewport();
      return;
    }
    fitCategoryNodesToViewport();
  });
}

function openGraphEditorForSelected() {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (!selectedKp.value) return;
  openContentWorkspaceInNewTab(selectedKp.value.id);
}

function openContentWorkspaceInNewTab(kpId: number) {
  if (!kpId) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  router.push({
    path: `/teacher/kp-content/${kpId}`,
    query: {
      subject: props.subject || undefined,
      grade: props.grade || undefined,
      mode: "edit",
      from: "graph-workspace",
    },
  });
}

function openContentFromSelected() {
  if (!selectedKp.value) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  openContentWorkspaceInNewTab(selectedKp.value.id);
}

function openCreateWorkspaceInNewTab(chapter = "") {
  router.push({
    path: "/teacher/kp-content/0",
    query: {
      subject: props.subject || undefined,
      grade: props.grade || undefined,
      chapter: chapter || undefined,
      mode: "create",
      from: "graph-workspace",
    },
  });
}

function startLinkSelection(modeValue: "forward" | "backward" | "related" | "support" | "contains") {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (!selectedKp.value) return;
  linkSelectionMode.value = modeValue;
  graphEditorOpen.value = false;
  ElMessage.info(
    modeValue === "forward"
      ? "请选择后继知识点"
      : modeValue === "backward"
        ? "请选择前置知识点"
        : modeValue === "support"
          ? "请选择能力支撑知识点"
          : modeValue === "contains"
            ? "请选择包含或归属知识点"
            : "请选择关联知识点",
  );
}

function cancelLinkSelection() {
  linkSelectionMode.value = null;
}

function startCategoryLinkSelection(modeValue: "prerequisite" | "related" | "support") {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (!selectedCategoryNode.value) return;
  categoryLinkMode.value = modeValue;
  ElMessage.info(
    modeValue === "prerequisite" ? "请选择后续分类节点" : modeValue === "support" ? "请选择支撑分类节点" : "请选择关联分类节点",
  );
}

function cancelCategoryLinkSelection() {
  categoryLinkMode.value = null;
}

function zoomIn() {
  zoomToScale(Math.min(MAX_CANVAS_SCALE, Number((canvasScale.value + SCALE_STEP).toFixed(2))));
}

function zoomOut() {
  zoomToScale(Math.max(MIN_CANVAS_SCALE, Number((canvasScale.value - SCALE_STEP).toFixed(2))));
}

function zoomToScale(nextScale: number) {
  if (!stageRef.value) {
    canvasScale.value = nextScale;
    return;
  }
  const centerX = stageRef.value.clientWidth / 2;
  const centerY = stageRef.value.clientHeight / 2;
  const worldX = (centerX - panX.value) / canvasScale.value;
  const worldY = (centerY - panY.value) / canvasScale.value;
  canvasScale.value = nextScale;
  panX.value = centerX - worldX * nextScale;
  panY.value = centerY - worldY * nextScale;
}

function resetViewport() {
  canvasScale.value = DEFAULT_CANVAS_SCALE;
  panX.value = 0;
  panY.value = 0;
  activeChapter.value = "全部";
  search.value = "";
  linkSelectionMode.value = null;
  categoryLinkMode.value = null;
  localStorage.removeItem(chapterPositionStorageKey());
  categoryPositions.value = { ...defaultCategoryPositions.value };
  syncCategoryPositions();
  syncKpPositions();
  nextTick(() => {
    viewportFitRetryCount.value = 0;
    fitStageToViewport();
  });
}

function arrangeGraphLayout() {
  localStorage.removeItem(chapterPositionStorageKey());
  localStorage.removeItem(manualKpPositionStorageKey());
  manualKpPositionIds.value = new Set();
  categoryPositions.value = { ...defaultCategoryPositions.value };
  kpPositions.value = { ...defaultKpPositions.value };
  activeChapter.value = "全部";
  search.value = "";
  showAllKps.value = true;
  syncCategoryPositions();
  syncKpPositions();
  ElMessage.success("已整理为规则图谱布局");
  nextTick(() => {
    viewportFitRetryCount.value = 0;
    fitVisibleToViewport();
  });
}

function scheduleViewportFit(next: "categories" | "visible") {
  if (viewportFitRetryCount.value >= 3) return;
  viewportFitRetryCount.value += 1;
  requestAnimationFrame(() => {
    if (next === "visible") fitVisibleToViewport();
    else fitCategoryNodesToViewport();
  });
}

function fitVisibleToViewport() {
  if (!stageRef.value) return;
  const sw = stageRef.value.clientWidth;
  const sh = stageRef.value.clientHeight;
  if (sw <= 0 || sh <= 0) {
    scheduleViewportFit("visible");
    return;
  }
  if (visibleKps.value.length === 0) {
    fitCategoryNodesToViewport();
    return;
  }
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const kp of visibleKps.value) {
    const p = displayKpPoint(kp.id);
    const r = nodeRadius(kp) + 28;
    minX = Math.min(minX, p.x - r);
    maxX = Math.max(maxX, p.x + r);
    minY = Math.min(minY, p.y - r);
    maxY = Math.max(maxY, p.y + r);

    const chapter = kp.chapter || "未分章";
    const category = categoryPoint(chapter);
    minX = Math.min(minX, category.x - 130);
    maxX = Math.max(maxX, category.x + 130);
    minY = Math.min(minY, category.y - 54);
    maxY = Math.max(maxY, category.y + 54);
  }
  const w = maxX - minX || 1;
  const h = maxY - minY || 1;
  const pad = 100;
  const scale = Math.min((sw - pad) / w, (sh - pad) / h, DEFAULT_CANVAS_SCALE);
  canvasScale.value = Math.max(MIN_CANVAS_SCALE, Math.min(MAX_CANVAS_SCALE, Number(scale.toFixed(4))));
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  panX.value = sw / 2 - cx * canvasScale.value;
  panY.value = sh / 2 - cy * canvasScale.value;
  persistViewState();
}

function fitCategoryNodesToViewport() {
  if (!stageRef.value || categoryNodes.value.length === 0) return;
  categoryPositions.value = sanitizeCategoryPositions(categoryPositions.value);
  const sw = stageRef.value.clientWidth;
  const sh = stageRef.value.clientHeight;
  if (sw <= 0 || sh <= 0) {
    scheduleViewportFit("categories");
    return;
  }
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const item of categoryNodes.value) {
    const p = categoryPoint(item.key);
    const halfW = 130;
    const halfH = 54;
    minX = Math.min(minX, p.x - halfW);
    maxX = Math.max(maxX, p.x + halfW);
    minY = Math.min(minY, p.y - halfH);
    maxY = Math.max(maxY, p.y + halfH);
  }
  const w = maxX - minX || 1;
  const h = maxY - minY || 1;
  const pad = 100;
  const scale = Math.min((sw - pad) / w, (sh - pad) / h, DEFAULT_CANVAS_SCALE);
  canvasScale.value = Math.max(MIN_CANVAS_SCALE, Math.min(MAX_CANVAS_SCALE, Number(scale.toFixed(4))));
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  panX.value = sw / 2 - cx * canvasScale.value;
  panY.value = sh / 2 - cy * canvasScale.value;
  persistViewState();
}

function clampPan(nextX = panX.value, nextY = panY.value) {
  panX.value = nextX;
  panY.value = nextY;
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
  // 双指滚动作为画布平移，体验接近无限画布
  panX.value -= event.deltaX;
  panY.value -= event.deltaY;
}

function onStageMouseDown(event: MouseEvent) {
  const target = event.target as HTMLElement | null;
  if (target?.closest(".teacher-node") || target?.closest(".teacher-category-node")) return;
  draggingCanvas.value = true;
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
  dragOriginX.value = panX.value;
  dragOriginY.value = panY.value;
}

function onNodeMouseDown(event: MouseEvent, type: "kp" | "category", id: number | string) {
  event.stopPropagation();
  const origin = type === "kp" ? displayKpPoint(Number(id)) : categoryPoint(String(id));
  draggingNode.value = { type, id, origin };
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
}

function onWindowMouseMove(event: MouseEvent) {
  if (draggingNode.value) {
    const dx = (event.clientX - dragStartX.value) / canvasScale.value;
    const dy = (event.clientY - dragStartY.value) / canvasScale.value;

    if (draggingNode.value.type === "kp") {
      const kpId = Number(draggingNode.value.id);
      markKpPositionManual(kpId);
      const current = kps.value.find((kp) => kp.id === kpId);
      const radius = (current ? nodeRadius(current) : 80) + 18;
      const newX = Math.max(radius, Math.min(CANVAS_WIDTH - radius, draggingNode.value.origin.x + dx));
      const newY = Math.max(radius, Math.min(CANVAS_HEIGHT - radius, draggingNode.value.origin.y + dy));

      kpPositions.value = {
        ...kpPositions.value,
        [kpId]: {
          x: newX,
          y: newY,
        },
      };
    } else {
      const halfWidth = 112;
      const halfHeight = 44;
      const newX = Math.max(halfWidth, Math.min(CANVAS_WIDTH - halfWidth, draggingNode.value.origin.x + dx));
      const newY = Math.max(halfHeight, Math.min(CANVAS_HEIGHT - halfHeight, draggingNode.value.origin.y + dy));

      categoryPositions.value = {
        ...categoryPositions.value,
        [String(draggingNode.value.id)]: {
          x: newX,
          y: newY,
        },
      };
    }
    return;
  }
  if (!draggingCanvas.value) return;
  clampPan(
    dragOriginX.value + (event.clientX - dragStartX.value),
    dragOriginY.value + (event.clientY - dragStartY.value),
  );
}

async function stopDragging() {
  if (props.readonly) {
    draggingCanvas.value = false;
    draggingNode.value = null;
    return;
  }
  if (draggingNode.value?.type === "kp" && draggingNode.value.id) {
    const kpId = Number(draggingNode.value.id);
    const point = kpPositions.value[kpId];
    if (kpId && point) {
      try {
        await api.put(`/admin/kps/${kpId}/position`, { x: point.x, y: point.y });
        saveManualKpPositionIds();
      } catch {
        ElMessage.warning("节点位置保存失败，请重试");
      }
    }
  }
  if (draggingNode.value?.type === "category") {
    localStorage.setItem(chapterPositionStorageKey(), JSON.stringify(categoryPositions.value));
    if (props.subject) {
      try {
        await api.put("/admin/graph/chapter-layout", {
          subject: props.subject,
          grade: props.grade,
          chapters: categoryPositions.value,
        });
      } catch (error) {
        console.warn("Chapter layout sync failed; using local cache fallback.", error);
      }
    }
  }
  draggingCanvas.value = false;
  draggingNode.value = null;
}

function kpCoverageWarnLabels(kpId: number): string[] {
  const c = kpCoverageMap.value[kpId];
  if (!c) return [];
  const out: string[] = [];
  if (!c.resource_count) out.push("缺资源");
  if (!c.question_count) out.push("缺题");
  return out;
}

async function exportGraphStructure(format: "json" | "csv") {
  if (!props.subject) return;
  try {
    const res = await api.get(
      `/admin/graph/export?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&format=${format}`,
      { responseType: "blob" },
    );
    const blob = new Blob([res.data], {
      type: format === "json" ? "application/json" : "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ext = format === "json" ? "json" : "csv";
    a.download = `知识图谱-${props.subject}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("图谱已导出");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导出失败");
  }
}

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    loadManualKpPositionIds();
    const viewRestored = !props.fullscreen && !props.embedded && restoreViewState();
    const [kpRes, edgeRes, chapterEdgeRes, covRes, layoutRes] = await Promise.all([
      api.get(`/graph/kps?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
      api.get(`/admin/edges?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&page=1&page_size=500`),
      api.get(`/admin/chapter-edges?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
      api.get(
        `/admin/graph/kp-coverage?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`,
      ),
      api.get(`/graph/chapter-layout?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
    ]);
    kps.value = kpRes.data ?? [];
    edges.value = edgeRes.data.items ?? [];
    chapterEdges.value = chapterEdgeRes.data ?? [];
    syncManualKpPositionIdsFromRows(kps.value);
    const nextCov: Record<number, { resource_count: number; question_count: number; task_count: number; has_quiz: boolean }> = {};
    for (const row of covRes.data?.items ?? []) {
      nextCov[row.kp_id] = {
        resource_count: Number(row.resource_count ?? 0),
        question_count: Number(row.question_count ?? 0),
        task_count: Number(row.task_count ?? 0),
        has_quiz: Boolean(row.has_quiz),
      };
    }
    kpCoverageMap.value = nextCov;

    const normalizedPersisted = normalizePersistedKpPositions(kps.value);
    if (useLegacyFallbackLayout.value) {
      console.info("Detected legacy graph coordinates; using separated graph layout fallback.");
    }
    kpPositions.value = normalizedPersisted;

    const det = buildDeterministicGraphLayout(
      kps.value.map((kp) => ({ id: kp.id, code: kp.code, chapter: kp.chapter })),
    );
    const serverChapters = (layoutRes.data?.chapters ?? {}) as Record<string, { x: number; y: number }>;
    let mergedCat = mergeChapterLayout(det.categoryPositions, serverChapters);
    try {
      const raw = localStorage.getItem(chapterPositionStorageKey());
      const parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === "object") {
        const next: Record<string, Point> = {};
        for (const [key, point] of Object.entries(parsed)) {
          const x = Number((point as any)?.x);
          const y = Number((point as any)?.y);
          if (Number.isFinite(x) && Number.isFinite(y)) {
            next[key] = { x, y };
          }
        }
        mergedCat = mergeChapterLayout(mergedCat, next);
      }
    } catch {
      // ignore invalid local cache
    }
    categoryPositions.value = sanitizeCategoryPositions(mergedCat);
    syncCategoryPositions();
    syncKpPositions();
    if (props.fullscreen && !viewRestored) {
      canvasScale.value = DEFAULT_CANVAS_SCALE;
      panX.value = 0;
      panY.value = 0;
      activeChapter.value = "全部";
      search.value = "";
      selectedType.value = "category";
      selectedId.value = null;
      selectedCategory.value = categoryNodes.value[0]?.key || null;
      drawerOpen.value = false;
      detailTab.value = "overview";
    }
    const normalizedChanged = normalizeWorkbenchSelectionState();
    if (normalizedChanged) {
      if (selectedType.value === "kp" && selectedId.value) centerOnPoint(displayKpPoint(selectedId.value));
      else if (selectedCategory.value) centerOnPoint(categoryPoint(selectedCategory.value));
    }
    nextTick(() => {
      viewportFitRetryCount.value = 0;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (props.fullscreen) {
            if (showAllKps.value && visibleKps.value.length > 0) fitVisibleToViewport();
            else fitCategoryNodesToViewport();
          } else if (!hasVisibleGraphNodeInViewport()) {
            fitStageToViewport();
          } else {
            fitVisibleToViewport();
          }
        });
      });
    });
    persistViewState();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师图谱失败");
  } finally {
    loading.value = false;
  }
}

defineExpose({
  reloadGraph: load,
  fitGraph: fitStageToViewport,
  resetGraphViewport: resetViewport,
});

async function saveKp() {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (!props.subject) return;
  saving.value = true;
  try {
    if (form.id) {
      const point = kpPoint(form.id);
      await api.put(`/admin/kps/${form.id}`, {
        code: form.code,
        title: form.title,
        description: form.description,
        chapter: form.chapter,
        knowledge_tag: form.knowledge_tag,
        ability_tag: form.ability_tag,
        literacy_tag: form.literacy_tag,
        importance: form.importance,
        difficulty: form.difficulty,
        is_terminal: form.is_terminal,
        pos_x: point.x,
        pos_y: point.y,
      });
      ElMessage.success("知识点已更新");
    } else {
      const draft = deterministicDraftPosition(`${form.code}|${form.title}`);
      await api.post("/admin/kps", {
        subject: props.subject,
        grade: props.grade,
        code: form.code,
        title: form.title,
        description: form.description,
        chapter: form.chapter,
        knowledge_tag: form.knowledge_tag,
        ability_tag: form.ability_tag,
        literacy_tag: form.literacy_tag,
        importance: form.importance,
        difficulty: form.difficulty,
        is_terminal: form.is_terminal,
        pos_x: draft.x,
        pos_y: draft.y,
      });
      ElMessage.success("知识点已创建");
    }
    graphEditorOpen.value = false;
    await load();
    if (!form.id && kps.value.length) {
      const created = kps.value.find((item) => item.code === form.code && item.title === form.title);
      if (created) selectKp(created.id);
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存知识点失败");
  } finally {
    saving.value = false;
  }
}

async function removeKp() {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (!selectedId.value) return;
  try {
    await api.delete(`/admin/kps/${selectedId.value}`);
    ElMessage.success("知识点已删除");
    selectedId.value = null;
    graphEditorOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除失败，可能还有边或资源引用");
  }
}

async function createEdgeFromCanvas(targetId: number) {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (!selectedId.value || !linkSelectionMode.value) return;
  let prereqId = selectedId.value;
  let nextId = targetId;
  let relationType = "prerequisite";
  if (linkSelectionMode.value === "backward") {
    prereqId = targetId;
    nextId = selectedId.value;
  } else if (linkSelectionMode.value === "support") {
    relationType = "support";
  } else if (linkSelectionMode.value === "contains") {
    relationType = "contains";
  } else if (linkSelectionMode.value === "related") {
    relationType = "related";
  }

  try {
    await api.post("/admin/edges", {
      subject: props.subject,
      grade: props.grade,
      prereq_id: prereqId,
      next_id: nextId,
      relation_type: relationType,
    });
    ElMessage.success("知识边已添加");
    linkSelectionMode.value = null;
    await load();
    selectedType.value = "kp";
    selectedId.value = targetId;
    syncFormFromSelected();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "添加知识边失败");
  }
}

async function createChapterEdge(sourceChapter: string, targetChapter: string) {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  try {
    await api.post("/admin/chapter-edges", {
      subject: props.subject,
      grade: props.grade,
      source_chapter: sourceChapter,
      target_chapter: targetChapter,
      relation_type: categoryLinkMode.value || "related",
    });
    categoryLinkMode.value = null;
    ElMessage.success("分类关系已添加");
    await load();
    selectedType.value = "category";
    selectedCategory.value = targetChapter;
    selectedId.value = null;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "添加分类关系失败");
  }
}

async function deleteChapterEdge(edgeId: number) {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  try {
    await api.delete(`/admin/chapter-edges/${edgeId}`);
    ElMessage.success("分类关系已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除分类关系失败");
  }
}

async function deleteEdge(edge: Edge) {
  if (props.readonly) {
    ElMessage.warning("当前课程已归档，图谱只读");
    return;
  }
  if (!selectedKp.value || (edge.prereq_id !== selectedKp.value.id && edge.next_id !== selectedKp.value.id)) {
    ElMessage.warning("这里只能删除当前选中节点的直接关系");
    return;
  }
  try {
    await api.delete(`/admin/edges/${edge.id}`);
    ElMessage.success("知识边已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除知识边失败");
  }
}

function edgeLabel(edge: Edge) {
  if (edge.relation_type === "related") return "关联";
  if (edge.relation_type === "support") return "支撑";
  if (edge.relation_type === "contains") return "包含";
  return "前置";
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

watch(
  () => [props.subject, props.grade],
  () => {
    stopDragging();
    mutingViewStatePersist.value = true;
    linkSelectionMode.value = null;
    categoryLinkMode.value = null;
    graphEditorOpen.value = false;
    selectedId.value = null;
    selectedCategory.value = null;
    const restored = !props.fullscreen && !props.embedded && restoreViewState();
    if (!restored || props.fullscreen) {
      canvasScale.value = DEFAULT_CANVAS_SCALE;
      panX.value = 0;
      panY.value = 0;
      activeChapter.value = "全部";
      search.value = "";
      showAllKps.value = false;
      selectedType.value = "kp";
      drawerOpen.value = !props.fullscreen;
      detailTab.value = "overview";
    }
    mutingViewStatePersist.value = false;
    load();
  },
  { immediate: true },
);

watch(visibleKps, () => {
  syncCategoryPositions();
  syncKpPositions();
  normalizeWorkbenchSelectionState();
});

watch(stageRef, (value) => {
  connectStageResizeObserver(value);
}, { flush: "post" });

watch(
  [kps, categoryNodes, visibleKps, selectedType, selectedId, selectedCategory],
  () => {
    emitState();
  },
  { immediate: true },
);

watch(
  [canvasScale, panX, panY, activeChapter, search, showAllKps, selectedType, selectedId, selectedCategory, drawerOpen, detailTab],
  () => {
    persistViewState();
  },
);

window.addEventListener("mousemove", onWindowMouseMove);
window.addEventListener("mouseup", stopDragging);

onBeforeUnmount(() => {
  disconnectStageResizeObserver();
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", stopDragging);
});
</script>

<template>
  <div
    class="teacher-workbench"
    :class="{
      'teacher-workbench--fullscreen': props.fullscreen,
      'teacher-workbench--embedded': props.embedded,
    }"
    v-loading="loading"
  >
    <div v-if="!props.embedded" class="teacher-header">
      <div class="teacher-heading">
        <h1 class="teacher-title">知识图谱建设</h1>
        <p class="teacher-subtitle">先找分类，再选知识点，然后补信息、连关系、进内容页。</p>
      </div>
      <div class="teacher-controls">
        <QueryToolbar
          v-model="search"
          placeholder="请输入知识点名称、编码或章节"
          hint="请输入知识点名称、编码或章节"
          input-width="420px"
          @search="runTeacherSearch"
          @reset="resetTeacherSearch"
        />
        <el-checkbox v-model="showIncompleteOnly" size="small" border title="仅显示缺资源或缺题的知识点">仅待完善</el-checkbox>
        <el-dropdown trigger="click">
          <button type="button" class="teacher-btn">导出 ▾</button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="exportGraphStructure('json')">导出 JSON</el-dropdown-item>
              <el-dropdown-item @click="exportGraphStructure('csv')">导出 CSV</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button
          class="teacher-btn teacher-btn--primary"
          @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)"
        >
          新建知识点
        </button>
        <button class="teacher-btn" @click="resetViewport">重置视图</button>
        <button v-if="!props.fullscreen" class="teacher-btn teacher-btn--primary" @click="drawerOpen = !drawerOpen">
          {{ drawerVisible ? "收起右侧" : "打开右侧" }}
        </button>
      </div>
    </div>

    <div v-if="!props.embedded && !props.fullscreen" class="teacher-guide">
      <span>查看提示</span>
      <HoverTip content="先找分类，再点节点，最后改内容或连关系。" />
    </div>

    <div
      class="teacher-content"
      :class="{
        'teacher-content--fullscreen': props.fullscreen,
        'teacher-content--drawer-collapsed': !drawerVisible,
      }"
    >
      <aside v-if="showSidebar" class="teacher-sidebar">
        <div class="teacher-tree">
          <div class="teacher-tree__intro">
            <strong>先选分类或知识点</strong>
            <span>左边负责定位，中间负责看结构，右边负责改内容。</span>
          </div>
          <button
            class="teacher-tree__create"
            @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)"
          >
            新建知识点
          </button>
          <div v-if="treeNodes.length === 0" class="teacher-tree__empty">
            <strong>左边现在没有可选内容</strong>
            <span>可以先清空搜索词，或先新建一个知识点。</span>
          </div>
          <div v-for="item in treeNodes" :key="item.key" class="teacher-tree__group">
            <div class="teacher-tree__summary" :class="{ active: activeChapter === item.key }" @click="selectCategory(item.key)">
              <span>{{ item.title }}</span>
              <span class="teacher-tree__count">{{ item.children.length }}</span>
            </div>
            <div class="teacher-tree__children" v-if="activeChapter === item.key || activeChapter === '全部'">
              <button
                v-for="kp in item.children"
                :key="kp.id"
                class="teacher-tree__child"
                :class="{ active: kp.id === selectedKp?.id }"
                @click="selectKp(kp.id)"
              >
                <span>{{ kp.title }}</span>
                <small>{{ kp.code }}</small>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <aside v-if="props.fullscreen" class="teacher-fullscreen-nav">
        <div class="teacher-fullscreen-nav__tabs">
          <span class="active">导航</span>
        </div>
        <div class="teacher-fullscreen-nav__search">
          <span class="teacher-fullscreen-nav__search-icon">⌕</span>
          <input
            v-model="search"
            type="search"
            placeholder="检索分类或知识点"
            @keydown.enter.prevent="runTeacherSearch"
          />
          <button v-if="search" type="button" @click="resetTeacherSearch">清空</button>
        </div>
        <div class="teacher-fullscreen-nav__tree">
          <div v-for="item in treeNodes" :key="item.key" class="teacher-fullscreen-nav__group">
            <button
              type="button"
              class="teacher-fullscreen-nav__item"
              :class="{ active: selectedCategory === item.key }"
              @click="selectCategory(item.key)"
            >
              <span class="teacher-fullscreen-nav__arrow">{{ selectedCategory === item.key && showAllKps ? "▾" : "▸" }}</span>
              <span class="teacher-fullscreen-nav__name">{{ item.title }}</span>
              <span class="teacher-fullscreen-nav__count">{{ item.children.length }}</span>
            </button>
            <div v-if="selectedCategory === item.key && showAllKps" class="teacher-fullscreen-nav__children">
              <button
                v-for="kp in item.children"
                :key="kp.id"
                type="button"
                class="teacher-fullscreen-nav__child"
                :class="{ active: kp.id === selectedKp?.id, match: isTeacherSearchMatch(kp) }"
                @click.stop="selectKp(kp.id)"
              >
                <span>{{ kp.title }}</span>
                <small>{{ kp.code }}</small>
              </button>
            </div>
          </div>
        </div>
      </aside>

    <section
      class="teacher-stage"
      :class="{ 'teacher-stage--dragging': draggingCanvas }"
    >
      <div class="teacher-stage__top">
        <div class="teacher-stage__top-row">
          <div class="teacher-stage__stats">
            <span class="teacher-stage__pill">分类 {{ stageStats.categories }}</span>
            <span class="teacher-stage__pill">知识点 {{ stageStats.points }}</span>
            <span class="teacher-stage__pill">关系 {{ stageStats.edges }}</span>
          </div>
        <div class="teacher-stage__actions">
          <button class="teacher-stage__button" @click="toggleAllKps">
            {{ expansionToggleLabel }}
          </button>
          <button class="teacher-stage__button teacher-stage__button--primary" :disabled="props.readonly" @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)">新增知识点</button>
          <button v-if="props.embedded && !props.fullscreen" class="teacher-stage__button" @click="emit('open-fullscreen')">全屏图谱</button>
          <button class="teacher-stage__button" @click="arrangeGraphLayout">整理布局</button>
          <button class="teacher-stage__button" @click="fitVisibleToViewport">适应画布</button>
          <button class="teacher-stage__button" @click="resetViewport">重置画布</button>
          <button v-if="inlineEditorEnabled" class="teacher-stage__button" @click="detailTab = 'relations'; drawerOpen = true">管理当前关系</button>
        </div>
      </div>
        <div v-if="!props.fullscreen" class="teacher-stage__focus">
          <button
            v-if="selectedType === 'kp' && selectedKp"
            class="teacher-stage__focus-btn teacher-stage__focus-btn--primary"
            @click.stop="openContentFromSelected"
          >
            打开知识点配置页
          </button>
        </div>
        <details class="teacher-stage__legend-details">
          <summary class="teacher-stage__legend-summary">连线与图例说明（默认收起，点击展开）</summary>
          <div class="teacher-stage__legend">
            <span class="teacher-stage__legend-item">
              <i class="teacher-stage__legend-line teacher-stage__legend-line--solid"></i>
              实线箭头：前置 / 顺序关系
            </span>
            <span class="teacher-stage__legend-item">
              <i class="teacher-stage__legend-line teacher-stage__legend-line--chapter"></i>
              虚线 / 三角箭头：支撑、包含、分类关系
            </span>
            <span class="teacher-stage__legend-item">
              <i class="teacher-stage__legend-line teacher-stage__legend-line--attach"></i>
              细虚线：分类与知识点归属，同色环表示同类能力/素养
            </span>
            <span class="teacher-stage__legend-item">
              <i class="teacher-stage__legend-dimensions">
                <span class="td td--knowledge">知</span>
                <span class="td td--ability">能</span>
                <span class="td td--literacy">素</span>
              </i>
              节点徽标：知识 / 能力 / 素养；置灰表示该维度未配置，能力/素养同标签同色
            </span>
          </div>
        </details>
      </div>

      <!-- 视口用 flex 占满剩余高度；ref 挂在视口上，缩放/平移与可见区域一致 -->
      <div
        ref="stageRef"
        class="teacher-stage__viewport"
        @mousedown="onStageMouseDown"
        @wheel.prevent="onStageWheel"
      >
      <svg
        class="teacher-canvas"
        width="100%"
        height="100%"
      >
        <defs>
          <marker id="teacher-edge-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(103,121,154,0.58)" />
          </marker>
          <marker id="teacher-edge-arrow-triangle" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M 1 1 L 9 5 L 1 9 z" fill="#47b089" />
          </marker>
          <marker id="teacher-edge-arrow-open" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M 1 1 L 9 5 L 1 9" fill="none" stroke="#d5a253" stroke-width="1.5" />
          </marker>
          <marker id="teacher-chapter-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(103,121,154,0.5)" />
          </marker>
        </defs>
        <g :transform="`translate(${panX} ${panY})`">
          <g :transform="`scale(${canvasScale})`">
          <line
            v-for="edge in visibleChapterEdges"
            :key="`chapter-${edge.id}`"
            :x1="categoryPoint(edge.source_chapter).x"
            :y1="categoryPoint(edge.source_chapter).y"
            :x2="categoryPoint(edge.target_chapter).x"
            :y2="categoryPoint(edge.target_chapter).y"
            :stroke="edge.relation_type === 'support' ? 'rgba(71,176,137,0.46)' : (edge.relation_type === 'related' ? 'rgba(184,143,70,0.34)' : 'rgba(103,121,154,0.42)')"
            stroke-width="2.2"
            stroke-dasharray="6 6"
            :marker-end="edge.relation_type === 'related' ? undefined : 'url(#teacher-chapter-arrow)'"
          />

          <line
            v-for="edge in visibleEdges"
            :key="`${edge.id}-${edge.relation_type}`"
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
            v-for="kp in renderedCategoryKpLines"
            :key="`cat-${kp.id}`"
            :x1="categoryKpLine(kp).x1"
            :y1="categoryKpLine(kp).y1"
            :x2="categoryKpLine(kp).x2"
            :y2="categoryKpLine(kp).y2"
            stroke="rgba(103, 121, 154, 0.48)"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-dasharray="4 5"
          />

          <g
            v-for="category in categoryNodes"
            :key="category.key"
            class="teacher-category-node"
            :transform="`translate(${categoryPoint(category.key).x}, ${categoryPoint(category.key).y})`"
            @click="selectCategory(category.key)"
            @mousedown="onNodeMouseDown($event, 'category', category.key)"
          >
            <rect x="-112" y="-44" width="224" height="88" rx="20" :fill="selectedCategory === category.key ? '#eef8ff' : '#ffffff'" :stroke="selectedCategory === category.key ? '#93c5fd' : '#d8e5f6'" stroke-width="2" />
            <g class="teacher-category-node__label" :transform="readableLabelTransform()">
              <text class="teacher-category-node__title" text-anchor="middle" :y="shouldRenderCategoryMeta() ? -6 : 5">{{ categoryNodeTitle(category.title) }}</text>
              <text v-if="shouldRenderCategoryMeta()" class="teacher-category-node__meta" text-anchor="middle" y="22">{{ category.total }} 个知识点</text>
            </g>
          </g>

          <g
            v-for="kp in renderedKps"
            :key="kp.id"
            :class="['teacher-node', { 'teacher-node--search-match': isTeacherSearchMatch(kp) }]"
            :transform="`translate(${displayKpPoint(kp.id).x}, ${displayKpPoint(kp.id).y})`"
            @click="selectKp(kp.id)"
            @mousedown="onNodeMouseDown($event, 'kp', kp.id)"
            @mouseenter="hoveredKpId = kp.id"
            @mouseleave="hoveredKpId = null"
          >
            <circle :r="nodeRadius(kp) + 22" :fill="isTeacherSearchMatch(kp) ? 'rgba(245, 158, 11, 0.2)' : (kp.id === selectedKp?.id ? 'rgba(147, 197, 253, 0.22)' : 'rgba(219, 234, 254, 0.16)')" />
            <circle :r="nodeRadius(kp)" :fill="kp.id === selectedKp?.id ? '#eef8ff' : (isTeacherSearchMatch(kp) ? '#fff7ed' : '#ffffff')" :stroke="isTeacherSearchMatch(kp) ? '#f59e0b' : (kp.id === selectedKp?.id ? '#93c5fd' : '#d8e5f6')" :stroke-width="isTeacherSearchMatch(kp) ? 3 : 2" />
            <g v-if="shouldRenderNodeDetails(kp)" class="teacher-node__dimensions" :transform="`translate(0, ${-nodeRadius(kp) - 28})`">
              <g transform="translate(-38, 0)">
                <rect x="-13" y="-10" width="26" height="20" rx="10" :fill="dimensionBadgeFill('knowledge', kp)" :opacity="dimensionBadgeOpacity('knowledge', kp)" stroke="rgba(15, 23, 42, 0.2)" stroke-width="1.2" />
                <text class="teacher-node__dimension-label" text-anchor="middle" y="5">知</text>
              </g>
              <g transform="translate(0, 0)">
                <rect x="-13" y="-10" width="26" height="20" rx="10" :fill="dimensionBadgeFill('ability', kp)" :opacity="dimensionBadgeOpacity('ability', kp)" stroke="rgba(15, 23, 42, 0.2)" stroke-width="1.2" />
                <text class="teacher-node__dimension-label" text-anchor="middle" y="5">能</text>
              </g>
              <g transform="translate(38, 0)">
                <rect x="-13" y="-10" width="26" height="20" rx="10" :fill="dimensionBadgeFill('literacy', kp)" :opacity="dimensionBadgeOpacity('literacy', kp)" stroke="rgba(15, 23, 42, 0.2)" stroke-width="1.2" />
                <text class="teacher-node__dimension-label" text-anchor="middle" y="5">素</text>
              </g>
            </g>
            <g class="teacher-node__label" :transform="readableLabelTransform()">
              <text v-if="shouldRenderNodeCode(kp)" class="teacher-node__code" text-anchor="middle" y="-8">{{ kp.code }}</text>
              <text class="teacher-node__title" text-anchor="middle" :y="shouldRenderNodeCode(kp) ? 16 : 5">{{ kpNodeTitle(kp) }}</text>
            </g>
            <g v-if="shouldRenderNodeDetails(kp) && kpCoverageWarnLabels(kp.id).length" :transform="`translate(0, ${nodeRadius(kp) + 16})`">
              <text class="teacher-node__warn" text-anchor="middle" y="0">{{ kpCoverageWarnLabels(kp.id).join(" · ") }}</text>
            </g>
          </g>
          </g>
        </g>
      </svg>

      <div v-if="props.fullscreen && selectedKp" class="teacher-stage__selected-action">
        <div>
          <strong>{{ selectedKp.title }}</strong>
          <span>{{ selectedKp.code }}</span>
        </div>
        <button :disabled="props.readonly" @click.stop="openContentFromSelected">编辑知识点</button>
      </div>

      <div
        v-if="selectedKp && selectedLayout"
        class="teacher-stage__menu"
        :class="{ 'teacher-stage__menu--below': selectedMenuBelow }"
        :style="selectedMenuStyle"
      >
          <button :disabled="props.readonly" @click="openGraphEditorForSelected">编辑基础信息</button>
          <button @click="openContentFromSelected">打开知识点配置页</button>
        <button class="danger" :disabled="props.readonly" @click="removeKp">删除</button>
      </div>

      <div v-if="!props.fullscreen && linkSelectionMode" class="teacher-stage__hint">
        <span>
          {{
            linkSelectionMode === 'forward'
              ? '正在添加后续知识点，请再点一个节点。'
              : linkSelectionMode === 'backward'
                ? '正在添加前置知识点，请再点一个节点。'
                : linkSelectionMode === 'support'
                  ? '正在添加支撑关系，请再点一个节点。'
                  : linkSelectionMode === 'contains'
                    ? '正在添加包含关系，请再点一个节点。'
                    : '正在添加关联关系，请再点一个节点。'
          }}
        </span>
        <button @click="cancelLinkSelection">取消</button>
      </div>

      <div v-if="!props.fullscreen && categoryLinkMode" class="teacher-stage__hint teacher-stage__hint--chapter">
        <span>
          {{ categoryLinkMode === 'prerequisite' ? '正在给分类添加前后顺序，请再点一个分类。' : categoryLinkMode === 'support' ? '正在给分类添加支撑关系，请再点一个分类。' : '正在给分类添加关联关系，请再点一个分类。' }}
        </span>
        <button @click="cancelCategoryLinkSelection">取消</button>
      </div>

      <div class="teacher-stage__bottom">
        <div v-if="props.fullscreen" class="teacher-stage__fullscreen-filters">
          <div class="teacher-stage__filter-group teacher-stage__filter-group--expand">
            <button class="teacher-stage__filter-action" @click="toggleAllKps">{{ expansionToggleLabel }}</button>
          </div>
          <div class="teacher-stage__filter-group">
            <button :class="{ active: fullscreenRelationFilter === 'all' }" @click="fullscreenRelationFilter = 'all'">全部关系</button>
            <button :class="{ active: fullscreenRelationFilter === 'prerequisite' }" @click="fullscreenRelationFilter = 'prerequisite'">前后关系</button>
            <button :class="{ active: fullscreenRelationFilter === 'related' }" @click="fullscreenRelationFilter = 'related'">关联关系</button>
            <button :class="{ active: fullscreenRelationFilter === 'support' }" @click="fullscreenRelationFilter = 'support'">支撑关系</button>
            <button :class="{ active: fullscreenRelationFilter === 'contains' }" @click="fullscreenRelationFilter = 'contains'">父子关系</button>
          </div>
          <div class="teacher-stage__filter-group teacher-stage__filter-group--focus">
            <button :class="{ active: fullscreenFocusFilter === 'all' }" @click="fullscreenFocusFilter = 'all'">全部</button>
            <button :class="{ active: fullscreenFocusFilter === 'important' }" @click="fullscreenFocusFilter = 'important'">重点</button>
            <button :class="{ active: fullscreenFocusFilter === 'difficult' }" @click="fullscreenFocusFilter = 'difficult'">难点</button>
            <button :class="{ active: fullscreenFocusFilter === 'incomplete' }" @click="fullscreenFocusFilter = 'incomplete'">待完善</button>
          </div>
        </div>
        <div class="teacher-stage__zoom">
          <button @click="zoomOut">-</button>
          <span>缩放 {{ Math.round(canvasScale * 100) }}%</span>
          <button @click="zoomIn">+</button>
        </div>
      </div>

      <div v-if="!loading && !hasGraphData" class="teacher-stage__empty">
        <strong>这门课还没有知识图谱</strong>
        <span>请先新建知识点，再把它们连起来。</span>
        <button
          class="teacher-stage__empty-btn"
          @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)"
        >
          立即新建知识点
        </button>
      </div>

      <div v-else-if="!loading && showAllKps && visibleKps.length === 0" class="teacher-stage__empty">
        <strong>{{ showAllKps ? "当前没有可显示的知识点" : "当前仅显示章节节点" }}</strong>
        <span>
          {{
            showAllKps
              ? "当前处于全部节点模式，但没有可渲染的圆形知识点。"
              : "已隐藏圆形知识点，点击上方“展开全部节点”可查看完整图谱。"
          }}
        </span>
        <div class="teacher-stage__empty-actions">
          <button class="teacher-stage__empty-btn" @click="toggleAllKps">
            {{ expansionToggleLabel }}
          </button>
          <button
            v-if="!props.readonly"
            class="teacher-stage__empty-btn teacher-stage__empty-btn--ghost"
            @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)"
          >
            新建知识点
          </button>
        </div>
      </div>
      </div>

    </section>

    <aside v-if="drawerVisible && inlineEditorEnabled" class="teacher-drawer" :class="{ open: drawerOpen }">
      <div class="teacher-drawer__header">
        <h3 class="teacher-drawer__title">{{ drawerTitle }}</h3>
        <button class="teacher-drawer__close" @click="drawerOpen = false">×</button>
      </div>

      <div class="teacher-drawer__content">
        <template v-if="graphEditorOpen">
          <div class="teacher-drawer__guide">
            先把最关键的信息填好并保存，后续再补关系、资源和练习。
          </div>
          <el-form label-position="top" size="small">
            <div class="teacher-form-grid">
              <el-form-item label="编码"><el-input v-model="form.code" placeholder="例如 OS-01" /></el-form-item>
              <el-form-item label="标题"><el-input v-model="form.title" placeholder="直接写学生能看懂的知识点名" /></el-form-item>
            </div>
            <div class="teacher-form-grid">
              <el-form-item label="章节"><el-input v-model="form.chapter" placeholder="例如 进程管理" /></el-form-item>
              <el-form-item label="知识目标"><el-input v-model="form.knowledge_tag" placeholder="例如 同步与互斥、页式存储" /></el-form-item>
            </div>
            <div class="teacher-form-grid">
              <el-form-item label="能力目标"><el-input v-model="form.ability_tag" placeholder="例如 逻辑推理、系统分析，可用逗号分隔" /></el-form-item>
              <el-form-item label="素养目标"><el-input v-model="form.literacy_tag" placeholder="例如 主动学习、规范意识，可用逗号分隔" /></el-form-item>
            </div>
            <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" placeholder="用一句话说明这个知识点学什么、为什么重要" /></el-form-item>
            <div class="teacher-form-grid">
              <el-form-item label="学习重点"><el-input-number v-model="form.importance" :min="0" :max="1" :step="0.05" /></el-form-item>
              <el-form-item label="理解难度"><el-input-number v-model="form.difficulty" :min="0" :max="1" :step="0.05" /></el-form-item>
            </div>
            <el-form-item label="课程终点"><el-switch v-model="form.is_terminal" active-text="达标终点" inactive-text="普通节点" /></el-form-item>
            <div class="teacher-drawer__actions">
              <button class="teacher-drawer__primary" type="button" :disabled="saving" @click="saveKp">
                {{ saving ? "保存中..." : "保存知识点" }}
              </button>
              <button class="teacher-drawer__secondary" type="button" @click="graphEditorOpen = false">取消编辑</button>
            </div>
          </el-form>
        </template>

        <template v-else-if="selectedType === 'category' && selectedCategoryNode && categoryOverview">
          <div class="teacher-drawer__meta">共 {{ categoryOverview.total }} 个知识点</div>
          <div class="teacher-drawer__guide-inline">
            <span>查看提示</span>
            <HoverTip content="这里显示这个分类的整体情况。先看分类里有多少知识点，再点下面的知识点进入具体编辑。" />
          </div>

          <div class="teacher-drawer__metrics teacher-drawer__metrics--triple">
            <div class="teacher-drawer__metric">
              <span>培养能力</span>
              <strong>{{ categoryOverview.abilityTags.length }}</strong>
            </div>
            <div class="teacher-drawer__metric">
                <span>培养素养</span>
              <strong>{{ categoryOverview.literacyTags.length }}</strong>
            </div>
            <div class="teacher-drawer__metric">
              <span>节点数量</span>
              <strong>{{ categoryOverview.total }}</strong>
            </div>
          </div>

          <div class="teacher-drawer__section">
            <h4 class="teacher-drawer__section-title">这个分类重点培养什么</h4>
            <div v-if="categoryOverview.abilityTags.length === 0" class="teacher-drawer__empty">还没设置</div>
            <div v-else class="teacher-drawer__tags">
              <span v-for="item in categoryOverview.abilityTags" :key="item" class="teacher-drawer__tag">{{ item }}</span>
            </div>
          </div>

            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">分类下有哪些知识点</h4>
            <div class="teacher-drawer__tags">
              <button v-for="kp in categoryOverview.items" :key="kp.id" class="teacher-drawer__tag" @click="selectKp(kp.id)">
                {{ kp.title }}
              </button>
            </div>
          </div>

          <div class="teacher-drawer__actions">
            <button class="teacher-drawer__primary" @click="resetCreateForm(selectedCategoryNode.key)">在这个分类下新建知识点</button>
          </div>

          <div class="teacher-drawer__section">
            <h4 class="teacher-drawer__section-title">分类之间的关系</h4>
            <div class="teacher-drawer__actions teacher-drawer__actions--compact">
              <button class="teacher-drawer__secondary" @click="startCategoryLinkSelection('prerequisite')">新增后续分类</button>
              <button class="teacher-drawer__secondary" @click="startCategoryLinkSelection('support')">新增支撑分类</button>
              <button class="teacher-drawer__secondary" @click="startCategoryLinkSelection('related')">新增关联分类</button>
            </div>
            <div
              v-if="chapterEdges.filter((edge) => edge.source_chapter === selectedCategoryNode.key || edge.target_chapter === selectedCategoryNode.key).length"
              class="teacher-drawer__list"
            >
              <div
                v-for="edge in chapterEdges.filter((item) => item.source_chapter === selectedCategoryNode.key || item.target_chapter === selectedCategoryNode.key)"
                :key="`c-${edge.id}`"
                class="teacher-drawer__relation-item"
              >
                <span>{{ edge.source_chapter }} → {{ edge.target_chapter }}（{{ edge.relation_type === 'related' ? '关联' : edge.relation_type === 'support' ? '支撑' : '前置' }}）</span>
                <button @click="deleteChapterEdge(edge.id)">删除</button>
              </div>
            </div>
            <div v-else class="teacher-drawer__empty">暂无分类关系</div>
          </div>
        </template>

        <template v-else-if="selectedKp">
          <div class="teacher-drawer__tabs">
            <button :class="{ active: detailTab === 'overview' }" @click="detailTab = 'overview'">看信息</button>
            <button :class="{ active: detailTab === 'relations' }" @click="detailTab = 'relations'">管关系</button>
            <button :class="{ active: detailTab === 'content' }" @click="detailTab = 'content'">内容配置</button>
          </div>
          <div class="teacher-drawer__meta">{{ selectedKp.code }} · {{ selectedKp.chapter || '未分章' }}</div>
          <div class="teacher-drawer__guide-inline">
            <span>查看提示</span>
            <HoverTip
              :content="
                detailTab === 'overview'
                  ? '这里先看当前知识点的基本信息。'
                  : detailTab === 'relations'
                    ? '这里专门处理前置、后续和关联关系。'
                    : '资源、练习和任务放在单独页面里维护。'
              "
            />
          </div>

          <div class="teacher-drawer__metrics">
            <div class="teacher-drawer__metric">
              <span>学习重点</span>
              <strong>{{ Math.round((selectedKp.importance ?? 0.5) * 100) }}</strong>
            </div>
            <div class="teacher-drawer__metric">
              <span>理解难度</span>
              <strong>{{ Math.round((selectedKp.difficulty ?? 0.5) * 100) }}</strong>
            </div>
          </div>

          <div v-if="detailTab === 'overview'">
            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">先改基础信息</h4>
              <div class="teacher-drawer__actions">
                <button class="teacher-drawer__primary" @click="openGraphEditorForSelected">编辑基础信息</button>
              </div>
            </div>

            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">当前知识点信息</h4>
              <div class="teacher-drawer__detail-grid">
                <div class="teacher-drawer__detail-item">
                  <span>章节</span>
                  <strong>{{ selectedKp.chapter || "未分章" }}</strong>
                </div>
                <div class="teacher-drawer__detail-item">
                  <span>知识目标</span>
                  <strong>{{ selectedKp.knowledge_tag || selectedKp.title || "暂未设置" }}</strong>
                </div>
                <div class="teacher-drawer__detail-item">
                  <span>能力目标</span>
                  <strong>{{ selectedKp.ability_tag || "暂未设置" }}</strong>
                </div>
                <div class="teacher-drawer__detail-item">
                  <span>素养目标</span>
                  <strong>{{ selectedKp.literacy_tag || "暂未设置" }}</strong>
                </div>
              </div>
              <div class="teacher-drawer__desc">{{ selectedKp.description || "暂未填写描述" }}</div>
            </div>

            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">当前标签</h4>
              <div class="teacher-drawer__tags">
                <span class="teacher-drawer__tag">{{ selectedKp.knowledge_tag || "未设置知识目标" }}</span>
                <span class="teacher-drawer__tag">{{ selectedKp.ability_tag || "未设置能力标签" }}</span>
                <span class="teacher-drawer__tag">{{ selectedKp.literacy_tag || "未设置素养标签" }}</span>
              </div>
            </div>
          </div>

          <div v-else-if="detailTab === 'relations'">
            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">先选你要补的关系</h4>
              <div class="teacher-drawer__actions teacher-drawer__actions--compact">
              <button class="teacher-drawer__secondary" @click="startLinkSelection('forward')">新增后继</button>
              <button class="teacher-drawer__secondary" @click="startLinkSelection('backward')">新增前置</button>
              <button class="teacher-drawer__secondary" @click="startLinkSelection('support')">新增支撑</button>
              <button class="teacher-drawer__secondary" @click="startLinkSelection('contains')">新增包含</button>
              <button class="teacher-drawer__secondary" @click="startLinkSelection('related')">添加关联</button>
            </div>
              <div class="teacher-drawer__relation-group">
                <strong>前置</strong>
                <div v-if="selectedConnections.incoming.length === 0" class="teacher-drawer__empty">无前置知识点</div>
                <div v-else class="teacher-drawer__tags">
                  <button v-for="kp in selectedConnections.incoming" :key="kp.id" class="teacher-drawer__tag" @click="selectKp(kp.id)">{{ kp.title }}</button>
                </div>
              </div>
              <div class="teacher-drawer__relation-group">
                <strong>后续</strong>
                <div v-if="selectedConnections.outgoing.length === 0" class="teacher-drawer__empty">无后续知识点</div>
                <div v-else class="teacher-drawer__tags">
                  <button v-for="kp in selectedConnections.outgoing" :key="kp.id" class="teacher-drawer__tag" @click="selectKp(kp.id)">{{ kp.title }}</button>
                </div>
              </div>
              <div class="teacher-drawer__relation-group">
                <strong>关联</strong>
                <div v-if="selectedConnections.related.length === 0" class="teacher-drawer__empty">无关联知识点</div>
                <div v-else class="teacher-drawer__tags">
                  <button v-for="kp in selectedConnections.related" :key="kp.id" class="teacher-drawer__tag" @click="selectKp(kp.id)">{{ kp.title }}</button>
                </div>
              </div>

              <div class="teacher-drawer__section">
                <h4 class="teacher-drawer__section-title">支撑与包含</h4>
                <div v-if="selectedConnections.support.length === 0 && selectedConnections.contains.length === 0" class="teacher-drawer__empty">暂无支撑或包含关系</div>
                <div v-else class="teacher-drawer__tags">
                  <button v-for="kp in selectedConnections.support" :key="`sup-${kp.id}`" class="teacher-drawer__tag" @click="selectKp(kp.id)">支撑：{{ kp.title }}</button>
                  <button v-for="kp in selectedConnections.contains" :key="`con-${kp.id}`" class="teacher-drawer__tag" @click="selectKp(kp.id)">包含：{{ kp.title }}</button>
                </div>
              </div>
            </div>

            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">删除已有关系</h4>
              <div class="teacher-drawer__guide-inline">
                <span>查看提示</span>
                <HoverTip content="这里只显示当前节点的直接关系，不能跨层删除更上级或更下级的关系。" />
              </div>
              <div class="teacher-drawer__list" v-if="deletableEdges.length">
                <div v-for="item in deletableEdges" :key="item.edge.id" class="teacher-drawer__relation-item">
                  <div class="teacher-drawer__relation-copy">
                    <span class="teacher-drawer__relation-label">{{ item.relationLabel }}</span>
                    <strong>{{ item.summary }}</strong>
                    <small>{{ item.detail }}</small>
                  </div>
                  <button @click="deleteEdge(item.edge)">删除</button>
                </div>
              </div>
              <div v-else class="teacher-drawer__empty">暂无关系可删除</div>
            </div>
          </div>

          <div v-else>
            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">知识点内容配置</h4>
              <div class="teacher-drawer__guide-inline">
                <span>查看提示</span>
                <HoverTip content="点击下面按钮，进入独立的资源内容页面，单独维护视频、练习和推荐资源。" />
              </div>
              <div class="teacher-drawer__actions">
                <button class="teacher-drawer__primary" @click="openContentWorkspace">打开知识点内容页</button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </aside>
    </div>
  </div>
</template>

<style scoped>
.teacher-workbench {
  background: transparent;
  overflow: hidden;
  border-radius: 0;
  border: none;
  box-shadow: none;
}

.teacher-workbench--fullscreen {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.teacher-workbench--fullscreen .teacher-header,
.teacher-workbench--fullscreen .teacher-guide {
  flex-shrink: 0;
}

.teacher-workbench--fullscreen .teacher-guide {
  display: none;
}

.teacher-workbench--fullscreen .teacher-subtitle {
  display: none;
}

.teacher-workbench--fullscreen .teacher-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 20px 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
}

.teacher-workbench--fullscreen .teacher-title {
  font-size: 22px;
  line-height: 1.2;
}

.teacher-workbench--fullscreen .teacher-controls {
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.teacher-workbench--fullscreen .teacher-search {
  width: min(220px, 36vw);
}

.teacher-workbench--fullscreen .teacher-btn {
  min-height: 38px;
  padding: 0 14px;
  font-size: 13px;
}

.teacher-workbench--fullscreen .teacher-content {
  flex: 1;
  min-height: 0;
  gap: 0;
  padding: 0;
}

.teacher-workbench--embedded {
  min-height: 0;
}

.teacher-workbench--embedded .teacher-content {
  min-height: 0;
}

.teacher-workbench--embedded .teacher-stage {
  min-height: 0;
}

.teacher-workbench--embedded .teacher-stage__viewport {
  min-height: clamp(320px, 54dvh, 720px);
}

.teacher-workbench--fullscreen .teacher-sidebar {
  flex: 0 0 280px;
  width: 280px;
  max-width: 280px;
  padding: 16px;
}

.teacher-workbench--fullscreen .teacher-drawer {
  flex: 0 0 336px;
  width: 336px;
  max-width: 336px;
  padding: 0;
}

.teacher-workbench--fullscreen .teacher-stage {
  min-height: calc(100dvh - 250px);
}

.teacher-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 18px 20px 14px;
  gap: 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, #f8fbff 0%, #ffffff 52%, #eef6ff 100%);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
}

.teacher-heading {
  display: grid;
  gap: 4px;
}

.teacher-title {
  font-size: 22px;
  font-weight: 800;
  color: #1f2937;
  margin: 0;
  line-height: 1.25;
}

.teacher-subtitle {
  display: none;
}

.teacher-guide {
  display: none;
}

.teacher-guide span {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.teacher-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.teacher-search-card {
  display: grid;
  gap: 6px;
  min-width: 240px;
}

.teacher-search-card__label {
  font-size: 12px;
  font-weight: 800;
  color: #243449;
}

.teacher-search-card__hint {
  font-size: 12px;
  color: #6f829a;
}

.teacher-search {
  width: 240px;
}

.teacher-search :deep(.el-input__wrapper) {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: none;
  border: 1px solid rgba(31, 41, 55, 0.14);
  border-radius: 14px;
}

.teacher-search :deep(.el-input__inner) {
  color: #243449;
}

.teacher-btn {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid var(--app-border);
  border-radius: 999px;
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  color: #1f2937;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
  box-shadow: var(--app-shadow-soft);
}

.teacher-btn--primary {
  border-color: var(--app-green);
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}

.teacher-btn:hover {
  background: linear-gradient(180deg, #ebf8ff 0%, #dff2fb 100%);
}

.teacher-content {
  display: flex;
  align-items: stretch;
  gap: 18px;
  padding: 0;
  min-width: 0;
  overflow: hidden;
  min-height: 0;
}

.teacher-content > * {
  min-height: 0;
}

.teacher-content--fullscreen {
  position: relative;
  flex: 1;
  min-height: 0;
}

.teacher-content--drawer-collapsed .teacher-drawer {
  display: none;
}

.teacher-sidebar {
  width: 280px;
  flex: 0 0 280px;
  max-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
  color: var(--app-text-soft);
  z-index: 4;
}

.teacher-content--fullscreen .teacher-sidebar {
  position: static;
  width: auto;
  box-shadow: none;
}

.teacher-fullscreen-nav {
  position: absolute;
  left: 14px;
  top: 14px;
  width: 240px;
  max-height: calc(100% - 28px);
  overflow: hidden;
  display: grid;
  gap: 10px;
  padding: 10px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 251, 255, 0.98) 100%);
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  color: #1f2937;
  z-index: 14;
  pointer-events: auto;
}

.teacher-fullscreen-nav__tabs {
  display: flex;
  padding: 4px;
  border-radius: 999px;
  background: #eef5ff;
  border: 1px solid rgba(147, 197, 253, 0.28);
}

.teacher-fullscreen-nav__tabs span {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 800;
  width: 100%;
}

.teacher-fullscreen-nav__tabs span.active {
  color: #ffffff;
  background: linear-gradient(135deg, #4f8df7 0%, #2563eb 100%);
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18);
}

.teacher-fullscreen-nav__search {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border-radius: 8px;
  background: #f8fbff;
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.teacher-fullscreen-nav__search-icon {
  color: #64748b;
  font-size: 18px;
  line-height: 1;
}

.teacher-fullscreen-nav__search input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #1f2937;
  font-size: 13px;
  font-weight: 700;
}

.teacher-fullscreen-nav__search input::placeholder {
  color: #94a3b8;
}

.teacher-fullscreen-nav__search button {
  border: 0;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.teacher-fullscreen-nav__tree {
  display: grid;
  gap: 4px;
  overflow: auto;
  max-height: 184px;
  padding-right: 2px;
}

.teacher-fullscreen-nav__group {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.teacher-fullscreen-nav__item {
  min-height: 31px;
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) auto;
  align-items: center;
  gap: 5px;
  width: 100%;
  border: 0;
  border-radius: 7px;
  padding: 0 7px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  text-align: left;
}

.teacher-fullscreen-nav__item:hover,
.teacher-fullscreen-nav__item.active {
  background: #eef5ff;
}

.teacher-fullscreen-nav__arrow {
  color: #94a3b8;
  font-size: 12px;
}

.teacher-fullscreen-nav__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 800;
}

.teacher-fullscreen-nav__count {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.teacher-fullscreen-nav__children {
  display: grid;
  gap: 4px;
  max-height: 128px;
  overflow: auto;
  padding: 2px 0 4px 21px;
}

.teacher-fullscreen-nav__child {
  min-height: 30px;
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 7px;
  background: rgba(248, 251, 255, 0.94);
  color: #475569;
  cursor: pointer;
  padding: 0 8px;
  text-align: left;
}

.teacher-fullscreen-nav__child:hover,
.teacher-fullscreen-nav__child.active {
  border-color: rgba(59, 130, 246, 0.34);
  background: #eef5ff;
  color: #1d4ed8;
}

.teacher-fullscreen-nav__child.match {
  border-color: rgba(245, 158, 11, 0.46);
  background: #fff7ed;
  color: #9a3412;
}

.teacher-fullscreen-nav__child span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 800;
}

.teacher-fullscreen-nav__child small {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 800;
}

.teacher-tree {
  display: grid;
  gap: 12px;
}

.teacher-tree__intro {
  display: none;
}

.teacher-tree__intro strong {
  font-size: 13px;
  color: #274161;
}

.teacher-tree__intro span {
  font-size: 12px;
  line-height: 1.6;
  color: #637d9b;
}

.teacher-tree__create {
  min-height: 40px;
  border: 1px solid rgba(31, 41, 55, 0.14);
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #1f2937;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

.teacher-tree__create:hover {
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
}

.teacher-tree__empty {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 18px;
  border: 1px dashed #dfe7f1;
  background: #ffffff;
  color: #617792;
}

.teacher-tree__empty strong {
  color: #243449;
  font-size: 14px;
}

.teacher-tree__empty span {
  font-size: 12px;
  line-height: 1.6;
}

.teacher-tree__summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #dfe7f1;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.teacher-tree__summary:hover {
  background: linear-gradient(180deg, #eef8ff 0%, #ffffff 100%);
  border-color: #cfe0f6;
}

.teacher-tree__summary.active {
  background: #edf4ff;
  color: #2459ab;
  border-color: #a9c5ef;
}

.teacher-tree__count {
  font-size: 12px;
  color: #94a3b8;
}

.teacher-tree__children {
  margin-top: 8px;
  display: grid;
  gap: 8px;
}

.teacher-tree__child {
  display: block;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e1eaf1;
  border-radius: 16px;
  background: #ffffff;
  color: #475569;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
}

.teacher-tree__child small {
  display: block;
  font-size: 10px;
  color: #94a3b8;
  margin-top: 2px;
}

.teacher-tree__child:hover {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.teacher-tree__child.active {
  background: #edf4ff;
  border-color: #a9c5ef;
  color: #2459ab;
}

.teacher-stage {
  --graph-stage-pad: 8px;
  position: relative;
  overflow: hidden;
  cursor: default;
  user-select: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: var(--graph-stage-pad);
  min-width: 0;
  flex: 1;
  min-height: 0;
  max-height: 100%;
  height: 100%;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid #e3ebf5;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.teacher-workbench--fullscreen .teacher-stage {
  min-height: 0;
}

.teacher-stage__viewport {
  position: relative;
  flex: 1 1 0;
  min-height: 220px;
  width: 100%;
  overflow: hidden;
  /* 与外层 .teacher-stage 圆角同心：内半径 = 外半径 − 内边距，避免底角“直角顶到”外框 */
  border-radius: 16px;
  background: linear-gradient(180deg, #fffbf6 0%, #fff8ef 100%);
  border: none;
  contain: layout style;
  isolation: isolate;
  transform: translateZ(0);
}

/* 全屏工作台：不要强推最小高度，避免底部缩放区被裁切 */
.teacher-workbench--fullscreen .teacher-stage__viewport {
  min-height: 0;
  height: 100%;
}

.teacher-stage--dragging {
  cursor: grabbing;
}

.teacher-stage__top {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.teacher-stage__stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.teacher-stage__top-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 8px 12px;
  min-width: 0;
}

.teacher-stage__legend-details {
  display: none;
}

.teacher-stage__legend-summary {
  list-style: none;
  cursor: pointer;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #5e6b7d;
  user-select: none;
  line-height: 1.35;
}

.teacher-stage__legend-summary::-webkit-details-marker {
  display: none;
}

.teacher-stage__legend-details[open] .teacher-stage__legend-summary {
  border-bottom: 1px solid #ebe3d6;
}

.teacher-stage__legend-details .teacher-stage__legend {
  padding: 8px 10px 10px;
  margin: 0;
}

.teacher-stage__bottom {
  position: absolute;
  right: calc(var(--graph-stage-pad) + 12px);
  bottom: calc(var(--graph-stage-pad) + 12px);
  z-index: 9;
  pointer-events: none;
  display: flex;
  align-items: center;
  gap: 10px;
}

.teacher-stage__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.teacher-stage__legend {
  display: none;
}

.teacher-stage__legend-item {
  min-height: 34px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 253, 249, 0.92);
  border: 1px solid #e4ddd2;
  color: #5f6f85;
  font-size: 12px;
  line-height: 1.4;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
}

.teacher-stage__legend-line {
  width: 28px;
  height: 0;
  border-top: 2px solid #64748b;
  flex: 0 0 auto;
}

.teacher-stage__legend-line--chapter {
  border-top-style: dashed;
  border-top-color: rgba(184, 143, 70, 0.7);
}

.teacher-stage__legend-line--attach {
  border-top-style: dashed;
  border-top-width: 1.5px;
  border-top-color: rgba(179, 154, 117, 0.7);
}

.teacher-stage__legend-dimensions {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex: 0 0 auto;
}

.teacher-stage__legend-dimensions .td {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
}

.teacher-stage__legend-dimensions .td--knowledge { background: #3978d8; }
.teacher-stage__legend-dimensions .td--ability { background: #24a36f; }
.teacher-stage__legend-dimensions .td--literacy { background: #d58b2a; }

.teacher-stage__pill,
.teacher-stage__button {
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #dde3ef;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%);
  color: #29476a;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.teacher-stage__button {
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.teacher-stage__button:hover {
  background: linear-gradient(180deg, #fffefb 0%, #f8fbf1 100%);
}

.teacher-stage__button--primary {
  background: linear-gradient(180deg, #edf9cf 0%, #dff2b4 100%);
  border-color: #c7e38e;
  color: #23421f;
  box-shadow: 0 10px 20px rgba(182, 214, 118, 0.24);
}

.teacher-stage__actions {
  justify-content: flex-end;
}

.teacher-stage__focus {
  margin-top: 10px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.teacher-stage__focus span {
  font-size: 13px;
  font-weight: 700;
  color: #314661;
}

.teacher-stage__focus-btn {
  border: 1px solid #dde3ef;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%);
  color: #39506d;
  border-radius: 999px;
  padding: 0 14px;
  min-height: 34px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.teacher-stage__focus-btn--primary {
  border-color: #c7e38e;
  background: linear-gradient(180deg, #edf9cf 0%, #dff2b4 100%);
  color: #23421f;
}

.teacher-canvas {
  position: absolute;
  left: 0;
  top: 0;
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
  cursor: grab;
  z-index: 1;
}

.teacher-category-node,
.teacher-node {
  cursor: pointer;
}

.teacher-category-node__label,
.teacher-node__label {
  pointer-events: none;
}

.teacher-category-node__title,
.teacher-category-node__meta,
.teacher-node__code,
.teacher-node__title {
  fill: #243449;
  font-weight: 500;
  paint-order: stroke fill;
  pointer-events: none;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-linejoin: round;
  stroke-width: 3px;
}

.teacher-node__dimensions {
  pointer-events: none;
  filter: drop-shadow(0 4px 8px rgba(15, 23, 42, 0.16));
}

.teacher-node__dimension-label {
  fill: #ffffff;
  font-size: 12px;
  font-weight: 900;
  pointer-events: none;
}

.teacher-category-node__title,
.teacher-node__title {
  font-size: 15px;
  font-weight: 700;
}

.teacher-category-node__meta,
.teacher-node__code {
  font-size: 12px;
  fill: #718097;
}

.teacher-node__warn {
  font-size: 10px;
  font-weight: 700;
  fill: #c2410c;
  pointer-events: none;
}

.teacher-stage__selected-action {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 16;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  max-width: min(520px, calc(100% - 320px));
  padding: 10px 12px 10px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.28);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.12);
  color: #1f2937;
  pointer-events: auto;
}

.teacher-stage__selected-action div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.teacher-stage__selected-action strong,
.teacher-stage__selected-action span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.teacher-stage__selected-action strong {
  font-size: 14px;
  font-weight: 900;
}

.teacher-stage__selected-action span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.teacher-stage__selected-action button {
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
  color: #ffffff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
}

.teacher-stage__selected-action button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.teacher-stage__menu {
  position: absolute;
  z-index: 5;
  transform: translateY(calc(-100% - 8px));
  display: flex;
  gap: 8px;
  padding: 8px;
  border-radius: 20px;
  background: #fffdf9;
  border: 1px solid #e3ddd3;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.teacher-stage__menu--below {
  transform: translateY(8px);
}

.teacher-stage__menu button,
.teacher-stage__hint button,
.teacher-stage__zoom button,
.teacher-drawer__primary,
.teacher-drawer__secondary,
.teacher-drawer__relation-item button {
  border: 0;
  cursor: pointer;
}

.teacher-stage__menu button {
  padding: 0 12px;
  border-radius: 999px;
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%);
  color: #29476a;
  font-size: 12px;
  font-weight: 700;
  transition: background 0.2s ease;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.teacher-stage__menu button:hover {
  background: linear-gradient(180deg, #fffefb 0%, #f8fbf1 100%);
}

.teacher-stage__menu .danger {
  background: #fee2e2;
  color: #dc2626;
}

.teacher-stage__hint {
  display: none;
}

.teacher-stage__hint--chapter {
  bottom: 132px;
}

.teacher-editor-float {
  position: absolute;
  top: 94px;
  right: 28px;
  z-index: 6;
  width: 380px;
  max-height: calc(100% - 128px);
  padding: 18px;
  border-radius: 24px;
  background: #ffffff;
  border: 1px solid #dfe7f1;
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
  color: #475569;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.teacher-editor-float__title {
  margin-bottom: 4px;
  color: #243449;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}

.teacher-editor-float__intro {
  margin: -4px 0 10px;
  font-size: 12px;
  line-height: 1.6;
  color: #6a809d;
  flex-shrink: 0;
}

.teacher-editor-float__body {
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.teacher-editor-float__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e1eaf1;
  background: #ffffff;
  position: sticky;
  bottom: 0;
  flex-shrink: 0;
}

.teacher-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.teacher-stage__zoom {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 253, 249, 0.98) 0%, rgba(255, 247, 239, 0.98) 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  box-shadow: 0 10px 22px rgba(31, 41, 55, 0.08);
  pointer-events: auto;
}

.teacher-stage__fullscreen-filters {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  pointer-events: auto;
}

.teacher-stage__filter-group {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.1);
}

.teacher-stage__filter-group--focus {
  background: rgba(255, 255, 255, 0.96);
}

.teacher-stage__filter-group--expand {
  background: rgba(239, 246, 255, 0.98);
}

.teacher-stage__filter-group button {
  min-height: 30px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.teacher-stage__filter-group .teacher-stage__filter-action {
  color: #1e3a8a;
  background: #eff6ff;
}

.teacher-stage__filter-group .teacher-stage__filter-action:hover {
  color: #ffffff;
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
}

.teacher-stage__filter-group button:hover {
  background: #f1f5f9;
}

.teacher-stage__filter-group button.active {
  color: #ffffff;
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
}

.teacher-stage__filter-group--focus button.active:nth-child(2) {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
}

.teacher-stage__filter-group--focus button.active:nth-child(3) {
  background: linear-gradient(135deg, #c87911 0%, #a16207 100%);
}

.teacher-stage__filter-group--focus button.active:nth-child(4) {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
}

.teacher-stage__zoom button {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f2fbe5 0%, #e4f6c6 100%);
  color: #355a28;
  border: 1px solid rgba(31, 41, 55, 0.08);
  font-size: 14px;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.teacher-stage__zoom button:hover {
  background: linear-gradient(180deg, #f6fde9 0%, #dcf2b7 100%);
}

.teacher-stage__zoom span {
  font-size: 12px;
  color: #6b7280;
  min-width: 78px;
  text-align: center;
  font-weight: 800;
}

.teacher-stage__empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  gap: 10px;
  padding: 24px;
  text-align: center;
  border: none;
  border-radius: 22px;
  background:
    radial-gradient(circle at top left, rgba(255, 214, 203, 0.18), transparent 22%),
    radial-gradient(circle at bottom right, rgba(184, 228, 246, 0.2), transparent 24%),
    rgba(255, 252, 247, 0.96);
  color: #1f2937;
  z-index: 3;
  pointer-events: auto;
}

.teacher-stage__empty strong {
  font-size: 22px;
  line-height: 1.2;
}

.teacher-stage__empty span {
  max-width: 34rem;
  color: #6b7280;
  line-height: 1.7;
}

.teacher-stage__empty-btn {
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
  border-radius: 999px;
  min-height: 42px;
  padding: 0 18px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.teacher-stage__empty-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.teacher-stage__empty-btn--ghost {
  background: linear-gradient(180deg, #dff2fb 0%, #bfe3f5 100%);
  color: #334155;
  border-color: rgba(31, 41, 55, 0.16);
  box-shadow: 0 4px 0 rgba(31, 41, 55, 0.12);
}

.teacher-drawer {
  width: 336px;
  flex: 0 0 336px;
  max-height: 100%;
  overflow-x: hidden;
  overflow-y: hidden;
  padding: 0;
  border-radius: 24px;
  background: #ffffff;
  border: 1px solid #dfe7f1;
  color: var(--app-text-soft);
  z-index: 5;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
}

.teacher-content--fullscreen .teacher-drawer {
  position: static;
  box-shadow: none;
  z-index: 5;
  display: flex;
  flex-direction: column;
}

.teacher-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 18px 14px;
  border-bottom: 1px solid #e5edf6;
}

.teacher-drawer__title {
  font-size: 16px;
  font-weight: 700;
  color: #243449;
  margin: 0;
}

.teacher-drawer__close {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: #eff5ff;
  color: #35507f;
  font-size: 16px;
}

.teacher-drawer__guide-inline {
  display: none;
}

.teacher-drawer__close:hover {
  background: #dfefff;
  color: #2459ab;
}

.teacher-drawer__content {
  padding: 16px 18px 20px;
  overflow-y: auto;
  min-height: 0;
}

.teacher-drawer__guide {
  display: none;
}

.teacher-stage__hint,
.teacher-stage__hint--chapter,
.teacher-drawer__flow-hint,
.teacher-drawer__recommend,
.teacher-drawer__ability-hint {
  display: none;
}

.teacher-drawer__meta {
  font-size: 12px;
  color: #718097;
  margin-bottom: 8px;
}

.teacher-drawer__tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 18px;
}

.teacher-drawer__tabs button {
  border: 1px solid #dce6f2;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  background: #ffffff;
  color: #3c587d;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.teacher-drawer__tabs button:hover {
  background: #eff5ff;
  color: #1565c0;
}

.teacher-drawer__tabs button.active {
  border-color: #a8c5f8;
  background: linear-gradient(165deg, #f5f9ff 0%, #eef4fc 100%);
  color: #22549b;
}

.teacher-drawer__metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 20px;
}

.teacher-drawer__metrics.teacher-drawer__metrics--triple {
  grid-template-columns: repeat(3, 1fr);
}

.teacher-drawer__metric {
  padding: 12px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #dfe7f1;
}

.teacher-drawer__metric span {
  display: block;
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
}

.teacher-drawer__metric strong {
  font-size: 20px;
  color: #1e293b;
  font-weight: 700;
}

.teacher-drawer__section {
  margin-bottom: 20px;
}

.teacher-drawer__detail-grid {
  display: grid;
  gap: 8px;
  margin-bottom: 10px;
}

.teacher-drawer__detail-item {
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid #dfe7f1;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  display: grid;
  gap: 4px;
}

.teacher-drawer__detail-item span {
  font-size: 11px;
  color: #728299;
}

.teacher-drawer__detail-item strong {
  font-size: 13px;
  color: #233447;
  line-height: 1.7;
}

.teacher-drawer__desc {
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid #dfe7f1;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #51657f;
  font-size: 13px;
  line-height: 1.7;
}

.teacher-drawer__section-title {
  font-size: 13px;
  font-weight: 700;
  color: #314661;
  margin: 0 0 8px 0;
}

.teacher-drawer__empty {
  font-size: 12px;
  color: #94a3b8;
}

.teacher-drawer__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.teacher-drawer__tag {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #dce6f2;
  border-radius: 999px;
  background: #ffffff;
  color: #35507f;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
}

.teacher-drawer__tag:hover {
  background: #e3f2fd;
  border-color: #90caf9;
  color: #1565c0;
}

.teacher-drawer__list {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.teacher-drawer__list-item,
.teacher-drawer__relation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #dfe7f1;
  border-radius: 16px;
  background: #ffffff;
  color: #475569;
}

.teacher-drawer__list-item {
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
}

.teacher-drawer__list-item:hover {
  background: #e3f2fd;
  border-color: #90caf9;
}

.teacher-drawer__list-item small {
  color: #94a3b8;
  font-size: 10px;
}

.teacher-drawer__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.teacher-drawer__actions--compact {
  margin-top: 8px;
}

.teacher-drawer__primary,
.teacher-drawer__secondary {
  padding: 0 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  transition: all 0.2s ease;
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.teacher-drawer__primary {
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  border: 1px solid var(--app-green);
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
}

.teacher-drawer__primary:hover {
  transform: translateY(-1px);
}

.teacher-drawer__secondary {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e1eaf1;
}

.teacher-drawer__secondary:hover {
  background: #e3f2fd;
  color: #1565c0;
  border-color: #90caf9;
}

.teacher-drawer__relation-group {
  margin-bottom: 12px;
}

.teacher-drawer__relation-group strong {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.teacher-drawer__relation-tip {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.teacher-drawer__relation-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.teacher-drawer__relation-label {
  width: fit-content;
  padding: 4px 8px;
  border-radius: 999px;
  background: #edf4ff;
  border: 1px solid #d5e4fb;
  color: #35507f;
  font-size: 11px;
  font-weight: 700;
}

.teacher-drawer__relation-copy strong {
  color: #243449;
  font-size: 14px;
  line-height: 1.6;
}

.teacher-drawer__relation-copy small {
  color: #7b8ba1;
  font-size: 12px;
  line-height: 1.6;
}

.teacher-drawer__relation-item button {
  padding: 4px 8px;
  border-radius: 4px;
  background: #fee2e2;
  color: #dc2626;
  font-size: 11px;
  transition: background 0.2s ease;
}

.teacher-drawer__relation-item button:hover {
  background: #fecaca;
}

.teacher-drawer__binder {
  margin-top: 16px;
}

.teacher-drawer__binder :deep(.content-binder) {
  border: 0;
  background: transparent;
}

.teacher-drawer__binder :deep(.content-binder__header) {
  display: none;
}

.teacher-drawer__binder :deep(.content-binder__section) {
  background: #f8fafc;
  border-radius: 4px;
  border: 1px solid #e1eaf1;
}

.teacher-editor-float :deep(.el-input__wrapper),
.teacher-editor-float :deep(.el-textarea__inner),
.teacher-editor-float :deep(.el-input-number),
.teacher-drawer :deep(.content-binder__section),
.teacher-drawer :deep(.el-input__wrapper),
.teacher-drawer :deep(.el-textarea__inner),
.teacher-drawer :deep(.el-input-number),
.teacher-drawer :deep(.el-select__wrapper) {
  background: #ffffff;
  color: #475569;
  box-shadow: inset 0 0 0 1px #e1eaf1;
}

.teacher-editor-float :deep(.el-form-item__label),
.teacher-drawer :deep(.el-form-item__label),
.teacher-drawer :deep(.content-binder__section-title),
.teacher-drawer :deep(.content-binder__meta) {
  color: #64748b;
}

.teacher-editor-float :deep(.el-input__inner),
.teacher-editor-float :deep(.el-textarea__inner),
.teacher-drawer :deep(.el-input__inner),
.teacher-drawer :deep(.el-textarea__inner),
.teacher-drawer :deep(.el-select__placeholder),
.teacher-drawer :deep(.content-binder__section),
.teacher-drawer :deep(.content-binder__subtext) {
  color: #475569;
}

.teacher-editor-float :deep(.el-input-number__decrease),
.teacher-editor-float :deep(.el-input-number__increase),
.teacher-drawer :deep(.el-input-number__decrease),
.teacher-drawer :deep(.el-input-number__increase) {
  background: #f8fafc;
  color: #475569;
}

@media (max-width: 1200px) {
  .teacher-sidebar {
    width: 240px;
    flex: 0 0 240px;
  }

  .teacher-drawer {
    width: 300px;
    flex: 0 0 300px;
  }
}

@media (max-width: 768px) {
  .teacher-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .teacher-controls {
    width: 100%;
    justify-content: space-between;
  }

  .teacher-search {
    flex: 1;
  }

  .teacher-content {
    flex-direction: column;
    min-height: 0;
    overflow: auto;
  }

  .teacher-sidebar {
    width: 100%;
    flex: none;
    max-height: 42vh;
  }

  .teacher-stage {
    min-height: min(360px, 50vh);
    flex: 1 1 auto;
  }

  .teacher-stage__viewport {
    min-height: min(280px, 40vh);
  }

  .teacher-workbench--fullscreen .teacher-stage__viewport {
    min-height: clamp(240px, 48dvh, 720px);
  }

  .teacher-stage__legend {
    flex-wrap: wrap;
  }

  .teacher-drawer {
    width: 100%;
    flex: none;
    max-height: 50vh;
  }

  .teacher-stage__top-row {
    flex-direction: column;
    align-items: stretch;
  }

  .teacher-stage__focus {
    align-items: flex-start;
  }
}

.teacher-workbench {
  gap: 14px;
  padding: 16px;
  background: transparent;
}

.teacher-header,
.teacher-sidebar,
.teacher-stage,
.teacher-drawer {
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.18), transparent 34%),
    radial-gradient(circle at top left, rgba(187, 247, 208, 0.12), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow:
    0 18px 36px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.teacher-header {
  border-radius: 28px;
  padding: 18px 20px;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.22), transparent 30%),
    radial-gradient(circle at right bottom, rgba(187, 247, 208, 0.16), transparent 24%),
    linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
}

.teacher-sidebar {
  border-radius: 28px;
}

.teacher-stage {
  border-radius: 28px;
}

.teacher-stage__top {
  padding: 8px 12px 4px;
  gap: 6px;
  background: transparent;
  border-bottom: none;
}

.teacher-stage__stats,
.teacher-stage__focus {
  gap: 8px;
}

.teacher-stage__pill {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(187, 247, 208, 0.4);
  border-color: rgba(34, 197, 94, 0.22);
  color: #166534;
}

.teacher-stage__button,
.teacher-stage__focus-btn,
.teacher-stage__menu button,
.teacher-stage__zoom button,
.teacher-drawer__primary,
.teacher-drawer__secondary,
.teacher-drawer__tag,
.teacher-drawer__relation-item button {
  border-radius: 12px;
}

.teacher-stage__button,
.teacher-stage__focus-btn,
.teacher-stage__menu button {
  min-height: 34px;
  padding-inline: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #334155;
}

.teacher-stage__focus-btn {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.teacher-stage__button--primary,
.teacher-stage__focus-btn--primary,
.teacher-drawer__primary {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  border-color: rgba(34, 197, 94, 0.3);
  color: #ffffff;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
}

.teacher-stage__legend {
  gap: 8px 12px;
}

.teacher-stage__legend-item {
  color: #5f6f85;
}

.teacher-stage__legend-line,
.teacher-stage__legend-dimensions {
  opacity: 0.85;
}

.teacher-stage__viewport {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.14), transparent 22%),
    radial-gradient(circle at top right, rgba(187, 247, 208, 0.12), transparent 24%),
    linear-gradient(180deg, #f8fbff 0%, #f5faff 56%, #ffffff 100%);
}

.teacher-stage__empty {
  background: rgba(255, 255, 255, 0.98);
  border-color: #e4ddd2;
}

.teacher-drawer {
  border-radius: 28px;
}

.teacher-drawer__header {
  padding: 14px 16px 10px;
  border-bottom-color: rgba(148, 163, 184, 0.18);
}

.teacher-drawer__content {
  padding: 14px 14px 16px;
}

.teacher-drawer__guide-inline,
.teacher-drawer__flow-hint,
.teacher-drawer__recommend,
.teacher-drawer__ability-hint,
.teacher-stage__hint,
.teacher-stage__hint--chapter {
  display: none;
}

.teacher-drawer__tabs {
  gap: 8px;
  padding: 8px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.teacher-drawer__tabs button {
  min-height: 34px;
  border-radius: 12px;
  border-color: rgba(148, 163, 184, 0.18);
  background: #ffffff;
  color: #475569;
}

.teacher-drawer__tabs button.active {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
  border-color: rgba(34, 197, 94, 0.3);
}

.teacher-drawer__metric,
.teacher-drawer__desc,
.teacher-drawer__empty,
.teacher-drawer__relation-tip {
  border-radius: 16px;
}

.teacher-drawer__metric {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.teacher-drawer__tag {
  background: #f8fafc;
  border-color: rgba(148, 163, 184, 0.18);
  color: #475569;
}

.teacher-drawer__secondary {
  background: #ffffff;
  border-color: rgba(148, 163, 184, 0.18);
  color: #475569;
}

.teacher-drawer__secondary:hover {
  background: #f8fbff;
  border-color: rgba(59, 130, 246, 0.24);
  color: #1d4ed8;
}

.teacher-drawer__relation-item button {
  background: #fee2e2;
  color: #dc2626;
}

.teacher-tree__summary,
.teacher-tree__child,
.teacher-stage__menu,
.teacher-stage__zoom {
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.teacher-tree__summary {
  box-shadow: var(--app-shadow-soft);
}

.teacher-tree__summary.active,
.teacher-tree__child.active {
  background: radial-gradient(circle at top left, rgba(187, 247, 208, 0.36), transparent 58%), #ffffff;
  border-color: rgba(34, 197, 94, 0.24);
}

.teacher-tree__child:hover {
  background: #f8fbff;
}

.teacher-stage__menu {
  padding: 8px;
  gap: 8px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.teacher-stage__menu button {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: #ffffff;
  color: #475569;
}

.teacher-stage__menu .danger {
  background: #fef2f2;
  color: #dc2626;
  border-color: #f5c2c7;
}

.teacher-node:hover circle:last-of-type,
.teacher-category-node:hover rect {
  filter: drop-shadow(0 10px 18px rgba(90, 147, 230, 0.14));
}
</style>
