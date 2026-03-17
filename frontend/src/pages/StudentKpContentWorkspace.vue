<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
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
  overlay?: { blocked_reason?: string | null };
  resource_list: ResourceItem[];
  task_list: TaskItem[];
  practice_list: Array<{ id: number; kp_id: number; type: string; prompt: string; difficulty: number }>;
  prerequisites: RelationNode[];
  downstream: RelationNode[];
  related: RelationNode[];
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
const activeMenu = ref<"resource" | "practice" | "recommend">("resource");
const detail = ref<NodeDetail | null>(null);
const reco = ref<RecoData | null>(null);
const lastRecommendedTargetId = ref<number | null>(null);
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

function goBack() {
  router.push({
    path: "/student/graph-workspace",
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      kp: kpId.value ? String(kpId.value) : undefined,
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
    activeMenu.value = "resource";
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

async function loadDetail() {
  if (!kpId.value) return;
  loading.value = true;
  try {
    const res = await api.get(`/graph/node/${kpId.value}`);
    detail.value = res.data;
    const blockedReason = res.data?.overlay?.blocked_reason;
    if (blockedReason) {
      ElMessage.warning(blockedReason);
      goBack();
      return;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载学习内容失败");
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
  await loadRecommendation();
});

watch(kpId, () => {
  closureState.resourceDone = false;
  closureState.practiceDone = false;
  loadDetail();
  loadRecommendation();
});
</script>

<template>
  <div class="student-content-page" v-loading="loading">
    <div class="student-content-page__toolbar">
      <div class="student-content-page__left">
        <button class="student-content-page__back" @click="goBack">返回图谱</button>
        <div>
          <h1 class="student-content-page__title">知识点学习内容</h1>
          <p class="student-content-page__subtitle">把资源、练习和推荐内容集中在一个页面学习。</p>
        </div>
      </div>
      <div class="student-content-page__chips" v-if="detail?.kp">
        <span>{{ detail.kp.code }}</span>
        <strong>{{ detail.kp.title }}</strong>
        <small>{{ detail.kp.chapter || "未分章" }}</small>
      </div>
    </div>

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
      <button class="student-content-reco__btn" @click="goToRecommendedTarget">
        {{ recommendationContext.isCurrentTarget ? "继续学习当前推荐点" : "跳到系统推荐点" }}
      </button>
    </section>

    <section v-if="recommendationContext" class="student-content-closure">
      <div class="student-content-closure__main">
        <div class="student-content-closure__eyebrow">推荐链路最后收口</div>
        <div class="student-content-closure__title">
          已完成 {{ closureDoneCount }}/3 项
          <span v-if="closureReady"> · 可以收口并进入下一步</span>
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

    <div class="student-content-layout">
      <aside class="student-content-menu">
        <button class="student-content-menu__item" :class="{ active: activeMenu === 'resource' }" @click="activeMenu = 'resource'">
          学习资源
        </button>
        <button class="student-content-menu__item" :class="{ active: activeMenu === 'practice' }" @click="activeMenu = 'practice'">
          练习题
        </button>
        <button class="student-content-menu__item" :class="{ active: activeMenu === 'recommend' }" @click="activeMenu = 'recommend'">
          推荐资源
        </button>
      </aside>

      <main class="student-content-main">
        <template v-if="activeMenu === 'resource'">
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
          v-else-if="activeMenu === 'practice'"
          :kp-id="kpId"
          :preview="isPreview"
          @mastery-updated="handlePracticeUpdated"
        />

        <el-card v-else shadow="never" class="student-content-card">
          <template #header>推荐资源与拓展</template>
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
        </el-card>
      </main>
    </div>
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

.student-content-page__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 20px;
  border: 1px solid var(--app-border);
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
}

.student-content-page__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.student-content-page__back {
  border: 0;
  border-radius: 999px;
  background: #f4f7fb;
  color: #39506d;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--app-border);
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.student-content-page__title {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: #243449;
}

.student-content-page__subtitle {
  margin: 4px 0 0;
  color: #6e8097;
  font-size: 13px;
}

.student-content-page__chips {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: 999px;
  background: #fafbfd;
  border: 1px solid var(--app-border);
  color: #314661;
}

.student-content-page__chips span {
  font-size: 12px;
  color: #6782a7;
  font-weight: 700;
}

.student-content-page__chips strong {
  font-size: 16px;
  color: #1f3249;
}

.student-content-page__chips small {
  font-size: 12px;
  color: #718097;
}

.student-content-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
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

.student-content-layout {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 16px;
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
  border-radius: 10px;
  background: #ffffff;
  color: #3c587d;
  min-height: 40px;
  padding: 0 12px;
  text-align: left;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  line-height: 1.2;
}

.student-content-menu__item.active {
  border-color: #a8c5f8;
  background: #f4f7fb;
  color: #22549b;
}

.student-content-main {
  min-width: 0;
}

.student-content-card {
  border-radius: 16px;
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

  .student-content-layout {
    grid-template-columns: 1fr;
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

  .student-content-menu {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
