<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { DataAnalysis, EditPen, Medal, User } from "@element-plus/icons-vue";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import HintButton from "../components/HintButton.vue";
import PortraitRadarChart from "../components/PortraitRadarChart.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type CourseItem = { id: number; code: string; title: string };
type StudentItem = {
  user_id: number;
  username: string;
  full_name: string;
  student_no: string;
  class_name: string;
  persona_label: string;
  dynamic_score: number;
  course_mastery: number;
  risk_level: string;
  suggested_score: number;
  confirmed_score?: number | null;
  confirmed_level?: string;
  confirmed_at?: string | null;
};

const router = useRouter();
const route = useRoute();
const grade = ref("通用");
const subject = ref("");
const courses = ref<CourseItem[]>([]);
const students = ref<StudentItem[]>([]);
const selectedUserId = ref<number | null>(null);
const detailLoading = ref(false);
const listLoading = ref(false);
const saving = ref(false);
const detail = ref<any | null>(null);
const form = reactive({
  confirmedScorePercent: 0,
  confirmedLevel: "",
  recommendationSummary: "",
  comment: "",
});

const levelOptions = ["优秀", "良好", "中等", "需关注"];
const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);
const stageHistory = computed(() => detail.value?.stage_history ?? []);
const finalDimensions = computed(() => detail.value?.profile?.final_portrait_dimensions ?? []);
const termSummary = computed(() => detail.value?.profile?.term_summary ?? {});
const recommendationClosure = computed(() => detail.value?.recommendation_closure ?? {});
const selectedStudent = computed(() => students.value.find((item) => item.user_id === selectedUserId.value) ?? null);
const canConfirmFinalScore = computed(() => Number(termSummary.value?.stage_count || 0) > 0);
const confirmedCount = computed(() => students.value.filter((item) => item.confirmed_score != null).length);
const metaText = computed(() => `当前课程：${subject.value || "未选择"} · 已确认 ${confirmedCount.value}/${students.value.length}`);

const summaryCards = computed(() => [
  { label: "建议得分", value: `${toPercent(termSummary.value?.final_score_reference)}%`, icon: DataAnalysis, tone: "blue" },
  { label: "已采样阶段", value: String(termSummary.value?.stage_count || 0), icon: EditPen, tone: "amber" },
  { label: "最终等级", value: detail.value?.final_score_confirmation?.confirmed_level || form.confirmedLevel || "待确认", icon: Medal, tone: "green" },
  { label: "当前学生", value: selectedStudent.value?.full_name || selectedStudent.value?.username || "未选择", icon: User, tone: "neutral" },
]);

function toPercent(value?: number | null) {
  return Math.round(Number(value || 0) * 100);
}

function syncFormFromDetail() {
  const confirmation = detail.value?.final_score_confirmation;
  form.confirmedScorePercent = confirmation ? toPercent(confirmation.confirmed_score) : toPercent(termSummary.value?.final_score_reference);
  form.confirmedLevel = confirmation?.confirmed_level || "";
  form.recommendationSummary = confirmation?.recommendation_summary || recommendationClosure.value?.final_summary || "";
  form.comment = confirmation?.comment || termSummary.value?.final_reason_summary || "";
}

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  const routeUserId = String(route.query.user_id || "").trim();
  const nextUserId = selectedUserId.value ? String(selectedUserId.value) : routeUserId || undefined;
  if (
    route.path === "/teacher/review" &&
    String(route.query.subject || "") === subject.value &&
    String(route.query.tab || "") === "final" &&
    String(route.query.user_id || "") === String(nextUserId || "")
  ) {
    return;
  }
  router.replace({
    path: "/teacher/review",
    query: {
      ...buildTeacherSubjectQuery(subject.value, { user_id: nextUserId }),
      tab: "final",
    },
  });
}

async function loadStudents() {
  if (!subject.value) return;
  listLoading.value = true;
  try {
    const res = await api.get(`/admin/final-score/students?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
    students.value = res.data?.items ?? [];
    const queryUserId = Number(route.query.user_id);
    if (Number.isFinite(queryUserId) && students.value.some((item) => item.user_id === queryUserId)) {
      selectedUserId.value = queryUserId;
    } else if (!selectedUserId.value && students.value.length) {
      selectedUserId.value = students.value[0].user_id;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载最终评分列表失败");
  } finally {
    listLoading.value = false;
  }
}

async function loadDetail() {
  if (!selectedUserId.value || !subject.value) {
    detail.value = null;
    return;
  }
  detailLoading.value = true;
  try {
    const res = await api.get(
      `/admin/final-score/detail?user_id=${selectedUserId.value}&subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`
    );
    detail.value = res.data;
    syncFormFromDetail();
  } catch (e: any) {
    detail.value = null;
    ElMessage.error(e?.response?.data?.detail ?? "加载评分确认详情失败");
  } finally {
    detailLoading.value = false;
  }
}

async function saveConfirmation() {
  if (!selectedUserId.value || !subject.value) {
    ElMessage.warning("请先选择课程和学生");
    return;
  }
  saving.value = true;
  try {
    await api.put("/admin/final-score/confirm", {
      user_id: selectedUserId.value,
      subject: subject.value,
      grade: grade.value,
      confirmed_score: Math.max(0, Math.min(100, Number(form.confirmedScorePercent || 0))) / 100,
      confirmed_level: form.confirmedLevel,
      recommendation_summary: form.recommendationSummary,
      comment: form.comment,
    });
    ElMessage.success("最终评分已确认并归档");
    await loadStudents();
    await loadDetail();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存最终评分失败");
  } finally {
    saving.value = false;
  }
}

watch(selectedCourseId, async () => {
  await loadStudents();
  await loadDetail();
});

watch(subject, () => {
  syncQuery();
});

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);

watch(selectedUserId, async () => {
  syncQuery();
  await loadDetail();
});

onMounted(async () => {
  await loadCourses();
  await loadStudents();
  await loadDetail();
});
</script>

<template>
  <div class="final-review-page">
    <WorkspaceTopbar
      v-model="subject"
      :courses="courses"
      badge="Final Review"
      title="最终评分确认"
      subtitle="结合阶段趋势、期末画像与推荐收口结果，形成教师最终确认结论。"
      :meta-text="metaText"
    >
      <el-button @click="router.push({ path: '/teacher/workspace', query: buildTeacherSubjectQuery(subject) })">返回课程工作台</el-button>
      <HintButton tip="切换到报名审核页，查看课程准入记录。" @click="router.push({ path: '/teacher/review', query: { ...buildTeacherSubjectQuery(subject), tab: 'enrollment' } })">
        报名审核
      </HintButton>
      <el-button type="primary" @click="loadDetail">刷新详情</el-button>
    </WorkspaceTopbar>

    <div class="final-review-layout">
      <aside class="final-review-sidebar panel-card" v-loading="listLoading">
        <div class="sidebar-head">
          <span class="section-eyebrow">学生列表</span>
          <h2>按学生完成学期收口</h2>
          <p>先选学生，再确认最终得分、等级与教师说明。</p>
        </div>

        <div class="sidebar-stats">
          <div><small>已确认</small><strong>{{ confirmedCount }}</strong></div>
          <div><small>待确认</small><strong>{{ Math.max(students.length - confirmedCount, 0) }}</strong></div>
        </div>

        <div class="student-list">
          <button
            v-for="item in students"
            :key="item.user_id"
            type="button"
            class="student-item"
            :class="{ active: item.user_id === selectedUserId }"
            @click="selectedUserId = item.user_id"
          >
            <div class="student-item__main">
              <strong>{{ item.full_name || item.username }}</strong>
              <span>{{ item.persona_label }} · {{ item.risk_level }}</span>
            </div>
            <div class="student-item__meta">
              <span>建议 {{ toPercent(item.suggested_score) }}%</span>
              <span v-if="item.confirmed_score != null">已确认 {{ toPercent(item.confirmed_score) }}%</span>
            </div>
          </button>
        </div>
      </aside>

      <main class="final-review-main" v-loading="detailLoading">
        <template v-if="detail">
          <section class="overview-card panel-card">
            <div class="overview-card__head">
              <div>
                <span class="section-eyebrow">收口概览</span>
                <h2>{{ selectedStudent?.full_name || selectedStudent?.username || "未选择学生" }}</h2>
                <p>将阶段评价、推荐结果与教师观察合并为课程期末结论。</p>
              </div>
              <div class="overview-card__badges">
                <span>{{ selectedStudent?.class_name || "未分班" }}</span>
                <span>{{ selectedStudent?.persona_label || "未生成画像" }}</span>
                <span>{{ selectedStudent?.risk_level || "未标记风险" }}</span>
              </div>
            </div>

            <div class="summary-grid">
              <article v-for="item in summaryCards" :key="item.label" class="summary-card" :class="`summary-card--${item.tone}`">
                <div class="summary-card__icon">
                  <el-icon><component :is="item.icon" /></el-icon>
                </div>
                <div class="summary-card__body">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </article>
            </div>
          </section>

          <section class="detail-grid">
            <el-card class="panel-card" shadow="never">
              <template #header>期末画像雷达图</template>
              <PortraitRadarChart
                :items="finalDimensions"
                title="学期最终五维结果"
                subtitle="系统根据各阶段快照汇总得到的期末画像"
                accent="#22c55e"
              />
            </el-card>

            <el-card class="panel-card" shadow="never">
              <template #header>教师确认表单</template>
              <div class="confirm-form">
                <div class="confirm-form__row">
                  <label>学生</label>
                  <div>{{ detail.student?.full_name || detail.student?.username }}</div>
                </div>
                <div class="confirm-form__row">
                  <label>确认分数</label>
                  <el-input-number v-model="form.confirmedScorePercent" :min="0" :max="100" :step="1" />
                </div>
                <div class="confirm-form__row">
                  <label>等级</label>
                  <el-select v-model="form.confirmedLevel" placeholder="请选择等级">
                    <el-option v-for="item in levelOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
                <div class="confirm-form__row confirm-form__row--stack">
                  <label>推荐链路收口说明</label>
                  <el-input v-model="form.recommendationSummary" type="textarea" :rows="3" placeholder="总结推荐链路最后的收口情况" />
                </div>
                <div class="confirm-form__row confirm-form__row--stack">
                  <label>教师确认说明</label>
                  <el-input v-model="form.comment" type="textarea" :rows="4" placeholder="填写最终评分依据、课堂观察或补充说明" />
                </div>
                <div class="confirm-form__actions">
                  <el-button type="primary" :loading="saving" :disabled="!canConfirmFinalScore" @click="saveConfirmation">确认并归档</el-button>
                  <el-button @click="router.push({ path: '/teacher/students', query: buildTeacherSubjectQuery(subject, { tab: 'detail', user_id: String(selectedUserId || '') || undefined }) })">
                    打开学生详情
                  </el-button>
                </div>
                <div v-if="!canConfirmFinalScore" class="empty-text">该学生还没有阶段评价数据，暂时不能确认期末成绩。</div>
              </div>
            </el-card>
          </section>

          <section class="detail-grid">
            <el-card class="panel-card" shadow="never">
              <template #header>阶段变化趋势</template>
              <div v-if="stageHistory.length === 0" class="empty-text">暂无阶段数据</div>
              <div v-else class="timeline-list">
                <div v-for="item in stageHistory" :key="item.stage_id" class="timeline-item">
                  <div class="timeline-item__title">{{ item.stage_order }}. {{ item.stage_title }}</div>
                  <div class="timeline-item__meta">
                    动态评分 {{ toPercent(item.dynamic_score) }}% · 掌握度 {{ toPercent(item.course_mastery) }}% · {{ item.trend_label }}
                  </div>
                  <div class="timeline-item__desc">{{ item.reason_summary }}</div>
                </div>
              </div>
            </el-card>

            <el-card class="panel-card" shadow="never">
              <template #header>推荐链路最终收口</template>
              <div class="closure-panel">
                <div class="closure-panel__item">
                  <span>最近推荐时间</span>
                  <strong>{{ recommendationClosure.latest_created_at ? recommendationClosure.latest_created_at.replace("T", " ").slice(0, 16) : "暂无" }}</strong>
                </div>
                <div class="closure-panel__item">
                  <span>最近推荐目标</span>
                  <strong>{{ recommendationClosure.latest_target_kp_id || "暂无" }}</strong>
                </div>
                <div class="closure-panel__item closure-panel__item--wide">
                  <span>系统推荐结论</span>
                  <strong>{{ recommendationClosure.latest_reason_summary || "暂无推荐结果" }}</strong>
                </div>
                <div class="closure-panel__item closure-panel__item--wide">
                  <span>当前收口摘要</span>
                  <strong>{{ recommendationClosure.final_summary || "尚未填写收口摘要" }}</strong>
                </div>
              </div>
            </el-card>
          </section>
        </template>

        <el-card v-else class="panel-card empty-card" shadow="never">
          <div class="empty-state">当前课程还没有可确认的期末评分数据。</div>
        </el-card>
      </main>
    </div>
  </div>
</template>

<style scoped>
.final-review-page {
  display: grid;
  gap: 18px;
}

.panel-card {
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background:
    radial-gradient(circle at top right, rgba(191, 221, 254, 0.18), transparent 24%),
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.08), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
}

.section-eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: linear-gradient(180deg, #eef6dc 0%, #fff2db 100%);
  color: #586537;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  width: fit-content;
}

.final-review-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
}

.final-review-sidebar {
  display: grid;
  gap: 16px;
  align-content: start;
  padding: 20px;
}

.sidebar-head h2,
.overview-card__head h2 {
  margin: 6px 0 0;
  color: #1f2937;
  font-size: 24px;
  line-height: 1.15;
}

.sidebar-head p,
.overview-card__head p {
  margin: 8px 0 0;
  color: #6a7280;
  line-height: 1.7;
}

.sidebar-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sidebar-stats > div {
  padding: 14px 16px;
  border-radius: 22px;
  border: 1px solid rgba(191, 167, 132, 0.24);
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(255, 244, 229, 0.92));
}

.sidebar-stats small {
  color: #6a7280;
}

.sidebar-stats strong {
  display: block;
  margin-top: 8px;
  color: #1f2937;
  font-size: 24px;
}

.student-list {
  display: grid;
  gap: 10px;
}

.student-item {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  text-align: left;
  border-radius: 22px;
  border: 1px solid rgba(191, 167, 132, 0.24);
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(255, 244, 229, 0.92));
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.student-item.active {
  border-color: rgba(34, 197, 94, 0.24);
  background:
    radial-gradient(circle at top right, rgba(215, 249, 168, 0.22), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #eef8ff 100%);
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.08);
}

.student-item__main,
.student-item__meta {
  display: grid;
  gap: 4px;
}

.student-item strong {
  color: #1f2937;
}

.student-item span {
  color: #6a7280;
  font-size: 13px;
}

.final-review-main {
  display: grid;
  gap: 18px;
}

.overview-card {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.overview-card__head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.overview-card__badges {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.overview-card__badges span {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(191, 167, 132, 0.34);
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
  color: #8a6740;
  font-size: 12px;
  font-weight: 800;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(191, 167, 132, 0.24);
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(255, 244, 229, 0.92));
}

.summary-card__icon {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: #ffffff;
}

.summary-card__body {
  display: grid;
  gap: 6px;
}

.summary-card__body span {
  color: #6a7280;
  font-size: 13px;
}

.summary-card__body strong {
  color: #1f2937;
  font-size: 22px;
  line-height: 1.15;
}

.summary-card--blue .summary-card__icon {
  color: #334155;
  background: rgba(191, 227, 245, 0.45);
}

.summary-card--amber .summary-card__icon {
  color: #b45309;
  background: rgba(253, 230, 138, 0.32);
}

.summary-card--green .summary-card__icon {
  color: #15803d;
  background: rgba(187, 247, 208, 0.3);
}

.summary-card--neutral .summary-card__icon {
  color: #475569;
  background: rgba(226, 232, 240, 0.52);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.final-review-main :deep(.el-card__header) {
  padding: 24px 24px 0;
  border-bottom: 0;
  color: #1f2937;
  font-size: 18px;
  font-weight: 800;
}

.final-review-main :deep(.el-card__body) {
  padding: 20px 24px 24px;
}

.confirm-form {
  display: grid;
  gap: 14px;
}

.confirm-form__row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.confirm-form__row--stack {
  grid-template-columns: 1fr;
}

.confirm-form__row label {
  color: #6a7280;
  font-size: 13px;
  font-weight: 700;
}

.confirm-form__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.timeline-list {
  display: grid;
  gap: 12px;
}

.timeline-item,
.closure-panel__item {
  border-radius: 22px;
  border: 1px solid rgba(191, 167, 132, 0.24);
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(255, 244, 229, 0.92));
  padding: 14px 16px;
}

.timeline-item__title {
  color: #1f2937;
  font-weight: 700;
}

.timeline-item__meta,
.timeline-item__desc,
.closure-panel__item span,
.empty-text,
.empty-state {
  margin-top: 6px;
  color: #6a7280;
  font-size: 13px;
  line-height: 1.7;
}

.closure-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.closure-panel__item {
  display: grid;
  gap: 8px;
}

.closure-panel__item--wide {
  grid-column: 1 / -1;
}

.closure-panel__item strong {
  color: #1f2937;
  line-height: 1.7;
}

.empty-card {
  padding: 24px;
}

@media (max-width: 1200px) {
  .final-review-layout {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .overview-card,
  .final-review-sidebar {
    padding: 18px;
  }

  .detail-grid,
  .closure-panel,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .sidebar-head h2,
  .overview-card__head h2 {
    font-size: 22px;
  }

  .confirm-form__row {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .student-item {
    transition: none;
  }
}
</style>
