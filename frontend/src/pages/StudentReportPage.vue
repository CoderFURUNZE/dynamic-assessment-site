<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import LearnerReportPane from "../components/LearnerReportPane.vue";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

type Course = {
  id: number;
  code: string;
  title: string;
  active?: boolean;
  enroll_status?: string;
};

const route = useRoute();
const router = useRouter();

const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);
const reportHighlights = computed(() => [
  { label: "当前课程", value: currentCourse.value?.title || "请选择课程" },
  { label: "查看内容", value: "学习结果与反馈建议" },
  { label: "建议动作", value: subject.value ? "根据报告调整重点" : "先选择课程" },
]);

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
  },
);

onMounted(async () => {
  await loadCourses();
});
</script>

<template>
  <div class="student-report-page">
    <section class="student-report-page__hero">
      <div class="student-report-page__hero-copy">
        <span class="student-report-page__eyebrow">学习报告</span>
        <h1>先看结果，再决定下一步怎么学</h1>
        <p>按课程查看学习表现、阶段变化和后续建议，页面只保留一个主内容区，方便连续阅读。</p>
      </div>

      <div class="student-report-page__hero-panel">
        <span>选择课程</span>
        <el-select v-model="subject" placeholder="请选择课程" size="large">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <div class="student-report-page__hero-actions">
          <el-button @click="router.push({ path: '/student/dashboard', query: studentQuery() })">返回学习中心</el-button>
          <el-button @click="router.push({ path: '/student/questionnaire', query: studentQuery({ subject: subject || undefined }) })">
            去补充问卷
          </el-button>
        </div>
      </div>
    </section>

    <section class="student-report-page__highlights">
      <article v-for="item in reportHighlights" :key="item.label" class="student-report-page__highlight-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="student-report-page__content panel-card">
      <header class="student-report-page__content-head">
        <div>
          <span>报告内容</span>
          <h2>{{ subject || "请选择课程后查看" }}</h2>
        </div>
        <p>把课程表现、阶段变化和建议放在一个区域里，避免多层切换。</p>
      </header>

      <LearnerReportPane :subject="subject" :grade="grade" />
    </section>
  </div>
</template>

<style scoped>
.student-report-page {
  display: grid;
  gap: 18px;
}

.student-report-page__hero,
.student-report-page__highlight-card,
.student-report-page__content {
  border-radius: 32px;
  border: 3px solid #1f2937;
  background: #fffdf8;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.student-report-page__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 18px;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(94, 234, 212, 0.18), transparent 30%),
    linear-gradient(180deg, #fff9f1 0%, #fffdf8 100%);
}

.student-report-page__hero-copy {
  display: grid;
  gap: 8px;
}

.student-report-page__eyebrow,
.student-report-page__content-head span {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #d7f9a8;
  color: #1f2937;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.student-report-page__hero-copy h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.05;
  letter-spacing: -0.04em;
  color: #1f2937;
}

.student-report-page__hero-copy p,
.student-report-page__content-head p {
  margin: 0;
  max-width: 58ch;
  color: #5f6b7a;
  line-height: 1.6;
}

.student-report-page__hero-panel {
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 18px;
  border-radius: 24px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.student-report-page__hero-panel span,
.student-report-page__highlight-card span {
  font-size: 12px;
  color: #6b7280;
  font-weight: 700;
}

.student-report-page__hero-panel :deep(.el-select),
.student-report-page__hero-panel :deep(.el-select__wrapper) {
  width: 100%;
}

.student-report-page__hero-panel :deep(.el-select__wrapper) {
  min-height: 48px;
  border-radius: 16px;
}

.student-report-page__hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.student-report-page__hero-actions :deep(.el-button) {
  min-height: 44px;
  padding-inline: 18px;
  border-radius: 14px;
}

.student-report-page__highlights {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.student-report-page__highlight-card {
  display: grid;
  gap: 8px;
  padding: 18px 20px;
  min-height: 106px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.student-report-page__highlight-card strong,
.student-report-page__content-head h2 {
  margin: 0;
  font-size: 18px;
  color: #1f2937;
  line-height: 1.35;
}

.student-report-page__content {
  padding: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.student-report-page__content-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 18px;
}

@media (max-width: 900px) {
  .student-report-page__hero,
  .student-report-page__highlights {
    grid-template-columns: 1fr;
  }

  .student-report-page__content-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
