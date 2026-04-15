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
  },
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
    <TeacherIntroHero
      eyebrow="教师工作台"
      title="知识图谱"
      pill="内容建设"
      :description="`${currentCourse?.title || '当前课程'} · 在这里维护课程知识点、章节关系与内容入口。`"
    >
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

    <section class="graph-page__summary panel-card">
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
        <strong>{{ isReadonlyCourse ? "只读查看" : "可继续建设" }}</strong>
      </article>
    </section>

    <section class="graph-page__panel">
      <div class="graph-page__panel-body">
        <TeacherGraphWorkbench
          ref="workbenchRef"
          embedded
          :subject="subject"
          :grade="grade"
          :readonly="isReadonlyCourse"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  width: 100%;
  padding: 0 12px 12px;
  display: grid;
  gap: 12px;
}

.graph-page__summary,
.graph-page__panel {
  border-radius: 28px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.24), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.graph-page__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.graph-page__summary-card {
  display: grid;
  gap: 12px;
  padding: 22px 24px;
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.18), transparent 26%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  min-height: 128px;
  align-content: start;
}

.graph-page__summary-card span {
  font-size: 14px;
  font-weight: 700;
  color: #4f5f75;
}

.graph-page__summary-card strong {
  font-size: 24px;
  line-height: 1.25;
  color: var(--app-text-main);
}

.graph-page__panel {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.graph-page__panel-body {
  overflow: hidden;
  min-height: calc(100dvh - 212px);
  background:
    radial-gradient(circle at top right, rgba(214, 245, 234, 0.16), transparent 28%),
    linear-gradient(180deg, #fffaf3 0%, #fffdf8 100%);
  border-radius: 30px;
  border: 3px solid #1f2937;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.graph-page__panel-body > * {
  width: 100%;
}

.graph-page__select {
  width: 240px;
}

.graph-page :deep(.teacher-intro-hero__actions .el-select__wrapper) {
  min-height: 42px;
  border-radius: 18px !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 1px #cfe7de inset !important;
}

.graph-page :deep(.teacher-intro-hero__actions .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #34d399 inset, 0 0 0 3px rgba(16, 185, 129, 0.12) !important;
}

.graph-page :deep(.teacher-intro-hero__actions .el-select__placeholder),
.graph-page :deep(.teacher-intro-hero__actions .el-select__selected-item),
.graph-page :deep(.teacher-intro-hero__actions .el-select__caret) {
  color: #25645b !important;
}

.graph-page__toolbar-btn {
  min-width: 118px;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 999px;
  border: 1px solid #cfe7de;
  background: #ffffff;
  color: #315f56;
  font-size: 14px;
  font-weight: 800;
  box-shadow: none;
}

.graph-page__toolbar-btn:hover,
.graph-page__toolbar-btn:focus-visible {
  border-color: #9fbef3;
  background: #f8fbff;
  color: #214d8f;
}

.graph-page__toolbar-btn.graph-page__toolbar-btn--accent {
  border-color: #8fd8c1;
  background: linear-gradient(180deg, #ffffff 0%, #effbf6 100%);
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

  .graph-page__panel-body {
    min-height: calc(100dvh - 232px);
  }
}
</style>
