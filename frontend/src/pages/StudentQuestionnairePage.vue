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
  { label: "补充内容", value: "学习状态、兴趣和策略" },
  { label: "保存后", value: "自动更新课程画像" },
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
        <span class="student-questionnaire-page__eyebrow">学习画像</span>
        <h1>用一页问卷补充你的学习状态</h1>
        <p>保留课程选择、填写说明和主问卷区，减少来回切换，完成后会直接更新课程画像。</p>
      </div>

      <div class="student-questionnaire-page__hero-panel">
        <span>选择课程</span>
        <el-select v-model="subject" placeholder="请选择课程" size="large">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <p>
          {{ selectedCourseId ? `当前课程：${subject}，保存后会自动更新画像结果。` : "请先选择课程，再完成补充问卷。" }}
        </p>
        <div class="student-questionnaire-page__hero-actions">
          <el-button @click="router.push({ path: '/student/dashboard', query: studentQuery() })">返回学习中心</el-button>
          <el-button type="primary" @click="router.push({ path: '/student/report', query: studentQuery({ subject: subject || undefined }) })">
            查看学习报告
          </el-button>
        </div>
      </div>
    </section>

    <section class="student-questionnaire-page__summary">
      <article v-for="item in questionnaireSummary" :key="item.label" class="student-questionnaire-page__summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="student-questionnaire-page__content panel-card">
      <header class="student-questionnaire-page__content-head">
        <div>
          <span>问卷填写</span>
          <h2>本次补充内容</h2>
        </div>
        <p>优先完成与当前课程最相关的题项，不需要在多个模块之间来回跳转。</p>
      </header>

      <QuestionnairePane :course-id="selectedCourseId" />
    </section>
  </div>
</template>

<style scoped>
.student-questionnaire-page {
  display: grid;
  gap: 20px;
}

.student-questionnaire-page__hero,
.student-questionnaire-page__summary-card,
.student-questionnaire-page__content {
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
  min-width: 0;
  max-width: 100%;
}

.student-questionnaire-page__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: 18px;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.22), transparent 30%),
    radial-gradient(circle at right bottom, rgba(187, 247, 208, 0.16), transparent 26%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  background: rgba(187, 247, 208, 0.42);
  color: #166534;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.student-questionnaire-page__hero-copy h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.06;
  letter-spacing: -0.04em;
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
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  gap: 16px;
}

.student-questionnaire-page__summary-card {
  padding: 18px 20px;
  display: grid;
  gap: 8px;
}

.student-questionnaire-page__summary-card strong {
  font-size: 22px;
  line-height: 1.2;
  color: #0f172a;
}

.student-questionnaire-page__content {
  padding: 22px;
  display: grid;
  gap: 18px;
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

@media (max-width: 960px) {
  .student-questionnaire-page__hero,
  .student-questionnaire-page__summary {
    grid-template-columns: 1fr;
  }

  .student-questionnaire-page__content-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
