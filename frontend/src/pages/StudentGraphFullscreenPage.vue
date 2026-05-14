<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import KnowledgeGraphWorkspace from "../components/KnowledgeGraphWorkspace.vue";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

type Course = { id: number; code: string; title: string; active?: boolean; enroll_status?: string };
type KP = { id: number; code: string; title: string; chapter?: string };
type RecoData = { target_kp: { id: number; code: string; title: string }; reason_summary: string; advice_text?: string };
type PathData = { next_candidates: number[]; next_titles: string[]; can_unlock_next: boolean; blocked_titles: string[]; path_summary: string };

const route = useRoute();
const router = useRouter();

const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);
const reco = ref<RecoData | null>(null);
const pathInfo = ref<PathData | null>(null);
const loading = ref(false);

const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const currentKp = computed(() => kps.value.find((item) => item.id === currentKpId.value) ?? null);
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
  router.replace({
    path: "/student/graph-fullscreen",
    query: {
      subject: subject.value || undefined,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
      preview: String(route.query.preview || "") || undefined,
    },
  });
}

async function loadCourses() {
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
  subject.value = routeSubject && !titles.has(routeSubject) ? "" : resolveStudentSubject(routeSubject, subject.value, courses.value);
  if (!subject.value) resetWorkspaceState();
}

async function loadKps() {
  if (!subject.value) {
    resetWorkspaceState();
    return;
  }
  const data = await getWithCache("/graph/kps", { subject: subject.value, grade: grade.value });
  kps.value = Array.isArray(data) ? data : [];
  const routeKp = Number(route.query.kp || route.query.kp_id || 0);
  currentKpId.value = routeKp && kps.value.some((item) => item.id === routeKp) ? routeKp : (kps.value[0]?.id ?? null);
}

async function loadRecommendation() {
  if (!currentKpId.value) {
    reco.value = null;
    return;
  }
  try {
    const res = await api.get(`/reco?kp_id=${currentKpId.value}&ai=true`);
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
  loading.value = true;
  try {
    await loadCourses();
    await loadKps();
    await loadRecommendation();
    await loadPathInfo();
  } catch (e: any) {
    resetWorkspaceState();
    if (e?.response?.status !== 401) ElMessage.error(e?.response?.data?.detail ?? "加载全屏图谱失败");
  } finally {
    loading.value = false;
  }
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
  router.push({ path: `/student/kp-content/${id}`, query: { subject: subject.value || undefined, from: "graph-fullscreen" } });
}

function openCurrentLearning() {
  if (!currentKpId.value) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  openStudentKpContent(currentKpId.value);
}

function backToWorkspace() {
  router.push({ path: "/student/graph-workspace", query: { subject: subject.value || undefined, kp: currentKpId.value ? String(currentKpId.value) : undefined, preview: String(route.query.preview || "") || undefined } });
}

function handleSelectKp(id: number) {
  currentKpId.value = id;
}

watch(currentKpId, async (value, oldValue) => {
  if (value === oldValue) return;
  syncQuery();
  await loadRecommendation();
  await loadPathInfo();
});

onMounted(refreshWorkspace);
</script>

<template>
  <main v-loading="loading" class="graph-fullscreen">
    <header class="graph-fullscreen__bar">
      <div class="graph-fullscreen__identity">
        <button type="button" class="graph-fullscreen__ghost" @click="backToWorkspace">返回</button>
        <div>
          <span>全屏学习图谱</span>
          <strong>{{ currentCourse?.title || subject || "知识图谱" }}</strong>
        </div>
      </div>

      <div class="graph-fullscreen__tools">
        <el-select v-model="subject" class="graph-fullscreen__select" placeholder="选择课程" :disabled="courses.length === 0" @change="handleCourseChange">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button type="button" class="graph-fullscreen__ghost" @click="refreshWorkspace">刷新</button>
      </div>
    </header>

    <section class="graph-fullscreen__meta">
      <span>知识点 {{ kps.length }}</span>
      <span>当前：{{ currentKp?.code || "--" }} {{ currentKp?.title || "未选择" }}</span>
      <span v-if="reco?.target_kp">推荐：{{ reco.target_kp.title }}</span>
      <span v-if="pathInfo?.path_summary">{{ pathInfo.path_summary }}</span>
    </section>

    <section class="graph-fullscreen__canvas">
      <KnowledgeGraphWorkspace
        embedded
        actor-mode="student"
        :subject="subject"
        :grade="grade"
        :current-kp-id="currentKpId"
        :recommended-kp-id="reco?.target_kp?.id ?? null"
        :highlighted-kp-ids="pathInfo?.next_candidates ?? null"
        :graph-path-hint="graphPathHint"
        :graph-reco-hint="graphRecoHint"
        @select-kp="handleSelectKp"
        @open-content="openStudentKpContent"
      />
    </section>
  </main>
</template>

<style scoped>
.graph-fullscreen {
  height: 100dvh;
  min-width: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  overflow: hidden;
  background: linear-gradient(180deg, #f8fbff 0%, #f7fafc 100%);
}

.graph-fullscreen__bar {
  min-height: 58px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
}

.graph-fullscreen__identity,
.graph-fullscreen__tools,
.graph-fullscreen__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.graph-fullscreen__identity > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.graph-fullscreen__identity span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.graph-fullscreen__identity strong {
  color: #0f172a;
  font-size: 18px;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.graph-fullscreen__tools {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.graph-fullscreen__select {
  width: 240px;
}

.graph-fullscreen__ghost,
.graph-fullscreen__primary {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: #ffffff;
  color: #334155;
  font-weight: 800;
  cursor: pointer;
}

.graph-fullscreen__primary {
  border-color: rgba(34, 197, 94, 0.28);
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
}

.graph-fullscreen__ghost:hover {
  background: #f8fafc;
}

.graph-fullscreen__meta {
  min-height: 38px;
  padding: 6px 16px;
  overflow-x: auto;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  background: #f8fafc;
}

.graph-fullscreen__meta span {
  flex: 0 0 auto;
  padding: 6px 10px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.graph-fullscreen__canvas {
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.graph-fullscreen :deep(.workspace-shell) {
  height: 100%;
  border-radius: 0;
}

.graph-fullscreen :deep(.workspace-content),
.graph-fullscreen :deep(.workspace-stage) {
  height: 100%;
  min-height: 0;
}

@media (max-width: 860px) {
  .graph-fullscreen__bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .graph-fullscreen__tools,
  .graph-fullscreen__select {
    width: 100%;
  }
}
</style>
