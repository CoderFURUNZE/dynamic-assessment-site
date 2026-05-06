<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Check, Lock, Star, Trophy, VideoPlay } from "@element-plus/icons-vue";
import { api, getWithCache } from "../api";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

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
};

type RecoData = {
  target_kp: { id: number; code: string; title: string; chapter?: string; mastery?: number };
  reason_summary: string;
  advice_text?: string;
  student_message?: string;
  personalized_path?: Array<{ kp_id?: number; id?: number; title?: string; action?: string; mastery?: number }>;
  course_completion?: { completed?: boolean; completed_terminal_title?: string };
};

type RouteStop = {
  kp: KP;
  index: number;
  role: "start" | "recommended" | "terminal";
  x: number;
  y: number;
};

type ConnectorLine = {
  key: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
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
const currentKpId = ref<number | null>(null);
const reco = ref<RecoData | null>(null);
const mapRef = ref<HTMLElement | null>(null);
const isDragging = ref(false);
const dragStart = ref({ x: 0, y: 0, left: 0, top: 0 });

const visibleCourses = computed(() =>
  courses.value.filter((item) => item.active !== false && String(item.enroll_status || "").trim().toLowerCase() !== "closed"),
);
const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const recommendedKp = computed(() => reco.value?.target_kp ?? null);
const courseClosed = computed(() => Boolean(currentCourse.value && currentCourse.value.learning_available === false));

const currentKp = computed(() => {
  const recommendedId = Number(recommendedKp.value?.id || 0);
  return visibleKps.value.find((item) => item.id === currentKpId.value)
    ?? visibleKps.value.find((item) => item.id === recommendedId)
    ?? visibleKps.value[0]
    ?? null;
});

const commonStartKp = computed(() =>
  visibleKps.value.find((item) => item.code === "HM-MID-01")
  ?? visibleKps.value.find((item) => !item.is_terminal)
  ?? visibleKps.value[0]
  ?? null,
);

const commonTerminalKp = computed(() =>
  visibleKps.value.find((item) => item.code === "HM-MID-C2")
  ?? visibleKps.value.find((item) => item.is_terminal)
  ?? null,
);

const routeKps = computed(() => {
  const recommendedId = Number(recommendedKp.value?.id || currentKpId.value || 0);
  const byId = new Map<number, KP>();
  for (const item of visibleKps.value) byId.set(item.id, { ...item });
  if (recommendedId && !byId.has(recommendedId) && recommendedKp.value) {
    byId.set(recommendedId, {
      id: recommendedId,
      code: recommendedKp.value.code,
      title: recommendedKp.value.title,
      chapter: recommendedKp.value.chapter,
      mastery: recommendedKp.value.mastery,
    });
  }

  const result: KP[] = [];
  const push = (item?: KP | null, previewLocked = false) => {
    if (!item || result.some((row) => row.id === item.id)) return;
    result.push({ ...item, previewLocked });
  };

  const start = commonStartKp.value;
  const terminal = commonTerminalKp.value;
  push(start);

  const pathIds = (reco.value?.personalized_path ?? [])
    .map((item) => Number(item.kp_id || item.id || 0))
    .filter(Boolean);
  pathIds.forEach((id) => {
    const item = byId.get(id);
    if (!item) return;
    if (start && item.id === start.id) return;
    if (terminal && item.id === terminal.id) return;
    push(item);
  });

  const recommended = recommendedId ? byId.get(recommendedId) ?? null : null;
  if (
    recommended
    && (!start || recommended.id !== start.id)
    && (!terminal || recommended.id !== terminal.id)
  ) {
    push(recommended);
  }

  if (result.length <= 1) {
    const fallback = visibleKps.value.find((item) => {
      if (start && item.id === start.id) return false;
      if (terminal && item.id === terminal.id) return false;
      return !isCompleted(item);
    });
    push(fallback);
  }

  if (terminal) push(terminal, !isCompleted(terminal) && Boolean(recommended && recommended.id !== terminal.id));
  if (result.length === 0) push(visibleKps.value[0]);
  return result.slice(0, 6);
});

const completedCount = computed(() => routeKps.value.filter((item) => isCompleted(item)).length);
const progressPercent = computed(() => {
  if (!routeKps.value.length) return 0;
  return Math.round((completedCount.value / routeKps.value.length) * 100);
});
const previewCount = computed(() => routeKps.value.filter((item) => item.previewLocked).length);
const routeTerminalCount = computed(() => routeKps.value.filter((item) => item.is_terminal).length);

const mapWidth = 1040;
const FAST_ENTRY_CACHE_TTL = 60 * 1000;
const mapHeight = computed(() => 700);
const routeStops = computed<RouteStop[]>(() => {
  const start = routeKps.value[0];
  const terminal = routeKps.value.find((kp) => commonTerminalKp.value && kp.id === commonTerminalKp.value.id)
    ?? routeKps.value[routeKps.value.length - 1];
  const middle = routeKps.value.filter((kp) => kp.id !== start?.id && kp.id !== terminal?.id);
  const laneXs = middle.length <= 1
    ? [520]
    : middle.length === 2
      ? [390, 650]
      : middle.length === 3
        ? [300, 520, 740]
        : [240, 425, 615, 800];
  const stops: RouteStop[] = [];
  if (start) stops.push({ kp: start, index: 0, role: "start", x: 520, y: 120 });
  middle.slice(0, 4).forEach((kp, index) => {
    const laneYs = middle.length <= 1
      ? [330]
      : middle.length === 2
        ? [275, 405]
        : middle.length === 3
          ? [260, 330, 400]
          : [245, 315, 385, 455];
    stops.push({ kp, index: stops.length, role: "recommended", x: laneXs[index] ?? 520, y: laneYs[index] ?? 330 });
  });
  if (terminal && (!start || terminal.id !== start.id)) {
    stops.push({ kp: terminal, index: stops.length, role: "terminal", x: 520, y: middle.length > 1 ? 610 : 545 });
  }
  return stops;
});
const connectorLines = computed(() => {
  const start = routeStops.value.find((item) => item.role === "start");
  const terminal = routeStops.value.find((item) => item.role === "terminal");
  const middle = routeStops.value.filter((item) => item.role === "recommended");
  const lines: ConnectorLine[] = [];
  if (start && middle.length > 0) {
    middle.forEach((stop) => {
      lines.push({
        key: `start-${stop.kp.id}`,
        x1: start.x,
        y1: start.y + 42,
        x2: stop.x,
        y2: stop.y - 42,
        state: nodeState(stop.kp),
      });
    });
  }
  if (terminal && middle.length > 0) {
    middle.forEach((stop) => {
      lines.push({
        key: `${stop.kp.id}-terminal`,
        x1: stop.x,
        y1: stop.y + 42,
        x2: terminal.x,
        y2: terminal.y - 42,
        state: nodeState(stop.kp),
      });
    });
  } else if (start && terminal) {
    lines.push({
      key: "start-terminal",
      x1: start.x,
      y1: start.y + 42,
      x2: terminal.x,
      y2: terminal.y - 42,
      state: nodeState(terminal.kp),
    });
  }
  return lines;
});
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
  return reco.value?.student_message || reco.value?.advice_text || reco.value?.reason_summary || "系统会根据你的掌握度，沿老师设置的路线推荐下一关。";
});

const selectedIsRecommendation = computed(() =>
  Boolean(currentKpId.value && currentKp.value?.id === recommendedKp.value?.id),
);

const focusBadge = computed(() => {
  if (!currentKpId.value) return "推荐本关";
  return selectedIsRecommendation.value ? "推荐本关" : "所选节点";
});

const focusText = computed(() => {
  if (currentKpId.value && !selectedIsRecommendation.value && currentKp.value) {
    return isCompleted(currentKp.value)
      ? "该知识点已经完成，你仍然可以重新进入学习。"
      : "你当前选择的是这个知识点，可以直接进入学习。";
  }
  return reco.value?.reason_summary || "系统会按你的掌握情况自动选择下一关。";
});

const focusActionText = computed(() => {
  if (courseClosed.value) return "查看报告";
  if (currentKpId.value && !selectedIsRecommendation.value && currentKp.value && isCompleted(currentKp.value)) return "重新学习";
  return "进入学习";
});

function isCompleted(kp: KP) {
  return Number(kp.mastery || 0) >= 0.7 || kp.status === "mastered";
}

function nodeState(kp: KP) {
  if (kp.previewLocked) return "locked";
  if (kp.id === recommendedKp.value?.id || kp.id === currentKpId.value) return "current";
  if (isCompleted(kp)) return "done";
  return "open";
}

function nodeIcon(kp: KP) {
  const state = nodeState(kp);
  if (state === "locked") return Lock;
  if (state === "current") return VideoPlay;
  if (kp.is_terminal) return Trophy;
  if (state === "done") return Check;
  return Star;
}

function centerCurrentStop() {
  nextTick(() => {
    const el = mapRef.value;
    if (!el) return;
    el.scrollTop = 0;
  });
}

function cardSide(stop: RouteStop) {
  return stop.index % 2 === 0 ? "is-card-right" : "is-card-left";
}

function onMapPointerDown(event: PointerEvent) {
  const el = mapRef.value;
  if (!el) return;
  const target = event.target as HTMLElement | null;
  if (target?.closest(".learning-route-stop")) return;
  isDragging.value = true;
  dragStart.value = { x: event.clientX, y: event.clientY, left: 0, top: el.scrollTop };
  dragStart.value.left = el.scrollLeft;
  el.setPointerCapture?.(event.pointerId);
}

function onMapPointerMove(event: PointerEvent) {
  const el = mapRef.value;
  if (!el || !isDragging.value) return;
  event.preventDefault();
  el.scrollLeft = dragStart.value.left - (event.clientX - dragStart.value.x);
  el.scrollTop = dragStart.value.top - (event.clientY - dragStart.value.y);
}

function onMapPointerUp(event: PointerEvent) {
  isDragging.value = false;
  mapRef.value?.releasePointerCapture?.(event.pointerId);
}

function resetState() {
  visibleKps.value = [];
  currentKpId.value = null;
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

async function loadCourses(useCache = true) {
  const raw = useCache
    ? await getWithCache<any[]>("/graph/courses", undefined, { skipGlobalLoading: true, ttlMs: FAST_ENTRY_CACHE_TTL })
    : (await api.get("/graph/courses", { skipGlobalLoading: true } as any)).data;
  const list = Array.isArray(raw) ? raw : [];
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
  const visibleTitles = new Set(visibleCourses.value.map((item) => item.title));
  subject.value = routeSubject && !visibleTitles.has(routeSubject)
    ? ""
    : resolveStudentSubject(routeSubject, subject.value, visibleCourses.value, {
      allowCompleted: true,
      allowUnavailable: true,
    });
}

async function loadVisibleKps(useCache = true) {
  if (!subject.value) {
    resetState();
    return;
  }
  const data = await getWithCache<any>(
    "/graph/map",
    { subject: subject.value, grade: grade.value },
    { skipGlobalLoading: true, ttlMs: FAST_ENTRY_CACHE_TTL },
  );
  const overlayMap = new Map<number, any>((Array.isArray(data?.overlay) ? data.overlay : []).map((item: any) => [Number(item.kp_id), item]));
  const list = Array.isArray(data?.base?.kps) ? data.base.kps : [];
  visibleKps.value = list.map((item: any) => {
    const overlay = overlayMap.get(Number(item.id)) || {};
    return {
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
      chapter: String(item.chapter || ""),
      is_terminal: item.is_terminal === true,
      mastery: Number(overlay.mastery || 0),
      status: String(overlay.status || "not_started"),
    };
  });

  const routeKp = Number(route.query.kp || 0);
  const firstLearning = visibleKps.value.find((item) => item.status === "learning" && !isCompleted(item))
    ?? visibleKps.value.find((item) => !isCompleted(item));
  currentKpId.value = routeKp && visibleKps.value.some((item) => item.id === routeKp)
    ? routeKp
    : firstLearning?.id ?? visibleKps.value[0]?.id ?? null;
}

async function loadRecommendation() {
  if (!currentKpId.value) {
    reco.value = null;
    return;
  }
  recoLoading.value = true;
  try {
    const res = await api.get("/reco", {
      params: { kp_id: currentKpId.value, ai: false },
      skipGlobalLoading: true,
    } as any);
    reco.value = res.data ?? null;
  } catch {
    reco.value = null;
  } finally {
    recoLoading.value = false;
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

async function selectKp(kp: KP) {
  if (nodeState(kp) === "locked") {
    ElMessage.info("先完成当前关卡，后续关卡会自动解锁");
    return;
  }
  currentKpId.value = kp.id;
  await loadRecommendation();
  syncQuery();
  centerCurrentStop();
}

function openKp(id?: number | null) {
  if (courseClosed.value) {
    openReport();
    return;
  }
  const targetId = Number(id || currentKpId.value || recommendedKp.value?.id || 0);
  if (!targetId) {
    ElMessage.warning("当前还没有可学习的关卡");
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
</script>

<template>
  <div v-loading="loading" class="learning-route-page">
    <section class="learning-route-hero">
      <div class="learning-route-hero__copy">
        <span class="learning-route-badge">个性化学习路线</span>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageLead }}</p>
      </div>
      <div class="learning-route-actions">
        <el-select v-model="subject" class="learning-route-course" placeholder="选择课程" :disabled="visibleCourses.length === 0" @change="handleCourseChange">
          <el-option v-for="course in visibleCourses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button type="button" class="learning-route-button" @click="() => refreshPage(true)">刷新</button>
        <button v-if="courseClosed" type="button" class="learning-route-button learning-route-button--primary" @click="openReport">查看报告</button>
        <button v-else type="button" class="learning-route-button learning-route-button--primary" @click="openKp(currentKpId || recommendedKp?.id)">开始本关</button>
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
          <div>
            <span class="learning-route-badge">当前课程</span>
            <h2>{{ currentCourse?.title || subject }}</h2>
          </div>
          <div class="learning-route-progress">
            <strong>{{ progressPercent }}%</strong>
            <span>路线进度</span>
          </div>
        </header>

        <div
          ref="mapRef"
          class="learning-route-map"
          :class="{ 'is-dragging': isDragging }"
          @pointerdown="onMapPointerDown"
          @pointermove="onMapPointerMove"
          @pointerup="onMapPointerUp"
          @pointerleave="onMapPointerUp"
        >
          <div class="learning-route-canvas" :style="{ width: `${mapWidth}px`, height: `${mapHeight}px` }">
            <svg class="learning-route-lines" :viewBox="`0 0 ${mapWidth} ${mapHeight}`" aria-hidden="true">
              <line
                v-for="line in connectorLines"
                :key="line.key"
                class="learning-route-line"
                :class="`is-${line.state}`"
                :x1="line.x1"
                :y1="line.y1"
                :x2="line.x2"
                :y2="line.y2"
              />
            </svg>
            <article
              v-for="stop in routeStops"
              :key="stop.kp.id"
              class="learning-route-stop"
              :class="[`is-${nodeState(stop.kp)}`, `is-${stop.role}`, cardSide(stop)]"
              :style="{ left: `${stop.x}px`, top: `${stop.y}px` }"
            >
              <button class="learning-route-node" type="button" @click.stop="selectKp(stop.kp)">
                <el-icon><component :is="nodeIcon(stop.kp)" /></el-icon>
              </button>
              <div class="learning-route-card">
                <span>{{ stop.kp.code }}</span>
                <strong>{{ stop.kp.title }}</strong>
                <small>{{ stop.role === "start" ? "共同起点" : (stop.role === "terminal" ? "达标终点" : "系统推荐节点") }}</small>
              </div>
            </article>
          </div>
        </div>
      </main>

      <aside class="learning-route-side">
        <section class="learning-route-panel learning-route-panel--focus">
          <span class="learning-route-badge">{{ focusBadge }}</span>
          <h2>{{ currentKp?.title || recommendedKp?.title || "等待推荐" }}</h2>
          <p>{{ focusText }}</p>
          <button class="learning-route-button learning-route-button--primary learning-route-button--wide" type="button" @click="openKp(currentKpId || recommendedKp?.id)">
            {{ focusActionText }}
          </button>
        </section>

        <section class="learning-route-panel">
          <span class="learning-route-badge">路线概况</span>
          <div class="learning-route-stats">
            <div><strong>{{ routeKps.length }}</strong><span>当前显示</span></div>
            <div><strong>{{ completedCount }}</strong><span>已完成</span></div>
            <div><strong>{{ previewCount || routeTerminalCount }}</strong><span>{{ previewCount ? "待解锁" : "终点" }}</span></div>
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
}

.learning-route-hero,
.learning-route-board,
.learning-route-panel,
.learning-route-empty {
  border: 1px solid #d8e5d4;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
}

.learning-route-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 22px 28px;
}

.learning-route-hero__copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.learning-route-badge {
  width: fit-content;
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: #edf8e8;
  color: #2b7a0b;
  border: 1px solid #cdeec0;
  font-size: 12px;
  font-weight: 900;
}

.learning-route-hero h1,
.learning-route-board__head h2,
.learning-route-panel h2 {
  margin: 0;
  color: #102033;
  overflow-wrap: anywhere;
}

.learning-route-hero h1 {
  font-size: 34px;
  line-height: 1.12;
}

.learning-route-hero p,
.learning-route-panel p,
.learning-route-empty p {
  margin: 0;
  color: #5f6d5d;
  line-height: 1.7;
}

.learning-route-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.learning-route-course {
  width: 260px;
}

.learning-route-button {
  min-height: 42px;
  border: 0;
  border-radius: 12px;
  padding: 0 18px;
  background: #eef4ea;
  color: #2e3d2a;
  font-weight: 900;
  cursor: pointer;
  box-shadow: inset 0 -3px 0 rgba(15, 23, 42, 0.08);
}

.learning-route-button--primary {
  background: #58cc02;
  color: #ffffff;
  box-shadow: inset 0 -4px 0 #46a302;
}

.learning-route-button--wide {
  width: 100%;
}

.learning-route-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
  align-items: start;
}

.learning-route-board {
  padding: 24px;
  overflow: hidden;
}

.learning-route-board__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid #edf3ea;
}

.learning-route-progress {
  width: 104px;
  height: 104px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  align-content: center;
  background: conic-gradient(#58cc02 var(--progress, 60%), #e8f4e3 0);
  color: #1f3d12;
}

.learning-route-progress strong {
  font-size: 26px;
}

.learning-route-progress span {
  font-size: 12px;
  font-weight: 800;
}

.learning-route-map {
  height: min(66vh, 680px);
  min-height: 560px;
  margin-top: 18px;
  overflow-x: auto;
  overflow-y: auto;
  overscroll-behavior: contain;
  border: 1px solid rgba(141, 184, 132, 0.32);
  border-radius: 16px;
  background:
    linear-gradient(rgba(221, 235, 214, 0.26) 1px, transparent 1px),
    linear-gradient(90deg, rgba(221, 235, 214, 0.26) 1px, transparent 1px),
    #fffef8;
  background-size: 40px 40px, 40px 40px, auto;
  cursor: grab;
  touch-action: none;
  user-select: none;
  scrollbar-width: thin;
}

.learning-route-map.is-dragging {
  cursor: grabbing;
}

.learning-route-canvas {
  position: relative;
  width: 720px;
  min-width: 1040px;
  margin: 0 auto;
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
  stroke: #b7c7d9;
  stroke-width: 3;
  stroke-linecap: round;
}

.learning-route-line.is-done {
  stroke: #58cc02;
  stroke-width: 5;
}

.learning-route-line.is-current {
  stroke: #ffb000;
  stroke-width: 5;
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
}

.learning-route-node {
  position: absolute;
  left: 0;
  top: 0;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  border: 0;
  border-radius: 999px;
  background: #58cc02;
  color: #ffffff;
  font-size: 30px;
  cursor: pointer;
  box-shadow: inset 0 -8px 0 #46a302, 0 10px 20px rgba(88, 204, 2, 0.24);
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

.learning-route-card {
  position: absolute;
  top: 0;
  width: 168px;
  min-height: 92px;
  display: grid;
  gap: 5px;
  place-items: center;
  padding: 15px 16px;
  border-radius: 14px;
  border: 1px solid #dfead9;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  text-align: center;
  z-index: 2;
}

.learning-route-stop.is-card-right .learning-route-card {
  left: 88px;
  transform: translateY(-50%);
}

.learning-route-stop.is-card-left .learning-route-card {
  right: 88px;
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

.learning-route-stop.is-current .learning-route-node {
  background: linear-gradient(180deg, #ffc800 0%, #ffab00 100%);
  box-shadow: inset 0 -8px 0 #d38a00, 0 18px 30px rgba(255, 178, 0, 0.28);
}

.learning-route-stop.is-open .learning-route-node {
  background: linear-gradient(180deg, #57c7ff 0%, #1d9ad6 100%);
  box-shadow: inset 0 -8px 0 #147fb7, 0 16px 26px rgba(29, 154, 214, 0.2);
}

.learning-route-stop.is-locked .learning-route-node {
  background: linear-gradient(180deg, #d7dfd1 0%, #aebbaa 100%);
  box-shadow: inset 0 -8px 0 #879281, 0 12px 22px rgba(95, 111, 90, 0.16);
}

.learning-route-stop.is-locked .learning-route-card {
  opacity: 0.68;
}

.learning-route-side {
  display: grid;
  gap: 18px;
  position: sticky;
  top: 18px;
}

.learning-route-panel {
  display: grid;
  gap: 14px;
  padding: 20px;
}

.learning-route-panel--focus {
  background: #fbfff8;
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
  border-radius: 12px;
  background: #f3f8f0;
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

.learning-route-empty {
  display: grid;
  place-items: center;
  text-align: center;
  gap: 12px;
  padding: 48px;
}

@media (max-width: 1080px) {
  .learning-route-layout {
    grid-template-columns: 1fr;
  }

  .learning-route-side {
    position: static;
  }
}

@media (max-width: 720px) {
  .learning-route-hero,
  .learning-route-board__head {
    flex-direction: column;
    align-items: flex-start;
  }

  .learning-route-course,
  .learning-route-actions {
    width: 100%;
  }

  .learning-route-map {
    min-height: 500px;
  }
}
</style>
