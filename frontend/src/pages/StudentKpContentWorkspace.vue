<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import ResourcePane from "../components/ResourcePane.vue";
import QuizPane from "../components/QuizPane.vue";
import StudentKpHeader from "../components/StudentKpHeader.vue";
import StudentKpStepTabs from "../components/StudentKpStepTabs.vue";

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
  tags?: string;
  preview_type?: string;
  preview_status?: string;
  preview_error?: string;
  converted_preview_url?: string;
  original_file_url?: string;
  detected_resource_type?: string;
  original_file_name?: string;
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
  recommendation_stage?: string;
  recommendation_stage_label?: string;
  advice_text: string;
  persona_label?: string;
  persona_strategy_tag?: string;
};

const route = useRoute();
const router = useRouter();

const loading = ref(false);
type WorkspaceView = "overview" | "resource" | "practice" | "review" | "next";
const activeView = ref<WorkspaceView>("overview");
const workflowSteps: WorkspaceView[] = ["overview", "resource", "practice", "review", "next"];
type QuizSubView = "practice" | "records" | "wrong" | "review";
const quizSubViewFromPath = computed<QuizSubView | null>(() => {
  const p = String(route.path || "");
  if (p.endsWith(`/practice`)) return "practice";
  if (p.endsWith(`/records`)) return "records";
  if (p.endsWith(`/wrong`)) return "wrong";
  if (p.endsWith(`/review`)) return "review";
  return null;
});
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
const graphView = computed(() => {
  const v = String(route.query.view || "");
  return v === "path" || v === "reco" || v === "map" ? v : "map";
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

watch(
  () => quizSubViewFromPath.value,
  (v: QuizSubView | null) => {
    // 当进入题库子路由时，自动聚焦对应工作流视图
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

const canEnterNextStep = computed(() => closureReady.value);
const stepLabelMap: Record<WorkspaceView, string> = {
  overview: "学习总览",
  resource: "资源学习",
  practice: "练习作答",
  review: "错题复盘",
  next: "下一步建议",
};
const nextStepDisabledReason = computed(() => {
  if (canEnterNextStep.value) return "";
  const todos: string[] = [];
  if (!closureState.resourceDone) todos.push("完成资源学习");
  if (!closureState.practiceDone) todos.push("完成练习提交");
  return `进入“下一步建议”前，请先${todos.join("、")}。`;
});

function getStepDisabled(view: WorkspaceView) {
  return view === "next" ? !canEnterNextStep.value : false;
}

function goPrevView() {
  const idx = workflowSteps.indexOf(activeView.value);
  if (idx <= 0) return;
  switchView(workflowSteps[idx - 1]);
}

function goNextView() {
  const idx = workflowSteps.indexOf(activeView.value);
  if (idx < 0 || idx >= workflowSteps.length - 1) return;
  const next = workflowSteps[idx + 1];
  if (getStepDisabled(next)) {
    if (nextStepDisabledReason.value) ElMessage.warning(nextStepDisabledReason.value);
    return;
  }
  switchView(next);
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

function handleQuizViewChange(v: QuizSubView) {
  activeView.value = v === "practice" ? "practice" : "review";
  goQuizSubView(v);
}

const masterySummary = computed(() => {
  const o = detail.value?.overlay;
  if (!o || o.mastery == null) return "";
  const pct = Math.round(Number(o.mastery) * 100);
  const raw = String(o.status || "").toLowerCase();
  const map: Record<string, string> = {
    mastered: "已掌握",
    learning: "学习中",
    in_progress: "学习中",
    not_started: "未学习",
    risk: "待巩固",
  };
  const label = map[raw] || o.status || "";
  return label ? `掌握度 ${pct}% · ${label}` : `掌握度 ${pct}%`;
});

function goBack() {
  router.push({
    path: "/student/graph-workspace",
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
    path: `/student/kp-content/${id}`,
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
  const targetPath = `/student/kp-content/${kpId.value}/${view === "practice" ? "practice" : view}`;
  const currentPath = String(router.currentRoute.value?.path || "");
  if (currentPath === targetPath) return;
  router
    .push({
      path: targetPath,
      query: {
        subject: subject.value || undefined,
        grade: grade.value || undefined,
        preview: isPreview.value ? "1" : undefined,
      },
    })
    .catch(() => {});
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
      return;
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
  <div class="student-content-page" v-loading="loading">
    <StudentKpHeader
      title="知识点学习"
      subtitle="按顺序完成资源学习、练习作答和错题复盘，最后再看下一步建议。"
      hint="这里的“练习题”是题库逐题作答，会直接影响掌握度和学习报告。"
      :code="detail?.kp?.code"
      :kp-title="detail?.kp?.title"
      :chapter="detail?.kp?.chapter"
      :mastery-summary="masterySummary"
      @back="goBack"
    />

    <section v-if="navigation" class="student-content-nav-card">
      <div class="student-content-nav-card__head">
        <div>
          <strong>知识点导航</strong>
          <span>当前位于 {{ navigation.chapter || detail?.kp.chapter || "未分章" }}</span>
        </div>
        <div class="student-content-nav-card__actions">
          <button class="student-content-page__back" :disabled="!navigation.previous" @click="navigation.previous && goToKp(navigation.previous.id)">
            上一个知识点
          </button>
          <button class="student-content-reco__btn" :disabled="!navigation.next" @click="navigation.next && goToKp(navigation.next.id)">
            下一个知识点
          </button>
        </div>
      </div>
      <div class="student-content-nav-card__list">
        <button
          v-for="item in navigation.chapter_nodes"
          :key="item.id"
          class="student-content-nav-card__node"
          :class="{ active: item.id === kpId }"
          @click="goToKp(item.id)"
        >
          {{ item.title }}
        </button>
      </div>
    </section>

    <section class="student-content-overview">
      <div class="student-content-overview__item">
        <span>学习资源</span>
        <strong>{{ stats.learning }}</strong>
      </div>
      <div class="student-content-overview__item">
        <span>练习题</span>
        <strong>{{ stats.practice }}</strong>
      </div>
      <div class="student-content-overview__item">
        <span>推荐内容</span>
        <strong>{{ stats.recommend }}</strong>
      </div>
    </section>

    <StudentKpStepTabs
      :active-view="activeView"
      :next-disabled="getStepDisabled('next')"
      :next-disabled-reason="nextStepDisabledReason"
      @switch="switchView"
    />

    <main class="student-content-main">
      <template v-if="activeView === 'overview'">
        <section v-if="recommendationContext" class="student-content-reco">
          <div class="student-content-reco__main">
            <div class="student-content-reco__eyebrow">知识图谱推荐</div>
            <div class="student-content-reco__title">
              {{ recommendationContext.label }}
              <span v-if="recommendationContext.isCurrentTarget"> · 当前正在学习推荐点</span>
            </div>
            <p class="student-content-reco__text">{{ recommendationContext.reason }}</p>
            <p class="student-content-reco__text">{{ recommendationContext.advice }}</p>
          </div>
          <button class="student-content-reco__btn" @click="switchView('resource')">进入资源学习</button>
        </section>

        <section class="student-content-closure">
          <div class="student-content-closure__main">
            <div class="student-content-closure__eyebrow">学习进度</div>
            <div class="student-content-closure__title">
              已完成 {{ closureDoneCount }}/2 项
              <span v-if="closureReady"> · 可进入下一步建议</span>
            </div>
            <div class="student-content-closure__checks">
              <span :class="{ done: closureState.resourceDone }">资源学习</span>
              <span :class="{ done: closureState.practiceDone }">练习提交</span>
            </div>
          </div>
          <div class="student-content-closure__actions">
            <button class="student-content-page__back" @click="switchView('resource')">先学资源</button>
            <button class="student-content-reco__btn" @click="switchView('practice')">去做练习</button>
          </div>
        </section>
      </template>

      <template v-else-if="activeView === 'resource'">
          <el-card v-if="isPreview" shadow="never" class="student-content-card">
            <template #header>学习资源（预览模式）</template>
            <div v-if="learningResources.length === 0" class="student-content-empty">当前知识点还没有学习资源</div>
            <div v-else class="student-content-links">
              <a v-for="item in learningResources" :key="item.id" :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
            </div>
          </el-card>
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

        <el-card v-else shadow="never" class="student-content-card">
          <template #header>推荐资源与拓展</template>
          <section v-if="recommendationContext" class="student-content-reco student-content-reco--inner">
            <div class="student-content-reco__main">
              <div class="student-content-reco__eyebrow">推荐说明</div>
              <div class="student-content-reco__title">
                {{ recommendationContext.label }}
                <span v-if="recommendationContext.isCurrentTarget"> · 当前点位即推荐目标</span>
              </div>
              <p class="student-content-reco__text">{{ recommendationContext.reason }}</p>
              <p class="student-content-reco__text">{{ recommendationContext.advice }}</p>
            </div>
            <button class="student-content-reco__btn" @click="goToRecommendedTarget">
              {{ recommendationContext.isCurrentTarget ? "继续学习当前推荐点" : "跳到系统推荐点" }}
            </button>
          </section>

          <div class="student-content-section">
            <h3>推荐资源</h3>
            <div v-if="recommendedResources.length === 0" class="student-content-empty">暂无推荐资源</div>
            <div v-else class="student-content-links">
              <a v-for="item in recommendedResources" :key="item.id" :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a>
            </div>
          </div>

          <div class="student-content-section">
            <h3>学习任务</h3>
            <div v-if="(detail?.task_list?.length ?? 0) === 0" class="student-content-empty">暂无学习任务</div>
            <div v-else class="student-content-task-list">
              <div v-for="task in detail?.task_list ?? []" :key="task.id" class="student-content-task">
                <strong>{{ task.title }}</strong>
                <p>{{ task.description || "暂无任务描述" }}</p>
                <a v-if="task.link_url" :href="task.link_url" target="_blank" rel="noreferrer">打开任务链接</a>
              </div>
            </div>
          </div>

          <div class="student-content-section">
            <h3>相关知识点</h3>
            <div class="student-content-tags">
              <button v-for="item in detail?.prerequisites ?? []" :key="`pre-${item.id}`" @click="goToKp(item.id)">
                前置：{{ item.title }}
              </button>
              <button v-for="item in detail?.downstream ?? []" :key="`next-${item.id}`" @click="goToKp(item.id)">
                后续：{{ item.title }}
              </button>
              <button v-for="item in detail?.related ?? []" :key="`rel-${item.id}`" @click="goToKp(item.id)">
                关联：{{ item.title }}
              </button>
            </div>
          </div>

          <section class="student-content-closure student-content-closure--inner">
            <div class="student-content-closure__main">
              <div class="student-content-closure__eyebrow">学习收口</div>
              <div class="student-content-closure__title">
                已完成 {{ closureDoneCount }}/2 项
                <span v-if="closureReady"> · 建议进入下一推荐知识点</span>
              </div>
              <div class="student-content-closure__checks">
                <span :class="{ done: closureState.resourceDone }">资源学习</span>
                <span :class="{ done: closureState.practiceDone }">练习提交</span>
              </div>
            </div>
            <div class="student-content-closure__actions">
              <button class="student-content-page__back" @click="goToRecommendedTarget">前往下一推荐</button>
              <button class="student-content-reco__btn" @click="goToReport">回到学习报告</button>
            </div>
          </section>
        </el-card>

      <section class="student-content-step-nav">
        <button class="student-content-page__back" :disabled="activeView === 'overview'" @click="goPrevView">
          上一步
        </button>
        <div class="student-content-step-nav__hint">
          <span v-if="activeView === 'next'">已到最后一步，可选择前往推荐知识点或回学习报告。</span>
          <span v-else-if="nextView === 'next' && !canEnterNextStep">
            {{ nextStepDisabledReason }}
          </span>
          <span v-else>按流程推进可减少操作分散：总览 → 资源 → 练习 → 复盘 → 下一步。</span>
        </div>
        <button
          class="student-content-reco__btn"
          :disabled="activeView === 'next' || (nextView === 'next' && !canEnterNextStep)"
          @click="goNextView"
        >
          {{ nextButtonText }}
        </button>
      </section>
    </main>
  </div>
</template>

<style scoped>
.student-content-page {
  min-height: 100vh;
  padding: 16px;
  background: var(--app-bg);
  display: grid;
  gap: 16px;
}

.student-content-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.student-content-nav-card {
  border-radius: 18px;
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
  padding: 16px 18px;
  display: grid;
  gap: 14px;
}

.student-content-nav-card__head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.student-content-nav-card__head strong {
  display: block;
  color: #23405f;
  font-size: 16px;
}

.student-content-nav-card__head span {
  display: block;
  margin-top: 4px;
  color: #6d819c;
  font-size: 12px;
}

.student-content-nav-card__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.student-content-nav-card__list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.student-content-nav-card__node {
  border: 1px solid #dbe5f2;
  background: #f8fbff;
  color: #3d5775;
  border-radius: 999px;
  min-height: 36px;
  padding: 0 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.student-content-nav-card__node.active {
  border-color: #7ea7f0;
  background: #edf4ff;
  color: #27476a;
}

.student-content-overview__item {
  border-radius: 16px;
  border: 1px solid var(--app-border);
  background: #ffffff;
  padding: 16px;
  display: grid;
  gap: 6px;
  box-shadow: var(--app-shadow-soft);
}

.student-content-overview__item span {
  font-size: 13px;
  color: #687d98;
}

.student-content-overview__item strong {
  font-size: 22px;
  color: #29415f;
}

.student-content-reco {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  border-radius: 16px;
  border: 1px solid var(--app-border);
  background: #ffffff;
  padding: 16px 18px;
  box-shadow: var(--app-shadow-soft);
}

.student-content-reco__main {
  display: grid;
  gap: 6px;
}

.student-content-reco__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #6d83a6;
  text-transform: uppercase;
}

.student-content-reco__title {
  font-size: 17px;
  font-weight: 800;
  color: #264160;
}

.student-content-reco__text {
  margin: 0;
  color: #667b98;
  font-size: 13px;
}

.student-content-reco__btn {
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: #f7f9fc;
  color: #39506d;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.student-content-closure {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  border-radius: 16px;
  border: 1px solid #dbe7df;
  background: #ffffff;
  padding: 16px 18px;
  box-shadow: var(--app-shadow-soft);
}

.student-content-closure__main {
  display: grid;
  gap: 8px;
}

.student-content-closure__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #5f856f;
  text-transform: uppercase;
}

.student-content-closure__title {
  font-size: 18px;
  font-weight: 800;
  color: #28473a;
}

.student-content-closure__checks {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.student-content-closure__checks span {
  border-radius: 999px;
  border: 1px solid #cfe2d5;
  padding: 6px 12px;
  color: #5c7569;
  font-size: 12px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.8);
}

.student-content-closure__checks span.done {
  border-color: #7cb592;
  color: #256145;
  background: #e9f6ee;
}

.student-content-closure__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.student-content-menu {
  border-radius: 16px;
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
  padding: 12px;
  display: grid;
  gap: 8px;
  align-content: start;
}

.student-content-menu__item {
  border: 1px solid #dce6f2;
  border-radius: 14px;
  background: #ffffff;
  color: #3c587d;
  min-height: 58px;
  padding: 12px;
  text-align: left;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 10px;
  line-height: 1.2;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.student-content-menu__item.active {
  border-color: #a8c5f8;
  background: linear-gradient(165deg, #f5f9ff 0%, #eef4fc 100%);
  color: #22549b;
  box-shadow: 0 10px 24px rgba(47, 111, 237, 0.08);
}

.student-content-menu__item:hover {
  border-color: #c8d7e7;
  background: #ffffff;
}

.student-content-menu__hint {
  margin: 0 6px -2px;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a5b8;
}

.student-content-menu__icon {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dbe4ef;
  display: grid;
  place-items: center;
  color: #5c7cb2;
}

.student-content-menu__text {
  font-size: 15px;
}

.student-content-menu__count {
  font-size: 12px;
  font-weight: 900;
  color: var(--app-primary);
  background: color-mix(in srgb, var(--app-primary) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--app-primary) 30%, var(--app-border));
  padding: 3px 8px;
  border-radius: 999px;
}

.student-content-menu__done {
  grid-column: 1 / -1;
  display: inline-flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-start;
  margin-top: 6px;
  color: #2f7a47;
  font-weight: 900;
  font-size: 12px;
}

.student-content-main {
  min-width: 0;
  display: grid;
  gap: 12px;
}

.student-content-step-nav {
  position: sticky;
  bottom: 12px;
  z-index: 2;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--app-border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(3px);
  box-shadow: var(--app-shadow-soft);
  padding: 10px 12px;
}

.student-content-step-nav__hint {
  color: #6b809d;
  font-size: 12px;
}

.student-content-card {
  border-radius: 16px;
}

.student-content-reco--inner {
  margin-bottom: 12px;
}

.student-content-closure--inner {
  margin-top: 12px;
}

.student-content-empty {
  color: #8ea1ba;
  font-size: 13px;
}

.student-content-section {
  margin-bottom: 18px;
}

.student-content-section h3 {
  margin: 0 0 8px;
  color: #2b4463;
  font-size: 14px;
}

.student-content-links {
  display: grid;
  gap: 8px;
}

.student-content-links a {
  text-decoration: none;
  color: #35507f;
  border: 1px solid #dce6f2;
  border-radius: 10px;
  padding: 10px 12px;
  background: #f8fbff;
}

.student-content-links a:hover {
  background: #eef5ff;
}

.student-content-task-list {
  display: grid;
  gap: 8px;
}

.student-content-task {
  border: 1px solid #dce6f2;
  border-radius: 12px;
  padding: 12px;
  background: #ffffff;
}

.student-content-task strong {
  font-size: 14px;
  color: #2a3e57;
}

.student-content-task p {
  margin: 6px 0;
  color: #617792;
  font-size: 13px;
}

.student-content-task a {
  color: #35507f;
  font-size: 13px;
}

.student-content-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.student-content-tags button {
  border: 1px solid #cdddf4;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  color: #35507f;
  background: #eef5ff;
  cursor: pointer;
}

@media (max-width: 1080px) {
  .student-content-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .student-content-reco {
    grid-template-columns: 1fr;
    align-items: start;
    display: grid;
  }

  .student-content-closure {
    grid-template-columns: 1fr;
    align-items: start;
    display: grid;
  }

  .student-content-step-nav {
    position: static;
    grid-template-columns: 1fr;
  }

}
</style>
