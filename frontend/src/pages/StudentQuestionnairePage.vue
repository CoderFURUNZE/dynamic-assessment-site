<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import QuestionnairePane from "../components/QuestionnairePane.vue";
import PageSectionCard from "../components/PageSectionCard.vue";

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
    const querySubject = String(route.query.subject || "");
    subject.value = querySubject || subject.value || courses.value[0]?.title || "";
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
  router.replace({
    path: "/student/questionnaire",
    query: {
      subject: subject.value || undefined,
      preview: preview || undefined,
    },
  });
}

watch(subject, () => syncQuery());

onMounted(async () => {
  await loadCourses();
});
</script>

<template>
  <div class="student-section-page">
    <WorkspaceTopbar
      v-model="subject"
      :courses="courses"
      badge="Student Questionnaire"
      title="补充问卷"
      @change="syncQuery"
    >
      <el-button @click="router.push({ path: '/student/overview', query: studentQuery() })">返回学习首页</el-button>
      <el-button type="primary" @click="router.push({ path: '/student/report', query: studentQuery({ subject: subject || undefined }) })">
        去看学习报告
      </el-button>
    </WorkspaceTopbar>

    <PageSectionCard eyebrow="Questionnaire" title="补充信息">
      <QuestionnairePane :course-id="selectedCourseId" />
    </PageSectionCard>
  </div>
</template>

<style scoped>
.student-section-page {
  display: grid;
  gap: 20px;
}
</style>
