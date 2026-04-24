
<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
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

type RiskFilter = "all" | "risk" | "高风险" | "中风险" | "低风险";

const route = useRoute();
const router = useRouter();

const subject = ref("");
const courses = ref<Course[]>([]);
const stages = ref<Stage[]>([]);
const selectedStageId = ref<number | null>(null);
const loading = ref(false);
const applying = ref(false);
const initialized = ref(false);
const report = ref<BehaviorSummaryPayload | null>(null);
const lastResult = ref<ImportResult | null>(null);
const activeRiskFilter = ref<RiskFilter>("all");
const detailTableAnchor = ref<HTMLElement | null>(null);
const highlightedStudentId = ref<number | null>(null);

const riskOrder: Record<string, number> = {
  高风险: 3,
  中风险: 2,
  低风险: 1,
  暂无: 0,
};

const selectedCourseId = computed<number | null>(() => courses.value.find((item) => item.title === subject.value)?.id ?? null);
const selectedStage = computed<Stage | null>(() => stages.value.find((item) => item.id === selectedStageId.value) ?? null);
const rows = computed(() => report.value?.rows ?? []);
const hasBehaviorData = computed(() =>
  rows.value.some(
    (row) => (row.behavior_events || 0) > 0 || (row.expression_events || 0) > 0 || (row.behavior_score || 0) > 0 || (row.dynamic_score || 0) > 0
  )
);
const avgBehaviorScore = computed(() => (rows.value.length ? rows.value.reduce((sum, row) => sum + (row.behavior_score || 0), 0) / rows.value.length : 0));
const avgDynamicScore = computed(() => (rows.value.length ? rows.value.reduce((sum, row) => sum + (row.dynamic_score || 0), 0) / rows.value.length : 0));
const avgPositiveRate = computed(() => {
  const totalPositive = rows.value.reduce((sum, row) => sum + (row.positive_events || 0), 0);
  const totalNegative = rows.value.reduce((sum, row) => sum + (row.negative_events || 0), 0);
  const total = totalPositive + totalNegative;
  return total ? totalPositive / total : 0;
});
const avgConfidence = computed(() => (rows.value.length ? rows.value.reduce((sum, row) => sum + (row.avg_confidence || 0), 0) / rows.value.length : 0));
const avgActiveDays = computed(() => (rows.value.length ? rows.value.reduce((sum, row) => sum + (row.active_days || 0), 0) / rows.value.length : 0));
const totalBehaviorEvents = computed(() => rows.value.reduce((sum, row) => sum + (row.behavior_events || 0), 0));
const totalExpressions = computed(() => rows.value.reduce((sum, row) => sum + (row.expression_events || 0), 0));

function normalizeRisk(level?: string) {
  if (level === "高风险" || level === "中风险" || level === "低风险") return level;
  return "暂无";
}

function getRiskWeight(row: BehaviorRow) {
  return riskOrder[normalizeRisk(row.risk_level)];
}

function getDisplayName(row: BehaviorRow) {
  return row.full_name || row.username || `学生 ${row.user_id}`;
}

function formatPercent(value?: number) {
  return `${Math.round((value || 0) * 100)}%`;
}

function riskClass(level?: string) {
  return `risk-${normalizeRisk(level)}`;
}

const sortedRows = computed(() =>
  [...rows.value].sort((a, b) => {
    const riskDiff = getRiskWeight(b) - getRiskWeight(a);
    if (riskDiff !== 0) return riskDiff;
    const dynamicDiff = (a.dynamic_score || 0) - (b.dynamic_score || 0);
    if (dynamicDiff !== 0) return dynamicDiff;
    return (b.behavior_events || 0) - (a.behavior_events || 0);
  })
);

const rankRows = computed(() =>
  [...rows.value]
    .sort((a, b) => {
      const behaviorDiff = (b.behavior_score || 0) - (a.behavior_score || 0);
      if (behaviorDiff !== 0) return behaviorDiff;
      return (b.dynamic_score || 0) - (a.dynamic_score || 0);
    })
    .slice(0, 8)
);

const focusStudents = computed(() => sortedRows.value.filter((row) => getRiskWeight(row) > 0).slice(0, 4));
const watchlistRows = computed(() => sortedRows.value.filter((row) => getRiskWeight(row) > 0).slice(0, 5));

const riskDistribution = computed(() => {
  const buckets = new Map<string, number>();
  rows.value.forEach((row) => {
    const key = normalizeRisk(row.risk_level);
    buckets.set(key, (buckets.get(key) || 0) + 1);
  });
  const total = report.value?.summary.student_count || rows.value.length || 0;
  return [
    { label: "高风险", tone: "high" },
    { label: "中风险", tone: "medium" },
    { label: "低风险", tone: "low" },
    { label: "暂无", tone: "none" },
  ].map((item) => ({ ...item, count: buckets.get(item.label) || 0, percent: total ? Math.round(((buckets.get(item.label) || 0) / total) * 100) : 0 }));
});

const detailRows = computed(() => {
  const filtered = rows.value.filter((row) => {
    const level = normalizeRisk(row.risk_level);
    if (activeRiskFilter.value === "all") return true;
    if (activeRiskFilter.value === "risk") return level !== "暂无";
    return level === activeRiskFilter.value;
  });
  return [...filtered].sort((a, b) => {
    const riskDiff = getRiskWeight(b) - getRiskWeight(a);
    if (riskDiff !== 0) return riskDiff;
    const dynamicDiff = (a.dynamic_score || 0) - (b.dynamic_score || 0);
    if (dynamicDiff !== 0) return dynamicDiff;
    return (a.behavior_score || 0) - (b.behavior_score || 0);
  });
});

const detailFilterOptions: Array<{ label: string; value: RiskFilter }> = [
  { label: "全部", value: "all" },
  { label: "风险学生", value: "risk" },
  { label: "高风险", value: "高风险" },
  { label: "中风险", value: "中风险" },
  { label: "低风险", value: "低风险" },
];

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
    if (!stages.value.some((item) => item.id === selectedStageId.value)) selectedStageId.value = stages.value[0]?.id ?? null;
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
    const res = await api.get(`/stages/internal-behavior-summary?course_id=${selectedCourseId.value}&stage_id=${selectedStageId.value}`);
    report.value = res.data ?? null;
  } catch (e: any) {
    report.value = null;
    ElMessage.error(e?.response?.data?.detail ?? "加载行为画像失败");
  }
}

function syncQuery() {
  if (!initialized.value || !subject.value) return;
  saveTeacherSubject(subject.value);
  const stageId = selectedStageId.value ?? queryStageId();
  const nextQuery = buildTeacherSubjectQuery(subject.value, {
    tab: "behavior",
    stage_id: stageId ? String(stageId) : undefined,
  });
  const currentSubject = String(route.query.subject || "").trim();
  const currentTab = String(route.query.tab || "class").trim();
  const currentStageId = String(route.query.stage_id || "").trim();
  const nextStageId = String(nextQuery.stage_id || "").trim();
  if (
    route.path === "/teacher/students"
    && currentSubject === String(nextQuery.subject || "").trim()
    && currentTab === "behavior"
    && currentStageId === nextStageId
  ) {
    return;
  }
  router.replace({ path: "/teacher/students", query: nextQuery });
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
    const res = await api.get(`/stages/internal-behavior-summary/export?course_id=${selectedCourseId.value}&stage_id=${selectedStageId.value}`, { responseType: "blob" });
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
    const res = await api.post("/stages/internal-behavior-summary/apply", form, { headers: { "Content-Type": "multipart/form-data" } });
    lastResult.value = res.data ?? null;
    ElMessage.success("行为信息已导入并生成阶段画像");
    await loadReport();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "应用行为汇总失败");
  } finally {
    applying.value = false;
  }
}

function goToImports() {
  router.push({ path: "/teacher/evaluation", query: { ...buildTeacherSubjectQuery(subject.value), tab: "imports" } });
}

function applyRiskFilter(filter: RiskFilter) {
  activeRiskFilter.value = filter;
  scrollToDetails();
}

function focusStudent(row: BehaviorRow) {
  highlightedStudentId.value = row.user_id;
  activeRiskFilter.value = normalizeRisk(row.risk_level) === "暂无" ? "all" : (normalizeRisk(row.risk_level) as RiskFilter);
  scrollToDetails();
}

function scrollToDetails() {
  nextTick(() => {
    detailTableAnchor.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function detailRowClassName({ row }: { row: BehaviorRow }) {
  return row.user_id === highlightedStudentId.value ? "is-highlighted-row" : "";
}

watch(subject, () => {
  if (!initialized.value || !subject.value) return;
  saveTeacherSubject(subject.value);
});
watch(selectedStageId, () => {
  if (!initialized.value) return;
  syncQuery();
  loadReport();
});
watch(() => route.query.subject, (value) => {
  const next = String(value || "").trim();
  if (next && next !== subject.value) subject.value = next;
});
watch(() => route.query.stage_id, () => {
  const next = queryStageId();
  if (next && next !== selectedStageId.value) selectedStageId.value = next;
});
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
    initialized.value = true;
    syncQuery();
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="report-page">
    <section class="report-toolbar">
      <div class="report-toolbar__context">
        <div class="toolbar-field">
          <label>课程</label>
          <el-select v-model="subject" class="toolbar-field__select" placeholder="选择课程" size="large">
            <el-option v-for="item in courses" :key="item.id" :label="item.title" :value="item.title" />
          </el-select>
        </div>
        <div class="toolbar-field">
          <label>阶段</label>
          <el-select v-model="selectedStageId" class="toolbar-field__select" placeholder="选择阶段" size="large">
            <el-option v-for="item in stages" :key="item.id" :label="`${item.stage_order}. ${item.title}`" :value="item.id" />
          </el-select>
        </div>
      </div>
      <div class="report-toolbar__actions">
        <HintButton size="small" tip="前往数据导入页继续补充数据" @click="goToImports">去数据导入</HintButton>
        <HintButton size="small" tip="导出当前阶段的行为画像明细 CSV" @click="downloadCsv">导出 CSV</HintButton>
        <HintButton size="small" type="primary" :loading="applying" tip="将行为汇总写入当前阶段并重新计算画像" @click="applyBehavior">一键导入并重算</HintButton>
      </div>
    </section>

    <section class="overview-section">
      <div class="section-heading">
        <div>
          <span class="section-heading__eyebrow">核心概览</span>
          <h2>先看整体情况</h2>
        </div>
        <p>{{ selectedStage?.title || "当前未选择阶段" }}</p>
      </div>
      <div class="summary-grid">
        <article class="summary-card summary-card--blue">
          <span class="summary-card__label">行为学生</span>
          <strong class="summary-card__value">{{ report?.summary.behavior_students ?? 0 }}</strong>
          <p class="summary-card__hint">有行为记录的学生数</p>
        </article>
        <article class="summary-card summary-card--green">
          <span class="summary-card__label">平均行为分</span>
          <strong class="summary-card__value">{{ Math.round(avgBehaviorScore * 100) }}%</strong>
          <p class="summary-card__hint">反映当前阶段行为活跃度</p>
        </article>
        <article class="summary-card summary-card--purple">
          <span class="summary-card__label">平均画像分</span>
          <strong class="summary-card__value">{{ Math.round(avgDynamicScore * 100) }}%</strong>
          <p class="summary-card__hint">反映阶段画像综合表现</p>
        </article>
        <article class="summary-card summary-card--red">
          <span class="summary-card__label">风险学生</span>
          <strong class="summary-card__value">{{ watchlistRows.length }}</strong>
          <p class="summary-card__hint">需要优先关注的学生</p>
        </article>
      </div>
    </section>

    <section class="analysis-section">
      <div class="analysis-main">
        <div class="panel-heading">
          <div>
            <span class="panel-heading__eyebrow">阶段行为画像</span>
            <h3>学生行为画像排行</h3>
          </div>
          <p>优先查看当前阶段最具代表性的行为画像变化</p>
        </div>
        <div v-if="hasBehaviorData" class="rank-list">
          <button v-for="row in rankRows" :key="row.user_id" type="button" class="rank-item" @click="focusStudent(row)">
            <div class="rank-item__main">
              <div class="rank-item__identity">
                <strong>{{ getDisplayName(row) }}</strong>
                <span>{{ row.student_no || row.username }}</span>
              </div>
              <div class="rank-item__progress">
                <div class="metric-line">
                  <span>行为分</span>
                  <div class="metric-line__track"><div class="metric-line__fill metric-line__fill--behavior" :style="{ width: formatPercent(row.behavior_score) }" /></div>
                  <strong>{{ formatPercent(row.behavior_score) }}</strong>
                </div>
                <div class="metric-line">
                  <span>画像分</span>
                  <div class="metric-line__track"><div class="metric-line__fill metric-line__fill--portrait" :style="{ width: formatPercent(row.dynamic_score) }" /></div>
                  <strong>{{ formatPercent(row.dynamic_score) }}</strong>
                </div>
              </div>
            </div>
            <div class="rank-item__side">
              <span class="signal-chip">{{ row.dominant_signal || "观察" }}</span>
              <span class="risk-chip" :class="riskClass(row.risk_level)">{{ normalizeRisk(row.risk_level) }}</span>
            </div>
          </button>
        </div>
        <div v-else class="empty-panel"><strong>暂无有效行为画像数据</strong><p>请先完成数据导入或执行重算</p></div>
      </div>

      <div class="analysis-side">
        <article class="side-card">
          <div class="panel-heading panel-heading--compact"><div><span class="panel-heading__eyebrow">风险分析</span><h3>风险分布</h3></div></div>
          <div v-if="rows.length" class="risk-stack">
            <button v-for="item in riskDistribution" :key="item.label" type="button" class="risk-stack__item" :class="[`risk-stack__item--${item.tone}`, { 'is-active': activeRiskFilter === item.label || (activeRiskFilter === 'risk' && item.label !== '暂无') }]" @click="applyRiskFilter(item.label === '暂无' ? 'all' : (item.label as RiskFilter))">
              <div class="risk-stack__head"><span>{{ item.label }}</span><strong>{{ item.count }}</strong></div>
              <div class="risk-stack__track"><div class="risk-stack__fill" :style="{ width: `${item.percent}%` }" /></div>
            </button>
          </div>
          <div v-else class="empty-panel empty-panel--compact"><strong>暂无风险分布数据</strong><p>待完成阶段计算后显示</p></div>
        </article>

        <article class="side-card">
          <div class="panel-heading panel-heading--compact"><div><span class="panel-heading__eyebrow">核心行为指标</span><h3>关键指标</h3></div></div>
          <div class="mini-stats">
            <div class="mini-stat"><span>平均活跃天数</span><strong>{{ avgActiveDays.toFixed(1) }}</strong></div>
            <div class="mini-stat"><span>平均正值度</span><strong>{{ Math.round(avgPositiveRate * 100) }}%</strong></div>
            <div class="mini-stat"><span>行为事件数</span><strong>{{ totalBehaviorEvents }}</strong></div>
            <div class="mini-stat"><span>表情信号数</span><strong>{{ totalExpressions }}</strong></div>
          </div>
        </article>

        <article class="side-card">
          <div class="panel-heading panel-heading--compact"><div><span class="panel-heading__eyebrow">重点名单</span><h3>重点关注名单</h3></div></div>
          <div v-if="watchlistRows.length" class="watch-list">
            <button v-for="row in watchlistRows" :key="row.user_id" type="button" class="watch-item" @click="focusStudent(row)">
              <div><strong>{{ getDisplayName(row) }}</strong><span>{{ row.student_no || row.username }}</span></div>
              <div class="watch-item__meta"><span class="risk-chip" :class="riskClass(row.risk_level)">{{ normalizeRisk(row.risk_level) }}</span><strong>{{ formatPercent(row.dynamic_score) }}</strong></div>
            </button>
          </div>
          <div v-else class="empty-panel empty-panel--compact"><strong>当前暂无重点高风险学生</strong><p>可继续查看下方学生明细</p></div>
        </article>
      </div>
    </section>
    <section class="focus-section">
      <div class="section-heading">
        <div><span class="section-heading__eyebrow">重点关注学生</span><h2>优先处理的学生</h2></div>
        <p>高风险学生优先展示，可快速定位到明细表</p>
      </div>
      <div v-if="focusStudents.length" class="focus-grid">
        <article v-for="row in focusStudents" :key="row.user_id" class="focus-card" :class="riskClass(row.risk_level)">
          <span class="focus-card__accent" />
          <div class="focus-card__head">
            <div><strong>{{ getDisplayName(row) }}</strong><span>{{ row.student_no || row.username }}</span></div>
            <span class="risk-chip" :class="riskClass(row.risk_level)">{{ normalizeRisk(row.risk_level) }}</span>
          </div>
          <div class="focus-card__stats">
            <div><span>行为分</span><strong>{{ formatPercent(row.behavior_score) }}</strong></div>
            <div><span>画像分</span><strong>{{ formatPercent(row.dynamic_score) }}</strong></div>
          </div>
          <div class="focus-card__signal">主信号：{{ row.dominant_signal || "观察" }}</div>
          <div class="focus-card__actions"><HintButton size="small" tip="定位到学生行为明细" @click="focusStudent(row)">查看详情</HintButton></div>
        </article>
      </div>
      <div v-else class="empty-panel"><strong>当前暂无重点高风险学生</strong><p>可继续查看下方学生明细</p></div>
    </section>

    <section ref="detailTableAnchor" class="detail-section">
      <div class="section-heading">
        <div><span class="section-heading__eyebrow">学生行为明细</span></div>
        <div class="filter-pills">
          <button v-for="item in detailFilterOptions" :key="item.value" type="button" class="filter-pill" :class="{ 'is-active': activeRiskFilter === item.value }" @click="activeRiskFilter = item.value">{{ item.label }}</button>
        </div>
      </div>
      <div class="detail-table-shell">
        <el-table v-if="detailRows.length" :data="detailRows" size="large" style="width: 100%" :row-class-name="detailRowClassName">
          <el-table-column prop="username" label="账号" min-width="120" />
          <el-table-column prop="student_no" label="学号" min-width="120" />
          <el-table-column prop="full_name" label="姓名" min-width="110"><template #default="{ row }">{{ getDisplayName(row) }}</template></el-table-column>
          <el-table-column prop="behavior_score" label="行为分" min-width="100"><template #default="{ row }">{{ formatPercent(row.behavior_score) }}</template></el-table-column>
          <el-table-column prop="dynamic_score" label="画像分" min-width="100"><template #default="{ row }">{{ formatPercent(row.dynamic_score) }}</template></el-table-column>
          <el-table-column prop="dominant_signal" label="主信号" min-width="120"><template #default="{ row }">{{ row.dominant_signal || "观察" }}</template></el-table-column>
          <el-table-column prop="risk_level" label="风险等级" min-width="120"><template #default="{ row }"><span class="risk-chip" :class="riskClass(row.risk_level)">{{ normalizeRisk(row.risk_level) }}</span></template></el-table-column>
          <el-table-column prop="behavior_events" label="事件数" min-width="90" />
          <el-table-column prop="active_days" label="活跃天数" min-width="100" />
        </el-table>
        <div v-else class="empty-panel empty-panel--table"><strong>暂无符合条件的学生明细</strong><p>请切换风险筛选，或先完成数据导入与阶段重算</p></div>
      </div>
      <div v-if="lastResult" class="recalc-summary">
        <div class="recalc-summary__item"><span>导入记录</span><strong>{{ lastResult.total_rows }}</strong></div>
        <div class="recalc-summary__item"><span>成功导入</span><strong>{{ lastResult.success_rows }}</strong></div>
        <div class="recalc-summary__item"><span>重算学生</span><strong>{{ lastResult.recalculated_users }}</strong></div>
        <div class="recalc-summary__item recalc-summary__item--wide"><span>下一步</span><strong>{{ lastResult.next_action }}</strong></div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.report-page { display: grid; gap: 18px; padding: 4px 0 20px; }
.report-toolbar, .overview-section, .analysis-main, .side-card, .focus-section, .detail-section { border: 1px solid rgba(148, 163, 184, 0.22); border-radius: 20px; background: radial-gradient(circle at top right, rgba(191, 221, 254, 0.16), transparent 28%), linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07), inset 0 1px 0 rgba(255,255,255,.78); }
.report-toolbar { padding: 16px 18px; }
.overview-section, .focus-section, .detail-section { padding: 20px; }
.analysis-section { display: grid; grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr); gap: 18px; }
.analysis-main, .side-card { padding: 20px; }
.analysis-side { display: grid; gap: 18px; }
.report-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.report-toolbar__context { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.section-heading__eyebrow, .panel-heading__eyebrow { font-size: 12px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: #586537; }
.section-heading h2, .panel-heading h3 { margin: 0; color: #1f2937; }
.section-heading p, .panel-heading p { margin: 0; color: #6a7280; font-size: 12px; }
.toolbar-field { display: grid; gap: 6px; min-width: 240px; }
.toolbar-field label { font-size: 12px; color: #7c5e3d; font-weight: 700; }
.toolbar-field__select { width: min(320px, 100%); }
.report-toolbar__actions, .filter-pills { display: flex; gap: 10px; flex-wrap: wrap; }
.section-heading, .panel-heading { display: flex; justify-content: space-between; gap: 14px; align-items: flex-end; margin-bottom: 16px; }
.panel-heading--compact { margin-bottom: 16px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.summary-card { position: relative; overflow: hidden; padding: 18px; border-radius: 18px; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); border: 1px solid rgba(191, 167, 132, 0.24); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82); }
.summary-card::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 5px; border-radius: 16px 0 0 16px; }
.summary-card--blue::before { background: #8ed4f4; } .summary-card--green::before { background: #22c55e; } .summary-card--purple::before { background: #ffd6cb; } .summary-card--red::before { background: #cf7f49; }
.summary-card__label { display: block; font-size: 13px; font-weight: 700; color: #6a7280; }
.summary-card__value { display: block; margin-top: 10px; font-size: 32px; line-height: 1; font-weight: 800; letter-spacing: -0.03em; color: #1f2937; }
.summary-card__hint { margin: 10px 0 0; font-size: 13px; color: #6a7280; }
.rank-list, .watch-list { display: grid; gap: 14px; }
.rank-item, .watch-item { width: 100%; border: 1.5px solid #e5ddd1; border-radius: 20px; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease; cursor: pointer; }
.rank-item:hover, .watch-item:hover, .focus-card:hover { transform: translateY(-2px); border-color: #d8dfc7; box-shadow: 0 10px 24px rgba(121, 110, 84, 0.1); }
.rank-item { display: flex; justify-content: space-between; gap: 18px; padding: 18px; text-align: left; }
.rank-item__main { flex: 1; display: grid; gap: 14px; }
.rank-item__identity { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.rank-item__identity strong { font-size: 16px; color: #1f5130; }
.rank-item__identity span, .focus-card__head span, .watch-item span, .signal-chip, .metric-line span { color: #5b715e; font-size: 13px; }
.rank-item__progress { display: grid; gap: 10px; }
.metric-line { display: grid; grid-template-columns: 54px 1fr auto; gap: 12px; align-items: center; }
.metric-line strong { font-size: 13px; color: #1f5130; }
.metric-line__track, .risk-stack__track { height: 10px; border-radius: 999px; background: #edf1e9; overflow: hidden; }
.metric-line__fill, .risk-stack__fill { height: 100%; border-radius: inherit; }
.metric-line__fill--behavior { background: linear-gradient(90deg, #c7e38e, #5f8f4a); } .metric-line__fill--portrait { background: linear-gradient(90deg, #9dd3c2, #3d9b8c); }
.rank-item__side { display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
.signal-chip, .risk-chip, .filter-pill { display: inline-flex; align-items: center; justify-content: center; min-height: 30px; padding: 0 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.signal-chip { background: rgba(224, 242, 226, 0.96); color: #2f6d42; }
.risk-chip { border: 1px solid transparent; }
.risk-高风险 { background: rgba(207, 127, 73, 0.12); color: #a75a2a; border-color: rgba(207, 127, 73, 0.22); }
.risk-中风险 { background: rgba(184, 143, 70, 0.14); color: #8f6a2a; border-color: rgba(184, 143, 70, 0.22); }
.risk-低风险 { background: rgba(154, 198, 89, 0.16); color: #5f7a33; border-color: rgba(154, 198, 89, 0.24); }
.risk-暂无 { background: rgba(213, 207, 196, 0.2); color: #7e705c; border-color: rgba(213, 207, 196, 0.36); }
.risk-stack { display: grid; gap: 12px; }
.risk-stack__item { width: 100%; padding: 14px 16px; border: 1.5px solid #e5ddd1; border-radius: 18px; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); text-align: left; cursor: pointer; transition: border-color 0.18s ease, transform 0.18s ease; }
.risk-stack__item:hover, .risk-stack__item.is-active { transform: translateY(-1px); border-color: #d8dfc7; }
.risk-stack__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.risk-stack__head span { font-size: 13px; font-weight: 700; color: #1f5130; }
.risk-stack__head strong { font-size: 18px; color: #1f5130; }
.risk-stack__item--high .risk-stack__fill { background: linear-gradient(90deg, #efc29f, #cf7f49); } .risk-stack__item--medium .risk-stack__fill { background: linear-gradient(90deg, #ead0a0, #b88f46); } .risk-stack__item--low .risk-stack__fill { background: linear-gradient(90deg, #d6ebb1, #9ac659); } .risk-stack__item--none .risk-stack__fill { background: linear-gradient(90deg, #e7e0d5, #cbbd9d); }
.mini-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.mini-stat { padding: 16px; border-radius: 18px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); display: grid; gap: 8px; }
.mini-stat span { font-size: 12px; color: #5b715e; }
.mini-stat strong { font-size: 26px; line-height: 1; color: #1f5130; }
.watch-item { display: flex; justify-content: space-between; gap: 16px; padding: 14px 16px; text-align: left; }
.watch-item strong, .focus-card__head strong { display: block; font-size: 15px; color: #1f5130; }
.watch-item__meta { display: flex; align-items: center; gap: 10px; }
.watch-item__meta strong { font-size: 14px; }
.focus-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.focus-card { position: relative; overflow: hidden; border: 1.5px solid #e5ddd1; border-radius: 22px; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); padding: 20px; transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease; }
.focus-card__accent { position: absolute; left: 0; top: 0; bottom: 0; width: 5px; background: #d8cfbe; }
.focus-card.risk-高风险 .focus-card__accent { background: #cf7f49; } .focus-card.risk-中风险 .focus-card__accent { background: #b88f46; } .focus-card.risk-低风险 .focus-card__accent { background: #9ac659; }
.focus-card__head { display: flex; justify-content: space-between; gap: 12px; }
.focus-card__stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }
.focus-card__stats span, .focus-card__signal { font-size: 12px; color: #5b715e; }
.focus-card__stats strong { display: block; margin-top: 6px; font-size: 22px; color: #1f5130; }
.focus-card__signal { margin-top: 14px; }
.focus-card__actions { margin-top: 18px; }
.detail-section { display: grid; gap: 20px; }
.filter-pill { border: 1.5px solid rgba(31, 41, 55, 0.14); background: linear-gradient(180deg, #dff2fb 0%, #fff7ef 100%); color: #6b7280; cursor: pointer; transition: all 0.18s ease; }
.filter-pill.is-active, .filter-pill:hover { background: radial-gradient(circle at top left, rgba(215, 249, 168, 0.42), transparent 60%), #fffdf6; border-color: #1f2937; color: #1f2937; }
.detail-table-shell { overflow: hidden; border: 1.5px solid #d9e6f2; border-radius: 22px; background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,0.84); }
.empty-panel { min-height: 180px; display: grid; place-content: center; gap: 8px; text-align: center; border: 1px dashed rgba(138, 171, 147, 0.4); border-radius: 20px; background: linear-gradient(180deg, rgba(243, 249, 244, 0.92), rgba(255, 255, 255, 0.96)); }
.empty-panel--compact { min-height: 120px; } .empty-panel--table { min-height: 220px; margin: 16px; }
.empty-panel strong { color: #1f5130; font-size: 18px; } .empty-panel p { margin: 0; color: #5b715e; }
.recalc-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.recalc-summary__item { padding: 16px; border-radius: 18px; border: 1.5px solid #e5ddd1; background: linear-gradient(180deg, #fffdfa 0%, #fff8f1 100%); display: grid; gap: 8px; }
.recalc-summary__item span { font-size: 12px; color: #5b715e; } .recalc-summary__item strong { font-size: 22px; color: #1f5130; line-height: 1.35; }
.recalc-summary__item--wide { grid-column: span 2; }
:deep(.detail-table-shell .el-table) { --el-table-border-color: #d9e6f2; --el-table-header-bg-color: #f6faff; --el-table-row-hover-bg-color: #f8fbff; background: transparent !important; }
:deep(.detail-table-shell .el-table::before),
:deep(.detail-table-shell .el-table--border::before),
:deep(.detail-table-shell .el-table--border::after),
:deep(.detail-table-shell .el-table__border-left-patch) { background: #d9e6f2 !important; }
:deep(.detail-table-shell .el-table th.el-table__cell) { color: #475569; font-weight: 700; height: 52px; background: linear-gradient(180deg, #f8fbff 0%, #f3f8ff 100%) !important; }
:deep(.detail-table-shell .el-table td.el-table__cell) { padding: 16px 0; background: transparent !important; }
:deep(.detail-table-shell .el-table tr td.el-table__cell),
:deep(.detail-table-shell .el-table tr th.el-table__cell) { border-bottom: 1px solid #e4edf6 !important; }
:deep(.detail-table-shell .el-table__row:nth-child(even) td.el-table__cell) { background: rgba(248, 251, 255, 0.72) !important; }
:deep(.detail-table-shell .el-table__row:hover > td.el-table__cell) { background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%) !important; }
:deep(.detail-table-shell .el-table .is-highlighted-row td.el-table__cell) { background: rgba(224, 242, 226, 0.9); }
:deep(.report-toolbar .el-select__wrapper) { border-radius: 18px; box-shadow: 0 0 0 1px #dde3ef inset; background: linear-gradient(180deg, #fffdfa 0%, #fff7ef 100%); }
:deep(.report-toolbar .el-select__wrapper.is-focused) { box-shadow: 0 0 0 1px #60a5fa inset, 0 0 0 4px rgba(96, 165, 250, 0.14); }
:deep(.report-toolbar .el-select__selected-item), :deep(.report-toolbar .el-select__placeholder), :deep(.report-toolbar .el-select__caret) { color: #5f6f85 !important; }
:deep(.report-toolbar .el-button--primary) { border-color: rgba(31, 41, 55, 0.14); background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: #ffffff; }
@media (max-width: 1280px) { .summary-grid, .focus-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .analysis-section { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .report-toolbar, .report-toolbar__context, .section-heading, .panel-heading { align-items: stretch; } .summary-grid, .focus-grid, .recalc-summary { grid-template-columns: 1fr; } .mini-stats { grid-template-columns: 1fr 1fr; } }
@media (max-width: 640px) { .report-page { gap: 18px; } .report-toolbar, .overview-section, .analysis-main, .side-card, .focus-section, .detail-section { padding: 18px; } .mini-stats, .focus-card__stats { grid-template-columns: 1fr; } .metric-line { grid-template-columns: 1fr; } }
</style>
