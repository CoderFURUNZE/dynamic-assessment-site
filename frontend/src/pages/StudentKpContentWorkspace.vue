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
  is_terminal?: boolean;
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
  student_message?: string;
  teacher_explanation?: string;
  recommendation_source?: string;
  personalized_path?: Array<{ kp_id?: number; id?: number; title?: string; action?: string }>;
  ai_enhanced?: Record<string, any>;
  course_completion?: { enabled?: boolean; completed?: boolean; completed_terminal_title?: string };
};

type WorkspaceView = "overview" | "resource" | "practice" | "review" | "next";
type QuizSubView = "practice" | "records" | "wrong" | "review";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const activeView = ref<WorkspaceView>("practice");
const workflowSteps: WorkspaceView[] = ["practice", "next"];
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
    advice: reco.value.student_message || reco.value.advice_text,
  };
});
const personalizedPathItems = computed(() => {
  const raw = Array.isArray(reco.value?.personalized_path) ? reco.value?.personalized_path ?? [] : [];
  const items = raw
    .map((item, index) => {
      const id = Number(item.kp_id ?? item.id ?? 0);
      const title = String(item.title || "").trim();
      const action = String(item.action || "").trim();
      if (!id && !title) return null;
      return {
        id,
        title: title || (id ? `知识点 ${id}` : `路径节点 ${index + 1}`),
        action,
      };
    })
    .filter((item): item is { id: number; title: string; action: string } => Boolean(item));
  if (items.length > 0) return items;
  const target = reco.value?.target_kp;
  return target?.id ? [{ id: Number(target.id), title: target.title, action: "进入系统推荐知识点" }] : [];
});
const recommendationSourceLabel = computed(() => (reco.value?.recommendation_source === "bailian" ? "百炼增强" : "规则推荐"));
const courseCompleted = computed(() => Boolean(reco.value?.course_completion?.completed));

const closureDoneCount = computed(() => [closureState.resourceDone, closureState.practiceDone].filter(Boolean).length);
const stats = computed(() => ({
  learning: learningResources.value.length,
  practice: detail.value?.practice_list?.length ?? 0,
  recommend: recommendedResources.value.length + (detail.value?.task_list?.length ?? 0),
}));
const navigation = computed(() => detail.value?.navigation ?? null);
const masteryPercent = computed(() => Math.round(Number(detail.value?.overlay?.mastery ?? 0) * 100));
const closureReady = computed(() => masteryPercent.value >= 70);
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
const currentTaskSubtitle = computed(() => detail.value?.kp?.title || "当前知识点");
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
    const res = await api.get("/reco", {
      params: { kp_id: kpId.value, ai: false },
      skipGlobalLoading: true,
    } as any);
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

      <div class="student-kp-page__hero-progress" :style="{ '--mastery': `${masteryPercent}%` }">
        <strong>{{ masteryPercent }}%</strong>
        <span>{{ masteryStatus }}</span>
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
            <span class="student-kp-page__section-eyebrow">推荐说明 · {{ recommendationSourceLabel }}</span>
            <h3>{{ recommendationContext.label }}</h3>
            <p>{{ recommendationContext.reason }}</p>
            <p>{{ recommendationContext.advice }}</p>
            <p v-if="courseCompleted" class="student-kp-page__complete-note">
              已完成终点知识点“{{ reco?.course_completion?.completed_terminal_title || reco?.target_kp?.title }}”，课程已达标，可进入学习报告查看评分结果。
            </p>
            <div v-if="personalizedPathItems.length" class="student-kp-page__path-list">
              <button
                v-for="(item, index) in personalizedPathItems"
                :key="`${item.id || item.title}-${index}`"
                class="student-kp-page__path-item"
                type="button"
                :disabled="!item.id"
                @click="item.id && goToKp(item.id)"
              >
                <span>{{ index + 1 }}</span>
                <strong>{{ item.title }}</strong>
                <small>{{ item.action || (index === 0 ? "优先学习" : "继续推进") }}</small>
              </button>
            </div>
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
            <span class="student-kp-page__section-eyebrow">推荐学习 · {{ recommendationSourceLabel }}</span>
            <h3>{{ recommendationContext.label }}</h3>
            <p>{{ recommendationContext.reason }}</p>
            <p>{{ recommendationContext.advice }}</p>
            <p v-if="courseCompleted" class="student-kp-page__complete-note">
              课程已达标，可进入学习报告查看评分结果。
            </p>
            <div v-if="personalizedPathItems.length" class="student-kp-page__path-list student-kp-page__path-list--compact">
              <button
                v-for="(item, index) in personalizedPathItems"
                :key="`${item.id || item.title}-${index}`"
                class="student-kp-page__path-item"
                type="button"
                :disabled="!item.id"
                @click="item.id && goToKp(item.id)"
              >
                <span>{{ index + 1 }}</span>
                <strong>{{ item.title }}</strong>
                <small>{{ item.action || "学习路径节点" }}</small>
              </button>
            </div>
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
  min-height: calc(100vh - 96px);
  max-width: 1320px;
  margin: 0 auto;
  padding: 18px 20px 32px;
  display: grid;
  gap: 14px;
  min-width: 0;
  color: #102033;
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
  border-radius: 8px;
  border: 1px solid #dbe4ee;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  min-width: 0;
  max-width: 100%;
}

.student-kp-page__hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 118px auto;
  align-items: center;
  gap: 20px;
  padding: 24px;
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.96) 0%, rgba(255, 255, 255, 0.98) 50%, rgba(240, 253, 244, 0.9) 100%),
    #ffffff;
}

.student-kp-page__hero-copy {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.student-kp-page__hero-text {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.student-kp-page__back,
.student-kp-page__btn {
  min-height: 40px;
  padding: 0 18px;
  border-radius: 8px;
  border: 1px solid #d7e0ea;
  background: #ffffff;
  color: #243449;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.student-kp-page__back {
  align-self: flex-start;
  white-space: nowrap;
}

.student-kp-page__back:hover,
.student-kp-page__btn:hover:not(:disabled) {
  border-color: #9fb2c8;
  background: #f8fbff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.student-kp-page__btn:disabled,
.student-kp-page__chapter-chip:disabled {
  cursor: not-allowed;
  opacity: 0.48;
  box-shadow: none;
}

.student-kp-page__eyebrow,
.student-kp-page__section-eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 8px;
  background: #ecfdf3;
  border: 1px solid #b9ebc8;
  color: #0f6b2f;
  font-size: 12px;
  font-weight: 900;
}

.student-kp-page__hero-text h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.12;
  color: #102033;
  overflow-wrap: anywhere;
}

.student-kp-page__hero-text p,
.student-kp-page__task-head p,
.student-kp-page__chapter-head p,
.student-kp-page__info-card p,
.student-kp-page__side-card p,
.student-kp-page__next-card p,
.student-kp-page__task-item p {
  margin: 0;
  color: #5e6e82;
  line-height: 1.65;
}

.student-kp-page__hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.student-kp-page__hero-meta span,
.student-kp-page__task-code,
.student-kp-page__status-pill {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 8px;
  background: #f6f9fc;
  color: #334155;
  border: 1px solid #dbe4ee;
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

.student-kp-page__hero-actions {
  justify-content: flex-end;
}

.student-kp-page__hero-progress {
  width: 104px;
  height: 104px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  align-content: center;
  background:
    radial-gradient(circle at center, #ffffff 0 56%, transparent 57%),
    conic-gradient(#22c55e var(--mastery), #dce7f2 0);
  color: #102033;
  box-shadow: inset 0 0 0 1px #dbe4ee, 0 12px 26px rgba(34, 197, 94, 0.16);
}

.student-kp-page__hero-progress strong {
  font-size: 25px;
  line-height: 1;
}

.student-kp-page__hero-progress span {
  color: #5e6e82;
  font-size: 12px;
  font-weight: 800;
}

.student-kp-page__btn--primary {
  border-color: #16a34a;
  background: #18b957;
  color: #ffffff;
  box-shadow: 0 10px 20px rgba(24, 185, 87, 0.22);
}

.student-kp-page__btn--primary:hover:not(:disabled) {
  background: #129447;
  border-color: #129447;
  color: #ffffff;
}

.student-kp-page__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  min-width: 0;
}

.student-kp-page__stat-card,
.student-kp-page__workflow-card,
.student-kp-page__task-card,
.student-kp-page__chapter-nav,
.student-kp-page__info-card,
.student-kp-page__side-card {
  padding: 18px;
  background: #ffffff;
}

.student-kp-page__stat-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "label value"
    "hint value";
  gap: 4px 12px;
  align-items: center;
  border-left: 4px solid #60a5fa;
}

.student-kp-page__stat-card:nth-child(2) {
  border-left-color: #22c55e;
}

.student-kp-page__stat-card:nth-child(3) {
  border-left-color: #f59e0b;
}

.student-kp-page__stat-card:nth-child(4) {
  border-left-color: #8b5cf6;
}

.student-kp-page__stat-card span,
.student-kp-page__stat-card small,
.student-kp-page__workflow-card span,
.student-kp-page__workflow-card small,
.student-kp-page__side-metrics small {
  color: #5e6e82;
  font-size: 13px;
}

.student-kp-page__stat-card span {
  grid-area: label;
  font-weight: 900;
}

.student-kp-page__stat-card small {
  grid-area: hint;
}

.student-kp-page__stat-card strong,
.student-kp-page__side-metrics strong {
  font-size: 30px;
  line-height: 1.1;
  color: #102033;
}

.student-kp-page__stat-card strong {
  grid-area: value;
}

.student-kp-page__workflow {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  min-width: 0;
  padding: 6px;
  border-radius: 8px;
  border: 1px solid #dbe4ee;
  background: #f6f9fc;
}

.student-kp-page__workflow-card {
  display: grid;
  gap: 4px;
  text-align: left;
  cursor: pointer;
  border: 1px solid transparent;
  background: transparent;
  box-shadow: none;
  padding: 13px 14px;
  transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.student-kp-page__workflow-card.active {
  border-color: #b9ebc8;
  background: #ffffff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
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
  color: #102033;
  overflow-wrap: anywhere;
}

.student-kp-page__task-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 18px;
  padding: 22px;
  border-top: 4px solid #2563eb;
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
  flex-wrap: wrap;
  min-width: 0;
}

.student-kp-page__task-head h2,
.student-kp-page__chapter-head h3,
.student-kp-page__info-card h3,
.student-kp-page__next-card h3,
.student-kp-page__side-card h3 {
  margin: 0;
}

.student-kp-page__progress-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  color: #5e6e82;
  font-weight: 800;
}

.student-kp-page__chapter-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
  min-width: 0;
}

.student-kp-page__chapter-list,
.student-kp-page__tag-list,
.student-kp-page__checklist {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}

.student-kp-page__chapter-chip,
.student-kp-page__tag-list button,
.student-kp-page__checklist span {
  border-radius: 8px;
  border: 1px solid #dbe4ee;
  background: #f8fafc;
  color: #334155;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 800;
}

.student-kp-page__chapter-chip.active,
.student-kp-page__checklist span.done {
  border-color: #b9ebc8;
  background: #ecfdf3;
  color: #0f6b2f;
}

.student-kp-page__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 18px;
  align-items: start;
  min-width: 0;
}

.student-kp-page__side {
  min-width: 0;
}

.student-kp-page__main {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.student-kp-page__panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-width: 0;
}

.student-kp-page__card :deep(.el-card__header) {
  padding: 18px 20px 14px;
  border-bottom: 1px solid #e6edf5;
  font-weight: 800;
  color: #102033;
  background: #f8fbff;
}

.student-kp-page__card :deep(.el-card__body) {
  padding: 18px 20px 20px;
}

.student-kp-page__empty {
  color: #5e6e82;
  font-size: 13px;
  padding: 6px 0;
}

.student-kp-page__link-list,
.student-kp-page__task-list {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.student-kp-page__path-list {
  display: grid;
  gap: 8px;
  margin: 4px 0;
  min-width: 0;
}

.student-kp-page__path-list--compact {
  gap: 6px;
}

.student-kp-page__path-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 2px 10px;
  align-items: center;
  text-align: left;
  border: 1px solid #c9ead4;
  border-radius: 8px;
  background: #f7fdf9;
  padding: 11px 12px;
  color: #102033;
  cursor: pointer;
  min-width: 0;
}

.student-kp-page__path-item:hover:not(:disabled) {
  border-color: #22c55e;
  background: #ecfdf3;
}

.student-kp-page__path-item:disabled {
  cursor: default;
}

.student-kp-page__path-item span {
  grid-row: span 2;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #16a34a;
  color: #ffffff;
  font-size: 12px;
  font-weight: 800;
}

.student-kp-page__path-item strong,
.student-kp-page__path-item small {
  overflow-wrap: anywhere;
}

.student-kp-page__path-item small {
  color: #5e6e82;
  font-size: 12px;
}

.student-kp-page__complete-note {
  border: 1px solid #b9ebc8;
  border-radius: 8px;
  background: #ecfdf3;
  color: #0f6b2f;
  padding: 10px 12px;
  font-weight: 700;
}

.student-kp-page__link-list a {
  text-decoration: none;
  color: #243449;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  padding: 12px 14px;
  background: #ffffff;
  overflow-wrap: anywhere;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.student-kp-page__link-list a:hover {
  border-color: #93c5fd;
  background: #f8fbff;
}

.student-kp-page__task-item {
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
  display: grid;
  gap: 8px;
  min-width: 0;
}

.student-kp-page__task-item strong {
  color: #102033;
  font-size: 15px;
}

.student-kp-page__task-item a {
  color: #16a34a;
  font-size: 13px;
}

.student-kp-page__section {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.student-kp-page__section h3 {
  margin: 0;
  color: #102033;
  font-size: 16px;
}

.student-kp-page__bottom-nav {
  justify-content: space-between;
  padding: 14px 16px;
}

.student-kp-page__bottom-hint {
  flex: 1;
  color: #5e6e82;
  font-size: 13px;
  line-height: 1.7;
}

.student-kp-page__side {
  display: grid;
  gap: 14px;
  position: sticky;
  top: 18px;
}

.student-kp-page__side-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.student-kp-page__side-metrics div {
  display: grid;
  gap: 4px;
  padding: 12px;
  border-radius: 8px;
  background: #f6f9fc;
  border: 1px solid #e6edf5;
}

.student-kp-page :deep(.el-progress-bar__outer) {
  background-color: #e6edf5;
}

.student-kp-page :deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, #2563eb 0%, #22c55e 100%) !important;
}

.student-kp-page :deep(.quiz-pane),
.student-kp-page :deep(.resource-pane) {
  border-radius: 8px;
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

  .student-kp-page__hero-progress,
  .student-kp-page__hero-actions {
    justify-self: start;
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
    align-items: stretch;
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
