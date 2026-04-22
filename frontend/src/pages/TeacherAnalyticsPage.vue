<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminAnalyticsOverview from "../components/AdminAnalyticsOverview.vue";
import HintButton from "../components/HintButton.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);

const heroStats = computed(() => [
  {
    label: "课程数",
    value: `${courses.value.length || 0}`,
    hint: "当前可切换的课程数量",
  },
  {
    label: "分析模式",
    value: "班级总览",
    hint: "先看整体，再决定处理对象",
  },
  {
    label: "下一步",
    value: subject.value ? "查看学生详情" : "先选择课程",
    hint: subject.value ? `${subject.value} 已可进入追踪` : "选中课程后自动同步分析对象",
  },
]);

const cockpitCards = computed(() => [
  {
    eyebrow: "班级画像",
    title: "先看整体走势",
    desc: "把风险学生、薄弱知识点和阶段表现放在一个入口里。",
    action: "刷新总览",
    handler: () => loadCourses(),
  },
  {
    eyebrow: "学生追踪",
    title: "直接进入个体详情",
    desc: "从班级总览切到学生详情，连续查看画像信号和学习表现。",
    action: "学生详情",
    handler: () => router.push({ path: "/teacher/students", query: { ...buildTeacherSubjectQuery(subject.value), tab: "detail" } }),
  },
  {
    eyebrow: "阶段联动",
    title: "返回阶段评价页",
    desc: "需要回看导入、指标或阶段配置时，直接回到评价工作区。",
    action: "阶段评价",
    handler: () => router.push({ path: "/teacher/evaluation", query: { ...buildTeacherSubjectQuery(subject.value), tab: "behavior" } }),
  },
]);

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
  const nextQuery = { ...buildTeacherSubjectQuery(subject.value), tab: "class" };
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "class").trim();
  if (
    route.path === "/teacher/students"
    && currentSubject === String(nextQuery.subject || "").trim()
    && currentTab === "class"
  ) {
    return;
  }
  saveTeacherSubject(subject.value);
  router.replace({ path: "/teacher/students", query: nextQuery });
}

watch(subject, () => syncQuery());
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);

onMounted(loadCourses);
</script>

<template>
  <div class="teacher-page">
    <section class="analytics-toolbar">
      <div class="analytics-toolbar__copy">
        <span class="analytics-title__eyebrow">班级总览</span>
        <div class="analytics-title">
          <h1>教师分析台</h1>
          <p>快速识别风险学生、薄弱知识点和阶段变化，先看整体，再进入个体处理。</p>
        </div>
        <div class="analytics-toolbar__meta">
          <span class="analytics-meta-pill analytics-meta-pill--course">{{ subject || "未选择课程" }}</span>
          <span class="analytics-meta-pill analytics-meta-pill--grade">{{ grade }}</span>
        </div>
        <div class="analytics-hero-stats">
          <article v-for="item in heroStats" :key="item.label" class="analytics-hero-stat">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.hint }}</p>
          </article>
        </div>
      </div>

      <div class="analytics-toolbar__panel">
        <div class="analytics-toolbar__panel-head">
          <span>当前操作</span>
          <strong>统一从这里切课程、刷新数据和进入详情</strong>
        </div>
        <div class="analytics-toolbar__course">
          <span>课程</span>
          <el-select v-model="subject" placeholder="请选择课程" size="large" style="width: 240px">
            <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
          </el-select>
        </div>
        <div class="analytics-toolbar__actions">
          <HintButton size="small" tip="刷新当前班级分析数据" @click="loadCourses">刷新</HintButton>
          <HintButton
            size="small"
            tip="切换到学生详情视图"
            @click="router.push({ path: '/teacher/students', query: { ...buildTeacherSubjectQuery(subject), tab: 'detail' } })"
          >
            学生详情
          </HintButton>
        </div>
      </div>
    </section>

    <section class="analytics-cockpit-grid">
      <article v-for="card in cockpitCards" :key="card.eyebrow" class="analytics-cockpit-card">
        <span class="analytics-cockpit-card__eyebrow">{{ card.eyebrow }}</span>
        <h3>{{ card.title }}</h3>
        <p>{{ card.desc }}</p>
        <button type="button" class="analytics-cockpit-card__action" @click="card.handler">{{ card.action }}</button>
      </article>
    </section>

    <section class="edu-panel analytics-panel">
      <AdminAnalyticsOverview
        :subject="subject"
        :grade="grade"
        :show-student-detail-action="true"
        @view-student="(id:number) => router.push({ path: '/teacher/students', query: { user_id: String(id), subject: subject || undefined, tab: 'detail' } })"
      />
    </section>
  </div>
</template>

<style scoped>
.teacher-page {
  display: grid;
  gap: 18px;
}

.analytics-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(300px, 0.75fr);
  gap: 18px;
  padding: 20px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 20px;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.2), transparent 24%),
    radial-gradient(circle at bottom right, rgba(187, 247, 208, 0.18), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.analytics-toolbar__copy {
  display: grid;
  align-content: start;
  gap: 12px;
}

.analytics-toolbar__panel {
  display: grid;
  gap: 14px;
  align-content: start;
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(248, 251, 255, 0.96) 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.analytics-toolbar__course {
  display: grid;
  gap: 8px;
}

.analytics-toolbar__course span,
.analytics-toolbar__panel-head span,
.analytics-title__eyebrow,
.analytics-hero-stat span,
.analytics-cockpit-card__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.analytics-toolbar__course span,
.analytics-toolbar__panel-head span,
.analytics-hero-stat span {
  color: #64748b;
}

.analytics-title {
  display: grid;
  gap: 10px;
}

.analytics-title__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 8px 12px;
  border-radius: 999px;
  color: #166534;
  background: rgba(187, 247, 208, 0.42);
}

.analytics-title h1 {
  margin: 0;
  font-size: clamp(24px, 3.2vw, 36px);
  line-height: 1.08;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #0f172a;
}

.analytics-title p {
  margin: 0;
  max-width: 54ch;
  font-size: 14px;
  line-height: 1.55;
  color: #64748b;
}

.analytics-toolbar__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.analytics-meta-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.86);
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.analytics-meta-pill--course {
  color: #2563eb;
  background: rgba(219, 234, 254, 0.72);
}

.analytics-hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.analytics-hero-stat {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.analytics-hero-stat strong {
  display: block;
  margin-top: 10px;
  font-size: 24px;
  line-height: 1.05;
  color: #0f172a;
}

.analytics-hero-stat p {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.analytics-toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.analytics-toolbar__panel-head {
  display: grid;
  gap: 6px;
}

.analytics-toolbar__panel-head strong {
  font-size: 18px;
  line-height: 1.35;
  color: #0f172a;
}

.analytics-cockpit-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.analytics-cockpit-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.16), transparent 22%),
    radial-gradient(circle at bottom right, rgba(187, 247, 208, 0.16), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
}

.analytics-cockpit-card__eyebrow {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  padding: 0 11px;
  border-radius: 999px;
  background: rgba(219, 234, 254, 0.72);
  color: #2563eb;
}

.analytics-cockpit-card h3 {
  margin: 14px 0 8px;
  font-size: 22px;
  line-height: 1.15;
  color: #0f172a;
}

.analytics-cockpit-card p {
  margin: 0;
  min-height: 66px;
  color: #64748b;
  line-height: 1.7;
}

.analytics-cockpit-card__action {
  margin-top: 18px;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #334155;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.analytics-cockpit-card__action:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.28);
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.08);
}

.analytics-panel {
  padding: 0;
  border: 0;
  box-shadow: none;
  background: transparent;
}

:deep(.analytics-toolbar .el-select__wrapper) {
  min-height: 44px;
  border-radius: 14px;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.24) inset !important;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
}

:deep(.analytics-toolbar .el-select__placeholder),
:deep(.analytics-toolbar .el-select__selected-item) {
  color: #334155;
  font-weight: 600;
}

:deep(.analytics-toolbar .el-button) {
  border-radius: 14px;
  min-height: 40px;
  border-width: 1px;
  font-weight: 700;
}

:deep(.analytics-toolbar__actions .hint-button),
:deep(.analytics-toolbar__actions .el-button) {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
  color: #334155 !important;
  border-color: rgba(148, 163, 184, 0.24) !important;
  box-shadow: none;
}

:deep(.analytics-toolbar__actions .hint-button:hover),
:deep(.analytics-toolbar__actions .el-button:hover) {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.28) !important;
  color: #1d4ed8 !important;
}

@media (max-width: 768px) {
  .analytics-toolbar {
    grid-template-columns: 1fr;
    padding: 20px 18px;
  }

  .analytics-hero-stats,
  .analytics-cockpit-grid {
    grid-template-columns: 1fr;
  }

  .analytics-toolbar__panel {
    padding: 18px 16px;
  }
}
</style>
