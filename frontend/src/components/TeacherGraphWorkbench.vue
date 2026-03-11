<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherNodeContentBinder from "./TeacherNodeContentBinder.vue";

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

type DragNode = {
  type: "kp" | "category";
  id: number | string;
  origin: Point;
};

const props = withDefaults(defineProps<{ subject: string; grade: string; fullscreen?: boolean }>(), {
  fullscreen: false,
});

const loading = ref(false);
const saving = ref(false);
const search = ref("");
const activeChapter = ref("全部");
const selectedType = ref<"kp" | "category">("kp");
const selectedId = ref<number | null>(null);
const selectedCategory = ref<string | null>(null);
const graphEditorOpen = ref(false);
const linkSelectionMode = ref<null | "forward" | "backward" | "related">(null);
const drawerOpen = ref(true);
const detailTab = ref<"overview" | "relations" | "content">("overview");
const sidebarOpen = ref(true);
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
const kps = ref<KP[]>([]);
const edges = ref<Edge[]>([]);

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

const chapterOptions = computed(() => ["全部", ...categoryNodes.value.map((item) => item.key)]);

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
  edges: edges.value.length,
  categories: categoryNodes.value.length,
}));

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
  const groups = new Map<string, KP[]>();
  for (const kp of filteredKps.value) {
    const key = kp.chapter || "未分章";
    const arr = groups.get(key) ?? [];
    arr.push(kp);
    groups.set(key, arr);
  }

  for (const [chapter, items] of groups.entries()) {
    const anchor = categoryPositions.value[chapter] ?? defaultCategoryPositions.value[chapter] ?? { x: 760, y: 180 };
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

const selectedLayout = computed(() => {
  if (!selectedKp.value) return null;
  return kpPoint(selectedKp.value.id);
});

const selectedMenuStyle = computed(() => {
  if (!selectedLayout.value) return {};
  const leftPercent = Math.max(14, Math.min(86, (selectedLayout.value.x / 1500) * 100));
  const topPercent = Math.max(12, Math.min(84, (selectedLayout.value.y / 980) * 100));
  return { left: `${leftPercent}%`, top: `${topPercent}%` };
});

const selectedMenuBelow = computed(() => (selectedLayout.value ? selectedLayout.value.y < 118 : false));

function categoryPoint(key: string) {
  return categoryPositions.value[key] ?? defaultCategoryPositions.value[key] ?? { x: 760, y: 180 };
}

function kpPoint(id: number) {
  return kpPositions.value[id] ?? defaultKpPositions.value[id] ?? { x: 760, y: 500 };
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

function nodeRadius(kp: KP) {
  const base = 44 + Math.round((kp.importance ?? 0.5) * 16);
  return kp.id === selectedKp.value?.id ? base + 8 : base;
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
  selectedType.value = "kp";
  selectedId.value = id;
  selectedCategory.value = null;
  drawerOpen.value = true;
  detailTab.value = "overview";
  syncFormFromSelected();
}

function selectCategory(chapter: string) {
  selectedType.value = "category";
  selectedCategory.value = chapter;
  selectedId.value = null;
  graphEditorOpen.value = false;
  drawerOpen.value = true;
  detailTab.value = "overview";
  activeChapter.value = chapter;
}

function openGraphEditorForSelected() {
  if (!selectedKp.value) return;
  syncFormFromSelected();
  graphEditorOpen.value = true;
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

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const [kpRes, edgeRes] = await Promise.all([
      api.get(`/graph/kps?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
      api.get(`/admin/edges?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&page=1&page_size=500`),
    ]);
    kps.value = kpRes.data ?? [];
    edges.value = edgeRes.data.items ?? [];
    syncCategoryPositions();
    syncKpPositions();
    if (!selectedId.value && kps.value.length) {
      selectedType.value = "kp";
      selectedId.value = kps.value[0].id;
      syncFormFromSelected();
    }
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
      await api.put(`/admin/kps/${form.id}`, {
        code: form.code,
        title: form.title,
        description: form.description,
        chapter: form.chapter,
        ability_tag: form.ability_tag,
        literacy_tag: form.literacy_tag,
        importance: form.importance,
        difficulty: form.difficulty,
      });
      ElMessage.success("知识点已更新");
    } else {
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

async function deleteEdge(edgeId: number) {
  try {
    await api.delete(`/admin/edges/${edgeId}`);
    ElMessage.success("知识边已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除知识边失败");
  }
}

function edgeLabel(edge: Edge) {
  return edge.relation_type === "related" ? "关联" : "前置";
}

watch(
  () => [props.subject, props.grade],
  () => {
    selectedId.value = null;
    selectedCategory.value = null;
    load();
  },
  { immediate: true },
);

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
  <div class="teacher-workbench" :class="{ 'teacher-workbench--fullscreen': props.fullscreen, 'teacher-workbench--sidebar-collapsed': !sidebarOpen }" v-loading="loading">
    <aside class="teacher-sidebar" :class="{ 'teacher-sidebar--collapsed': !sidebarOpen }">
      <div v-if="!sidebarOpen" class="teacher-sidebar__collapsed">
        <button class="teacher-sidebar__collapsed-btn" @click="sidebarOpen = true">展开导航</button>
      </div>
      <template v-else>
      <div class="teacher-sidebar__card">
        <div class="teacher-sidebar__title">图谱导航</div>
        <div class="teacher-sidebar__mode">
          <button class="teacher-sidebar__mode-item active">章节树</button>
          <button class="teacher-sidebar__mode-item" @click="activeChapter = '全部'">全局</button>
        </div>
        <el-input v-model="search" placeholder="检索分类或知识点" clearable class="teacher-sidebar__search" />
      </div>

      <div class="teacher-sidebar__card teacher-sidebar__tree">
        <details
          v-for="item in treeNodes"
          :key="item.key"
          class="teacher-tree__group"
          :open="activeChapter === item.key || activeChapter === '全部'"
        >
          <summary
            class="teacher-tree__summary"
            :class="{ active: activeChapter === item.key && selectedType === 'category' }"
            @click.prevent="selectCategory(item.key)"
          >
            <span>{{ item.title }}</span>
            <strong>{{ item.children.length }}</strong>
          </summary>
          <div class="teacher-tree__children">
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
        </details>
      </div>
      </template>
    </aside>

    <section class="teacher-stage" :class="{ 'teacher-stage--dragging': draggingCanvas }" @mousedown="onStageMouseDown">
      <div class="teacher-stage__top">
        <div class="teacher-stage__legend">
          <span>方形：分类总览</span>
          <span>圆形：知识点</span>
          <span>虚线：分类包含</span>
        </div>
        <div class="teacher-stage__actions">
          <span class="teacher-stage__pill">分类 {{ stageStats.categories }}</span>
          <span class="teacher-stage__pill">知识点 {{ stageStats.points }}</span>
          <span class="teacher-stage__pill">关系 {{ stageStats.edges }}</span>
          <button class="teacher-stage__button teacher-stage__button--ghost" @click="sidebarOpen = !sidebarOpen">
            {{ sidebarOpen ? "收起导航" : "展开导航" }}
          </button>
          <button class="teacher-stage__button" @click="resetCreateForm(activeChapter === '全部' ? '' : activeChapter)">新建知识点</button>
          <button class="teacher-stage__button teacher-stage__button--ghost" @click="drawerOpen = !drawerOpen">
            {{ drawerOpen ? "收起右栏" : "展开右栏" }}
          </button>
          <button class="teacher-stage__button teacher-stage__button--ghost" @click="resetViewport">重置视图</button>
        </div>
      </div>

      <svg
        class="teacher-canvas"
        viewBox="0 0 1500 980"
        preserveAspectRatio="xMidYMid meet"
        :style="{ transform: `translate(${panX}px, ${panY}px) scale(${canvasScale})` }"
      >
        <circle cx="240" cy="170" r="300" fill="rgba(120, 174, 255, 0.10)" />
        <circle cx="1220" cy="760" r="280" fill="rgba(95, 151, 255, 0.10)" />

        <line
          v-for="edge in visibleEdges"
          :key="`${edge.id}-${edge.relation_type}`"
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
          :y1="categoryPoint(kp.chapter || '未分章').y + 28"
          :x2="kpPoint(kp.id).x"
          :y2="kpPoint(kp.id).y - 24"
          stroke="rgba(120, 170, 255, 0.12)"
          stroke-width="1.8"
          stroke-dasharray="7 7"
        />

        <g
          v-for="category in categoryNodes"
          :key="category.key"
          class="teacher-category-node"
          :transform="`translate(${categoryPoint(category.key).x}, ${categoryPoint(category.key).y})`"
          @click="selectCategory(category.key)"
          @mousedown="onNodeMouseDown($event, 'category', category.key)"
        >
          <rect
            x="-84"
            y="-38"
            width="168"
            height="76"
            rx="22"
            :fill="selectedCategory === category.key ? 'rgba(137, 176, 255, 0.32)' : 'rgba(198, 216, 255, 0.18)'"
            :stroke="selectedCategory === category.key ? '#d7e7ff' : 'rgba(215,231,255,0.18)'"
            stroke-width="2.5"
          />
          <text class="teacher-category-node__title" text-anchor="middle" y="-4">{{ category.title }}</text>
          <text class="teacher-category-node__meta" text-anchor="middle" y="20">{{ category.total }} 个知识点</text>
        </g>

        <g
          v-for="kp in filteredKps"
          :key="kp.id"
          class="teacher-node"
          :transform="`translate(${kpPoint(kp.id).x}, ${kpPoint(kp.id).y})`"
          @click="selectKp(kp.id)"
          @mousedown="onNodeMouseDown($event, 'kp', kp.id)"
        >
          <circle :r="nodeRadius(kp) + 12" fill="rgba(111, 160, 255, 0.18)" />
          <circle
            :r="nodeRadius(kp)"
            :fill="kp.id === selectedKp?.id ? '#c9ced7' : '#b7bcc5'"
            :stroke="kp.id === selectedKp?.id ? '#f5f7fb' : 'rgba(255,255,255,0.12)'"
            :stroke-width="kp.id === selectedKp?.id ? 4 : 2"
          />
          <rect x="-44" y="-20" width="88" height="24" rx="12" fill="rgba(8, 31, 79, 0.20)" />
          <text class="teacher-node__code" text-anchor="middle" y="-4">{{ kp.code }}</text>
          <text class="teacher-node__title" text-anchor="middle" y="19">{{ kp.title.slice(0, 10) }}</text>
        </g>
      </svg>

      <div
        v-if="selectedKp && selectedLayout"
        class="teacher-stage__menu"
        :class="{ 'teacher-stage__menu--below': selectedMenuBelow }"
        :style="selectedMenuStyle"
      >
        <button @click="openGraphEditorForSelected">编辑节点</button>
        <button @click="startLinkSelection('forward')">新增后继</button>
        <button @click="startLinkSelection('backward')">新增前置</button>
        <button @click="startLinkSelection('related')">添加关联</button>
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

      <section v-if="graphEditorOpen" class="teacher-editor-float">
        <div class="teacher-editor-float__title">{{ form.id ? '编辑知识点' : '新建知识点' }}</div>
        <el-form label-position="top" size="small">
          <div class="teacher-form-grid">
            <el-form-item label="编码"><el-input v-model="form.code" /></el-form-item>
            <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
          </div>
          <div class="teacher-form-grid">
            <el-form-item label="章节"><el-input v-model="form.chapter" /></el-form-item>
            <el-form-item label="能力标签"><el-input v-model="form.ability_tag" /></el-form-item>
          </div>
          <el-form-item label="素养标签"><el-input v-model="form.literacy_tag" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
          <div class="teacher-form-grid">
            <el-form-item label="重要度"><el-input-number v-model="form.importance" :min="0" :max="1" :step="0.05" /></el-form-item>
            <el-form-item label="难度"><el-input-number v-model="form.difficulty" :min="0" :max="1" :step="0.05" /></el-form-item>
          </div>
        </el-form>
        <div class="teacher-editor-float__actions">
          <el-button type="primary" :loading="saving" @click="saveKp">保存</el-button>
          <el-button @click="graphEditorOpen = false">收起</el-button>
        </div>
      </section>

      <div class="teacher-stage__bottom">
        <div class="teacher-stage__zoom">
          <button @click="zoomOut">-</button>
          <span>{{ Math.round(canvasScale * 100) }}%</span>
          <button @click="zoomIn">+</button>
        </div>
      </div>
    </section>

    <aside class="teacher-drawer" :class="{ open: drawerOpen, 'teacher-drawer--collapsed': !drawerOpen }" v-if="selectedKp || selectedCategoryNode">
      <template v-if="selectedType === 'category' && selectedCategoryNode && categoryOverview">
        <div class="teacher-drawer__status">分类总览</div>
        <div class="teacher-drawer__title">{{ selectedCategoryNode.title }}</div>
        <div class="teacher-drawer__meta">{{ categoryOverview.total }} 个知识点</div>

        <div class="teacher-drawer__grid teacher-drawer__grid--triple">
          <div class="teacher-drawer__metric">
            <span>能力标签</span>
            <strong>{{ categoryOverview.abilityTags.length }}</strong>
          </div>
          <div class="teacher-drawer__metric">
            <span>素养标签</span>
            <strong>{{ categoryOverview.literacyTags.length }}</strong>
          </div>
          <div class="teacher-drawer__metric">
            <span>节点数量</span>
            <strong>{{ categoryOverview.total }}</strong>
          </div>
        </div>

        <div class="teacher-drawer__block">
          <div class="teacher-drawer__label">分类能力标签</div>
          <div class="teacher-drawer__tags" v-if="categoryOverview.abilityTags.length">
            <span v-for="item in categoryOverview.abilityTags" :key="item" class="teacher-drawer__tag teacher-drawer__tag--plain">{{ item }}</span>
          </div>
          <div v-else class="teacher-drawer__empty">暂无能力标签</div>
        </div>

        <div class="teacher-drawer__block">
          <div class="teacher-drawer__label">分类下知识点</div>
          <div class="teacher-drawer__list">
            <button v-for="kp in categoryOverview.items" :key="kp.id" class="teacher-drawer__list-item" @click="selectKp(kp.id)">
              <span>{{ kp.title }}</span>
              <small>{{ kp.code }}</small>
            </button>
          </div>
        </div>

        <div class="teacher-drawer__actions">
          <button class="teacher-drawer__primary" @click="resetCreateForm(selectedCategoryNode.key)">在该分类下新增知识点</button>
        </div>
      </template>

      <template v-else-if="selectedKp">
        <div class="teacher-drawer__tabs">
          <button :class="{ active: detailTab === 'overview' }" @click="detailTab = 'overview'">概览</button>
          <button :class="{ active: detailTab === 'relations' }" @click="detailTab = 'relations'">关系</button>
          <button :class="{ active: detailTab === 'content' }" @click="detailTab = 'content'">内容绑定</button>
        </div>
        <div class="teacher-drawer__status">知识点编辑</div>
        <div class="teacher-drawer__title">{{ selectedKp.title }}</div>
        <div class="teacher-drawer__meta">{{ selectedKp.code }} · {{ selectedKp.chapter || '未分章' }}</div>

        <div class="teacher-drawer__grid">
          <div class="teacher-drawer__metric">
            <span>重要度</span>
            <strong>{{ Math.round((selectedKp.importance ?? 0.5) * 100) }}</strong>
          </div>
          <div class="teacher-drawer__metric">
            <span>难度</span>
            <strong>{{ Math.round((selectedKp.difficulty ?? 0.5) * 100) }}</strong>
          </div>
        </div>

        <div v-if="detailTab === 'overview'">
          <div class="teacher-drawer__block">
            <div class="teacher-drawer__label">图内快捷操作</div>
            <div class="teacher-drawer__actions teacher-drawer__actions--compact">
              <button class="teacher-drawer__secondary" @click="openGraphEditorForSelected">编辑节点</button>
              <button class="teacher-drawer__secondary" @click="startLinkSelection('forward')">新增后继</button>
              <button class="teacher-drawer__secondary" @click="startLinkSelection('backward')">新增前置</button>
            </div>
          </div>

          <div class="teacher-drawer__block">
            <div class="teacher-drawer__label">关系速览</div>
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
          </div>
        </div>

        <div v-else-if="detailTab === 'relations'">
          <div class="teacher-drawer__block">
            <div class="teacher-drawer__label">当前关系</div>
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
                <button v-for="kp in selectedConnections.related" :key="kp.id" class="teacher-drawer__tag teacher-drawer__tag--plain" @click="selectKp(kp.id)">{{ kp.title }}</button>
              </div>
            </div>
          </div>

          <div class="teacher-drawer__block">
            <div class="teacher-drawer__label">关系删除</div>
            <div class="teacher-drawer__list" v-if="edges.filter((edge) => edge.prereq_id === selectedKp?.id || edge.next_id === selectedKp?.id).length">
              <div v-for="edge in edges.filter((item) => item.prereq_id === selectedKp?.id || item.next_id === selectedKp?.id)" :key="edge.id" class="teacher-drawer__relation-item">
                <span>{{ edgeLabel(edge) }}</span>
                <button @click="deleteEdge(edge.id)">删除</button>
              </div>
            </div>
            <div v-else class="teacher-drawer__empty">暂无关系可删除</div>
          </div>
        </div>

        <div v-else class="teacher-drawer__binder">
          <TeacherNodeContentBinder :kp-id="selectedKp.id" :kp-code="selectedKp.code" :kp-title="selectedKp.title" />
        </div>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.teacher-workbench {
  min-height: calc(100vh - 186px);
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr) 308px;
  gap: 14px;
}

.teacher-workbench--sidebar-collapsed {
  grid-template-columns: 88px minmax(0, 1fr) 308px;
}

.teacher-workbench--fullscreen {
  min-height: calc(100vh - 186px);
  grid-template-columns: minmax(0, 1fr) 308px;
  position: relative;
}

.teacher-workbench--fullscreen.teacher-workbench--sidebar-collapsed {
  grid-template-columns: minmax(0, 1fr) 308px;
}

.teacher-sidebar,
.teacher-drawer {
  display: grid;
  gap: 16px;
  align-content: start;
}

.teacher-sidebar--collapsed {
  display: block;
}

.teacher-workbench--fullscreen .teacher-sidebar {
  position: absolute;
  left: 18px;
  top: 94px;
  z-index: 8;
  width: 216px;
}

.teacher-workbench--fullscreen .teacher-sidebar--collapsed {
  width: 84px;
}

.teacher-sidebar__collapsed {
  display: grid;
  align-content: start;
}

.teacher-sidebar__collapsed-btn {
  border: 0;
  padding: 14px 10px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(10, 40, 92, 0.88) 0%, rgba(9, 34, 80, 0.82) 100%);
  color: #eef5ff;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 20px 45px rgba(6, 17, 48, 0.26);
}

.teacher-sidebar__card,
.teacher-drawer {
  background: linear-gradient(180deg, rgba(10, 40, 92, 0.88) 0%, rgba(9, 34, 80, 0.82) 100%);
  border: 1px solid rgba(148, 186, 255, 0.14);
  box-shadow: 0 20px 45px rgba(6, 17, 48, 0.26);
  backdrop-filter: blur(16px);
}

.teacher-sidebar__card {
  border-radius: 28px;
  padding: 18px;
}

.teacher-sidebar__title {
  margin-bottom: 12px;
  color: #f3f7ff;
  font-size: 18px;
  font-weight: 800;
}

.teacher-sidebar__mode {
  display: inline-flex;
  gap: 8px;
  padding: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  margin-bottom: 14px;
}

.teacher-sidebar__mode-item {
  border: 0;
  padding: 10px 18px;
  border-radius: 999px;
  background: transparent;
  color: #b5c4de;
  font-weight: 700;
  cursor: pointer;
}

.teacher-sidebar__mode-item.active {
  background: linear-gradient(135deg, #4f8fff 0%, #6c7cff 100%);
  color: #fff;
}

.teacher-sidebar__search :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: none;
}

.teacher-tree__group + .teacher-tree__group {
  margin-top: 10px;
}

.teacher-tree__summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.05);
  color: #dce7fb;
  cursor: pointer;
  list-style: none;
}

.teacher-tree__summary::-webkit-details-marker { display: none; }

.teacher-tree__summary.active {
  background: rgba(91, 139, 255, 0.24);
  border: 1px solid rgba(150, 191, 255, 0.26);
}

.teacher-tree__children {
  display: grid;
  gap: 8px;
  margin-top: 10px;
  padding-left: 10px;
}

.teacher-tree__child {
  display: grid;
  justify-items: start;
  gap: 4px;
  padding: 12px 14px;
  border: 0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  color: #d6e2f8;
  text-align: left;
  cursor: pointer;
}

.teacher-tree__child small {
  color: #8fa2c3;
}

.teacher-tree__child.active {
  background: rgba(92, 139, 255, 0.22);
  box-shadow: inset 0 0 0 1px rgba(150, 191, 255, 0.22);
}

.teacher-stage {
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 16px;
  min-height: calc(100vh - 194px);
  border-radius: 34px;
  padding: 18px;
  background: #082d6e;
  box-shadow: 0 24px 60px rgba(6, 17, 48, 0.28);
  overflow: hidden;
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

.teacher-stage__legend,
.teacher-stage__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.teacher-stage__legend {
  color: #d5e3fc;
  font-size: 13px;
}

.teacher-stage__pill,
.teacher-stage__button {
  padding: 10px 16px;
  border-radius: 999px;
  border: 0;
  background: rgba(255, 255, 255, 0.08);
  color: #d9e6fc;
  font-weight: 700;
}

.teacher-stage__button {
  cursor: pointer;
}

.teacher-stage__button--ghost {
  background: rgba(255, 255, 255, 0.05);
}

.teacher-canvas {
  width: 100%;
  height: 100%;
  display: block;
  background: transparent;
  transform-origin: center center;
  transition: transform 0.18s ease;
  cursor: grab;
  border-radius: 30px;
}

.teacher-category-node,
.teacher-node {
  cursor: pointer;
}

.teacher-category-node__title,
.teacher-category-node__meta,
.teacher-node__code,
.teacher-node__title {
  fill: #eef4ff;
  font-weight: 700;
  pointer-events: none;
}

.teacher-category-node__title,
.teacher-node__title {
  font-size: 20px;
}

.teacher-category-node__meta,
.teacher-node__code {
  font-size: 15px;
  fill: rgba(235, 243, 255, 0.84);
}

.teacher-stage__menu {
  position: absolute;
  z-index: 5;
  transform: translate(-50%, calc(-100% - 18px));
  display: flex;
  gap: 8px;
  padding: 10px;
  border-radius: 18px;
  background: rgba(9, 34, 80, 0.92);
  border: 1px solid rgba(145, 182, 255, 0.16);
  box-shadow: 0 18px 36px rgba(6, 18, 48, 0.28);
}

.teacher-stage__menu--below {
  transform: translate(-50%, 18px);
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
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  color: #f2f7ff;
  font-weight: 700;
}

.teacher-stage__menu .danger {
  background: rgba(255, 114, 114, 0.18);
  color: #ffdede;
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
  padding: 12px 18px;
  border-radius: 999px;
  background: rgba(9, 34, 80, 0.94);
  color: #eef5ff;
}

.teacher-stage__hint button {
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #eef5ff;
}

.teacher-editor-float {
  position: absolute;
  top: 94px;
  right: 28px;
  z-index: 6;
  width: 360px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(9, 34, 80, 0.94);
  border: 1px solid rgba(145, 182, 255, 0.18);
  box-shadow: 0 18px 36px rgba(6, 18, 48, 0.28);
}

.teacher-editor-float__title {
  margin-bottom: 12px;
  color: #f4f8ff;
  font-size: 18px;
  font-weight: 800;
}

.teacher-editor-float__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
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
  gap: 10px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(9, 34, 80, 0.88);
  color: #fff;
}

.teacher-stage__zoom button {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 20px;
}

.teacher-drawer {
  border-radius: 30px;
  padding: 18px;
  overflow: auto;
  color: #eff5ff;
}

.teacher-drawer--collapsed {
  width: 84px;
  overflow: hidden;
  padding: 18px 10px;
}

.teacher-drawer--collapsed > * {
  display: none;
}

.teacher-drawer--collapsed::after {
  content: "展开";
  display: block;
  color: #eef5ff;
  text-align: center;
  font-weight: 800;
}

.teacher-drawer__tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.teacher-drawer__tabs button {
  border: 0;
  padding: 10px 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #d7e5ff;
  font-weight: 700;
  cursor: pointer;
}

.teacher-drawer__tabs button.active {
  background: linear-gradient(135deg, #4f8fff 0%, #6c7cff 100%);
  color: #fff;
}

.teacher-drawer__status {
  display: inline-flex;
  width: fit-content;
  padding: 12px 20px;
  border-radius: 999px;
  background: rgba(95, 122, 255, 0.24);
  color: #f4f8ff;
  font-weight: 800;
}

.teacher-drawer__title {
  margin-top: 22px;
  font-size: 34px;
  line-height: 1.06;
  font-weight: 900;
}

.teacher-drawer__meta {
  margin-top: 12px;
  color: rgba(231, 239, 255, 0.78);
  font-size: 17px;
}

.teacher-drawer__grid {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.teacher-drawer__grid--triple {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.teacher-drawer__metric,
.teacher-drawer__block,
.teacher-drawer__binder :deep(.content-binder),
.teacher-drawer__list-item,
.teacher-drawer__relation-item {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.06);
}

.teacher-drawer__metric {
  padding: 18px;
  display: grid;
  gap: 10px;
}

.teacher-drawer__metric span,
.teacher-drawer__label,
.teacher-drawer__relation-group strong {
  color: rgba(233, 241, 255, 0.76);
}

.teacher-drawer__metric strong {
  font-size: 28px;
}

.teacher-drawer__block {
  margin-top: 16px;
  padding: 18px;
}

.teacher-drawer__empty {
  margin-top: 10px;
  color: rgba(205, 216, 236, 0.68);
}

.teacher-drawer__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.teacher-drawer__tag {
  border: 0;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(95, 122, 255, 0.24);
  color: #eef5ff;
}

.teacher-drawer__tag--plain {
  background: rgba(255, 255, 255, 0.08);
}

.teacher-drawer__list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.teacher-drawer__list-item,
.teacher-drawer__relation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  color: #eef5ff;
}

.teacher-drawer__list-item {
  border: 0;
  cursor: pointer;
  text-align: left;
}

.teacher-drawer__list-item small {
  color: rgba(201, 213, 232, 0.72);
}

.teacher-drawer__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.teacher-drawer__actions--compact {
  margin-top: 10px;
}

.teacher-drawer__primary,
.teacher-drawer__secondary {
  padding: 12px 18px;
  border-radius: 14px;
  font-weight: 800;
}

.teacher-drawer__primary {
  background: linear-gradient(135deg, #4f8fff 0%, #6c7cff 100%);
  color: #fff;
}

.teacher-drawer__secondary {
  background: rgba(255, 255, 255, 0.08);
  color: #eef5ff;
}

.teacher-drawer__relation-group + .teacher-drawer__relation-group {
  margin-top: 14px;
}

.teacher-drawer__relation-item button {
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 114, 114, 0.16);
  color: #ffe6e6;
}

.teacher-drawer__binder {
  margin-top: 18px;
}

.teacher-drawer__binder :deep(.content-binder) {
  border: 0;
  background: transparent;
}

.teacher-drawer__binder :deep(.content-binder__header) {
  display: none;
}

.teacher-drawer__binder :deep(.content-binder__section) {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 22px;
  border: 0;
}

@media (max-width: 1480px) {
  .teacher-workbench {
    grid-template-columns: 232px minmax(0, 1fr) 290px;
  }

  .teacher-workbench--fullscreen,
  .teacher-workbench--fullscreen.teacher-workbench--sidebar-collapsed {
    grid-template-columns: minmax(0, 1fr) 290px;
  }
}

@media (max-width: 1260px) {
  .teacher-workbench {
    grid-template-columns: 1fr;
  }

  .teacher-sidebar,
  .teacher-drawer {
    order: 2;
  }

  .teacher-stage {
    order: 1;
    min-height: 760px;
  }
}
</style>
