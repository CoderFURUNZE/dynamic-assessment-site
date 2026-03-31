<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import PageSectionCard from "../components/PageSectionCard.vue";
import HintButton from "../components/HintButton.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };
type Stage = { id: number; title: string; stage_order: number };
type BehaviorRow = {
  user_id: number;
  username: string;
  student_no: string;
  full_name: string;
  class_name: string;
  behavior_events: number;
  active_days: number;
  positive_events: number;
  negative_events: number;
  expression_events: number;
  expression_focus: number;
  expression_distracted: number;
  avg_confidence: number;
  behavior_score: number;
  signal_balance: number;
  dominant_signal: string;
  dynamic_score: number;
  risk_level: string;
};
type BehaviorSummary = {
  course_id: number;
  stage_id: number;
  stage_title: string;
  student_count: number;
  behavior_students: number;
  expression_students: number;
  positive_events: number;
  negative_events: number;
};
type BehaviorSummaryPayload = {
  summary: BehaviorSummary;
  rows: BehaviorRow[];
  columns: string[];
};
type ImportResult = {
  batch_id: number;
  metric_type: string;
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  errors: string[];
  affected_dimensions: string[];
  affected_indicators: string[];
  recalculated_users: number;
  next_action: string;
};

const route = useRoute();
const router = useRouter();
const subject = ref("");
const grade = ref("通用");
const courses = ref<Course[]>([]);
const stages = ref<Stage[]>([]);
const selectedStageId = ref<number | null>(null);
const loading = ref(false);
const applying = ref(false);
const report = ref<BehaviorSummaryPayload | null>(null);
const lastResult = ref<ImportResult | null>(null);

const selectedCourseId = computed<number | null>(() => {
  return courses.value.find((item) => item.title === subject.value)?.id ?? null;
});

const selectedStage = computed<Stage | null>(() => {
  return stages.value.find((item) => item.id === selectedStageId.value) ?? null;
});

const rows = computed(() => report.value?.rows ?? []);
const previewRows = computed(() => [...rows.value].sort((a, b) => (b.behavior_score || 0) - (a.behavior_score || 0)).slice(0, 8));
const riskRows = computed(() => [...rows.value].filter((row) => row.risk_level !== "暂无").slice(0, 8));
const avgBehaviorScore = computed(() => {
  if (!rows.value.length) return 0;
  return rows.value.reduce((sum, row) => sum + (row.behavior_score || 0), 0) / rows.value.length;
});
const avgDynamicScore = computed(() => {
  if (!rows.value.length) return 0;
  return rows.value.reduce((sum, row) => sum + (row.dynamic_score || 0), 0) / rows.value.length;
});
const avgConfidence = computed(() => {
  if (!rows.value.length) return 0;
  return rows.value.reduce((sum, row) => sum + (row.avg_confidence || 0), 0) / rows.value.length;
});
const avgActiveDays = computed(() => {
  if (!rows.value.length) return 0;
  return rows.value.reduce((sum, row) => sum + (row.active_days || 0), 0) / rows.value.length;
});
const totalBehaviorEvents = computed(() => rows.value.reduce((sum, row) => sum + (row.behavior_events || 0), 0));
const totalExpressions = computed(() => rows.value.reduce((sum, row) => sum + (row.expression_events || 0), 0));
const riskDistribution = computed(() => {
  const buckets = new Map<string, number>();
  rows.value.forEach((row) => {
    const key = row.risk_level || "暂无";
    buckets.set(key, (buckets.get(key) || 0) + 1);
  });
  return ["高风险", "中风险", "低风险", "暂无"].map((label) => ({
    label,
    count: buckets.get(label) || 0,
  }));
});
const behaviorBars = computed(() =>
  [...rows.value]
    .sort((a, b) => (b.behavior_score || 0) - (a.behavior_score || 0))
    .slice(0, 8)
    .map((row) => ({
      id: row.user_id,
      label: row.full_name || row.username || `学生${row.user_id}`,
      value: Math.round((row.behavior_score || 0) * 100),
      dynamic: Math.round((row.dynamic_score || 0) * 100),
      signal: row.dominant_signal || "观察",
    }))
);

function queryStageId() {
  const raw = route.query.stage_id;
  const value = Array.isArray(raw) ? raw[0] : raw;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

async function loadStages() {
  if (!selectedCourseId.value) {
    stages.value = [];
    selectedStageId.value = null;
    report.value = null;
    return;
  }
  try {
    const res = await api.get(`/stages/courses/${selectedCourseId.value}`);
    stages.value = res.data ?? [];
    const routeStageId = queryStageId();
    if (routeStageId && stages.value.some((item) => item.id === routeStageId)) {
      selectedStageId.value = routeStageId;
      return;
    }
    if (!stages.value.some((item) => item.id === selectedStageId.value)) {
      selectedStageId.value = stages.value[0]?.id ?? null;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载阶段列表失败");
  }
}

async function loadReport() {
  if (!selectedCourseId.value || !selectedStageId.value) {
    report.value = null;
    return;
  }
  try {
    const res = await api.get(
      `/stages/internal-behavior-summary?course_id=${selectedCourseId.value}&stage_id=${selectedStageId.value}`
    );
    report.value = res.data ?? null;
  } catch (e: any) {
    report.value = null;
    ElMessage.error(e?.response?.data?.detail ?? "加载行为画像失败");
  }
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  router.replace({
    path: "/teacher/evaluation",
    query: buildTeacherSubjectQuery(subject.value, {
      tab: "behavior",
      stage_id: selectedStageId.value ? String(selectedStageId.value) : undefined,
    }),
  });
}

async function refresh() {
  loading.value = true;
  try {
    await loadCourses();
    await loadStages();
    await loadReport();
  } finally {
    loading.value = false;
  }
}

async function downloadCsv() {
  if (!selectedCourseId.value || !selectedStageId.value) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  try {
    const res = await api.get(
      `/stages/internal-behavior-summary/export?course_id=${selectedCourseId.value}&stage_id=${selectedStageId.value}`,
      { responseType: "blob" }
    );
    const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `stage_behavior_summary_${selectedCourseId.value}_${selectedStageId.value}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导出行为汇总失败");
  }
}

async function applyBehavior() {
  if (!selectedCourseId.value || !selectedStageId.value) {
    ElMessage.warning("请先选择课程和阶段");
    return;
  }
  applying.value = true;
  try {
    const form = new FormData();
    form.append("course_id", String(selectedCourseId.value));
    form.append("stage_id", String(selectedStageId.value));
    const res = await api.post("/stages/internal-behavior-summary/apply", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    lastResult.value = res.data ?? null;
    ElMessage.success("行为信息已导入并生成阶段画像");
    await loadReport();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "应用行为汇总失败");
  } finally {
    applying.value = false;
  }
}

watch(subject, () => syncQuery());
watch(selectedStageId, () => {
  syncQuery();
  loadReport();
});
watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "").trim();
    if (next && next !== subject.value) subject.value = next;
  }
);
watch(
  () => route.query.stage_id,
  () => {
    const next = queryStageId();
    if (next && next !== selectedStageId.value) selectedStageId.value = next;
  }
);
watch(selectedCourseId, () => {
  loadStages().catch((e: any) => {
    ElMessage.error(e?.response?.data?.detail ?? "加载阶段列表失败");
  });
});

onMounted(async () => {
  loading.value = true;
  try {
    await loadCourses();
    await loadStages();
    await loadReport();
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="teacher-page">
    <WorkspaceTopbar v-model="subject" :courses="courses" badge="Teacher Behavior" title="行为画像明细" :meta-text="selectedStage ? `阶段 ${selectedStage.stage_order}. ${selectedStage.title}` : '请选择课程与阶段查看行为画像'" @change="syncQuery">
      <HintButton tip="回到阶段评价里的数据导入页，继续上传班级数据。" @click="router.push({ path: '/teacher/evaluation', query: { ...buildTeacherSubjectQuery(subject), tab: 'imports' } })">去数据导入</HintButton>
      <HintButton tip="导出当前阶段的行为画像明细 CSV。" @click="downloadCsv">导出 CSV</HintButton>
      <HintButton type="primary" :loading="applying" tip="将系统行为汇总写入阶段画像并重新计算。" @click="applyBehavior">一键导入并重算</HintButton>
    </WorkspaceTopbar>

    <PageSectionCard eyebrow="Behavior Report" title="阶段行为画像">
      <div class="behavior-shell" v-loading="loading">
        <el-alert class="behavior-auto-collect-hint" type="info" show-icon :closable="false">
          <template #title>自动采集与一键导入</template>
          <p class="behavior-auto-collect-hint__body">
            学生端在登录、浏览资源、练习作答、小测提交、视频进度、图谱与推荐等操作中会由系统自动写入行为事件。本页汇总即基于这些已入库记录。选择阶段后点击
            <strong>一键导入并重算</strong>，将当前阶段的行为信号写入阶段画像指标并触发动态评价重算，便于按阶段对比每位学生的画像变化（无需另外上传原始日志）。
          </p>
        </el-alert>
        <div class="behavior-toolbar">
          <div class="behavior-picker">
            <span>阶段</span>
            <el-select v-model="selectedStageId" class="behavior-picker__select" placeholder="选择阶段">
              <el-option v-for="item in stages" :key="item.id" :label="`${item.stage_order}. ${item.title}`" :value="item.id" />
            </el-select>
          </div>
          <div class="behavior-toolbar__meta">当前汇总来自系统采集的行为事件与表情信号，支持一键导入后重算画像。</div>
        </div>

        <div v-if="report" class="behavior-metrics">
          <el-card shadow="never" class="metric-card">
            <div class="metric-card__label">行为学生</div>
            <div class="metric-card__value">{{ report.summary.behavior_students }}</div>
            <div class="metric-card__hint">有系统行为记录的学生数</div>
          </el-card>
          <el-card shadow="never" class="metric-card">
            <div class="metric-card__label">平均行为分</div>
            <div class="metric-card__value">{{ Math.round(avgBehaviorScore * 100) }}%</div>
            <div class="metric-card__hint">按事件与活跃天数综合计算</div>
          </el-card>
          <el-card shadow="never" class="metric-card">
            <div class="metric-card__label">平均画像分</div>
            <div class="metric-card__value">{{ Math.round(avgDynamicScore * 100) }}%</div>
            <div class="metric-card__hint">阶段画像当前综合评分</div>
          </el-card>
          <el-card shadow="never" class="metric-card">
            <div class="metric-card__label">风险学生</div>
            <div class="metric-card__value">{{ riskRows.length }}</div>
            <div class="metric-card__hint">需要重点关注的学生数</div>
          </el-card>
        </div>

        <div v-if="report" class="behavior-panels">
          <el-card shadow="never" class="behavior-panel">
            <template #header>
              <div class="behavior-panel__header">
                <span>行为强度排行</span>
                <small>按行为得分从高到低排序</small>
              </div>
            </template>
            <div class="score-bars">
              <div v-for="item in behaviorBars" :key="item.id" class="score-bar">
                <div class="score-bar__head">
                  <strong>{{ item.label }}</strong>
                  <span>{{ item.value }}% · 图像 {{ item.dynamic }}%</span>
                </div>
                <div class="score-bar__track">
                  <div class="score-bar__fill" :style="{ width: `${item.value}%` }" />
                </div>
                <div class="score-bar__foot">主信号：{{ item.signal }}</div>
              </div>
              <el-empty v-if="!behaviorBars.length" description="暂无行为数据" />
            </div>
          </el-card>

          <el-card shadow="never" class="behavior-panel">
            <template #header>
              <div class="behavior-panel__header">
                <span>风险分布</span>
                <small>用于阶段干预和名单筛查</small>
              </div>
            </template>
            <div class="risk-list">
              <div v-for="item in riskDistribution" :key="item.label" class="risk-item">
                <div class="risk-item__head">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.count }}</strong>
                </div>
                <div class="risk-item__track">
                  <div class="risk-item__fill" :style="{ width: `${report.summary.student_count ? (item.count / report.summary.student_count) * 100 : 0}%` }" />
                </div>
              </div>
            </div>

            <div class="insight-grid">
              <div class="insight-card">
                <span>平均活跃天数</span>
                <strong>{{ avgActiveDays.toFixed(1) }}</strong>
              </div>
              <div class="insight-card">
                <span>平均置信度</span>
                <strong>{{ Math.round(avgConfidence * 100) }}%</strong>
              </div>
              <div class="insight-card">
                <span>行为事件数</span>
                <strong>{{ totalBehaviorEvents }}</strong>
              </div>
              <div class="insight-card">
                <span>表情信号数</span>
                <strong>{{ totalExpressions }}</strong>
              </div>
            </div>

            <div class="risk-students">
              <div class="risk-students__title">重点关注名单</div>
              <div v-if="riskRows.length" class="risk-students__list">
                <div v-for="row in riskRows" :key="row.user_id" class="risk-students__item">
                  <div class="risk-students__name">{{ row.full_name || row.username }}</div>
                  <div class="risk-students__meta">
                    {{ row.username }} · {{ row.risk_level }} · {{ Math.round((row.dynamic_score || 0) * 100) }}%
                  </div>
                </div>
              </div>
              <el-empty v-else description="当前没有风险学生" />
            </div>
          </el-card>
        </div>

        <el-card shadow="never" class="behavior-panel behavior-panel--table">
          <template #header>
            <div class="behavior-panel__header">
              <span>学生行为明细</span>
              <small>可用于阶段干预与画像核对</small>
            </div>
          </template>
          <el-table v-if="report" :data="previewRows" size="small" style="width: 100%">
            <el-table-column prop="username" label="账号" width="120" />
            <el-table-column prop="student_no" label="学号" width="120" />
            <el-table-column prop="full_name" label="姓名" width="110" />
            <el-table-column prop="behavior_events" label="事件数" width="90" />
            <el-table-column prop="active_days" label="活跃天数" width="100" />
            <el-table-column prop="positive_events" label="正向信号" width="100" />
            <el-table-column prop="negative_events" label="负向信号" width="100" />
            <el-table-column prop="behavior_score" label="行为得分" width="110">
              <template #default="{ row }">{{ Math.round((row.behavior_score || 0) * 100) }}%</template>
            </el-table-column>
            <el-table-column prop="dynamic_score" label="画像分" width="110">
              <template #default="{ row }">{{ Math.round((row.dynamic_score || 0) * 100) }}%</template>
            </el-table-column>
            <el-table-column prop="dominant_signal" label="主信号" min-width="120" />
            <el-table-column prop="risk_level" label="风险" width="100" />
          </el-table>
          <el-empty v-else description="请先选择课程和阶段" />
        </el-card>

        <div v-if="lastResult" class="behavior-result">
          <div class="behavior-result__item">
            <span>导入记录</span>
            <strong>{{ lastResult.total_rows }}</strong>
          </div>
          <div class="behavior-result__item">
            <span>成功导入</span>
            <strong>{{ lastResult.success_rows }}</strong>
          </div>
          <div class="behavior-result__item">
            <span>重算学生</span>
            <strong>{{ lastResult.recalculated_users }}</strong>
          </div>
          <div class="behavior-result__item behavior-result__item--full">
            <span>下一步</span>
            <strong>{{ lastResult.next_action }}</strong>
          </div>
        </div>
      </div>
    </PageSectionCard>
  </div>
</template>

<style scoped>
.teacher-page {
  display: grid;
  gap: 20px;
}

.behavior-shell {
  display: grid;
  gap: 16px;
}

.behavior-auto-collect-hint :deep(.el-alert__description) {
  margin: 0;
}
.behavior-auto-collect-hint__body {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--app-ink-soft);
}

.behavior-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.behavior-picker {
  display: grid;
  gap: 8px;
  min-width: 320px;
}

.behavior-picker span,
.behavior-toolbar__meta {
  color: var(--app-ink-soft);
  font-size: 12px;
}

.behavior-picker__select {
  width: min(100%, 380px);
}

.behavior-toolbar__meta {
  max-width: 560px;
  line-height: 1.7;
}

.behavior-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  border-radius: 16px;
  border: 1px solid var(--app-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.025), rgba(255, 255, 255, 0.015));
}

.metric-card__label {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.metric-card__value {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 800;
  color: var(--app-ink);
  letter-spacing: -0.02em;
}

.metric-card__hint {
  margin-top: 6px;
  color: var(--app-ink-soft);
  font-size: 12px;
  line-height: 1.6;
}

.behavior-panels {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

.behavior-panel {
  border-radius: 18px;
  border: 1px solid var(--app-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.01));
  box-shadow: none;
}

.behavior-panel__header {
  display: grid;
  gap: 4px;
}

.behavior-panel__header span {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-ink);
}

.behavior-panel__header small {
  color: var(--app-ink-soft);
  font-size: 12px;
}

.score-bars,
.risk-list {
  display: grid;
  gap: 14px;
}

.score-bar,
.risk-item,
.insight-card {
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(255, 255, 255, 0.025);
  padding: 12px 14px;
}

.score-bar__head,
.risk-item__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.score-bar__head strong,
.risk-item__head span {
  color: var(--app-ink);
}

.score-bar__head span,
.score-bar__foot {
  color: var(--app-ink-soft);
  font-size: 12px;
}

.score-bar__track,
.risk-item__track {
  margin-top: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.16);
  overflow: hidden;
}

.score-bar__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6ee7b7, #4f8cff);
}

.risk-item__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ffcf5a, #ff7a7a);
}

.score-bar__foot {
  margin-top: 8px;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.risk-students {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}

.risk-students__title {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-ink);
}

.risk-students__list {
  display: grid;
  gap: 10px;
}

.risk-students__item {
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(255, 255, 255, 0.02);
  padding: 12px 14px;
}

.risk-students__name {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-ink);
}

.risk-students__meta {
  margin-top: 4px;
  color: var(--app-ink-soft);
  font-size: 12px;
}

.insight-card {
  display: grid;
  gap: 6px;
}

.insight-card span {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.insight-card strong {
  font-size: 22px;
  color: var(--app-ink);
  font-weight: 800;
}

.behavior-panel--table {
  overflow: hidden;
}

.behavior-result {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.behavior-result__item {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 4px;
}

.behavior-result__item--full {
  grid-column: 1 / -1;
}

.behavior-result__item span {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.behavior-result__item strong {
  font-size: 20px;
  color: var(--app-ink);
  line-height: 1.4;
}

@media (max-width: 1200px) {
  .behavior-metrics,
  .behavior-result {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .behavior-panels {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .behavior-metrics,
  .behavior-result,
  .insight-grid {
    grid-template-columns: 1fr;
  }

  .behavior-picker {
    min-width: 0;
    width: 100%;
  }
}
</style>
