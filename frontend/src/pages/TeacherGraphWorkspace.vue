<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import TeacherIntroHero from "../components/TeacherIntroHero.vue";
import TeacherGraphWorkbench from "../components/TeacherGraphWorkbench.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  lifecycle_status?: string;
  start_at?: string | null;
  end_at?: string | null;
};

type TeacherGraphWorkbenchExpose = {
  reloadGraph: () => Promise<void>;
  fitGraph: () => void;
  resetGraphViewport: () => void;
};

const route = useRoute();
const router = useRouter();

const isTeacher = computed(() => getRole() === "teacher");
const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const workbenchRef = ref<TeacherGraphWorkbenchExpose | null>(null);
const refreshing = ref(false);

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

const courseLifecycleLabel = computed(() => {
  const value = String(currentCourse.value?.lifecycle_status || "draft").toLowerCase();
  if (value === "active") return "进行中";
  if (value === "archived") return "已归档";
  return "待开课";
});

const courseModeLabel = computed(() => (isReadonlyCourse.value ? "只读查看" : "可继续建设"));

const courseDescription = computed(
  () => `${currentCourse.value?.title || "当前课程"} · 在这里维护课程知识点、章节关系与内容入口，保证图谱结构和教学内容保持一致。`
);

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  if (route.path === "/teacher/content" && String(route.query.subject || "").trim() === subject.value.trim()) return;
  router.replace({
    path: "/teacher/content",
    query: buildTeacherSubjectQuery(subject.value),
  });
}

async function refreshWorkspace() {
  refreshing.value = true;
  try {
    await loadCourses();
    await nextTick();
    await workbenchRef.value?.reloadGraph?.();
    workbenchRef.value?.fitGraph?.();
    ElMessage.success("知识图谱已刷新");
  } finally {
    refreshing.value = false;
  }
}

function goBack() {
  router.push({ path: "/teacher/workspace", query: buildTeacherSubjectQuery(subject.value) });
}

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "");
    if (next && next !== subject.value) subject.value = next;
  }
);

watch(subject, () => {
  syncQuery();
});

onMounted(async () => {
  if (!isTeacher.value) {
    ElMessage.warning("仅教师可访问知识图谱");
    router.push("/login/staff");
    return;
  }
  await loadCourses();
});
</script>

<template>
  <div v-if="isTeacher" class="graph-page">
    <TeacherIntroHero eyebrow="教师工作台" title="知识图谱" pill="内容建设" :description="courseDescription">
      <template #actions>
        <el-select v-model="subject" class="graph-page__select" placeholder="选择课程">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <el-button class="graph-page__toolbar-btn" @click="goBack">返回工作台</el-button>
        <el-button class="graph-page__toolbar-btn graph-page__toolbar-btn--accent" :loading="refreshing" @click="refreshWorkspace">
          刷新图谱
        </el-button>
      </template>
    </TeacherIntroHero>

    <section class="graph-page__summary">
      <article class="graph-page__summary-card">
        <span>当前课程</span>
        <strong>{{ currentCourse?.title || "未选择课程" }}</strong>
      </article>
      <article class="graph-page__summary-card">
        <span>课程状态</span>
        <strong>{{ courseLifecycleLabel }}</strong>
      </article>
      <article class="graph-page__summary-card">
        <span>当前模式</span>
        <strong>{{ courseModeLabel }}</strong>
      </article>
    </section>

    <section class="graph-page__panel">
      <div class="graph-page__panel-head">
        <div>
          <span class="graph-page__eyebrow">图谱编辑</span>
          <h2>以课程图谱为中心维护知识结构</h2>
          <p>节点、关系和内容入口统一从这张图出发，减少老师在多个页面间切换和重复维护。</p>
        </div>
      </div>

      <div class="graph-page__panel-body">
        <TeacherGraphWorkbench ref="workbenchRef" embedded :subject="subject" :grade="grade" :readonly="isReadonlyCourse" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  width: 100%;
  padding: 0 12px 12px;
  display: grid;
  gap: 18px;
}

.graph-page__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.graph-page__summary-card,
.graph-page__panel {
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background:
    radial-gradient(circle at top right, rgba(219, 234, 254, 0.18), transparent 24%),
    radial-gradient(circle at top left, rgba(220, 252, 231, 0.1), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
}

.graph-page__summary-card {
  display: grid;
  gap: 10px;
  padding: 22px 24px;
  min-height: 122px;
  align-content: start;
}

.graph-page__summary-card span {
  font-size: 13px;
  font-weight: 700;
  color: #6a7280;
}

.graph-page__summary-card strong {
  font-size: 24px;
  line-height: 1.2;
  color: #1f2937;
  letter-spacing: -0.03em;
}

.graph-page__panel {
  padding: 22px;
  display: grid;
  gap: 18px;
}

.graph-page__panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.graph-page__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #eefbf3;
  color: #166534;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  border: 1px solid rgba(34, 197, 94, 0.18);
}

.graph-page__panel-head h2 {
  margin: 8px 0 0;
  color: #1f2937;
  font-size: 28px;
  line-height: 1.15;
}

.graph-page__panel-head p {
  margin: 10px 0 0;
  color: #6a7280;
  line-height: 1.75;
  max-width: 64ch;
}

.graph-page__panel-body {
  overflow: hidden;
  min-height: calc(100dvh - 278px);
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(219, 234, 254, 0.16), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.92));
}

.graph-page__panel-body > * {
  width: 100%;
}

.graph-page__select {
  width: 240px;
}

.graph-page :deep(.teacher-intro-hero__actions .el-select__wrapper) {
  min-height: 42px;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.22) inset !important;
}

.graph-page :deep(.teacher-intro-hero__actions .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #60a5fa inset, 0 0 0 4px rgba(96, 165, 250, 0.14) !important;
}

.graph-page :deep(.teacher-intro-hero__actions .el-select__placeholder),
.graph-page :deep(.teacher-intro-hero__actions .el-select__selected-item),
.graph-page :deep(.teacher-intro-hero__actions .el-select__caret) {
  color: #6b7280 !important;
}

.graph-page__toolbar-btn {
  min-width: 118px;
  min-height: 40px;
  padding: 0 20px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #ffffff;
  color: #475569;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.05);
}

.graph-page__toolbar-btn:hover,
.graph-page__toolbar-btn:focus-visible {
  border-color: rgba(100, 116, 139, 0.34);
  background: #f8fafc;
  color: #1f2937;
}

.graph-page__toolbar-btn.graph-page__toolbar-btn--accent {
  border-color: rgba(34, 197, 94, 0.24);
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

@media (max-width: 960px) {
  .graph-page__summary {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .graph-page {
    padding: 0 8px 8px;
  }

  .graph-page__select {
    width: 100%;
  }

  .graph-page__panel {
    padding: 18px;
  }

  .graph-page__panel-head h2 {
    font-size: 22px;
  }

  .graph-page__panel-body {
    min-height: calc(100dvh - 316px);
  }
}
</style>
