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
  const nextQuery = { ...buildTeacherSubjectQuery(subject.value), tab: "results" };
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "class").trim();
  if (
    route.path === "/teacher/students"
    && currentSubject === String(nextQuery.subject || "").trim()
    && currentTab === "results"
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
      title="画像结果"
      pill="结果查看"
      description="按课程查看学生画像等级、结果分布和判定摘要，再继续进入学生详情处理。"
      :courses="courses"
    >
      <template #meta>
        <span class="teacher-page__meta-pill">{{ subject || "未选择课程" }}</span>
        <span class="teacher-page__meta-pill teacher-page__meta-pill--muted">{{ grade }}</span>
      </template>
      <template #actions>
        <el-button @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'class' } })">班级总览</el-button>
        <el-button type="primary" @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'detail' } })">学生详情</el-button>
      </template>
    </TeacherWorkspaceHero>

    <section class="teacher-profiles-panel">
      <AdminPersonaManager
        :subject="subject"
        :grade="grade"
        :readonly="true"
        step="results"
        :show-student-detail-action="true"
        @view-student="(id:number)=>router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined, tab: 'detail' } })"
      />
    </section>
  </div>
</template>

<style scoped>
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

.teacher-profiles-panel {
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 16px;
  background: #ffffff;
  box-shadow: none;
  padding: 24px;
}

.teacher-profiles-panel :deep(.persona-card),
.teacher-profiles-panel :deep(.results-table-card),
.teacher-profiles-panel :deep(.persona-readonly__card),
.teacher-profiles-panel :deep(.persona-preset-card),
.teacher-profiles-panel :deep(.persona-threshold-card),
.teacher-profiles-panel :deep(.dimension-card),
.teacher-profiles-panel :deep(.strategy-item),
.teacher-profiles-panel :deep(.results-summary),
.teacher-profiles-panel :deep(.results-toolbar) {
  border-color: rgba(148, 163, 184, 0.2) !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.teacher-profiles-panel :deep(.persona-card) {
  box-shadow: none !important;
}

.teacher-profiles-panel :deep(.persona-block__title),
.teacher-profiles-panel :deep(.persona-title),
.teacher-profiles-panel :deep(.section-title),
.teacher-profiles-panel :deep(.results-header h3) {
  color: #0f172a !important;
}

.teacher-profiles-panel :deep(.persona-block__desc),
.teacher-profiles-panel :deep(.section-desc),
.teacher-profiles-panel :deep(.persona-step-header__desc),
.teacher-profiles-panel :deep(.results-summary),
.teacher-profiles-panel :deep(.reason-summary) {
  color: #64748b !important;
}

.teacher-profiles-panel :deep(.persona-preset-card__tag),
.teacher-profiles-panel :deep(.persona-config-wrap__meta),
.teacher-profiles-panel :deep(.persona-threshold-card__badge),
.teacher-profiles-panel :deep(.persona-type-pill),
.teacher-profiles-panel :deep(.level-pill) {
  border-color: rgba(148, 163, 184, 0.22) !important;
  background: #f8fafc !important;
  color: #475569 !important;
}

.teacher-profiles-panel :deep(.persona-preset-card.is-active) {
  background: #f0fdf4 !important;
  border-color: rgba(34, 197, 94, 0.3) !important;
}

.teacher-profiles-panel :deep(.results-toolbar .el-input__wrapper),
.teacher-profiles-panel :deep(.results-toolbar .el-select__wrapper),
.teacher-profiles-panel :deep(.override-cell .el-select__wrapper) {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.2) inset !important;
}

@media (max-width: 900px) {
  .teacher-profiles-panel {
    padding: 18px;
  }
}
</style>
