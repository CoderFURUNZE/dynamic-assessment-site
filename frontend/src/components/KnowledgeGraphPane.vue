<script setup lang="ts">
import { computed, ref, watch } from "vue";
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
const selectedId = ref<number | null>(null);
const nodeDetail = ref<NodeDetail | null>(null);

const overlayMap = computed(() => new Map(overlay.value.map((item) => [item.kp_id, item])));

const chapters = computed(() => {
  const names = Array.from(new Set(kps.value.map((kp) => kp.chapter || "未分章")));
  return ["全部", ...names];
});

const filteredKps = computed(() => {
  const kw = search.value.trim().toLowerCase();
  return kps.value.filter((kp) => {
    const chapterOk = activeChapter.value === "全部" || (kp.chapter || "未分章") === activeChapter.value;
    if (!chapterOk) return false;
    if (!kw) return true;
    return `${kp.code} ${kp.title} ${kp.description}`.toLowerCase().includes(kw);
  });
});

const chapterBuckets = computed(() => {
  const groups = new Map<string, GraphKp[]>();
  for (const kp of filteredKps.value) {
    const key = kp.chapter || "未分章";
    const arr = groups.get(key) ?? [];
    arr.push(kp);
    groups.set(key, arr);
  }
  return Array.from(groups.entries()).map(([chapter, items]) => ({ chapter, items }));
});

const chapterSummary = computed(() => {
  const bucket = new Map<string, number>();
  for (const kp of kps.value) {
    const key = kp.chapter || "未分章";
    bucket.set(key, (bucket.get(key) ?? 0) + 1);
  }
  return Array.from(bucket.entries()).map(([chapter, total]) => ({ chapter, total }));
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

const positionMap = computed(() => {
  const groups = chapterBuckets.value;
  const map = new Map<number, { x: number; y: number }>();
  const centerX = 940;
  const centerY = 430;
  const laneGap = 250;

  groups.forEach((bucket, chapterIndex) => {
    const offsetX = groups.length <= 1 ? 0 : (chapterIndex - (groups.length - 1) / 2) * laneGap;
    const radiusX = 170 + Math.min(bucket.items.length, 6) * 16;
    const radiusY = 150 + chapterIndex * 18;

    bucket.items.forEach((kp, itemIndex) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * itemIndex) / Math.max(bucket.items.length, 1) + chapterIndex * 0.3;
      const wobble = itemIndex % 2 === 0 ? 1 : 0.92;
      const x = centerX + offsetX + Math.cos(angle) * radiusX * wobble;
      const y = centerY + Math.sin(angle) * radiusY + Math.sin(itemIndex + chapterIndex) * 18;
      map.set(kp.id, { x, y });
    });
  });

  return map;
});

const chapterAnchors = computed(() =>
  chapterBuckets.value.map((bucket, chapterIndex) => {
    const points = bucket.items.map((item) => positionMap.value.get(item.id)).filter(Boolean) as Array<{ x: number; y: number }>;
    const avgX = points.length ? points.reduce((sum, point) => sum + point.x, 0) / points.length : 940;
    const minY = points.length ? Math.min(...points.map((point) => point.y)) : 150;
    return {
      chapter: bucket.chapter,
      x: avgX,
      y: Math.max(92, minY - 82 - chapterIndex * 6),
    };
  })
);

const visibleEdges = computed(() => {
  const ids = new Set(filteredKps.value.map((kp) => kp.id));
  return edges.value.filter((edge) => ids.has(edge.prereq_id) && ids.has(edge.next_id));
});

const selectedKp = computed(() => {
  const targetId = selectedId.value ?? props.currentKpId ?? filteredKps.value[0]?.id ?? null;
  return filteredKps.value.find((kp) => kp.id === targetId) ?? kps.value.find((kp) => kp.id === targetId) ?? null;
});

const selectedOverlay = computed(() => (selectedKp.value ? overlayMap.value.get(selectedKp.value.id) ?? null : null));
const activeOverlay = computed(() => nodeDetail.value?.overlay ?? selectedOverlay.value ?? null);

const selectedRelations = computed(() => {
  if (!selectedKp.value) return { prerequisites: [], downstream: [], related: [] as GraphKp[] };
  const currentId = selectedKp.value.id;
  const prereqIds = edges.value.filter((edge) => edge.next_id === currentId && edge.relation_type !== "related").map((edge) => edge.prereq_id);
  const downstreamIds = edges.value.filter((edge) => edge.prereq_id === currentId && edge.relation_type !== "related").map((edge) => edge.next_id);
  const relatedIds = edges.value
    .filter((edge) => edge.relation_type === "related" && (edge.prereq_id === currentId || edge.next_id === currentId))
    .map((edge) => (edge.prereq_id === currentId ? edge.next_id : edge.prereq_id));

  return {
    prerequisites: kps.value.filter((kp) => prereqIds.includes(kp.id)),
    downstream: kps.value.filter((kp) => downstreamIds.includes(kp.id)),
    related: kps.value.filter((kp) => relatedIds.includes(kp.id)),
  };
});

const detailRelations = computed(() => {
  if (nodeDetail.value) {
    return {
      prerequisites: nodeDetail.value.prerequisites,
      downstream: nodeDetail.value.downstream,
      related: nodeDetail.value.related,
    };
  }
  return selectedRelations.value;
});

function nodeColor(status?: string) {
  if (status === "mastered") return "#2dcc84";
  if (status === "learning") return "#4c92ff";
  if (status === "risk") return "#ff9553";
  return "#90a7c0";
}

function nodeLabel(status?: string) {
  if (status === "mastered") return "已掌握";
  if (status === "learning") return "学习中";
  if (status === "risk") return "风险";
  return "未开始";
}

function nodeRadius(kp: GraphKp) {
  const base = 36 + Math.round((kp.importance ?? 0.5) * 16);
  let extra = 0;
  if (kp.id === props.recommendedKpId) extra += 6;
  if (kp.id === selectedKp.value?.id) extra += 4;
  return base + extra;
}

function metricPercent(value?: number | null) {
  return Math.round((value ?? 0) * 100);
}

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    try {
      const res = await api.get(`/graph/map?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
      kps.value = res.data.base?.kps ?? [];
      edges.value = res.data.base?.edges ?? [];
      overlay.value = res.data.overlay ?? [];
    } catch {
      const [kpRes, edgeRes] = await Promise.all([
        api.get(`/graph/kps?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
        api.get(`/graph/edges?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`),
      ]);
      kps.value = kpRes.data ?? [];
      edges.value = edgeRes.data ?? [];
      overlay.value = kps.value.map((kp) => ({
        kp_id: kp.id,
        mastery: 0,
        status: "not_started",
        recommended: false,
        blocked_reason: null,
      }));
      ElMessage.warning("已切换到基础图谱模式，覆盖层数据暂不可用");
    }
    const selectedExists = selectedId.value ? kps.value.some((item) => item.id === selectedId.value) : false;
    if (!selectedExists) {
      selectedId.value = props.currentKpId && kps.value.some((item) => item.id === props.currentKpId)
        ? props.currentKpId
        : (kps.value[0]?.id ?? null);
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
  selectedId.value = id;
  emit("select-kp", id);
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
    if (value) selectedId.value = value;
  }
);

watch(selectedId, (value) => {
  loadNodeDetail(value ?? null);
});
</script>

<template>
  <el-card class="panel-card graph-shell" shadow="never" v-loading="loading">
    <template #header>
      <div class="graph-topbar">
        <div>
          <div class="graph-kicker">Course Map</div>
          <div class="graph-title">知识图谱学习地图</div>
          <div class="graph-subtitle">把课程结构、掌握状态和推荐路径放到同一张学习地图里。</div>
        </div>
        <div class="graph-toolbar">
          <div class="graph-stat-card">
            <span>知识点</span>
            <strong>{{ filteredKps.length }}</strong>
          </div>
          <div class="graph-stat-card graph-stat-card--accent">
            <span>已掌握</span>
            <strong>{{ stageStats.mastered }}</strong>
          </div>
          <el-button size="small" @click="load" :loading="loading">刷新图谱</el-button>
        </div>
      </div>
    </template>

    <div class="graph-layout">
      <aside class="graph-sidebar">
        <div class="float-section">
          <div class="float-title">快速定位</div>
          <el-input v-model="search" placeholder="搜索知识点 / 章节" clearable />
        </div>

        <div class="float-section">
          <div class="float-title">章节过滤</div>
          <div class="chapter-cloud">
            <button
              v-for="chapter in chapters"
              :key="chapter"
              class="chapter-pill"
              :class="{ active: chapter === activeChapter }"
              @click="activeChapter = chapter"
            >
              {{ chapter }}
            </button>
          </div>
        </div>

        <div class="float-section">
          <div class="float-title">章节概览</div>
          <div class="chapter-summary">
            <button
              v-for="item in chapterSummary"
              :key="item.chapter"
              class="chapter-summary-item"
              :class="{ active: activeChapter === item.chapter }"
              @click="activeChapter = item.chapter"
            >
              <span>{{ item.chapter }}</span>
              <strong>{{ item.total }}</strong>
            </button>
          </div>
        </div>

        <div class="float-section float-section--list">
          <div class="float-title">知识点列表</div>
          <div v-if="filteredKps.length === 0" class="empty-copy">当前筛选下没有知识点。</div>
          <div v-else class="kp-list">
            <button
              v-for="kp in filteredKps"
              :key="kp.id"
              class="kp-list-item"
              :class="{ active: kp.id === selectedKp?.id, recommended: kp.id === props.recommendedKpId }"
              @click="selectKp(kp.id)"
            >
              <div class="kp-list-item__head">
                <span class="kp-list-code">{{ kp.code }}</span>
                <span
                  class="kp-list-status"
                  :style="{ background: `${nodeColor(overlayMap.get(kp.id)?.status)}22`, color: nodeColor(overlayMap.get(kp.id)?.status) }"
                >
                  {{ nodeLabel(overlayMap.get(kp.id)?.status) }}
                </span>
              </div>
              <span class="kp-list-title">{{ kp.title }}</span>
            </button>
          </div>
        </div>
      </aside>

      <section class="graph-stage">
        <div class="graph-stage__hud">
          <div class="graph-stage__hud-copy">
            <div class="graph-stage__hud-label">图谱状态</div>
            <div class="graph-stage__hud-title">{{ activeChapter === "全部" ? "当前课程全量知识图谱" : `${activeChapter} · 知识图谱` }}</div>
          </div>
          <div class="graph-stage__hud-panel">
            <div class="stage-legend">
              <span class="legend-item"><i style="background:#2dcc84"></i>已掌握</span>
              <span class="legend-item"><i style="background:#4c92ff"></i>学习中</span>
              <span class="legend-item"><i style="background:#ff9553"></i>风险</span>
              <span class="legend-item"><i style="background:#90a7c0"></i>未开始</span>
            </div>
            <div class="stage-pills">
              <span class="stage-pill stage-pill--mastered">掌握 {{ stageStats.mastered }}</span>
              <span class="stage-pill stage-pill--learning">进行中 {{ stageStats.learning }}</span>
              <span class="stage-pill stage-pill--risk">风险 {{ stageStats.risk }}</span>
            </div>
          </div>
        </div>

        <div class="graph-stage__canvas-wrap">
          <div class="stage-legend">
          </div>
          <svg class="graph-canvas" viewBox="0 0 1500 860" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="studentGraphBg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#07111e" />
                <stop offset="42%" stop-color="#12345a" />
                <stop offset="100%" stop-color="#0a2139" />
              </linearGradient>
              <radialGradient id="studentGraphGlowA" cx="50%" cy="42%" r="70%">
                <stop offset="0%" stop-color="rgba(93,171,255,0.18)" />
                <stop offset="100%" stop-color="rgba(5,12,24,0)" />
              </radialGradient>
              <radialGradient id="studentGraphGlowB" cx="50%" cy="42%" r="70%">
                <stop offset="0%" stop-color="rgba(62,119,195,0.14)" />
                <stop offset="100%" stop-color="rgba(5,12,24,0)" />
              </radialGradient>
              <filter id="graphSoftGlow">
                <feGaussianBlur stdDeviation="12" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <marker id="graphArrow" markerWidth="9" markerHeight="9" refX="6.5" refY="4.5" orient="auto">
                <path d="M0,0 L9,4.5 L0,9 z" fill="rgba(225,240,255,0.45)" />
              </marker>
              <pattern id="graphDots" width="36" height="36" patternUnits="userSpaceOnUse">
                <circle cx="2" cy="2" r="1.2" fill="rgba(255,255,255,0.06)" />
              </pattern>
            </defs>

            <rect x="0" y="0" width="1500" height="860" rx="42" fill="url(#studentGraphBg)" />
            <rect x="22" y="22" width="1456" height="816" rx="34" fill="url(#graphDots)" stroke="rgba(255,255,255,0.06)" />
            <circle class="bg-orb bg-orb--a" cx="260" cy="130" r="280" fill="url(#studentGraphGlowA)" />
            <circle class="bg-orb bg-orb--b" cx="1160" cy="620" r="260" fill="url(#studentGraphGlowB)" />

            <g v-for="(anchor, anchorIndex) in chapterAnchors" :key="anchor.chapter" :transform="`translate(${anchor.x}, ${anchor.y})`" :style="{ '--anchor-index': anchorIndex }">
              <circle class="chapter-anchor-dot" r="7" />
              <text class="chapter-anchor__text" x="14" y="4">{{ anchor.chapter }}</text>
            </g>

            <line
              v-for="(edge, edgeIndex) in visibleEdges"
              :key="`${edge.prereq_id}-${edge.next_id}-${edge.relation_type}`"
              class="graph-edge"
              :class="{ 'graph-edge--related': edge.relation_type === 'related' }"
              :style="{ '--edge-index': edgeIndex }"
              :x1="positionMap.get(edge.prereq_id)?.x ?? 0"
              :y1="positionMap.get(edge.prereq_id)?.y ?? 0"
              :x2="positionMap.get(edge.next_id)?.x ?? 0"
              :y2="positionMap.get(edge.next_id)?.y ?? 0"
              :stroke="edge.relation_type === 'related' ? 'rgba(116,198,255,0.42)' : 'rgba(255,255,255,0.18)'"
              :stroke-dasharray="edge.relation_type === 'related' ? '8 9' : '0'"
              :marker-end="edge.relation_type === 'related' ? '' : 'url(#graphArrow)'"
              stroke-width="2.6"
            />

            <g
              v-for="(kp, index) in filteredKps"
              :key="kp.id"
              class="graph-node"
              :transform="`translate(${positionMap.get(kp.id)?.x ?? 0}, ${positionMap.get(kp.id)?.y ?? 0})`"
              @click="selectKp(kp.id)"
            >
              <g class="graph-node__body" :style="{ '--node-index': index }">
                <circle
                  v-if="kp.id === props.recommendedKpId"
                  class="node-ring"
                  :r="nodeRadius(kp) + 18"
                  fill="none"
                  stroke="rgba(255,220,108,0.95)"
                  stroke-dasharray="12 9"
                  stroke-width="3"
                />
                <circle
                  class="node-shadow"
                  :r="nodeRadius(kp) + (kp.id === selectedKp?.id ? 20 : 12)"
                  :fill="`${nodeColor(overlayMap.get(kp.id)?.status)}18`"
                  filter="url(#graphSoftGlow)"
                />
                <circle
                  class="node-core"
                  :r="nodeRadius(kp)"
                  :fill="nodeColor(overlayMap.get(kp.id)?.status)"
                  :stroke="kp.id === selectedKp?.id ? '#ffffff' : 'rgba(255,255,255,0.22)'"
                  :stroke-width="kp.id === selectedKp?.id ? 4 : 2.2"
                  :opacity="0.96"
                />
                <rect x="-42" y="-18" width="84" height="22" rx="11" fill="rgba(6,13,24,0.24)" />
                <text class="node-code" text-anchor="middle" y="-4">{{ kp.code }}</text>
                <text class="node-title" text-anchor="middle" y="20">{{ kp.title.slice(0, 9) }}</text>
                <circle v-if="overlayMap.get(kp.id)?.blocked_reason" cy="-36" r="5" fill="#ffbb6b" stroke="#ffffff" stroke-width="2" />
              </g>
            </g>
          </svg>
        </div>
      </section>

      <aside class="graph-detail" v-if="selectedKp">
        <section class="detail-hero">
          <div class="detail-status" :style="{ background: `${nodeColor(activeOverlay?.status)}20`, color: nodeColor(activeOverlay?.status) }">
            {{ nodeLabel(activeOverlay?.status) }}
          </div>
          <div class="detail-code">{{ selectedKp.code }}</div>
          <div class="detail-title">{{ selectedKp.title }}</div>
          <div class="detail-text">{{ selectedKp.description || "暂无知识点描述" }}</div>
          <div class="detail-tags" v-if="nodeDetail?.kp?.ability_tag || nodeDetail?.kp?.literacy_tag">
            <span v-if="nodeDetail?.kp?.ability_tag" class="detail-tag">能力：{{ nodeDetail.kp.ability_tag }}</span>
            <span v-if="nodeDetail?.kp?.literacy_tag" class="detail-tag detail-tag--soft">素养：{{ nodeDetail.kp.literacy_tag }}</span>
          </div>
        </section>

        <section class="detail-metrics">
          <div class="detail-metric">
            <span>掌握度</span>
            <strong>{{ metricPercent(activeOverlay?.mastery) }}%</strong>
          </div>
          <div class="detail-metric">
            <span>章节</span>
            <strong>{{ selectedKp.chapter || "未分章" }}</strong>
          </div>
          <div class="detail-metric">
            <span>重要度</span>
            <strong>{{ metricPercent(selectedKp.importance) }}</strong>
          </div>
          <div class="detail-metric">
            <span>难度</span>
            <strong>{{ metricPercent(selectedKp.difficulty) }}</strong>
          </div>
        </section>

        <el-alert
          v-if="activeOverlay?.blocked_reason"
          type="warning"
          :title="activeOverlay.blocked_reason"
          :closable="false"
          show-icon
        />
        <el-alert
          v-else-if="selectedKp.id === props.recommendedKpId"
          type="success"
          title="这是系统当前优先推荐学习的知识点。"
          :closable="false"
          show-icon
        />

        <section class="relation-card">
          <div class="relation-title">学习关系</div>
          <div class="relation-group">
            <div class="relation-group__label">前置知识点</div>
            <div v-if="detailRelations.prerequisites.length === 0" class="empty-copy">无前置要求</div>
            <div v-else class="relation-tags">
              <button v-for="kp in detailRelations.prerequisites" :key="kp.id" class="relation-tag" @click="selectKp(kp.id)">
                {{ kp.code }} {{ kp.title }}
              </button>
            </div>
          </div>
          <div class="relation-group">
            <div class="relation-group__label">后续知识点</div>
            <div v-if="detailRelations.downstream.length === 0" class="empty-copy">暂无后续节点</div>
            <div v-else class="relation-tags">
              <button v-for="kp in detailRelations.downstream" :key="kp.id" class="relation-tag" @click="selectKp(kp.id)">
                {{ kp.code }} {{ kp.title }}
              </button>
            </div>
          </div>
          <div class="relation-group">
            <div class="relation-group__label">关联拓展</div>
            <div v-if="detailRelations.related.length === 0" class="empty-copy">暂无关联拓展</div>
            <div v-else class="relation-tags relation-tags--soft">
              <button v-for="kp in detailRelations.related" :key="kp.id" class="relation-tag relation-tag--soft" @click="selectKp(kp.id)">
                {{ kp.code }} {{ kp.title }}
              </button>
            </div>
          </div>
        </section>

        <section class="relation-card">
          <div class="relation-title">节点内容</div>
          <div class="content-group">
            <div class="relation-group__label">学习资源</div>
            <div v-if="(nodeDetail?.resource_list?.length ?? 0) === 0" class="empty-copy">暂无资源</div>
            <div v-else class="content-list">
              <a
                v-for="item in nodeDetail?.resource_list ?? []"
                :key="`resource-${item.id}`"
                class="content-item"
                :href="item.url"
                target="_blank"
                rel="noreferrer"
              >
                <span class="content-item__title">{{ item.title }}</span>
                <span class="content-item__meta">{{ item.type }}</span>
              </a>
            </div>
          </div>

          <div class="content-group">
            <div class="relation-group__label">学习任务</div>
            <div v-if="(nodeDetail?.task_list?.length ?? 0) === 0" class="empty-copy">暂无任务</div>
            <div v-else class="content-list">
              <div v-for="item in nodeDetail?.task_list ?? []" :key="`task-${item.id}`" class="content-item content-item--plain">
                <span class="content-item__title">{{ item.title }}</span>
                <span class="content-item__desc">{{ item.description || "暂无说明" }}</span>
                <a v-if="item.link_url" :href="item.link_url" target="_blank" rel="noreferrer">{{ item.link_url }}</a>
              </div>
            </div>
          </div>

          <div class="content-group">
            <div class="relation-group__label">练习题预览</div>
            <div v-if="(nodeDetail?.practice_list?.length ?? 0) === 0" class="empty-copy">暂无练习题</div>
            <div v-else class="content-list">
              <div v-for="item in nodeDetail?.practice_list ?? []" :key="`practice-${item.id}`" class="content-item content-item--plain">
                <span class="content-item__title">{{ item.prompt }}</span>
                <span class="content-item__meta">{{ item.type }} · 难度 {{ Math.round((item.difficulty ?? 0) * 100) }}</span>
              </div>
            </div>
          </div>

          <div class="content-group">
            <div class="relation-group__label">小测 / 试卷</div>
            <div v-if="(nodeDetail?.quiz_or_exam_list?.length ?? 0) === 0" class="empty-copy">暂无小测或试卷</div>
            <div v-else class="content-list">
              <div v-for="item in nodeDetail?.quiz_or_exam_list ?? []" :key="`quiz-${item.kind}-${item.id}`" class="content-item content-item--plain">
                <span class="content-item__title">{{ item.title }}</span>
                <span class="content-item__meta" v-if="item.kind === 'quiz'">
                  小测 · {{ item.item_count }} 题 · 通过阈值 {{ Math.round((item.pass_accuracy ?? 0) * 100) }}%
                </span>
                <span class="content-item__meta" v-else>试卷/考试</span>
                <span v-if="item.description" class="content-item__desc">{{ item.description }}</span>
                <a v-if="item.link_url" :href="item.link_url" target="_blank" rel="noreferrer">{{ item.link_url }}</a>
              </div>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </el-card>
</template>

<style scoped>
.graph-shell {
  overflow: hidden;
  border-radius: 28px;
}

.graph-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.graph-kicker {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #5d89b7;
}

.graph-title {
  margin-top: 2px;
  font-size: 24px;
  font-weight: 800;
  color: var(--app-ink);
}

.graph-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: var(--app-ink-soft);
}

.graph-toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
}

.graph-stat-card {
  min-width: 96px;
  padding: 10px 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, #f2f7fc, #ffffff);
  border: 1px solid #dae6f1;
  display: grid;
  gap: 2px;
}

.graph-stat-card span {
  font-size: 12px;
  color: #6580a0;
}

.graph-stat-card strong {
  font-size: 20px;
  color: var(--app-ink);
}

.graph-stat-card--accent {
  background: linear-gradient(135deg, #ebf8f1, #ffffff);
}

.graph-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
}

.graph-stage {
  position: relative;
  min-height: 860px;
  border-radius: 34px;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(9, 26, 49, 0.22);
}

.graph-canvas {
  width: 100%;
  min-height: 860px;
  display: block;
}

.stage-float {
  position: absolute;
  z-index: 2;
  backdrop-filter: blur(18px);
}

.stage-float--controls {
  left: 20px;
  top: 20px;
  bottom: 20px;
  width: 300px;
  padding: 18px;
  border-radius: 28px;
  background: rgba(244, 248, 252, 0.9);
  border: 1px solid rgba(222, 233, 244, 0.95);
  box-shadow: 0 18px 48px rgba(8, 21, 38, 0.12);
  display: grid;
  gap: 16px;
  align-content: start;
}

.stage-float--legend {
  right: 20px;
  top: 20px;
  padding: 14px 16px;
  border-radius: 24px;
  background: rgba(8, 22, 40, 0.36);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 14px 36px rgba(7, 18, 34, 0.22);
  display: grid;
  gap: 10px;
}

.float-section {
  display: grid;
  gap: 12px;
}

.float-section--list {
  min-height: 0;
  flex: 1;
}

.float-title,
.relation-title {
  font-size: 13px;
  font-weight: 800;
  color: var(--app-ink);
  letter-spacing: 0.04em;
}

.chapter-cloud,
.relation-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chapter-pill,
.chapter-summary-item,
.kp-list-item,
.relation-tag {
  border: 0;
  cursor: pointer;
  transition: 0.22s ease;
}

.chapter-pill {
  border-radius: 999px;
  padding: 9px 14px;
  background: #edf4fb;
  color: #36587a;
  font-weight: 700;
}

.chapter-pill:hover,
.chapter-pill.active {
  background: linear-gradient(135deg, #123252, #21598a);
  color: #f8fbff;
  transform: translateY(-1px);
}

.chapter-summary {
  display: grid;
  gap: 8px;
}

.chapter-summary-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 13px;
  border-radius: 18px;
  background: #f7fbfe;
  border: 1px solid #dce7f0;
  color: #41627f;
}

.chapter-summary-item.active,
.chapter-summary-item:hover {
  background: linear-gradient(135deg, rgba(29, 82, 130, 0.09), rgba(109, 171, 243, 0.18));
  border-color: #80aff0;
}

.kp-list {
  display: grid;
  gap: 10px;
  max-height: 420px;
  overflow: auto;
  padding-right: 4px;
}

.kp-list-item {
  display: grid;
  gap: 6px;
  padding: 13px;
  border-radius: 20px;
  background: #f7fbfe;
  border: 1px solid #dce7f0;
}

.kp-list-item:hover,
.kp-list-item.active {
  background: linear-gradient(135deg, rgba(29, 82, 130, 0.09), rgba(109, 171, 243, 0.18));
  border-color: #80aff0;
  transform: translateX(2px);
}

.kp-list-item.recommended {
  box-shadow: inset 0 0 0 1px rgba(255, 197, 84, 0.5);
}

.kp-list-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.kp-list-code {
  font-size: 12px;
  color: #6180a0;
}

.kp-list-status {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.kp-list-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
}

.stage-legend,
.stage-pills {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(239, 247, 255, 0.9);
  font-weight: 700;
}

.legend-item i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.stage-pill {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.stage-pill--mastered {
  background: rgba(45, 204, 132, 0.16);
  color: #8cf1b8;
}

.stage-pill--learning {
  background: rgba(76, 146, 255, 0.18);
  color: #bed8ff;
}

.stage-pill--risk {
  background: rgba(255, 149, 83, 0.18);
  color: #ffd7bf;
}

.bg-orb {
  transform-origin: center;
}

.bg-orb--a {
  animation: orbFloatA 14s ease-in-out infinite alternate;
}

.bg-orb--b {
  animation: orbFloatB 18s ease-in-out infinite alternate;
}

.chapter-anchor-dot {
  fill: rgba(111, 187, 255, 0.9);
  animation: anchorPulse 3.2s ease-in-out infinite;
}

.chapter-anchor__text {
  fill: rgba(235, 245, 255, 0.82);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.06em;
}

.graph-edge {
  opacity: 0;
  animation: edgeReveal 0.9s ease forwards;
  animation-delay: calc(var(--edge-index, 0) * 45ms);
}

.graph-edge--related {
  animation-name: edgeReveal, relatedFlow;
  animation-duration: 0.9s, 4.6s;
  animation-delay: calc(var(--edge-index, 0) * 45ms), 1.1s;
  animation-iteration-count: 1, infinite;
  animation-timing-function: ease, linear;
}

.graph-node {
  cursor: pointer;
}

.graph-node__body {
  opacity: 0;
  animation: nodeReveal 0.72s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  animation-delay: calc(var(--node-index, 0) * 55ms);
}

.node-ring {
  animation: ringPulse 2.8s ease-in-out infinite;
}

.node-shadow {
  opacity: 0.7;
}

.node-core {
  transition: transform 0.24s ease, opacity 0.24s ease;
}

.node-code,
.node-title {
  fill: #f5fbff;
  font-size: 12px;
  font-weight: 800;
  pointer-events: none;
}

.graph-node:hover .node-core {
  opacity: 1;
}

.graph-detail {
  display: grid;
  gap: 14px;
  align-content: start;
}

.detail-hero,
.relation-card {
  border-radius: 24px;
  border: 1px solid #dbe7f2;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fc 100%);
  box-shadow: 0 18px 48px rgba(15, 40, 73, 0.08);
}

.detail-hero {
  padding: 20px;
  display: grid;
  gap: 10px;
}

.detail-status {
  width: fit-content;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.detail-code {
  font-size: 12px;
  color: #617f9e;
}

.detail-title {
  font-size: 26px;
  line-height: 1.2;
  font-weight: 800;
  color: var(--app-ink);
}

.detail-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--app-ink-soft);
}

.detail-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: #edf4fb;
  color: #345a7d;
  font-size: 12px;
  font-weight: 700;
}

.detail-tag--soft {
  background: #f4f8fc;
}

.detail-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detail-metric {
  padding: 14px;
  border-radius: 18px;
  border: 1px solid #dce8f1;
  background: linear-gradient(135deg, #f9fbfd, #eef5fb);
  display: grid;
  gap: 4px;
}

.detail-metric span {
  font-size: 12px;
  color: #62809e;
}

.detail-metric strong {
  font-size: 18px;
  color: var(--app-ink);
}

.relation-card {
  padding: 18px;
  display: grid;
  gap: 14px;
}

.relation-group {
  display: grid;
  gap: 8px;
}

.relation-group__label {
  font-size: 12px;
  font-weight: 800;
  color: #6783a2;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.relation-tag {
  padding: 9px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #edf4fb, #f8fbff);
  color: #31536f;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid #d9e6f1;
}

.relation-tag:hover {
  background: linear-gradient(135deg, #dcecff, #edf6ff);
}

.relation-tag--soft {
  background: linear-gradient(135deg, #f5f8fc, #ffffff);
}

.content-group {
  display: grid;
  gap: 8px;
}

.content-list {
  display: grid;
  gap: 10px;
}

.content-item {
  padding: 12px 14px;
  border-radius: 18px;
  border: 1px solid #dbe6ef;
  background: #f9fbfd;
  display: grid;
  gap: 6px;
  text-decoration: none;
}

.content-item:hover {
  border-color: #96b8e4;
  transform: translateY(-1px);
}

.content-item--plain {
  cursor: default;
}

.content-item__title {
  font-size: 13px;
  line-height: 1.5;
  font-weight: 700;
  color: var(--app-ink);
}

.content-item__meta,
.content-item__desc,
.content-item a {
  font-size: 12px;
  line-height: 1.6;
  color: #617b96;
  word-break: break-all;
}

.empty-copy {
  font-size: 13px;
  color: #7690ab;
}

@keyframes orbFloatA {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(28px, 22px) scale(1.06); }
}

@keyframes orbFloatB {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(-24px, -18px) scale(1.05); }
}

@keyframes anchorPulse {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.2); opacity: 1; }
}

@keyframes edgeReveal {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes relatedFlow {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -34; }
}

@keyframes nodeReveal {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

@keyframes ringPulse {
  0%, 100% { opacity: 0.7; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.03); }
}

@media (max-width: 1320px) {
  .graph-layout {
    grid-template-columns: 1fr;
  }

  .graph-detail {
    order: 2;
  }
}

@media (max-width: 1080px) {
  .graph-stage,
  .graph-canvas {
    min-height: 760px;
  }

  .stage-float--controls {
    position: static;
    width: auto;
    margin: 16px;
  }

  .stage-float--legend {
    right: 16px;
    top: auto;
    bottom: 16px;
  }
}

@media (max-width: 768px) {
  .graph-topbar {
    flex-direction: column;
  }

  .graph-title {
    font-size: 22px;
  }

  .graph-toolbar {
    width: 100%;
    justify-content: flex-start;
  }

  .stage-float--controls,
  .stage-float--legend {
    position: static;
    width: auto;
    margin: 14px;
  }

  .graph-stage,
  .graph-canvas {
    min-height: 640px;
  }

  .detail-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
