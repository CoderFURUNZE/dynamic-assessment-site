<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Check, Lock, Star, Trophy, VideoPlay } from "@element-plus/icons-vue";
import { api, getWithCache } from "../api";
import { getSavedStudentSubject, saveStudentSubject } from "../utils/studentCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  active?: boolean;
  enroll_status?: string;
  completed?: boolean;
  learning_available?: boolean;
};

type KP = {
  id: number;
  code: string;
  title: string;
  chapter?: string;
  is_terminal?: boolean;
  mastery?: number;
  status?: string;
  previewLocked?: boolean;
  pathSelected?: boolean;
  pos_x?: number | null;
  pos_y?: number | null;
};

type Edge = {
  prereq_id: number;
  next_id: number;
  relation_type: string;
};

type RecoData = {
  target_kp: { id: number; code: string; title: string; chapter?: string; mastery?: number; is_terminal?: boolean };
  reason_summary: string;
  advice_text?: string;
  student_message?: string;
  personalized_path?: Array<{ kp_id?: number; id?: number; code?: string; title?: string; chapter?: string; action?: string; mastery?: number; is_terminal?: boolean; locked?: boolean }>;
  route_options?: {
    display_nodes?: Array<{ kp_id?: number; id?: number; code?: string; title?: string; chapter?: string; mastery?: number; is_terminal?: boolean; locked?: boolean; recommended?: boolean }>;
    next_options?: Array<{ id?: number; title?: string }>;
    terminal_options?: Array<{ id?: number; title?: string }>;
    available_ids?: number[];
    explain?: string;
  };
  course_completion?: { completed?: boolean; completed_terminal_title?: string };
};

type RouteStop = {
  kp: KP;
  index: number;
  role: "start" | "recommended" | "option" | "terminal";
  x: number;
  y: number;
  page: number;
};

type ConnectorLine = {
  key: string;
  d: string;
  state: string;
};

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const recoLoading = ref(false);
const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const visibleKps = ref<KP[]>([]);
const visibleEdges = ref<Edge[]>([]);
const currentKpId = ref<number | null>(null);
const recommendationSourceKpId = ref<number | null>(null);
const reco = ref<RecoData | null>(null);
const mapRef = ref<HTMLElement | null>(null);
const isDragging = ref(false);
const dragMoved = ref(false);
const suppressNodeClick = ref(false);
const choosingKpId = ref<number | null>(null);
const graphMapRequestSeq = ref(0);
const recoRequestSeq = ref(0);
const selectionQueryTimer = ref<ReturnType<typeof window.setTimeout> | null>(null);
const selectionMapTimer = ref<ReturnType<typeof window.setTimeout> | null>(null);
const selectionRecoTimer = ref<ReturnType<typeof window.setTimeout> | null>(null);
const dragStart = ref({ x: 0, y: 0, offsetX: 0, offsetY: 0 });
const panOffset = ref({ x: 0, y: 0 });

const visibleCourses = computed(() =>
  courses.value.filter((item) => item.active !== false && String(item.enroll_status || "").trim().toLowerCase() !== "closed"),
);
const routeSelectableCourses = computed(() =>
  courses.value.filter((item) => Boolean(String(item.title || "").trim())),
);
const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const recommendedKp = computed(() => reco.value?.target_kp ?? null);
const courseClosed = computed(() => Boolean(currentCourse.value && currentCourse.value.learning_available === false));

const recommendedNodeId = computed(() => Number(recommendedKp.value?.id || 0));

const routeKps = computed(() => {
  // The graph map is the source of truth; recommendation only highlights a suggested node.
  return visibleKps.value.map((item) => ({ ...item }));
});

const currentKp = computed(() => {
  const recommendedId = Number(recommendedKp.value?.id || 0);
  return routeKps.value.find((item) => item.id === currentKpId.value)
    ?? visibleKps.value.find((item) => item.id === currentKpId.value)
    ?? routeKps.value.find((item) => item.id === recommendedId)
    ?? visibleKps.value.find((item) => item.id === recommendedId)
    ?? routeKps.value[0]
    ?? visibleKps.value[0]
    ?? null;
});

const availableCount = computed(() => routeKps.value.filter((item) => !item.previewLocked).length);
const completedCount = computed(() => routeKps.value.filter((item) => !item.previewLocked && isCompleted(item)).length);
const progressPercent = computed(() => {
  if (!availableCount.value) return 0;
  return Math.round((completedCount.value / availableCount.value) * 100);
});
const previewCount = computed(() => routeKps.value.filter((item) => item.previewLocked).length);
const routeTerminalCount = computed(() => routeKps.value.filter((item) => item.is_terminal).length);
const currentMasteryPercent = computed(() => Math.round(Number(currentKp.value?.mastery || recommendedKp.value?.mastery || 0) * 100));
const routeProgressStyle = computed(() => ({ "--route-progress": `${progressPercent.value}%` }));
const masteryRingStyle = computed(() => ({ "--mastery-progress": `${currentMasteryPercent.value}%` }));
const routeContentWidth = computed(() => mapWidth + pagePanPadding * 2);
const routeContentHeight = computed(() => {
  const lowestStopY = routeStops.value.reduce((max, stop) => Math.max(max, stop.y), 0);
  return Math.max(mapHeight.value, lowestStopY + 230);
});
const mapCanvasStyle = computed(() => ({
  width: `${routeContentWidth.value}px`,
  height: `${routeContentHeight.value}px`,
  transform: `translate3d(${panOffset.value.x}px, ${panOffset.value.y}px, 0)`,
}));
const selectedStopIndex = computed(() => {
  const id = Number(currentKp.value?.id || recommendedKp.value?.id || 0);
  const index = routeKps.value.findIndex((item) => item.id === id);
  return index >= 0 ? index + 1 : 1;
});
const currentStatusLabel = computed(() => {
  const kp = currentKp.value;
  if (!kp) return "等待推荐";
  const state = nodeState(kp);
  if (state === "selected") return "当前选择";
  if (state === "recommended") return "建议优先";
  if (state === "locked") return "待解锁";
  if (state === "current") return "当前推荐";
  if (state === "done") return "已完成";
  if (state === "path") return "已选路径";
  return "可学习";
});
const currentNodeState = computed(() => currentKp.value ? nodeState(currentKp.value) : "open");
const learningAdvice = computed(() => {
  const kp = currentKp.value;
  if (courseClosed.value) return ["课程已经结束，建议先查看学习报告和最终反馈。", "可以回到薄弱节点复习，但不再产生新的课程进度。"];
  if (!kp) return ["等待老师开放课程路线后，系统会自动生成下一步建议。"];
  if (kp.previewLocked) return ["这个节点暂未解锁，先完成当前推荐关卡。", "完成前置节点后，路线会自动刷新并开放后续内容。"];
  if (isCompleted(kp)) return ["这个知识点已经达标，可以重新学习巩固，也可以继续挑战下一关。", "建议重点查看错题和小测解释，避免遗忘。"];
  if (Number(kp.mastery || 0) < 0.5) return ["先看本关资源，建立概念，再进入练习。", "练习时优先完成基础题，系统会根据结果更新掌握度。"];
  return ["继续完成练习和小测，把掌握度推到 70% 以上。", "如果卡住，可以回看资源或查看题目解析。"];
});
const routeStepItems = computed(() => routeKps.value.map((kp, index) => ({
  kp,
  index: index + 1,
  state: nodeState(kp),
  mastery: Math.round(Number(kp.mastery || 0) * 100),
})));
const mapWidth = 1040;
const pagePanPadding = 220;
const routeNodeRadius = 43;
const FAST_ENTRY_CACHE_TTL = 60 * 1000;
const mapHeight = computed(() => routeStops.value.length >= 8 ? 1180 : routeStops.value.length >= 6 ? 1040 : 860);
function middlePositions(count: number) {
  const positionsByCount: Record<number, Array<{ x: number; y: number }>> = {
    1: [{ x: 520, y: 420 }],
    2: [{ x: 360, y: 390 }, { x: 680, y: 390 }],
    3: [{ x: 260, y: 330 }, { x: 520, y: 470 }, { x: 780, y: 330 }],
    4: [{ x: 220, y: 320 }, { x: 420, y: 500 }, { x: 620, y: 500 }, { x: 820, y: 320 }],
    5: [{ x: 180, y: 320 }, { x: 350, y: 500 }, { x: 520, y: 360 }, { x: 690, y: 500 }, { x: 860, y: 320 }],
    6: [{ x: 180, y: 300 }, { x: 350, y: 450 }, { x: 520, y: 600 }, { x: 690, y: 450 }, { x: 860, y: 300 }, { x: 520, y: 780 }],
  };
  if (count <= 6) return positionsByCount[Math.max(count, 1)] ?? positionsByCount[1];
  const columns = 3;
  const xByColumn = [220, 520, 820];
  return Array.from({ length: count }, (_, index) => {
    const row = Math.floor(index / columns);
    const column = index % columns;
    return {
      x: xByColumn[row % 2 === 0 ? column : columns - 1 - column],
      y: 300 + row * 190,
    };
  });
}

function kpOrderScore(kp: KP) {
  const numbers = String(kp.code || "")
    .match(/\d+/g)
    ?.map((item) => Number(item)) ?? [];
  if (!numbers.length) return Number.MAX_SAFE_INTEGER;
  return numbers.reduce((score, item) => score * 1000 + item, 0);
}

function chapterLaneMap(nodes: KP[], centerX: number) {
  const bestScoreByChapter = new Map<string, number>();
  for (const kp of nodes) {
    const chapter = kp.chapter || "__default__";
    const score = kpOrderScore(kp);
    bestScoreByChapter.set(chapter, Math.min(bestScoreByChapter.get(chapter) ?? score, score));
  }
  const chapters = [...bestScoreByChapter.keys()].sort((a, b) => {
    const diff = (bestScoreByChapter.get(a) ?? 0) - (bestScoreByChapter.get(b) ?? 0);
    return diff || a.localeCompare(b);
  });
  const lanes = [centerX, centerX - 300, centerX + 300, centerX - 460, centerX + 460, centerX - 150, centerX + 150];
  return new Map(chapters.map((chapter, index) => [chapter, lanes[index % lanes.length] ?? centerX]));
}

function levelLanePositions(group: KP[], laneByChapter: Map<string, number>, centerX: number) {
  const usedByLane = new Map<number, number>();
  const offsets = [0, -150, 150, -285, 285];
  return group.map((kp, index) => {
    const base = laneByChapter.get(kp.chapter || "__default__") ?? centerX;
    const used = usedByLane.get(base) ?? 0;
    usedByLane.set(base, used + 1);
    const rawX = base + (offsets[used] ?? (used % 2 === 0 ? 1 : -1) * (320 + used * 24));
    const extraSpread = group.length === 1 ? 0 : (index - (group.length - 1) / 2) * 18;
    return Math.max(60, Math.min(980, rawX + extraSpread));
  });
}

function relationLayoutStops(nodes: KP[]): RouteStop[] {
  const nodeIds = new Set(nodes.map((kp) => kp.id));
  const order = new Map(nodes.map((kp, index) => [kp.id, index]));
  const incoming = new Map<number, number[]>();
  const outgoing = new Map<number, number[]>();
  for (const edge of visibleEdges.value) {
    if (edge.relation_type !== "prerequisite") continue;
    if (!nodeIds.has(edge.prereq_id) || !nodeIds.has(edge.next_id)) continue;
    incoming.set(edge.next_id, [...(incoming.get(edge.next_id) ?? []), edge.prereq_id]);
    outgoing.set(edge.prereq_id, [...(outgoing.get(edge.prereq_id) ?? []), edge.next_id]);
  }

  const indegree = new Map(nodes.map((kp) => [kp.id, incoming.get(kp.id)?.length ?? 0]));
  const level = new Map<number, number>();
  const queue = nodes
    .filter((kp) => (indegree.get(kp.id) ?? 0) === 0)
    .sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0))
    .map((kp) => kp.id);
  if (!queue.length && nodes[0]) queue.push(nodes[0].id);
  for (const id of queue) level.set(id, 0);

  while (queue.length) {
    const currentId = queue.shift()!;
    const currentLevel = level.get(currentId) ?? 0;
    for (const nextId of outgoing.get(currentId) ?? []) {
      level.set(nextId, Math.max(level.get(nextId) ?? 0, currentLevel + 1));
      indegree.set(nextId, (indegree.get(nextId) ?? 0) - 1);
      if ((indegree.get(nextId) ?? 0) <= 0) queue.push(nextId);
    }
  }

  nodes.forEach((kp, index) => {
    if (!level.has(kp.id)) level.set(kp.id, Math.floor(index / 3));
  });

  const groups = new Map<number, KP[]>();
  nodes.forEach((kp) => {
    const itemLevel = level.get(kp.id) ?? 0;
    groups.set(itemLevel, [...(groups.get(itemLevel) ?? []), kp]);
  });
  for (const [itemLevel, group] of groups) {
    groups.set(itemLevel, group.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0)));
  }

  const levelGap = 210;
  const top = 120;
  const centerX = 520;
  const laneByChapter = chapterLaneMap(nodes, centerX);
  const stops: RouteStop[] = [];
  for (const itemLevel of [...groups.keys()].sort((a, b) => a - b)) {
    const group = groups.get(itemLevel) ?? [];
    const positions = levelLanePositions(group, laneByChapter, centerX);
    group.forEach((kp, groupIndex) => {
      const x = pagePanPadding + (positions[groupIndex] ?? centerX);
      const y = top + itemLevel * levelGap;
      stops.push({
        kp,
        index: order.get(kp.id) ?? stops.length,
        role: kp.is_terminal ? "terminal" : kp.id === recommendedNodeId.value ? "recommended" : (order.get(kp.id) ?? 0) === 0 ? "start" : "option",
        x,
        y,
        page: 0,
      });
    });
  }
  return stops.sort((a, b) => a.index - b.index);
}

const fullRouteStops = computed<RouteStop[]>(() => {
  const nodes = routeKps.value;
  if (nodes.length) return relationLayoutStops(nodes);
  const positions = middlePositions(nodes.length);
  const stops: RouteStop[] = [];
  nodes.forEach((kp, index) => {
    const position = positions[index] ?? { x: 520, y: 420 + index * 120 };
    stops.push({
      kp,
      index,
      role: kp.is_terminal ? "terminal" : kp.id === recommendedNodeId.value ? "recommended" : index === 0 ? "start" : "option",
      x: pagePanPadding + position.x,
      y: position.y,
      page: 0,
    });
  });
  return stops;
});

const routeStops = computed<RouteStop[]>(() => fullRouteStops.value);
const connectorLines = computed(() => {
  const stopById = new Map(routeStops.value.map((stop) => [stop.kp.id, stop]));
  const lines: ConnectorLine[] = [];
  for (const edge of visibleEdges.value) {
    if (edge.relation_type !== "prerequisite") continue;
    const from = stopById.get(edge.prereq_id);
    const to = stopById.get(edge.next_id);
    if (!from || !to) continue;
    lines.push(makeConnector(`${edge.prereq_id}-${edge.next_id}`, from, to, nodeState(to.kp)));
  }
  return lines;
});

function makeConnector(key: string, from: RouteStop, to: RouteStop, state: string): ConnectorLine {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.hypot(dx, dy) || 1;
  const insetX = (dx / length) * routeNodeRadius;
  const insetY = (dy / length) * routeNodeRadius;
  const x1 = from.x + insetX;
  const y1 = from.y + insetY;
  const x2 = to.x - insetX;
  const y2 = to.y - insetY;
  return {
    key,
    d: `M ${x1.toFixed(1)} ${y1.toFixed(1)} L ${x2.toFixed(1)} ${y2.toFixed(1)}`,
    state,
  };
}
const pageTitle = computed(() => {
  if (courseClosed.value) return "课程已结束";
  if (recommendedKp.value?.title) return `下一关：${recommendedKp.value.title}`;
  if (currentKp.value?.title) return `继续学习：${currentKp.value.title}`;
  return "等待老师开放学习路线";
});

const pageLead = computed(() => {
  if (courseClosed.value) {
    return "老师已结束这门课程，当前可查看学习路径和学习报告。";
  }
  return reco.value?.student_message || reco.value?.advice_text || reco.value?.reason_summary || "系统会展示当前路径末端可选择的节点，你可以自主选择，也可以优先学习系统建议的节点。";
});

const selectedIsRecommendation = computed(() =>
  Boolean(currentKpId.value && currentKp.value?.id === recommendedKp.value?.id),
);

const focusBadge = computed(() => {
  if (!currentKpId.value) return "建议优先";
  return selectedIsRecommendation.value ? "建议优先" : "所选节点";
});

const focusText = computed(() => {
  if (currentKpId.value && !selectedIsRecommendation.value && currentKp.value) {
    return isCompleted(currentKp.value)
      ? "该知识点已经完成，你仍然可以重新进入学习。"
      : "你当前查看的是这个知识点，可以点击进入学习查看资源。";
  }
  return reco.value?.reason_summary || "系统会按你的掌握情况标记建议优先节点，你也可以从其他已解锁节点开始。";
});

const focusActionText = computed(() => {
  if (courseClosed.value) return "查看报告";
  if (currentKpId.value && !selectedIsRecommendation.value && currentKp.value && isCompleted(currentKp.value)) return "重新学习";
  return "进入学习";
});

function isCompleted(kp: KP) {
  return Number(kp.mastery || 0) >= 0.7 || kp.status === "mastered";
}

function isStartedKp(kp: KP) {
  return Boolean(kp.pathSelected);
}

function isLockedKp(kp?: KP | null) {
  return Boolean(kp?.previewLocked);
}

function findKpById(id?: number | null) {
  const targetId = Number(id || 0);
  if (!targetId) return null;
  return routeKps.value.find((item) => item.id === targetId)
    ?? visibleKps.value.find((item) => item.id === targetId)
    ?? null;
}

function nodeState(kp: KP) {
  if (isLockedKp(kp)) return "locked";
  if (isCompleted(kp)) return "done";
  if (kp.id === currentKpId.value) return "selected";
  if (kp.id === recommendedNodeId.value) return "recommended";
  if (isStartedKp(kp)) return "path";
  return "open";
}

function nodeIcon(kp: KP) {
  const state = nodeState(kp);
  if (state === "locked") return Lock;
  if (state === "selected" || state === "recommended") return VideoPlay;
  if (kp.is_terminal) return Trophy;
  if (state === "done") return Check;
  return Star;
}

function statusLabel(kp: KP) {
  const state = nodeState(kp);
  if (state === "selected") return "当前选择";
  if (state === "recommended") return "建议优先";
  if (state === "locked") return "待解锁";
  if (state === "current") return "当前推荐";
  if (state === "done") return "已完成";
  if (state === "path") return "已选路径";
  return "可学习";
}

function roleLabel(role: RouteStop["role"]) {
  if (role === "start") return "共同起点";
  if (role === "terminal") return "达标终点";
  if (role === "recommended") return "建议优先";
  return "可选分支";
}

function centerCurrentStop() {
  nextTick(() => {
    const el = mapRef.value;
    if (!el) return;
    const targetId = Number(currentKp.value?.id || recommendedKp.value?.id || 0);
    const stop = routeStops.value.find((item) => item.kp.id === targetId) ?? routeStops.value.find((item) => item.role === "recommended") ?? routeStops.value[0];
    if (!stop) return;
    setPan(el.clientWidth / 2 - stop.x, el.clientHeight / 2 - stop.y);
  });
}

function centerCurrentPage() {
  nextTick(() => {
    const el = mapRef.value;
    if (!el || !routeStops.value.length) return;
    const left = Math.min(...routeStops.value.map((stop) => stop.x));
    const right = Math.max(...routeStops.value.map((stop) => stop.x));
    const top = Math.min(...routeStops.value.map((stop) => stop.y));
    const bottom = Math.max(...routeStops.value.map((stop) => stop.y));
    setPan(el.clientWidth / 2 - (left + right) / 2, el.clientHeight / 2 - (top + bottom) / 2);
  });
}

function jumpToRecommendation() {
  const targetId = Number(recommendedKp.value?.id || currentKpId.value || 0);
  if (targetId) currentKpId.value = targetId;
  syncQuery();
  centerCurrentStop();
}

function cardSide(stop: RouteStop) {
  const pageLeft = pagePanPadding;
  if (stop.x < pageLeft + mapWidth / 2) return "is-card-left";
  if (stop.x > pageLeft + mapWidth / 2) return "is-card-right";
  return stop.index % 2 === 0 ? "is-card-right" : "is-card-left";
}

function clampAxis(value: number, viewportSize: number, contentSize: number) {
  if (viewportSize >= contentSize) {
    const centered = Math.round((viewportSize - contentSize) / 2);
    return Math.min(centered + pagePanPadding, Math.max(centered - pagePanPadding, value));
  }
  return Math.min(pagePanPadding, Math.max(viewportSize - contentSize - pagePanPadding, value));
}

function clampPan(x: number, y: number) {
  const el = mapRef.value;
  if (!el) return { x, y };
  return {
    x: clampAxis(x, el.clientWidth, routeContentWidth.value),
    y: clampAxis(y, el.clientHeight, routeContentHeight.value),
  };
}

function setPan(x: number, y: number) {
  panOffset.value = clampPan(x, y);
}

function onMapPointerDown(event: PointerEvent) {
  const el = mapRef.value;
  if (!el || event.button !== 0) return;
  const target = event.target as HTMLElement | null;
  if (target?.closest(".learning-route-stop")) return;
  isDragging.value = true;
  dragMoved.value = false;
  dragStart.value = {
    x: event.clientX,
    y: event.clientY,
    offsetX: panOffset.value.x,
    offsetY: panOffset.value.y,
  };
  try {
    el.setPointerCapture?.(event.pointerId);
  } catch {
    // Pointer capture is a convenience; dragging still works while the pointer stays over the map.
  }
}

function onStopPointerDown(event: PointerEvent) {
  event.stopPropagation();
}

function onMapPointerMove(event: PointerEvent) {
  const el = mapRef.value;
  if (!el || !isDragging.value) return;
  const dx = event.clientX - dragStart.value.x;
  const dy = event.clientY - dragStart.value.y;
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragMoved.value = true;
  if (!dragMoved.value) return;
  event.preventDefault();
  setPan(dragStart.value.offsetX + dx, dragStart.value.offsetY + dy);
}

function onMapPointerUp(event: PointerEvent) {
  if (dragMoved.value) {
    event.preventDefault();
    event.stopPropagation();
    suppressNodeClick.value = true;
    window.setTimeout(() => {
      suppressNodeClick.value = false;
    }, 160);
  }
  isDragging.value = false;
  try {
    mapRef.value?.releasePointerCapture?.(event.pointerId);
  } catch {
    // Ignore capture release failures from browsers that already released it.
  }
}

function onMapWheel(event: WheelEvent) {
  const el = mapRef.value;
  if (!el) return;
  const canPanX = routeContentWidth.value > el.clientWidth;
  const canPanY = routeContentHeight.value > el.clientHeight;
  if (!canPanX && !canPanY) return;
  event.preventDefault();
  const primaryDeltaX = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : 0;
  const primaryDeltaY = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : 0;
  setPan(
    panOffset.value.x - (canPanX ? primaryDeltaX : 0),
    panOffset.value.y - (canPanY ? primaryDeltaY : 0),
  );
}

function resetState() {
  visibleKps.value = [];
  visibleEdges.value = [];
  currentKpId.value = null;
  recommendationSourceKpId.value = null;
  reco.value = null;
}

function syncQuery() {
  saveStudentSubject(subject.value);
  router.replace({
    path: "/student/graph-workspace",
    query: {
      subject: subject.value || undefined,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
      preview: String(route.query.preview || "") || undefined,
    },
  }).catch(() => {});
}

function clearSelectionTimers() {
  for (const timerRef of [selectionQueryTimer, selectionMapTimer, selectionRecoTimer]) {
    if (timerRef.value != null) {
      window.clearTimeout(timerRef.value);
      timerRef.value = null;
    }
  }
}

function scheduleSelectionSideEffects(kpId: number) {
  if (selectionQueryTimer.value != null) window.clearTimeout(selectionQueryTimer.value);
  if (selectionMapTimer.value != null) window.clearTimeout(selectionMapTimer.value);
  if (selectionRecoTimer.value != null) window.clearTimeout(selectionRecoTimer.value);

  selectionQueryTimer.value = window.setTimeout(() => {
    selectionQueryTimer.value = null;
    syncQuery();
  }, 100);

  selectionMapTimer.value = window.setTimeout(() => {
    selectionMapTimer.value = null;
    void loadVisibleKps(false, kpId).then(() => {
      syncQuery();
    });
  }, 180);

  selectionRecoTimer.value = window.setTimeout(() => {
    selectionRecoTimer.value = null;
    void loadRecommendation(kpId);
  }, 220);
}

async function loadCourses(useCache = true) {
  const raw = useCache
    ? await getWithCache<any[]>("/graph/courses", undefined, { skipGlobalLoading: true, ttlMs: FAST_ENTRY_CACHE_TTL })
    : (await api.get("/graph/courses", { skipGlobalLoading: true } as any)).data;
  let list = Array.isArray(raw) ? raw : [];
  if (list.length === 0) {
    try {
      const fallback = await getWithCache<any[]>("/graph/available-courses", undefined, { skipGlobalLoading: true, ttlMs: FAST_ENTRY_CACHE_TTL });
      list = Array.isArray(fallback) ? fallback : [];
    } catch {
      list = [];
    }
  }
  courses.value = list.map((item: any) => ({
    id: Number(item.id),
    code: String(item.code || ""),
    title: String(item.title || ""),
    active: item.active !== false,
    enroll_status: String(item.enroll_status || ""),
    completed: item.completed === true,
    learning_available: item.learning_available !== false,
  }));
  const routeSubject = String(route.query.subject || "").trim();
  const candidates = [
    routeSubject,
    subject.value,
    getSavedStudentSubject(),
    routeSelectableCourses.value[0]?.title || "",
  ];
  subject.value = String(candidates.find((item) => String(item || "").trim()) || "").trim();
}

async function loadVisibleKps(useCache = true, preferredSourceId?: number | null) {
  if (!subject.value) {
    resetState();
    return;
  }
  const requestSeq = ++graphMapRequestSeq.value;
  const previousKps = visibleKps.value;
  const previousEdges = visibleEdges.value;
  const requestedSourceId = Number(preferredSourceId || currentKpId.value || route.query.kp || recommendationSourceKpId.value || 0);
  const params = {
    subject: subject.value,
    grade: grade.value,
    source_id: requestedSourceId || undefined,
  };
  const data = (await api.get("/graph/map", { params, skipGlobalLoading: true } as any)).data;
  if (requestSeq !== graphMapRequestSeq.value) return;
  const overlayMap = new Map<number, any>((Array.isArray(data?.overlay) ? data.overlay : []).map((item: any) => [Number(item.kp_id), item]));
  const list = Array.isArray(data?.base?.kps) ? data.base.kps : [];
  const nextEdges = (Array.isArray(data?.base?.edges) ? data.base.edges : [])
    .map((item: any) => ({
      prereq_id: Number(item.prereq_id || 0),
      next_id: Number(item.next_id || 0),
      relation_type: String(item.relation_type || "prerequisite"),
    }))
    .filter((item: Edge) => item.prereq_id && item.next_id);
  const nextKps = list.map((item: any) => {
    const overlay = overlayMap.get(Number(item.id)) || {};
    return {
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
      chapter: String(item.chapter || ""),
      is_terminal: item.is_terminal === true,
      mastery: Number(overlay.mastery || 0),
      status: String(overlay.status || "not_started"),
      previewLocked: Boolean(overlay.blocked_reason),
      pathSelected: Boolean(overlay.path_selected),
      pos_x: item.pos_x == null ? null : Number(item.pos_x),
      pos_y: item.pos_y == null ? null : Number(item.pos_y),
    };
  });
  if (!useCache && previousKps.length) {
    const kpById = new Map(nextKps.map((item) => [item.id, item]));
    const nextIdSet = new Set(kpById.keys());
    const stableEdges = [...nextEdges];
    for (const edge of previousEdges) {
      if (edge.relation_type !== "prerequisite") continue;
      const parentStillVisible = nextIdSet.has(edge.prereq_id);
      const childWasVisible = previousKps.some((item) => item.id === edge.next_id && !item.previewLocked);
      if (!parentStillVisible || !childWasVisible) continue;
      const previousChild = previousKps.find((item) => item.id === edge.next_id);
      if (previousChild && !kpById.has(previousChild.id)) {
        kpById.set(previousChild.id, { ...previousChild });
        nextIdSet.add(previousChild.id);
      }
      if (!stableEdges.some((item) => item.prereq_id === edge.prereq_id && item.next_id === edge.next_id)) {
        stableEdges.push({ ...edge });
      }
    }
    visibleKps.value = Array.from(kpById.values());
    visibleEdges.value = stableEdges.filter((edge) => nextIdSet.has(edge.prereq_id) && nextIdSet.has(edge.next_id));
  } else {
    visibleKps.value = nextKps;
    visibleEdges.value = nextEdges;
  }

  const routeKp = Number(route.query.kp || 0);
  const firstLearning = visibleKps.value.find((item) => item.status === "learning" && !item.previewLocked && !isCompleted(item))
    ?? visibleKps.value.find((item) => !item.previewLocked && !isCompleted(item))
    ?? visibleKps.value.find((item) => !item.previewLocked);
  const requestedKp = requestedSourceId
    ? visibleKps.value.find((item) => item.id === requestedSourceId && !item.previewLocked)
    : null;
  const queryKp = routeKp
    ? visibleKps.value.find((item) => item.id === routeKp && !item.previewLocked)
    : null;
  const nextCurrent = requestedKp ?? queryKp ?? firstLearning ?? visibleKps.value.find((item) => !item.previewLocked) ?? null;
  recommendationSourceKpId.value = nextCurrent?.id ?? null;
  currentKpId.value = nextCurrent?.id ?? null;
}

async function loadRecommendation(preferredSourceId?: number | null) {
  const requestSeq = ++recoRequestSeq.value;
  const sourceKpId = preferredSourceId || recommendationSourceKpId.value || currentKpId.value;
  if (!sourceKpId) {
    reco.value = null;
    return;
  }
  recoLoading.value = true;
  try {
    const res = await api.get("/reco", {
      params: { kp_id: sourceKpId, ai: false },
      skipGlobalLoading: true,
    } as any);
    if (requestSeq !== recoRequestSeq.value) return;
    reco.value = res.data ?? null;
  } catch {
    if (requestSeq !== recoRequestSeq.value) return;
    reco.value = null;
  } finally {
    if (requestSeq === recoRequestSeq.value) recoLoading.value = false;
  }
}

async function refreshPage(forceReload = false) {
  loading.value = courses.value.length === 0 && visibleKps.value.length === 0;
  try {
    const useCache = !forceReload;
    await loadCourses(useCache);
    await loadVisibleKps(useCache);
    syncQuery();
    centerCurrentStop();
    loading.value = false;
    void loadRecommendation().then(() => {
      syncQuery();
      centerCurrentStop();
    });
  } catch (e: any) {
    resetState();
    if (e?.response?.status !== 401) ElMessage.error(e?.response?.data?.detail ?? "加载学习路线失败");
  } finally {
    loading.value = false;
  }
}

async function handleCourseChange() {
  currentKpId.value = null;
  reco.value = null;
  await loadVisibleKps();
  syncQuery();
  centerCurrentStop();
  void loadRecommendation().then(() => {
    syncQuery();
    centerCurrentStop();
  });
}

function selectKp(kp: KP) {
  if (suppressNodeClick.value) return;
  if (isLockedKp(kp)) {
    ElMessage.info("先完成当前关卡，后续关卡会自动解锁");
    return;
  }
  currentKpId.value = kp.id;
  recommendationSourceKpId.value = kp.id;
  scheduleSelectionSideEffects(kp.id);
}

async function chooseKp(kp?: KP | null) {
  if (!kp) {
    ElMessage.warning("当前还没有可选择的节点");
    return false;
  }
  if (isLockedKp(kp)) {
    ElMessage.info("先完成前置节点，后续节点会自动解锁");
    return false;
  }
  if (choosingKpId.value === kp.id) return false;
  choosingKpId.value = kp.id;
  try {
    await api.post(`/graph/path-choice/${kp.id}`, {}, { skipGlobalLoading: true } as any);
    currentKpId.value = kp.id;
    recommendationSourceKpId.value = kp.id;
    syncQuery();
    centerCurrentStop();
    void loadVisibleKps(false, kp.id).then(() => {
      syncQuery();
      centerCurrentStop();
    });
    void loadRecommendation(kp.id).then(() => centerCurrentStop());
    return true;
  } catch (e: any) {
    ElMessage.warning(e?.response?.data?.detail ?? "当前节点暂时不能加入学习路径");
    return false;
  } finally {
    choosingKpId.value = null;
  }
}

async function openKp(id?: number | null) {
  if (courseClosed.value) {
    openReport();
    return;
  }
  const targetId = Number(id || currentKpId.value || recommendedKp.value?.id || 0);
  if (!targetId) {
    ElMessage.warning("当前还没有可学习的关卡");
    return;
  }
  const targetKp = findKpById(targetId);
  if (!targetKp) {
    ElMessage.warning("当前节点不在可学习路径中，请先刷新路径");
    return;
  }
  if (isLockedKp(targetKp)) {
    ElMessage.info("先完成前置节点，后续节点会自动解锁");
    return;
  }
  router.push({
    path: `/student/kp-content/${targetId}`,
    query: { subject: subject.value || undefined, from: "learning-path" },
  });
}
function openReport() {
  router.push({ path: "/student/report", query: { subject: subject.value || undefined } });
}

watch(
  () => route.query.subject,
  async (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) {
      subject.value = next;
      await refreshPage();
    }
  },
);

onMounted(() => refreshPage());
onBeforeUnmount(() => clearSelectionTimers());
</script>

<template>
  <div v-loading="loading" class="learning-route-page">
    <section class="learning-route-hero">
      <div class="learning-route-hero__copy">
        <span class="learning-route-badge">可选学习路径</span>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageLead }}</p>
      </div>
      <div class="learning-route-hero__metrics" :style="routeProgressStyle">
        <div class="learning-route-hero__ring">
          <strong>{{ progressPercent }}%</strong>
          <span>完成度</span>
        </div>
        <div class="learning-route-hero__metric-body">
          <div class="learning-route-hero__metric-row">
            <span>当前位置</span>
            <strong>{{ selectedStopIndex }}/{{ routeKps.length || 1 }}</strong>
          </div>
          <div class="learning-route-hero__metric-track"><i></i></div>
          <div class="learning-route-hero__metric-row">
            <span>节点状态</span>
            <strong>{{ currentStatusLabel }}</strong>
          </div>
        </div>
      </div>
      <div class="learning-route-actions">
        <el-select v-model="subject" class="learning-route-course" placeholder="选择课程" :disabled="visibleCourses.length === 0" @change="handleCourseChange">
          <el-option v-for="course in routeSelectableCourses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button type="button" class="learning-route-button" @click="jumpToRecommendation">回到建议优先</button>
        <button type="button" class="learning-route-button" @click="() => refreshPage(true)">刷新</button>
        <button v-if="courseClosed" type="button" class="learning-route-button learning-route-button--primary" @click="openReport">查看报告</button>
        <button v-else type="button" class="learning-route-button learning-route-button--primary" @click="openKp(currentKpId || recommendedKp?.id)">进入所选节点</button>
      </div>
    </section>

    <section v-if="!subject" class="learning-route-empty">
      <strong>当前没有可继续学习的课程</strong>
      <p>如果已经完成课程，请进入学习报告查看评分结果。</p>
      <button type="button" class="learning-route-button learning-route-button--primary" @click="openReport">查看学习报告</button>
    </section>

    <section v-else class="learning-route-layout">
      <main class="learning-route-board">
        <header class="learning-route-board__head">
          <div class="learning-route-board__title">
            <span class="learning-route-badge">当前课程</span>
            <h2>{{ currentCourse?.title || subject }}</h2>
          </div>
          <div class="learning-route-board__tools">
            <div class="learning-route-legend">
              <span class="is-selected">当前选择</span>
              <span class="is-recommended">建议优先</span>
              <span class="is-path">已选路径</span>
              <span class="is-done">已完成</span>
              <span class="is-current">当前</span>
              <span class="is-open">可学习</span>
              <span class="is-locked">待解锁</span>
            </div>
            <div class="learning-route-progress" :style="routeProgressStyle">
              <strong>{{ progressPercent }}%</strong>
              <span>完成度</span>
            </div>
          </div>
        </header>

        <div
          ref="mapRef"
          class="learning-route-map"
          :class="{ 'is-dragging': isDragging }"
          @pointerdown="onMapPointerDown"
          @pointermove="onMapPointerMove"
          @pointerup="onMapPointerUp"
          @pointercancel="onMapPointerUp"
          @wheel="onMapWheel"
          @dragstart.prevent
        >
          <div class="learning-route-drag-hint">按住画布可上下左右拖动</div>
          <div class="learning-route-canvas" :style="mapCanvasStyle">
            <svg class="learning-route-lines" :viewBox="`0 0 ${routeContentWidth} ${routeContentHeight}`" aria-hidden="true">
              <path
                v-for="line in connectorLines"
                :key="line.key"
                class="learning-route-line"
                :class="`is-${line.state}`"
                :d="line.d"
              />
            </svg>
            <article
              v-for="stop in routeStops"
              :key="stop.kp.id"
              class="learning-route-stop"
              :class="[
                `is-${nodeState(stop.kp)}`,
                `role-${stop.role}`,
                cardSide(stop),
                {
                  'is-focus': stop.kp.id === currentKpId,
                  'is-recommendation': stop.kp.id === recommendedNodeId,
                },
              ]"
              :style="{ left: `${stop.x}px`, top: `${stop.y}px` }"
              @pointerdown="onStopPointerDown"
              @click.stop="selectKp(stop.kp)"
            >
              <button
                class="learning-route-node"
                type="button"
                :aria-label="`选择${stop.kp.title}`"
              >
                <el-icon><component :is="nodeIcon(stop.kp)" /></el-icon>
              </button>
              <div class="learning-route-card">
                <span>{{ stop.kp.code }}</span>
                <strong>{{ stop.kp.title }}</strong>
                <small>{{ roleLabel(stop.role) }} · {{ statusLabel(stop.kp) }}</small>
                <div class="learning-route-card__bar">
                  <i :style="{ width: `${Math.round(Number(stop.kp.mastery || 0) * 100)}%` }"></i>
                </div>
                <em>掌握度 {{ Math.round(Number(stop.kp.mastery || 0) * 100) }}%</em>
              </div>
            </article>
          </div>
        </div>
      </main>

      <aside class="learning-route-side">
        <section class="learning-route-panel learning-route-panel--focus">
          <div class="learning-route-panel__top">
            <span class="learning-route-badge">{{ focusBadge }}</span>
            <span class="learning-route-status" :class="`is-${currentNodeState}`">{{ currentStatusLabel }}</span>
          </div>
          <div class="learning-route-focus-grid">
            <div class="learning-route-mastery" :style="masteryRingStyle">
              <strong>{{ currentMasteryPercent }}%</strong>
              <span>掌握度</span>
            </div>
            <div>
              <h2>{{ currentKp?.title || recommendedKp?.title || "等待推荐" }}</h2>
              <p>{{ currentKp?.code || recommendedKp?.code || "暂无节点" }}</p>
            </div>
          </div>
          <p>{{ focusText }}</p>
          <button class="learning-route-button learning-route-button--primary learning-route-button--wide" type="button" @click="openKp(currentKpId || recommendedKp?.id)">
            {{ focusActionText }}
          </button>
        </section>

        <section class="learning-route-panel">
          <span class="learning-route-badge">学习建议</span>
          <ul class="learning-route-advice">
            <li v-for="item in learningAdvice" :key="item">{{ item }}</li>
          </ul>
        </section>

        <section class="learning-route-panel">
          <span class="learning-route-badge">图谱概况</span>
          <div class="learning-route-stats">
            <div><strong>{{ routeKps.length }}</strong><span>可见节点</span></div>
            <div><strong>{{ completedCount }}</strong><span>已完成</span></div>
            <div><strong>{{ previewCount || routeTerminalCount }}</strong><span>{{ previewCount ? "待解锁" : "终点" }}</span></div>
          </div>
          <div class="learning-route-mini-progress" :style="routeProgressStyle"><i></i></div>
        </section>

        <section class="learning-route-panel">
          <span class="learning-route-badge">路径与可选节点</span>
          <div class="learning-route-steps">
            <button
              v-for="item in routeStepItems"
              :key="item.kp.id"
              type="button"
              class="learning-route-step"
              :class="[`is-${item.state}`, { 'is-active': item.kp.id === currentKp?.id }]"
              @click="selectKp(item.kp)"
            >
              <span>{{ item.index }}</span>
              <strong>{{ item.kp.title }}</strong>
              <em>{{ item.mastery }}%</em>
            </button>
          </div>
        </section>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.learning-route-page {
  width: min(100%, 1520px);
  min-height: calc(100vh - 96px);
  margin: 0 auto;
  display: grid;
  gap: 18px;
  padding-bottom: 24px;
  color: #102033;
}

.learning-route-hero,
.learning-route-board,
.learning-route-panel,
.learning-route-empty {
  border: 1px solid rgba(160, 184, 207, 0.42);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(38, 62, 92, 0.08);
}

.learning-route-hero {
  display: grid;
  grid-template-columns: minmax(460px, 1fr) minmax(320px, auto);
  align-items: start;
  gap: 18px;
  padding: 20px 24px;
  background:
    linear-gradient(135deg, rgba(238, 246, 255, 0.96), rgba(250, 255, 244, 0.98)),
    #ffffff;
}

.learning-route-hero__copy {
  display: grid;
  gap: 8px;
  min-width: 360px;
  max-width: 720px;
}

.learning-route-badge {
  width: fit-content;
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  font-size: 12px;
  font-weight: 900;
}

.learning-route-hero h1,
.learning-route-board__head h2,
.learning-route-panel h2 {
  margin: 0;
  color: #102033;
  overflow-wrap: break-word;
}

.learning-route-hero h1 {
  font-size: 30px;
  line-height: 1.12;
  word-break: keep-all;
  text-wrap: balance;
}

.learning-route-hero p,
.learning-route-panel p,
.learning-route-empty p {
  margin: 0;
  color: #5f6d5d;
  line-height: 1.7;
  overflow-wrap: break-word;
}

.learning-route-actions {
  grid-column: 1 / -1;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
}

.learning-route-hero__metrics {
  min-width: 360px;
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(248, 251, 255, 0.86)),
    linear-gradient(90deg, rgba(34, 197, 94, 0.1) var(--route-progress), rgba(255, 255, 255, 0.7) 0);
  border: 1px solid rgba(148, 163, 184, 0.28);
  box-shadow: 0 14px 30px rgba(20, 35, 58, 0.08);
}

.learning-route-hero__ring {
  width: 82px;
  height: 82px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 2px;
  border-radius: 999px;
  background: conic-gradient(#22c55e var(--route-progress), #dbeafe 0);
  box-shadow: inset 0 0 0 8px #ffffff, 0 10px 20px rgba(34, 197, 94, 0.14);
}

.learning-route-hero__ring strong {
  color: #0f172a;
  font-size: 22px;
  line-height: 1;
}

.learning-route-hero__ring span {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.learning-route-hero__metric-body {
  display: grid;
  gap: 9px;
  min-width: 0;
}

.learning-route-hero__metric-row {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.learning-route-hero__metric-row span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.learning-route-hero__metric-row strong {
  color: #102033;
  font-size: 17px;
  font-weight: 900;
  line-height: 1.25;
  overflow-wrap: break-word;
}

.learning-route-hero__metric-track {
  height: 9px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.learning-route-hero__metric-track i {
  display: block;
  width: var(--route-progress);
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #22c55e, #0ea5e9);
}

.learning-route-course {
  width: 260px;
}

.learning-route-button {
  min-height: 42px;
  border: 0;
  border-radius: 10px;
  padding: 0 18px;
  background: #e2e8f0;
  color: #1e293b;
  font-weight: 900;
  cursor: pointer;
  box-shadow: inset 0 -3px 0 rgba(15, 23, 42, 0.08);
  transition: transform 180ms ease, box-shadow 180ms ease, background 180ms ease;
}

.learning-route-button:hover,
.learning-route-button:focus-visible {
  background: #dbeafe;
  box-shadow: inset 0 -3px 0 rgba(37, 99, 235, 0.18), 0 8px 18px rgba(37, 99, 235, 0.12);
}

.learning-route-button--primary {
  background: #22c55e;
  color: #ffffff;
  box-shadow: inset 0 -4px 0 #15803d;
}

.learning-route-button--primary:hover,
.learning-route-button--primary:focus-visible {
  background: #16a34a;
  box-shadow: inset 0 -4px 0 #166534, 0 10px 22px rgba(34, 197, 94, 0.22);
}

.learning-route-button--wide {
  width: 100%;
}

.learning-route-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 20px;
  align-items: stretch;
}

.learning-route-board {
  min-height: 760px;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow: hidden;
}

.learning-route-board__head {
  display: grid;
  grid-template-columns: minmax(132px, 180px) minmax(0, 1fr);
  align-items: center;
  gap: 16px 22px;
  padding-bottom: 18px;
  border-bottom: 1px solid #edf3ea;
}

.learning-route-board__title {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.learning-route-board__title h2 {
  font-size: 28px;
  line-height: 1.18;
  word-break: keep-all;
  white-space: nowrap;
}

.learning-route-board__tools {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-width: 0;
  justify-content: end;
}

.learning-route-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

.learning-route-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 9px;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.learning-route-legend .is-current {
  display: none;
}

.learning-route-legend span::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #94a3b8;
}

.learning-route-legend .is-done::before { background: #22c55e; }
.learning-route-legend .is-current::before { background: #f59e0b; }
.learning-route-legend .is-selected::before { background: #f59e0b; }
.learning-route-legend .is-recommended::before { background: #8b5cf6; }
.learning-route-legend .is-path::before { background: #ef4444; }
.learning-route-legend .is-open::before { background: #0ea5e9; }
.learning-route-legend .is-locked::before { background: #94a3b8; }

.learning-route-progress {
  width: 78px;
  height: 78px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  align-content: center;
  background: conic-gradient(#22c55e var(--route-progress), #e2e8f0 0);
  color: #0f172a;
  box-shadow: inset 0 0 0 8px #ffffff, 0 12px 22px rgba(15, 23, 42, 0.08);
}

.learning-route-progress strong {
  font-size: 22px;
}

.learning-route-progress span {
  font-size: 12px;
  font-weight: 800;
}

.learning-route-map {
  position: relative;
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
  margin-top: 18px;
  overflow: hidden;
  overscroll-behavior: contain;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 14px;
  background:
    radial-gradient(circle at 50% 10%, rgba(34, 197, 94, 0.08), transparent 32%),
    linear-gradient(rgba(203, 213, 225, 0.28) 1px, transparent 1px),
    linear-gradient(90deg, rgba(203, 213, 225, 0.28) 1px, transparent 1px),
    #fbfdf8;
  background-size: 40px 40px, 40px 40px, auto;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.learning-route-map.is-dragging {
  cursor: grabbing;
}

.learning-route-drag-hint {
  position: sticky;
  left: 12px;
  top: 12px;
  z-index: 8;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #ffffff;
  font-size: 12px;
  font-weight: 800;
  pointer-events: none;
  opacity: 0.86;
}

.learning-route-canvas {
  position: absolute;
  left: 0;
  top: 0;
  width: 720px;
  min-width: 1040px;
  margin: 0;
  overflow: hidden;
  transform-origin: 0 0;
  will-change: transform;
}

.learning-route-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.learning-route-line {
  stroke: #cbd5e1;
  stroke-width: 4;
  stroke-linecap: round;
}

.learning-route-line.is-done {
  stroke: #22c55e;
  stroke-width: 6;
}

.learning-route-line.is-current {
  stroke: #f59e0b;
  stroke-width: 6;
}

.learning-route-line.is-selected {
  stroke: #f59e0b;
  stroke-width: 6;
}

.learning-route-line.is-recommended {
  stroke: #8b5cf6;
  stroke-width: 6;
}

.learning-route-line.is-path {
  stroke: #ef4444;
  stroke-width: 6;
}

.learning-route-line.is-locked {
  stroke-dasharray: 8 8;
}

.learning-route-stop {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 0;
  height: 0;
  z-index: 3;
  cursor: pointer;
}

.learning-route-node {
  position: absolute;
  left: 0;
  top: 0;
  transform: translate(-50%, -50%);
  width: 74px;
  height: 74px;
  border: 0;
  border-radius: 999px;
  background: #22c55e;
  color: #ffffff;
  font-size: 30px;
  cursor: pointer;
  box-shadow: inset 0 -7px 0 #15803d, 0 10px 20px rgba(34, 197, 94, 0.24);
  z-index: 3;
}

.learning-route-node::before {
  content: "";
  position: absolute;
  inset: -8px;
  border-radius: 999px;
  border: 4px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 5px 0 rgba(15, 23, 42, 0.08);
}

.learning-route-node :deep(.el-icon) {
  position: relative;
  z-index: 1;
}

.learning-route-stop:hover .learning-route-node,
.learning-route-stop:focus-within .learning-route-node {
  filter: brightness(1.04);
}

.learning-route-stop:hover .learning-route-card,
.learning-route-stop:focus-within .learning-route-card {
  border-color: #93c5fd;
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.14);
}

.learning-route-card {
  position: absolute;
  top: 0;
  width: 176px;
  min-height: 118px;
  display: grid;
  gap: 5px;
  place-items: center;
  padding: 13px 14px;
  border-radius: 12px;
  border: 1px solid #dbe7f3;
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.08);
  text-align: center;
  z-index: 2;
}

.learning-route-stop.is-card-right .learning-route-card {
  left: 112px;
  transform: translateY(-50%);
}

.learning-route-stop.is-card-left .learning-route-card {
  right: 112px;
  left: auto;
  transform: translateY(-50%);
}

.learning-route-card span,
.learning-route-card small {
  color: #71806c;
  font-size: 12px;
  font-weight: 800;
}

.learning-route-card strong {
  color: #102033;
  overflow-wrap: anywhere;
}

.learning-route-card__bar {
  width: 100%;
  height: 7px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.learning-route-card__bar i {
  display: block;
  height: 100%;
  min-width: 4px;
  border-radius: inherit;
  background: linear-gradient(90deg, #22c55e, #0ea5e9);
}

.learning-route-card em {
  color: #475569;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.learning-route-stop.is-current .learning-route-node {
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 100%);
  box-shadow: inset 0 -7px 0 #b45309, 0 18px 30px rgba(245, 158, 11, 0.28);
  animation: routePulse 2s ease-in-out infinite;
}

.learning-route-stop.is-focus .learning-route-node::before {
  border-color: rgba(59, 130, 246, 0.42);
  box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.08);
}

.learning-route-stop.is-focus .learning-route-card {
  border-color: #93c5fd;
  box-shadow: 0 18px 34px rgba(37, 99, 235, 0.15);
}

.learning-route-stop.is-recommendation:not(.is-focus) .learning-route-node::before {
  border-color: rgba(139, 92, 246, 0.3);
}

.learning-route-stop.is-selected .learning-route-node {
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 100%);
  box-shadow: inset 0 -7px 0 #b45309, 0 18px 30px rgba(245, 158, 11, 0.28);
  animation: routePulse 2s ease-in-out infinite;
}

.learning-route-stop.is-recommended .learning-route-node {
  background: linear-gradient(180deg, #a78bfa 0%, #8b5cf6 100%);
  box-shadow: inset 0 -7px 0 #6d28d9, 0 18px 30px rgba(139, 92, 246, 0.24);
}

.learning-route-stop.is-path .learning-route-node {
  background: linear-gradient(180deg, #fb7185 0%, #ef4444 100%);
  box-shadow: inset 0 -7px 0 #b91c1c, 0 18px 30px rgba(239, 68, 68, 0.22);
}

.learning-route-stop.is-open .learning-route-node {
  background: linear-gradient(180deg, #38bdf8 0%, #0284c7 100%);
  box-shadow: inset 0 -7px 0 #0369a1, 0 16px 26px rgba(14, 165, 233, 0.2);
}

.learning-route-stop.is-locked .learning-route-node {
  background: linear-gradient(180deg, #d7dfd1 0%, #aebbaa 100%);
  box-shadow: inset 0 -8px 0 #879281, 0 12px 22px rgba(95, 111, 90, 0.16);
}

.learning-route-stop.is-locked .learning-route-card {
  opacity: 0.68;
}

.learning-route-side {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
  align-self: stretch;
  position: sticky;
  top: 18px;
}

.learning-route-panel {
  display: grid;
  gap: 14px;
  padding: 20px;
}

.learning-route-panel--focus {
  background: linear-gradient(180deg, #fbfff8, #f8fbff);
}

.learning-route-panel__top,
.learning-route-focus-grid {
  display: flex;
  align-items: center;
  gap: 14px;
  justify-content: space-between;
}

.learning-route-status {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 900;
}

.learning-route-status.is-done {
  background: #dcfce7;
  color: #166534;
}

.learning-route-status.is-current {
  background: #fef3c7;
  color: #92400e;
}

.learning-route-status.is-selected {
  background: #fef3c7;
  color: #92400e;
}

.learning-route-status.is-recommended {
  background: #ede9fe;
  color: #5b21b6;
}

.learning-route-status.is-path {
  background: #fee2e2;
  color: #991b1b;
}

.learning-route-status.is-locked {
  background: #e2e8f0;
  color: #475569;
}

.learning-route-focus-grid {
  justify-content: flex-start;
}

.learning-route-focus-grid h2 {
  font-size: 24px;
  line-height: 1.2;
}

.learning-route-mastery {
  width: 92px;
  height: 92px;
  flex: 0 0 auto;
  border-radius: 999px;
  display: grid;
  place-items: center;
  align-content: center;
  background: conic-gradient(#0ea5e9 var(--mastery-progress), #e2e8f0 0);
  box-shadow: inset 0 0 0 8px #ffffff, 0 10px 24px rgba(14, 165, 233, 0.16);
}

.learning-route-mastery strong {
  color: #0f172a;
  font-size: 22px;
}

.learning-route-mastery span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.learning-route-advice {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.learning-route-advice li {
  position: relative;
  padding: 10px 12px 10px 30px;
  border-radius: 10px;
  background: #f8fafc;
  color: #334155;
  line-height: 1.55;
  font-weight: 700;
}

.learning-route-advice li::before {
  content: "";
  position: absolute;
  left: 12px;
  top: 18px;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #22c55e;
}

.learning-route-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.learning-route-stats div {
  display: grid;
  place-items: center;
  gap: 4px;
  padding: 12px 8px;
  border-radius: 10px;
  background: #f8fafc;
}

.learning-route-stats strong {
  font-size: 24px;
  color: #102033;
}

.learning-route-stats span {
  color: #71806c;
  font-size: 12px;
  font-weight: 800;
}

.learning-route-mini-progress {
  height: 9px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.learning-route-mini-progress i {
  display: block;
  width: var(--route-progress);
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #22c55e, #0ea5e9);
}

.learning-route-steps {
  display: grid;
  gap: 9px;
  max-height: 100%;
  overflow: auto;
  padding-right: 2px;
  scrollbar-width: thin;
}

.learning-route-step {
  width: 100%;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
  padding: 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
}

.learning-route-step:hover,
.learning-route-step:focus-visible,
.learning-route-step.is-active {
  border-color: #93c5fd;
  background: #f8fbff;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.1);
}

.learning-route-step span {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  font-weight: 900;
}

.learning-route-step.is-done span {
  background: #dcfce7;
  color: #166534;
}

.learning-route-step.is-current span {
  background: #fef3c7;
  color: #92400e;
}

.learning-route-step.is-selected span {
  background: #fef3c7;
  color: #92400e;
}

.learning-route-step.is-recommended span {
  background: #ede9fe;
  color: #5b21b6;
}

.learning-route-step.is-path span {
  background: #fee2e2;
  color: #991b1b;
}

.learning-route-step.is-open span {
  background: #e0f2fe;
  color: #0369a1;
}

.learning-route-step strong {
  min-width: 0;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.learning-route-step em {
  color: #64748b;
  font-style: normal;
  font-weight: 900;
}

.learning-route-empty {
  display: grid;
  place-items: center;
  text-align: center;
  gap: 12px;
  padding: 48px;
}

@media (max-width: 1080px) {
  .learning-route-hero {
    grid-template-columns: 1fr;
  }

  .learning-route-hero__copy {
    min-width: 0;
  }

  .learning-route-hero__metrics {
    width: 100%;
    min-width: 0;
  }

  .learning-route-layout {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .learning-route-board__head {
    grid-template-columns: minmax(132px, 180px) minmax(0, 1fr);
  }

  .learning-route-side {
    height: auto;
    position: static;
  }
}

@media (max-width: 720px) {
  .learning-route-hero,
  .learning-route-board__head {
    align-items: flex-start;
  }

  .learning-route-board__head {
    grid-template-columns: 1fr;
  }

  .learning-route-board__title h2 {
    white-space: normal;
  }

  .learning-route-course,
  .learning-route-actions {
    width: 100%;
  }

  .learning-route-actions,
  .learning-route-focus-grid {
    flex-direction: column;
    align-items: stretch;
  }

  .learning-route-board__tools {
    grid-template-columns: 1fr;
    justify-content: stretch;
  }

  .learning-route-legend {
    justify-content: flex-start;
  }

  .learning-route-hero__metrics {
    grid-template-columns: 1fr;
  }

  .learning-route-board {
    min-height: 0;
    padding: 16px;
  }

  .learning-route-map {
    height: 500px;
    min-height: 500px;
  }
}

@keyframes routePulse {
  0%,
  100% {
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.04);
  }
}

@media (prefers-reduced-motion: reduce) {
  .learning-route-stop.is-current .learning-route-node {
    animation: none;
  }

  .learning-route-stop.is-selected .learning-route-node {
    animation: none;
  }

  .learning-route-button,
  .learning-route-step {
    transition: none;
  }
}
</style>
