<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import {
  buildDeterministicGraphLayout,
  mergeChapterLayout,
  CANVAS_WIDTH,
  CANVAS_HEIGHT,
  INITIAL_CENTER_X,
  INITIAL_CENTER_Y,
} from "../graph/graphLayout";
import HoverTip from "./HoverTip.vue";
import QueryToolbar from "./QueryToolbar.vue";

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

function runWorkspaceSearch() {
  const keyword = search.value.trim();
  if (!keyword) {
    ElMessage.info("请输入知识点名称、编码或章节");
    return;
  }
  showAllKps.value = true;
  if (filteredKps.value.length === 0) {
    ElMessage.warning("未找到匹配的知识点");
    return;
  }
  const first = filteredKps.value[0];
  activeChapter.value = first.chapter || "未分章";
  selectKp(first.id);
  nextTick(() => {
    fitViewportRetryCount = 0;
    fitVisibleToViewport();
  });
}

function resetWorkspaceSearch() {
  search.value = "";
}

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

const DEFAULT_CANVAS_SCALE = 0.58;
const MIN_CANVAS_SCALE = 0.2;
const MAX_CANVAS_SCALE = 4;
const SCALE_STEP = 0.2;

type GraphPathHint = {
  next_candidate_ids: number[];
  next_titles: string[];
  can_unlock_next: boolean;
  blocked_titles: string[];
  path_summary: string;
};

type GraphRecoHint = {
  reason_summary: string;
  advice_text?: string;
  target_kp_id: number;
  target_code?: string;
  target_title?: string;
};

const props = withDefaults(
  defineProps<{
    subject: string;
    grade: string;
    currentKpId?: number | null;
    recommendedKpId?: number | null;
    highlightedKpIds?: number[] | null;
    /** 与 currentKpId 同步的路径建议（来自 /graph/path） */
    graphPathHint?: GraphPathHint | null;
    /** 与 currentKpId 同步的推荐说明（来自 /reco） */
    graphRecoHint?: GraphRecoHint | null;
    /** 嵌入学生「图谱工作台」页：隐藏重复标题区并由外层控制高度，避免整页被撑长 */
    embedded?: boolean;
    actorMode?: "student" | "teacher";
  }>(),
  { embedded: false, actorMode: "student" },
);

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
const showAllKps = ref(props.actorMode === "teacher");
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
/** 嵌入页首帧视口宽高可能为 0，适配画布需重试 */
let fitViewportRetryCount = 0;
let embeddedResizeObserver: ResizeObserver | null = null;
let embeddedResizeDebounce: ReturnType<typeof setTimeout> | null = null;
const kpPositions = ref<Record<number, Point>>({});
const categoryPositions = ref<Record<string, Point>>({});
const mutingLayoutPersist = ref(false);
const layoutRestored = ref(false);
const useLegacyFallbackLayout = ref(false);
const hoveredKpId = ref<number | null>(null);
const savingGraphLayout = ref(false);

const overlayMap = computed(() => new Map(overlay.value.map((item) => [item.kp_id, item])));
const isTeacherMode = computed(() => props.actorMode === "teacher");
const canEditLayout = computed(() => isTeacherMode.value);
const effectiveOverlayMap = computed(() => {
  const map = new Map(overlayMap.value);
  if (!isTeacherMode.value && props.recommendedKpId) {
    const current = map.get(props.recommendedKpId);
    map.set(props.recommendedKpId, {
      kp_id: props.recommendedKpId,
      mastery: current?.mastery ?? 0,
      status: current?.status ?? "not_started",
      recommended: true,
      blocked_reason: current?.blocked_reason ?? null,
      knowledge_enabled: current?.knowledge_enabled,
      ability_enabled: current?.ability_enabled,
      literacy_enabled: current?.literacy_enabled,
      knowledge_status: current?.knowledge_status,
      ability_status: current?.ability_status,
      literacy_status: current?.literacy_status,
      knowledge_label: current?.knowledge_label,
      ability_labels: current?.ability_labels,
      literacy_labels: current?.literacy_labels,
      evidence: current?.evidence,
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
    ["#15803d", "#16a34a", "#22c55e", "#4ade80", "#166534", "#14532d"],
  ),
);

const literacyColorMap = computed(() =>
  buildLabelColorMap(
    Array.from(new Set(overlay.value.flatMap((item) => item.literacy_labels ?? []).concat(kps.value.flatMap((kp) => splitLabels(kp.literacy_tag))))),
    ["#0f766e", "#14b8a6", "#38bdf8", "#7dd3fc", "#0891b2", "#22c55e"],
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

const categoryNodes = computed<CategoryNode[]>(() =>
  chapterSummary.value
    .map((item) => ({ key: item.chapter, title: item.chapter, total: item.total }))
    .sort((a, b) => a.key.localeCompare(b.key, "zh-Hans-CN")),
);

const visibleCategoryNodes = computed(() => {
  if (isTeacherMode.value || activeChapter.value === "全部") return categoryNodes.value;
  return categoryNodes.value.filter((item) => item.key === activeChapter.value);
});

const visibleCategoryKeySet = computed(() => new Set(visibleCategoryNodes.value.map((item) => item.key)));

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
  if (!showAllKps.value) return [];
  return filteredKps.value;
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

const filteredEdgeCount = computed(() => {
  const ids = new Set(filteredKps.value.map((kp) => kp.id));
  return edges.value.filter((edge) => ids.has(edge.prereq_id) && ids.has(edge.next_id)).length;
});

/** 顶部统计反映当前筛选结果，不受“是否展开全部节点”影响 */
const canvasStageStats = computed(() => ({
  categories: visibleCategoryNodes.value.length,
  points: filteredKps.value.length,
  edges: filteredEdgeCount.value,
}));

const deterministicLayout = computed(() =>
  buildDeterministicGraphLayout(kps.value.map((kp) => ({ id: kp.id, code: kp.code, chapter: kp.chapter }))),
);
const defaultCategoryPositions = computed<Record<string, Point>>(() => deterministicLayout.value.categoryPositions);
const defaultKpPositions = computed<Record<number, Point>>(() => deterministicLayout.value.kpPositions);

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
  const categoryKeys = visibleCategoryKeySet.value;
  for (const edge of visibleEdges.value) {
    const source = kps.value.find((item) => item.id === edge.prereq_id)?.chapter || "未分章";
    const target = kps.value.find((item) => item.id === edge.next_id)?.chapter || "未分章";
    if (source === target) continue;
    if (!categoryKeys.has(source) || !categoryKeys.has(target)) continue;
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

const drawerVisible = computed(() => drawerOpen.value && (selectedKp.value != null || selectedCategoryNode.value != null));
type DrawerTab = "overview" | "resource" | "relation" | "evidence" | "goals";
const drawerTab = ref<DrawerTab>("overview");
const drawerTabOrder: DrawerTab[] = ["overview", "resource", "relation", "evidence", "goals"];
const drawerTabLabelMap: Record<DrawerTab, string> = {
  overview: "概览",
  resource: "资源",
  relation: "关系",
  evidence: "证据",
  goals: "目标",
};
const drawerTabDone = computed<Record<DrawerTab, boolean>>(() => {
  const hasResource = (nodeDetail.value?.resource_list?.length ?? 0) > 0;
  const hasRelation =
    (nodeDetail.value?.prerequisites?.length ?? 0) > 0 ||
    (nodeDetail.value?.downstream?.length ?? 0) > 0 ||
    (nodeDetail.value?.related?.length ?? 0) > 0;
  const hasEvidence = !!formatEvidenceSummary(nodeDetail.value?.overlay?.evidence as Record<string, unknown>);
  const hasGoals = !!(
    activeOverlay.value?.knowledge_label ||
    selectedKp.value?.knowledge_tag ||
    (activeOverlay.value?.ability_labels?.length ?? 0) > 0 ||
    (activeOverlay.value?.literacy_labels?.length ?? 0) > 0 ||
    selectedKp.value?.ability_tag ||
    selectedKp.value?.literacy_tag
  );
  return {
    overview: true,
    resource: hasResource,
    relation: hasRelation,
    evidence: hasEvidence,
    goals: hasGoals,
  };
});
const drawerNextTab = computed<DrawerTab | null>(() => {
  const idx = drawerTabOrder.indexOf(drawerTab.value);
  if (idx < 0 || idx >= drawerTabOrder.length - 1) return null;
  return drawerTabOrder[idx + 1];
});
const drawerFlowHint = computed(() => {
  const next = drawerNextTab.value;
  if (!next) return "已到最后一步，可返回“概览”或直接去学习。";
  if (!drawerTabDone.value[next]) return `建议下一步：${drawerTabLabelMap[next]}（当前暂无数据，可先继续后续步骤）。`;
  return `建议下一步：${drawerTabLabelMap[next]}。`;
});

function categoryPoint(key: string) {
  return categoryPositions.value[key] ?? defaultCategoryPositions.value[key] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y - 360 };
}

function kpPoint(id: number) {
  return kpPositions.value[id] ?? defaultKpPositions.value[id] ?? { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y };
}

function clampPoint(point: Point, type: "kp" | "category", kp?: GraphKp | null): Point {
  if (type === "category") {
    return {
      x: Math.max(140, Math.min(CANVAS_WIDTH - 140, point.x)),
      y: Math.max(84, Math.min(CANVAS_HEIGHT - 84, point.y)),
    };
  }
  const radius = kp ? nodeRadius(kp) + 24 : 110;
  return {
    x: Math.max(radius, Math.min(CANVAS_WIDTH - radius, point.x)),
    y: Math.max(radius, Math.min(CANVAS_HEIGHT - radius, point.y)),
  };
}

function stageClientToCanvasPoint(clientX: number, clientY: number): Point {
  const rect = stageRef.value?.getBoundingClientRect();
  if (!rect) return { x: INITIAL_CENTER_X, y: INITIAL_CENTER_Y };
  return {
    x: (clientX - rect.left - panX.value) / canvasScale.value,
    y: (clientY - rect.top - panY.value) / canvasScale.value,
  };
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

function persistStudentLayout() {
  return;
}

async function persistGraphLayoutChange(node: DragNode | null) {
  if (!node || !canEditLayout.value || !props.subject) return;
  try {
    savingGraphLayout.value = true;
    if (node.type === "kp" && typeof node.id === "number") {
      const point = kpPositions.value[node.id];
      if (!point) return;
      await api.put(`/admin/kps/${node.id}/position`, { x: point.x, y: point.y });
      return;
    }
    if (node.type === "category" && typeof node.id === "string") {
      await api.put("/admin/graph/chapter-layout", {
        subject: props.subject,
        grade: props.grade,
        chapters: categoryPositions.value,
      });
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存图谱布局失败");
  } finally {
    savingGraphLayout.value = false;
  }
}

function persistStudentViewState() {
  if (isTeacherMode.value && props.embedded) return;
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

function restoreStudentViewState() {
  if (isTeacherMode.value && props.embedded) {
    mutingLayoutPersist.value = true;
    try {
      canvasScale.value = DEFAULT_CANVAS_SCALE;
      panX.value = 0;
      panY.value = 0;
      activeChapter.value = "全部";
      search.value = "";
      drawerOpen.value = true;
      sidebarOpen.value = true;
      selectedType.value = "kp";
      selectedId.value = null;
      selectedCategory.value = null;
      showAllKps.value = true;
      return false;
    } finally {
      mutingLayoutPersist.value = false;
    }
  }
  const key = studentViewStateStorageKey();
  if (!key) return false;
  const raw = localStorage.getItem(key);
  if (!raw) return false;
  try {
    const parsed = JSON.parse(raw) as Partial<StudentWorkspaceViewState>;
    mutingLayoutPersist.value = true;
    // 嵌入学生页不恢复平移/缩放：不同容器宽度下旧值会把图画到视野外，表现为「空白画布」
    if (!props.embedded) {
      const nextScale = Number(parsed.canvasScale ?? DEFAULT_CANVAS_SCALE);
      const nextPanX = Number(parsed.panX ?? 0);
      const nextPanY = Number(parsed.panY ?? 0);
      canvasScale.value = Math.min(MAX_CANVAS_SCALE, Math.max(MIN_CANVAS_SCALE, nextScale));
      panX.value = Number.isFinite(nextPanX) ? nextPanX : 0;
      panY.value = Number.isFinite(nextPanY) ? nextPanY : 0;
    } else {
      canvasScale.value = DEFAULT_CANVAS_SCALE;
      panX.value = 0;
      panY.value = 0;
    }
    activeChapter.value = typeof parsed.activeChapter === "string" && parsed.activeChapter ? parsed.activeChapter : "全部";
    search.value = typeof parsed.search === "string" ? parsed.search : "";
    drawerOpen.value = true;
    sidebarOpen.value = true;
    selectedType.value = parsed.selectedType === "category" ? "category" : "kp";
    selectedId.value = Number.isFinite(Number(parsed.selectedId)) ? Number(parsed.selectedId) : null;
    selectedCategory.value = typeof parsed.selectedCategory === "string" ? parsed.selectedCategory : null;
    showAllKps.value = true;
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

  if (!isTeacherMode.value && showAllKps.value && activeChapter.value === "全部" && firstChapter) {
    selectedType.value = "category";
    selectedCategory.value = firstChapter;
    activeChapter.value = firstChapter;
    showAllKps.value = true;
    changed = true;
  }

  if (!showAllKps.value && !selectedId.value && !selectedCategory.value) {
    selectedType.value = "category";
    selectedCategory.value = firstChapter;
    activeChapter.value = "全部";
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

function edgeTouchesHover(edge: GraphEdge) {
  const h = hoveredKpId.value;
  if (h == null) return false;
  return edge.prereq_id === h || edge.next_id === h;
}

function edgeStroke(edge: GraphEdge) {
  if (isPathEdge(edge)) return "#22c55e";
  if (edgeTouchesHover(edge)) return "#14b8a6";
  if (edge.relation_type === "support") return "#46a57b";
  if (edge.relation_type === "contains") return "#db9d37";
  if (edge.relation_type === "related") return "rgba(20, 184, 166, 0.52)";
  return "rgba(71,85,105,0.78)";
}

function edgeDasharray(edge: GraphEdge) {
  if (isPathEdge(edge)) return "8 5";
  if (edge.relation_type === "support") return "10 6";
  if (edge.relation_type === "contains") return "2 6";
  return undefined;
}

function edgeWidth(edge: GraphEdge) {
  if (isPathEdge(edge)) return 2.8;
  if (edgeTouchesHover(edge)) return 3.2;
  if (edge.relation_type === "contains") return 2.2;
  if (edge.relation_type === "support") return 2.1;
  return 1.6;
}

function edgeMarker(edge: GraphEdge) {
  if (edge.relation_type === "related") return undefined;
  if (isPathEdge(edge)) return "url(#teacher-edge-arrow-path)";
  if (edge.relation_type === "support") return "url(#teacher-edge-arrow-triangle)";
  if (edge.relation_type === "contains") return "url(#teacher-edge-arrow-open)";
  return "url(#teacher-edge-arrow)";
}

function chapterEdgeStroke(edge: ChapterEdge) {
  if (edge.relation_type === "related") return "rgba(20, 184, 166, 0.36)";
  if (edge.relation_type === "support") return "rgba(70,165,123,0.5)";
  return "rgba(75,94,130,0.52)";
}

function nodeRadius(kp: GraphKp) {
  const base = 62 + Math.round((kp.importance ?? 0.5) * 16);
  if (kp.id === selectedKp.value?.id) return base + 10;
  if (isRecommended(kp.id)) return base + 6;
  return base;
}

function dimensionBadgeFill(level: "knowledge" | "ability" | "literacy", labels?: string[]) {
  if (level === "ability") {
    const label = labels?.[0];
    if (label && abilityColorMap.value.has(label)) return abilityColorMap.value.get(label) as string;
    return "#24a36f";
  }
  if (level === "literacy") {
    const label = labels?.[0];
    if (label && literacyColorMap.value.has(label)) return literacyColorMap.value.get(label) as string;
    return "#d58b2a";
  }
  return "#3978d8";
}

function dimensionBadgeOpacity(status?: string, enabled = true) {
  if (!enabled) return 0.2;
  if (status === "achieved" || status === "mastered") return 1;
  if (status === "in_progress" || status === "learning") return 0.72;
  return 0.42;
}

function dimensionBadgeStroke(status?: string, enabled = true) {
  if (!enabled) return "rgba(148, 163, 184, 0.58)";
  if (status === "achieved" || status === "mastered") return "rgba(15, 23, 42, 0.24)";
  if (status === "in_progress" || status === "learning") return "rgba(15, 23, 42, 0.18)";
  return "rgba(100, 116, 139, 0.28)";
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

const learningHintsActive = computed(
  () =>
    props.currentKpId != null &&
    selectedType.value === "kp" &&
    selectedId.value === props.currentKpId,
);

function formatEvidenceSummary(ev: Record<string, unknown> | null | undefined): string {
  if (!ev || typeof ev !== "object") return "";
  const practiceT = Number(ev.practice_total ?? 0);
  const practiceC = Number(ev.practice_correct ?? 0);
  const quizT = Number(ev.quiz_total ?? 0);
  const quizP = Number(ev.quiz_passed ?? 0);
  const vidS = Number(ev.video_started ?? 0);
  const vidC = Number(ev.video_completed ?? 0);
  const visits = Number(ev.resource_visits ?? 0);
  const mastery = Number(ev.mastery ?? 0);
  const parts: string[] = [];
  if (practiceT > 0) parts.push(`练习答对 ${practiceC}/${practiceT} 次`);
  if (quizT > 0) parts.push(`小测通过 ${quizP}/${quizT} 次`);
  if (vidC > 0) parts.push("视频已完播");
  else if (vidS > 0) parts.push("视频已学习");
  if (visits > 0) parts.push(`资源访问 ${visits} 次`);
  parts.push(`掌握度约 ${Math.round(mastery * 100)}%`);
  return parts.join("；");
}

function nextStepTitle(index: number): string {
  const h = props.graphPathHint;
  if (!h) return "";
  return h.next_titles[index] || `知识点 #${h.next_candidate_ids[index] ?? ""}`;
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
  if (!props.subject) {
    kps.value = [];
    edges.value = [];
    overlay.value = [];
    selectedId.value = null;
    selectedCategory.value = null;
    nodeDetail.value = null;
    return;
  }
  loading.value = true;
  try {
    let baseKps: GraphKp[] = [];
    let baseEdges: GraphEdge[] = [];
    let overlayRows: OverlayNode[] = [];
    let chapterLayout: Record<string, { x: number; y: number }> = {};
    try {
      const res = await api.get(`/graph/map?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
      baseKps = res.data.base?.kps ?? [];
      baseEdges = res.data.base?.edges ?? [];
      overlayRows = res.data.overlay ?? [];
      chapterLayout = (res.data.base?.chapter_layout ?? {}) as Record<string, { x: number; y: number }>;
    } catch (mapError) {
      const [kpRes, edgeRes] = await Promise.all([
        api.get("/graph/kps", { params: { subject: props.subject, grade: props.grade } }),
        api.get("/graph/edges", { params: { subject: props.subject, grade: props.grade } }),
      ]);
      baseKps = kpRes.data ?? [];
      baseEdges = edgeRes.data ?? [];
      overlayRows = [];
      chapterLayout = {};
      console.warn("Graph map overlay failed; rendering base graph fallback.", mapError);
    }
    kps.value = baseKps;
    edges.value = baseEdges;
    overlay.value = overlayRows;

    const normalizedPersisted = normalizePersistedKpPositions(kps.value);

    const restoredView = restoreStudentViewState();
    layoutRestored.value = restoredView;
    kpPositions.value = normalizedPersisted;

    const det = buildDeterministicGraphLayout(
      kps.value.map((kp) => ({ id: kp.id, code: kp.code, chapter: kp.chapter })),
    );
    categoryPositions.value = mergeChapterLayout(det.categoryPositions, chapterLayout);

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
    kps.value = [];
    edges.value = [];
    overlay.value = [];
    selectedId.value = null;
    selectedCategory.value = null;
    nodeDetail.value = null;
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.detail ?? "加载知识图谱失败");
    }
  } finally {
    loading.value = false;
  }
}

function applyInitialCenterAfterLoad() {
  // 嵌入页必须根据当前视口重新适配，不能因「已恢复视图」跳过（否则节点在画布外）
  if (props.embedded) {
    fitViewportRetryCount = 0;
    nextTick(() => {
      if (visibleKps.value.length > 0) {
        fitVisibleToViewport();
        requestAnimationFrame(() => fitVisibleToViewport());
        requestAnimationFrame(() => requestAnimationFrame(() => fitVisibleToViewport()));
        return;
      }
      fitCategoryNodesToViewport();
      requestAnimationFrame(() => fitCategoryNodesToViewport());
      requestAnimationFrame(() => requestAnimationFrame(() => fitCategoryNodesToViewport()));
    });
    return;
  }
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
    const res = await api.get(`/graph/node/${id}`, { skipGlobalLoading: true } as any);
    nodeDetail.value = res.data;
  } catch (e: any) {
    nodeDetail.value = null;
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.detail ?? "加载节点详情失败");
    }
  }
}

function selectKp(id: number) {
  selectedType.value = "kp";
  selectedId.value = id;
  selectedCategory.value = selectedKp.value?.chapter || kps.value.find((item) => item.id === id)?.chapter || null;
  if (!isTeacherMode.value && selectedCategory.value) {
    activeChapter.value = selectedCategory.value;
    showAllKps.value = true;
  }
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
  if (!isTeacherMode.value && blockedReason) {
    ElMessage.warning(blockedReason);
    return;
  }
  emit("open-content", selectedKp.value.id);
}

function selectCategory(chapter: string) {
  const shouldCollapseStudentChapter =
    !isTeacherMode.value &&
    showAllKps.value &&
    selectedType.value === "category" &&
    selectedCategory.value === chapter &&
    activeChapter.value === chapter;

  selectedType.value = "category";
  selectedCategory.value = chapter;
  selectedId.value = null;
  nodeDetail.value = null;
  activeChapter.value = shouldCollapseStudentChapter ? "全部" : chapter;
  showAllKps.value = !shouldCollapseStudentChapter;
  drawerOpen.value = true;
  if (isTeacherMode.value) {
    centerOnPoint(categoryPoint(chapter));
    return;
  }
  nextTick(() => {
    fitViewportRetryCount = 0;
    if (shouldCollapseStudentChapter) {
      fitCategoryNodesToViewport();
      return;
    }
    fitVisibleToViewport();
  });
}

function toggleAllKps() {
  const next = !showAllKps.value;
  showAllKps.value = next;
  activeChapter.value = "全部";
  ElMessage.success(next ? "已显示全部节点" : "已仅显示方形节点");
  nextTick(() => {
    fitViewportRetryCount = 0;
    if (next) {
      fitVisibleToViewport();
      return;
    }
    fitCategoryNodesToViewport();
  });
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

function fitVisibleToViewport() {
  if (!stageRef.value) return;
  if (visibleKps.value.length === 0) {
    fitCategoryNodesToViewport();
    return;
  }
  const sw0 = stageRef.value.clientWidth;
  const sh0 = stageRef.value.clientHeight;
  if (sw0 < 48 || sh0 < 48) {
    if (fitViewportRetryCount < 12) {
      fitViewportRetryCount += 1;
      requestAnimationFrame(() => fitVisibleToViewport());
    }
    return;
  }
  fitViewportRetryCount = 0;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const item of visibleCategoryNodes.value) {
    const p = categoryPoint(item.key);
    const halfW = 132;
    const halfH = 56;
    minX = Math.min(minX, p.x - halfW);
    maxX = Math.max(maxX, p.x + halfW);
    minY = Math.min(minY, p.y - halfH);
    maxY = Math.max(maxY, p.y + halfH);
  }
  for (const kp of visibleKps.value) {
    const p = kpPoint(kp.id);
    const r = nodeRadius(kp) + 28;
    minX = Math.min(minX, p.x - r);
    maxX = Math.max(maxX, p.x + r);
    minY = Math.min(minY, p.y - r);
    maxY = Math.max(maxY, p.y + r);
  }
  const w = maxX - minX || 1;
  const h = maxY - minY || 1;
  const pad = 100;
  const scale = Math.min((sw0 - pad) / w, (sh0 - pad) / h, DEFAULT_CANVAS_SCALE);
  canvasScale.value = Math.max(MIN_CANVAS_SCALE, Math.min(MAX_CANVAS_SCALE, Number(scale.toFixed(4))));
  const sw = stageRef.value.clientWidth;
  const sh = stageRef.value.clientHeight;
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  panX.value = sw / 2 - cx * canvasScale.value;
  panY.value = sh / 2 - cy * canvasScale.value;
  persistStudentViewState();
}

function fitCategoryNodesToViewport() {
  if (!stageRef.value || visibleCategoryNodes.value.length === 0) return;
  const sw0 = stageRef.value.clientWidth;
  const sh0 = stageRef.value.clientHeight;
  if (sw0 < 48 || sh0 < 48) return;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const item of visibleCategoryNodes.value) {
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
  const scale = Math.min((sw0 - pad) / w, (sh0 - pad) / h, DEFAULT_CANVAS_SCALE);
  canvasScale.value = Math.max(MIN_CANVAS_SCALE, Math.min(MAX_CANVAS_SCALE, Number(scale.toFixed(4))));
  const sw = stageRef.value.clientWidth;
  const sh = stageRef.value.clientHeight;
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  panX.value = sw / 2 - cx * canvasScale.value;
  panY.value = sh / 2 - cy * canvasScale.value;
  persistStudentViewState();
}

function resetViewport() {
  canvasScale.value = DEFAULT_CANVAS_SCALE;
  search.value = "";
  syncCategoryPositions();
  syncKpPositions();
  if (!isTeacherMode.value) {
    const targetChapter = selectedCategory.value || selectedKp.value?.chapter || categoryNodes.value[0]?.key || "全部";
    activeChapter.value = targetChapter;
    selectedType.value = selectedId.value ? "kp" : "category";
    selectedCategory.value = targetChapter === "全部" ? null : targetChapter;
    showAllKps.value = true;
    nextTick(() => {
      fitViewportRetryCount = 0;
      fitVisibleToViewport();
    });
    return;
  }
  activeChapter.value = "全部";
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
  if (
    target?.closest(".workspace-node") ||
    target?.closest(".workspace-category-node") ||
    target?.closest(".teacher-node") ||
    target?.closest(".teacher-category-node")
  ) {
    return;
  }
  draggingCanvas.value = true;
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
  dragOriginX.value = panX.value;
  dragOriginY.value = panY.value;
}

function onNodeMouseDown(event: MouseEvent, type: "kp" | "category", id: number | string) {
  event.stopPropagation();
  if (!canEditLayout.value) return;
  draggingCanvas.value = false;
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
  if (type === "kp" && typeof id === "number") {
    const point = kpPoint(id);
    dragOriginX.value = point.x;
    dragOriginY.value = point.y;
  } else {
    const point = categoryPoint(String(id));
    dragOriginX.value = point.x;
    dragOriginY.value = point.y;
  }
  draggingNode.value = {
    type,
    id,
    origin: { x: dragOriginX.value, y: dragOriginY.value },
  };
}

function onWindowMouseMove(event: MouseEvent) {
  if (draggingNode.value) {
    const pointer = stageClientToCanvasPoint(event.clientX, event.clientY);
    if (draggingNode.value.type === "kp" && typeof draggingNode.value.id === "number") {
      const kp = kps.value.find((item) => item.id === draggingNode.value?.id) ?? null;
      kpPositions.value = {
        ...kpPositions.value,
        [draggingNode.value.id]: clampPoint(pointer, "kp", kp),
      };
      return;
    }
    if (draggingNode.value.type === "category" && typeof draggingNode.value.id === "string") {
      categoryPositions.value = {
        ...categoryPositions.value,
        [draggingNode.value.id]: clampPoint(pointer, "category"),
      };
      return;
    }
  }
  if (!draggingCanvas.value) return;
  panX.value = dragOriginX.value + (event.clientX - dragStartX.value);
  panY.value = dragOriginY.value + (event.clientY - dragStartY.value);
}

function stopDragging() {
  const dragNode = draggingNode.value;
  draggingCanvas.value = false;
  draggingNode.value = null;
  void persistGraphLayoutChange(dragNode);
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

watch([selectedType, selectedId, selectedCategory], () => {
  drawerTab.value = "overview";
});

watch(visibleKps, () => {
  syncCategoryPositions();
  syncKpPositions();
  normalizeStudentSelectionState();
  if (props.embedded) {
    nextTick(() => {
      fitViewportRetryCount = 0;
      fitVisibleToViewport();
    });
  }
});

watch(
  [canvasScale, panX, panY, activeChapter, search, drawerOpen, sidebarOpen, selectedType, selectedId, selectedCategory, showAllKps],
  () => {
    persistStudentViewState();
  },
);

window.addEventListener("mousemove", onWindowMouseMove);
window.addEventListener("mouseup", stopDragging);

watch(
  () => [loading.value, props.embedded, stageRef.value] as const,
  ([ld, emb, el]) => {
    embeddedResizeObserver?.disconnect();
    embeddedResizeObserver = null;
    if (ld || !emb || !el) return;
    nextTick(() => {
      fitViewportRetryCount = 0;
      if (visibleKps.value.length > 0) {
        fitVisibleToViewport();
        requestAnimationFrame(() => fitVisibleToViewport());
        return;
      }
      fitCategoryNodesToViewport();
      requestAnimationFrame(() => fitCategoryNodesToViewport());
    });
    embeddedResizeObserver = new ResizeObserver(() => {
      if (!props.embedded) return;
      if (embeddedResizeDebounce) clearTimeout(embeddedResizeDebounce);
      embeddedResizeDebounce = setTimeout(() => {
        embeddedResizeDebounce = null;
        fitViewportRetryCount = 0;
        if (visibleKps.value.length > 0) {
          fitVisibleToViewport();
          return;
        }
        fitCategoryNodesToViewport();
      }, 100);
    });
    embeddedResizeObserver.observe(el);
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  embeddedResizeObserver?.disconnect();
  embeddedResizeObserver = null;
  if (embeddedResizeDebounce) clearTimeout(embeddedResizeDebounce);
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", stopDragging);
});
</script>

<template>
  <div
    v-loading="loading"
    class="workspace-shell"
    :class="{
      'workspace-shell--embedded': props.embedded,
    }"
  >
    <div v-if="!props.embedded" class="workspace-header">
      <div class="workspace-heading">
        <h1 class="workspace-title">课程知识图谱</h1>
        <p class="workspace-subtitle">左侧查看章节与筛选，中部浏览知识图谱，右侧查看当前知识点的学习信息。</p>
      </div>
      <div class="workspace-controls">
        <QueryToolbar
          v-model="search"
          placeholder="请输入知识点名称、编码或章节"
          hint="请输入知识点名称、编码或章节"
          input-width="420px"
          @search="runWorkspaceSearch"
          @reset="resetWorkspaceSearch"
        >
          <template #extras>
            <button class="workspace-btn" @click="fitVisibleToViewport">适应画布</button>
            <button class="workspace-btn" @click="resetViewport">重置画布</button>
          </template>
        </QueryToolbar>
      </div>
    </div>

    <div v-if="!props.embedded" class="workspace-guide">
      <span>图谱说明</span>
      <HoverTip content="先在左边找分类，再点中间节点，最后在右边看资源和前后关系。" />
    </div>

    <div
      :class="['workspace-content', { 'workspace-content--embedded': props.embedded, 'workspace-content--drawer-collapsed': props.embedded && !drawerVisible }]"
    >
      <aside v-if="!props.embedded" class="workspace-sidebar">
        <div class="workspace-tree">
          <div v-if="treeNodes.length === 0" class="workspace-tree__empty">
            <strong>左边现在没有可选内容</strong>
            <span>可以先清空搜索词，或换一门课程再查看。</span>
          </div>
          <div v-for="item in treeNodes" :key="item.key" class="workspace-tree__group">
            <div :class="['workspace-tree__summary', { active: activeChapter === item.key }]" @click="selectCategory(item.key)">
              <span>{{ item.title }}</span>
              <span class="workspace-tree__count">{{ item.children.length }}</span>
            </div>
            <div class="workspace-tree__children" v-if="activeChapter === item.key || (isTeacherMode && activeChapter === '全部')">
              <button
                v-for="kp in item.children"
                :key="kp.id"
                :class="['workspace-tree__child', { active: kp.id === selectedKp?.id }]"
                @click="selectKp(kp.id)"
              >
                <span>{{ kp.title }}</span>
                <small v-if="props.embedded">{{ kp.code }}</small>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <section :class="['workspace-stage', { 'workspace-stage--dragging': draggingCanvas, 'workspace-stage--embedded': props.embedded }]">
        <template v-if="props.embedded">
          <div class="workspace-stage__top">
            <div class="workspace-stage__top-main">
              <div class="workspace-stage__stats">
                <span class="workspace-stage__pill">分类 {{ canvasStageStats.categories }}</span>
                <span class="workspace-stage__pill">知识点 {{ canvasStageStats.points }}</span>
                <span class="workspace-stage__pill">关系 {{ canvasStageStats.edges }}</span>
              </div>
              <div class="workspace-stage__legend">
                <span class="workspace-stage__legend-item">
                  <i class="workspace-stage__legend-line workspace-stage__legend-line--solid"></i>
                  {{ isTeacherMode ? "实线箭头：前置 / 后继关系" : "实线箭头：前置 / 顺序关系" }}
                </span>
                <span class="workspace-stage__legend-item">
                  <i class="workspace-stage__legend-line workspace-stage__legend-line--dashed"></i>
                  虚线 / 三角箭头：支撑、包含、分类归属
                </span>
                <span v-if="!isTeacherMode" class="workspace-stage__legend-item">
                  <i class="workspace-stage__legend-line workspace-stage__legend-line--path"></i>
                  蓝色虚线：推荐路径；同名能力/素养标签共用同色环
                </span>
              </div>
            </div>
            <div class="workspace-stage__focus">
              <button type="button" class="workspace-stage__learn-btn workspace-stage__learn-btn--ghost" @click.stop="toggleAllKps">
                {{ showAllKps ? "仅显示方形节点" : "展开全部节点" }}
              </button>
              <button
                v-if="selectedType === 'kp' && selectedKp"
                type="button"
                class="workspace-stage__learn-btn workspace-stage__learn-btn--ghost"
                @click.stop="openContentFromSelected"
              >
                {{ isTeacherMode ? "进入配置页" : "去学习" }}
              </button>
              <button type="button" class="workspace-stage__learn-btn workspace-stage__learn-btn--ghost" @click="fitVisibleToViewport">适应画布</button>
              <button type="button" class="workspace-stage__learn-btn workspace-stage__learn-btn--ghost" @click="resetViewport">重置画布</button>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="workspace-stage__top">
            <div class="workspace-stage__top-main">
              <div class="workspace-stage__stats">
                <span class="workspace-stage__pill">分类 {{ visibleCategoryNodes.length }}</span>
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
                  蓝色虚线：推荐路径；同名能力/素养标签共用同色环，便于分组
                </span>
                <span class="workspace-stage__legend-item">
                  <i class="workspace-stage__legend-dimensions">
                    <span class="dim dim--knowledge">知</span>
                    <span class="dim dim--ability">能</span>
                    <span class="dim dim--literacy">素</span>
                  </i>
                  节点徽标：知识 / 能力 / 素养；颜色区分维度，深浅表示达成状态
                </span>
              </div>
            </div>
            <div class="workspace-stage__focus">
              <button v-if="isTeacherMode" class="workspace-stage__learn-btn workspace-stage__learn-btn--ghost" @click.stop="toggleAllKps">
                {{ showAllKps ? "仅显示方形节点" : "展开全部节点" }}
              </button>
              <button v-if="selectedType === 'kp' && selectedKp" class="workspace-stage__learn-btn" @click.stop="openContentFromSelected">
                去学习
              </button>
            </div>
          </div>
        </template>
        <div
          ref="stageRef"
          class="workspace-stage__viewport"
          @mousedown="onStageMouseDown"
          @wheel.prevent="onStageWheel"
        >
        <svg
          class="workspace-canvas"
          width="100%"
          height="100%"
        >
          <defs>
            <marker id="teacher-edge-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(100,116,139,0.55)" />
            </marker>
            <marker id="teacher-edge-arrow-path" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#5a8ef0" />
            </marker>
            <marker id="teacher-edge-arrow-triangle" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 1 1 L 9 5 L 1 9 z" fill="#46a57b" />
            </marker>
            <marker id="teacher-edge-arrow-open" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 1 1 L 9 5 L 1 9" fill="none" stroke="#db9d37" stroke-width="1.5" />
            </marker>
            <marker id="teacher-chapter-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(75,94,130,0.55)" />
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
              :stroke="chapterEdgeStroke(edge)"
              stroke-width="2.2"
              stroke-dasharray="6 6"
              :marker-end="edge.relation_type === 'related' ? undefined : 'url(#teacher-chapter-arrow)'"
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
              v-for="category in visibleCategoryNodes"
              :key="category.key"
              :class="props.embedded ? 'teacher-category-node workspace-category-node' : 'workspace-category-node'"
              :transform="`translate(${categoryPoint(category.key).x}, ${categoryPoint(category.key).y})`"
              @click="selectCategory(category.key)"
              @mousedown="onNodeMouseDown($event, 'category', category.key)"
            >
              <rect x="-112" y="-44" width="224" height="88" rx="20" :fill="selectedCategory === category.key ? '#eef8ff' : '#ffffff'" :stroke="selectedCategory === category.key ? '#60a5fa' : 'rgba(31, 41, 55, 0.14)'" stroke-width="1.8" />
              <text
                :class="props.embedded ? 'teacher-category-node__title workspace-category-node__title' : 'workspace-category-node__title'"
                text-anchor="middle"
                y="-6"
              >
                {{ category.title }}
              </text>
              <text
                :class="props.embedded ? 'teacher-category-node__meta workspace-category-node__meta' : 'workspace-category-node__meta'"
                text-anchor="middle"
                y="22"
              >
                {{ category.total }} 个知识点
              </text>
            </g>

            <g
              v-for="kp in visibleKps"
              :key="kp.id"
              :class="props.embedded ? 'teacher-node workspace-node' : 'workspace-node'"
              :transform="`translate(${kpPoint(kp.id).x}, ${kpPoint(kp.id).y})`"
              @click="selectKp(kp.id)"
              @mousedown="onNodeMouseDown($event, 'kp', kp.id)"
              @mouseenter="hoveredKpId = kp.id"
              @mouseleave="hoveredKpId = null"
            >
              <circle :r="nodeRadius(kp) + 22" :fill="!isTeacherMode && (isRecommended(kp.id) || isPathNode(kp.id)) ? 'rgba(34, 197, 94, 0.14)' : 'rgba(20, 184, 166, 0.08)'" />
              <circle
                :r="nodeRadius(kp)"
                :fill="kp.id === selectedKp?.id ? '#eef8ff' : ((!isTeacherMode && (isRecommended(kp.id) || isPathNode(kp.id))) ? '#f8fbff' : '#ffffff')"
                :stroke="kp.id === selectedKp?.id ? '#3b82f6' : ((!isTeacherMode && (isRecommended(kp.id) || isPathNode(kp.id))) ? '#14b8a6' : 'rgba(31, 41, 55, 0.14)')"
                :stroke-width="!isTeacherMode && isRecommended(kp.id) ? 2.6 : (!isTeacherMode && isPathNode(kp.id) ? 2.3 : 2)"
              />
              <g class="workspace-node__dimensions" :transform="`translate(0, ${-nodeRadius(kp) - 28})`">
                <g transform="translate(-38, 0)">
                  <rect x="-13" y="-10" width="26" height="20" rx="10" :fill="dimensionBadgeFill('knowledge')" :opacity="dimensionBadgeOpacity(effectiveOverlayMap.get(kp.id)?.knowledge_status, effectiveOverlayMap.get(kp.id)?.knowledge_enabled !== false)" :stroke="dimensionBadgeStroke(effectiveOverlayMap.get(kp.id)?.knowledge_status, effectiveOverlayMap.get(kp.id)?.knowledge_enabled !== false)" stroke-width="1.2" />
                  <text class="workspace-node__dimension-label" text-anchor="middle" y="5">知</text>
                </g>
                <g transform="translate(0, 0)">
                  <rect x="-13" y="-10" width="26" height="20" rx="10" :fill="dimensionBadgeFill('ability', effectiveOverlayMap.get(kp.id)?.ability_labels || splitLabels(kp.ability_tag))" :opacity="dimensionBadgeOpacity(effectiveOverlayMap.get(kp.id)?.ability_status, effectiveOverlayMap.get(kp.id)?.ability_enabled !== false)" :stroke="dimensionBadgeStroke(effectiveOverlayMap.get(kp.id)?.ability_status, effectiveOverlayMap.get(kp.id)?.ability_enabled !== false)" stroke-width="1.2" />
                  <text class="workspace-node__dimension-label" text-anchor="middle" y="5">能</text>
                </g>
                <g transform="translate(38, 0)">
                  <rect x="-13" y="-10" width="26" height="20" rx="10" :fill="dimensionBadgeFill('literacy', effectiveOverlayMap.get(kp.id)?.literacy_labels || splitLabels(kp.literacy_tag))" :opacity="dimensionBadgeOpacity(effectiveOverlayMap.get(kp.id)?.literacy_status, effectiveOverlayMap.get(kp.id)?.literacy_enabled !== false)" :stroke="dimensionBadgeStroke(effectiveOverlayMap.get(kp.id)?.literacy_status, effectiveOverlayMap.get(kp.id)?.literacy_enabled !== false)" stroke-width="1.2" />
                  <text class="workspace-node__dimension-label" text-anchor="middle" y="5">素</text>
                </g>
              </g>
              <text :class="props.embedded ? 'teacher-node__code workspace-node__code' : 'workspace-node__code'" text-anchor="middle" y="-8">
                {{ kp.code }}
              </text>
              <text :class="props.embedded ? 'teacher-node__title workspace-node__title' : 'workspace-node__title'" text-anchor="middle" y="16">
                {{ kp.title.slice(0, 10) }}
              </text>
              <g v-if="!isTeacherMode && isRecommended(kp.id)">
                <rect x="-24" y="-50" width="48" height="20" rx="10" fill="#22c55e" />
                <text class="workspace-node__badge" text-anchor="middle" y="-36">推荐</text>
              </g>
              <g v-else-if="!isTeacherMode && isPathNode(kp.id)">
                <rect x="-24" y="-50" width="48" height="20" rx="10" fill="#14b8a6" />
                <text class="workspace-node__badge" text-anchor="middle" y="-36">路径</text>
              </g>
            </g>
            </g>
          </g>
        </svg>
        </div>

        <div class="workspace-bottom">
          <div class="workspace-zoom">
            <button type="button" @click="zoomOut">-</button>
            <span>缩放 {{ Math.round(canvasScale * 100) }}%</span>
            <button type="button" @click="zoomIn">+</button>
          </div>
        </div>

        <div v-if="!loading && !hasGraphData" class="workspace-stage__empty">
          <strong>这门课还没有知识图谱</strong>
          <span>{{ isTeacherMode ? "请先创建知识点并配置关系。" : "请先让老师创建知识点和关系，再回来查看。" }}</span>
        </div>
      </section>

      <aside v-if="!props.embedded && drawerVisible" :class="['workspace-drawer', { open: props.embedded && drawerOpen }]">
        <div class="workspace-drawer__header">
          <h3 class="workspace-drawer__title">
            {{ selectedType === "kp" ? selectedKp?.title : selectedCategoryNode?.title }}
          </h3>
          <button v-if="props.embedded" type="button" class="workspace-drawer__close" @click="drawerOpen = false">×</button>
        </div>

        <div class="workspace-drawer__content">
          <template v-if="selectedType === 'kp' && selectedKp">
            <div class="workspace-drawer__meta">{{ selectedKp.code }} · {{ selectedKp.chapter || "未分章" }}</div>
            <div class="workspace-drawer__guide-inline">
              <span>知识点说明</span>
              <HoverTip content="按“概览-资源-关系-证据-目标”查看，不用在一个长页面里来回找信息。" />
            </div>
            <div class="workspace-drawer__tabs">
              <button
                v-for="tab in drawerTabOrder"
                :key="tab"
                class="workspace-drawer__tab"
                :class="{ active: drawerTab === tab, done: drawerTabDone[tab] }"
                @click="drawerTab = tab"
              >
                {{ drawerTabLabelMap[tab] }}
                <span v-if="drawerTabDone[tab]" class="workspace-drawer__tab-check">已看</span>
              </button>
            </div>
            <p class="workspace-drawer__flow-hint">{{ drawerFlowHint }}</p>

            <section v-if="drawerTab === 'overview'" class="workspace-drawer__section">
              <div class="workspace-drawer__status">{{ nodeLabel(activeOverlay?.status) }}</div>
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
              <div v-if="activeOverlay?.recommended" class="workspace-drawer__recommend">这是系统当前推荐你优先学习的知识点。</div>
              <div v-if="activeOverlay?.blocked_reason" class="workspace-drawer__blocked">前置阻塞：{{ activeOverlay.blocked_reason }}</div>
              <div class="workspace-drawer__desc">
                {{ selectedKp.description || "暂未填写描述" }}
              </div>
              <button class="workspace-drawer__learn-btn" @click="openContentFromSelected">去学习</button>
            </section>

            <section v-else-if="drawerTab === 'resource'" class="workspace-drawer__section">
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
            </section>

            <section v-else-if="drawerTab === 'relation'" class="workspace-drawer__section">
              <h4 class="workspace-drawer__section-title">前置知识</h4>
              <div v-if="(nodeDetail?.prerequisites?.length ?? 0) === 0" class="workspace-drawer__empty">无前置要求</div>
              <div v-else class="workspace-drawer__tags">
                <button v-for="item in nodeDetail?.prerequisites ?? []" :key="`pre-${item.id}`" class="workspace-drawer__tag" @click="selectKp(item.id)">
                  {{ item.title }}
                </button>
              </div>

              <h4 class="workspace-drawer__section-title">后续知识</h4>
              <div v-if="(nodeDetail?.downstream?.length ?? 0) === 0" class="workspace-drawer__empty">暂无后续关系</div>
              <div v-else class="workspace-drawer__tags">
                <button v-for="item in nodeDetail?.downstream ?? []" :key="`next-${item.id}`" class="workspace-drawer__tag" @click="selectKp(item.id)">
                  {{ item.title }}
                </button>
              </div>

              <h4 class="workspace-drawer__section-title">关联知识</h4>
              <div v-if="(nodeDetail?.related?.length ?? 0) === 0" class="workspace-drawer__empty">暂无关联关系</div>
              <div v-else class="workspace-drawer__tags">
                <button v-for="item in nodeDetail?.related ?? []" :key="`rel-${item.id}`" class="workspace-drawer__tag" @click="selectKp(item.id)">
                  {{ item.title }}
                </button>
              </div>

              <div v-if="learningHintsActive && graphPathHint" class="workspace-drawer__section">
                <h4 class="workspace-drawer__section-title">建议下一步</h4>
                <p class="workspace-drawer__hint-text">{{ graphPathHint.path_summary }}</p>
                <div v-if="graphPathHint.blocked_titles?.length" class="workspace-drawer__blocked">
                  需先补前置：{{ graphPathHint.blocked_titles.join("、") }}
                </div>
                <div v-else-if="graphPathHint.can_unlock_next && (graphPathHint.next_candidate_ids?.length ?? 0) > 0" class="workspace-drawer__next-btns">
                  <button
                    v-for="(nid, idx) in graphPathHint.next_candidate_ids.slice(0, 5)"
                    :key="`nx-${nid}`"
                    type="button"
                    class="workspace-drawer__next-btn"
                    @click="selectKp(nid)"
                  >
                    {{ nextStepTitle(idx) }}
                  </button>
                </div>
                <p v-else class="workspace-drawer__hint-text">暂无可点击的后继节点，可在前置或关联知识点中继续探索。</p>
              </div>
              <div v-if="isPathNode(selectedKp.id)" class="workspace-drawer__recommend">当前知识点位于系统推荐路径中，可按路径顺序继续学习。</div>
            </section>

            <section v-else-if="drawerTab === 'evidence'" class="workspace-drawer__section">
              <h4 class="workspace-drawer__section-title">过程证据摘要</h4>
              <p v-if="formatEvidenceSummary(nodeDetail?.overlay?.evidence as Record<string, unknown>)" class="workspace-drawer__evidence-line">
                {{ formatEvidenceSummary(nodeDetail?.overlay?.evidence as Record<string, unknown>) }}
              </p>
              <p v-else class="workspace-drawer__empty">暂无过程证据数据</p>
              <p class="workspace-drawer__micro-hint">依据您在本知识点的练习、小测、视频与资源访问等记录汇总，与图谱色环判定一致。</p>

              <div v-if="learningHintsActive && graphRecoHint" class="workspace-drawer__section">
                <h4 class="workspace-drawer__section-title">个性化推荐</h4>
                <p class="workspace-drawer__hint-text">{{ graphRecoHint.reason_summary }}</p>
                <p v-if="graphRecoHint.advice_text" class="workspace-drawer__hint-text">{{ graphRecoHint.advice_text }}</p>
                <div
                  v-if="graphRecoHint.target_kp_id && graphRecoHint.target_kp_id !== selectedKp.id"
                  class="workspace-drawer__next-btns"
                >
                  <button type="button" class="workspace-drawer__next-btn workspace-drawer__next-btn--accent" @click="selectKp(graphRecoHint.target_kp_id)">
                    前往推荐：{{ graphRecoHint.target_code }} {{ graphRecoHint.target_title }}
                  </button>
                </div>
              </div>
            </section>

            <section v-else class="workspace-drawer__section">
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
              <h4 class="workspace-drawer__section-title">知识 / 能力 / 素养</h4>
              <p class="workspace-drawer__ability-hint">
                「能力」由教师在知识点上标注能力标签，系统根据掌握度与学习证据自动判定是否达成；图谱中层绿环与这里状态一致。
              </p>
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
            </section>
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  overflow: hidden;
  border-radius: 28px;
  border: 1px solid rgba(31, 41, 55, 0.14);
  box-shadow: 0 20px 42px rgba(31, 41, 55, 0.08);
}

.workspace-shell--embedded {
  border-radius: 28px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  box-shadow: none;
  background: transparent;
  border: 0;
}

.workspace-toolbar-inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: color-mix(in srgb, var(--app-card) 96%, var(--app-primary-soft));
  border-bottom: 1px solid var(--app-border);
  flex-shrink: 0;
}

.workspace-search--grow {
  flex: 1;
  min-width: 160px;
  max-width: 400px;
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 22px 14px;
  border-bottom: 1px solid rgba(31, 41, 55, 0.08);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  flex-shrink: 0;
}

.workspace-guide {
  display: none;
}

.workspace-drawer__guide-inline {
  display: none;
}

.workspace-drawer__flow-hint,
.workspace-drawer__guide,
.workspace-drawer__micro-hint,
.workspace-drawer__hint-text,
.workspace-drawer__blocked,
.workspace-drawer__next-btns,
.workspace-drawer__recommend,
.workspace-drawer__ability-hint {
  display: none;
}

.workspace-heading {
  display: grid;
  gap: 4px;
}

.workspace-title {
  font-size: 22px;
  font-weight: 800;
  color: #1f2937;
  margin: 0;
}

.workspace-subtitle {
  display: none;
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(31, 41, 55, 0.14);
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
  border: 1px solid rgba(31, 41, 55, 0.14);
  border-radius: 999px;
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  color: #1f2937;
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
  background: linear-gradient(180deg, #ebf8ff 0%, #dff2fb 100%);
}

.workspace-btn--primary {
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  border-color: var(--app-green);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}

.workspace-content {
  display: flex;
  align-items: stretch;
  gap: 18px;
  padding: 18px;
  overflow: hidden;
  height: min(72vh, 820px);
  max-height: min(72vh, 820px);
  flex: 1;
  min-height: 320px;
}

.workspace-shell--embedded .workspace-content {
  height: auto;
  max-height: none;
  flex: 1;
  min-height: calc(100dvh - 190px);
  padding: 0;
  gap: 0;
}

.workspace-content > * {
  min-height: 0;
}

.workspace-content--sidebar-collapsed {
  /* legacy：当前模板未使用；保留占位避免误删引用时报错 */
}

.workspace-content--drawer-collapsed {
  /* legacy */
}

.workspace-sidebar {
  width: 260px;
  flex: 0 0 260px;
  max-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 16px;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
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
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #334155;
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #617792;
}

.workspace-tree__empty strong {
  color: #1f2937;
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
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.workspace-tree__summary:hover {
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
  border-color: rgba(59, 130, 246, 0.24);
}

.workspace-tree__summary.active {
  background: radial-gradient(circle at top left, rgba(187, 247, 208, 0.36), transparent 58%), #ffffff;
  border-color: rgba(34, 197, 94, 0.28);
  color: #166534;
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
  border-radius: 16px;
  background: #ffffff;
  color: #475569;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
  margin-bottom: 4px;
}

.workspace-tree__child:hover {
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
}

.workspace-tree__child.active {
  background: linear-gradient(180deg, #eef8ff 0%, #ffffff 100%);
  border-color: rgba(34, 197, 94, 0.28);
  color: #166534;
}

.workspace-stage {
  /* 与 .workspace-stage__viewport 的 left/right 内缩一致，用于同心圆角 */
  --graph-stage-viewport-inset-x: 12px;
  position: relative;
  overflow: hidden;
  cursor: grab;
  user-select: none;
  touch-action: none;
  flex: 1;
  min-width: 0;
  min-height: var(--app-graph-canvas-min-height, clamp(360px, 52dvh, 820px));
  max-height: 100%;
  height: 100%;
  border-radius: 28px;
  background: #ffffff;
  border: 1px solid #dfe7f1;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
}

.workspace-shell--embedded .workspace-stage {
  min-height: max(420px, min(76dvh, 980px));
}

.workspace-stage--dragging {
  cursor: grabbing;
}

.workspace-stage__top {
  position: absolute;
  top: 14px;
  left: 14px;
  right: 14px;
  z-index: 3;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 22px;
  background: rgba(255, 250, 242, 0.92);
  border: 1px solid rgba(31, 41, 55, 0.1);
  backdrop-filter: blur(8px);
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
  display: none;
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

.workspace-stage__legend-dimensions {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex: 0 0 auto;
}

.workspace-stage__legend-dimensions .dim {
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

.workspace-stage__legend-dimensions .dim--knowledge { background: #3978d8; }
.workspace-stage__legend-dimensions .dim--ability { background: #24a36f; }
.workspace-stage__legend-dimensions .dim--literacy { background: #d58b2a; }

.workspace-stage__pill,
.workspace-stage__focus {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dbe5f0;
  color: #35507f;
  font-size: 12px;
  font-weight: 700;
}

.workspace-stage__focus {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  max-width: none;
  min-height: auto;
  padding: 0;
  border: 0;
  background: transparent;
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
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
  background: linear-gradient(180deg, #ebf8ff 0%, #dff2fb 100%);
}

.workspace-stage__viewport {
  position: absolute;
  left: var(--graph-stage-viewport-inset-x);
  right: var(--graph-stage-viewport-inset-x);
  top: 94px;
  bottom: var(--graph-stage-viewport-inset-x);
  width: auto;
  min-height: 0;
  overflow: hidden;
  border-radius: max(0px, calc(28px - var(--graph-stage-viewport-inset-x)));
  background: radial-gradient(circle at 24px 24px, rgba(20, 184, 166, 0.05) 1px, transparent 1px), radial-gradient(circle at 0 0, rgba(34, 197, 94, 0.03) 1px, transparent 1px), #ffffff;
  border: 1px solid rgba(31, 41, 55, 0.08);
  contain: layout;
  isolation: isolate;
}

.workspace-canvas {
  position: absolute;
  left: 0;
  top: 0;
  display: block;
  transform-origin: 0 0;
  transition: transform 0.08s ease;
  cursor: grab;
  z-index: 1;
  backface-visibility: hidden;
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

.workspace-node__dimensions {
  pointer-events: none;
  filter: drop-shadow(0 4px 8px rgba(15, 23, 42, 0.16));
}

.workspace-node__dimension-label {
  fill: #ffffff;
  font-size: 12px;
  font-weight: 900;
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
  bottom: calc(var(--graph-stage-viewport-inset-x) + 10px);
  right: calc(var(--graph-stage-viewport-inset-x) + 10px);
  z-index: 10;
  pointer-events: none;
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
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #dce6f2;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  pointer-events: auto;
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
  width: 320px;
  flex: 0 0 320px;
  max-height: 100%;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 16px;
  border-radius: 24px;
  background: #ffffff;
  border: 1px solid #dfe7f1;
  color: var(--app-text-soft);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
}

/* 嵌入学生工作台：与 .teacher-drawer 组合时改由内部区域滚动，见下方 .teacher-drawer.workspace-drawer */
.workspace-drawer.teacher-drawer {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0;
  background: #ffffff;
}

.workspace-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5edf6;
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

.workspace-drawer__tabs {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 12px;
}

.workspace-drawer__tab {
  border: 1px solid #dce6f2;
  border-radius: 10px;
  background: #ffffff;
  color: #3c587d;
  min-height: 34px;
  padding: 0 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.workspace-drawer__tab.active {
  border-color: #a8c5f8;
  background: linear-gradient(165deg, #f5f9ff 0%, #eef4fc 100%);
  color: #22549b;
}

.workspace-drawer__tab.done {
  border-color: #bfe2cd;
}

.workspace-drawer__tab-check {
  margin-left: 4px;
  font-size: 10px;
  color: #2f7a47;
}

.workspace-drawer__flow-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: #667b98;
  line-height: 1.55;
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

.workspace-drawer__evidence-line {
  margin: 0 0 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fafcff;
  border: 1px solid #e1eaf1;
  color: #51657f;
  font-size: 12px;
  line-height: 1.65;
}

.workspace-drawer__micro-hint {
  margin: 0;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.55;
}

.workspace-drawer__hint-text {
  margin: 0 0 10px;
  font-size: 12px;
  color: #51657f;
  line-height: 1.65;
}

.workspace-drawer__hint-text:last-child {
  margin-bottom: 0;
}

.workspace-drawer__blocked {
  margin: 0 0 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff8f0;
  border: 1px solid #f5dcc4;
  color: #8b5a2b;
  font-size: 12px;
  line-height: 1.55;
}

.workspace-drawer__next-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.workspace-drawer__next-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid #90caf9;
  background: #ffffff;
  color: #1565c0;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.workspace-drawer__next-btn:hover {
  background: #e3f2fd;
  border-color: #42a5f5;
}

.workspace-drawer__next-btn--accent {
  border-color: var(--app-green, #2f6fed);
  background: linear-gradient(180deg, #5a8ef0 0%, var(--app-green, #2f6fed) 100%);
  color: #ffffff;
}

.workspace-drawer__next-btn--accent:hover {
  filter: brightness(1.03);
}

.workspace-drawer__recommend {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f1f6ff;
  border: 1px solid #c5d8f0;
  color: #2f4f7a;
  font-size: 12px;
  line-height: 1.55;
}

.workspace-drawer__ability-hint {
  margin: 0 0 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fffbf0;
  border: 1px solid #f5e0b8;
  color: #6b5b2a;
  font-size: 12px;
  line-height: 1.6;
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
  .workspace-sidebar {
    width: 200px;
    flex: 0 0 200px;
  }

  .workspace-drawer {
    width: 280px;
    flex: 0 0 280px;
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
    flex-direction: column;
    height: auto;
    max-height: none;
    min-height: 0;
  }

  .workspace-stage {
    min-height: min(420px, 52vh);
    --graph-stage-viewport-inset-x: 8px;
  }

  .workspace-stage__viewport {
    position: relative;
    left: auto;
    right: auto;
    top: auto;
    bottom: auto;
    height: min(48vh, 420px);
    margin: 0 var(--graph-stage-viewport-inset-x) 8px;
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
}

/* 嵌入学生页时与 TeacherGraphWorkbench（fullscreen）同源布局与控件样式 */
.teacher-workbench--fullscreen.workspace-shell--embedded {
  border: none;
  box-shadow: none;
  background: transparent;
}

.teacher-workbench--fullscreen {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-width: 100%;
  min-width: 0;
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
  display: grid;
  grid-template-columns: minmax(0, auto) minmax(0, 1fr);
  align-items: center;
  gap: 8px 12px;
  padding: 6px 12px;
}

.teacher-workbench--fullscreen .teacher-title {
  font-size: 16px;
  line-height: 1.25;
}

.teacher-workbench--fullscreen .teacher-controls {
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}

.teacher-workbench--fullscreen .teacher-search {
  width: min(200px, 36vw);
}

.teacher-workbench--fullscreen .teacher-btn {
  min-height: 34px;
  padding: 0 12px;
  font-size: 12px;
}

.teacher-workbench--fullscreen .teacher-content {
  flex: 1;
  min-height: 0;
  gap: 8px;
  padding: 8px;
}

.teacher-workbench--fullscreen .teacher-sidebar {
  flex: 0 0 200px;
  width: 200px;
  max-width: 200px;
  padding: 10px;
}

.teacher-workbench--fullscreen .teacher-drawer {
  flex: 0 0 300px;
  width: 300px;
  max-width: 300px;
  padding: 0;
  min-height: 0;
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

.teacher-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.teacher-search :deep(.el-input__wrapper) {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px #d8e2ef;
}

.teacher-btn {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid #d8e2ef;
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
  color: #35507f;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--app-shadow-soft);
}

.teacher-btn--primary {
  border-color: var(--app-green);
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
}

.teacher-content {
  display: flex;
  align-items: stretch;
  gap: 16px;
  padding: 16px;
  min-width: 0;
  overflow: hidden;
  min-height: 0;
}

.teacher-content--fullscreen {
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
  padding: 14px;
  border-radius: var(--app-radius-lg);
  background: linear-gradient(180deg, var(--app-card) 0%, var(--app-primary-soft) 100%);
  border: 1px solid var(--app-border);
}

.teacher-workbench--fullscreen .teacher-content .teacher-sidebar {
  position: static;
  width: auto;
  box-shadow: none;
}

.teacher-tree__child small {
  display: block;
  font-size: 10px;
  color: #94a3b8;
  margin-top: 2px;
}

.teacher-stage {
  --graph-stage-pad: 8px;
  position: relative;
  overflow: hidden;
  cursor: default;
  user-select: none;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: var(--graph-stage-pad);
  min-width: 0;
  flex: 1;
  min-height: 0;
  max-height: 100%;
  height: 100%;
  border-radius: var(--app-radius-lg);
  background: linear-gradient(180deg, var(--app-card) 0%, rgba(79, 140, 255, 0.06) 100%);
  border: 1px solid var(--app-border);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.teacher-stage--dragging {
  cursor: grabbing;
}

.teacher-stage__top {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

/* 学生嵌入：压缩顶栏占用，把垂直空间留给画布；图例默认一行内提示 */
.teacher-stage__top--embedded {
  gap: 4px;
  padding-bottom: 2px;
}

.teacher-stage__top--embedded .teacher-stage__top-row {
  gap: 6px 8px;
}

.teacher-stage__top--embedded .teacher-stage__legend-details {
  border-radius: 10px;
}

.teacher-stage__top--embedded .teacher-stage__legend-summary {
  padding: 5px 10px;
  font-size: 11px;
  line-height: 1.35;
}

.teacher-stage__top--embedded .teacher-stage__legend-details[open] .teacher-stage__legend {
  padding: 6px 8px 8px;
}

.teacher-stage__top-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 10px;
  min-width: 0;
}

.teacher-stage__stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.teacher-stage__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.teacher-stage__legend-details {
  min-width: 0;
  border-radius: 12px;
  border: 1px solid #e2ebf5;
  background: rgba(255, 255, 255, 0.88);
}

.teacher-stage__legend-summary {
  list-style: none;
  cursor: pointer;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  user-select: none;
  line-height: 1.35;
}

.teacher-stage__legend-summary::-webkit-details-marker {
  display: none;
}

.teacher-stage__legend-details[open] .teacher-stage__legend-summary {
  border-bottom: 1px solid #e8eef5;
}

.teacher-stage__legend-details .teacher-stage__legend {
  padding: 8px 10px 10px;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.teacher-stage__legend-line--dashed {
  border-top-style: dashed;
  opacity: 0.72;
}

.teacher-stage__legend-line--path {
  border-top-color: #5a8ef0;
  border-top-style: dashed;
  border-top-width: 3px;
}

.teacher-stage__legend-line {
  width: 28px;
  height: 0;
  border-top: 2px solid #64748b;
  flex: 0 0 auto;
}

.teacher-stage__legend-item {
  min-height: 30px;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #dce6f2;
  color: #51657f;
  font-size: 11px;
  line-height: 1.35;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
}

.teacher-stage__legend-dimensions {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex: 0 0 auto;
}

.teacher-stage__pill,
.teacher-stage__button {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #dce6f2;
  background: #ffffff;
  color: #35507f;
  font-size: 11px;
  font-weight: 600;
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
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  border-color: var(--app-green);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
}

.teacher-stage__viewport {
  position: relative;
  flex: 1 1 0;
  min-height: 220px;
  width: 100%;
  overflow: hidden;
  border-radius: max(0px, calc(var(--app-radius-lg) - var(--graph-stage-pad)));
  background: var(--graph-canvas-bg);
  /* strict 会在部分嵌套 flex 场景下影响子项绘制与命中，改为轻量 containment */
  contain: layout style;
  isolation: isolate;
  transform: translateZ(0);
}

.teacher-workbench--fullscreen .teacher-stage__viewport {
  min-height: clamp(280px, 58dvh, 900px);
}

/* 学生端嵌入页：不要强推最小高度，否则会在外层容器内被裁切（底部缩放区被挡） */
.teacher-workbench--fullscreen.workspace-shell--embedded .teacher-stage__viewport {
  min-height: 0;
  height: 100%;
}

.teacher-workbench--fullscreen.workspace-shell--embedded .teacher-stage {
  min-height: 0;
}

.teacher-canvas {
  position: absolute;
  left: 0;
  top: 0;
  display: block;
  transform-origin: 0 0;
  transition: transform 0.08s ease;
  cursor: grab;
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

.teacher-stage__bottom {
  position: absolute;
  right: calc(var(--graph-stage-pad) + 12px);
  bottom: calc(var(--graph-stage-pad) + 12px);
  z-index: 9;
  pointer-events: none;
}

.teacher-stage__zoom {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dce6f2;
  box-shadow: var(--app-shadow-soft);
  font-size: 12px;
  font-weight: 700;
  color: #35507f;
}

.teacher-stage__zoom button {
  border: 0;
  background: #eff5ff;
  border-radius: 10px;
  width: 32px;
  height: 32px;
  cursor: pointer;
  font-weight: 800;
}

.teacher-stage__empty {
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

.teacher-stage__empty strong {
  color: #243449;
  font-size: 16px;
}

.teacher-drawer {
  width: 320px;
  flex: 0 0 320px;
  max-height: 100%;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: var(--app-radius-lg);
  background: #ffffff;
  border: 1px solid var(--app-border);
}

.teacher-workbench--fullscreen .teacher-content .teacher-drawer {
  position: static;
  width: auto;
  max-height: 100%;
  min-height: 0;
}

/* 右侧详情：头部固定，正文区域独立滚动，避免长内容被裁切 */
.teacher-drawer.workspace-drawer .workspace-drawer__header {
  flex-shrink: 0;
}

.teacher-drawer.workspace-drawer .workspace-drawer__content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 12px 12px 16px;
  box-sizing: border-box;
}

.teacher-drawer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 12px 8px;
  border-bottom: 1px solid #e8eef5;
  flex-shrink: 0;
}

.teacher-drawer__title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #243449;
  line-height: 1.3;
}

.teacher-drawer__close {
  border: 0;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: #94a3b8;
  padding: 0 4px;
}

.teacher-drawer__close:hover {
  color: #475569;
}

.workspace-shell {
  gap: 16px;
  padding: 12px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.workspace-header,
.workspace-sidebar,
.workspace-stage,
.workspace-drawer {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(31, 41, 55, 0.14);
  box-shadow: 0 16px 34px rgba(31, 41, 55, 0.08);
}

.workspace-header {
  border-radius: 28px;
  padding: 18px 20px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.24), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.workspace-sidebar {
  border-radius: 28px;
  background:
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.workspace-stage {
  border-radius: 28px;
  background:
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.workspace-stage__top {
  padding: 16px 18px;
  gap: 12px;
  background:
    radial-gradient(circle at top left, rgba(215, 249, 168, 0.14), transparent 24%),
    rgba(248, 251, 255, 0.94);
  border-bottom: 1.5px solid rgba(31, 41, 55, 0.1);
}

.workspace-stage__stats,
.workspace-stage__focus {
  gap: 8px;
}

.workspace-stage__pill {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: #f5f9ff;
  border: 1.5px solid #d8e5f6;
  color: #35507f;
  font-weight: 800;
}

.workspace-stage__learn-btn,
.workspace-stage__focus-btn,
.workspace-stage__menu button,
.workspace-stage__zoom button,
.workspace-drawer__primary,
.workspace-drawer__secondary,
.workspace-drawer__link-btn,
.workspace-drawer__tag {
  border-radius: 12px;
}

.workspace-stage__learn-btn,
.workspace-stage__focus-btn,
.workspace-stage__menu button {
  min-height: 34px;
  padding-inline: 12px;
  border: 1.5px solid #d8e5f6;
  background: #ffffff;
  color: #35507f;
  font-weight: 800;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.workspace-stage__learn-btn--ghost,
.workspace-stage__focus-btn--ghost {
  background: #f7fbff;
}

.workspace-stage__learn-btn--primary,
.workspace-stage__focus-btn--primary {
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  border-color: var(--app-green);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
}

.workspace-stage__learn-btn:hover,
.workspace-stage__focus-btn:hover,
.workspace-stage__menu button:hover,
.workspace-stage__zoom button:hover,
.workspace-drawer__secondary:hover,
.workspace-drawer__link-btn:hover,
.workspace-drawer__tag:hover {
  transform: translateY(-1px);
}

.workspace-stage__legend {
  gap: 8px 12px;
}

.workspace-stage__legend-item {
  color: #5f738f;
}

.workspace-stage__legend-line,
.workspace-stage__legend-dimensions {
  opacity: 0.85;
}

.workspace-stage__viewport {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  background:
    radial-gradient(circle at top left, rgba(215, 249, 168, 0.1), transparent 20%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.workspace-stage__empty {
  background: rgba(255, 255, 255, 0.98);
  border: 1.5px solid #dbe5f1;
  box-shadow: 0 18px 40px rgba(31, 41, 55, 0.1);
}

.workspace-drawer {
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.2), transparent 24%),
    linear-gradient(180deg, #fffdfb 0%, #fbfdff 100%);
}

.workspace-drawer__header {
  padding: 14px 16px 10px;
  border-bottom-color: #e6eef7;
}

.workspace-drawer__content {
  padding: 14px 14px 16px;
}

.workspace-drawer__guide-inline,
.workspace-drawer__flow-hint,
.workspace-drawer__recommend,
.workspace-drawer__ability-hint {
  display: none;
}

.workspace-drawer__tabs {
  gap: 8px;
  padding: 8px;
  border-radius: 18px;
  background: #f6faff;
  border: 1.5px solid #dfe9f5;
}

.workspace-drawer__tab {
  min-height: 34px;
  border-radius: 12px;
  border: 1.5px solid #d8e5f6;
  background: #ffffff;
  font-weight: 800;
}

.workspace-drawer__tab.active {
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  border-color: var(--app-green);
}

.workspace-drawer__section,
.workspace-drawer__metrics,
.workspace-drawer__detail-grid {
  gap: 10px;
}

.workspace-drawer__metric,
.workspace-drawer__desc,
.workspace-drawer__empty,
.workspace-drawer__relation-tip {
  border-radius: 16px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.workspace-drawer__metric {
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.workspace-drawer__tag {
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  color: #1f2937;
  font-weight: 700;
}

.workspace-drawer__primary {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
  border-color: var(--app-green);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}

.workspace-drawer__secondary,
.workspace-drawer__link-btn {
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  border-color: rgba(31, 41, 55, 0.14);
  color: #475569;
}

.workspace-drawer__secondary:hover,
.workspace-drawer__link-btn:hover {
  background: linear-gradient(180deg, #ebf8ff 0%, #dff2fb 100%);
  border-color: rgba(31, 41, 55, 0.18);
  color: #1f2937;
}

.workspace-tree__summary,
.workspace-tree__child,
.workspace-stage__menu,
.workspace-zoom {
  border-radius: 18px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: rgba(255, 255, 255, 0.96);
}

.workspace-tree__summary {
  box-shadow: 0 10px 20px rgba(31, 41, 55, 0.06);
}

.workspace-tree__summary.active,
.workspace-tree__child.active {
  background: linear-gradient(180deg, #eef8ff 0%, #ffffff 100%);
  border-color: rgba(34, 197, 94, 0.28);
}

.workspace-tree__child:hover {
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
}

.workspace-stage__menu {
  padding: 8px;
  gap: 8px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.1);
}

.workspace-stage__menu button {
  border: 1px solid #d8e5f6;
  background: #ffffff;
  color: #35507f;
}

.workspace-stage__menu .danger {
  background: #fef2f2;
  color: #dc2626;
  border-color: #f5c2c7;
}

.workspace-node:hover circle:last-of-type,
.workspace-category-node:hover rect {
  filter: drop-shadow(0 10px 18px rgba(15, 23, 42, 0.08));
}
</style>

