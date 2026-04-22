<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherIndicatorSelector from "../components/TeacherIndicatorSelector.vue";
import TeacherIntroHero from "../components/TeacherIntroHero.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
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

function syncQuery() {
  saveTeacherSubject(subject.value);
  const nextQuery = { ...buildTeacherSubjectQuery(subject.value), tab: "indicators" };
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "stages").trim();
  if (route.path === "/teacher/evaluation" && currentSubject === String(nextQuery.subject || "").trim() && currentTab === "indicators") {
    return;
  }
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
    <TeacherIntroHero
      eyebrow="阶段评价"
      title="指标配置"
      pill="评价口径"
      description="把课程评价维度、指标映射和使用口径集中维护，避免后续结果解释出现偏差。"
    />

    <section class="teacher-page__content">
      <TeacherIndicatorSelector
        :course-id="selectedCourseId"
        :subject="subject"
        :courses="courses"
        @subject-change="subject = $event"
      />
    </section>
  </div>
</template>

<style scoped>
.teacher-page {
  display: grid;
  gap: 20px;
}

.teacher-page__content {
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
