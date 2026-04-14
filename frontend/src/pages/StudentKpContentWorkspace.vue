<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElCard, ElMessage, ElProgress } from "element-plus";
import { api } from "../api";
import ResourcePane from "../components/ResourcePane.vue";
import QuizPane from "../components/QuizPane.vue";

type KpInfo = {
  id: number;
  code: string;
  title: string;
  chapter?: string;
};

type ResourceItem = {
  id: number;
  kp_id: number;
  type: string;
  title: string;
  url: string;
  category?: string;
  description?: string;
};

type TaskItem = {
  id: number;
  kp_id: number;
  type: string;
  title: string;
  description: string;
  link_url: string;
  sort_order: number;
};

type RelationNode = {
  id: number;
  code: string;
  title: string;
};

type NodeDetail = {
  kp: KpInfo;
  overlay?: {
    blocked_reason?: string | null;
    mastery?: number;
    status?: string;
  } | null;
  resource_list: ResourceItem[];
  task_list: TaskItem[];
  practice_list: Array<{ id: number; kp_id: number; type: string; prompt: string; difficulty: number }>;
  prerequisites: RelationNode[];
  downstream: RelationNode[];
  related: RelationNode[];
  navigation?: {
    chapter: string;
    previous?: RelationNode | null;
    next?: RelationNode | null;
    chapter_nodes: RelationNode[];
  } | null;
};

type RecoData = {
  target_kp: { id: number; code: string; title: string; mastery?: number };
  reason_summary: string;
  recommendation_stage_label?: string;
  advice_text: string;
};

type WorkspaceView = "overview" | "resource" | "practice" | "review" | "next";
type QuizSubView = "practice" | "records" | "wrong" | "review";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const activeView = ref<WorkspaceView>("resource");
const workflowSteps: WorkspaceView[] = ["overview", "resource", "practice", "review", "next"];
const detail = ref<NodeDetail | null>(null);
const reco = ref<RecoData | null>(null);
const lastRecommendedTargetId = ref<number | null>(null);
const deniedMessageShown = ref(false);
const closureState = reactive({
  resourceDone: false,
  practiceDone: false,
});

const kpId = computed(() => {
  const raw = Number(route.params.kpId);
  return Number.isFinite(raw) && raw > 0 ? raw : 0;
});

const subject = computed(() => String(route.query.subject || ""));
const grade = computed(() => String(route.query.grade || "通用"));
const isPreview = computed(() => String(route.query.preview || "") === "1");
const isTeacherPreview = computed(() => String(route.path || "").startsWith("/teacher/kp-preview/"));
const graphView = computed(() => {
  const v = String(route.query.view || "");
  return v === "path" || v === "reco" || v === "map" ? v : "map";
});

const quizSubViewFromPath = computed<QuizSubView | null>(() => {
  const p = String(route.path || "");
  if (p.endsWith("/practice")) return "practice";
  if (p.endsWith("/records")) return "records";
  if (p.endsWith("/wrong")) return "wrong";
  if (p.endsWith("/review")) return "review";
  return null;
});

const learningResources = computed(() =>
  (detail.value?.resource_list ?? []).filter((item) => (item.category || "learning") !== "recommend"),
);
const videoResources = computed(() => learningResources.value.filter((item) => item.type === "video"));
const recommendedResources = computed(() =>
  (detail.value?.resource_list ?? []).filter((item) => (item.category || "learning") === "recommend"),
);
const recommendationContext = computed(() => {
  if (!reco.value) return null;
  const isCurrentTarget = reco.value.target_kp?.id === kpId.value;
  return {
    isCurrentTarget,
    label: reco.value.recommendation_stage_label || "当前推荐",
    reason: reco.value.reason_summary,
    advice: reco.value.advice_text,
  };
});

const closureDoneCount = computed(() => [closureState.resourceDone, closureState.practiceDone].filter(Boolean).length);
const closureReady = computed(() => closureDoneCount.value >= 2);
const stats = computed(() => ({
  learning: learningResources.value.length,
  practice: detail.value?.practice_list?.length ?? 0,
  recommend: recommendedResources.value.length + (detail.value?.task_list?.length ?? 0),
}));
const navigation = computed(() => detail.value?.navigation ?? null);
const masteryPercent = computed(() => Math.round(Number(detail.value?.overlay?.mastery ?? 0) * 100));
const masteryStatus = computed(() => {
  const raw = String(detail.value?.overlay?.status || "").toLowerCase();
  if (raw === "mastered") return "已掌握";
  if (raw === "learning" || raw === "in_progress") return "学习中";
  if (raw === "risk") return "待巩固";
  if (raw === "not_started") return "未开始";
  if (masteryPercent.value >= 85) return "已掌握";
  if (masteryPercent.value >= 50) return "学习中";
  if (masteryPercent.value > 0) return "待巩固";
  return "未开始";
});
const taskLead = computed(() => detail.value?.kp?.description || "先完成资源学习和练习，再看下一步建议。");
const currentTaskSubtitle = computed(() => `${detail.value?.kp?.title || "当前知识点"}（示例）`);
const sidebarSuggestion = computed(() => {
  if (recommendationContext.value?.reason) return recommendationContext.value.reason;
  if (detail.value?.overlay?.blocked_reason) return detail.value.overlay.blocked_reason;
  return "建议先完成当前知识点的资源学习与练习，再进入下一知识点。";
});
const nextStepSuggestion = computed(() => {
  if (reco.value?.target_kp?.title) return reco.value.target_kp.title;
  if (navigation.value?.next?.title) return navigation.value.next.title;
  return "继续巩固当前知识点";
});

const stepLabelMap: Record<WorkspaceView, string> = {
  overview: "学习概览",
  resource: "资源学习",
  practice: "练习作答",
  review: "复盘反馈",
  next: "下一步建议",
};

const workflowCards = computed(() => [
  { key: "overview" as WorkspaceView, title: "学习概览", hint: "先看推荐与当前进度", count: "概览" },
  { key: "resource" as WorkspaceView, title: "资源学习", hint: `${stats.value.learning} 项资源`, count: `${stats.value.learning}` },
  { key: "practice" as WorkspaceView, title: "练习作答", hint: `${stats.value.practice} 道练习`, count: `${stats.value.practice}` },
  { key: "review" as WorkspaceView, title: "复盘反馈", hint: "错题与记录复盘", count: closureState.practiceDone ? "已更新" : "待完成" },
  { key: "next" as WorkspaceView, title: "下一步建议", hint: closureReady.value ? "已解锁" : "待解锁", count: closureReady.value ? "可进入" : "未解锁" },
]);

const nextStepDisabledReason = computed(() => {
  if (closureReady.value) return "";
  const todos: string[] = [];
  if (!closureState.resourceDone) todos.push("完成资源学习");
  if (!closureState.practiceDone) todos.push("完成练习提交");
  return `进入“下一步建议”前，请先${todos.join("、")}。`;
});

function getStepDisabled(view: WorkspaceView) {
  return view === "next" ? !closureReady.value : false;
}

const nextView = computed<WorkspaceView | null>(() => {
  const idx = workflowSteps.indexOf(activeView.value);
  if (idx < 0 || idx >= workflowSteps.length - 1) return null;
  return workflowSteps[idx + 1];
});

const nextButtonText = computed(() => {
  if (!nextView.value) return "下一步";
  return `下一步：${stepLabelMap[nextView.value]}`;
});

watch(
  () => quizSubViewFromPath.value,
  (v) => {
    if (!v) return;
    activeView.value = v === "practice" ? "practice" : "review";
  },
  { immediate: true },
);

const quizRouteView = computed<QuizSubView | null>(() => {
  if (activeView.value === "practice") return "practice";
  if (activeView.value === "review") {
    return quizSubViewFromPath.value && quizSubViewFromPath.value !== "practice" ? quizSubViewFromPath.value : "wrong";
  }
  return null;
});

function switchView(view: WorkspaceView) {
  if (getStepDisabled(view)) {
    if (nextStepDisabledReason.value) ElMessage.warning(nextStepDisabledReason.value);
    return;
  }
  activeView.value = view;
  if (view === "practice") {
    goQuizSubView("practice");
    return;
  }
  if (view === "review") {
    const fallback = quizSubViewFromPath.value && quizSubViewFromPath.value !== "practice" ? quizSubViewFromPath.value : "wrong";
    goQuizSubView(fallback);
  }
}

function goPrevView() {
  const idx = workflowSteps.indexOf(activeView.value);
  if (idx <= 0) return;
  switchView(workflowSteps[idx - 1]);
}

function goNextView() {
  const idx = workflowSteps.indexOf(activeView.value);
  if (idx < 0 || idx >= workflowSteps.length - 1) return;
  switchView(workflowSteps[idx + 1]);
}

function handleQuizViewChange(v: QuizSubView) {
  activeView.value = v === "practice" ? "practice" : "review";
  goQuizSubView(v);
}

const masterySummary = computed(() => `${masteryPercent.value}% · ${masteryStatus.value}`);

function goBack() {
  router.push({
    path: isTeacherPreview.value ? "/teacher/content" : "/student/graph-workspace",
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      kp: kpId.value ? String(kpId.value) : undefined,
      view: graphView.value !== "map" ? graphView.value : undefined,
      preview: isPreview.value ? "1" : undefined,
    },
  });
}

function goToKp(id: number) {
  router.push({
    path: isTeacherPreview.value ? `/teacher/kp-preview/${id}` : `/student/kp-content/${id}`,
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      preview: isPreview.value ? "1" : undefined,
    },
  });
}

function goToRecommendedTarget() {
  const targetId = reco.value?.target_kp?.id;
  if (!targetId) return;
  if (targetId === kpId.value) {
    activeView.value = "resource";
    return;
  }
  goToKp(targetId);
}

function goToReport() {
  if (isTeacherPreview.value) {
    goBack();
    return;
  }
  router.push({
    path: "/student/report",
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      preview: isPreview.value ? "1" : undefined,
    },
  });
}

function goQuizSubView(view: QuizSubView) {
  if (!kpId.value) return;
  const base = isTeacherPreview.value ? `/teacher/kp-preview/${kpId.value}` : `/student/kp-content/${kpId.value}`;
  const targetPath = `${base}/${view === "practice" ? "practice" : view}`;
  const currentPath = String(router.currentRoute.value?.path || "");
  if (currentPath === targetPath) return;
  router.push({
    path: targetPath,
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      preview: isPreview.value ? "1" : undefined,
    },
  }).catch(() => {});
}

async function loadDetail() {
  if (!kpId.value) return;
  loading.value = true;
  try {
    const res = await api.get(`/graph/node/${kpId.value}`);
    deniedMessageShown.value = false;
    detail.value = res.data;
    const blockedReason = res.data?.overlay?.blocked_reason;
    if (blockedReason) {
      if (!deniedMessageShown.value) {
        deniedMessageShown.value = true;
        ElMessage.warning(blockedReason);
      }
      goBack();
    }
  } catch (e: any) {
    const message = e?.response?.data?.detail ?? "加载学习内容失败";
    if (e?.response?.status === 403) {
      if (!deniedMessageShown.value) {
        deniedMessageShown.value = true;
        ElMessage.warning(message);
      }
      goBack();
      return;
    }
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
}

async function loadRecommendation(options: { notifyOnChange?: boolean } = {}) {
  if (!kpId.value) return;
  try {
    const previousTargetId = reco.value?.target_kp?.id ?? lastRecommendedTargetId.value ?? null;
    const res = await api.get(`/reco?kp_id=${kpId.value}`);
    reco.value = res.data ?? null;
    const nextTargetId = reco.value?.target_kp?.id ?? null;
    lastRecommendedTargetId.value = nextTargetId;
    if (
      options.notifyOnChange &&
      previousTargetId &&
      nextTargetId &&
      previousTargetId !== nextTargetId &&
      reco.value?.target_kp?.title
    ) {
      ElMessage.success(`系统已更新下一推荐点：${reco.value.target_kp.title}`);
    }
  } catch {
    reco.value = null;
  }
}

async function refreshAfterLearning() {
  await loadDetail();
  await loadRecommendation({ notifyOnChange: true });
}

async function handleResourceUpdated() {
  closureState.resourceDone = true;
  await refreshAfterLearning();
}

async function handlePracticeUpdated() {
  closureState.practiceDone = true;
  await refreshAfterLearning();
}

onMounted(async () => {
  if (!kpId.value) {
    ElMessage.warning("缺少知识点参数");
    goBack();
    return;
  }
  await loadDetail();
  if (deniedMessageShown.value) return;
  await loadRecommendation();
});

watch(kpId, async () => {
  deniedMessageShown.value = false;
  closureState.resourceDone = false;
  closureState.practiceDone = false;
  await loadDetail();
  if (deniedMessageShown.value) return;
  await loadRecommendation();
});
</script>

<template>
  <div class="student-kp-page" v-loading="loading">
    <section class="student-kp-page__hero">
      <div class="student-kp-page__hero-copy">
        <button class="student-kp-page__back" type="button" @click="goBack">返回图谱</button>
        <div class="student-kp-page__hero-text">
          <span class="student-kp-page__eyebrow">知识点学习</span>
          <h1>{{ detail?.kp?.title || "知识点学习" }}</h1>
          <p>{{ taskLead }}</p>
          <div class="student-kp-page__hero-meta">
            <span>{{ detail?.kp?.code || "--" }}</span>
            <span>{{ detail?.kp?.chapter || "未分类" }}</span>
            <span>{{ masterySummary }}</span>
          </div>
        </div>
      </div>

      <div class="student-kp-page__hero-actions">
        <button class="student-kp-page__btn" type="button" @click="switchView('resource')">资源学习</button>
        <button class="student-kp-page__btn student-kp-page__btn--primary" type="button" @click="switchView('practice')">
          继续学习
        </button>
      </div>
    </section>

    <section class="student-kp-page__stats">
      <article class="student-kp-page__stat-card">
        <span>掌握度</span>
        <strong>{{ masteryPercent }}%</strong>
        <small>当前知识点学习状态：{{ masteryStatus }}</small>
      </article>
      <article class="student-kp-page__stat-card">
        <span>学习资源</span>
        <strong>{{ stats.learning }}</strong>
        <small>{{ videoResources.length }} 个视频资源</small>
      </article>
      <article class="student-kp-page__stat-card">
        <span>练习作答</span>
        <strong>{{ stats.practice }}</strong>
        <small>当前知识点可练习题目数</small>
      </article>
      <article class="student-kp-page__stat-card">
        <span>推荐内容</span>
        <strong>{{ stats.recommend }}</strong>
        <small>推荐资源与任务数量</small>
      </article>
    </section>

    <section class="student-kp-page__workflow">
      <button
        v-for="item in workflowCards"
        :key="item.key"
        class="student-kp-page__workflow-card"
        :class="{ active: activeView === item.key, disabled: getStepDisabled(item.key) }"
        type="button"
        @click="switchView(item.key)"
      >
        <span>{{ item.title }}</span>
        <strong>{{ item.count }}</strong>
        <small>{{ item.hint }}</small>
      </button>
    </section>

    <section class="student-kp-page__content">
      <main class="student-kp-page__main">
        <section class="student-kp-page__task-card">
          <div class="student-kp-page__task-copy">
            <span class="student-kp-page__section-eyebrow">当前学习任务</span>
            <div class="student-kp-page__task-head">
              <div>
                <span class="student-kp-page__task-code">{{ detail?.kp?.code || "--" }}</span>
                <h2>{{ detail?.kp?.title || "当前暂无知识点" }}</h2>
                <p>{{ currentTaskSubtitle }}</p>
              </div>
              <span class="student-kp-page__status-pill">{{ masteryStatus }}</span>
            </div>
            <div class="student-kp-page__progress">
              <div class="student-kp-page__progress-head">
                <span>当前掌握度</span>
                <strong>{{ masteryPercent }}%</strong>
              </div>
              <ElProgress :percentage="masteryPercent" :show-text="false" :stroke-width="10" color="#4f7fff" />
            </div>
          </div>

          <div class="student-kp-page__task-actions">
            <button class="student-kp-page__btn student-kp-page__btn--primary" type="button" @click="switchView('resource')">
              进入资源学习
            </button>
            <button class="student-kp-page__btn" type="button" @click="switchView('practice')">
              进入练习作答
            </button>
          </div>
        </section>

        <section v-if="navigation" class="student-kp-page__chapter-nav">
          <div class="student-kp-page__chapter-head">
            <div>
              <span class="student-kp-page__section-eyebrow">章节导航</span>
              <h3>当前位于 {{ navigation.chapter || detail?.kp?.chapter || "未分章" }}</h3>
            </div>
            <div class="student-kp-page__chapter-actions">
              <button class="student-kp-page__btn" type="button" :disabled="!navigation.previous" @click="navigation.previous && goToKp(navigation.previous.id)">
                上一知识点
              </button>
              <button class="student-kp-page__btn" type="button" :disabled="!navigation.next" @click="navigation.next && goToKp(navigation.next.id)">
                下一知识点
              </button>
            </div>
          </div>
          <div class="student-kp-page__chapter-list">
            <button
              v-for="item in navigation.chapter_nodes"
              :key="item.id"
              class="student-kp-page__chapter-chip"
              :class="{ active: item.id === kpId }"
              type="button"
              @click="goToKp(item.id)"
            >
              {{ item.title }}
            </button>
          </div>
        </section>

        <section v-if="activeView === 'overview'" class="student-kp-page__panel-grid">
          <article v-if="recommendationContext" class="student-kp-page__info-card">
            <span class="student-kp-page__section-eyebrow">推荐说明</span>
            <h3>{{ recommendationContext.label }}</h3>
            <p>{{ recommendationContext.reason }}</p>
            <p>{{ recommendationContext.advice }}</p>
            <button class="student-kp-page__btn" type="button" @click="switchView('resource')">开始资源学习</button>
          </article>

          <article class="student-kp-page__info-card">
            <span class="student-kp-page__section-eyebrow">学习进度</span>
            <h3>已完成 {{ closureDoneCount }}/2 项</h3>
            <p>{{ closureReady ? "可以进入下一步建议" : "建议先完成资源学习与练习提交" }}</p>
            <div class="student-kp-page__checklist">
              <span :class="{ done: closureState.resourceDone }">资源学习</span>
              <span :class="{ done: closureState.practiceDone }">练习提交</span>
            </div>
          </article>
        </section>

        <template v-else-if="activeView === 'resource'">
          <ElCard v-if="isPreview" shadow="never" class="student-kp-page__card">
            <template #header>学习资源（预览模式）</template>
            <div v-if="learningResources.length === 0" class="student-kp-page__empty">当前知识点还没有学习资源</div>
            <div v-else class="student-kp-page__link-list">
              <a v-for="item in learningResources" :key="item.id" :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
            </div>
          </ElCard>
          <ResourcePane v-else :kp-id="kpId" @progress-updated="handleResourceUpdated" />
        </template>

        <QuizPane
          v-else-if="activeView === 'practice' || activeView === 'review'"
          :kp-id="kpId"
          :preview="isPreview"
          :route-view="quizRouteView"
          @mastery-updated="handlePracticeUpdated"
          @view-change="(v) => handleQuizViewChange(v)"
        />

        <ElCard v-else shadow="never" class="student-kp-page__card">
          <template #header>下一步建议</template>

          <section v-if="recommendationContext" class="student-kp-page__next-card">
            <span class="student-kp-page__section-eyebrow">推荐学习</span>
            <h3>{{ recommendationContext.label }}</h3>
            <p>{{ recommendationContext.reason }}</p>
            <p>{{ recommendationContext.advice }}</p>
            <button class="student-kp-page__btn student-kp-page__btn--primary" type="button" @click="goToRecommendedTarget">
              {{ recommendationContext.isCurrentTarget ? "继续学习当前推荐点" : "跳转到系统推荐点" }}
            </button>
          </section>

          <div class="student-kp-page__section">
            <h3>推荐资源</h3>
            <div v-if="recommendedResources.length === 0" class="student-kp-page__empty">暂无推荐资源</div>
            <div v-else class="student-kp-page__link-list">
              <a v-for="item in recommendedResources" :key="item.id" :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
            </div>
          </div>

          <div class="student-kp-page__section">
            <h3>学习任务</h3>
            <div v-if="(detail?.task_list?.length ?? 0) === 0" class="student-kp-page__empty">暂无学习任务</div>
            <div v-else class="student-kp-page__task-list">
              <div v-for="task in detail?.task_list ?? []" :key="task.id" class="student-kp-page__task-item">
                <strong>{{ task.title }}</strong>
                <p>{{ task.description || "暂无任务描述" }}</p>
                <a v-if="task.link_url" :href="task.link_url" target="_blank" rel="noreferrer">打开任务链接</a>
              </div>
            </div>
          </div>

          <div class="student-kp-page__section">
            <h3>相关知识点</h3>
            <div class="student-kp-page__tag-list">
              <button v-for="item in detail?.prerequisites ?? []" :key="`pre-${item.id}`" type="button" @click="goToKp(item.id)">
                前置：{{ item.title }}
              </button>
              <button v-for="item in detail?.downstream ?? []" :key="`next-${item.id}`" type="button" @click="goToKp(item.id)">
                后续：{{ item.title }}
              </button>
              <button v-for="item in detail?.related ?? []" :key="`rel-${item.id}`" type="button" @click="goToKp(item.id)">
                关联：{{ item.title }}
              </button>
            </div>
          </div>
        </ElCard>

        <section class="student-kp-page__bottom-nav">
          <button class="student-kp-page__btn" type="button" :disabled="activeView === 'overview'" @click="goPrevView">上一步</button>
          <div class="student-kp-page__bottom-hint">
            <span v-if="activeView === 'next'">已经到最后一步，可继续前往推荐知识点或查看学习报告。</span>
            <span v-else-if="nextView === 'next' && !closureReady">{{ nextStepDisabledReason }}</span>
            <span v-else>按顺序推进学习流程：概览 → 资源 → 练习 → 复盘 → 下一步。</span>
          </div>
          <button
            class="student-kp-page__btn student-kp-page__btn--primary"
            type="button"
            :disabled="activeView === 'next' || (nextView === 'next' && !closureReady)"
            @click="goNextView"
          >
            {{ nextButtonText }}
          </button>
        </section>
      </main>

      <aside class="student-kp-page__side">
        <section class="student-kp-page__side-card">
          <span class="student-kp-page__section-eyebrow">下一步建议</span>
          <h3>{{ nextStepSuggestion }}</h3>
          <p>{{ sidebarSuggestion }}</p>
        </section>

        <section class="student-kp-page__side-card">
          <span class="student-kp-page__section-eyebrow">学习概况</span>
          <div class="student-kp-page__side-metrics">
            <div>
              <small>掌握度</small>
              <strong>{{ masteryPercent }}%</strong>
            </div>
            <div>
              <small>资源</small>
              <strong>{{ stats.learning }}</strong>
            </div>
            <div>
              <small>练习</small>
              <strong>{{ stats.practice }}</strong>
            </div>
            <div>
              <small>推荐</small>
              <strong>{{ stats.recommend }}</strong>
            </div>
          </div>
        </section>

        <section class="student-kp-page__side-card">
          <span class="student-kp-page__section-eyebrow">学习提醒</span>
          <div class="student-kp-page__checklist">
            <span :class="{ done: closureState.resourceDone }">已学资源</span>
            <span :class="{ done: closureState.practiceDone }">已做练习</span>
          </div>
          <p>{{ closureReady ? "当前已完成本轮学习闭环，可以进入下一步建议。" : "建议优先完成当前任务后再进入下一知识点。" }}</p>
          <button class="student-kp-page__btn" type="button" @click="goToReport">查看学习报告</button>
        </section>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.student-kp-page {
  min-height: 100vh;
  max-width: 1480px;
  margin: 0 auto;
  padding: 20px 20px 28px;
  display: grid;
  gap: 18px;
}

.student-kp-page__hero,
.student-kp-page__stat-card,
.student-kp-page__workflow-card,
.student-kp-page__task-card,
.student-kp-page__chapter-nav,
.student-kp-page__info-card,
.student-kp-page__side-card,
.student-kp-page__card,
.student-kp-page__bottom-nav {
  border-radius: 24px;
  border: 1px solid #dfe7f1;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
}

.student-kp-page__hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 24px;
}

.student-kp-page__hero-copy {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.student-kp-page__hero-text {
  display: grid;
  gap: 8px;
}

.student-kp-page__back,
.student-kp-page__btn {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid #dce6f2;
  background: #ffffff;
  color: #314661;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.student-kp-page__eyebrow,
.student-kp-page__section-eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(79, 127, 255, 0.1);
  color: #4f7fff;
  font-size: 12px;
  font-weight: 800;
}

.student-kp-page__hero-text h1 {
  margin: 0;
  font-size: clamp(26px, 3vw, 34px);
  line-height: 1.1;
  color: #1f2a44;
}

.student-kp-page__hero-text p,
.student-kp-page__task-head p,
.student-kp-page__chapter-head p,
.student-kp-page__info-card p,
.student-kp-page__side-card p,
.student-kp-page__next-card p,
.student-kp-page__task-item p {
  margin: 0;
  color: #70819a;
  line-height: 1.7;
}

.student-kp-page__hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.student-kp-page__hero-meta span,
.student-kp-page__task-code,
.student-kp-page__status-pill {
  display: inline-flex;
  padding: 7px 12px;
  border-radius: 999px;
  background: #eef4ff;
  color: #4f7fff;
  font-size: 12px;
  font-weight: 800;
}

.student-kp-page__hero-actions,
.student-kp-page__task-actions,
.student-kp-page__chapter-actions,
.student-kp-page__bottom-nav {
  display: flex;
  gap: 12px;
  align-items: center;
}

.student-kp-page__btn--primary {
  border-color: #4f7fff;
  background: linear-gradient(135deg, #5b7cfa 0%, #59b7ff 100%);
  color: #ffffff;
}

.student-kp-page__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.student-kp-page__stat-card,
.student-kp-page__workflow-card,
.student-kp-page__task-card,
.student-kp-page__chapter-nav,
.student-kp-page__info-card,
.student-kp-page__side-card {
  padding: 20px 22px;
}

.student-kp-page__stat-card {
  display: grid;
  gap: 8px;
}

.student-kp-page__stat-card span,
.student-kp-page__stat-card small,
.student-kp-page__workflow-card span,
.student-kp-page__workflow-card small,
.student-kp-page__side-metrics small {
  color: #70819a;
  font-size: 13px;
}

.student-kp-page__stat-card strong,
.student-kp-page__side-metrics strong {
  font-size: 28px;
  line-height: 1.1;
  color: #1f2a44;
}

.student-kp-page__workflow {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.student-kp-page__workflow-card {
  display: grid;
  gap: 6px;
  text-align: left;
  cursor: pointer;
}

.student-kp-page__workflow-card.active {
  border-color: #9fbef3;
  background: linear-gradient(165deg, #f7faff 0%, #eef4ff 100%);
}

.student-kp-page__workflow-card.disabled {
  opacity: 0.6;
}

.student-kp-page__workflow-card strong,
.student-kp-page__task-head h2,
.student-kp-page__chapter-head h3,
.student-kp-page__info-card h3,
.student-kp-page__next-card h3,
.student-kp-page__side-card h3 {
  color: #1f2a44;
}

.student-kp-page__task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.student-kp-page__task-copy,
.student-kp-page__chapter-head,
.student-kp-page__progress,
.student-kp-page__next-card {
  display: grid;
  gap: 10px;
}

.student-kp-page__task-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.student-kp-page__progress-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  color: #5d6d84;
  font-weight: 700;
}

.student-kp-page__chapter-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.student-kp-page__chapter-list,
.student-kp-page__tag-list,
.student-kp-page__checklist {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.student-kp-page__chapter-chip,
.student-kp-page__tag-list button,
.student-kp-page__checklist span {
  border-radius: 999px;
  border: 1px solid #dbe5f2;
  background: #f8fbff;
  color: #36506f;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
}

.student-kp-page__chapter-chip.active,
.student-kp-page__checklist span.done {
  border-color: #8ab39a;
  background: #eaf8f0;
  color: #2f6e49;
}

.student-kp-page__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
}

.student-kp-page__main {
  display: grid;
  gap: 18px;
}

.student-kp-page__panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.student-kp-page__card :deep(.el-card__header) {
  padding: 18px 20px 14px;
  border-bottom: 1px solid #e8eef6;
  font-weight: 800;
  color: #264160;
}

.student-kp-page__card :deep(.el-card__body) {
  padding: 18px 20px 20px;
}

.student-kp-page__empty {
  color: #8ea1ba;
  font-size: 13px;
  padding: 6px 0;
}

.student-kp-page__link-list,
.student-kp-page__task-list {
  display: grid;
  gap: 10px;
}

.student-kp-page__link-list a {
  text-decoration: none;
  color: #35507f;
  border: 1px solid #dce6f2;
  border-radius: 14px;
  padding: 12px 14px;
  background: #f8fbff;
}

.student-kp-page__task-item {
  border: 1px solid #dfe7f1;
  border-radius: 16px;
  padding: 14px;
  background: #f8fbff;
  display: grid;
  gap: 8px;
}

.student-kp-page__task-item strong {
  color: #2a3e57;
  font-size: 15px;
}

.student-kp-page__task-item a {
  color: #35507f;
  font-size: 13px;
}

.student-kp-page__section {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.student-kp-page__section h3 {
  margin: 0;
  color: #2b4463;
  font-size: 16px;
}

.student-kp-page__bottom-nav {
  justify-content: space-between;
  padding: 14px 16px;
}

.student-kp-page__bottom-hint {
  flex: 1;
  color: #6b809d;
  font-size: 13px;
  line-height: 1.7;
}

.student-kp-page__side {
  display: grid;
  gap: 16px;
  position: sticky;
  top: 18px;
}

.student-kp-page__side-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 1180px) {
  .student-kp-page__stats,
  .student-kp-page__workflow,
  .student-kp-page__panel-grid,
  .student-kp-page__content {
    grid-template-columns: 1fr;
  }

  .student-kp-page__task-card,
  .student-kp-page__chapter-head,
  .student-kp-page__hero {
    display: grid;
    grid-template-columns: 1fr;
  }

  .student-kp-page__side {
    position: static;
  }
}

@media (max-width: 768px) {
  .student-kp-page {
    padding: 16px 14px 24px;
  }

  .student-kp-page__hero-copy {
    flex-direction: column;
  }

  .student-kp-page__hero-actions,
  .student-kp-page__task-actions,
  .student-kp-page__chapter-actions,
  .student-kp-page__bottom-nav {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
