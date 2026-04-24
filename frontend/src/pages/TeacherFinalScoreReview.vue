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
const confirmationProgress = computed(() => (students.value.length ? Math.round((confirmedCount.value / students.value.length) * 100) : 0));
const metaText = computed(() => `当前课程：${subject.value || "未选择"} · 已确认 ${confirmedCount.value}/${students.value.length}`);
const latestRecommendationTargetLabel = computed(() => {
  const title = String(recommendationClosure.value?.latest_target_kp_title || "").trim();
  const code = String(recommendationClosure.value?.latest_target_kp_code || "").trim();
  const id = recommendationClosure.value?.latest_target_kp_id;
  if (title) return code ? `${code} · ${title}` : title;
  const target = (detail.value?.mastery_map ?? []).find((item: any) => Number(item.kp_id) === Number(id));
  if (target?.title) return target.code ? `${target.code} · ${target.title}` : target.title;
  return id ? `知识点 ID ${id}` : "暂无";
});

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
      <button type="button" class="refresh-detail-button" @click="loadDetail">刷新详情</button>
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
        <div class="sidebar-progress" aria-label="确认进度">
          <div class="sidebar-progress__top">
            <span>确认进度</span>
            <strong>{{ confirmationProgress }}%</strong>
          </div>
          <div class="sidebar-progress__track">
            <div class="sidebar-progress__bar" :style="{ width: `${confirmationProgress}%` }"></div>
          </div>
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
              <span>{{ item.class_name || "未分班" }} · {{ item.persona_label || "未生成画像" }}</span>
            </div>
            <div class="student-item__meta">
              <span :class="['student-risk', `student-risk--${item.risk_level}`]">{{ item.risk_level || "未标记" }}</span>
              <span>建议 {{ toPercent(item.suggested_score) }}%</span>
              <span v-if="item.confirmed_score != null" class="student-confirmed">已确认 {{ toPercent(item.confirmed_score) }}%</span>
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
              <div class="overview-score">
                <span>建议得分</span>
                <strong>{{ toPercent(termSummary.final_score_reference) }}%</strong>
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

          <section class="detail-grid detail-grid--primary">
            <el-card class="panel-card detail-card detail-card--radar" shadow="never">
              <template #header>期末画像雷达图</template>
              <PortraitRadarChart
                :items="finalDimensions"
                title="学期最终五维结果"
                subtitle="系统根据各阶段快照汇总得到的期末画像"
                accent="#22c55e"
              />
            </el-card>

            <el-card class="panel-card detail-card detail-card--confirm" shadow="never">
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

          <section class="detail-grid detail-grid--evidence">
            <el-card class="panel-card detail-card detail-card--timeline" shadow="never">
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

            <el-card class="panel-card detail-card detail-card--closure" shadow="never">
              <template #header>推荐链路最终收口</template>
              <div class="closure-panel">
                <div class="closure-panel__item">
                  <span>最近推荐时间</span>
                  <strong>{{ recommendationClosure.latest_created_at ? recommendationClosure.latest_created_at.replace("T", " ").slice(0, 16) : "暂无" }}</strong>
                </div>
                <div class="closure-panel__item">
                  <span>最近推荐知识点</span>
                  <strong>{{ latestRecommendationTargetLabel }}</strong>
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
  gap: 20px;
  --review-ink: var(--app-text-main);
  --review-muted: var(--app-text-soft);
  --review-subtle: var(--app-text-light);
  --review-border: var(--app-border);
  --review-border-strong: var(--app-border-hover);
  --review-surface: var(--app-card);
  --review-soft: var(--app-surface-muted);
  --review-blue: #2f6fed;
  --review-green: var(--app-primary);
  --review-amber: var(--app-warning);
}

.panel-card {
  border-radius: var(--app-radius);
  border: 1px solid var(--review-border);
  background:
    radial-gradient(circle at top right, rgba(184, 228, 246, 0.14), transparent 28%),
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.06), transparent 24%),
    var(--app-gradient-surface);
  box-shadow: var(--app-shadow-sm);
}

.section-eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--app-primary-tint);
  color: var(--app-eyebrow);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
  width: fit-content;
}

.refresh-detail-button {
  appearance: none;
  border: none;
  min-width: 108px;
  min-height: 38px;
  padding: 0 16px;
  border-radius: 12px;
  background: var(--app-primary);
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  line-height: 38px;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(34, 197, 94, 0.24);
  transition: background-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.refresh-detail-button:hover,
.refresh-detail-button:focus-visible {
  outline: none;
  background: var(--app-primary-deep);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(34, 197, 94, 0.28);
}

.final-review-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.final-review-sidebar {
  position: sticky;
  top: 118px;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 14px;
  max-height: calc(100dvh - 136px);
  padding: 18px;
  overflow: hidden;
}

.sidebar-head h2,
.overview-card__head h2 {
  margin: 8px 0 0;
  color: var(--review-ink);
  font-size: 22px;
  line-height: 1.2;
  letter-spacing: 0;
}

.sidebar-head p,
.overview-card__head p {
  margin: 6px 0 0;
  color: var(--review-muted);
  line-height: 1.6;
  font-size: 13px;
}

.sidebar-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.sidebar-stats > div {
  padding: 12px 14px;
  border-radius: var(--app-radius-sm);
  border: 1px solid color-mix(in srgb, var(--review-border) 90%, #ffffff);
  background: rgba(255, 255, 255, 0.82);
}

.sidebar-stats small {
  color: var(--review-muted);
  font-weight: 700;
}

.sidebar-stats strong {
  display: block;
  margin-top: 4px;
  color: var(--review-ink);
  font-size: 24px;
  line-height: 1;
}

.sidebar-progress {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border-radius: var(--app-radius-sm);
  border: 1px solid color-mix(in srgb, var(--app-primary) 18%, var(--review-border));
  background: linear-gradient(180deg, var(--app-primary-tint) 0%, #ffffff 100%);
}

.sidebar-progress__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--review-muted);
  font-size: 12px;
  font-weight: 800;
}

.sidebar-progress__top strong {
  color: var(--review-blue);
}

.sidebar-progress__track {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--app-bg-alt);
}

.sidebar-progress__bar {
  height: 100%;
  min-width: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #bfe3f5 0%, var(--app-primary) 100%);
  transition: width 0.22s ease;
}

.student-list {
  display: grid;
  align-content: start;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
  overscroll-behavior: contain;
}

.student-item {
  display: grid;
  gap: 10px;
  padding: 13px 14px;
  text-align: left;
  border-radius: var(--app-radius-sm);
  border: 1px solid color-mix(in srgb, var(--review-border) 90%, #ffffff);
  background: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.student-item:hover,
.student-item:focus-visible {
  outline: none;
  border-color: color-mix(in srgb, var(--app-primary) 24%, var(--review-border));
  background: #f8fbff;
}

.student-item.active {
  border-color: color-mix(in srgb, var(--app-primary) 34%, var(--review-border));
  background:
    radial-gradient(circle at top right, rgba(184, 228, 246, 0.22), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, var(--app-primary-tint) 100%);
  box-shadow: inset 3px 0 0 var(--app-primary), var(--app-shadow-sm);
}

.student-item__main,
.student-item__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.student-item strong {
  width: 100%;
  color: var(--review-ink);
  line-height: 1.2;
}

.student-item span {
  color: var(--review-muted);
  font-size: 12px;
}

.student-item__meta span {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--app-surface-muted);
  color: #475569;
  font-weight: 700;
}

.student-item__meta .student-confirmed {
  background: var(--app-primary-tint);
  color: var(--app-primary-deep);
}

.student-risk {
  background: #fff7ed !important;
  color: #c2410c !important;
}

.student-risk--优秀,
.student-risk--良好 {
  background: var(--app-primary-tint) !important;
  color: var(--app-primary-deep) !important;
}

.student-risk--预警,
.student-risk--需关注 {
  background: #fef2f2 !important;
  color: #b91c1c !important;
}

.final-review-main {
  display: grid;
  gap: 22px;
}

.overview-card {
  display: grid;
  gap: 20px;
  padding: 22px;
  background:
    radial-gradient(circle at top right, rgba(184, 228, 246, 0.18), transparent 28%),
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.08), transparent 24%),
    var(--app-gradient-surface);
}

.overview-card__head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

.overview-card__badges {
  grid-column: 1 / -1;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.overview-card__badges span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.86);
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.overview-score {
  min-width: 132px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 24%, var(--review-border));
  background:
    radial-gradient(circle at top right, rgba(34, 197, 94, 0.14), transparent 36%),
    linear-gradient(180deg, #ffffff 0%, var(--app-primary-tint) 100%);
  color: var(--review-ink);
  box-shadow: var(--app-shadow-sm);
}

.overview-score span {
  display: block;
  color: var(--review-muted);
  font-size: 12px;
  font-weight: 800;
}

.overview-score strong {
  display: block;
  margin-top: 4px;
  font-size: 30px;
  line-height: 1;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: flex;
  gap: 12px;
  min-height: 84px;
  padding: 14px;
  border-radius: var(--app-radius-sm);
  border: 1px solid color-mix(in srgb, var(--review-border) 90%, #ffffff);
  background: rgba(255, 255, 255, 0.86);
}

.summary-card__icon {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--app-surface-muted);
}

.summary-card__body {
  display: grid;
  gap: 6px;
}

.summary-card__body span {
  color: var(--review-muted);
  font-size: 12px;
  font-weight: 700;
}

.summary-card__body strong {
  color: var(--review-ink);
  font-size: 21px;
  line-height: 1.15;
}

.summary-card--blue .summary-card__icon {
  color: #1d4ed8;
  background: #eef6ff;
}

.summary-card--amber .summary-card__icon {
  color: var(--review-amber);
  background: #fffbeb;
}

.summary-card--green .summary-card__icon {
  color: #15803d;
  background: var(--app-primary-tint);
}

.summary-card--neutral .summary-card__icon {
  color: #475569;
  background: var(--app-surface-muted);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 22px;
  align-items: start;
}

.detail-card {
  min-width: 0;
}

.detail-card--radar {
  grid-column: span 7;
  min-height: 470px;
}

.detail-card--confirm {
  grid-column: span 5;
}

.detail-card--timeline {
  grid-column: span 7;
}

.detail-card--closure {
  grid-column: span 5;
}

.detail-card--radar :deep(.el-card__body) {
  min-height: 410px;
  display: grid;
  align-items: center;
}

.detail-card--confirm :deep(.el-card__body) {
  padding-bottom: 24px;
}

.final-review-main :deep(.el-card__header) {
  padding: 18px 20px 0;
  border-bottom: 0;
  color: var(--review-ink);
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0;
}

.final-review-main :deep(.el-card__body) {
  padding: 16px 20px 20px;
}

.confirm-form {
  display: grid;
  gap: 13px;
}

.confirm-form__row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.confirm-form__row--stack {
  grid-template-columns: 1fr;
}

.confirm-form__row label {
  color: #475569;
  font-size: 13px;
  font-weight: 800;
}

.confirm-form__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.timeline-list {
  display: grid;
  gap: 10px;
}

.timeline-item,
.closure-panel__item {
  border-radius: var(--app-radius-sm);
  border: 1px solid color-mix(in srgb, var(--review-border) 90%, #ffffff);
  background: rgba(255, 255, 255, 0.88);
  padding: 14px;
}

.timeline-item__title {
  color: var(--review-ink);
  font-weight: 700;
}

.timeline-item__meta,
.timeline-item__desc,
.closure-panel__item span,
.empty-text,
.empty-state {
  margin-top: 6px;
  color: var(--review-muted);
  font-size: 13px;
  line-height: 1.65;
}

.closure-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.closure-panel__item {
  display: grid;
  gap: 6px;
}

.closure-panel__item--wide {
  grid-column: 1 / -1;
}

.closure-panel__item strong {
  color: var(--review-ink);
  line-height: 1.6;
}

.empty-card {
  padding: 24px;
}

@media (max-width: 1200px) {
  .final-review-layout {
    grid-template-columns: 1fr;
  }

  .final-review-sidebar {
    position: relative;
    top: auto;
    max-height: none;
  }

  .student-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow: visible;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-card--radar,
  .detail-card--confirm,
  .detail-card--timeline,
  .detail-card--closure {
    grid-column: 1 / -1;
  }

  .detail-card--radar {
    min-height: auto;
  }

  .detail-card--radar :deep(.el-card__body) {
    min-height: 360px;
  }
}

@media (max-width: 768px) {
  .overview-card,
  .final-review-sidebar {
    padding: 16px;
  }

  .overview-card__head {
    grid-template-columns: 1fr;
  }

  .overview-score {
    width: 100%;
  }

  .student-list {
    grid-template-columns: 1fr;
  }

  .detail-grid,
  .closure-panel,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .sidebar-head h2,
  .overview-card__head h2 {
    font-size: 20px;
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
