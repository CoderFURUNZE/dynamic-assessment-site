<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import KnowledgeGraphWorkspace from "../components/KnowledgeGraphWorkspace.vue";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

type Course = { id: number; code: string; title: string };
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
const selectedLabel = computed(() => {
  if (currentKp.value) return `${currentKp.value.code} ${currentKp.value.title}`;
  if (workspaceState.value.selectedCategory) return workspaceState.value.selectedCategory;
  return "未选择";
});
const recommendationLabel = computed(() => reco.value?.target_kp?.title || "暂无");

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
    }));
    const routeSubject = String(route.query.subject || "").trim();
    const titles = new Set(courses.value.map((item) => item.title));
    const nextSubject = routeSubject && !titles.has(routeSubject)
      ? ""
      : resolveStudentSubject(routeSubject, subject.value, courses.value);
    subject.value = nextSubject;
    if (!nextSubject) {
      resetWorkspaceState();
    }
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

function handleSelectKp(id: number) {
  router.push({
    path: `/student/kp-content/${id}`,
    query: {
      subject: subject.value || undefined,
      from: "graph-workspace",
    },
  });
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
        <span class="graph-page__eyebrow">Knowledge Graph</span>
        <h1>知识图谱</h1>
        <p>{{ currentCourse?.title || "当前没有可学习课程" }}</p>
      </div>

      <div class="graph-page__toolbar-actions">
        <el-select v-model="subject" class="graph-page__select" placeholder="选择课程" @change="handleCourseChange" :disabled="courses.length === 0">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="graph-page__toolbar-btn" type="button" @click="refreshWorkspace">刷新</button>
      </div>
    </section>

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
        @state-change="handleStateChange"
      />
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  min-height: calc(100dvh - 96px);
  display: grid;
  gap: 10px;
}

.graph-page__toolbar,
.graph-page__workspace,
.graph-page__stat-card {
  border-radius: 24px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 14%, var(--app-border));
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
}

.graph-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 18px;
  background: #ffffff;
}

.graph-page__toolbar-copy {
  display: grid;
  gap: 6px;
  max-width: 60ch;
}

.graph-page__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5a7db7;
}

.graph-page__toolbar-copy h1 {
  margin: 0;
  font-size: clamp(22px, 3vw, 30px);
  line-height: 1.1;
  color: #11284a;
}

.graph-page__toolbar-copy p {
  margin: 0;
  color: #60758f;
  font-size: 13px;
  line-height: 1.5;
}

.graph-page__toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.graph-page__select {
  width: 240px;
}

.graph-page__toolbar-actions :deep(.el-select__wrapper) {
  min-height: 42px;
  border-radius: 18px !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 1px #d7e4f5 inset !important;
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
  min-height: 42px;
  padding: 0 20px;
  border-radius: 999px;
  border: 1px solid #d7e4f5;
  background: #ffffff;
  color: #274263;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.graph-page__toolbar-btn:hover,
.graph-page__toolbar-btn:focus-visible {
  border-color: #9fbef3;
  background: #f8fbff;
  color: #214d8f;
}

.graph-page__workspace {
  overflow: hidden;
  min-height: min(82vh, 1000px);
  padding: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f7fc 100%);
}

@media (max-width: 1100px) {
  .graph-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
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
