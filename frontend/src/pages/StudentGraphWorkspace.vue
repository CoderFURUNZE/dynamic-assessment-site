<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import KnowledgeGraphWorkspace from "../components/KnowledgeGraphWorkspace.vue";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  active?: boolean;
  enroll_status?: string;
};
type KP = { id: number; code: string; title: string; chapter?: string };
type WorkspaceState = {
  kpCount: number;
  categoryCount: number;
  filteredCount: number;
  selectedType: "kp" | "category";
  selectedKpId: number | null;
  selectedCategory: string | null;
};

type RecoData = {
  target_kp: { id: number; code: string; title: string };
  reason_summary: string;
  advice_text?: string;
};

type PathData = {
  next_candidates: number[];
  next_titles: string[];
  can_unlock_next: boolean;
  blocked_titles: string[];
  path_summary: string;
};

const route = useRoute();
const router = useRouter();

const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);
const reco = ref<RecoData | null>(null);
const pathInfo = ref<PathData | null>(null);
const workspaceState = ref<WorkspaceState>({
  kpCount: 0,
  categoryCount: 0,
  filteredCount: 0,
  selectedType: "kp",
  selectedKpId: null,
  selectedCategory: null,
});

const isStandaloneWorkspace = computed(() => Boolean(route.meta?.standaloneWorkspace));
const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const currentKp = computed(() => kps.value.find((item) => item.id === currentKpId.value) ?? null);

const recommendationLabel = computed(() => reco.value?.target_kp?.title || "继续完成当前知识点");
const currentNodeLabel = computed(() => currentKp.value?.title || "请先在图谱中选择一个知识点");
const currentNodeCode = computed(() => currentKp.value?.code || "--");
const graphLead = computed(() => {
  if (pathInfo.value?.path_summary) return pathInfo.value.path_summary;
  if (reco.value?.reason_summary) return reco.value.reason_summary;
  return "从图谱里选择一个知识点，系统会告诉你下一步该学什么。";
});

const graphOverviewCards = computed(() => [
  {
    label: "知识点数量",
    value: workspaceState.value.kpCount || kps.value.length,
    hint: "当前课程纳入图谱的知识点",
  },
  {
    label: "分类数量",
    value: workspaceState.value.categoryCount,
    hint: "用于组织学习路径的分类层级",
  },
  {
    label: "当前筛选",
    value: workspaceState.value.filteredCount || workspaceState.value.kpCount || kps.value.length,
    hint: "当前视图里可见的节点数量",
  },
]);

const graphStatusText = computed(() => {
  if (!currentKp.value) return "等待选择";
  if (pathInfo.value?.can_unlock_next === false && (pathInfo.value.blocked_titles?.length || 0) > 0) return "需补前置";
  if (reco.value?.target_kp?.id === currentKp.value.id) return "推荐学习";
  return "可继续学习";
});

const blockedSummary = computed(() => {
  if (!pathInfo.value?.blocked_titles?.length) return "当前没有前置阻塞，可以继续推进后续知识点。";
  return `需先补足：${pathInfo.value.blocked_titles.join("、")}`;
});

const nextCandidatesPreview = computed(() => {
  if (!pathInfo.value?.next_titles?.length) return "完成当前知识点后，系统会在这里提示下一步内容。";
  return pathInfo.value.next_titles.slice(0, 3).join("、");
});

const graphPathHint = computed(() => {
  if (!pathInfo.value) return null;
  return {
    next_candidate_ids: pathInfo.value.next_candidates ?? [],
    next_titles: pathInfo.value.next_titles ?? [],
    can_unlock_next: pathInfo.value.can_unlock_next,
    blocked_titles: pathInfo.value.blocked_titles ?? [],
    path_summary: pathInfo.value.path_summary || "",
  };
});

const graphRecoHint = computed(() => {
  if (!reco.value?.target_kp?.id) return null;
  return {
    reason_summary: reco.value.reason_summary,
    advice_text: reco.value.advice_text,
    target_kp_id: reco.value.target_kp.id,
    target_code: reco.value.target_kp.code,
    target_title: reco.value.target_kp.title,
  };
});

function resetWorkspaceState() {
  kps.value = [];
  currentKpId.value = null;
  reco.value = null;
  pathInfo.value = null;
}

function syncQuery() {
  saveStudentSubject(subject.value);
  const preview = String(route.query.preview || "");
  router.replace({
    path: "/student/graph-workspace",
    query: {
      subject: subject.value || undefined,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
      preview: preview || undefined,
    },
  });
}

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    const raw = res.data ?? [];
    courses.value = raw.map((item: any) => ({
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
      active: item.active !== false,
      enroll_status: String(item.enroll_status || ""),
    }));
    const routeSubject = String(route.query.subject || "").trim();
    const titles = new Set(courses.value.map((item) => item.title));
    const nextSubject = routeSubject && !titles.has(routeSubject)
      ? ""
      : resolveStudentSubject(routeSubject, subject.value, courses.value);
    subject.value = nextSubject;
    if (!nextSubject) resetWorkspaceState();
  } catch (e: any) {
    resetWorkspaceState();
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

async function loadKps() {
  if (!subject.value) {
    resetWorkspaceState();
    return;
  }
  try {
    const data = await getWithCache("/graph/kps", { subject: subject.value, grade: grade.value });
    kps.value = Array.isArray(data) ? data : [];
    const routeKp = Number(route.query.kp || 0);
    currentKpId.value = routeKp && kps.value.some((item) => item.id === routeKp) ? routeKp : (kps.value[0]?.id ?? null);
  } catch (e: any) {
    resetWorkspaceState();
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
  }
}

async function loadRecommendation() {
  if (!currentKpId.value) {
    reco.value = null;
    return;
  }
  try {
    const res = await api.get(`/reco?kp_id=${currentKpId.value}`);
    reco.value = res.data ?? null;
  } catch {
    reco.value = null;
  }
}

async function loadPathInfo() {
  if (!currentKpId.value) {
    pathInfo.value = null;
    return;
  }
  try {
    const res = await api.get(`/graph/path/${currentKpId.value}`);
    pathInfo.value = res.data ?? null;
  } catch {
    pathInfo.value = null;
  }
}

async function refreshWorkspace() {
  await loadCourses();
  await loadKps();
  await loadRecommendation();
  await loadPathInfo();
}

async function handleCourseChange() {
  currentKpId.value = null;
  reco.value = null;
  pathInfo.value = null;
  await loadKps();
  await loadRecommendation();
  await loadPathInfo();
  syncQuery();
}

function openStudentKpContent(id: number) {
  router.push({
    path: `/student/kp-content/${id}`,
    query: {
      subject: subject.value || undefined,
      from: "graph-workspace",
    },
  });
}

function openCurrentLearning() {
  if (!currentKpId.value) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  openStudentKpContent(currentKpId.value);
}

function openRecommendedLearning() {
  if (reco.value?.target_kp?.id) {
    openStudentKpContent(reco.value.target_kp.id);
    return;
  }
  openCurrentLearning();
}

function handleSelectKp(id: number) {
  currentKpId.value = id;
}

function handleStateChange(payload: WorkspaceState) {
  workspaceState.value = payload;
}

watch(
  () => route.query.subject,
  async (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) {
      subject.value = next;
      await loadCourses();
      await loadKps();
      await loadRecommendation();
      await loadPathInfo();
    }
  },
);

watch(
  currentKpId,
  async (value, oldValue) => {
    if (value === oldValue) return;
    syncQuery();
    await loadRecommendation();
    await loadPathInfo();
  },
);

onMounted(refreshWorkspace);
</script>

<template>
  <div class="graph-page" :class="{ 'graph-page--standalone': isStandaloneWorkspace }">
    <section class="graph-page__toolbar">
      <div class="graph-page__toolbar-copy">
        <span class="graph-page__eyebrow">学习导航</span>
        <h1>知识图谱</h1>
        <p>{{ currentCourse?.title || "当前没有可学习课程" }}</p>
        <div class="graph-page__toolbar-meta">
          <span>当前知识点：{{ currentNodeCode }}</span>
          <span>学习状态：{{ graphStatusText }}</span>
        </div>
      </div>

      <div class="graph-page__toolbar-actions">
        <el-select
          v-model="subject"
          class="graph-page__select"
          placeholder="选择课程"
          :disabled="courses.length === 0"
          @change="handleCourseChange"
        >
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="graph-page__toolbar-btn" type="button" @click="refreshWorkspace">刷新</button>
        <button class="graph-page__toolbar-btn graph-page__toolbar-btn--primary" type="button" @click="openCurrentLearning">
          去学习
        </button>
      </div>
    </section>

    <section class="graph-page__overview-shell">
      <div class="graph-page__overview">
        <article v-for="item in graphOverviewCards" :key="item.label" class="graph-page__overview-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </article>
      </div>
    </section>

    <section class="graph-page__content">
      <section class="graph-page__workspace">
        <KnowledgeGraphWorkspace
          embedded
          :subject="subject"
          :grade="grade"
          :current-kp-id="currentKpId"
          :recommended-kp-id="reco?.target_kp?.id ?? null"
          :highlighted-kp-ids="pathInfo?.next_candidates ?? null"
          :graph-path-hint="graphPathHint"
          :graph-reco-hint="graphRecoHint"
          @select-kp="handleSelectKp"
          @open-content="openStudentKpContent"
          @state-change="handleStateChange"
        />
      </section>

      <aside class="graph-page__side">
        <section class="graph-page__side-panel">
          <div class="graph-page__side-head">
            <span class="graph-page__section-eyebrow">当前学习点</span>
            <h3>{{ currentNodeLabel }}</h3>
            <p>{{ graphLead }}</p>
          </div>

          <div class="graph-page__focus-card">
            <span class="graph-page__focus-code">{{ currentNodeCode }}</span>
            <strong>{{ graphStatusText }}</strong>
            <p>{{ currentKp?.chapter || "当前知识点尚未配置所属分类" }}</p>
          </div>

          <div class="graph-page__side-list">
            <article class="graph-page__side-item">
              <span>推荐学习</span>
              <strong>{{ recommendationLabel }}</strong>
              <p>{{ reco?.reason_summary || "系统会根据你的当前学习状态推荐下一步内容。" }}</p>
            </article>

            <article class="graph-page__side-item">
              <span>前置状态</span>
              <strong>{{ pathInfo?.can_unlock_next === false ? "需要补前置" : "可以继续推进" }}</strong>
              <p>{{ blockedSummary }}</p>
            </article>

            <article class="graph-page__side-item">
              <span>下一步路径</span>
              <strong>{{ nextCandidatesPreview }}</strong>
              <p>{{ pathInfo?.path_summary || "完成当前知识点后，系统会给出后续学习建议。" }}</p>
            </article>
          </div>

          <div class="graph-page__side-actions">
            <button class="graph-page__side-btn graph-page__side-btn--primary" type="button" @click="openCurrentLearning">
              进入当前知识点
            </button>
            <button class="graph-page__side-btn" type="button" @click="openRecommendedLearning">
              学习推荐内容
            </button>
          </div>
        </section>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  min-height: calc(100dvh - 96px);
  display: grid;
  gap: 16px;
  min-width: 0;
}

.graph-page__toolbar,
.graph-page__overview-shell,
.graph-page__workspace,
.graph-page__overview-card,
.graph-page__side-panel {
  border-radius: 32px;
  border: 3px solid #1f2937;
  background: #fffdf8;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  min-width: 0;
  max-width: 100%;
}

.graph-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 24px 26px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.32), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
}

.graph-page__toolbar-copy {
  display: grid;
  gap: 8px;
  max-width: 60ch;
  min-width: 0;
}

.graph-page__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #d7f9a8;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #1f2937;
}

.graph-page__toolbar-copy h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 44px);
  line-height: 1.02;
  letter-spacing: -0.04em;
  color: #16355c;
  overflow-wrap: anywhere;
}

.graph-page__toolbar-copy p {
  margin: 0;
  color: #60758f;
  font-size: 15px;
  line-height: 1.7;
}

.graph-page__toolbar-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  min-width: 0;
}

.graph-page__toolbar-meta span {
  font-size: 12px;
  font-weight: 800;
  color: #46617f;
  padding: 7px 12px;
  border-radius: 999px;
  background: #f5f9ff;
  border: 1.5px solid #cfe0f5;
}

.graph-page__toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.graph-page__select {
  width: 240px;
  max-width: 100%;
}

.graph-page__toolbar-actions :deep(.el-select__wrapper) {
  min-height: 48px;
  border-radius: 18px !important;
  background: #f8fbff !important;
  box-shadow: 0 0 0 1.5px #c6d8ef inset !important;
}

.graph-page__toolbar-actions :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #7ea9f6 inset, 0 0 0 3px rgba(87, 133, 231, 0.12) !important;
}

.graph-page__toolbar-actions :deep(.el-select__placeholder),
.graph-page__toolbar-actions :deep(.el-select__selected-item),
.graph-page__toolbar-actions :deep(.el-select__caret) {
  color: #5a6f8f !important;
}

.graph-page__toolbar-btn {
  min-width: 118px;
  min-height: 44px;
  padding: 0 20px;
  border-radius: 999px;
  border: 2px solid #c6d8ef;
  background: #ffffff;
  color: #274263;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
  box-shadow: 0 6px 16px rgba(31, 41, 55, 0.06);
}

.graph-page__toolbar-btn:hover,
.graph-page__toolbar-btn:focus-visible {
  transform: translateY(-1px);
  border-color: #9fbef3;
  background: #f8fbff;
  color: #214d8f;
}

.graph-page__toolbar-btn--primary {
  background: linear-gradient(135deg, #eaf8d3 0%, #ffffff 100%);
  border-color: #c6d8ef;
  color: #16355c;
}

.graph-page__toolbar-btn--primary:hover,
.graph-page__toolbar-btn--primary:focus-visible {
  background: linear-gradient(135deg, #dff3c6 0%, #f7fbff 100%);
  border-color: #bfd4ef;
  color: #16355c;
}

.graph-page__overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  min-width: 0;
}

.graph-page__overview-shell {
  padding: 14px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.24), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
}

.graph-page__overview-card {
  display: grid;
  gap: 8px;
  padding: 18px 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1.5px solid #c6d8ef;
  border-radius: 24px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.graph-page__overview-card:hover {
  transform: translateY(-2px);
  border-color: #9fbef3;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.8),
    0 12px 22px rgba(31, 41, 55, 0.08);
}

.graph-page__overview-card span,
.graph-page__section-eyebrow,
.graph-page__side-item span,
.graph-page__focus-card span {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

.graph-page__overview-card strong {
  font-size: 24px;
  line-height: 1.1;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.graph-page__overview-card small {
  color: #7b8da6;
  font-size: 12px;
  line-height: 1.6;
}

.graph-page__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
  min-width: 0;
}

.graph-page__workspace {
  overflow: hidden;
  min-height: min(82vh, 1000px);
  padding: 14px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.24), transparent 24%),
    linear-gradient(180deg, #f9fbff 0%, #f4f8fd 100%);
  min-width: 0;
}

.graph-page__side {
  min-width: 0;
}

.graph-page__side-panel {
  display: grid;
  gap: 16px;
  padding: 20px;
  position: sticky;
  top: 18px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.24), transparent 24%),
    linear-gradient(180deg, #fffdfb 0%, #fbfdff 100%);
}

.graph-page__side-head {
  display: grid;
  gap: 8px;
}

.graph-page__section-eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef5ff;
  color: #355070;
  border: 1.5px solid #cfe0f5;
  font-weight: 800;
}

.graph-page__side-head h3 {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.graph-page__side-head p,
.graph-page__side-item p,
.graph-page__focus-card p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
}

.graph-page__focus-card {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 24px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(135deg, #eef4ff 0%, #ffffff 100%);
  min-width: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.graph-page__focus-card strong,
.graph-page__side-item strong {
  font-size: 18px;
  line-height: 1.4;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.graph-page__focus-code {
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #cfe0f5;
}

.graph-page__side-list {
  display: grid;
  gap: 12px;
}

.graph-page__side-item {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 22px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  min-width: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.graph-page__side-item:hover {
  transform: translateY(-2px);
  border-color: #9fbef3;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 12px 22px rgba(31, 41, 55, 0.08);
}

.graph-page__side-actions {
  display: grid;
  gap: 10px;
}

.graph-page__side-btn {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  border: 2px solid #c6d8ef;
  background: #ffffff;
  color: #274263;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
  box-shadow: 0 6px 16px rgba(31, 41, 55, 0.06);
}

.graph-page__side-btn--primary {
  background: linear-gradient(135deg, #eaf8d3 0%, #ffffff 100%);
  border-color: #c6d8ef;
  color: #16355c;
}

.graph-page__side-btn:hover,
.graph-page__side-btn:focus-visible {
  transform: translateY(-1px);
  border-color: #9fbef3;
}

@media (max-width: 1100px) {
  .graph-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .graph-page__overview,
  .graph-page__content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .graph-page__toolbar-copy h1 {
    font-size: 28px;
  }

  .graph-page__select {
    width: 100%;
  }

  .graph-page__workspace {
    min-height: min(76vh, 920px);
  }
}
</style>
