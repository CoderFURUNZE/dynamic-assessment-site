<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import TeacherIntroHero from "../components/TeacherIntroHero.vue";
import TeacherStageManager from "../components/TeacherStageManager.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

const selectedCourseId = computed<number | null>(
  () => courses.value.find((item) => item.title === subject.value)?.id ?? null,
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

function syncQuery(nextSubject?: string) {
  if (typeof nextSubject === "string") {
    subject.value = nextSubject;
  }
  saveTeacherSubject(subject.value);
  router.replace({ path: "/teacher/stages", query: buildTeacherSubjectQuery(subject.value) });
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
      title="阶段设置"
      pill="阶段流程"
      description="先设定课程阶段，再让后续的导入、结果和审核都基于同一套阶段口径运行。"
    />
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
  gap: 20px;
}

.teacher-page__panel {
  min-width: 0;
  padding: 18px;
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}
</style>
