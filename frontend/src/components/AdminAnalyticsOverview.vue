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
const currentRiskPage = ref(1);
const riskPageSize = 5;

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

const weakKnowledgeList = computed<WeakKpRow[]>(() =>
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

const hasRiskStudents = computed(() => (data.value.risk_students ?? []).length > 0);

const pagedRiskStudents = computed(() => {
  const start = (currentRiskPage.value - 1) * riskPageSize;
  return filteredRiskStudents.value.slice(start, start + riskPageSize);
});

const progressRankingRows = computed(() =>
  [...data.value.progress_ranking].sort((a, b) => (b.dynamic_score || 0) - (a.dynamic_score || 0))
);

const progressRankingList = computed<StudentRow[]>(() =>
  progressRankingRows.value
    .filter((row) => !focusStudentIdSet.value.has(Number(row.user_id)))
    .map((row, index) => ({
      ...row,
      rank: index + 1,
      masteryPercent: Math.round((row.course_mastery || 0) * 100),
    }))
);

const suggestionText = computed(() => {
  const high = riskOverview.value.find((item) => item.key === "high")?.count ?? 0;
  const medium = riskOverview.value.find((item) => item.key === "medium")?.count ?? 0;
  if (high > 0) return `建议优先关注 ${high} 名高风险学生，并结合薄弱知识点安排补救任务。`;
  if (medium > 0) return `建议跟进 ${medium} 名中风险学生的阶段表现，及时调整练习和反馈节奏。`;
  return "当前班级风险整体可控，可继续观察学习进展和知识薄弱点变化。";
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

watch(
  () => activeRiskFilter.value,
  () => {
    currentRiskPage.value = 1;
  }
);

watch(
  () => filteredRiskStudents.value.length,
  (length) => {
    const maxPage = Math.max(1, Math.ceil(length / riskPageSize));
    if (currentRiskPage.value > maxPage) currentRiskPage.value = maxPage;
  },
  { immediate: true }
);
</script>

<template>
  <div class="analytics-shell" v-loading="loading">
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
            v-for="row in pagedRiskStudents"
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
        <div v-if="filteredRiskStudents.length > riskPageSize" class="risk-pagination">
          <el-pagination
            v-model:current-page="currentRiskPage"
            :page-size="riskPageSize"
            :total="filteredRiskStudents.length"
            layout="prev, pager, next"
            background
          />
        </div>
        <div v-else-if="!hasRiskStudents" class="empty-panel empty-panel--compact">
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
  --ana-ink: #15213d;
  --ana-soft: #4d5c7f;
  --ana-border: rgba(31, 41, 55, 0.12);
  --ana-blue: #416ff3;
  --ana-cyan: #7fb9d9;
  --ana-violet: #7f7dd8;
  --ana-peach: #e4b46a;
  --ana-rose: #d99ca5;
  --ana-lime: #a8c97a;
  --ana-mint: #6fb596;
  --ana-btn-radius: 14px;
  --ana-btn-primary-bg: linear-gradient(135deg, #2f59c9 0%, #4c79f0 58%, #6aa6f4 100%);
  --ana-btn-primary-bg-hover: linear-gradient(135deg, #274eb3 0%, #426fe2 58%, #5f9aec 100%);
  --ana-btn-primary-border: rgba(47, 89, 201, 0.28);
  --ana-btn-primary-shadow: 0 10px 22px rgba(65, 111, 243, 0.18);
  --ana-btn-secondary-bg: linear-gradient(180deg, rgba(255, 251, 245, 0.98) 0%, rgba(255, 243, 226, 0.94) 100%);
  --ana-btn-secondary-bg-hover: linear-gradient(180deg, rgba(255, 247, 238, 0.98) 0%, rgba(247, 250, 243, 0.96) 100%);
  --ana-btn-secondary-border: rgba(228, 180, 106, 0.24);
  --ana-btn-secondary-text: #7b5a33;
  position: relative;
  display: grid;
  gap: 26px;
  padding: 8px 0 18px;
  overflow: hidden;
}

.analytics-shell::before,
.analytics-shell::after {
  content: "";
  position: absolute;
  inset: auto;
  width: 260px;
  height: 260px;
  border-radius: 999px;
  filter: blur(60px);
  opacity: 0.18;
  pointer-events: none;
}

.analytics-shell::before {
  top: 28px;
  right: -80px;
  background: rgba(228, 180, 106, 0.16);
}

.analytics-shell::after {
  bottom: 180px;
  left: -90px;
  background: rgba(65, 111, 243, 0.08);
}

.analytics-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(260px, 0.9fr);
  gap: 18px;
  padding: 26px 28px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 34px;
  background:
    radial-gradient(circle at 12% 18%, rgba(191, 219, 254, 0.18), transparent 22%),
    radial-gradient(circle at 88% 14%, rgba(187, 247, 208, 0.1), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 18px 38px rgba(34, 58, 118, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.analytics-hero::after {
  content: "";
  position: absolute;
  inset: 12px;
  border-radius: 26px;
  border: 1px dashed rgba(65, 111, 243, 0.1);
  pointer-events: none;
}

.analytics-hero__copy {
  display: grid;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.analytics-hero__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 7px 13px;
  border-radius: 999px;
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  color: #2563eb;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  border: 1px solid rgba(139, 63, 88, 0.12);
  box-shadow: 0 8px 16px rgba(217, 156, 165, 0.1);
}

.analytics-hero__copy h2 {
  margin: 0;
  font-size: clamp(26px, 3.2vw, 38px);
  line-height: 1.08;
  letter-spacing: -0.03em;
  color: var(--ana-ink);
  text-shadow: 0 8px 18px rgba(65, 111, 243, 0.08);
}

.analytics-hero__copy p {
  margin: 0;
  max-width: 60ch;
  color: var(--ana-soft);
  line-height: 1.7;
}

.analytics-hero__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-content: start;
  justify-content: flex-end;
  position: relative;
  z-index: 1;
}

.analytics-chip {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(65, 111, 243, 0.12);
  background: rgba(255, 255, 255, 0.9);
  color: #34518a;
  font-size: 12px;
  font-weight: 700;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 16px rgba(42, 59, 108, 0.05);
}

.analytics-chip--warm {
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.94) 0%, rgba(240, 253, 244, 0.92) 100%);
  color: #334155;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.08), transparent 24%),
    radial-gradient(circle at bottom right, rgba(187, 247, 208, 0.08), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 14px 30px rgba(74, 49, 122, 0.05);
}

.summary-card,
.analytics-card,
.focus-section {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(248, 251, 255, 0.98) 100%);
  box-shadow:
    0 12px 24px rgba(24, 34, 64, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
}

.summary-card {
  grid-column: span 2;
  padding: 24px 22px;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease,
    filter 0.18s ease;
  position: relative;
  overflow: hidden;
}

.summary-card:nth-child(1) {
  grid-column: span 3;
}

.summary-card:nth-child(4) {
  grid-column: span 3;
}

.summary-card::before {
  content: "";
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 6px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.22), currentColor);
  opacity: 0.18;
}

.summary-card::after {
  content: "";
  position: absolute;
  width: 110px;
  height: 110px;
  right: -22px;
  top: -22px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
}

.summary-card:hover,
.analytics-card:hover,
.focus-card:hover,
.knowledge-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 28px rgba(33, 63, 118, 0.09);
}

.summary-card:hover {
  filter: saturate(1.02);
}

.summary-card--blue {
  background:
    radial-gradient(circle at top right, rgba(135, 182, 255, 0.14), transparent 28%),
    linear-gradient(180deg, #fffaf5 0%, #f9fbff 100%);
  color: #315ccc;
}

.summary-card--red {
  background:
    radial-gradient(circle at top right, rgba(217, 156, 165, 0.2), transparent 28%),
    linear-gradient(180deg, #fff9f6 0%, #fdf1f3 100%);
  color: #bd6573;
}

.summary-card--green {
  background:
    radial-gradient(circle at top right, rgba(168, 201, 122, 0.2), transparent 28%),
    linear-gradient(180deg, #fffbf4 0%, #f2f8ec 100%);
  color: #5f8750;
}

.summary-card:nth-child(2) {
  background:
    radial-gradient(circle at top right, rgba(127, 125, 216, 0.16), transparent 28%),
    linear-gradient(180deg, #fffaf5 0%, #f3eff8 100%);
  color: #6e6cc2;
}

.summary-card:nth-child(4) {
  background:
    radial-gradient(circle at top right, rgba(228, 180, 106, 0.18), transparent 28%),
    linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
  color: #476899;
}

.summary-card:nth-child(6) {
  background:
    radial-gradient(circle at top right, rgba(111, 181, 150, 0.16), transparent 28%),
    linear-gradient(180deg, #fffbf5 0%, #edf7f1 100%);
  color: #4f866d;
}

.summary-card__label,
.card-header__eyebrow,
.section-title__eyebrow {
  font-size: 12px;
  font-weight: 800;
  color: #8b6482;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-card__value {
  display: block;
  margin-top: 10px;
  font-size: 32px;
  line-height: 1;
  font-weight: 800;
  color: var(--ana-ink);
  font-family: inherit;
}

.summary-card__hint {
  display: block;
  margin-top: 12px;
  font-size: 13px;
  color: var(--ana-soft);
}

.summary-card--green .summary-card__value {
  color: #547b49;
}

.summary-card--red .summary-card__value {
  color: #b55b68;
}

.analysis-layout {
  display: grid;
  gap: 18px;
}

.analysis-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
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
  gap: 18px;
}

.analysis-overview__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-inline: 4px;
}

.analysis-overview__header h3 {
  margin: 6px 0 0;
  font-size: 24px;
  line-height: 1.2;
  color: var(--ana-ink);
  font-family: inherit;
}

.analysis-overview__header p,
.card-header__desc {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--ana-soft);
}

.analytics-card,
.focus-section {
  padding: 24px;
}

.analytics-card--compact {
  padding: 20px;
}

.analytics-card--collapsed {
  padding: 16px 20px;
}

.analytics-card--stack {
  background:
    radial-gradient(circle at top right, rgba(127, 185, 217, 0.06), transparent 20%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.analysis-row:nth-child(1) .analytics-card:first-child {
  background:
    radial-gradient(circle at top right, rgba(127, 125, 216, 0.1), transparent 22%),
    linear-gradient(180deg, #fff9f4 0%, #f7f3fb 100%);
}

.analysis-row:nth-child(1) .analytics-card:last-child {
  background:
    radial-gradient(circle at top right, rgba(228, 180, 106, 0.1), transparent 22%),
    linear-gradient(180deg, #fff8f0 0%, #fbf7f0 100%);
}

.analysis-row:nth-child(2) .analytics-card:first-child {
  background:
    radial-gradient(circle at top right, rgba(217, 156, 165, 0.1), transparent 22%),
    linear-gradient(180deg, #fff8f3 0%, #faf4f6 100%);
}

.analysis-row:nth-child(2) .analytics-card:last-child {
  background:
    radial-gradient(circle at top right, rgba(111, 181, 150, 0.1), transparent 22%),
    linear-gradient(180deg, #f8fbff 0%, #eef8ff 100%);
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
  font-size: 24px;
  line-height: 1.1;
  color: var(--ana-ink);
  font-family: inherit;
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
  border: 1.5px solid rgba(31, 41, 55, 0.1);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 251, 246, 0.94) 0%, rgba(255, 255, 252, 0.94) 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.persona-row,
.stage-chart__row,
.risk-overview__item {
  padding: 14px 15px;
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
  color: var(--ana-ink);
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
  color: var(--ana-soft);
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
  background: rgba(116, 133, 170, 0.12);
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
  background: linear-gradient(90deg, var(--ana-blue) 0%, var(--ana-cyan) 100%);
}

.practice-meter__fill--secondary {
  background: linear-gradient(90deg, var(--ana-lime) 0%, var(--ana-mint) 100%);
}

.knowledge-item {
  width: 100%;
  padding: 14px 15px;
  text-align: left;
}

.knowledge-item__fill {
  background: linear-gradient(90deg, var(--ana-peach) 0%, #ffd785 100%);
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
  background: linear-gradient(90deg, #ef697a 0%, #ffab92 100%);
}

.risk-overview__item--medium .risk-overview__fill {
  background: linear-gradient(90deg, #ffb84c 0%, #ffd27a 100%);
}

.risk-overview__item--low .risk-overview__fill {
  background: linear-gradient(90deg, #7ed957 0%, #4bc79b 100%);
}

.advice-panel {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 244, 228, 0.96) 0%, rgba(255, 251, 243, 0.94) 100%);
  border: 1.5px solid rgba(255, 186, 107, 0.24);
  color: #6d5e51;
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
  background: linear-gradient(135deg, rgba(255, 238, 186, 0.9) 0%, rgba(255, 255, 255, 0.82) 100%);
  color: #91632b;
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
  color: var(--ana-ink);
}

.stage-bar__fill--score {
  background: linear-gradient(90deg, var(--ana-violet) 0%, var(--ana-blue) 100%);
}

.stage-bar__fill--mastery {
  background: linear-gradient(90deg, var(--ana-lime) 0%, var(--ana-mint) 100%);
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
  background:
    radial-gradient(circle at top right, rgba(228, 180, 106, 0.1), transparent 18%),
    radial-gradient(circle at bottom left, rgba(217, 156, 165, 0.08), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  background: linear-gradient(180deg, rgba(255, 250, 245, 0.96) 0%, rgba(255, 255, 251, 0.96) 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.1);
  border-radius: 18px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.focus-card__accent {
  align-self: stretch;
  width: 6px;
  background: #e5e7eb;
}

.focus-card.risk-tone--high .focus-card__accent {
  background: linear-gradient(180deg, #ef697a 0%, #ffab92 100%);
}

.focus-card.risk-tone--medium .focus-card__accent {
  background: linear-gradient(180deg, #ffb84c 0%, #ffd27a 100%);
}

.focus-card.risk-tone--low .focus-card__accent {
  background: linear-gradient(180deg, #7ed957 0%, #4bc79b 100%);
}

.focus-card__main {
  display: grid;
  gap: 8px;
  min-width: 0;
  padding: 18px 16px 18px 20px;
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
  color: var(--ana-ink);
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
  color: var(--ana-soft);
}

.focus-card__issue {
  display: grid;
  gap: 4px;
}

.focus-card__issue span {
  font-size: 12px;
  color: #9a7286;
  font-weight: 600;
}

.focus-card__issue strong {
  color: var(--ana-ink);
  font-size: 17px;
  line-height: 1.4;
  font-weight: 700;
}

.focus-card__actions {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 16px 16px 16px 8px;
  border-left: 1.5px solid rgba(31, 41, 55, 0.08);
}

.focus-section__dot {
  width: 10px;
  height: 10px;
  margin-top: 6px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--ana-rose) 0%, var(--ana-peach) 100%);
  box-shadow: 0 0 0 6px rgba(217, 156, 165, 0.08);
}

.focus-section__title {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.focus-section__title-copy .section-title__eyebrow {
  color: #d75f70;
  font-size: 12px;
  font-weight: 800;
}

.focus-section__title-copy h3 {
  margin: 6px 0 0;
  font-size: 30px;
  line-height: 1.15;
  color: var(--ana-ink);
}

.focus-section__title p {
  margin: 8px 0 0;
  color: var(--ana-soft);
  font-size: 14px;
}

.focus-section__guide {
  display: grid;
  gap: 6px;
  padding: 18px 20px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 243, 229, 0.96) 0%, rgba(255, 251, 245, 0.94) 100%);
  border: 1.5px solid rgba(255, 186, 107, 0.22);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.focus-section__guide span {
  color: #9b6f31;
  font-size: 14px;
  font-weight: 600;
}

.focus-section__guide p {
  margin: 0;
  color: var(--ana-soft);
  font-size: 14px;
  line-height: 1.6;
}

.focus-card :deep(.el-button) {
  width: 96px;
  height: 36px;
  border-radius: var(--ana-btn-radius);
  padding: 0 16px;
  background: var(--ana-btn-primary-bg);
  border: 1.5px solid var(--ana-btn-primary-border);
  color: #ffffff;
  box-shadow: var(--ana-btn-primary-shadow);
  margin-top: 2px;
  font-weight: 700;
}

.focus-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.1);
}

.focus-card.is-active,
.risk-student-row.is-active,
.progress-ranking-row.is-active {
  border-color: rgba(65, 111, 243, 0.28);
  box-shadow: 0 0 0 4px rgba(65, 111, 243, 0.1);
}

.focus-card :deep(.el-button:hover) {
  background: var(--ana-btn-primary-bg-hover);
  border-color: rgba(47, 89, 201, 0.38);
}

.focus-card.risk-tone--high,
.focus-card.risk-tone--medium,
.focus-card.risk-tone--low {
  border-color: rgba(31, 41, 55, 0.1);
}

.focus-card .risk-tag {
  min-height: 30px;
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.focus-section__guide-btn :deep(.el-button),
.focus-section__guide-btn {
  border-radius: var(--ana-btn-radius);
  padding: 10px 16px;
  min-height: 40px;
  background: var(--ana-btn-secondary-bg);
  border: 1.5px solid var(--ana-btn-secondary-border);
  color: var(--ana-btn-secondary-text);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 6px 14px rgba(228, 180, 106, 0.08);
  font-weight: 700;
}

.focus-section__guide-btn:hover {
  background: var(--ana-btn-secondary-bg-hover);
  border-color: rgba(168, 201, 122, 0.28);
  color: #5f6a3d;
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
  min-height: 34px;
  padding: 7px 13px;
  border-radius: 999px;
  border: 1.5px solid rgba(228, 180, 106, 0.2);
  background: var(--ana-btn-secondary-bg);
  color: #6a6f86;
  font-size: 12px;
  font-weight: 700;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 4px 10px rgba(228, 180, 106, 0.06);
  transition: transform 0.18s ease, border-color 0.18s ease, color 0.18s ease, background 0.18s ease;
}

.table-filter.is-active {
  background: linear-gradient(180deg, rgba(250, 244, 232, 0.98) 0%, rgba(238, 245, 255, 0.96) 100%);
  border-color: rgba(65, 111, 243, 0.22);
  color: #284fbe;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 6px 14px rgba(65, 111, 243, 0.1);
}

.table-filter:hover {
  transform: translateY(-1px);
}

.risk-student-list,
.progress-ranking-list {
  display: grid;
  gap: 16px;
}

.risk-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.risk-pagination :deep(.el-pagination) {
  --el-pagination-button-bg-color: rgba(255, 250, 245, 0.94);
  --el-pagination-hover-color: #284fbe;
  --el-pagination-text-color: var(--ana-soft);
  --el-pagination-button-color: var(--ana-soft);
  --el-pagination-button-disabled-bg-color: rgba(248, 250, 252, 0.88);
}

.risk-pagination :deep(.btn-prev),
.risk-pagination :deep(.btn-next),
.risk-pagination :deep(.number),
.risk-pagination :deep(.more) {
  border-radius: 12px;
}

.risk-student-row,
.progress-ranking-row {
  display: grid;
  gap: 16px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(255, 250, 245, 0.94) 0%, rgba(255, 255, 252, 0.94) 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.1);
  border-radius: 18px;
  transition: background-color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.risk-student-row {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.risk-student-row:hover,
.progress-ranking-row:hover {
  background: linear-gradient(180deg, rgba(255, 252, 248, 0.98) 0%, rgba(255, 255, 253, 0.98) 100%);
  border-color: rgba(65, 111, 243, 0.18);
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
  color: var(--ana-ink);
}

.risk-student-row__identity span,
.progress-ranking-row__identity span,
.risk-student-row__problem span {
  font-size: 13px;
  color: var(--ana-soft);
}

.risk-student-row__problem strong {
  font-size: 16px;
  line-height: 1.5;
  color: var(--ana-ink);
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
  border-radius: var(--ana-btn-radius);
  border: 1.5px solid var(--ana-btn-secondary-border);
  color: var(--ana-btn-secondary-text);
  background: var(--ana-btn-secondary-bg);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 6px 14px rgba(228, 180, 106, 0.06);
  font-weight: 700;
}

.risk-student-row__aside :deep(.el-button:hover) {
  background: var(--ana-btn-secondary-bg-hover);
  border-color: rgba(168, 201, 122, 0.24);
  color: #5f6a3d;
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
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 238, 186, 0.96) 100%);
  border: 1px solid rgba(255, 186, 107, 0.24);
  color: #8a6a34;
  font-size: 14px;
  font-weight: 700;
}

.progress-ranking-row__metric {
  justify-items: end;
}

.progress-ranking-row__metric span {
  font-size: 14px;
  font-weight: 700;
  color: var(--ana-ink);
}

.progress-ranking-row__track {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: rgba(116, 133, 170, 0.12);
  overflow: hidden;
}

.progress-ranking-row__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--ana-violet) 0%, var(--ana-blue) 100%);
}

.collapsed-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.collapsed-state strong {
  color: var(--ana-ink);
  font-size: 14px;
}

.collapsed-state span {
  color: var(--ana-soft);
  font-size: 13px;
}

.risk-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  letter-spacing: 0.01em;
}

.risk-tag--high {
  background: linear-gradient(135deg, rgba(255, 240, 242, 0.96) 0%, rgba(255, 227, 227, 0.96) 100%);
  color: #b6544a;
  border-color: rgba(214, 95, 112, 0.24);
}

.risk-tag--medium {
  background: linear-gradient(135deg, rgba(255, 248, 231, 0.96) 0%, rgba(255, 237, 204, 0.96) 100%);
  color: #b27a25;
  border-color: rgba(205, 139, 47, 0.24);
}

.risk-tag--low {
  background: linear-gradient(135deg, rgba(241, 255, 239, 0.96) 0%, rgba(227, 255, 236, 0.96) 100%);
  color: #5c8b32;
  border-color: rgba(76, 141, 46, 0.24);
}

.empty-panel {
  min-height: 140px;
  display: grid;
  place-content: center;
  gap: 8px;
  text-align: center;
  border: 1.5px dashed rgba(65, 111, 243, 0.18);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 250, 244, 0.96) 0%, rgba(255, 253, 248, 0.94) 100%);
}

.empty-panel--compact {
  min-height: 120px;
}

.empty-panel strong {
  color: var(--ana-ink);
  font-size: 18px;
}

.empty-panel p {
  margin: 0;
  color: var(--ana-soft);
}

@media (prefers-reduced-motion: reduce) {
  .summary-card,
  .analytics-card,
  .focus-card,
  .knowledge-item,
  .table-filter,
  .focus-card :deep(.el-button) {
    transition: none !important;
  }
}

@media (max-width: 1280px) {
  .analytics-hero {
    grid-template-columns: 1fr;
  }

  .summary-cards {
    grid-template-columns: repeat(6, minmax(0, 1fr));
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

  .summary-card,
  .summary-card:nth-child(1),
  .summary-card:nth-child(4) {
    grid-column: span 1;
  }

  .stage-bar {
    grid-template-columns: 1fr;
  }

  .focus-grid,
  .focus-card {
    grid-template-columns: 1fr;
  }

  .focus-section {
    padding: 22px;
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
