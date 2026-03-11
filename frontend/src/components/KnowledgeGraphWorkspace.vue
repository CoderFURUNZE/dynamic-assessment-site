<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type GraphKp = {
  id: number;
  code: string;
  title: string;
  description: string;
  chapter?: string;
  importance?: number;
  difficulty?: number;
};

type GraphEdge = {
  prereq_id: number;
  next_id: number;
  relation_type: string;
};

type OverlayNode = {
  kp_id: number;
  mastery: number;
  status: string;
  recommended?: boolean;
  blocked_reason?: string | null;
};

type RelationNode = {
  id: number;
  code: string;
  title: string;
};

type NodeDetail = {
  kp: GraphKp & { ability_tag?: string; literacy_tag?: string };
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

const props = defineProps<{
  subject: string;
  grade: string;
  currentKpId?: number | null;
  recommendedKpId?: number | null;
}>();

const emit = defineEmits<{
  (e: "select-kp", id: number): void;
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
const nodeDetail = ref<NodeDetail | null>(null);
const drawerOpen = ref(true);
const canvasScale = ref(1);
const panX = ref(0);
const panY = ref(0);
const draggingCanvas = ref(false);
const draggingNode = ref<DragNode | null>(null);
const dragStartX = ref(0);
const dragStartY = ref(0);
const dragOriginX = ref(0);
const dragOriginY = ref(0);
const kpPositions = ref<Record<number, Point>>({});
const categoryPositions = ref<Record<string, Point>>({});

const overlayMap = computed(() => new Map(overlay.value.map((item) => [item.kp_id, item])));

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
  for (const kp of filteredKps.value) {
    const status = overlayMap.value.get(kp.id)?.status ?? "not_started";
    if (status === "mastered") mastered += 1;
    else if (status === "learning") learning += 1;
    else if (status === "risk") risk += 1;
    else idle += 1;
  }
  return { mastered, learning, risk, idle };
});

const defaultCategoryPositions = computed<Record<string, Point>>(() => {
  const entries: Record<string, Point> = {};
  const list = categoryNodes.value;
  const total = Math.max(list.length, 1);
  const spread = Math.min(620, Math.max(280, (total - 1) * 210));
  const startX = 750 - spread / 2;
  const endX = 750 + spread / 2;
  const step = total === 1 ? 0 : spread / (total - 1);
  list.forEach((item, index) => {
    entries[item.key] = {
      x: startX + step * index,
      y: 170 + (index % 2 === 0 ? 0 : 36),
    };
  });
  return entries;
});

const defaultKpPositions = computed<Record<number, Point>>(() => {
  const entries: Record<number, Point> = {};
  const groups = new Map<string, GraphKp[]>();
  for (const kp of filteredKps.value) {
    const key = kp.chapter || "未分章";
    const arr = groups.get(key) ?? [];
    arr.push(kp);
    groups.set(key, arr);
  }

  for (const [chapter, items] of groups.entries()) {
    const anchor = categoryPositions.value[chapter] ?? defaultCategoryPositions.value[chapter] ?? { x: 780, y: 180 };
    const total = Math.max(items.length, 1);
    const radius = Math.min(220, 104 + items.length * 12);
    const verticalLift = total <= 4 ? 160 : 190;
    items.forEach((kp, index) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / total;
      entries[kp.id] = {
        x: anchor.x + Math.cos(angle) * radius,
        y: anchor.y + verticalLift + Math.sin(angle) * (radius * 0.74),
      };
    });
  }

  return entries;
});

const visibleEdges = computed(() => {
  const ids = new Set(filteredKps.value.map((kp) => kp.id));
  return edges.value.filter((edge) => ids.has(edge.prereq_id) && ids.has(edge.next_id));
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
  return overlayMap.value.get(selectedKp.value.id) ?? null;
});

const selectedCategoryOverview = computed(() => {
  if (!selectedCategoryNode.value) return null;
  const chapter = selectedCategoryNode.value.key;
  const items = kps.value.filter((kp) => (kp.chapter || "未分章") === chapter);
  const mastered = items.filter((kp) => overlayMap.value.get(kp.id)?.status === "mastered").length;
  const learning = items.filter((kp) => overlayMap.value.get(kp.id)?.status === "learning").length;
  const risk = items.filter((kp) => overlayMap.value.get(kp.id)?.status === "risk").length;
  const recommended = items.find((kp) => overlayMap.value.get(kp.id)?.recommended);
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
  return categoryPositions.value[key] ?? defaultCategoryPositions.value[key] ?? { x: 780, y: 180 };
}

function kpPoint(id: number) {
  return kpPositions.value[id] ?? defaultKpPositions.value[id] ?? { x: 780, y: 500 };
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
  for (const kp of filteredKps.value) {
    next[kp.id] = kpPositions.value[kp.id] ?? defaultKpPositions.value[kp.id];
  }
  kpPositions.value = next;
}

function nodeColor(status?: string) {
  if (status === "mastered") return "#5ef0a8";
  if (status === "learning") return "#62a4ff";
  if (status === "risk") return "#ffb066";
  return "#aeb8c6";
}

function nodeLabel(status?: string) {
  if (status === "mastered") return "已掌握";
  if (status === "learning") return "学习中";
  if (status === "risk") return "风险";
  return "未开始";
}

function nodeRadius(kp: GraphKp) {
  const base = 44 + Math.round((kp.importance ?? 0.5) * 16);
  if (kp.id === selectedKp.value?.id) return base + 8;
  if (kp.id === props.recommendedKpId) return base + 4;
  return base;
}

function metricPercent(value?: number | null) {
  return Math.round((value ?? 0) * 100);
}

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const res = await api.get(`/graph/map?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
    kps.value = res.data.base?.kps ?? [];
    edges.value = res.data.base?.edges ?? [];
    overlay.value = res.data.overlay ?? [];
    syncCategoryPositions();
    syncKpPositions();
    const valid = props.currentKpId && kps.value.some((item) => item.id === props.currentKpId);
    if (valid) {
      selectedType.value = "kp";
      selectedId.value = props.currentKpId ?? null;
    } else if (!selectedId.value && kps.value.length) {
      selectedType.value = "kp";
      selectedId.value = kps.value[0].id;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识图谱失败");
  } finally {
    loading.value = false;
  }
}

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
  selectedType.value = "kp";
  selectedId.value = id;
  selectedCategory.value = null;
  drawerOpen.value = true;
  emit("select-kp", id);
}

function selectCategory(chapter: string) {
  selectedType.value = "category";
  selectedCategory.value = chapter;
  selectedId.value = null;
  nodeDetail.value = null;
  activeChapter.value = chapter;
  drawerOpen.value = true;
}

function zoomIn() {
  canvasScale.value = Math.min(1.6, Number((canvasScale.value + 0.1).toFixed(2)));
}

function zoomOut() {
  canvasScale.value = Math.max(0.7, Number((canvasScale.value - 0.1).toFixed(2)));
}

function resetViewport() {
  canvasScale.value = 1;
  panX.value = 0;
  panY.value = 0;
  activeChapter.value = "全部";
  search.value = "";
  syncCategoryPositions();
  syncKpPositions();
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
      kpPositions.value = {
        ...kpPositions.value,
        [Number(draggingNode.value.id)]: {
          x: draggingNode.value.origin.x + dx,
          y: draggingNode.value.origin.y + dy,
        },
      };
    } else {
      categoryPositions.value = {
        ...categoryPositions.value,
        [String(draggingNode.value.id)]: {
          x: draggingNode.value.origin.x + dx,
          y: draggingNode.value.origin.y + dy,
        },
      };
    }
    return;
  }
  if (!draggingCanvas.value) return;
  panX.value = dragOriginX.value + (event.clientX - dragStartX.value);
  panY.value = dragOriginY.value + (event.clientY - dragStartY.value);
}

function stopDragging() {
  draggingCanvas.value = false;
  draggingNode.value = null;
}

watch(
  () => [props.subject, props.grade],
  async () => {
    await load();
  },
  { immediate: true }
);

watch(
  () => props.currentKpId,
  (value) => {
    if (value) {
      selectedType.value = "kp";
      selectedId.value = value;
      selectedCategory.value = null;
    }
  }
);

watch(selectedId, (value) => {
  if (selectedType.value === "kp") {
    loadNodeDetail(value ?? null);
  }
});

watch(filteredKps, () => {
  syncCategoryPositions();
  syncKpPositions();
});

window.addEventListener("mousemove", onWindowMouseMove);
window.addEventListener("mouseup", stopDragging);

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", stopDragging);
});
</script>

<template>
  <div class="workspace-shell" v-loading="loading">
    <div class="workspace-badge">知识图谱</div>

    <aside class="workspace-sidebar">
      <div class="workspace-mode">
        <button class="workspace-mode__item active">导航</button>
        <button class="workspace-mode__item" @click="activeChapter = '全部'">全局</button>
      </div>

      <el-input v-model="search" placeholder="检索分类或知识点" clearable class="workspace-search" />

      <div class="workspace-tree">
        <details v-for="item in treeNodes" :key="item.key" class="workspace-tree__group" :open="activeChapter === item.key || activeChapter === '全部'">
          <summary class="workspace-tree__summary" :class="{ active: activeChapter === item.key && selectedType === 'category' }" @click.prevent="selectCategory(item.key)">
            <span>{{ item.title }}</span>
            <strong>{{ item.children.length }}</strong>
          </summary>
          <div class="workspace-tree__children">
            <button
              v-for="kp in item.children"
              :key="kp.id"
              class="workspace-tree__child"
              :class="{ active: kp.id === selectedKp?.id }"
              @click="selectKp(kp.id)"
            >
              <span>{{ kp.title }}</span>
              <small>{{ kp.code }}</small>
            </button>
          </div>
        </details>
      </div>
    </aside>

    <section class="workspace-stage" :class="{ 'workspace-stage--dragging': draggingCanvas }" @mousedown="onStageMouseDown">
      <div class="workspace-stage__top">
        <div class="workspace-stage__tabs">
          <span class="active">课程图谱</span>
          <span>分类总览</span>
        </div>
        <div class="workspace-stage__searchbar">
          <button class="workspace-stage__icon">⌕</button>
          <div class="workspace-stage__course">{{ props.subject }}</div>
          <button class="workspace-stage__icon" @click="resetViewport">⟳</button>
        </div>
      </div>

      <svg
        class="workspace-canvas"
        viewBox="0 0 1500 980"
        preserveAspectRatio="xMidYMid meet"
        :style="{ transform: `translate(${panX}px, ${panY}px) scale(${canvasScale})` }"
      >
        <rect x="0" y="0" width="1500" height="980" rx="42" fill="#082d6e" />
        <rect x="18" y="18" width="1464" height="944" rx="34" fill="none" stroke="transparent" />

        <line
          v-for="edge in visibleEdges"
          :key="`${edge.prereq_id}-${edge.next_id}-${edge.relation_type}`"
          :x1="kpPoint(edge.prereq_id).x"
          :y1="kpPoint(edge.prereq_id).y"
          :x2="kpPoint(edge.next_id).x"
          :y2="kpPoint(edge.next_id).y"
          :stroke="edge.relation_type === 'related' ? 'rgba(121,160,255,0.24)' : 'rgba(255,255,255,0.14)'"
          :stroke-dasharray="edge.relation_type === 'related' ? '10 8' : '0'"
          stroke-width="2.2"
        />

        <line
          v-for="kp in filteredKps"
          :key="`cat-${kp.id}`"
          :x1="categoryPoint(kp.chapter || '未分章').x"
          :y1="categoryPoint(kp.chapter || '未分章').y + 26"
          :x2="kpPoint(kp.id).x"
          :y2="kpPoint(kp.id).y - 22"
          stroke="rgba(120, 170, 255, 0.12)"
          stroke-width="1.8"
          stroke-dasharray="7 7"
        />

        <g
          v-for="category in categoryNodes"
          :key="category.key"
          class="workspace-category-node"
          :transform="`translate(${categoryPoint(category.key).x}, ${categoryPoint(category.key).y})`"
          @click="selectCategory(category.key)"
          @mousedown="onNodeMouseDown($event, 'category', category.key)"
        >
          <rect x="-76" y="-34" width="152" height="68" rx="20" :fill="selectedCategory === category.key ? 'rgba(137, 176, 255, 0.32)' : 'rgba(198, 216, 255, 0.18)'" :stroke="selectedCategory === category.key ? '#d7e7ff' : 'rgba(215,231,255,0.18)'" stroke-width="2.5" />
          <text class="workspace-category-node__title" text-anchor="middle" y="-4">{{ category.title }}</text>
          <text class="workspace-category-node__meta" text-anchor="middle" y="18">{{ category.total }} 个知识点</text>
        </g>

        <g
          v-for="kp in filteredKps"
          :key="kp.id"
          class="workspace-node"
          :transform="`translate(${kpPoint(kp.id).x}, ${kpPoint(kp.id).y})`"
          @click="selectKp(kp.id)"
          @mousedown="onNodeMouseDown($event, 'kp', kp.id)"
        >
          <circle
            v-if="kp.id === props.recommendedKpId"
            :r="nodeRadius(kp) + 16"
            fill="none"
            stroke="rgba(111,140,255,0.82)"
            stroke-width="4"
            stroke-dasharray="10 8"
          />
          <circle :r="nodeRadius(kp) + 10" :fill="`${nodeColor(overlayMap.get(kp.id)?.status)}22`" />
          <circle
            :r="nodeRadius(kp)"
            :fill="kp.id === selectedKp?.id ? '#c9ced7' : '#b7bcc5'"
            :stroke="kp.id === selectedKp?.id ? '#f5f7fb' : 'rgba(255,255,255,0.12)'"
            :stroke-width="kp.id === selectedKp?.id ? 4 : 2"
          />
          <text class="workspace-node__index" text-anchor="middle" y="-10">{{ kp.id }}</text>
          <text class="workspace-node__title" text-anchor="middle" y="18">{{ kp.title.slice(0, 10) }}</text>
        </g>
      </svg>

      <div class="workspace-bottom">
        <div class="workspace-legend">
          <span>圆形：知识点</span>
          <span>方形：分类总览</span>
          <span>虚线：分类包含</span>
        </div>
        <div class="workspace-zoom">
          <button @click="zoomOut">-</button>
          <span>{{ Math.round(canvasScale * 100) }}%</span>
          <button @click="zoomIn">+</button>
        </div>
      </div>
    </section>

    <div class="workspace-view-btn" @click="drawerOpen = !drawerOpen">查看</div>

    <aside class="workspace-drawer" :class="{ open: drawerOpen }" v-if="selectedKp || selectedCategoryNode">
      <template v-if="selectedType === 'kp' && selectedKp">
        <div class="workspace-drawer__status">{{ nodeLabel(activeOverlay?.status) }}</div>
        <div class="workspace-drawer__title">{{ selectedKp.title }}</div>
        <div class="workspace-drawer__meta">{{ selectedKp.code }} · {{ selectedKp.chapter || "未分章" }}</div>

        <div class="workspace-drawer__grid">
          <div class="workspace-drawer__metric">
            <span>掌握度</span>
            <strong>{{ metricPercent(activeOverlay?.mastery) }}%</strong>
          </div>
          <div class="workspace-drawer__metric">
            <span>难度</span>
            <strong>{{ metricPercent(selectedKp.difficulty) }}</strong>
          </div>
        </div>

        <div class="workspace-drawer__block">
          <div class="workspace-drawer__label">学习资源</div>
          <div v-if="(nodeDetail?.resource_list?.length ?? 0) === 0" class="workspace-drawer__empty">暂无资源</div>
          <a v-for="item in nodeDetail?.resource_list ?? []" :key="item.id" class="workspace-drawer__link" :href="item.url" target="_blank" rel="noreferrer">
            {{ item.title }}
          </a>
        </div>

        <div class="workspace-drawer__block">
          <div class="workspace-drawer__label">学习任务</div>
          <div v-if="(nodeDetail?.task_list?.length ?? 0) === 0" class="workspace-drawer__empty">暂无任务</div>
          <div v-for="item in nodeDetail?.task_list ?? []" :key="item.id" class="workspace-drawer__task">
            <strong>{{ item.title }}</strong>
            <span>{{ item.description || '暂无说明' }}</span>
          </div>
        </div>

        <div class="workspace-drawer__block">
          <div class="workspace-drawer__label">前置知识</div>
          <div v-if="(nodeDetail?.prerequisites?.length ?? 0) === 0" class="workspace-drawer__empty">无前置要求</div>
          <div v-else class="workspace-drawer__tags">
            <button v-for="item in nodeDetail?.prerequisites ?? []" :key="item.id" class="workspace-drawer__tag" @click="selectKp(item.id)">
              {{ item.title }}
            </button>
          </div>
        </div>
      </template>

      <template v-else-if="selectedCategoryNode && selectedCategoryOverview">
        <div class="workspace-drawer__status">分类总览</div>
        <div class="workspace-drawer__title">{{ selectedCategoryNode.title }}</div>
        <div class="workspace-drawer__meta">共 {{ selectedCategoryOverview.total }} 个知识点</div>

        <div class="workspace-drawer__grid workspace-drawer__grid--four">
          <div class="workspace-drawer__metric"><span>已掌握</span><strong>{{ selectedCategoryOverview.mastered }}</strong></div>
          <div class="workspace-drawer__metric"><span>学习中</span><strong>{{ selectedCategoryOverview.learning }}</strong></div>
          <div class="workspace-drawer__metric"><span>风险</span><strong>{{ selectedCategoryOverview.risk }}</strong></div>
          <div class="workspace-drawer__metric"><span>未开始</span><strong>{{ selectedCategoryOverview.idle }}</strong></div>
        </div>

        <div class="workspace-drawer__block">
          <div class="workspace-drawer__label">分类内知识点</div>
          <div class="workspace-drawer__tags">
            <button v-for="item in selectedCategoryOverview.items" :key="item.id" class="workspace-drawer__tag" @click="selectKp(item.id)">
              {{ item.title }}
            </button>
          </div>
        </div>

        <div class="workspace-drawer__block">
          <div class="workspace-drawer__label">推荐入口</div>
          <div v-if="selectedCategoryOverview.recommended" class="workspace-drawer__task">
            <strong>{{ selectedCategoryOverview.recommended.title }}</strong>
            <span>系统建议优先进入该知识点继续学习</span>
            <button class="workspace-drawer__tag" @click="selectKp(selectedCategoryOverview.recommended.id)">跳转查看</button>
          </div>
          <div v-else class="workspace-drawer__empty">当前没有推荐节点</div>
        </div>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.workspace-shell {
  position: relative;
  min-height: calc(100vh - 190px);
  border-radius: 32px;
  background: #082d6e;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(4, 14, 33, 0.42);
}

.workspace-badge {
  position: absolute;
  top: 22px;
  left: 22px;
  z-index: 4;
  padding: 14px 26px;
  border-radius: 999px;
  background: linear-gradient(135deg, #4b8cff, #6f6fff);
  color: #f7f9ff;
  font-size: 16px;
  font-weight: 800;
  box-shadow: 0 18px 38px rgba(69, 106, 255, 0.34);
}

.workspace-sidebar {
  position: absolute;
  left: 22px;
  top: 150px;
  bottom: 90px;
  z-index: 3;
  width: 282px;
  padding: 14px;
  border-radius: 26px;
  background: rgba(10, 37, 92, 0.48);
  border: 1px solid rgba(190, 214, 255, 0.06);
  backdrop-filter: blur(14px);
  display: grid;
  gap: 12px;
  overflow: hidden;
}

.workspace-mode {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 8px;
  border-radius: 20px;
  background: rgba(7, 27, 72, 0.32);
}

.workspace-mode__item,
.workspace-tree__summary,
.workspace-tree__child,
.workspace-drawer__tag {
  border: 0;
  cursor: pointer;
}

.workspace-mode__item {
  height: 42px;
  border-radius: 16px;
  background: transparent;
  color: rgba(232, 240, 255, 0.68);
  font-weight: 700;
}

.workspace-mode__item.active {
  background: linear-gradient(135deg, #4f8fff, #5c69ff);
  color: #ffffff;
}

.workspace-search :deep(.el-input__wrapper) {
  background: rgba(9, 34, 85, 0.38);
  box-shadow: inset 0 0 0 1px rgba(190, 214, 255, 0.06);
}

.workspace-search :deep(.el-input__inner) {
  color: #eef3ff;
}

.workspace-tree {
  display: grid;
  gap: 10px;
  overflow: auto;
  padding-right: 4px;
}

.workspace-tree__group {
  border-radius: 18px;
  background: rgba(232, 240, 255, 0.06);
  overflow: hidden;
}

.workspace-tree__summary {
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  color: #dfe8f7;
  font-weight: 700;
}

.workspace-tree__summary.active {
  background: rgba(123, 169, 255, 0.22);
}

.workspace-tree__summary::-webkit-details-marker {
  display: none;
}

.workspace-tree__children {
  display: grid;
  gap: 6px;
  padding: 0 10px 10px;
}

.workspace-tree__child {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  color: #e7edf8;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  text-align: left;
}

.workspace-tree__child.active {
  background: rgba(160, 193, 255, 0.18);
  box-shadow: inset 0 0 0 1px rgba(111, 140, 255, 0.36);
}

.workspace-tree__child small {
  color: rgba(225, 235, 250, 0.7);
}

.workspace-stage {
  position: absolute;
  inset: 0;
  padding: 28px 118px 84px 330px;
  cursor: grab;
  user-select: none;
}

.workspace-stage__top {
  position: absolute;
  top: 18px;
  left: 344px;
  right: 146px;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.workspace-stage__tabs {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(9, 35, 89, 0.26);
  color: rgba(236, 242, 255, 0.72);
}

.workspace-stage__tabs span {
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.workspace-stage__tabs .active {
  background: rgba(109, 154, 255, 0.28);
  color: #ffffff;
}

.workspace-stage__searchbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(9, 35, 89, 0.26);
  color: rgba(236, 242, 255, 0.8);
}

.workspace-stage__icon {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  border: 0;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  font-size: 18px;
  cursor: pointer;
}

.workspace-stage__course {
  min-width: 160px;
  text-align: center;
  font-weight: 700;
  font-size: 13px;
}

.workspace-canvas {
  width: 100%;
  height: 100%;
  display: block;
  transform-origin: center center;
  transition: transform 0.22s ease;
  will-change: transform;
}

.workspace-stage--dragging {
  cursor: grabbing;
}

.workspace-node,
.workspace-category-node {
  cursor: grab;
}

.workspace-node__index,
.workspace-node__title,
.workspace-category-node__title,
.workspace-category-node__meta {
  fill: #f8fafc;
  font-weight: 800;
  pointer-events: none;
}

.workspace-node__index {
  font-size: 16px;
}

.workspace-node__title {
  font-size: 13px;
}

.workspace-category-node__title {
  font-size: 16px;
}

.workspace-category-node__meta {
  font-size: 12px;
  fill: rgba(240, 244, 255, 0.84);
}

.workspace-view-btn {
  position: absolute;
  top: 70px;
  right: 26px;
  z-index: 4;
  width: 86px;
  height: 86px;
  border-radius: 999px;
  background: radial-gradient(circle at 30% 30%, #7d96ff, #5967ff 68%);
  color: #ffffff;
  font-size: 18px;
  font-weight: 800;
  display: grid;
  place-items: center;
  box-shadow: 0 18px 44px rgba(85, 104, 255, 0.44);
  cursor: pointer;
}

.workspace-drawer {
  position: absolute;
  top: 188px;
  right: 26px;
  bottom: 144px;
  z-index: 3;
  width: 314px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(10, 36, 88, 0.72);
  border: 1px solid rgba(190, 214, 255, 0.06);
  backdrop-filter: blur(14px);
  transform: translateX(118%);
  transition: transform 0.24s ease;
  display: grid;
  align-content: start;
  gap: 18px;
  overflow: auto;
}

.workspace-drawer.open {
  transform: translateX(0);
}

.workspace-drawer__status,
.workspace-drawer__tag {
  width: fit-content;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(92, 105, 255, 0.18);
  color: #d9e1ff;
  font-size: 12px;
  font-weight: 800;
}

.workspace-drawer__title {
  font-size: 26px;
  line-height: 1.15;
  font-weight: 800;
  color: #f8fbff;
}

.workspace-drawer__meta {
  font-size: 14px;
  color: rgba(230, 236, 248, 0.72);
}

.workspace-drawer__grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.workspace-drawer__grid--four {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.workspace-drawer__metric,
.workspace-drawer__block {
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(232, 240, 255, 0.06);
  display: grid;
  gap: 10px;
}

.workspace-drawer__metric span,
.workspace-drawer__label {
  font-size: 13px;
  color: rgba(224, 233, 248, 0.66);
}

.workspace-drawer__metric strong {
  font-size: 24px;
  color: #ffffff;
}

.workspace-drawer__link {
  color: #b4c5ff;
  text-decoration: none;
  line-height: 1.7;
}

.workspace-drawer__empty {
  color: rgba(224, 233, 248, 0.58);
  font-size: 13px;
}

.workspace-drawer__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-start;
}

.workspace-drawer__task {
  display: grid;
  gap: 8px;
  color: #e7effd;
}

.workspace-drawer__task strong {
  font-size: 15px;
}

.workspace-bottom {
  position: absolute;
  left: 34px;
  right: 140px;
  bottom: 26px;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.workspace-legend {
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(8, 32, 82, 0.54);
  color: rgba(235, 240, 248, 0.72);
  display: flex;
  gap: 18px;
  font-size: 13px;
  flex-wrap: wrap;
}

.workspace-zoom {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(8, 32, 82, 0.62);
  color: #f6f9ff;
}

.workspace-zoom button {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  border: 0;
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
  font-size: 22px;
  cursor: pointer;
}

@media (max-width: 1400px) {
  .workspace-drawer {
    width: 280px;
  }
}

@media (max-width: 1180px) {
  .workspace-sidebar,
  .workspace-drawer,
  .workspace-view-btn {
    position: static;
    width: auto;
  }

  .workspace-shell {
    padding: 24px;
    display: grid;
    gap: 18px;
  }

  .workspace-stage {
    position: relative;
    padding: 0;
    min-height: 560px;
  }

  .workspace-stage__top {
    position: static;
    margin-bottom: 14px;
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-bottom {
    position: static;
  }
}
</style>
