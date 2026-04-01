<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import LearnerReportPane from "../components/LearnerReportPane.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

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
    subject.value = resolveStudentSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

function studentQuery(extra: Record<string, string | undefined> = {}) {
  const preview = String(route.query.preview || "");
  return {
    ...(preview === "1" ? { preview: "1" } : {}),
    ...extra,
  };
}

function syncQuery() {
  const preview = String(route.query.preview || "");
  if (subject.value) saveStudentSubject(subject.value);
  router.replace({
    path: "/student/report",
    query: {
      subject: subject.value || undefined,
      preview: preview || undefined,
    },
  });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);

onMounted(async () => {
  await loadCourses();
});
</script>

<template>
  <div class="student-section-page">
    <WorkspaceTopbar
      v-model="subject"
      :courses="courses"
      badge="Student Report"
      title="学习报告"
      @change="syncQuery"
    >
      <el-button @click="router.push({ path: '/student/dashboard', query: studentQuery() })">返回学习台</el-button>
      <el-button @click="router.push({ path: '/student/questionnaire', query: studentQuery({ subject: subject || undefined }) })">
        去补充问卷
      </el-button>
    </WorkspaceTopbar>

    <PageSectionCard eyebrow="Report" title="学习结果">
      <LearnerReportPane :subject="subject" :grade="grade" />
    </PageSectionCard>
  </div>
</template>

<style scoped>
.student-section-page {
  display: grid;
  gap: 20px;
}
</style>
