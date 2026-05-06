<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import TeacherGraphWorkbench from "../components/TeacherGraphWorkbench.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  lifecycle_status?: string;
  end_at?: string | null;
};

type TeacherGraphWorkbenchExpose = {
  reloadGraph: () => Promise<void>;
  fitGraph: () => void;
};

const route = useRoute();
const router = useRouter();

const canOpenTeacherGraph = computed(() => ["teacher", "admin"].includes(getRole()));
const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const workbenchRef = ref<TeacherGraphWorkbenchExpose | null>(null);

const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const isReadonlyCourse = computed(() => {
  const course = currentCourse.value;
  if (!course) return false;
  if (String(course.lifecycle_status || "").toLowerCase() === "archived") return true;
  if (course.end_at) {
    const end = new Date(course.end_at).getTime();
    if (Number.isFinite(end) && end < Date.now()) return true;
  }
  return false;
});

async function loadCourses() {
  const res = await api.get("/graph/courses");
  courses.value = res.data ?? [];
  const routeSubject = String(route.query.subject || "").trim();
  subject.value = resolveTeacherSubject(routeSubject, subject.value, courses.value) || routeSubject;
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  if (route.path === "/teacher/graph-fullscreen" && String(route.query.subject || "").trim() === subject.value.trim()) return;
  router.replace({ path: "/teacher/graph-fullscreen", query: buildTeacherSubjectQuery(subject.value) });
}

async function refreshWorkspace() {
  try {
    await loadCourses();
    await workbenchRef.value?.reloadGraph?.();
    workbenchRef.value?.fitGraph?.();
  } catch (e: any) {
    if (e?.response?.status !== 401) ElMessage.error(e?.response?.data?.detail ?? "加载全屏图谱失败");
  }
}

function backToWorkspace() {
  router.push({ path: "/teacher/workspace", query: buildTeacherSubjectQuery(subject.value) });
}

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "");
    if (next && next !== subject.value) subject.value = next;
  },
);

watch(subject, () => {
  syncQuery();
});

onMounted(async () => {
  if (!canOpenTeacherGraph.value) {
    ElMessage.warning("仅教师或管理员可访问全屏图谱");
    router.push("/login/staff");
    return;
  }
  await refreshWorkspace();
});
</script>

<template>
  <main v-if="canOpenTeacherGraph" class="teacher-graph-fullscreen">
    <header class="teacher-graph-fullscreen__bar">
      <button type="button" class="teacher-graph-fullscreen__back" @click="backToWorkspace">返回主工作台</button>
      <div class="teacher-graph-fullscreen__title">
        <span>全屏图谱</span>
        <strong>{{ currentCourse?.title || subject || "知识图谱" }}</strong>
      </div>
    </header>

    <section class="teacher-graph-fullscreen__canvas">
      <TeacherGraphWorkbench ref="workbenchRef" fullscreen :subject="subject" :grade="grade" :readonly="isReadonlyCourse" />
    </section>
  </main>
</template>

<style scoped>
.teacher-graph-fullscreen {
  height: 100dvh;
  min-width: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  background: linear-gradient(180deg, #f8fbff 0%, #f7fafc 100%);
}

.teacher-graph-fullscreen__bar {
  min-height: 58px;
  padding: 10px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
}

.teacher-graph-fullscreen__back {
  min-height: 38px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font-weight: 800;
  white-space: nowrap;
}

.teacher-graph-fullscreen__back:hover {
  background: #f8fafc;
}

.teacher-graph-fullscreen__title {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.teacher-graph-fullscreen__title span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.teacher-graph-fullscreen__title strong {
  color: #0f172a;
  font-size: 18px;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.teacher-graph-fullscreen__canvas {
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  padding: 10px;
}

.teacher-graph-fullscreen :deep(.teacher-workbench) {
  height: 100%;
}

.teacher-graph-fullscreen :deep(.teacher-workbench--fullscreen .teacher-header),
.teacher-graph-fullscreen :deep(.teacher-workbench--fullscreen .teacher-stage__top),
.teacher-graph-fullscreen :deep(.teacher-workbench--fullscreen .teacher-stage__menu),
.teacher-graph-fullscreen :deep(.teacher-workbench--fullscreen .teacher-stage__hint) {
  display: none;
}

.teacher-graph-fullscreen :deep(.teacher-content--fullscreen) {
  height: 100%;
  min-height: 0;
}

.teacher-graph-fullscreen :deep(.teacher-workbench--fullscreen .teacher-stage) {
  min-height: 0;
}

.teacher-graph-fullscreen :deep(.teacher-workbench--fullscreen .teacher-stage__viewport) {
  min-height: 0;
  height: 100%;
}

@media (max-width: 900px) {
  .teacher-graph-fullscreen__bar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
