<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";
import PortraitRadarChart from "./PortraitRadarChart.vue";
import LearnerReportHeader from "./LearnerReportHeader.vue";
import LearnerReportHero from "./LearnerReportHero.vue";

const QUESTIONNAIRE_SCORE_OPTIONS = [
  { label: "很少", value: 0.2 },
  { label: "偶尔", value: 0.4 },
  { label: "一般", value: 0.6 },
  { label: "经常", value: 0.8 },
  { label: "总是", value: 1.0 },
];

function questionnaireOptionLabel(score: number | null | undefined) {
  const option = QUESTIONNAIRE_SCORE_OPTIONS.find((item) => item.value === score);
  return option?.label ?? "未选择";
}

type TrendPoint = {
  updated_at: string;
  dynamic_score: number;
  course_mastery: number;
  persona_type: string;
  stage_title?: string | null;
  trend_label?: string | null;
};

type StagePoint = {
  course_id?: number | null;
  stage_id: number;
  stage_title: string;
  stage_order: number;
  engagement: number;
  achievement: number;
  habit: number;
  characteristic: number;
  dynamic_score: number;
  course_mastery: number;
  trend_label: string;
  risk_level: string;
  reason_summary: string;
  portrait_dimensions?: Array<{ dimension_title: string; score: number | null; available: boolean }>;
  portrait_indicators?: Array<{
    title: string;
    score: number | null;
    available: boolean;
    source_type: string;
    weight: number;
    score_source?: string;
    formula_text?: string;
    source_detail?: string;
    evidence_metrics?: Array<{ metric_label: string; metric_percent: number; weight: number }>;
  }>;
};

type DimensionConfig = {
  key: string;
  label: string;
  enabled: boolean;
  weight: number;
};

type TeacherFeedback = {
  stage_id: number;
  feedback_tag: string;
  comment: string;
  updated_by: string;
  updated_at?: string | null;
};

type ProfileData = {
  course_id?: number | null;
  persona_type: string;
  persona_label: string;
  engagement: number;
  achievement: number;
  habit?: number;
  characteristic?: number;
  efficiency: number;
  risk: number;
  course_mastery: number;
  dynamic_score: number;
  stability: number;
  risk_level: string;
  override_source: string;
  reason_summary: string;
  trend: TrendPoint[];
  current_stage?: StagePoint | null;
  stage_history?: StagePoint[];
  dimension_config?: DimensionConfig[];
  teacher_feedback?: TeacherFeedback | null;
  portrait_dimensions?: Array<{ dimension_title: string; score: number | null; available: boolean }>;
  portrait_indicators?: Array<{
    title: string;
    score: number | null;
    available: boolean;
    source_type: string;
    weight: number;
    score_source?: string;
    formula_text?: string;
    source_detail?: string;
    evidence_metrics?: Array<{ metric_label: string; metric_percent: number; weight: number }>;
  }>;
  final_portrait_dimensions?: Array<{ dimension_title: string; score: number | null; available: boolean }>;
  final_portrait_indicators?: Array<{
    title: string;
    score: number | null;
    available: boolean;
    source_type: string;
    weight: number;
    score_source?: string;
    formula_text?: string;
    source_detail?: string;
  }>;
  term_summary?: {
    stage_count?: number;
    progress_stages?: number;
    steady_stages?: number;
    regress_stages?: number;
    avg_dynamic_score?: number;
    latest_dynamic_score?: number;
    final_score_reference?: number;
    final_reason_summary?: string;
  };
  kp_dimension_summary?: {
    summary?: {
      knowledge_total?: number;
      knowledge_achieved?: number;
      ability_target_total?: number;
      ability_achieved?: number;
      literacy_target_total?: number;
      literacy_achieved?: number;
      top_abilities?: Array<{ label: string; achieved_count: number; target_count: number }>;
      top_literacies?: Array<{ label: string; achieved_count: number; target_count: number }>;
    };
  };
  ability_practice_stats?: {
    high_order_note?: string;
    overall?: { attempts?: number; correct?: number; accuracy?: number };
    high_order_overall?: { attempts?: number; correct?: number; accuracy?: number };
    by_ability_tag?: Array<{
      label: string;
      high_order_attempts: number;
      high_order_correct: number;
      high_order_accuracy: number;
      all_attempts: number;
      all_correct: number;
      all_accuracy: number;
    }>;
    by_cognitive_level?: Array<{
      level: string;
      attempts: number;
      correct: number;
      accuracy: number;
      is_high_order: boolean;
    }>;
  };
  latest_recommendation?: {
    target_kp_title?: string;
    source_kp_title?: string;
    reason_summary?: string;
    created_at?: string;
  };
  evaluation_explain?: {
    summary?: string;
    current_stage_title?: string;
    current_trend_label?: string;
    explain_cards?: Array<{ key: string; label: string; score: number; score_label: string; explain: string }>;
    next_actions?: string[];
    teacher_feedback?: string;
    term_reason_summary?: string;
  };
  graph_coverage?: {
    total_nodes?: number;
    completed_nodes?: number;
    mastered_nodes?: number;
    learning_coverage?: number;
    mastery_coverage?: number;
    graph_score?: number;
    formula?: string;
    dynamic_weight?: number;
  };
};

const props = defineProps<{ subject: string; grade: string; reloadKey?: number }>();

const loading = ref(false);
const profile = ref<ProfileData | null>(null);
const questionnaireLoading = ref(false);
const savingQuestionnaire = ref(false);
const reportTab = ref("summary");
const behaviorSubTab = ref("overview");
const questionnaireIndicators = ref<Array<{ dimension_id: number; dimension_title: string; indicator_id: number; indicator_title: string; indicator_code: string; weight: number; score: number | null; note: string }>>([]);

function sourceTypeLabel(sourceType: string) {
  if (sourceType === "auto") return "系统自动";
  if (sourceType === "imported") return "阶段导入";
  if (sourceType === "teacher") return "老师填写";
  if (sourceType === "questionnaire") return "学生补充";
  return sourceType;
}

function scoreSourceLabel(scoreSource?: string) {
  if (scoreSource === "teacher_input") return "老师评分";
  if (scoreSource === "questionnaire_input") return "问卷补充";
  if (scoreSource === "stage_inference") return "阶段映射";
  return "待补充";
}

const currentStage = computed(() => profile.value?.current_stage ?? null);
const stageHistory = computed(() => profile.value?.stage_history ?? []);
const dimensionConfig = computed(() => (profile.value?.dimension_config ?? []).filter((item) => item.enabled));
const hasStageModel = computed(() => stageHistory.value.length > 0 || Boolean(currentStage.value));
const portraitDimensions = computed(() => currentStage.value?.portrait_dimensions ?? profile.value?.portrait_dimensions ?? []);
const stageResultRows = computed(() => {
  if (portraitDimensions.value.length) return portraitDimensions.value;
  if (!currentStage.value) return [];
  return [
    { dimension_title: "学习投入", score: currentStage.value.engagement ?? 0, available: true },
    { dimension_title: "学习成效", score: currentStage.value.achievement ?? 0, available: true },
    { dimension_title: "学习习惯", score: currentStage.value.habit ?? 0, available: true },
    { dimension_title: "学习特征", score: currentStage.value.characteristic ?? 0, available: true },
  ];
});
const finalPortraitDimensions = computed(() => profile.value?.final_portrait_dimensions ?? []);
const termSummary = computed(() => profile.value?.term_summary ?? {});
const portraitIndicatorRows = computed(() => currentStage.value?.portrait_indicators ?? profile.value?.portrait_indicators ?? []);
const portraitIndicators = computed(() => portraitIndicatorRows.value.filter((item) => item.available));
const hasQuestionnaireItems = computed(() => questionnaireIndicators.value.length > 0);
const kpDimensionSummary = computed(() => profile.value?.kp_dimension_summary?.summary ?? {});
const topAbilityRows = computed(() => kpDimensionSummary.value.top_abilities ?? []);
const topLiteracyRows = computed(() => kpDimensionSummary.value.top_literacies ?? []);
const abilityPracticeStats = computed(() => profile.value?.ability_practice_stats ?? null);
const learningBehaviorOverview = computed(() => (profile.value as any)?.learning_behavior_overview ?? null);
const behaviorTimeline = computed(() => ((profile.value as any)?.behavior_timeline ?? []) as Array<any>);
const recentPracticeRecords = computed(() => ((profile.value as any)?.recent_practice_records ?? []) as Array<any>);
const recentQuizRecords = computed(() => ((profile.value as any)?.recent_quiz_records ?? []) as Array<any>);
const recentVideoRecords = computed(() => ((profile.value as any)?.recent_video_records ?? []) as Array<any>);
const evaluationExplain = computed(() => profile.value?.evaluation_explain ?? null);
const latestRecommendation = computed(() => profile.value?.latest_recommendation ?? null);
const graphCoverage = computed(() => profile.value?.graph_coverage ?? null);

function bloomLevelLabel(level: string) {
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
const mentorDimensionOrder = [
  "潜能与特质倾向",
  "情感与社会性发展",
  "知识与认知状态",
  "学习行为与过程",
  "个体基础特征",
];
const indicatorDimensionMap: Record<string, string> = {
  创造性思维倾向: "潜能与特质倾向",
  跨情境迁移能力: "潜能与特质倾向",
  存在思考与价值判断: "潜能与特质倾向",
  协作能力与社交网络: "情感与社会性发展",
  学习动机与态度: "情感与社会性发展",
  自我调节与元认知: "情感与社会性发展",
  跨学科知识关联能力: "知识与认知状态",
  学科能力层级与认知路径: "知识与认知状态",
  语言类知识掌握度: "知识与认知状态",
  逻辑类知识掌握度: "知识与认知状态",
  资源偏好: "学习行为与过程",
  辅助学习策略: "学习行为与过程",
  "交互偏好：文本/讨论型": "学习行为与过程",
  "交互偏好：实践/体验型": "学习行为与过程",
  人口学背景与学业经历: "个体基础特征",
  探究兴趣类型: "个体基础特征",
  智能优势倾向标签: "个体基础特征",
};
const dimensionScoreMap = computed(() => {
  const map = new Map<string, number | null>();
  for (const item of portraitDimensions.value) map.set(item.dimension_title, item.score);
  return map;
});
type MentorIndicator = NonNullable<StagePoint["portrait_indicators"]>[number];

const mentorDimensionGroups = computed(() => {
  const bucket = new Map<string, MentorIndicator[]>();
  for (const item of portraitIndicatorRows.value) {
    const dim = indicatorDimensionMap[item.title] || "未归类";
    const arr = bucket.get(dim) ?? [];
    arr.push(item);
    bucket.set(dim, arr);
  }

  const rows = mentorDimensionOrder.map((title) => {
    const indicators = bucket.get(title) ?? [];
    const scored = indicators.filter((item) => item.available && item.score != null);
    const completion = indicators.length ? Math.round((scored.length / indicators.length) * 100) : 0;
    return {
      title,
      score: dimensionScoreMap.value.get(title) ?? null,
      indicators,
      completion,
    };
  });

  for (const [title, indicators] of bucket.entries()) {
    if (mentorDimensionOrder.includes(title)) continue;
    const scored = indicators.filter((item) => item.available && item.score != null);
    rows.push({
      title,
      score: dimensionScoreMap.value.get(title) ?? null,
      indicators,
      completion: indicators.length ? Math.round((scored.length / indicators.length) * 100) : 0,
    });
  }
  return rows;
});

const dimensions = computed(() => {
  const current = profile.value;
  if (!current) return [];
  if (currentStage.value) {
    return [
      { label: "学习投入", value: currentStage.value.engagement ?? 0, color: "#2f8cff" },
      { label: "学习成效", value: currentStage.value.achievement ?? 0, color: "#2cb67d" },
      { label: "学习习惯", value: currentStage.value.habit ?? 0, color: "#ff9b42" },
      { label: "学习特征", value: currentStage.value.characteristic ?? 0, color: "#2f8cff" },
    ];
  }
  return [
    { label: "参与度 E", value: current.engagement ?? 0, color: "#2f8cff" },
    { label: "成效 A", value: current.achievement ?? 0, color: "#2cb67d" },
    { label: "效率 F", value: current.efficiency ?? 0, color: "#ff9b42" },
    { label: "风险 R", value: current.risk ?? 0, color: "#ff9b42" },
  ];
});

const timelineCards = computed(() => {
  if (stageHistory.value.length) return stageHistory.value;
  return ([] as ProfileData["trend"]).map((item, index) => ({
    stage_id: index + 1,
    stage_title: item.stage_title || `第 ${index + 1} 次评价`,
    stage_order: index + 1,
    engagement: 0,
    achievement: 0,
    habit: 0,
    characteristic: 0,
    dynamic_score: item.dynamic_score,
    course_mastery: item.course_mastery,
    trend_label: item.trend_label || "持平",
    risk_level: "预警",
    reason_summary: "",
  }));
});

const suggestions = computed(() => {
  const current = profile.value;
  if (!current) return [];
  const stageHint = currentStage.value?.trend_label;
  const base = [] as string[];
  if (current.persona_type === "smart_capable") {
    base.push("优先推进下一阶段知识点，减少重复基础练习。", "把时间放在综合题和迁移题上。", "保留阶段复盘，避免高分低稳。");
  } else if (current.persona_type === "diligent") {
    base.push("继续按阶段顺序推进，每完成一个阶段就做一次小结。", "把学习资源和练习穿插进行，避免只看不练。", "阶段结束前优先完成老师布置的关键任务。");
  } else if (current.persona_type === "struggling_persistent") {
    base.push("优先补前置知识点，再进入当前阶段任务。", "短资源和低阶练习优先，先稳住正确率。", "错题和未完成任务要在下一阶段前清掉。");
  } else if (current.persona_type === "procrastinating_risk") {
    base.push("先完成最短任务链，别同时开太多内容。", "把阶段目标拆成每天一小步。", "优先完成老师明确要求提交的任务。");
  } else {
    base.push("保持当前节奏，优先处理薄弱知识点。", "学习资源和练习同步推进。", "每个阶段结束时做一次总结回看。");
  }
  if (stageHint === "进步") base.unshift("当前阶段处于上升趋势，下一阶段保持同样节奏即可。");
  if (stageHint === "退步") base.unshift("当前阶段较上一阶段有回落，建议先回补前置知识点和未完成任务。");
  if (current.teacher_feedback?.comment) base.unshift(`教师建议：${current.teacher_feedback.comment}`);
  return base.slice(0, 4);
});

async function loadQuestionnaireIndicators() {
  const courseId = currentStage.value?.course_id ?? profile.value?.course_id ?? null;
  if (!courseId) {
    questionnaireIndicators.value = [];
    return;
  }
  questionnaireLoading.value = true;
  try {
    const res = await api.get(`/portrait/questionnaire-input?course_id=${courseId}`);
    questionnaireIndicators.value = res.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载问卷型指标失败");
  } finally {
    questionnaireLoading.value = false;
  }
}

async function saveQuestionnaireIndicators() {
  const courseId = currentStage.value?.course_id ?? profile.value?.course_id ?? null;
  if (!courseId) {
    ElMessage.warning("当前课程信息缺失");
    return;
  }
  savingQuestionnaire.value = true;
  try {
    await api.put(`/portrait/questionnaire-input?course_id=${courseId}`, {
      inputs: questionnaireIndicators.value.map((item) => ({
        indicator_id: item.indicator_id,
        score: item.score,
        note: item.note,
      })),
    });
    ElMessage.success("问卷/标签型指标已保存");
    await load();
    await loadQuestionnaireIndicators();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存问卷型指标失败");
  } finally {
    savingQuestionnaire.value = false;
  }
}

async function load() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const res = await api.get(
      `/eval/profile?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    profile.value = res.data;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载学习报告失败");
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.subject, props.grade, props.reloadKey ?? 0],
  () => load(),
  { immediate: true }
);

watch(
  () => [profile.value?.course_id, currentStage.value?.course_id],
  () => {
    loadQuestionnaireIndicators();
  }
);
</script>

<template>
  <el-card class="panel-card report-shell" shadow="never" v-loading="loading">
    <template #header>
      <LearnerReportHeader :loading="loading" @refresh="load" />
    </template>

    <div v-if="profile" class="report-grid">
      <LearnerReportHero class="report-grid__hero" :profile="profile" :current-stage="currentStage" :has-stage-model="hasStageModel" />

      <section v-if="evaluationExplain" class="config-board report-grid__hero">
        <div class="board-title">评价解释与下一步</div>
        <div class="config-list">
          <div v-if="evaluationExplain.summary" class="config-item config-item--stack">
            <div class="config-item__title">本次评价说明</div>
            <div class="config-item__hint">{{ evaluationExplain.summary }}</div>
          </div>
          <div v-if="evaluationExplain.explain_cards?.length" class="behavior-overview-grid">
            <div v-for="item in evaluationExplain.explain_cards" :key="item.key" class="config-item config-item--stack">
              <div class="config-item__meta">
                <span>{{ item.label }}</span>
                <strong>{{ Math.round(Number(item.score || 0) * 100) }}%</strong>
              </div>
              <div class="config-item__hint">{{ item.explain }}</div>
              <div class="config-item__hint">状态：{{ item.score_label }}</div>
            </div>
          </div>
          <div v-if="latestRecommendation?.target_kp_title" class="config-item config-item--stack">
            <div class="config-item__title">推荐学习目标</div>
            <div class="config-item__hint">
              建议优先学习“{{ latestRecommendation.target_kp_title }}”
              <span v-if="latestRecommendation.reason_summary">，原因：{{ latestRecommendation.reason_summary }}</span>
            </div>
          </div>
          <div v-if="evaluationExplain.next_actions?.length" class="advice-list">
            <div v-for="item in evaluationExplain.next_actions" :key="item" class="advice-item">{{ item }}</div>
          </div>
        </div>
      </section>

      <section class="dimension-board report-card--metric">
        <div class="board-title">核心维度</div>
        <div class="dimension-list">
          <div v-for="item in dimensions" :key="item.label" class="dimension-item">
            <div class="dimension-top">
              <span>{{ item.label }}</span>
              <strong>{{ Math.round(item.value * 100) }}%</strong>
            </div>
            <div class="dimension-bar">
              <div class="dimension-bar__value" :style="{ width: `${Math.round(item.value * 100)}%`, background: item.color }" />
            </div>
          </div>
        </div>
      </section>

      <section v-if="graphCoverage" class="dimension-board report-card--metric">
        <div class="board-title">知识图谱融合评价</div>
        <div class="dimension-list">
          <div class="dimension-item">
            <div class="dimension-top">
              <span>学习覆盖度</span>
              <strong>{{ graphCoverage.completed_nodes || 0 }}/{{ graphCoverage.total_nodes || 0 }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{ width: `${Math.round((graphCoverage.learning_coverage || 0) * 100)}%`, background: '#2f8cff' }"
              />
            </div>
          </div>
          <div class="dimension-item">
            <div class="dimension-top">
              <span>掌握覆盖度</span>
              <strong>{{ graphCoverage.mastered_nodes || 0 }}/{{ graphCoverage.total_nodes || 0 }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{ width: `${Math.round((graphCoverage.mastery_coverage || 0) * 100)}%`, background: '#2cb67d' }"
              />
            </div>
          </div>
          <div class="dimension-item">
            <div class="dimension-top">
              <span>图谱评价得分</span>
              <strong>{{ Math.round((graphCoverage.graph_score || 0) * 100) }}%</strong>
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{ width: `${Math.round((graphCoverage.graph_score || 0) * 100)}%`, background: '#ff9b42' }"
              />
            </div>
          </div>
        </div>
        <div class="empty-help__text" style="text-align:left; margin-top: 10px;">
          图谱评价得分 = 学习覆盖度 60% + 掌握覆盖度 40%，并以 20% 权重融入动态评价。
        </div>
      </section>

      <section class="dimension-board report-card--metric">
        <div class="board-title">学期总结果</div>
        <div class="dimension-list">
          <div class="dimension-item">
            <div class="dimension-top"><span>覆盖阶段</span><strong>{{ termSummary.stage_count || 0 }}</strong></div>
            <div class="dimension-bar"><div class="dimension-bar__value" :style="{ width: `${Math.min(100, (termSummary.stage_count || 0) * 20)}%`, background: '#2f8cff' }" /></div>
          </div>
          <div class="dimension-item">
            <div class="dimension-top"><span>学期参考分</span><strong>{{ Math.round((termSummary.final_score_reference || 0) * 100) }}%</strong></div>
            <div class="dimension-bar"><div class="dimension-bar__value" :style="{ width: `${Math.round((termSummary.final_score_reference || 0) * 100)}%`, background: '#2cb67d' }" /></div>
          </div>
          <div class="dimension-item">
            <div class="dimension-top"><span>进步次数</span><strong>{{ termSummary.progress_stages || 0 }}</strong></div>
            <div class="dimension-bar"><div class="dimension-bar__value" :style="{ width: `${Math.min(100, (termSummary.progress_stages || 0) * 20)}%`, background: '#ff9b42' }" /></div>
          </div>
        </div>
        <div class="empty-help__text" style="text-align:left; margin-top: 10px;">
          {{ termSummary.final_reason_summary || "系统会把整个学期的结果汇总到这里。" }}
        </div>
      </section>

      <section class="dimension-board report-card--kal">
        <div class="board-title">知识 / 能力 / 素养</div>
        <div class="dimension-list">
          <div class="dimension-item">
            <div class="dimension-top">
              <span>知识点达成</span>
              <strong>{{ kpDimensionSummary.knowledge_achieved || 0 }}/{{ kpDimensionSummary.knowledge_total || 0 }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{ width: `${Math.round(((kpDimensionSummary.knowledge_achieved || 0) / Math.max(1, kpDimensionSummary.knowledge_total || 0)) * 100)}%`, background: '#2ea96b' }"
              />
            </div>
          </div>
          <div class="dimension-item">
            <div class="dimension-top">
              <span>能力目标达成</span>
              <strong>{{ kpDimensionSummary.ability_achieved || 0 }}/{{ kpDimensionSummary.ability_target_total || 0 }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{ width: `${Math.round(((kpDimensionSummary.ability_achieved || 0) / Math.max(1, kpDimensionSummary.ability_target_total || 0)) * 100)}%`, background: '#f0b429' }"
              />
            </div>
          </div>
          <div class="dimension-item">
            <div class="dimension-top">
              <span>素养目标达成</span>
              <strong>{{ kpDimensionSummary.literacy_achieved || 0 }}/{{ kpDimensionSummary.literacy_target_total || 0 }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{ width: `${Math.round(((kpDimensionSummary.literacy_achieved || 0) / Math.max(1, kpDimensionSummary.literacy_target_total || 0)) * 100)}%`, background: '#2f8cff' }"
              />
            </div>
          </div>
        </div>
        <div class="kal-grid">
          <div class="kal-card">
            <div class="kal-card__title">当前较强能力</div>
            <div v-if="topAbilityRows.length" class="kal-list">
              <div v-for="item in topAbilityRows" :key="`ability-${item.label}`" class="kal-item">
                <span>{{ item.label }}</span>
                <strong>{{ item.achieved_count }}/{{ item.target_count }}</strong>
              </div>
            </div>
            <div v-else class="empty-help__text">当前还没有形成明显能力优势，先继续完成知识点学习与练习。</div>
          </div>
          <div class="kal-card">
            <div class="kal-card__title">当前较强素养</div>
            <div v-if="topLiteracyRows.length" class="kal-list">
              <div v-for="item in topLiteracyRows" :key="`literacy-${item.label}`" class="kal-item">
                <span>{{ item.label }}</span>
                <strong>{{ item.achieved_count }}/{{ item.target_count }}</strong>
              </div>
            </div>
            <div v-else class="empty-help__text">当前素养证据还不多，可以多使用老师推荐资源、完成视频与拓展内容。</div>
          </div>
        </div>
      </section>

      <section v-if="abilityPracticeStats" class="dimension-board report-card--practice">
        <div class="board-title">练习表现 · 认知层级与能力标签</div>
        <p v-if="abilityPracticeStats.high_order_note" class="empty-help__text" style="text-align: left; margin-bottom: 12px">
          {{ abilityPracticeStats.high_order_note }}。下方「高阶」指应用、分析、评价、创造四类题目上的答题情况。
        </p>
        <div v-if="(abilityPracticeStats.overall?.attempts ?? 0) > 0" class="dimension-list">
          <div class="dimension-item">
            <div class="dimension-top">
              <span>全部练习尝试</span>
              <strong
                >{{ abilityPracticeStats.overall?.correct ?? 0 }}/{{ abilityPracticeStats.overall?.attempts ?? 0 }} ·
                {{ Math.round((abilityPracticeStats.overall?.accuracy ?? 0) * 100) }}%</strong
              >
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{
                  width: `${Math.round((abilityPracticeStats.overall?.accuracy ?? 0) * 100)}%`,
                  background: '#5b8fd9',
                }"
              />
            </div>
          </div>
          <div class="dimension-item">
            <div class="dimension-top">
              <span>高阶题尝试</span>
              <strong
                >{{ abilityPracticeStats.high_order_overall?.correct ?? 0 }}/{{
                  abilityPracticeStats.high_order_overall?.attempts ?? 0
                }}
                · {{ Math.round((abilityPracticeStats.high_order_overall?.accuracy ?? 0) * 100) }}%</strong
              >
            </div>
            <div class="dimension-bar">
              <div
                class="dimension-bar__value"
                :style="{
                  width: `${Math.round((abilityPracticeStats.high_order_overall?.accuracy ?? 0) * 100)}%`,
                  background: '#16a34a',
                }"
              />
            </div>
          </div>
        </div>
        <el-empty
          v-else
          description="还没有足够练习记录；请老师为题目标注认知层级与能力标签后多完成练习。"
          :image-size="72"
          style="margin: 12px 0"
        />
        <div v-if="(abilityPracticeStats.by_ability_tag?.length ?? 0) > 0" style="margin-top: 14px">
          <div class="kal-card__title" style="margin-bottom: 8px">按能力二级标签 · 高阶题正确率</div>
          <div class="kal-list">
            <div v-for="row in abilityPracticeStats.by_ability_tag" :key="`apt-${row.label}`" class="kal-item">
              <span>{{ row.label }}</span>
              <strong
                >高阶 {{ row.high_order_correct }}/{{ row.high_order_attempts }} ({{
                  Math.round((row.high_order_accuracy || 0) * 100)
                }}%) · 全题 {{ row.all_correct }}/{{ row.all_attempts }}</strong
              >
            </div>
          </div>
        </div>
        <div v-if="(abilityPracticeStats.by_cognitive_level?.length ?? 0) > 0" style="margin-top: 14px">
          <div class="kal-card__title" style="margin-bottom: 8px">按认知层级</div>
          <div class="kal-list">
            <div v-for="row in abilityPracticeStats.by_cognitive_level" :key="`cl-${row.level}`" class="kal-item">
              <span>{{ bloomLevelLabel(row.level) }}{{ row.is_high_order ? "（高阶）" : "" }}</span>
              <strong>{{ row.correct }}/{{ row.attempts }}（{{ Math.round((row.accuracy || 0) * 100) }}%）</strong>
            </div>
          </div>
        </div>
      </section>

      <section class="dimension-board report-card--radar">
        <div class="board-title">当前阶段结果</div>
        <PortraitRadarChart
          title="当前阶段结果图"
          subtitle="这张图表示你在当前阶段各方面的大致情况。"
          :items="stageResultRows"
          accent="#2f8cff"
          empty-text="这门课当前还没有足够数据生成雷达图"
        />
        <div v-if="stageResultRows.length" class="dimension-list">
          <div v-for="item in stageResultRows" :key="item.dimension_title" class="dimension-item">
            <div class="dimension-top">
              <span>{{ item.dimension_title }}</span>
              <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                v-if="item.score != null"
                class="dimension-bar__value"
                :style="{ width: `${Math.round(item.score * 100)}%`, background: '#2f8cff' }"
              />
            </div>
          </div>
        </div>
        <div v-else class="empty-help">
          <el-empty description="这门课还没有生成阶段结果" />
          <div class="empty-help__text">一般是因为老师还没导入阶段数据，或者这门课还没配置完成。</div>
        </div>
      </section>

      <section v-if="finalPortraitDimensions.length" class="dimension-board report-card--radar">
        <div class="board-title">学期结果汇总</div>
        <PortraitRadarChart
          title="学期结果图"
          subtitle="这张图是把整个学期的结果汇总后得到的。"
          :items="finalPortraitDimensions"
          accent="#2cb67d"
          empty-text="当前还没有可展示的学期结果图"
        />
        <div class="dimension-list">
          <div v-for="item in finalPortraitDimensions" :key="item.dimension_title" class="dimension-item">
            <div class="dimension-top">
              <span>{{ item.dimension_title }}</span>
              <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                v-if="item.score != null"
                class="dimension-bar__value"
                :style="{ width: `${Math.round(item.score * 100)}%`, background: '#2cb67d' }"
              />
            </div>
          </div>
        </div>
      </section>

      <section class="stage-board report-card--timeline">
        <div class="board-title">学习变化</div>
        <div v-if="timelineCards.length" class="stage-list">
          <div v-for="item in timelineCards" :key="`${item.stage_id}-${item.stage_order}`" class="stage-card">
            <div class="stage-card__top">
              <span class="stage-card__index">阶段 {{ item.stage_order }}</span>
              <el-tag size="small" :type="item.trend_label === '进步' ? 'success' : item.trend_label === '退步' ? 'danger' : 'info'">
                {{ item.trend_label }}
              </el-tag>
            </div>
            <div class="stage-card__title">{{ item.stage_title }}</div>
            <div class="stage-card__metrics">
              <span>评分 {{ Math.round((item.dynamic_score || 0) * 100) }}%</span>
              <span>掌握 {{ Math.round((item.course_mastery || 0) * 100) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-help">
          <el-empty description="当前还没有阶段评价数据" />
          <div class="empty-help__text">请先让老师创建阶段并导入学习数据，系统才会生成阶段变化。</div>
        </div>
      </section>
      <section class="detail-tabs">
        <el-tabs v-model="reportTab">
          <el-tab-pane label="结果和建议" name="summary">
            <div class="detail-grid">
              <section class="feedback-board">
                <div class="board-title">老师建议</div>
                <div v-if="profile.teacher_feedback" class="feedback-card">
                  <div class="feedback-tag">{{ profile.teacher_feedback.feedback_tag || "阶段评语" }}</div>
                  <div class="feedback-text">{{ profile.teacher_feedback.comment || "老师暂时还没有填写建议" }}</div>
                  <div class="feedback-meta">
                    {{ profile.teacher_feedback.updated_by || "教师" }}
                    <span v-if="profile.teacher_feedback.updated_at">· {{ new Date(profile.teacher_feedback.updated_at).toLocaleString() }}</span>
                  </div>
                </div>
                <div v-else class="empty-help empty-help--compact">
                  <el-empty description="当前阶段暂无老师建议" :image-size="72" />
                  <div class="empty-help__text">这不是错误，只是老师暂时还没有填写。</div>
                </div>
              </section>

              <section class="advice-board">
                <div class="board-title">下一步怎么学</div>
                <div class="advice-list">
                  <div v-for="item in suggestions" :key="item" class="advice-item">{{ item }}</div>
                </div>
              </section>
            </div>
          </el-tab-pane>

          <el-tab-pane label="详细结果" name="indicators">
            <div class="detail-grid">
              <section class="config-board">
                <div class="board-title">老师当前参考的内容</div>
                <div v-if="dimensionConfig.length" class="config-list">
                  <div v-for="item in dimensionConfig" :key="item.key" class="config-item">
                    <span>{{ item.label }}</span>
                    <strong>{{ Math.round(item.weight * 100) }}%</strong>
                  </div>
                </div>
                <div v-else class="empty-help empty-help--compact">
                  <el-empty description="老师还没设置当前阶段要看哪些内容" :image-size="72" />
                  <div class="empty-help__text">老师先设置评价项，这里才会显示。</div>
                </div>
              </section>

              <section class="config-board">
                <div class="board-title">详细分项结果</div>
                <div v-if="portraitIndicators.length" class="config-list">
                  <div v-for="item in portraitIndicators" :key="item.title" class="config-item config-item--stack">
                    <div class="config-item__title">{{ item.title }}</div>
                    <div class="config-item__meta">
                      <span>{{ sourceTypeLabel(item.source_type) }}</span>
                      <span>{{ scoreSourceLabel(item.score_source) }}</span>
                      <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
                    </div>
                    <div v-if="item.formula_text" class="config-item__hint">{{ item.formula_text }}</div>
                    <div v-if="item.evidence_metrics?.length" class="config-item__chips">
                      <span v-for="metric in item.evidence_metrics" :key="`${item.title}-${metric.metric_label}`">
                        {{ metric.metric_label }} {{ metric.metric_percent }}%
                      </span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-help empty-help--compact">
                  <el-empty description="当前阶段还没有详细分项结果" :image-size="72" />
                  <div class="empty-help__text">老师导入数据后，系统会自动生成这里的结果。</div>
                </div>
              </section>
            </div>
          </el-tab-pane>

          <el-tab-pane label="我来补充" name="questionnaire">
            <section class="config-board" v-loading="questionnaireLoading">
              <div class="board-title">补充学习情况</div>
              <div v-if="hasQuestionnaireItems" class="config-list">
                <div v-for="item in questionnaireIndicators" :key="item.indicator_id" class="config-item config-item--stack">
                  <div class="config-item__title">{{ item.indicator_title }}</div>
                  <div class="config-item__meta">
                    <span>{{ item.dimension_title }}</span>
                    <span>学生补充项</span>
                  </div>
                  <div class="questionnaire-row">
                    <div class="questionnaire-row__value">你的问卷答案：{{ questionnaireOptionLabel(item.score) }}</div>
                    <el-radio-group v-model="item.score" size="small" class="questionnaire-row__options">
                      <el-radio-button
                        v-for="option in QUESTIONNAIRE_SCORE_OPTIONS"
                        :key="`${item.indicator_id}-questionnaire-${option.value}`"
                        :label="option.value"
                      >
                        {{ option.label }}
                      </el-radio-button>
                    </el-radio-group>
                  </div>
                  <div class="questionnaire-row__hint">
                    这里只需要按实际情况选择并补充说明，不用自己计算分数。
                  </div>
                  <el-input v-model="item.note" type="textarea" :rows="2" placeholder="补充标签或说明" />
                </div>
                <div class="questionnaire-actions">
                  <el-button type="primary" :loading="savingQuestionnaire" @click="saveQuestionnaireIndicators">保存</el-button>
                </div>
              </div>
              <div v-else class="empty-help empty-help--compact">
                <el-empty description="这门课还没有需要你补充填写的内容" :image-size="72" />
                <div class="empty-help__text">如果老师开启了这部分内容，你就可以在这里填写。</div>
              </div>
            </section>
          </el-tab-pane>

          <el-tab-pane label="分类查看" name="mi-map">
            <section class="config-board">
              <div class="board-title">按类别查看结果</div>
              <div class="mi-intro">
                这里会把结果按几大类分开，方便你看清楚自己哪一类更强，哪一类还要补。
              </div>
              <div v-if="mentorDimensionGroups.length" class="mi-grid">
                <article v-for="group in mentorDimensionGroups" :key="group.title" class="mi-card">
                  <div class="mi-card__head">
                    <div>
                      <div class="mi-card__title">{{ group.title }}</div>
                      <div class="mi-card__meta">子指标 {{ group.indicators.length }} · 完成度 {{ group.completion }}%</div>
                    </div>
                    <div class="mi-card__score">{{ group.score == null ? "待补充" : `${Math.round(group.score * 100)}%` }}</div>
                  </div>
                  <div class="mi-list">
                    <div v-for="item in group.indicators" :key="`${group.title}-${item.title}`" class="mi-item">
                      <div class="mi-item__top">
                        <span>{{ item.title }}</span>
                        <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
                      </div>
                      <div class="mi-item__meta">
                        {{ sourceTypeLabel(item.source_type) }} · {{ scoreSourceLabel(item.score_source) }}
                      </div>
                      <div class="mi-item__bar">
                        <div
                          v-if="item.score != null"
                          class="mi-item__bar-value"
                          :style="{ width: `${Math.round(item.score * 100)}%` }"
                        />
                      </div>
                    </div>
                  </div>
                </article>
              </div>
              <div v-else class="empty-help empty-help--compact">
                <el-empty description="当前还没有可展示的分类结果" :image-size="72" />
                <div class="empty-help__text">请先让老师完成阶段数据导入，并补充需要的内容。</div>
              </div>
            </section>
          </el-tab-pane>

          <el-tab-pane label="学习行为记录" name="behavior">
            <section class="config-board">
              <div class="board-title">学习行为记录（多视图）</div>
              <div class="mi-intro">先看总览，再按“登录/时长/视频/答题/时间线”逐步查看，操作更清晰。</div>
              <el-tabs v-model="behaviorSubTab">
                <el-tab-pane label="总览" name="overview">
                  <div class="behavior-overview-grid">
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">登录频率（30天）</div>
                      <div class="config-item__meta">
                        <span>登录次数 {{ learningBehaviorOverview?.login_count_30d ?? 0 }}</span>
                        <strong>登录天数 {{ learningBehaviorOverview?.login_days_30d ?? 0 }}</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">学习活跃（14天）</div>
                      <div class="config-item__meta">
                        <span>活跃天数 {{ learningBehaviorOverview?.active_days_14d ?? 0 }}</span>
                        <strong>连续 {{ learningBehaviorOverview?.consecutive_days_14d ?? 0 }} 天</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">学习时长（14天）</div>
                      <div class="config-item__meta">
                        <span>视频+练习+小测合计</span>
                        <strong>{{ Math.round(Number(learningBehaviorOverview?.study_duration_minutes_14d ?? 0)) }} 分钟</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">视频进度（30天）</div>
                      <div class="config-item__meta">
                        <span>开始 {{ learningBehaviorOverview?.video_started_30d ?? 0 }} · 完成 {{ learningBehaviorOverview?.video_completed_30d ?? 0 }}</span>
                        <strong>{{ Math.round(Number(learningBehaviorOverview?.avg_video_completion_30d ?? 0) * 100) }}%</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">答题行为（30天）</div>
                      <div class="config-item__meta">
                        <span>尝试 {{ learningBehaviorOverview?.practice_attempts_30d ?? 0 }} 次</span>
                        <strong>{{ Math.round(Number(learningBehaviorOverview?.practice_accuracy_30d ?? 0) * 100) }}%</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">常见行为类型</div>
                      <div class="config-item__chips">
                        <span v-for="row in learningBehaviorOverview?.top_event_types_30d ?? []" :key="row.event_type">
                          {{ row.event_type }} {{ row.count }}
                        </span>
                      </div>
                    </div>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="登录与活跃" name="login">
                  <div class="mi-intro">功能范围：查看登录频率、活跃天数与连续学习状态；操作说明：先看 30 天登录，再看 14 天活跃与连续天数。</div>
                  <div class="behavior-overview-grid">
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">登录次数（30天）</div>
                      <div class="config-item__meta">
                        <span>累计登录</span>
                        <strong>{{ learningBehaviorOverview?.login_count_30d ?? 0 }} 次</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">登录天数（30天）</div>
                      <div class="config-item__meta">
                        <span>发生过登录的日期</span>
                        <strong>{{ learningBehaviorOverview?.login_days_30d ?? 0 }} 天</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">活跃天数（14天）</div>
                      <div class="config-item__meta">
                        <span>有学习行为发生</span>
                        <strong>{{ learningBehaviorOverview?.active_days_14d ?? 0 }} 天</strong>
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">连续学习（14天）</div>
                      <div class="config-item__meta">
                        <span>最近连续活跃</span>
                        <strong>{{ learningBehaviorOverview?.consecutive_days_14d ?? 0 }} 天</strong>
                      </div>
                    </div>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="学习时长" name="duration">
                  <div class="mi-intro">功能范围：查看学习时长汇总；操作说明：先看总分钟，再看各来源（练习/小测/视频）对时长的共同贡献。</div>
                  <div class="behavior-overview-grid">
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">总学习时长（14天）</div>
                      <div class="config-item__meta">
                        <span>视频 + 练习 + 小测</span>
                        <strong>{{ Math.round(Number(learningBehaviorOverview?.study_duration_minutes_14d ?? 0)) }} 分钟</strong>
                      </div>
                      <div class="config-item__hint">
                        该时长用于反映近期投入强度，建议与“答题正确率/视频完成率”一起看，避免只看时长不看效果。
                      </div>
                    </div>
                    <div class="config-item config-item--stack">
                      <div class="config-item__title">推荐参与（30天）</div>
                      <div class="config-item__meta">
                        <span>系统推荐链路触发</span>
                        <strong>{{ learningBehaviorOverview?.recommendation_count_30d ?? 0 }} 次</strong>
                      </div>
                      <div class="config-item__hint">若时长高但推荐参与低，通常表示学习路径较固定，可尝试增加薄弱点推荐学习。</div>
                    </div>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="视频学习" name="video">
                  <div class="mi-intro">功能范围：查看最近视频学习进度、是否完成与更新时间。</div>
                  <el-table :data="recentVideoRecords" size="small" max-height="340">
                    <el-table-column prop="kp_id" label="知识点ID" width="110" />
                    <el-table-column label="观看进度" min-width="180">
                      <template #default="{ row }">
                        <el-progress
                          :percentage="
                            Math.round(
                              Math.min(
                                100,
                                Number(row.duration_seconds || 0) > 0
                                  ? (Number(row.watched_seconds || 0) / Number(row.duration_seconds || 1)) * 100
                                  : 0
                              )
                            )
                          "
                          :stroke-width="8"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column prop="completed" label="完成" width="90">
                      <template #default="{ row }">
                        <el-tag :type="row.completed ? 'success' : 'info'">{{ row.completed ? "已完成" : "进行中" }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="updated_at" label="更新时间" min-width="180">
                      <template #default="{ row }">{{ new Date(row.updated_at).toLocaleString() }}</template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>

                <el-tab-pane label="答题行为" name="practice">
                  <div class="mi-intro">功能范围：查看练习与小测作答记录、正确率、耗时。</div>
                  <div class="detail-grid">
                    <section class="config-board">
                      <div class="board-title">最近练习</div>
                      <el-table :data="recentPracticeRecords" size="small" max-height="300">
                        <el-table-column prop="kp_id" label="知识点ID" width="110" />
                        <el-table-column prop="question_id" label="题目ID" width="100" />
                        <el-table-column prop="correct" label="结果" width="90">
                          <template #default="{ row }">
                            <el-tag :type="row.correct ? 'success' : 'danger'">{{ row.correct ? "正确" : "错误" }}</el-tag>
                          </template>
                        </el-table-column>
                        <el-table-column prop="duration_ms" label="耗时(ms)" width="110" />
                        <el-table-column prop="created_at" label="提交时间" min-width="180">
                          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
                        </el-table-column>
                      </el-table>
                    </section>
                    <section class="config-board">
                      <div class="board-title">最近小测</div>
                      <el-table :data="recentQuizRecords" size="small" max-height="300">
                        <el-table-column prop="kp_id" label="知识点ID" width="110" />
                        <el-table-column prop="score" label="得分" width="90">
                          <template #default="{ row }">{{ Math.round((row.score || 0) * 100) }}%</template>
                        </el-table-column>
                        <el-table-column prop="passed" label="通过" width="90">
                          <template #default="{ row }">
                            <el-tag :type="row.passed ? 'success' : 'info'">{{ row.passed ? "通过" : "未通过" }}</el-tag>
                          </template>
                        </el-table-column>
                        <el-table-column prop="duration_ms" label="耗时(ms)" width="110" />
                        <el-table-column prop="created_at" label="提交时间" min-width="180">
                          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
                        </el-table-column>
                      </el-table>
                    </section>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="行为时间线" name="timeline">
                  <div class="mi-intro">功能范围：查看系统自动采集的行为事件原始记录，用于核对学习过程。</div>
                  <div class="config-list">
                    <div v-for="item in behaviorTimeline" :key="item.id" class="config-item config-item--stack">
                      <div class="config-item__meta">
                        <span>{{ item.event_type }}</span>
                        <strong>{{ new Date(item.created_at).toLocaleString() }}</strong>
                      </div>
                      <div class="config-item__hint">{{ item.value_json }}</div>
                    </div>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </section>
          </el-tab-pane>

        </el-tabs>
      </section>
    </div>
    <div v-else class="report-empty">
      <el-empty description="这门课还没有形成学习情况报告" :image-size="88" />
      <div class="report-tip-inline">
        <span>为什么还没有结果</span>
        <HoverTip content="先让老师完成三步：1. 选这门课要看的内容；2. 创建阶段；3. 导入阶段数据。完成后，这里就会自动出现结果。" />
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.report-shell {
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(99, 120, 153, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: none;
}

.report-shell :deep(.el-card__header) {
  padding: 18px 20px;
  border-bottom: 1px solid #e6eef7;
  background: rgba(255, 255, 255, 0.86);
}

.report-shell :deep(.el-card__body) {
  padding: 18px;
}

.report-ability-provenance {
  margin-bottom: 16px;
  border: 1px solid #d9e6f2;
  border-radius: 14px;
  overflow: hidden;
  --el-collapse-header-bg-color: #f6faff;
}
.report-ability-provenance :deep(.el-collapse-item__header) {
  font-weight: 700;
  color: #243449;
  padding: 12px 16px;
}
.report-ability-provenance :deep(.el-collapse-item__wrap) {
  border-top: 1px solid #e6eef7;
}
.report-ability-provenance__body {
  padding: 4px 4px 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #617792;
}
.report-ability-provenance__body p {
  margin: 0 0 10px;
}
.report-ability-provenance__body p:last-child {
  margin-bottom: 0;
}

.report-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  align-items: start;
}

.report-grid__hero {
  grid-column: 1 / -1;
}

.report-card--metric {
  grid-column: span 4;
}

.report-card--kal {
  grid-column: span 5;
}

.report-card--practice {
  grid-column: span 7;
}

.report-card--radar {
  grid-column: span 6;
  min-height: 0;
}

.report-card--timeline {
  grid-column: 1 / -1;
}

.report-empty {
  display: grid;
  gap: 14px;
}

.report-empty__tip {
  margin-top: -6px;
}

.report-tip-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #617792;
  font-size: 13px;
  font-weight: 700;
}

.detail-tabs {
  grid-column: 1 / -1;
}

.detail-tabs :deep(.el-tabs__nav-scroll) {
  padding: 2px 6px;
}

.detail-tabs :deep(.el-tabs__item) {
  min-height: 38px;
  font-weight: 700;
  border-radius: 10px;
  border: 1px solid #dbe7f3;
  background: #f8fafc;
  color: #52647a;
  padding: 6px 14px;
  transition: all 0.2s ease;
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
  border-bottom: none;
}

.detail-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.detail-tabs :deep(.el-tabs__nav-wrap)::after {
  display: none;
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  background: #ecfdf5;
  border-color: rgba(34, 197, 94, 0.32);
  color: #166534;
  box-shadow: 0 8px 16px rgba(34, 197, 94, 0.1);
}

.detail-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.empty-help {
  display: grid;
  gap: 8px;
  align-content: start;
}

.empty-help--compact :deep(.el-empty) {
  padding: 6px 0;
}

.empty-help__text {
  font-size: 12px;
  line-height: 1.7;
  color: var(--app-ink-soft);
  text-align: center;
}

.dimension-board,
.stage-board,
.config-board,
.feedback-board,
.advice-board {
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(99, 120, 153, 0.18);
  box-shadow: 0 12px 28px rgba(20, 35, 58, 0.06);
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 800;
  color: #102033;
  margin-bottom: 14px;
}

.board-title::before {
  content: "";
  width: 8px;
  height: 18px;
  border-radius: 999px;
  background: linear-gradient(180deg, #2563eb, #22c55e);
}

.dimension-list,
.config-list,
.advice-list,
.stage-list {
  display: grid;
  gap: 10px;
}

.dimension-item {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #dbe7f3;
  background: #ffffff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.kal-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.kal-card {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #dbe7f3;
  background: #ffffff;
  display: grid;
  gap: 10px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.kal-card__title {
  font-size: 13px;
  font-weight: 800;
  color: #243449;
}

.kal-list {
  display: grid;
  gap: 8px;
}

.kal-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  font-size: 13px;
  color: #617792;
}

.kal-item span,
.kal-item strong {
  min-width: 0;
}

.kal-item strong {
  white-space: nowrap;
}

.dimension-top,
.config-item,
.stage-card__top,
.stage-card__metrics {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.dimension-top {
  font-size: 13px;
  color: #52647a;
}

.dimension-bar {
  height: 9px;
  border-radius: 999px;
  overflow: hidden;
  background: #e7eef8;
}

.dimension-bar__value {
  height: 100%;
  border-radius: inherit;
}

.stage-list {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}

.stage-card {
  padding: 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #dbe7f3;
  display: grid;
  gap: 8px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.stage-card__index {
  font-size: 12px;
  color: #52647a;
}

.stage-card__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
}

.stage-card__metrics {
  font-size: 12px;
  color: #52647a;
}

.config-item {
  padding: 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #dbe7f3;
  color: var(--app-ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.config-item--stack {
  display: grid;
  gap: 6px;
}

.config-item__title {
  font-weight: 700;
  color: var(--app-ink);
}

.config-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  color: #52647a;
  font-size: 12px;
}

.config-item__hint {
  font-size: 12px;
  line-height: 1.6;
  color: #52647a;
}

.config-item__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.config-item__chips span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  border: 1px solid #dbe7f3;
  color: #102033;
  font-size: 12px;
}

.questionnaire-row {
  margin-top: 4px;
}

.questionnaire-row__value {
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--app-ink-soft);
}

.questionnaire-row__options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.questionnaire-row__hint {
  font-size: 12px;
  color: #7f6747;
  line-height: 1.5;
}

.questionnaire-actions {
  display: flex;
  justify-content: flex-end;
}

.feedback-card {
  padding: 14px;
  border-radius: 12px;
  background: #f7fff9;
  border: 1px solid rgba(34, 197, 94, 0.22);
  display: grid;
  gap: 8px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.feedback-tag {
  font-size: 13px;
  font-weight: 700;
  color: #243449;
}

.feedback-text {
  color: var(--app-ink);
  line-height: 1.7;
}

.feedback-meta {
  font-size: 12px;
  color: #52647a;
}

.advice-item {
  position: relative;
  padding: 12px 14px 12px 34px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #dbe7f3;
  color: var(--app-ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.advice-item::before {
  content: "";
  position: absolute;
  left: 14px;
  top: 18px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
}

.mi-intro {
  margin-bottom: 12px;
  font-size: 12px;
  line-height: 1.7;
  color: #52647a;
}

.mi-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.mi-card {
  border: 1px solid #dbe7f3;
  border-radius: 14px;
  background: #ffffff;
  padding: 12px;
  display: grid;
  gap: 10px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.mi-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.mi-card__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
}

.mi-card__meta {
  margin-top: 2px;
  font-size: 12px;
  color: #52647a;
}

.mi-card__score {
  font-size: 14px;
  font-weight: 700;
  color: #166534;
}

.mi-list {
  display: grid;
  gap: 8px;
}

.mi-item {
  border: 1px solid #dbe7f3;
  border-radius: 12px;
  background: #ffffff;
  padding: 10px 12px;
  display: grid;
  gap: 5px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  min-width: 0;
}

.mi-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #52647a;
}

.mi-item__meta {
  font-size: 12px;
  color: #52647a;
}

.mi-item__bar {
  height: 8px;
  border-radius: 999px;
  background: #e7eef8;
  overflow: hidden;
}

.mi-item__bar-value {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #60a5fa 0%, #86efac 100%);
}

.behavior-overview-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

@media (max-width: 1320px) {
  .report-card--metric,
  .report-card--kal {
    grid-column: span 6;
  }

  .report-card--practice,
  .report-card--radar {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .report-grid {
    grid-template-columns: 1fr;
  }

  .report-card--metric,
  .report-card--kal,
  .report-card--practice,
  .report-card--radar,
  .report-card--timeline,
  .detail-tabs {
    grid-column: 1 / -1;
  }

  .kal-grid {
    grid-template-columns: 1fr;
  }

  .stage-list {
    grid-template-columns: 1fr;
  }
}
</style>
