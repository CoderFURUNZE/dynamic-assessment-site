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
  { label: "课程", value: currentCourse.value?.title || "请选择" },
  { label: "内容", value: "阶段结果" },
  { label: "动作", value: subject.value ? "查看建议" : "选择课程" },
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
        <h1>{{ currentCourse?.title || "请选择课程" }}</h1>
        <p>集中查看阶段结果、知识图谱覆盖、老师建议和下一步学习安排。</p>
      </div>

      <div class="student-report-page__highlights" aria-label="报告概况">
        <article v-for="item in reportHighlights" :key="item.label" class="student-report-page__highlight-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>

      <div class="student-report-page__hero-panel">
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

    <section class="student-report-page__content panel-card">
      <LearnerReportPane :subject="subject" :grade="grade" />
    </section>
  </div>
</template>

<style scoped>
.student-report-page {
  --report-theme-surface: #ffffff;
  --report-theme-surface-soft: #f8fafc;
  --report-theme-surface-muted: #eef4ff;
  --report-theme-surface-accent: #ecfdf5;
  --report-theme-border: rgba(99, 120, 153, 0.2);
  --report-theme-border-strong: rgba(34, 197, 94, 0.3);
  --report-theme-ink: #102033;
  --report-theme-ink-soft: #52647a;
  --report-theme-blue: #2563eb;
  --report-theme-green: #22c55e;
  --report-theme-amber: #f59e0b;
  display: grid;
  gap: 18px;
}

.student-report-page__hero,
.student-report-page__highlight-card,
.student-report-page__content {
  border-radius: 16px;
  border: 1px solid var(--report-theme-border);
  background: #ffffff;
  box-shadow: 0 16px 36px rgba(20, 35, 58, 0.08);
}

.student-report-page__hero {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(280px, 0.72fr) minmax(320px, 0.9fr);
  gap: 16px;
  align-items: center;
  padding: 18px;
  background:
    radial-gradient(circle at 4% 0%, rgba(37, 99, 235, 0.12), transparent 30%),
    radial-gradient(circle at 88% 0%, rgba(34, 197, 94, 0.12), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
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
  background: #eefbf3;
  border: 1px solid rgba(34, 197, 94, 0.18);
  color: #166534;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.student-report-page__hero-copy h1 {
  margin: 0;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.12;
  color: var(--report-theme-ink);
  overflow-wrap: break-word;
}

.student-report-page__hero-copy p,
.student-report-page__content-head p {
  margin: 0;
  max-width: 58ch;
  color: var(--report-theme-ink-soft);
  line-height: 1.6;
}

.student-report-page__hero-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--report-theme-border);
  background: rgba(255, 255, 255, 0.78);
}

.student-report-page__hero-panel span,
.student-report-page__highlight-card span {
  font-size: 12px;
  color: var(--report-theme-ink-soft);
  font-weight: 700;
}

.student-report-page__hero-panel :deep(.el-select),
.student-report-page__hero-panel :deep(.el-select__wrapper) {
  width: 260px;
}

.student-report-page__hero-panel :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 12px;
  background: var(--report-theme-surface-soft) !important;
  box-shadow: 0 0 0 1px var(--report-theme-border) inset !important;
}

.student-report-page__hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.student-report-page__hero-actions :deep(.el-button) {
  min-height: 40px;
  padding-inline: 18px;
  border-radius: 14px;
}

.student-report-page__hero-actions :deep(.el-button:not(.el-button--primary)) {
  border-color: var(--report-theme-border);
  background: var(--report-theme-surface);
  color: #475569;
}

.student-report-page__hero-actions :deep(.el-button--primary) {
  border-color: var(--report-theme-border-strong);
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #ffffff;
}

.student-report-page__highlights {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.student-report-page__highlight-card {
  display: grid;
  gap: 4px;
  min-height: 76px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: none;
}

.student-report-page__highlight-card strong,
.student-report-page__content-head h2 {
  margin: 0;
  font-size: 17px;
  color: var(--report-theme-ink);
  line-height: 1.35;
  overflow-wrap: break-word;
}

.student-report-page__content {
  padding: 0;
  background: transparent;
  overflow: hidden;
}

.student-report-page__content-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 18px;
}

.student-report-page :deep(.report-shell) {
  border: 0;
  border-radius: 16px;
  background: linear-gradient(180deg, var(--report-theme-surface-soft) 0%, var(--report-theme-surface) 100%);
}

.student-report-page :deep(.report-shell .el-card__header) {
  border-bottom-color: var(--report-theme-border);
  background: linear-gradient(180deg, var(--report-theme-surface-accent) 0%, var(--report-theme-surface-soft) 100%);
}

.student-report-page :deep(.report-hero) {
  background: linear-gradient(180deg, var(--report-theme-surface) 0%, var(--report-theme-surface-soft) 100%);
}

.student-report-page :deep(.hero-label),
.student-report-page :deep(.hero-stage),
.student-report-page :deep(.hero-text) {
  color: var(--report-theme-ink-soft);
}

.student-report-page :deep(.hero-title) {
  color: #243449;
}

.student-report-page :deep(.hero-tag) {
  border-color: var(--report-theme-border);
  background: var(--report-theme-surface-accent);
  color: #166534;
}

.student-report-page :deep(.hero-metric) {
  border-color: var(--report-theme-border);
  background: linear-gradient(180deg, var(--report-theme-surface) 0%, var(--report-theme-surface-soft) 100%);
}

.student-report-page :deep(.hero-metric span) {
  color: var(--report-theme-ink-soft);
}

.student-report-page :deep(.hero-metric strong) {
  color: #243449;
}

.student-report-page :deep(.report-ability-provenance) {
  border-color: var(--report-theme-border);
  --el-collapse-header-bg-color: var(--report-theme-surface-soft);
}

.student-report-page :deep(.detail-tabs .el-tabs__item) {
  border-color: var(--report-theme-border);
  background: var(--report-theme-surface-soft);
  color: var(--report-theme-ink-soft);
}

.student-report-page :deep(.detail-tabs .el-tabs__item.is-active) {
  background: var(--report-theme-surface-accent);
  border-color: var(--report-theme-border-strong);
  color: #166534;
  box-shadow: 0 8px 14px rgba(15, 23, 42, 0.06);
}

.student-report-page :deep(.dimension-board),
.student-report-page :deep(.stage-board),
.student-report-page :deep(.config-board),
.student-report-page :deep(.feedback-board),
.student-report-page :deep(.advice-board) {
  background: linear-gradient(180deg, var(--report-theme-surface-soft) 0%, var(--report-theme-surface) 100%);
}

.student-report-page :deep(.dimension-item),
.student-report-page :deep(.kal-card),
.student-report-page :deep(.stage-card),
.student-report-page :deep(.feedback-card),
.student-report-page :deep(.advice-card),
.student-report-page :deep(.radar-card),
.student-report-page :deep(.timeline-card),
.student-report-page :deep(.portrait-card),
.student-report-page :deep(.summary-card),
.student-report-page :deep(.score-card) {
  border-color: var(--report-theme-border);
  background: linear-gradient(180deg, var(--report-theme-surface) 0%, var(--report-theme-surface-soft) 100%);
}

.student-report-page :deep(.board-title),
.student-report-page :deep(.kal-card__title),
.student-report-page :deep(.config-item__title),
.student-report-page :deep(.mi-card__title),
.student-report-page :deep(.feedback-tag) {
  color: #243449;
}

.student-report-page :deep(.dimension-top),
.student-report-page :deep(.stage-card__index),
.student-report-page :deep(.stage-card__metrics),
.student-report-page :deep(.config-item__meta),
.student-report-page :deep(.config-item__hint),
.student-report-page :deep(.questionnaire-row__value),
.student-report-page :deep(.questionnaire-row__hint),
.student-report-page :deep(.feedback-meta),
.student-report-page :deep(.mi-intro),
.student-report-page :deep(.mi-card__meta),
.student-report-page :deep(.mi-item__top),
.student-report-page :deep(.mi-item__meta),
.student-report-page :deep(.report-tip-inline),
.student-report-page :deep(.empty-help__text),
.student-report-page :deep(.report-empty__tip) {
  color: var(--report-theme-ink-soft);
}

.student-report-page :deep(.dimension-bar),
.student-report-page :deep(.mi-item__bar) {
  background: #dbeafe;
}

.student-report-page :deep(.config-item__chips span),
.student-report-page :deep(.feedback-tag) {
  background: var(--report-theme-surface-accent);
  border-color: var(--report-theme-border);
  color: #243449;
}

.student-report-page :deep(.config-item),
.student-report-page :deep(.mi-card),
.student-report-page :deep(.mi-item),
.student-report-page :deep(.advice-item),
.student-report-page :deep(.hero-metric) {
  border-color: var(--report-theme-border);
  background: linear-gradient(180deg, var(--report-theme-surface) 0%, var(--report-theme-surface-soft) 100%);
}

.student-report-page :deep(.mi-card__score) {
  color: #8a6a34;
}

.student-report-page :deep(.report-empty),
.student-report-page :deep(.empty-help),
.student-report-page :deep(.empty-help--compact) {
  background: transparent;
}

.student-report-page :deep(.empty-help .el-empty),
.student-report-page :deep(.report-empty .el-empty) {
  --el-empty-fill-color-0: #f8fbff;
  --el-empty-fill-color-1: #eef6ff;
  --el-empty-fill-color-2: #dbeafe;
  --el-empty-fill-color-3: #c7ddfb;
  --el-empty-fill-color-4: #b7d3f8;
  --el-empty-fill-color-5: #a8cbf4;
  --el-empty-fill-color-6: #98c3f0;
  --el-empty-fill-color-7: #86efac;
  --el-empty-fill-color-8: #bfdbfe;
  --el-empty-fill-color-9: #eaf3ff;
}

.student-report-page :deep(.portrait-card),
.student-report-page :deep(.timeline-card),
.student-report-page :deep(.radar-card) {
  border-color: var(--report-theme-border);
  background: linear-gradient(180deg, var(--report-theme-surface) 0%, var(--report-theme-surface-soft) 100%);
}

.student-report-page :deep(.portrait-card .el-empty),
.student-report-page :deep(.timeline-card .el-empty),
.student-report-page :deep(.radar-card .el-empty) {
  --el-empty-fill-color-0: #f8fbff;
  --el-empty-fill-color-1: #eef6ff;
  --el-empty-fill-color-2: #dbeafe;
  --el-empty-fill-color-3: #c7ddfb;
  --el-empty-fill-color-4: #b7d3f8;
  --el-empty-fill-color-5: #a8cbf4;
  --el-empty-fill-color-6: #98c3f0;
  --el-empty-fill-color-7: #86efac;
  --el-empty-fill-color-8: #bfdbfe;
  --el-empty-fill-color-9: #eaf3ff;
}

.student-report-page :deep(.questionnaire-row .el-input__wrapper),
.student-report-page :deep(.questionnaire-row .el-textarea__inner) {
  background: var(--report-theme-surface-soft) !important;
  box-shadow: 0 0 0 1.5px var(--report-theme-border) inset !important;
}

.student-report-page :deep(.questionnaire-row .el-radio-button__inner) {
  border-color: var(--report-theme-border);
  background: var(--report-theme-surface-soft);
  color: var(--report-theme-ink-soft);
}

.student-report-page :deep(.questionnaire-row .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #edf7cf 0%, #fff1de 100%);
  border-color: var(--report-theme-border-strong);
  color: #243449;
  box-shadow: none;
}

@media (max-width: 1200px) {
  .student-report-page__hero {
    grid-template-columns: 1fr;
  }

  .student-report-page__hero-panel {
    justify-content: flex-start;
  }

  .student-report-page__hero-panel :deep(.el-select),
  .student-report-page__hero-panel :deep(.el-select__wrapper) {
    width: min(100%, 360px);
  }
}

@media (max-width: 720px) {
  .student-report-page__highlights {
    grid-template-columns: 1fr;
  }

  .student-report-page__content-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
