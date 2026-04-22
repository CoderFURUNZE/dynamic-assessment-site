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
  const nextUserId = String(nextQuery.user_id || "").trim();
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
        <el-button type="primary" @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'results' } })">画像结果</el-button>
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
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.18), transparent 24%),
    radial-gradient(circle at bottom right, rgba(187, 247, 208, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}
</style>
