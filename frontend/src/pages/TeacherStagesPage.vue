<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherStageManager from "../components/TeacherStageManager.vue";
import TeacherWorkspaceHero from "../components/TeacherWorkspaceHero.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

function syncQuery(nextSubject?: string) {
  if (typeof nextSubject === "string") {
    subject.value = nextSubject;
  }
  const nextQuery = { ...buildTeacherSubjectQuery(subject.value), tab: "stages" };
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "stages").trim();
  if (
    route.path === "/teacher/evaluation"
    && currentSubject === String(nextQuery.subject || "").trim()
    && currentTab === "stages"
  ) {
    return;
  }
  saveTeacherSubject(subject.value);
  router.replace({ path: "/teacher/evaluation", query: nextQuery });
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
      title="阶段设置"
      pill="阶段流程"
      description="先定义课程阶段，再让导入、画像结果和审核流程都落在同一套阶段口径上。"
      field-label="课程"
      :courses="courses"
    >
      <template #meta>
        <span class="teacher-page__meta-pill">{{ subject || "未选择课程" }}</span>
        <span class="teacher-page__meta-pill teacher-page__meta-pill--muted">{{ grade }}</span>
      </template>
    </TeacherWorkspaceHero>

    <section class="teacher-page__panel">
      <TeacherStageManager
        :course-id="selectedCourseId"
        :subject="subject"
        :grade="grade"
        :courses="courses"
        @subject-change="syncQuery"
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

.teacher-page__panel {
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
