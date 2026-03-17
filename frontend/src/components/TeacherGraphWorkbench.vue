<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

type KP = {
  id: number;
  code: string;
  title: string;
  description: string;
  chapter?: string;
  ability_tag?: string;
  literacy_tag?: string;
  importance?: number;
  difficulty?: number;
  pos_x?: number | null;
  pos_y?: number | null;
};

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
  selectedType: "kp" | "category";
  selectedId: number | null;
  selectedCategory: string | null;
  drawerOpen: boolean;
  detailTab: "overview" | "relations" | "content";
};

const props = withDefaults(defineProps<{ subject: string; grade: string; fullscreen?: boolean }>(), {
  fullscreen: false,
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
}>();

const loading = ref(false);
const saving = ref(false);
const search = ref("");
const activeChapter = ref("全部");
const selectedType = ref<"kp" | "category">("kp");
const selectedId = ref<number | null>(null);
const selectedCategory = ref<string | null>(null);
const graphEditorOpen = ref(false);
const linkSelectionMode = ref<null | "forward" | "backward" | "related">(null);
const categoryLinkMode = ref<null | "prerequisite" | "related">(null);
const drawerOpen = ref(true);
const detailTab = ref<"overview" | "relations" | "content">("overview");
const DEFAULT_CANVAS_SCALE = 0.7;
const MIN_CANVAS_SCALE = 0.5;
const MAX_CANVAS_SCALE = 4;
const SCALE_STEP = 0.2;
const canvasScale = ref(DEFAULT_CANVAS_SCALE);
const panX = ref(0);
const panY = ref(0);
const stageRef = ref<HTMLElement | null>(null);
const CANVAS_WIDTH = 60000;
const CANVAS_HEIGHT = 40000;
const INITIAL_CENTER_X = 30000;
const INITIAL_CENTER_Y = 20000;
const draggingCanvas = ref(false);
const draggingNode = ref<DragNode | null>(null);
const dragStartX = ref(0);
const dragStartY = ref(0);
const dragOriginX = ref(0);
const dragOriginY = ref(0);
const kpPositions = ref<Record<number, Point>>({});
const categoryPositions = ref<Record<string, Point>>({});
const kps = ref<KP[]>([]);
const edges = ref<Edge[]>([]);
const chapterEdges = ref<ChapterEdge[]>([]);
const mutingViewStatePersist = ref(false);
const legacyLayoutWarned = ref(false);
const useLegacyFallbackLayout = ref(false);

const form = reactive({
  id: 0,
  code: "",
  title: "",
  description: "",
  chapter: "",
  ability_tag: "",
  literacy_tag: "",
  importance: 0.5,
  difficulty: 0.5,
});

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
    return `${kp.code} ${kp.title} ${kp.description || ""} ${kp.chapter || ""}`.toLowerCase().includes(kw);
  });
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
const drawerVisible = computed(() => drawerOpen.value && (selectedKp.value != null || selectedCategoryNode.value != null));

const selectedConnections = computed(() => {
  if (!selectedKp.value) return { incoming: [], outgoing: [], related: [] as KP[] };
  const currentId = selectedKp.value.id;
  const incomingIds = edges.value.filter((edge) => edge.next_id === currentId && edge.relation_type !== "related").map((edge) => edge.prereq_id);
  const outgoingIds = edges.value.filter((edge) => edge.prereq_id === currentId && edge.relation_type !== "related").map((edge) => edge.next_id);
  const relatedIds = edges.value
    .filter((edge) => edge.relation_type === "related" && (edge.prereq_id === currentId || edge.next_id === currentId))
    .map((edge) => (edge.prereq_id === currentId ? edge.next_id : edge.prereq_id));

  return {
    incoming: kps.value.filter((kp) => incomingIds.includes(kp.id)),
    outgoing: kps.value.filter((kp) => outgoingIds.includes(kp.id)),
    related: kps.value.filter((kp) => relatedIds.includes(kp.id)),
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

const stageStats = computed(() => ({
  points: filteredKps.value.length,
  edges: edges.value.length + chapterEdges.value.length,
  categories: categoryNodes.value.length,
}));

const hasGraphData = computed(() => kps.value.length > 0);
const categoryKeys = computed(() => new Set(categoryNodes.value.map((item) => item.key)));
const visibleChapterEdges = computed(() =>
  chapterEdges.value.filter(
    (edge) => categoryKeys.value.has(edge.source_chapter) && categoryKeys.value.has(edge.target_chapter),
  ),
);

function chapterPositionStorageKey() {
  return `da_teacher_category_pos_v2_${props.subject}_${props.grade}`;
}

function viewStateStorageKey() {
  if (!props.subject) return "";
  return `da_teacher_graph_view_v3_${props.subject}_${props.grade}`;
}

function persistViewState() {
  if (mutingViewStatePersist.value) return;
  const key = viewStateStorageKey();
  if (!key) return;
  const payload: WorkbenchViewState = {
    canvasScale: canvasScale.value,
    panX: panX.value,
    panY: panY.value,
    activeChapter: activeChapter.value,
    search: search.value,
    selectedType: selectedType.value,
    selectedId: selectedId.value,
    selectedCategory: selectedCategory.value,
    drawerOpen: drawerOpen.value,
    detailTab: detailTab.value,
  };
  localStorage.setItem(key, JSON.stringify(payload));
}

function restoreViewState() {
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
  const groups = new Map<string, KP[]>();
  for (const kp of filteredKps.value) {
    const key = kp.chapter || "未分章";
    const arr = groups.get(key) ?? [];
    arr.push(kp);
    groups.set(key, arr);
  }

  for (const [chapter, items] of groups.entries()) {
    const anchor = categoryPositions.value[chapter] ?? defaultCategoryPositions.value[chapter] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
    const total = Math.max(items.length, 1);
    const radiusX = Math.min(360, 220 + items.length * 10);
    const radiusY = Math.min(220, 140 + items.length * 8);
    const verticalLift = 240;
    items.forEach((kp, index) => {
      if (total === 1) {
        entries[kp.id] = {
          x: anchor.x,
          y: anchor.y + 250,
        };
        return;
      }
      const angle = total === 1
        ? Math.PI / 2
        : (Math.PI * 0.08) + ((Math.PI * 0.84) * index) / (total - 1);
      entries[kp.id] = {
        x: anchor.x + Math.cos(angle) * radiusX,
        y: anchor.y + verticalLift + Math.sin(angle) * radiusY,
      };
    });
  }
  return entries;
});

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
  const ids = new Set(filteredKps.value.map((kp) => kp.id));
  return edges.value.filter((edge) => ids.has(edge.prereq_id) && ids.has(edge.next_id));
});

const selectedLayout = computed(() => {
  if (!selectedKp.value) return null;
  return kpPoint(selectedKp.value.id);
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

function kpPoint(id: number) {
  return kpPositions.value[id] ?? defaultKpPositions.value[id] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y };
}

function edgeLine(edge: Edge) {
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

function categoryKpLine(kp: KP) {
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

function syncFormFromSelected() {
  if (!selectedKp.value) return;
  Object.assign(form, {
    id: selectedKp.value.id,
    code: selectedKp.value.code,
    title: selectedKp.value.title,
    description: selectedKp.value.description || "",
    chapter: selectedKp.value.chapter || "",
    ability_tag: selectedKp.value.ability_tag || "",
    literacy_tag: selectedKp.value.literacy_tag || "",
    importance: selectedKp.value.importance ?? 0.5,
    difficulty: selectedKp.value.difficulty ?? 0.5,
  });
}

function resetCreateForm(chapter = "") {
  selectedType.value = "kp";
  selectedId.value = null;
  selectedCategory.value = null;
  graphEditorOpen.value = true;
  Object.assign(form, {
    id: 0,
    code: "",
    title: "",
    description: "",
    chapter,
    ability_tag: "",
    literacy_tag: "",
    importance: 0.5,
    difficulty: 0.5,
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
  selectedCategory.value = null;
  drawerOpen.value = true;
  detailTab.value = "overview";
  syncFormFromSelected();
  centerOnPoint(kpPoint(id));
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
  drawerOpen.value = true;
  detailTab.value = "overview";
  activeChapter.value = chapter;
  centerOnPoint(categoryPoint(chapter));
}

function openGraphEditorForSelected() {
  if (!selectedKp.value) return;
  syncFormFromSelected();
  graphEditorOpen.value = true;
}

function openContentWorkspace() {
  if (!selectedKp.value?.id) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  router.push({
    path: `/teacher/kp-content/${selectedKp.value.id}`,
    query: {
      subject: props.subject || undefined,
      grade: props.grade || undefined,
      from: "graph-workspace",
    },
  });
}

function startLinkSelection(modeValue: "forward" | "backward" | "related") {
  if (!selectedKp.value) return;
  linkSelectionMode.value = modeValue;
  graphEditorOpen.value = false;
  ElMessage.info(
    modeValue === "forward" ? "请选择后继知识点" : modeValue === "backward" ? "请选择前置知识点" : "请选择关联知识点",
  );
}

function cancelLinkSelection() {
  linkSelectionMode.value = null;
}

function startCategoryLinkSelection(modeValue: "prerequisite" | "related") {
  if (!selectedCategoryNode.value) return;
  categoryLinkMode.value = modeValue;
  ElMessage.info(modeValue === "prerequisite" ? "请选择后续分类节点" : "请选择关联分类节点");
}

function cancelCategoryLinkSelection() {
  categoryLinkMode.value = null;
}

function zoomIn() {
  canvasScale.value = Math.min(MAX_CANVAS_SCALE, Number((canvasScale.value + SCALE_STEP).toFixed(2)));
}

function zoomOut() {
  canvasScale.value = Math.max(MIN_CANVAS_SCALE, Number((canvasScale.value - SCALE_STEP).toFixed(2)));
}

function resetViewport() {
  canvasScale.value = DEFAULT_CANVAS_SCALE;
  panX.value = 0;
  panY.value = 0;
  activeChapter.value = "全部";
  search.value = "";
  linkSelectionMode.value = null;
  categoryLinkMode.value = null;
  syncCategoryPositions();
  syncKpPositions();
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
  const origin = type === "kp" ? kpPoint(Number(id)) : categoryPoint(String(id));
  draggingNode.value = { type, id, origin };
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
}

function onWindowMouseMove(event: MouseEvent) {
  if (draggingNode.value) {
    const dx = (event.clientX - dragStartX.value) / canvasScale.value;
    const dy = (event.clientY - dragStartY.value) / canvasScale.value;

    if (draggingNode.value.type === "kp") {
      const current = kps.value.find((kp) => kp.id === Number(draggingNode.value?.id));
      const radius = (current ? nodeRadius(current) : 80) + 18;
      const newX = Math.max(radius, Math.min(CANVAS_WIDTH - radius, draggingNode.value.origin.x + dx));
      const newY = Math.max(radius, Math.min(CANVAS_HEIGHT - radius, draggingNode.value.origin.y + dy));

      kpPositions.value = {
        ...kpPositions.value,
        [Number(draggingNode.value.id)]: {
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
  if (draggingNode.value?.type === "kp" && draggingNode.value.id) {
    const kpId = Number(draggingNode.value.id);
    const point = kpPositions.value[kpId];
    if (kpId && point) {
      try {
        await api.put(`/admin/kps/${kpId}/position`, { x: point.x, y: point.y });
      } catch {
        ElMessage.warning("节点位置保存失败，请重试");
      }
    }
  }
  if (draggingNode.value?.type === "category") {
    localStorage.setItem(chapterPositionStorageKey(), JSON.stringify(categoryPositions.value));
  }
  draggingCanvas.value = false;
  draggingNode.value = null;
}

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const [kpRes, edgeRes, chapterEdgeRes] = await Promise.all([
      api.get(`/graph/kps?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
      api.get(`/admin/edges?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&page=1&page_size=500`),
      api.get(`/admin/chapter-edges?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
    ]);
    kps.value = kpRes.data ?? [];
    edges.value = edgeRes.data.items ?? [];
    chapterEdges.value = chapterEdgeRes.data ?? [];

    const normalizedPersisted = normalizePersistedKpPositions(kps.value);
    if (useLegacyFallbackLayout.value) {
      if (!legacyLayoutWarned.value) {
        legacyLayoutWarned.value = true;
        ElMessage.info("检测到旧版图谱坐标，已自动使用新版分离布局");
      }
    }
    kpPositions.value = normalizedPersisted;

    try {
      const raw = localStorage.getItem(chapterPositionStorageKey());
      const parsed = raw ? JSON.parse(raw) : {};
      if (parsed && typeof parsed === "object") {
        const next: Record<string, Point> = {};
        for (const [key, point] of Object.entries(parsed)) {
          const x = Number((point as any)?.x);
          const y = Number((point as any)?.y);
          if (Number.isFinite(x) && Number.isFinite(y)) {
            next[key] = { x, y };
          }
        }
        categoryPositions.value = { ...categoryPositions.value, ...next };
      }
    } catch {
      // ignore invalid local cache
    }
    syncCategoryPositions();
    syncKpPositions();
    const hasSelectedKp =
      selectedType.value === "kp"
      && selectedId.value != null
      && kps.value.some((kp) => kp.id === selectedId.value);
    const hasSelectedCategory =
      selectedType.value === "category"
      && !!selectedCategory.value
      && categoryNodes.value.some((item) => item.key === selectedCategory.value);

    if (hasSelectedKp) {
      syncFormFromSelected();
    } else if (hasSelectedCategory) {
      // keep restored chapter focus
      if (activeChapter.value !== "全部" && activeChapter.value !== selectedCategory.value) {
        activeChapter.value = selectedCategory.value || "全部";
      }
    } else if (kps.value.length) {
      selectedType.value = "kp";
      selectedId.value = kps.value[0].id;
      selectedCategory.value = null;
      syncFormFromSelected();
      centerOnPoint(kpPoint(kps.value[0].id));
    }
    persistViewState();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师图谱失败");
  } finally {
    loading.value = false;
  }
}

async function saveKp() {
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
        ability_tag: form.ability_tag,
        literacy_tag: form.literacy_tag,
        importance: form.importance,
        difficulty: form.difficulty,
        pos_x: point.x,
        pos_y: point.y,
      });
      ElMessage.success("知识点已更新");
    } else {
      const draftX = INITIAL_CENTER_X + Math.random() * 240 - 120;
      const draftY = INITIAL_CENTER_Y + Math.random() * 240 - 120;
      await api.post("/admin/kps", {
        subject: props.subject,
        grade: props.grade,
        code: form.code,
        title: form.title,
        description: form.description,
        chapter: form.chapter,
        ability_tag: form.ability_tag,
        literacy_tag: form.literacy_tag,
        importance: form.importance,
        difficulty: form.difficulty,
        pos_x: draftX,
        pos_y: draftY,
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
  if (!selectedId.value || !linkSelectionMode.value) return;
  let prereqId = selectedId.value;
  let nextId = targetId;
  let relationType = "prerequisite";
  if (linkSelectionMode.value === "backward") {
    prereqId = targetId;
    nextId = selectedId.value;
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
  try {
    await api.delete(`/admin/chapter-edges/${edgeId}`);
    ElMessage.success("分类关系已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除分类关系失败");
  }
}

async function deleteEdge(edge: Edge) {
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
  return edge.relation_type === "related" ? "关联" : "前置";
}

function emitState() {
  emit("state-change", {
    kpCount: kps.value.length,
    categoryCount: categoryNodes.value.length,
    filteredCount: filteredKps.value.length,
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
    const restored = restoreViewState();
    if (!restored) {
      canvasScale.value = DEFAULT_CANVAS_SCALE;
      panX.value = 0;
      panY.value = 0;
      activeChapter.value = "全部";
      search.value = "";
      selectedType.value = "kp";
      drawerOpen.value = true;
      detailTab.value = "overview";
    }
    mutingViewStatePersist.value = false;
    load();
  },
  { immediate: true },
);

watch(filteredKps, () => {
  syncCategoryPositions();
  syncKpPositions();
});

watch(
  [kps, categoryNodes, filteredKps, selectedType, selectedId, selectedCategory],
  () => {
    emitState();
  },
  { immediate: true },
);

watch(
  [canvasScale, panX, panY, activeChapter, search, selectedType, selectedId, selectedCategory, drawerOpen, detailTab],
  () => {
    persistViewState();
  },
);

watch(
  categoryPositions,
  () => {
    if (!props.subject) return;
    localStorage.setItem(chapterPositionStorageKey(), JSON.stringify(categoryPositions.value));
  },
  { deep: true },
);

window.addEventListener("mousemove", onWindowMouseMove);
window.addEventListener("mouseup", stopDragging);

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", stopDragging);
});
</script>

<template>
  <div
    class="teacher-workbench"
    :class="{
      'teacher-workbench--fullscreen': props.fullscreen,
    }"
    v-loading="loading"
  >
    <div class="teacher-header">
      <div class="teacher-heading">
        <h1 class="teacher-title">知识图谱</h1>
        <p class="teacher-subtitle">先在左边找分类，再点中间节点，最后在右边维护内容。</p>
      </div>
      <div class="teacher-controls">
        <el-input v-model="search" placeholder="搜索知识点" clearable class="teacher-search" />
        <button
          class="teacher-btn teacher-btn--primary"
          @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)"
        >
          新建知识点
        </button>
        <button class="teacher-btn" @click="resetViewport">重置</button>
        <button class="teacher-btn teacher-btn--primary" @click="drawerOpen = !drawerOpen">
          {{ drawerVisible ? "收起右侧" : "打开右侧" }}
        </button>
      </div>
    </div>

    <div class="teacher-guide">
      <span>先找分类</span>
      <span>再点节点</span>
      <span>最后改内容或连关系</span>
    </div>

    <div
      class="teacher-content"
      :class="{
        'teacher-content--fullscreen': props.fullscreen,
        'teacher-content--drawer-collapsed': !drawerVisible,
      }"
    >
      <aside class="teacher-sidebar">
        <div class="teacher-tree">
          <button
            class="teacher-tree__create"
            @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)"
          >
            + 新建知识点
          </button>
          <div v-if="treeNodes.length === 0" class="teacher-tree__empty">
            <strong>左边现在没有可选内容</strong>
            <span>可以先清空搜索词，或先新建知识点。</span>
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

    <section
      ref="stageRef"
      class="teacher-stage"
      :class="{ 'teacher-stage--dragging': draggingCanvas }"
      @mousedown="onStageMouseDown"
      @wheel.prevent="onStageWheel"
    >
      <div class="teacher-stage__top">
        <div class="teacher-stage__top-main">
          <div class="teacher-stage__stats">
            <span class="teacher-stage__pill">分类 {{ stageStats.categories }}</span>
            <span class="teacher-stage__pill">知识点 {{ stageStats.points }}</span>
            <span class="teacher-stage__pill">关系 {{ stageStats.edges }}</span>
          </div>
          <div class="teacher-stage__legend">
            <span class="teacher-stage__legend-item">
              <i class="teacher-stage__legend-line teacher-stage__legend-line--solid"></i>
              实线：知识点关系
            </span>
            <span class="teacher-stage__legend-item">
              <i class="teacher-stage__legend-line teacher-stage__legend-line--chapter"></i>
              虚线：分类关系
            </span>
            <span class="teacher-stage__legend-item">
              <i class="teacher-stage__legend-line teacher-stage__legend-line--attach"></i>
              细虚线：分类与知识点归属
            </span>
          </div>
        </div>
        <div class="teacher-stage__actions">
          <button class="teacher-stage__button teacher-stage__button--primary" @click="resetCreateForm(selectedCategoryNode?.key || activeChapter === '全部' ? '' : activeChapter)">新建知识点</button>
          <button class="teacher-stage__button" @click="resetViewport">重置画布</button>
          <button class="teacher-stage__button" @click="detailTab = 'relations'; drawerOpen = true">管理关系</button>
        </div>
      </div>

      <svg
        class="teacher-canvas"
        :width="CANVAS_WIDTH"
        :height="CANVAS_HEIGHT"
        :style="{ transform: `translate(${panX}px, ${panY}px) scale(${canvasScale})` }"
      >
        <rect x="0" y="0" :width="CANVAS_WIDTH" :height="CANVAS_HEIGHT" fill="#f8fbff" />
        <defs>
          <marker id="teacher-edge-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(100,116,139,0.55)" />
          </marker>
          <marker id="teacher-chapter-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
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
          :stroke="edge.relation_type === 'related' ? 'rgba(74,120,213,0.42)' : 'rgba(75,94,130,0.52)'"
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
          :stroke="edge.relation_type === 'related' ? 'rgba(74,120,213,0.6)' : 'rgba(100,116,139,0.4)'"
          stroke-width="1.5"
          stroke-linecap="round"
          :marker-end="edge.relation_type === 'related' ? undefined : 'url(#teacher-edge-arrow)'"
        />

        <line
          v-for="kp in filteredKps"
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
          class="teacher-category-node"
          :transform="`translate(${categoryPoint(category.key).x}, ${categoryPoint(category.key).y})`"
          @click="selectCategory(category.key)"
          @mousedown="onNodeMouseDown($event, 'category', category.key)"
        >
          <rect x="-112" y="-44" width="224" height="88" rx="20" :fill="selectedCategory === category.key ? '#edf4ff' : '#ffffff'" :stroke="selectedCategory === category.key ? '#7fb0ff' : '#d7e2f0'" stroke-width="1.8" />
          <text class="teacher-category-node__title" text-anchor="middle" y="-6">{{ category.title }}</text>
          <text class="teacher-category-node__meta" text-anchor="middle" y="22">{{ category.total }} 个知识点</text>
        </g>

        <g
          v-for="kp in filteredKps"
          :key="kp.id"
          class="teacher-node"
          :transform="`translate(${kpPoint(kp.id).x}, ${kpPoint(kp.id).y})`"
          @click="selectKp(kp.id)"
          @mousedown="onNodeMouseDown($event, 'kp', kp.id)"
        >
          <circle :r="nodeRadius(kp) + 12" fill="rgba(96,139,232,0.14)" />
          <circle :r="nodeRadius(kp)" :fill="kp.id === selectedKp?.id ? '#eef5ff' : '#ffffff'" :stroke="kp.id === selectedKp?.id ? '#7ca9f3' : '#d7e2f0'" stroke-width="2" />
          <text class="teacher-node__code" text-anchor="middle" y="-8">{{ kp.code }}</text>
          <text class="teacher-node__title" text-anchor="middle" y="16">{{ kp.title.slice(0, 10) }}</text>
        </g>
      </svg>

      <div
        v-if="selectedKp && selectedLayout"
        class="teacher-stage__menu"
        :class="{ 'teacher-stage__menu--below': selectedMenuBelow }"
        :style="selectedMenuStyle"
      >
        <button @click="openGraphEditorForSelected">编辑节点</button>
        <button @click="detailTab = 'relations'; drawerOpen = true">连关系</button>
        <button class="danger" @click="removeKp">删除</button>
      </div>

      <div v-if="linkSelectionMode" class="teacher-stage__hint">
        <span>
          {{
            linkSelectionMode === 'forward'
              ? '连线模式：请选择后继知识点'
              : linkSelectionMode === 'backward'
                ? '连线模式：请选择前置知识点'
                : '连线模式：请选择关联知识点'
          }}
        </span>
        <button @click="cancelLinkSelection">取消</button>
      </div>

      <div v-if="categoryLinkMode" class="teacher-stage__hint teacher-stage__hint--chapter">
        <span>
          {{ categoryLinkMode === 'prerequisite' ? '分类连线模式：请选择后续分类节点' : '分类连线模式：请选择关联分类节点' }}
        </span>
        <button @click="cancelCategoryLinkSelection">取消</button>
      </div>

      <section v-if="graphEditorOpen" class="teacher-editor-float">
        <div class="teacher-editor-float__title">{{ form.id ? '编辑知识点' : '新建知识点' }}</div>
        <div class="teacher-editor-float__body">
          <el-form label-position="top" size="small">
            <div class="teacher-form-grid">
              <el-form-item label="编码"><el-input v-model="form.code" /></el-form-item>
              <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
            </div>
            <div class="teacher-form-grid">
              <el-form-item label="章节"><el-input v-model="form.chapter" /></el-form-item>
              <el-form-item label="适合培养什么能力"><el-input v-model="form.ability_tag" placeholder="例如 分析问题、动手操作" /></el-form-item>
            </div>
            <el-form-item label="适合培养什么习惯"><el-input v-model="form.literacy_tag" placeholder="例如 团队合作、规范意识" /></el-form-item>
            <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
            <div class="teacher-form-grid">
              <el-form-item label="学习重点"><el-input-number v-model="form.importance" :min="0" :max="1" :step="0.05" /></el-form-item>
              <el-form-item label="理解难度"><el-input-number v-model="form.difficulty" :min="0" :max="1" :step="0.05" /></el-form-item>
            </div>
          </el-form>
        </div>
        <div class="teacher-editor-float__actions">
          <el-button type="primary" :loading="saving" @click="saveKp">保存</el-button>
          <el-button @click="graphEditorOpen = false">收起</el-button>
        </div>
      </section>

      <div class="teacher-stage__bottom">
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

      <div v-else-if="!loading && filteredKps.length === 0" class="teacher-stage__empty">
        <strong>当前没有可显示的知识点</strong>
        <span>先选择章节、清空搜索词，或点击“新建知识点”。</span>
      </div>
    </section>

    <aside class="teacher-drawer" :class="{ open: drawerOpen }" v-if="drawerVisible">
      <div class="teacher-drawer__header">
        <h3 class="teacher-drawer__title">{{ selectedType === 'kp' ? selectedKp?.title : selectedCategoryNode?.title }}</h3>
        <button class="teacher-drawer__close" @click="drawerOpen = false">×</button>
      </div>

      <div class="teacher-drawer__content">
        <template v-if="selectedType === 'category' && selectedCategoryNode && categoryOverview">
          <div class="teacher-drawer__meta">共 {{ categoryOverview.total }} 个知识点</div>
          <div class="teacher-drawer__guide">这里显示这个分类的整体情况。先看分类里有多少知识点，再点下面的知识点进入具体编辑。</div>

          <div class="teacher-drawer__metrics teacher-drawer__metrics--triple">
            <div class="teacher-drawer__metric">
              <span>培养能力</span>
              <strong>{{ categoryOverview.abilityTags.length }}</strong>
            </div>
            <div class="teacher-drawer__metric">
              <span>培养习惯</span>
              <strong>{{ categoryOverview.literacyTags.length }}</strong>
            </div>
            <div class="teacher-drawer__metric">
              <span>节点数量</span>
              <strong>{{ categoryOverview.total }}</strong>
            </div>
          </div>

          <div class="teacher-drawer__section">
            <h4 class="teacher-drawer__section-title">这个分类主要培养</h4>
            <div v-if="categoryOverview.abilityTags.length === 0" class="teacher-drawer__empty">还没设置</div>
            <div v-else class="teacher-drawer__tags">
              <span v-for="item in categoryOverview.abilityTags" :key="item" class="teacher-drawer__tag">{{ item }}</span>
            </div>
          </div>

            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">分类下知识点</h4>
            <div class="teacher-drawer__tags">
              <button v-for="kp in categoryOverview.items" :key="kp.id" class="teacher-drawer__tag" @click="selectKp(kp.id)">
                {{ kp.title }}
              </button>
            </div>
          </div>

          <div class="teacher-drawer__actions">
            <button class="teacher-drawer__primary" @click="resetCreateForm(selectedCategoryNode.key)">在该分类下新增知识点</button>
          </div>

          <div class="teacher-drawer__section">
            <h4 class="teacher-drawer__section-title">分类关系</h4>
            <div class="teacher-drawer__actions teacher-drawer__actions--compact">
              <button class="teacher-drawer__secondary" @click="startCategoryLinkSelection('prerequisite')">新增后续分类</button>
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
                <span>{{ edge.source_chapter }} → {{ edge.target_chapter }}（{{ edge.relation_type === 'related' ? '关联' : '前置' }}）</span>
                <button @click="deleteChapterEdge(edge.id)">删除</button>
              </div>
            </div>
            <div v-else class="teacher-drawer__empty">暂无分类关系</div>
          </div>
        </template>

        <template v-else-if="selectedKp">
          <div class="teacher-drawer__tabs">
            <button :class="{ active: detailTab === 'overview' }" @click="detailTab = 'overview'">基本信息</button>
            <button :class="{ active: detailTab === 'relations' }" @click="detailTab = 'relations'">知识关系</button>
            <button :class="{ active: detailTab === 'content' }" @click="detailTab = 'content'">资源内容</button>
          </div>
          <div class="teacher-drawer__meta">{{ selectedKp.code }} · {{ selectedKp.chapter || '未分章' }}</div>
          <div class="teacher-drawer__guide">
            {{
              detailTab === 'overview'
                ? '这里只处理当前知识点的基本信息。'
                : detailTab === 'relations'
                  ? '这里只处理前置、后续和关联关系。'
                  : '资源内容单独进入一个页面处理，不和其他功能混在一起。'
            }}
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
              <h4 class="teacher-drawer__section-title">基本信息编辑</h4>
              <div class="teacher-drawer__actions">
                <button class="teacher-drawer__primary" @click="openGraphEditorForSelected">进入基本信息编辑</button>
              </div>
            </div>

            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">当前标签</h4>
              <div class="teacher-drawer__tags">
                <span class="teacher-drawer__tag">{{ selectedKp.ability_tag || "未设置能力标签" }}</span>
                <span class="teacher-drawer__tag">{{ selectedKp.literacy_tag || "未设置素养标签" }}</span>
              </div>
            </div>
          </div>

          <div v-else-if="detailTab === 'relations'">
            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">当前关系</h4>
              <div class="teacher-drawer__actions teacher-drawer__actions--compact">
                <button class="teacher-drawer__secondary" @click="startLinkSelection('forward')">新增后继</button>
                <button class="teacher-drawer__secondary" @click="startLinkSelection('backward')">新增前置</button>
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
            </div>

            <div class="teacher-drawer__section">
              <h4 class="teacher-drawer__section-title">关系删除</h4>
              <div class="teacher-drawer__relation-tip">这里只显示当前节点的直接关系，不能跨层删除更上级或更下级的关系。</div>
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
              <h4 class="teacher-drawer__section-title">资源内容入口</h4>
              <div class="teacher-drawer__guide">
                点击下面按钮，进入独立的“资源内容页面”，单独维护视频、练习和推荐资源。
              </div>
              <div class="teacher-drawer__actions">
                <button class="teacher-drawer__primary" @click="openContentWorkspace">进入资源内容页</button>
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
  min-height: calc(100vh - 190px);
  background: #ffffff;
  overflow: hidden;
  border-radius: 28px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
}

.teacher-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  gap: 16px;
  border-bottom: 1px solid #e1eaf1;
  background: #ffffff;
}

.teacher-heading {
  display: grid;
  gap: 4px;
}

.teacher-title {
  font-size: 22px;
  font-weight: 800;
  color: #243449;
  margin: 0;
}

.teacher-subtitle {
  margin: 0;
  color: #718097;
  font-size: 13px;
}

.teacher-guide {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 22px 0;
  background: #ffffff;
}

.teacher-guide span {
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

.teacher-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.teacher-search {
  width: 200px;
}

.teacher-search :deep(.el-input__wrapper) {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px #d8e2ef;
}

.teacher-search :deep(.el-input__inner) {
  color: #243449;
}

.teacher-btn {
  min-height: 40px;
  padding: 0 15px;
  border: 1px solid #d8e2ef;
  border-radius: 999px;
  background: #ffffff;
  color: #35507f;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.teacher-btn--primary {
  border-color: #cfe0fb;
  background: #edf4ff;
  color: #2459ab;
}

.teacher-btn:hover {
  background: #eff5ff;
}

.teacher-content {
  display: grid;
  grid-template-columns: minmax(248px, 280px) minmax(0, 1fr) minmax(320px, 340px);
  height: calc(100vh - 250px);
  gap: 14px;
  padding: 14px;
  min-width: 0;
  overflow: hidden;
}

.teacher-content--fullscreen {
  grid-template-columns: minmax(248px, 280px) minmax(0, 1fr) minmax(320px, 340px);
}

.teacher-content--drawer-collapsed {
  grid-template-columns: minmax(248px, 280px) minmax(0, 1fr);
}

.teacher-sidebar {
  padding: 14px;
  border-radius: 24px;
  background: #f8fbff;
  border: 1px solid #dce6f2;
  overflow-y: auto;
  color: #475569;
  z-index: 4;
}

.teacher-content--fullscreen .teacher-sidebar {
  position: static;
  width: auto;
  box-shadow: none;
}

.teacher-tree {
  display: grid;
  gap: 12px;
}

.teacher-tree__create {
  min-height: 40px;
  border: 1px solid #cfe0fb;
  border-radius: 14px;
  background: #edf4ff;
  color: #2459ab;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

.teacher-tree__create:hover {
  background: #e0ecff;
}

.teacher-tree__empty {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 18px;
  border: 1px dashed #d7e2ef;
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
  border-radius: 16px;
  background: #ffffff;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.teacher-tree__summary:hover {
  background: #eff5ff;
}

.teacher-tree__summary.active {
  background: #e3f2fd;
  color: #1565c0;
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
  border-radius: 14px;
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
  background: #f8fafc;
}

.teacher-tree__child.active {
  background: #e3f2fd;
  border-color: #90caf9;
  color: #1565c0;
}

.teacher-stage {
  position: relative;
  overflow: hidden;
  cursor: default;
  user-select: none;
  display: grid;
  grid-template-rows: 1fr auto;
  gap: 16px;
  padding: 14px;
  min-width: 0;
  border-radius: 28px;
  background: #f8fbff;
  border: 1px solid #dce6f2;
}

.teacher-stage--dragging {
  cursor: grabbing;
}

.teacher-stage__top,
.teacher-stage__bottom {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
}

.teacher-stage__top-main {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.teacher-stage__bottom {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 9;
  pointer-events: none;
}

.teacher-stage__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.teacher-stage__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.teacher-stage__legend-item {
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

.teacher-stage__legend-line {
  width: 28px;
  height: 0;
  border-top: 2px solid #64748b;
  flex: 0 0 auto;
}

.teacher-stage__legend-line--chapter {
  border-top-style: dashed;
  border-top-color: rgba(75, 94, 130, 0.7);
}

.teacher-stage__legend-line--attach {
  border-top-style: dashed;
  border-top-width: 1.5px;
  border-top-color: rgba(100, 116, 139, 0.7);
}

.teacher-stage__pill,
.teacher-stage__button {
  min-height: 38px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid #dce6f2;
  background: #ffffff;
  color: #35507f;
  font-size: 12px;
  font-weight: 500;
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
  background: #eff5ff;
}

.teacher-stage__button--primary {
  background: #edf4ff;
  border-color: #cfe0fb;
}

.teacher-stage__actions {
  justify-content: flex-end;
}

.teacher-canvas {
  display: block;
  transform-origin: 0 0;
  transition: transform 0.08s ease;
  cursor: grab;
  position: relative;
  z-index: 1;
}

.teacher-category-node,
.teacher-node {
  cursor: pointer;
}

.teacher-category-node__title,
.teacher-category-node__meta,
.teacher-node__code,
.teacher-node__title {
  fill: #243449;
  font-weight: 500;
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

.teacher-stage__menu {
  position: absolute;
  z-index: 5;
  transform: translateY(calc(-100% - 8px));
  display: flex;
  gap: 8px;
  padding: 8px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #dce6f2;
  box-shadow: 0 20px 38px rgba(15, 23, 42, 0.12);
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
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff5ff;
  color: #35507f;
  font-size: 12px;
  font-weight: 500;
  transition: background 0.2s ease;
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.teacher-stage__menu button:hover {
  background: #dfefff;
}

.teacher-stage__menu .danger {
  background: #fee2e2;
  color: #dc2626;
}

.teacher-stage__hint {
  position: absolute;
  left: 50%;
  bottom: 88px;
  transform: translateX(-50%);
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #dce6f2;
  color: #475569;
  font-size: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.teacher-stage__hint button {
  padding: 4px 8px;
  border-radius: 999px;
  background: #eff5ff;
  color: #35507f;
  font-size: 11px;
  transition: background 0.2s ease;
}

.teacher-stage__hint button:hover {
  background: #dfefff;
}

.teacher-stage__hint--chapter {
  bottom: 132px;
}

.teacher-editor-float {
  position: absolute;
  top: 94px;
  right: 28px;
  z-index: 6;
  width: 360px;
  max-height: calc(100% - 128px);
  padding: 16px;
  border-radius: 24px;
  background: #ffffff;
  border: 1px solid #dce6f2;
  box-shadow: 0 22px 40px rgba(15, 23, 42, 0.12);
  color: #475569;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.teacher-editor-float__title {
  margin-bottom: 12px;
  color: #243449;
  font-size: 16px;
  font-weight: 600;
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
  padding: 4px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dce6f2;
  box-shadow: none;
  pointer-events: auto;
}

.teacher-stage__zoom button {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #eff5ff;
  color: #35507f;
  font-size: 14px;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.teacher-stage__zoom button:hover {
  background: #dfefff;
}

.teacher-stage__zoom span {
  font-size: 12px;
  color: #35507f;
  min-width: 70px;
  text-align: center;
}

.teacher-stage__empty {
  position: absolute;
  inset: 120px 32px 88px;
  display: grid;
  place-items: center;
  gap: 8px;
  text-align: center;
  border: 1px dashed #dce6f2;
  border-radius: 24px;
  background: #ffffff;
  color: #35507f;
  z-index: 3;
}

.teacher-stage__empty strong {
  font-size: 18px;
}

.teacher-stage__empty span {
  color: #90a0b6;
}

.teacher-stage__empty-btn {
  border: 1px solid #cfe0fb;
  background: #edf4ff;
  color: #2459ab;
  border-radius: 999px;
  min-height: 40px;
  padding: 0 18px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.teacher-drawer {
  padding: 14px;
  border-radius: 24px;
  background: #f8fbff;
  border: 1px solid #dce6f2;
  overflow-y: auto;
  color: #475569;
  z-index: 5;
}

.teacher-content--fullscreen .teacher-drawer {
  position: static;
  width: auto;
  box-shadow: none;
  z-index: 5;
}

.teacher-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e1eaf1;
}

.teacher-drawer__title {
  font-size: 16px;
  font-weight: 600;
  color: #243449;
  margin: 0;
}

.teacher-drawer__close {
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 999px;
  background: #eff5ff;
  color: #35507f;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.teacher-drawer__close:hover {
  background: #dfefff;
  color: #2459ab;
}

.teacher-drawer__content {
  padding: 16px;
}

.teacher-drawer__guide {
  padding: 12px 14px;
  border-radius: 16px;
  background: #f4f8fc;
  border: 1px solid #dde7f2;
  color: #617792;
  font-size: 12px;
  line-height: 1.7;
  margin-bottom: 14px;
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
  margin-bottom: 16px;
}

.teacher-drawer__tabs button {
  border: 1px solid #dce6f2;
  padding: 8px 0;
  border-radius: 4px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.teacher-drawer__tabs button:hover {
  background: #e3f2fd;
  color: #1565c0;
}

.teacher-drawer__tabs button.active {
  background: #e3f2fd;
  border-color: #90caf9;
  color: #1565c0;
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
  background: #ffffff;
  border: 1px solid #e1eaf1;
}

.teacher-drawer__metric span {
  display: block;
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
}

.teacher-drawer__metric strong {
  font-size: 16px;
  color: #1e293b;
  font-weight: 600;
}

.teacher-drawer__section {
  margin-bottom: 20px;
}

.teacher-drawer__section-title {
  font-size: 13px;
  font-weight: 600;
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
  padding: 8px 12px;
  border: 1px solid #dce6f2;
  border-radius: 999px;
  background: #ffffff;
  color: #35507f;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s ease;
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
  border: 1px solid #e1eaf1;
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
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.teacher-drawer__primary {
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid #90caf9;
}

.teacher-drawer__primary:hover {
  background: #bbdefb;
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
  .teacher-content {
    grid-template-columns: minmax(200px, 224px) minmax(0, 1fr) minmax(260px, 300px);
    padding: 10px;
  }

  .teacher-content--drawer-collapsed {
    grid-template-columns: minmax(200px, 224px) minmax(0, 1fr);
  }

  .teacher-drawer {
    position: static;
    width: auto;
    box-shadow: none;
    z-index: 5;
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
    grid-template-columns: 1fr;
    height: calc(100vh - 280px);
    padding: 10px;
  }

  .teacher-stage__top {
    flex-direction: column;
    align-items: stretch;
  }

  .teacher-sidebar {
    display: none;
  }
}
</style>
