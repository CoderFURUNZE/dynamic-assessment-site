<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

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
  portrait_indicators?: Array<{ title: string; score: number | null; available: boolean; source_type: string; weight: number }>;
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
  portrait_indicators?: Array<{ title: string; score: number | null; available: boolean; source_type: string; weight: number }>;
};

const props = defineProps<{ subject: string; grade: string }>();

const loading = ref(false);
const profile = ref<ProfileData | null>(null);
const questionnaireLoading = ref(false);
const savingQuestionnaire = ref(false);
const questionnaireIndicators = ref<Array<{ dimension_id: number; dimension_title: string; indicator_id: number; indicator_title: string; indicator_code: string; weight: number; score: number | null; note: string }>>([]);

const currentStage = computed(() => profile.value?.current_stage ?? null);
const stageHistory = computed(() => profile.value?.stage_history ?? []);
const dimensionConfig = computed(() => (profile.value?.dimension_config ?? []).filter((item) => item.enabled));
const hasStageModel = computed(() => stageHistory.value.length > 0 || Boolean(currentStage.value));
const portraitDimensions = computed(() => currentStage.value?.portrait_dimensions ?? profile.value?.portrait_dimensions ?? []);
const portraitIndicators = computed(() =>
  (currentStage.value?.portrait_indicators ?? profile.value?.portrait_indicators ?? []).filter((item) => item.available)
);

const dimensions = computed(() => {
  const current = profile.value;
  if (!current) return [];
  if (currentStage.value) {
    return [
      { label: "学习投入", value: currentStage.value.engagement ?? 0, color: "#2f8cff" },
      { label: "学习成效", value: currentStage.value.achievement ?? 0, color: "#2cb67d" },
      { label: "学习习惯", value: currentStage.value.habit ?? 0, color: "#ff9b42" },
      { label: "学习特征", value: currentStage.value.characteristic ?? 0, color: "#7b61ff" },
    ];
  }
  return [
    { label: "参与度 E", value: current.engagement ?? 0, color: "#2f8cff" },
    { label: "成效 A", value: current.achievement ?? 0, color: "#2cb67d" },
    { label: "效率 F", value: current.efficiency ?? 0, color: "#ff9b42" },
    { label: "风险 R", value: current.risk ?? 0, color: "#f2545b" },
  ];
});

const timelineCards = computed(() => {
  if (stageHistory.value.length) return stageHistory.value;
  return (profile.value?.trend ?? []).map((item, index) => ({
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
    base.push("先完成最短任务链，别同时开太多内容。", "把阶段目标拆成每天一小步。", "优先完成老师明确要求提交的任务和小测。");
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
  () => [props.subject, props.grade],
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
      <div class="report-header">
        <div>
          <div class="report-title">学习画像与动态评价</div>
          <div class="report-subtitle">系统会根据教师导入的阶段数据、知识图谱掌握情况和学习轨迹更新你的画像结果。</div>
        </div>
        <el-button size="small" @click="load" :loading="loading">刷新</el-button>
      </div>
    </template>

    <div v-if="profile" class="report-grid">
      <section class="report-hero">
        <div class="hero-label">当前画像</div>
        <div class="hero-title">{{ profile.persona_label }}</div>
        <div class="hero-stage">
          <span>{{ currentStage?.stage_title || "尚未形成阶段评价" }}</span>
          <el-tag v-if="currentStage" size="small" effect="dark">{{ currentStage.trend_label }}</el-tag>
        </div>
        <div class="hero-text">{{ currentStage?.reason_summary || profile.reason_summary }}</div>
        <div class="hero-metrics">
          <div class="hero-metric">
            <span>课程掌握度</span>
            <strong>{{ Math.round(profile.course_mastery * 100) }}%</strong>
          </div>
          <div class="hero-metric">
            <span>动态评分</span>
            <strong>{{ Math.round(profile.dynamic_score * 100) }}%</strong>
          </div>
          <div class="hero-metric">
            <span>{{ hasStageModel ? "阶段等级" : "稳定性" }}</span>
            <strong>{{ hasStageModel ? currentStage?.risk_level || profile.risk_level : `${Math.round(profile.stability * 100)}%` }}</strong>
          </div>
          <div class="hero-metric">
            <span>当前状态</span>
            <strong>{{ profile.risk_level }}</strong>
          </div>
        </div>
      </section>

      <section class="dimension-board">
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

      <section class="dimension-board">
        <div class="board-title">一级维度画像</div>
        <div v-if="portraitDimensions.length" class="dimension-list">
          <div v-for="item in portraitDimensions" :key="item.dimension_title" class="dimension-item">
            <div class="dimension-top">
              <span>{{ item.dimension_title }}</span>
              <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
            </div>
            <div class="dimension-bar">
              <div
                v-if="item.score != null"
                class="dimension-bar__value"
                :style="{ width: `${Math.round(item.score * 100)}%`, background: '#5c7cff' }"
              />
            </div>
          </div>
        </div>
        <el-empty v-else description="当前课程还未形成一级维度画像" />
      </section>

      <section class="stage-board">
        <div class="board-title">阶段变化</div>
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
        <el-empty v-else description="当前还没有阶段评价数据" />
      </section>

      <section class="config-board">
        <div class="board-title">当前启用维度</div>
        <div v-if="dimensionConfig.length" class="config-list">
          <div v-for="item in dimensionConfig" :key="item.key" class="config-item">
            <span>{{ item.label }}</span>
            <strong>{{ Math.round(item.weight * 100) }}%</strong>
          </div>
        </div>
        <el-empty v-else description="教师暂未配置阶段维度" />
      </section>

      <section class="config-board">
        <div class="board-title">二级指标映射结果</div>
        <div v-if="portraitIndicators.length" class="config-list">
          <div v-for="item in portraitIndicators" :key="item.title" class="config-item config-item--stack">
            <div class="config-item__title">{{ item.title }}</div>
            <div class="config-item__meta">
              <span>{{ item.source_type }}</span>
              <span>权重 {{ Number(item.weight || 0).toFixed(1) }}</span>
              <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
            </div>
          </div>
        </div>
        <el-empty v-else description="当前阶段暂无可映射的二级指标结果" />
      </section>

      <section class="config-board" v-loading="questionnaireLoading">
        <div class="board-title">问卷/标签补充指标</div>
        <div v-if="questionnaireIndicators.length" class="config-list">
          <div v-for="item in questionnaireIndicators" :key="item.indicator_id" class="config-item config-item--stack">
            <div class="config-item__title">{{ item.indicator_title }}</div>
            <div class="config-item__meta">
              <span>{{ item.dimension_title }}</span>
              <span>权重 {{ Number(item.weight || 0).toFixed(1) }}</span>
            </div>
            <div class="questionnaire-row">
              <el-slider v-model="item.score" :min="0" :max="1" :step="0.05" show-input />
            </div>
            <el-input v-model="item.note" type="textarea" :rows="2" placeholder="补充标签或说明" />
          </div>
          <div class="questionnaire-actions">
            <el-button type="primary" :loading="savingQuestionnaire" @click="saveQuestionnaireIndicators">保存问卷指标</el-button>
          </div>
        </div>
        <el-empty v-else description="当前课程未启用问卷/标签型指标" />
      </section>

      <section class="feedback-board">
        <div class="board-title">教师补充评价</div>
        <div v-if="profile.teacher_feedback" class="feedback-card">
          <div class="feedback-tag">{{ profile.teacher_feedback.feedback_tag || "阶段评语" }}</div>
          <div class="feedback-text">{{ profile.teacher_feedback.comment || "教师暂未填写补充评价" }}</div>
          <div class="feedback-meta">
            {{ profile.teacher_feedback.updated_by || "教师" }}
            <span v-if="profile.teacher_feedback.updated_at">· {{ new Date(profile.teacher_feedback.updated_at).toLocaleString() }}</span>
          </div>
        </div>
        <el-empty v-else description="当前阶段暂无教师补充评价" />
      </section>

      <section class="advice-board">
        <div class="board-title">个性化建议</div>
        <div class="advice-list">
          <div v-for="item in suggestions" :key="item" class="advice-item">{{ item }}</div>
        </div>
      </section>

      <section class="config-board">
        <div class="board-title">系统如何判断</div>
        <div class="config-list">
          <div class="config-item">动态评价：老师导入阶段数据后，系统更新阶段评分和趋势，不按每次点击实时重算。</div>
          <div class="config-item">学习者画像：当前以学习投入、学习成效、学习习惯、学习特征四类维度为主。</div>
          <div class="config-item">知识图谱：图谱负责组织知识结构，并把资源、任务、练习和小测挂到节点上。</div>
          <div class="config-item">推荐结果：系统先判断该补哪个点，再结合画像决定推什么资源和练习。</div>
        </div>
      </section>
    </div>
  </el-card>
</template>

<style scoped>
.report-shell {
  overflow: hidden;
}

.report-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.report-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.report-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-ink-soft);
}

.report-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: 1.1fr 0.9fr;
}

.report-hero {
  padding: 22px;
  border-radius: 24px;
  background: linear-gradient(135deg, #143759, #2a5d84);
  color: #f7fbff;
  display: grid;
  gap: 12px;
}

.hero-label {
  font-size: 12px;
  letter-spacing: 0.08em;
  opacity: 0.72;
  text-transform: uppercase;
}

.hero-title {
  font-size: 30px;
  font-weight: 800;
}

.hero-stage {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
  opacity: 0.92;
}

.hero-text {
  line-height: 1.7;
  font-size: 13px;
  opacity: 0.88;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.hero-metric {
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.12);
  display: grid;
  gap: 4px;
}

.hero-metric span {
  font-size: 12px;
  opacity: 0.8;
}

.hero-metric strong {
  font-size: 22px;
  font-weight: 800;
}

.dimension-board,
.stage-board,
.config-board,
.feedback-board,
.advice-board {
  padding: 18px;
  border-radius: 22px;
  background: #f7fafc;
  border: 1px solid #e0e8ef;
}

.board-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
  margin-bottom: 14px;
}

.dimension-list,
.config-list,
.advice-list,
.stage-list {
  display: grid;
  gap: 12px;
}

.dimension-item {
  display: grid;
  gap: 6px;
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
  color: #4b6888;
}

.dimension-bar {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #dfe8ef;
}

.dimension-bar__value {
  height: 100%;
  border-radius: inherit;
}

.stage-list {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.stage-card {
  padding: 14px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid #dce7ef;
  display: grid;
  gap: 8px;
}

.stage-card__index {
  font-size: 12px;
  color: #5b7797;
}

.stage-card__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-ink);
}

.stage-card__metrics {
  font-size: 12px;
  color: #587392;
}

.config-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #dde7ef;
  color: var(--app-ink);
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
  color: #5b7797;
  font-size: 12px;
}

.questionnaire-row {
  margin-top: 4px;
}

.questionnaire-actions {
  display: flex;
  justify-content: flex-end;
}

.feedback-card {
  padding: 14px 16px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid #dde7ef;
  display: grid;
  gap: 8px;
}

.feedback-tag {
  font-size: 13px;
  font-weight: 700;
  color: #184f88;
}

.feedback-text {
  color: var(--app-ink);
  line-height: 1.7;
}

.feedback-meta {
  font-size: 12px;
  color: #5b7797;
}

.advice-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #dde7ef;
  color: var(--app-ink);
}

@media (max-width: 960px) {
  .report-grid {
    grid-template-columns: 1fr;
  }
}
</style>
