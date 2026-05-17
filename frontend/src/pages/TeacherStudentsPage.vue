<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherStudentDetail from "../components/TeacherStudentDetail.vue";
import TeacherWorkspaceHero from "../components/TeacherWorkspaceHero.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

const selectedStudentId = computed<number | null>(() => {
  const raw = route.query.user_id;
  const value = Array.isArray(raw) ? raw[0] : raw;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
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
  const nextQuery = buildTeacherSubjectQuery(subject.value, {
    tab: "detail",
    user_id: selectedStudentId.value ? String(selectedStudentId.value) : undefined,
  });
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "class").trim();
  const currentUserId = String(route.query.user_id || "").trim();
  const nextUserId = String((nextQuery as Record<string, unknown>).user_id || "").trim();
  if (
    route.path === "/teacher/students"
    && currentSubject === String(nextQuery.subject || "").trim()
    && currentTab === "detail"
    && currentUserId === nextUserId
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
    const next = resolveTeacherSubject(String(value || ""), subject.value, courses.value);
    if (next && next !== subject.value) subject.value = next;
  },
);

onMounted(loadCourses);
</script>

<template>
  <div class="teacher-page">
    <TeacherWorkspaceHero
      v-model="subject"
      title="学生详情"
      pill="个体变化"
      description="围绕单个学生查看画像、阶段变化和学习记录，先判断状态，再决定是否干预。"
      :courses="courses"
    >
      <template #meta>
        <span class="teacher-page__meta-pill">{{ subject || "未选择课程" }}</span>
        <span class="teacher-page__meta-pill teacher-page__meta-pill--muted">{{ grade }}</span>
      </template>
      <template #actions>
        <el-button @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'class' } })">班级总览</el-button>
        <el-button type="primary">学生详情</el-button>
        <el-button @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'results' } })">画像结果</el-button>
      </template>
    </TeacherWorkspaceHero>

    <section class="teacher-detail-panel">
      <TeacherStudentDetail :subject="subject" :grade="grade" :initial-user-id="selectedStudentId" />
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

.teacher-detail-panel {
  min-width: 0;
  padding: 20px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: #ffffff;
  box-shadow: none;
}

.teacher-detail-panel :deep(.panel-card),
.teacher-detail-panel :deep(.sub-card),
.teacher-detail-panel :deep(.detail-header),
.teacher-detail-panel :deep(.metric-card),
.teacher-detail-panel :deep(.summary-metric),
.teacher-detail-panel :deep(.record-card),
.teacher-detail-panel :deep(.stage-card),
.teacher-detail-panel :deep(.empty-strip),
.teacher-detail-panel :deep(.teacher-tools-panel),
.teacher-detail-panel :deep(.indicator-input-card) {
  border-radius: 14px !important;
  border-color: rgba(148, 163, 184, 0.22) !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.teacher-detail-panel :deep(.detail-header__eyebrow),
.teacher-detail-panel :deep(.section-label),
.teacher-detail-panel :deep(.sub-card__title::before) {
  box-shadow: none !important;
}
</style>
