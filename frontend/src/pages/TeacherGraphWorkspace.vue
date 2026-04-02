<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import KnowledgeGraphWorkspace from "../components/KnowledgeGraphWorkspace.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  lifecycle_status?: string;
  start_at?: string | null;
  end_at?: string | null;
};

const route = useRoute();
const router = useRouter();

const isTeacher = computed(() => getRole() === "teacher");
const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");

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
  await loadCourses();
}

function goBack() {
  router.push({ path: "/teacher/workspace", query: buildTeacherSubjectQuery(subject.value) });
}

function openTeacherKpWorkspace(kpId: number) {
  if (!kpId) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  router.push({
    path: `/teacher/kp-content/${kpId}`,
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      mode: "edit",
      from: "graph-workspace",
    },
  });
}

function createTeacherKp() {
  router.push({
    path: "/teacher/kp-content/0",
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      mode: "create",
      from: "graph-workspace",
    },
  });
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
    router.push("/login/student");
    return;
  }
  await loadCourses();
});
</script>

<template>
  <div v-if="isTeacher" class="graph-page">
    <section class="graph-page__toolbar">
      <div class="graph-page__toolbar-copy">
        <h1>知识图谱</h1>
        <p>{{ currentCourse?.title || "当前课程" }}</p>
      </div>
      <div class="graph-page__toolbar-actions">
        <el-select v-model="subject" class="graph-page__select" placeholder="选择课程">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <el-button class="graph-page__toolbar-btn graph-page__toolbar-btn--accent" :disabled="isReadonlyCourse" @click="createTeacherKp">新建知识点</el-button>
        <el-button class="graph-page__toolbar-btn" @click="goBack">返回工作台</el-button>
        <el-button class="graph-page__toolbar-btn graph-page__toolbar-btn--accent" @click="refreshWorkspace">刷新</el-button>
      </div>
    </section>

    <section class="graph-page__panel">
      <div class="graph-page__panel-body">
        <KnowledgeGraphWorkspace
          embedded
          actor-mode="teacher"
          :subject="subject"
          :grade="grade"
          @open-content="openTeacherKpWorkspace"
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

.graph-page__toolbar,
.graph-page__panel {
  border-radius: 20px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 12%, var(--app-border));
  background: #ffffff;
  box-shadow: var(--app-shadow-soft);
}

.graph-page__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #ffffff;
}

.graph-page__toolbar-copy {
  display: grid;
  gap: 4px;
}

.graph-page__toolbar-copy h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.1;
  color: #11284a;
  letter-spacing: -0.03em;
}

.graph-page__toolbar-copy p {
  margin: 0;
  color: #60758f;
  font-size: 13px;
  line-height: 1.4;
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
  box-shadow: none;
}

.graph-page__toolbar-btn:hover,
.graph-page__toolbar-btn:focus-visible {
  border-color: #9fbef3;
  background: #f8fbff;
  color: #214d8f;
}

.graph-page__toolbar-btn.graph-page__toolbar-btn--accent {
  border-color: #b8cdf3;
  color: #2e5ea8;
}

.graph-page__toolbar-btn.is-disabled,
.graph-page__toolbar-btn.is-disabled:hover {
  border-color: #e3eaf5;
  background: #f8fbff;
  color: #afbdd0;
}

.graph-page__panel {
  padding: 8px;
}

.graph-page__panel-body {
  overflow: hidden;
  min-height: calc(100dvh - 156px);
  background: linear-gradient(180deg, #f8fbff 0%, #f3f7fc 100%);
  border-radius: 16px;
}

@media (max-width: 1100px) {
  .graph-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 768px) {
  .graph-page {
    padding: 0 8px 8px;
  }

  .graph-page__toolbar-copy h1 {
    font-size: 22px;
  }

  .graph-page__select {
    width: 100%;
  }

  .graph-page__panel-body {
    min-height: calc(100dvh - 176px);
  }
}
</style>
