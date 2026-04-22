<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";
import TeacherWorkspaceHero from "../components/TeacherWorkspaceHero.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

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
  const nextQuery = { ...buildTeacherSubjectQuery(subject.value), tab: "rules" };
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "class").trim();
  if (
    route.path === "/teacher/students"
    && currentSubject === String(nextQuery.subject || "").trim()
    && currentTab === "rules"
  ) {
    return;
  }
  saveTeacherSubject(subject.value);
  router.replace({ path: "/teacher/students", query: nextQuery });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  },
);

onMounted(loadCourses);
</script>

<template>
  <div class="teacher-page">
    <TeacherWorkspaceHero
      v-model="subject"
      title="课程画像规则"
      pill="教师配置"
      description="为当前课程调整画像风格、维度权重和默认策略，让结果更贴合教学目标。"
      :courses="courses"
    >
      <template #meta>
        <span class="teacher-page__meta-pill">{{ subject || "未选择课程" }}</span>
        <span class="teacher-page__meta-pill teacher-page__meta-pill--muted">{{ grade }}</span>
      </template>
      <template #actions>
        <el-button @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'class' } })">班级总览</el-button>
        <el-button type="primary" @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'results' } })">画像结果</el-button>
      </template>
    </TeacherWorkspaceHero>

    <section class="teacher-rules-panel">
      <AdminPersonaManager
        :subject="subject"
        :grade="grade"
        manager-role="teacher"
        step="settings"
      />
    </section>
  </div>
</template>

<style scoped>
.teacher-page,
.teacher-rules-panel {
  min-width: 0;
}

.teacher-page {
  display: grid;
  gap: 24px;
}

.teacher-page__meta-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  background: rgba(255, 255, 255, 0.82);
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.teacher-page__meta-pill--muted {
  color: #64748b;
}

.teacher-rules-panel {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.18), transparent 24%),
    radial-gradient(circle at bottom right, rgba(187, 247, 208, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
  padding: 24px;
}

.teacher-rules-panel :deep(.persona-card),
.teacher-rules-panel :deep(.persona-preset-card),
.teacher-rules-panel :deep(.persona-section),
.teacher-rules-panel :deep(.dimension-card),
.teacher-rules-panel :deep(.strategy-item),
.teacher-rules-panel :deep(.persona-collapse-hint),
.teacher-rules-panel :deep(.persona-readonly__card) {
  border-color: rgba(148, 163, 184, 0.2) !important;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
}

.teacher-rules-panel :deep(.persona-card) {
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.06) !important;
}

.teacher-rules-panel :deep(.persona-block__title),
.teacher-rules-panel :deep(.persona-title),
.teacher-rules-panel :deep(.section-title) {
  color: #0f172a !important;
}

.teacher-rules-panel :deep(.persona-block__desc),
.teacher-rules-panel :deep(.section-desc),
.teacher-rules-panel :deep(.persona-step-header__desc),
.teacher-rules-panel :deep(.persona-collapse-hint__desc),
.teacher-rules-panel :deep(.dimension-summary),
.teacher-rules-panel :deep(.persona-tip-inline) {
  color: #64748b !important;
}

.teacher-rules-panel :deep(.persona-preset-card__tag),
.teacher-rules-panel :deep(.persona-config-wrap__meta),
.teacher-rules-panel :deep(.persona-threshold-card__badge) {
  border-color: rgba(148, 163, 184, 0.22) !important;
  background: #f8fafc !important;
  color: #475569 !important;
}

.teacher-rules-panel :deep(.persona-preset-card__icon),
.teacher-rules-panel :deep(.persona-block__title--with-icon .el-icon),
.teacher-rules-panel :deep(.section-title--with-icon .el-icon),
.teacher-rules-panel :deep(.persona-collapse-toggle-icon) {
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%) !important;
  color: #2563eb !important;
  box-shadow: none !important;
}

.teacher-rules-panel :deep(.persona-preset-card.is-active) {
  background: radial-gradient(circle at top left, rgba(187, 247, 208, 0.28), transparent 56%), #ffffff !important;
}

.teacher-rules-panel :deep(.el-input__wrapper),
.teacher-rules-panel :deep(.el-input-number .el-input__wrapper) {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.2) inset !important;
}
</style>
