<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import QuestionnairePane from "../components/QuestionnairePane.vue";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();

const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);
const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);
const questionnaireSummary = computed(() => [
  { label: "当前课程", value: subject.value || "请选择课程" },
  { label: "填写内容", value: "状态 / 兴趣 / 策略" },
  { label: "保存后", value: "更新学习画像" },
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
    path: "/student/questionnaire",
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
  <div class="student-questionnaire-page">
    <section class="student-questionnaire-page__hero">
      <div class="student-questionnaire-page__hero-copy">
        <span class="student-questionnaire-page__eyebrow">问卷填写</span>
        <h1>本次补充内容</h1>
        <p>{{ selectedCourseId ? `当前课程：${subject}。优先完成最相关题项，保存后会更新学习画像。` : "请先选择课程，再完成补充问卷。" }}</p>
      </div>

      <section class="student-questionnaire-page__summary" aria-label="问卷概况">
        <article v-for="item in questionnaireSummary" :key="item.label" class="student-questionnaire-page__summary-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </section>

      <div class="student-questionnaire-page__hero-panel">
        <el-select v-model="subject" placeholder="请选择课程" size="large">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <div class="student-questionnaire-page__hero-actions">
          <el-button @click="router.push({ path: '/student/dashboard', query: studentQuery() })">返回学习中心</el-button>
          <el-button type="primary" @click="router.push({ path: '/student/report', query: studentQuery({ subject: subject || undefined }) })">
            查看学习报告
          </el-button>
        </div>
      </div>
    </section>

    <section class="student-questionnaire-page__content panel-card">
      <QuestionnairePane :course-id="selectedCourseId" />
    </section>
  </div>
</template>

<style scoped>
.student-questionnaire-page {
  display: grid;
  gap: 18px;
  color: #102033;
}

.student-questionnaire-page__hero,
.student-questionnaire-page__summary-card,
.student-questionnaire-page__content {
  border-radius: 16px;
  border: 1px solid rgba(120, 142, 166, 0.22);
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(20, 35, 58, 0.07);
  min-width: 0;
  max-width: 100%;
}

.student-questionnaire-page__hero {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(320px, 0.9fr) auto;
  gap: 16px;
  align-items: center;
  padding: 18px;
  background:
    radial-gradient(circle at 0% 0%, rgba(37, 99, 235, 0.11), transparent 30%),
    radial-gradient(circle at 92% 0%, rgba(34, 197, 94, 0.13), transparent 26%),
    linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
}

.student-questionnaire-page__hero-copy {
  display: grid;
  gap: 10px;
}

.student-questionnaire-page__eyebrow,
.student-questionnaire-page__content-head span {
  display: inline-flex;
  width: fit-content;
  padding: 7px 11px;
  border-radius: 999px;
  background: #ecfdf5;
  border: 1px solid rgba(34, 197, 94, 0.22);
  color: #166534;
  font-size: 12px;
  font-weight: 800;
}

.student-questionnaire-page__hero-copy h1 {
  margin: 0;
  font-size: clamp(26px, 3vw, 36px);
  line-height: 1.12;
  color: #0f172a;
}

.student-questionnaire-page__hero-copy p,
.student-questionnaire-page__hero-panel p,
.student-questionnaire-page__content-head p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.student-questionnaire-page__hero-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.78);
}

.student-questionnaire-page__hero-panel :deep(.el-select),
.student-questionnaire-page__hero-panel :deep(.el-select__wrapper) {
  width: 260px;
}

.student-questionnaire-page__hero-panel :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 12px;
  background: #f8fafc !important;
  box-shadow: 0 0 0 1px rgba(120, 142, 166, 0.22) inset !important;
}

.student-questionnaire-page__hero-panel span,
.student-questionnaire-page__summary-card span {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.student-questionnaire-page__hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 4px;
}

.student-questionnaire-page__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.student-questionnaire-page__summary-card {
  min-height: 76px;
  padding: 12px;
  border-radius: 12px;
  display: grid;
  gap: 4px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: none;
}

.student-questionnaire-page__summary-card strong {
  font-size: 16px;
  line-height: 1.2;
  color: #0f172a;
  overflow-wrap: break-word;
}

.student-questionnaire-page__content {
  padding: 0;
  overflow: hidden;
}

.student-questionnaire-page__content-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
}

.student-questionnaire-page__content-head h2 {
  margin: 8px 0 0;
  font-size: 28px;
  line-height: 1.1;
  color: #0f172a;
}

@media (max-width: 1180px) {
  .student-questionnaire-page__hero {
    grid-template-columns: 1fr;
  }

  .student-questionnaire-page__hero-panel {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .student-questionnaire-page__summary {
    grid-template-columns: 1fr;
  }

  .student-questionnaire-page__content-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
