<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const props = withDefaults(
  defineProps<{ subject: string; grade: string; showStudentDetailAction?: boolean }>(),
  { showStudentDetailAction: false }
);
const emit = defineEmits<{
  (e: "view-student", userId: number): void;
}>();

type StageSummary = {
  stage_id: number;
  stage_title: string;
  stage_order: number;
  student_count: number;
  avg_dynamic_score: number;
  avg_course_mastery: number;
  risk_count: number;
  progress_count: number;
  steady_count: number;
  regress_count: number;
};

type StudentRow = Record<string, any>;
type WeakKpRow = Record<string, any>;
type RiskFilter = "all" | "high" | "medium" | "low";

const loading = ref(false);
const activeRiskFilter = ref<RiskFilter>("all");
const riskTableAnchor = ref<HTMLElement | null>(null);
const activeStudentId = ref<number | null>(null);

const data = ref({
  total_students: 0,
  persona_distribution: [] as Array<{ persona_label: string; count: number }>,
  stage_summary: [] as StageSummary[],
  latest_stage: null as StageSummary | null,
  risk_students: [] as StudentRow[],
  weak_kps: [] as WeakKpRow[],
  progress_ranking: [] as StudentRow[],
  ability_practice_cohort: {} as Record<string, any>,
});

const stageCount = computed(() => data.value.stage_summary.length);
const latestStageScore = computed(() => Math.round((data.value.latest_stage?.avg_dynamic_score ?? 0) * 100));
const latestStageMastery = computed(() => Math.round((data.value.latest_stage?.avg_course_mastery ?? 0) * 100));
const practiceCount = computed(() => data.value.ability_practice_cohort?.overall?.attempts ?? 0);

const cohortAbility = computed(() => data.value.ability_practice_cohort ?? {});
const cohortHasPractice = computed(() => (cohortAbility.value?.overall?.attempts ?? 0) > 0);

function bloomLabel(level: string) {
  const map: Record<string, string> = {
    remember: "记忆",
    understand: "理解",
    apply: "应用",
    analyze: "分析",
    evaluate: "评价",
    create: "创造",
  };
  return map[level] || level;
}

function normalizeRisk(level?: string) {
  if (level === "高风险") return "高风险";
  if (level === "中风险" || level === "风险") return "中风险";
  if (level === "低风险") return "低风险";
  return "低风险";
}

function riskTagClass(level?: string) {
  const normalized = normalizeRisk(level);
  if (normalized === "高风险") return "risk-tag risk-tag--high";
  if (normalized === "中风险") return "risk-tag risk-tag--medium";
  return "risk-tag risk-tag--low";
}

function riskToneClass(level?: string) {
  const normalized = normalizeRisk(level);
  if (normalized === "高风险") return "risk-tone--high";
  if (normalized === "中风险") return "risk-tone--medium";
  return "risk-tone--low";
}

function progressWidth(value: number) {
  return `${Math.max(4, Math.min(100, Math.round(value)))}%`;
}

const personaTotal = computed(() => {
  const total = data.value.persona_distribution.reduce((sum, item) => sum + (item.count || 0), 0);
  return Math.max(total, data.value.total_students || 0, 1);
});

const personaDistribution = computed(() =>
  data.value.persona_distribution.map((item) => ({
    ...item,
    percent: Math.round(((item.count || 0) / personaTotal.value) * 100),
  }))
);

const stageTrendData = computed(() =>
  data.value.stage_summary.map((item) => ({
    ...item,
    score: Math.round((item.avg_dynamic_score || 0) * 100),
    mastery: Math.round((item.avg_course_mastery || 0) * 100),
  }))
);

const maxStageMetric = computed(() => {
  const values = stageTrendData.value.flatMap((item) => [item.score, item.mastery]);
  return Math.max(...values, 1);
});

const overallAccuracy = computed(() => Math.round((cohortAbility.value?.overall?.accuracy ?? 0) * 100));
const highOrderAccuracy = computed(() => Math.round((cohortAbility.value?.high_order_overall?.accuracy ?? 0) * 100));

const weakKnowledgeList = computed(() =>
  [...data.value.weak_kps]
    .sort((a, b) => (a.avg_mastery || 0) - (b.avg_mastery || 0))
    .slice(0, 5)
    .map((item, index) => ({
      ...item,
      rank: index + 1,
      masteryPercent: Math.round((item.avg_mastery || 0) * 100),
    }))
);

const riskOverview = computed(() => {
  const students = data.value.risk_students ?? [];
  const counts = {
    高风险: 0,
    中风险: 0,
    低风险: 0,
  };
  students.forEach((row) => {
    counts[normalizeRisk(row.risk_level)] += 1;
  });
  const total = Math.max(students.length, 1);
  return [
    { key: "high", label: "高风险", count: counts["高风险"], percent: Math.round((counts["高风险"] / total) * 100), tone: "high" },
    { key: "medium", label: "中风险", count: counts["中风险"], percent: Math.round((counts["中风险"] / total) * 100), tone: "medium" },
    { key: "low", label: "低风险", count: counts["低风险"], percent: Math.round((counts["低风险"] / total) * 100), tone: "low" },
  ];
});

function getActivityDays(row: StudentRow) {
  const value = row.active_days ?? row.activity_days ?? row.active_day_count ?? row.active_day;
  return typeof value === "number" ? value : 9999;
}

function getProblemSummary(row: StudentRow) {
  const raw = String(row.reason_summary || "").trim();
  if (!raw) return "参与度偏低，学习成效偏弱";
  const afterJudge = raw.includes("主要判断：") ? raw.split("主要判断：").pop() : raw;
  const compact = String(afterJudge || "")
    .replace(/^；+/, "")
    .replace(/\s+/g, " ")
    .trim();
  return compact || "参与度偏低，学习成效偏弱";
}

const focusStudents = computed(() =>
  [...data.value.risk_students]
    .sort((a, b) => {
      const riskWeight = { 高风险: 3, 中风险: 2, 低风险: 1 };
      const diff = riskWeight[normalizeRisk(b.risk_level)] - riskWeight[normalizeRisk(a.risk_level)];
      if (diff !== 0) return diff;

      const masteryDiff = (a.course_mastery ?? 1) - (b.course_mastery ?? 1);
      if (masteryDiff !== 0) return masteryDiff;

      return getActivityDays(a) - getActivityDays(b);
    })
    .slice(0, 3)
);

const focusStudentIdSet = computed(() => new Set(focusStudents.value.map((row) => Number(row.user_id))));

const filteredRiskStudents = computed(() => {
  const list = [...data.value.risk_students];
  if (activeRiskFilter.value === "all") return list;
  const target =
    activeRiskFilter.value === "high" ? "高风险" : activeRiskFilter.value === "medium" ? "中风险" : "低风险";
  return list.filter((row) => normalizeRisk(row.risk_level) === target);
});

const progressRankingRows = computed(() =>
  [...data.value.progress_ranking].sort((a, b) => (b.dynamic_score || 0) - (a.dynamic_score || 0))
);

const progressRankingList = computed(() =>
  progressRankingRows.value
    .filter((row) => !focusStudentIdSet.value.has(Number(row.user_id)))
    .map((row, index) => ({
    ...row,
    rank: index + 1,
    masteryPercent: Math.round((row.course_mastery || 0) * 100),
    }))
);

const summaryCards = computed(() => [
  { key: "students", label: "班级学生数", value: data.value.total_students, hint: "当前课程下已纳入分析的学生", tone: "blue" },
  { key: "stages", label: "阶段完成数", value: stageCount.value, hint: "已有阶段评价数据的阶段数", tone: "blue" },
  { key: "risk", label: "风险学生数", value: data.value.risk_students.length, hint: "需要优先关注的学生", tone: "red" },
  { key: "score", label: "最新平均分", value: `${latestStageScore.value}%`, hint: "最近阶段动态评价平均分", tone: "blue" },
  { key: "mastery", label: "最新平均掌握度", value: `${latestStageMastery.value}%`, hint: "最近阶段课程掌握情况", tone: "green" },
  { key: "practice", label: "测验完成数", value: practiceCount.value, hint: "当前班级已完成的练习尝试数", tone: "green" },
]);

const suggestionText = computed(() => {
  const high = riskOverview.value.find((item) => item.label === "高风险")?.count ?? 0;
  if (high > 0) return `当前班级有 ${high} 名高风险学生，建议优先查看重点关注学生与风险学生清单。`;
  if (weakKnowledgeList.value.length > 0) return `当前薄弱知识点集中在 ${weakKnowledgeList.value[0].title} 等内容，建议先安排针对性练习。`;
  return "当前班级整体风险较低，可继续关注知识薄弱点与学习进度变化。";
});

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const res = await api.get(
      `/admin/analytics/overview?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    data.value = res.data;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载学习分析失败");
  } finally {
    loading.value = false;
  }
}

function scrollToRiskTable() {
  nextTick(() => {
    riskTableAnchor.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function applyRiskFilter(filter: RiskFilter) {
  activeRiskFilter.value = filter;
  scrollToRiskTable();
}

function isRiskStudent(row: StudentRow) {
  return data.value.risk_students.some((item) => Number(item.user_id) === Number(row.user_id));
}

function activateStudent(row: StudentRow, options?: { scrollToRisk?: boolean }) {
  activeStudentId.value = Number(row.user_id);
  if (options?.scrollToRisk && isRiskStudent(row)) {
    scrollToRiskTable();
  }
}

function openStudent(row: StudentRow) {
  emit("view-student", Number(row.user_id));
}

watch(
  () => [props.subject, props.grade],
  () => load(),
  { immediate: true }
);
</script>

<template>
  <div class="analytics-shell" v-loading="loading">
    <section class="summary-cards">
      <button
        v-for="card in summaryCards"
        :key="card.key"
        type="button"
        class="summary-card"
        :class="`summary-card--${card.tone}`"
        @click="card.key === 'risk' ? applyRiskFilter('all') : undefined"
      >
        <span class="summary-card__label">{{ card.label }}</span>
        <strong class="summary-card__value">{{ card.value }}</strong>
        <span class="summary-card__hint">{{ card.hint }}</span>
      </button>
    </section>

    <section class="focus-section">
      <div class="section-title">
        <div class="focus-section__title">
          <span class="focus-section__dot" />
          <div class="focus-section__title-copy">
            <span class="section-title__eyebrow">重点关注学生</span>
            <h3>重点关注学生</h3>
            <p>系统已为你筛选出最需要优先干预的学生</p>
          </div>
        </div>
        <el-button class="focus-section__guide-btn" @click="applyRiskFilter('all')">查看风险清单</el-button>
      </div>
      <div v-if="focusStudents.length" class="focus-grid">
        <article
          v-for="row in focusStudents"
          :key="row.user_id"
          class="focus-card"
          :class="[riskToneClass(row.risk_level), { 'is-active': activeStudentId === Number(row.user_id) }]"
          @click="activateStudent(row, { scrollToRisk: true })"
        >
          <span class="focus-card__accent" />
          <div class="focus-card__main">
            <div class="focus-card__topline">
              <div class="focus-card__name-group">
                <strong>{{ row.full_name || "未命名学生" }}</strong>
                <button
                  type="button"
                  :class="riskTagClass(row.risk_level)"
                  @click.stop="applyRiskFilter(normalizeRisk(row.risk_level) === '高风险' ? 'high' : normalizeRisk(row.risk_level) === '中风险' ? 'medium' : 'low')"
                >
                  {{ normalizeRisk(row.risk_level) }}
                </button>
              </div>
            </div>
            <div class="focus-card__meta">
              <span>掌握度 {{ Math.round((row.course_mastery || 0) * 100) }}%</span>
              <span>{{ row.persona_label || "未分类" }}</span>
            </div>
            <div class="focus-card__issue">
              <span>主要问题</span>
              <strong>{{ getProblemSummary(row) }}</strong>
            </div>
          </div>
          <div v-if="props.showStudentDetailAction" class="focus-card__actions">
            <el-button size="small" type="primary" @click.stop="openStudent(row)">查看详情</el-button>
          </div>
        </article>
      </div>
      <div v-if="focusStudents.length" class="focus-section__guide">
        <span>处理建议</span>
        <p>优先处理高风险、低掌握度且近期活跃度偏低的学生，再到下方风险学生清单查看完整原因。</p>
      </div>
      <div v-else class="empty-panel">
        <strong>当前暂无重点风险学生</strong>
        <p>班级整体状态良好</p>
      </div>
    </section>

    <section class="detail-layout">
      <article ref="riskTableAnchor" class="analytics-card analytics-card--stack">
        <div class="card-header">
          <div>
            <span class="card-header__eyebrow">风险学生清单</span>
            <h3>优先处理对象</h3>
          </div>
          <div class="table-filters">
            <button
              v-for="item in [
                { label: '全部', value: 'all' },
                { label: '高风险', value: 'high' },
                { label: '中风险', value: 'medium' },
                { label: '低风险', value: 'low' },
              ]"
              :key="item.value"
              type="button"
              class="table-filter"
              :class="{ 'is-active': activeRiskFilter === item.value }"
              @click="activeRiskFilter = item.value as RiskFilter"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <div v-if="filteredRiskStudents.length" class="risk-student-list">
          <article
            v-for="row in filteredRiskStudents"
            :key="row.user_id"
            class="risk-student-row"
            :class="{ 'is-active': activeStudentId === Number(row.user_id) }"
            @click="activateStudent(row)"
          >
            <div class="risk-student-row__main">
              <div class="risk-student-row__identity">
                <strong>{{ row.full_name || "未命名学生" }}</strong>
                <span>{{ row.persona_label || "未分类" }} · {{ row.latest_stage_title || "暂无阶段" }}</span>
              </div>
              <div class="risk-student-row__problem">
                <span>主要问题</span>
                <strong>{{ getProblemSummary(row) }}</strong>
              </div>
            </div>
            <div class="risk-student-row__aside">
              <button
                type="button"
                :class="riskTagClass(row.risk_level)"
                @click.stop="applyRiskFilter(normalizeRisk(row.risk_level) === '高风险' ? 'high' : normalizeRisk(row.risk_level) === '中风险' ? 'medium' : 'low')"
              >
                {{ normalizeRisk(row.risk_level) }}
              </button>
              <el-button v-if="props.showStudentDetailAction" size="small" @click.stop="openStudent(row)">查看</el-button>
            </div>
          </article>
        </div>
        <div v-else class="empty-panel empty-panel--compact">
          <strong>暂无符合条件的学生</strong>
          <p>请切换筛选条件后查看</p>
        </div>
      </article>

      <section class="analysis-overview">
        <div class="analysis-overview__header">
          <div>
            <span class="card-header__eyebrow">班级分析概览</span>
            <h3>班级分析概览</h3>
            <p>聚合展示类型分布、薄弱知识点、风险结构与练习表现，帮助快速判断班级整体状态。</p>
          </div>
        </div>

        <div class="analysis-layout">
          <div class="analysis-row">
            <article class="analytics-card analytics-card--compact">
              <div class="card-header card-header--compact">
                <div>
                  <span class="card-header__eyebrow">学习者类型分布</span>
                  <h3>班级学习者类型</h3>
                </div>
              </div>
              <div v-if="personaDistribution.length" class="persona-list">
                <div v-for="item in personaDistribution" :key="item.persona_label" class="persona-row">
                  <div class="persona-row__head">
                    <strong>{{ item.persona_label }}</strong>
                    <span>{{ item.count }} 人（{{ item.percent }}%）</span>
                  </div>
                  <div class="persona-row__track">
                    <div class="persona-row__fill" :style="{ width: progressWidth(item.percent) }" />
                  </div>
                </div>
              </div>
              <div v-else class="empty-panel empty-panel--compact">
                <strong>暂无学习者类型数据</strong>
                <p>待班级画像数据生成后显示</p>
              </div>
            </article>
            <article class="analytics-card analytics-card--compact">
              <div class="card-header card-header--compact">
                <div>
                  <span class="card-header__eyebrow">知识薄弱点</span>
                  <h3>薄弱知识点 Top5</h3>
                </div>
              </div>
              <div v-if="weakKnowledgeList.length" class="knowledge-list">
                <button v-for="item in weakKnowledgeList" :key="item.code || item.title" type="button" class="knowledge-item">
                  <div class="knowledge-item__head">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.masteryPercent }}%</span>
                  </div>
                  <div class="knowledge-item__code">{{ item.code }}</div>
                  <div class="knowledge-item__track">
                    <div class="knowledge-item__fill" :style="{ width: progressWidth(item.masteryPercent) }" />
                  </div>
                </button>
              </div>
              <div v-else class="empty-panel empty-panel--compact">
                <strong>暂无知识薄弱点数据</strong>
                <p>待班级知识分析完成后显示</p>
              </div>
            </article>
          </div>

          <div class="analysis-row">
            <article class="analytics-card analytics-card--compact">
              <div class="card-header card-header--compact">
                <div>
                  <span class="card-header__eyebrow">风险概览</span>
                  <h3>班级学习风险</h3>
                </div>
              </div>
              <div v-if="riskOverview.some((item) => item.count > 0)" class="risk-overview">
                <button
                  v-for="item in riskOverview"
                  :key="item.label"
                  type="button"
                  class="risk-overview__item"
                  :class="`risk-overview__item--${item.tone}`"
                  @click="applyRiskFilter(item.key as RiskFilter)"
                >
                  <div class="risk-overview__head">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.count }}</strong>
                  </div>
                  <div class="risk-overview__track">
                    <div class="risk-overview__fill" :style="{ width: progressWidth(item.percent) }" />
                  </div>
                </button>
              </div>
              <div v-else class="empty-panel empty-panel--compact">
                <strong>暂无风险分布数据</strong>
                <p>待班级分析结果生成后显示</p>
              </div>
              <div class="advice-panel">{{ suggestionText }}</div>
            </article>

            <article v-if="cohortHasPractice" class="analytics-card analytics-card--compact">
              <div class="card-header card-header--compact">
                <div>
                  <span class="card-header__eyebrow">班级练习与认知能力</span>
                  <h3>练习表现概览</h3>
                </div>
              </div>
              <div class="practice-overview">
                <div class="practice-meter">
                  <div class="practice-meter__head">
                    <strong>完成题量</strong>
                    <span>{{ cohortAbility.overall?.correct ?? 0 }}/{{ cohortAbility.overall?.attempts ?? 0 }}（{{ overallAccuracy }}%）</span>
                  </div>
                  <div class="practice-meter__track">
                    <div class="practice-meter__fill" :style="{ width: progressWidth(overallAccuracy) }" />
                  </div>
                </div>
                <div class="practice-meter">
                  <div class="practice-meter__head">
                    <strong>高阶能力</strong>
                    <span>{{ cohortAbility.high_order_overall?.correct ?? 0 }}/{{ cohortAbility.high_order_overall?.attempts ?? 0 }}（{{ highOrderAccuracy }}%）</span>
                  </div>
                  <div class="practice-meter__track">
                    <div class="practice-meter__fill practice-meter__fill--secondary" :style="{ width: progressWidth(highOrderAccuracy) }" />
                  </div>
                </div>
              </div>
              <div v-if="(cohortAbility.by_cognitive_level?.length ?? 0) > 0" class="cognitive-tags">
                <span v-for="lv in cohortAbility.by_cognitive_level" :key="lv.level" class="cognitive-tag">
                  {{ bloomLabel(lv.level) }} {{ lv.correct }}/{{ lv.attempts }}
                </span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <article class="analytics-card analytics-card--stack analytics-card--subtle">
        <div class="card-header">
          <div>
            <span class="card-header__eyebrow">学习进度排行</span>
            <h3>班级学习进展</h3>
            <p class="card-header__desc">按课程掌握度排序</p>
          </div>
        </div>
        <div v-if="progressRankingList.length" class="progress-ranking-list">
          <article
            v-for="row in progressRankingList"
            :key="row.user_id"
            class="progress-ranking-row"
            :class="{ 'is-active': activeStudentId === Number(row.user_id) }"
            @click="activateStudent(row, { scrollToRisk: true })"
          >
            <span class="progress-ranking-row__rank">{{ row.rank }}</span>
            <div class="progress-ranking-row__identity">
              <strong>{{ row.full_name || "未命名学生" }}</strong>
              <span>{{ row.persona_label || "未分类" }}</span>
            </div>
            <div class="progress-ranking-row__metric">
              <span>{{ row.masteryPercent }}%</span>
              <div class="progress-ranking-row__track">
                <div class="progress-ranking-row__fill" :style="{ width: progressWidth(row.masteryPercent) }" />
              </div>
            </div>
          </article>
        </div>
        <div v-else class="empty-panel empty-panel--compact">
          <strong>暂无学习进展排行</strong>
          <p>待学习数据生成后显示</p>
        </div>
      </article>

      <article v-if="stageTrendData.length" class="analytics-card analytics-card--stack analytics-card--subtle">
        <div class="card-header">
          <div>
            <span class="card-header__eyebrow">班级阶段分析</span>
            <h3>阶段变化趋势</h3>
          </div>
        </div>
        <div class="stage-chart">
          <div v-for="item in stageTrendData" :key="item.stage_id" class="stage-chart__row">
            <div class="stage-chart__meta">
              <strong>阶段 {{ item.stage_order }}</strong>
              <span>{{ item.stage_title }}</span>
            </div>
            <div class="stage-chart__bars">
              <div class="stage-bar">
                <span>平均分</span>
                <div class="stage-bar__track">
                  <div class="stage-bar__fill stage-bar__fill--score" :style="{ width: progressWidth((item.score / maxStageMetric) * 100) }" />
                </div>
                <strong>{{ item.score }}%</strong>
              </div>
              <div class="stage-bar">
                <span>掌握度</span>
                <div class="stage-bar__track">
                  <div class="stage-bar__fill stage-bar__fill--mastery" :style="{ width: progressWidth((item.mastery / maxStageMetric) * 100) }" />
                </div>
                <strong>{{ item.mastery }}%</strong>
              </div>
            </div>
          </div>
        </div>
      </article>
      <article v-else class="analytics-card analytics-card--collapsed">
        <div class="collapsed-state">
          <strong>暂无阶段评价数据</strong>
          <span>请先完成数据导入或执行阶段计算</span>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.analytics-shell {
  display: grid;
  gap: 24px;
  padding-bottom: 12px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 16px;
  padding: 14px;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.24), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.summary-card,
.analytics-card,
.focus-section {
  border: 3px solid #1f2937;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.2), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 10px 0 rgba(31, 41, 55, 0.1);
}

.summary-card {
  padding: 24px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.summary-card:hover,
.analytics-card:hover,
.focus-card:hover,
.knowledge-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(33, 63, 118, 0.1);
}

.summary-card--red {
  border-color: #fee2e2;
}

.summary-card__label,
.card-header__eyebrow,
.section-title__eyebrow {
  font-size: 12px;
  font-weight: 700;
  color: #3b82f6;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-card__value {
  display: block;
  margin-top: 12px;
  font-size: 36px;
  line-height: 1;
  font-weight: 800;
  color: #0f172a;
}

.summary-card__hint {
  display: block;
  margin-top: 12px;
  font-size: 13px;
  color: #64748b;
}

.summary-card--green .summary-card__value {
  color: #22c55e;
}

.summary-card--red .summary-card__value {
  color: #ef4444;
}

.analysis-layout {
  display: grid;
  gap: 16px;
}

.analysis-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}

.analysis-row > .analytics-card {
  height: 100%;
}

.detail-layout {
  display: grid;
  gap: 24px;
}

.analysis-overview {
  display: grid;
  gap: 16px;
}

.analysis-overview__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.analysis-overview__header h3 {
  margin: 6px 0 0;
  font-size: 24px;
  line-height: 1.2;
  color: #0f172a;
}

.analysis-overview__header p,
.card-header__desc {
  margin: 8px 0 0;
  font-size: 14px;
  color: #64748b;
}

.analytics-card,
.focus-section {
  padding: 24px;
}

.analytics-card--compact {
  padding: 18px;
}

.analytics-card--collapsed {
  padding: 16px 20px;
}

.card-header,
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 18px;
}

.card-header h3,
.section-title h3 {
  margin: 4px 0 0;
  font-size: 30px;
  line-height: 1.1;
  color: #0f172a;
}

.card-header--compact {
  margin-bottom: 12px;
}

.card-header--compact h3 {
  font-size: 22px;
}

.persona-list,
.stage-chart,
.knowledge-list {
  display: grid;
  gap: 10px;
}

.persona-row,
.stage-chart__row,
.knowledge-item,
.risk-overview__item,
.focus-card {
  border: 1.5px solid #c6d8ef;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.persona-row,
.stage-chart__row,
.risk-overview__item {
  padding: 12px 14px;
}

.persona-row__head,
.knowledge-item__head,
.risk-overview__head,
.practice-meter__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.persona-row__head strong,
.knowledge-item__head strong,
.risk-overview__head strong,
.focus-card__head strong,
.practice-meter__head strong,
.stage-chart__meta strong {
  color: #0f172a;
  font-size: 14px;
}

.persona-row__head span,
.knowledge-item__head span,
.knowledge-item__code,
.risk-overview__head span,
.practice-meter__head span,
.stage-chart__meta span,
.focus-card__head span,
.focus-card__reason {
  color: #64748b;
  font-size: 12px;
}

.persona-row__track,
.knowledge-item__track,
.risk-overview__track,
.practice-meter__track,
.stage-bar__track {
  height: 8px;
  margin-top: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #e2e8f0;
}

.persona-row__fill,
.knowledge-item__fill,
.risk-overview__fill,
.practice-meter__fill,
.stage-bar__fill {
  height: 100%;
  border-radius: inherit;
}

.persona-row__fill,
.practice-meter__fill {
  background: #3b82f6;
}

.practice-meter__fill--secondary {
  background: #22c55e;
}

.knowledge-item {
  width: 100%;
  padding: 12px 14px;
  text-align: left;
}

.knowledge-item__fill {
  background: #f59e0b;
}

.risk-overview {
  display: grid;
  gap: 12px;
}

.risk-overview__item {
  width: 100%;
  text-align: left;
}

.risk-overview__item--high .risk-overview__fill {
  background: #ef4444;
}

.risk-overview__item--medium .risk-overview__fill {
  background: #f59e0b;
}

.risk-overview__item--low .risk-overview__fill {
  background: #22c55e;
}

.advice-panel {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.practice-overview {
  display: grid;
  gap: 14px;
}

.cognitive-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.cognitive-tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.stage-chart__row {
  display: grid;
  gap: 14px;
}

.stage-chart__bars {
  display: grid;
  gap: 10px;
}

.stage-bar {
  display: grid;
  grid-template-columns: 56px 1fr auto;
  align-items: center;
  gap: 12px;
}

.stage-bar span,
.stage-bar strong {
  font-size: 12px;
}

.stage-bar strong {
  color: #0f172a;
}

.stage-bar__fill--score {
  background: #3b82f6;
}

.stage-bar__fill--mastery {
  background: #22c55e;
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 18px;
}

.focus-section {
  display: grid;
  gap: 18px;
  padding: 24px 26px 26px;
}

.focus-section .section-title {
  margin-bottom: 0;
  align-items: center;
}

.focus-card {
  display: grid;
  grid-template-columns: 4px minmax(0, 1fr) 132px;
  align-items: stretch;
  gap: 0;
  min-height: 172px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  border-radius: 18px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.focus-card__accent {
  align-self: stretch;
  width: 4px;
  background: #e5e7eb;
}

.focus-card.risk-tone--high .focus-card__accent {
  background: #ef4444;
}

.focus-card.risk-tone--medium .focus-card__accent {
  background: #f59e0b;
}

.focus-card.risk-tone--low .focus-card__accent {
  background: #22c55e;
}

.focus-card__main {
  display: grid;
  gap: 8px;
  min-width: 0;
  padding: 16px 16px 16px 18px;
}

.focus-card__topline,
.focus-card__name-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.focus-card__name-group strong {
  font-size: 18px;
  color: #0f172a;
  line-height: 1.2;
}

.focus-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

.focus-card__meta span {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}

.focus-card__issue {
  display: grid;
  gap: 4px;
}

.focus-card__issue span {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.focus-card__issue strong {
  color: #0f172a;
  font-size: 17px;
  line-height: 1.4;
  font-weight: 700;
}

.focus-card__actions {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 16px 16px 16px 8px;
  border-left: 1.5px solid #d9e7f6;
}

.focus-section__dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 999px;
  background: #ef4444;
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.08);
}

.focus-section__title {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.focus-section__title-copy .section-title__eyebrow {
  color: #ef4444;
  font-size: 12px;
  font-weight: 500;
}

.focus-section__title-copy h3 {
  margin: 6px 0 0;
  font-size: 30px;
  line-height: 1.15;
  color: #0f172a;
}

.focus-section__title p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
}

.focus-section__guide {
  display: grid;
  gap: 6px;
  padding: 18px 20px;
  border-radius: 20px;
  background: linear-gradient(180deg, #f4f9ff 0%, #edf6ff 100%);
  border: 1.5px solid #c6d8ef;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.focus-section__guide span {
  color: #2563eb;
  font-size: 14px;
  font-weight: 600;
}

.focus-section__guide p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.focus-card :deep(.el-button) {
  width: 96px;
  height: 36px;
  border-radius: 14px;
  padding: 0 16px;
  background: linear-gradient(135deg, #2754c5 0%, #22c55e 120%);
  border: 1.5px solid #2a5bbf;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(39, 84, 197, 0.16);
  margin-top: 2px;
}

.focus-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.1);
}

.focus-card.is-active,
.risk-student-row.is-active,
.progress-ranking-row.is-active {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.focus-card :deep(.el-button:hover) {
  background: linear-gradient(135deg, #2146a5 0%, #16a34a 120%);
  border-color: #2146a5;
}

.focus-card.risk-tone--high,
.focus-card.risk-tone--medium,
.focus-card.risk-tone--low {
  border-color: #c6d8ef;
}

.focus-card .risk-tag {
  min-height: 30px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.focus-section__guide-btn :deep(.el-button),
.focus-section__guide-btn {
  border-radius: 14px;
  padding: 10px 16px;
  background: linear-gradient(180deg, #f4f9ff 0%, #edf6ff 100%);
  border: 1.5px solid #c6d8ef;
  color: #2563eb;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.focus-section__guide-btn:hover {
  background: linear-gradient(180deg, #eaf3ff 0%, #e0efff 100%);
  border-color: #93c5fd;
  color: #2563eb;
}

.detail-layout {
  display: grid;
  gap: 24px;
  grid-template-columns: 1fr;
}

.analytics-card--stack {
  padding: 24px;
}

.analytics-card--subtle {
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.03);
}

.table-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.table-filter {
  padding: 7px 12px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f9ff 100%);
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.table-filter.is-active {
  background: linear-gradient(180deg, #eef6ff 0%, #e0efff 100%);
  border-color: #93c5fd;
  color: #2563eb;
}

.risk-student-list,
.progress-ranking-list {
  display: grid;
  gap: 16px;
}

.risk-student-row,
.progress-ranking-row {
  display: grid;
  gap: 16px;
  padding: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  border-radius: 18px;
  transition: background-color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.risk-student-row {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.risk-student-row:hover,
.progress-ranking-row:hover {
  background: #f8fafc;
  border-color: #dbeafe;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.risk-student-row__main {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.risk-student-row__identity,
.risk-student-row__problem,
.progress-ranking-row__identity,
.progress-ranking-row__metric {
  display: grid;
  gap: 4px;
}

.risk-student-row__identity strong,
.progress-ranking-row__identity strong {
  font-size: 18px;
  line-height: 1.3;
  color: #0f172a;
}

.risk-student-row__identity span,
.progress-ranking-row__identity span,
.risk-student-row__problem span {
  font-size: 13px;
  color: #64748b;
}

.risk-student-row__problem strong {
  font-size: 16px;
  line-height: 1.5;
  color: #0f172a;
}

.risk-student-row__aside {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.risk-student-row__aside :deep(.el-button) {
  min-width: 72px;
  height: 34px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1.5px solid #c6d8ef;
  color: #2563eb;
  background: linear-gradient(180deg, #f4f9ff 0%, #edf6ff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.risk-student-row__aside :deep(.el-button:hover) {
  background: linear-gradient(180deg, #eaf3ff 0%, #e0efff 100%);
  border-color: #93c5fd;
}

.progress-ranking-row {
  grid-template-columns: 40px minmax(0, 1fr) minmax(180px, 280px);
  align-items: center;
}

.progress-ranking-row__rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #2563eb;
  font-size: 14px;
  font-weight: 700;
}

.progress-ranking-row__metric {
  justify-items: end;
}

.progress-ranking-row__metric span {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.progress-ranking-row__track {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.progress-ranking-row__fill {
  height: 100%;
  border-radius: inherit;
  background: #3b82f6;
}

.collapsed-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.collapsed-state strong {
  color: #0f172a;
  font-size: 14px;
}

.collapsed-state span {
  color: #64748b;
  font-size: 13px;
}

.risk-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}

.risk-tag--high {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fecaca;
}

.risk-tag--medium {
  background: #fffbeb;
  color: #b45309;
  border-color: #fde68a;
}

.risk-tag--low {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
}

.empty-panel {
  min-height: 140px;
  display: grid;
  place-content: center;
  gap: 8px;
  text-align: center;
  border: 1.5px dashed #c6d8ef;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.empty-panel--compact {
  min-height: 120px;
}

.empty-panel strong {
  color: #0f172a;
  font-size: 18px;
}

.empty-panel p {
  margin: 0;
  color: #64748b;
}

@media (max-width: 1280px) {
  .summary-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .analysis-layout,
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .analysis-row {
    grid-template-columns: 1fr;
  }

  .focus-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .progress-ranking-row {
    grid-template-columns: 40px minmax(0, 1fr);
  }
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: 1fr;
  }

  .stage-bar {
    grid-template-columns: 1fr;
  }

  .focus-grid,
  .focus-card {
    grid-template-columns: 1fr;
  }

  .focus-section {
    padding: 24px;
  }

  .focus-section .section-title {
    align-items: flex-start;
  }

  .focus-section__title-copy h3 {
    font-size: 28px;
  }

  .focus-card__actions {
    justify-content: flex-start;
    padding: 0 18px 16px;
    border-left: 0;
  }

  .card-header {
    align-items: flex-start;
  }

  .analysis-overview__header {
    align-items: flex-start;
  }

  .risk-student-row,
  .progress-ranking-row {
    grid-template-columns: 1fr;
  }

  .risk-student-row__aside {
    justify-content: flex-start;
  }

  .progress-ranking-row__metric {
    justify-items: stretch;
  }

  .collapsed-state {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
