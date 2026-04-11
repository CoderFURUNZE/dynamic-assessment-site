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
      badge="学习报告"
      title="学习报告"
      meta-text="按课程查看评价结果、学习反馈与后续建议"
      @change="syncQuery"
    >
      <el-button @click="router.push({ path: '/student/dashboard', query: studentQuery() })">返回学习中心</el-button>
      <el-button @click="router.push({ path: '/student/questionnaire', query: studentQuery({ subject: subject || undefined }) })">
        去补充问卷
      </el-button>
    </WorkspaceTopbar>

    <section class="student-section-page__overview panel-card">
      <article class="student-section-page__overview-card">
        <span>当前课程</span>
        <strong>{{ subject || "未选择课程" }}</strong>
      </article>
      <article class="student-section-page__overview-card">
        <span>主要内容</span>
        <strong>学习结果与反馈建议</strong>
      </article>
      <article class="student-section-page__overview-card">
        <span>下一步</span>
        <strong>根据报告调整学习重点</strong>
      </article>
    </section>

    <PageSectionCard eyebrow="学习报告" title="学习结果" description="把课程表现、阶段变化和建议放在同一个区域查看。">
      <LearnerReportPane :subject="subject" :grade="grade" />
    </PageSectionCard>
  </div>
</template>

<style scoped>
.student-section-page {
  display: grid;
  gap: 20px;
}

.student-section-page__overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 14px;
}

.student-section-page__overview-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid #dce6f5;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.student-section-page__overview-card span {
  font-size: 12px;
  color: var(--app-text-soft);
}

.student-section-page__overview-card strong {
  font-size: 16px;
  color: var(--app-text-main);
  line-height: 1.35;
}

@media (max-width: 900px) {
  .student-section-page__overview {
    grid-template-columns: 1fr;
  }
}
</style>
