<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import PortraitRadarChart from "./PortraitRadarChart.vue";

type StudentRow = {
  user_id: number;
  username: string;
  full_name: string;
  persona_label: string;
  dynamic_score: number;
  course_mastery: number;
  risk_level: string;
};

type StageHistoryItem = {
  stage_id: number;
  stage_title: string;
  stage_order: number;
  persona_label: string;
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
  updated_at: string;
};
type PortraitDimensionItem = { dimension_title: string; score: number | null; available: boolean };
type TermSummary = {
  stage_count?: number;
  progress_stages?: number;
  steady_stages?: number;
  regress_stages?: number;
  avg_dynamic_score?: number;
  latest_dynamic_score?: number;
  final_score_reference?: number;
  final_reason_summary?: string;
};
type FeedbackHistoryItem = {
  id: number;
  user_id: number;
  stage_id: number;
  stage_title: string;
  stage_order: number | null;
  feedback_tag: string;
  comment: string;
  updated_by: string;
  updated_at: string;
};

const props = withDefaults(defineProps<{ subject: string; grade: string; initialUserId?: number | null }>(), {
  initialUserId: null,
});

const loading = ref(false);
const detailLoading = ref(false);
const feedbackLoading = ref(false);
const savingFeedback = ref(false);
const teacherIndicatorLoading = ref(false);
const savingTeacherIndicators = ref(false);
const detailTab = ref("summary");
const emptyDetailMessage = ref("当前课程下还没有可展示的学生详情数据");
const students = ref<StudentRow[]>([]);
const selectedUserId = ref<number | null>(null);
const selectedStageId = ref<number | null>(null);
const detail = ref<any | null>(null);
const feedbackForm = reactive({
  feedback_tag: "",
  comment: "",
});
const feedbackHistory = ref<FeedbackHistoryItem[]>([]);
const teacherIndicators = ref<Array<{ dimension_id: number; dimension_title: string; indicator_id: number; indicator_title: string; indicator_code: string; weight: number; score: number | null; note: string }>>([]);

const feedbackTagOptions = ["进步明显", "保持稳定", "需要补强", "拖延风险", "建议面谈"];
const feedbackQuickTemplates = [
  "本阶段完成情况较稳定，建议保持当前学习节奏。",
  "建议优先补强前置知识点，再进入当前阶段核心任务。",
  "建议减少分散学习，先完成本阶段关键任务。",
  "建议每周固定复盘一次，重点关注错题和薄弱知识点。",
];

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

const weakPoints = computed(() =>
  (detail.value?.mastery_map ?? [])
    .slice()
    .sort((a: any, b: any) => Number(a.mastery ?? 0) - Number(b.mastery ?? 0))
    .slice(0, 6)
);

const stageHistory = computed<StageHistoryItem[]>(() => detail.value?.stage_history ?? []);
const finalPortraitDimensions = computed<PortraitDimensionItem[]>(() => detail.value?.profile?.final_portrait_dimensions ?? []);
const termSummary = computed<TermSummary>(() => detail.value?.profile?.term_summary ?? {});
const selectedStage = computed<StageHistoryItem | null>(() => {
  if (!selectedStageId.value) return stageHistory.value[stageHistory.value.length - 1] ?? null;
  return stageHistory.value.find((item) => item.stage_id === selectedStageId.value) ?? stageHistory.value[stageHistory.value.length - 1] ?? null;
});

async function loadStudents() {
  if (!props.subject) return;
  loading.value = true;
  try {
    const res = await api.get(
      `/admin/persona/students?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    students.value = res.data.items ?? [];
    if (props.initialUserId && students.value.some((item) => item.user_id === props.initialUserId)) {
      selectedUserId.value = props.initialUserId;
    } else if (!selectedUserId.value && students.value.length) {
      selectedUserId.value = students.value[0].user_id;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载学生列表失败");
  } finally {
    loading.value = false;
  }
}

function syncFeedbackForm(row: any | null) {
  feedbackForm.feedback_tag = row?.feedback_tag ?? "";
  feedbackForm.comment = row?.comment ?? "";
}

async function loadStageFeedback() {
  if (!selectedUserId.value || !selectedStageId.value || !props.subject) {
    syncFeedbackForm(null);
    return;
  }
  feedbackLoading.value = true;
  try {
    const res = await api.get(
      `/admin/stage-feedback?user_id=${selectedUserId.value}&subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&stage_id=${selectedStageId.value}`
    );
    syncFeedbackForm(res.data);
  } catch (e: any) {
    if (e?.response?.status === 404) {
      syncFeedbackForm(null);
    } else {
      ElMessage.error(e?.response?.data?.detail ?? "加载教师评语失败");
    }
  } finally {
    feedbackLoading.value = false;
  }
}

async function loadFeedbackHistory() {
  if (!selectedUserId.value || !props.subject) {
    feedbackHistory.value = [];
    return;
  }
  try {
    const res = await api.get(
      `/admin/stage-feedback/history?user_id=${selectedUserId.value}&subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    feedbackHistory.value = res.data?.items ?? [];
  } catch (e: any) {
    feedbackHistory.value = [];
    ElMessage.error(e?.response?.data?.detail ?? "加载评语历史失败");
  }
}

async function loadTeacherIndicators() {
  if (!selectedUserId.value || !selectedStageId.value || !props.subject) {
    teacherIndicators.value = [];
    return;
  }
  teacherIndicatorLoading.value = true;
  try {
    const courseId = detail.value?.profile?.course_id ?? detail.value?.course_id ?? null;
    if (!courseId) {
      teacherIndicators.value = [];
      return;
    }
    const res = await api.get(
      `/portrait/teacher-input?course_id=${courseId}&user_id=${selectedUserId.value}&stage_id=${selectedStageId.value}`
    );
    teacherIndicators.value = res.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师型指标失败");
  } finally {
    teacherIndicatorLoading.value = false;
  }
}

async function saveStageFeedback() {
  if (!selectedUserId.value || !selectedStageId.value) {
    ElMessage.warning("请先选择学生和阶段");
    return;
  }
  savingFeedback.value = true;
  try {
    const res = await api.put("/admin/stage-feedback", {
      user_id: selectedUserId.value,
      stage_id: selectedStageId.value,
      feedback_tag: feedbackForm.feedback_tag,
      comment: feedbackForm.comment,
    });
    detail.value = {
      ...(detail.value ?? {}),
      teacher_feedback: res.data,
    };
    await loadFeedbackHistory();
    await loadDetail();
    ElMessage.success("教师补充评价已保存，系统已重算该阶段画像");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存教师评语失败");
  } finally {
    savingFeedback.value = false;
  }
}

function applyQuickTemplate(text: string) {
  feedbackForm.comment = text;
}

function applyHistoryComment(row: FeedbackHistoryItem) {
  feedbackForm.feedback_tag = row.feedback_tag || feedbackForm.feedback_tag;
  feedbackForm.comment = row.comment || "";
}

async function saveTeacherIndicators() {
  if (!selectedUserId.value || !selectedStageId.value) {
    ElMessage.warning("请先选择学生和阶段");
    return;
  }
  const courseId = detail.value?.profile?.course_id ?? detail.value?.course_id ?? null;
  if (!courseId) {
    ElMessage.warning("当前课程信息缺失");
    return;
  }
  savingTeacherIndicators.value = true;
  try {
    await api.put(`/portrait/teacher-input?course_id=${courseId}`, {
      user_id: selectedUserId.value,
      stage_id: selectedStageId.value,
      inputs: teacherIndicators.value.map((item) => ({
        dimension_id: item.dimension_id,
        indicator_id: item.indicator_id,
        score: item.score,
        note: item.note,
      })),
    });
    await loadDetail();
    ElMessage.success("教师型二级指标已保存，系统已同步更新阶段画像和总画像");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存教师型指标失败");
  } finally {
    savingTeacherIndicators.value = false;
  }
}

async function loadDetail() {
  if (!selectedUserId.value || !props.subject) return;
  detailLoading.value = true;
  try {
    const res = await api.get(
      `/admin/analytics/student-detail?user_id=${selectedUserId.value}&subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    detail.value = res.data;
    const history = res.data?.stage_history ?? [];
    if (history.length) {
      const wanted = props.initialUserId === selectedUserId.value ? selectedStageId.value : null;
      const latest = history[history.length - 1]?.stage_id ?? null;
      selectedStageId.value = history.some((item: any) => item.stage_id === wanted) ? wanted : latest;
    } else {
      selectedStageId.value = null;
    }
    syncFeedbackForm(res.data?.teacher_feedback ?? null);
    emptyDetailMessage.value = "当前课程下还没有可展示的学生详情数据";
    await loadStageFeedback();
    await loadFeedbackHistory();
    await loadTeacherIndicators();
  } catch (e: any) {
    detail.value = null;
    selectedStageId.value = null;
    syncFeedbackForm(null);
    feedbackHistory.value = [];
    teacherIndicators.value = [];
    if (e?.response?.status === 404) {
      emptyDetailMessage.value = e?.response?.data?.detail ?? "当前课程下还没有可展示的学生详情数据";
    } else {
      emptyDetailMessage.value = "加载学生详情失败";
      ElMessage.error(e?.response?.data?.detail ?? "加载学生详情失败");
    }
  } finally {
    detailLoading.value = false;
  }
}

watch(
  () => [props.subject, props.grade],
  async () => {
    detail.value = null;
    selectedUserId.value = null;
    selectedStageId.value = null;
    await loadStudents();
    await loadDetail();
  },
  { immediate: true }
);

watch(
  () => selectedUserId.value,
  () => loadDetail()
);

watch(
  () => selectedStageId.value,
  async () => {
    await loadStageFeedback();
    await loadTeacherIndicators();
  }
);

watch(
  () => props.initialUserId,
  (value) => {
    if (value && value !== selectedUserId.value) {
      selectedUserId.value = value;
    }
  }
);
</script>

<template>
  <div class="student-detail-shell">
    <el-card class="panel-card" shadow="never" v-loading="loading">
      <template #header>
        <div class="detail-header">
          <div>
            <div class="detail-title">单学生学习详情</div>
            <div class="detail-subtitle">查看学生画像、阶段变化、教师补充评价和知识点掌握依据。</div>
          </div>
          <div class="detail-actions">
            <el-select v-model="selectedUserId" placeholder="选择学生" style="width: 260px">
              <el-option
                v-for="student in students"
                :key="student.user_id"
                :label="`${student.username} ${student.full_name || ''}`"
                :value="student.user_id"
              />
            </el-select>
          </div>
        </div>
      </template>

      <div v-if="detail" class="detail-grid" v-loading="detailLoading">
        <section class="hero-card">
          <div class="hero-label">当前学习者画像</div>
          <div class="hero-name">{{ detail.student.full_name || detail.student.username }}</div>
          <div class="hero-meta">
            {{ detail.profile.persona_label }} · {{ detail.profile.risk_level }}
            <span v-if="detail.profile.current_stage_title">· {{ detail.profile.current_stage_title }}</span>
            <span v-if="detail.profile.current_stage_trend">· {{ detail.profile.current_stage_trend }}</span>
          </div>
          <div class="hero-text">{{ selectedStage?.reason_summary || detail.profile.reason_summary }}</div>
          <div class="hero-stats">
            <div class="hero-stat">
              <span>动态评分</span>
              <strong>{{ Math.round((detail.profile.dynamic_score || 0) * 100) }}%</strong>
            </div>
            <div class="hero-stat">
              <span>课程掌握度</span>
              <strong>{{ Math.round((detail.profile.course_mastery || 0) * 100) }}%</strong>
            </div>
            <div class="hero-stat">
              <span>学习投入</span>
              <strong>{{ Math.round(((selectedStage?.engagement ?? detail.profile.engagement) || 0) * 100) }}%</strong>
            </div>
            <div class="hero-stat">
              <span>学习成效</span>
              <strong>{{ Math.round(((selectedStage?.achievement ?? detail.profile.achievement) || 0) * 100) }}%</strong>
            </div>
          </div>
        </section>

        <section class="panel-card soft-card">
          <div class="soft-title">阶段变化</div>
          <div v-if="stageHistory.length" class="stage-list">
            <button
              v-for="item in stageHistory"
              :key="item.stage_id"
              type="button"
              class="stage-item"
              :class="{ 'stage-item--active': item.stage_id === selectedStageId }"
              @click="selectedStageId = item.stage_id"
            >
              <div class="stage-item__top">
                <span>阶段 {{ item.stage_order }}</span>
                <el-tag size="small" :type="item.trend_label === '进步' ? 'success' : item.trend_label === '退步' ? 'danger' : 'info'">
                  {{ item.trend_label }}
                </el-tag>
              </div>
              <div class="stage-item__title">{{ item.stage_title }}</div>
              <div class="stage-item__meta">
                <span>{{ item.persona_label }}</span>
                <span>{{ Math.round((item.dynamic_score || 0) * 100) }}%</span>
              </div>
            </button>
          </div>
          <div v-else class="empty-help">
            <el-empty description="当前还没有阶段评价数据" />
            <div class="empty-help__text">请先在教师端创建阶段，并为这门课导入阶段数据，系统才会生成这里的结果。</div>
          </div>
        </section>
        <section class="detail-tabs">
          <el-tabs v-model="detailTab">
            <el-tab-pane label="结果概览" name="summary">
              <div class="tab-grid">
                <section v-if="selectedStage" class="panel-card soft-card">
                  <div class="soft-title">期末汇总结果</div>
                  <div class="stage-focus-grid">
                    <div class="stage-focus-card">
                      <span>覆盖阶段</span>
                      <strong>{{ termSummary.stage_count || 0 }}</strong>
                    </div>
                    <div class="stage-focus-card">
                      <span>期末参考分</span>
                      <strong>{{ Math.round((termSummary.final_score_reference || 0) * 100) }}%</strong>
                    </div>
                    <div class="stage-focus-card">
                      <span>进步次数</span>
                      <strong>{{ termSummary.progress_stages || 0 }}</strong>
                    </div>
                    <div class="stage-focus-card">
                      <span>回落次数</span>
                      <strong>{{ termSummary.regress_stages || 0 }}</strong>
                    </div>
                  </div>
                  <div class="stage-reason">{{ termSummary.final_reason_summary || "系统会把整个学期的阶段结果汇总成这里的期末参考。" }}</div>
                </section>

                <section v-if="finalPortraitDimensions.length" class="panel-card soft-card">
                  <div class="soft-title">期末五大类结果</div>
                  <PortraitRadarChart
                    title="期末五维雷达图"
                    subtitle="系统把整个学期的阶段结果汇总后，得到这里的期末五维画像。"
                    :items="finalPortraitDimensions"
                    accent="#2cb67d"
                    empty-text="当前还没有可展示的期末五维结果"
                  />
                  <div class="portrait-grid">
                    <div v-for="item in finalPortraitDimensions" :key="item.dimension_title" class="portrait-card">
                      <span>{{ item.dimension_title }}</span>
                      <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
                    </div>
                  </div>
                </section>

                <section v-if="selectedStage" class="panel-card soft-card">
                  <div class="soft-title">当前选中阶段</div>
                  <div class="stage-focus-grid">
                    <div class="stage-focus-card">
                      <span>学习投入</span>
                      <strong>{{ Math.round((selectedStage.engagement || 0) * 100) }}%</strong>
                    </div>
                    <div class="stage-focus-card">
                      <span>学习成效</span>
                      <strong>{{ Math.round((selectedStage.achievement || 0) * 100) }}%</strong>
                    </div>
                    <div class="stage-focus-card">
                      <span>学习习惯</span>
                      <strong>{{ Math.round((selectedStage.habit || 0) * 100) }}%</strong>
                    </div>
                    <div class="stage-focus-card">
                      <span>学习特征</span>
                      <strong>{{ Math.round((selectedStage.characteristic || 0) * 100) }}%</strong>
                    </div>
                  </div>
                  <div class="stage-reason">{{ selectedStage.reason_summary }}</div>
                </section>

                <section v-if="selectedStage" class="panel-card soft-card">
                  <div class="soft-title">五大类结果</div>
                  <PortraitRadarChart
                    title="当前阶段五维雷达图"
                    subtitle="这张图反映当前所选阶段在五大一级维度上的综合结果。"
                    :items="selectedStage.portrait_dimensions ?? []"
                    accent="#5c7cff"
                    empty-text="当前阶段还没有足够数据生成雷达图"
                  />
                  <div v-if="selectedStage.portrait_dimensions?.length" class="portrait-grid">
                    <div v-for="item in selectedStage.portrait_dimensions" :key="item.dimension_title" class="portrait-card">
                      <span>{{ item.dimension_title }}</span>
                      <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
                    </div>
                  </div>
                  <div v-else class="empty-help empty-help--compact">
                    <el-empty description="当前阶段还没形成五大类结果" :image-size="72" />
                    <div class="empty-help__text">当前阶段的数据还不够，或者老师还没有选好这门课要看的内容。</div>
                  </div>
                </section>

                <section v-if="selectedStage" class="panel-card soft-card">
                  <div class="soft-title">细项结果</div>
                  <div v-if="selectedStage.portrait_indicators?.length" class="indicator-stack">
                    <div
                      v-for="item in selectedStage.portrait_indicators.filter((row) => row.available)"
                      :key="item.title"
                      class="indicator-row"
                    >
                      <div>
                        <div class="indicator-row__title">{{ item.title }}</div>
                        <div class="indicator-row__meta">
                          {{ sourceTypeLabel(item.source_type) }} · {{ scoreSourceLabel(item.score_source) }} · 比重 {{ Number(item.weight || 0).toFixed(1) }}
                        </div>
                        <div v-if="item.formula_text" class="indicator-row__desc">{{ item.formula_text }}</div>
                        <div v-if="item.evidence_metrics?.length" class="indicator-row__evidence">
                          <span v-for="metric in item.evidence_metrics" :key="`${item.title}-${metric.metric_label}`">
                            {{ metric.metric_label }} {{ metric.metric_percent }}%
                          </span>
                        </div>
                      </div>
                      <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
                    </div>
                  </div>
                  <div v-else class="empty-help empty-help--compact">
                    <el-empty description="当前阶段还没有可显示的细项结果" :image-size="72" />
                    <div class="empty-help__text">系统会根据阶段数据、老师填写和学生补充内容自动生成这里的结果。</div>
                  </div>
                </section>
              </div>
            </el-tab-pane>

            <el-tab-pane label="老师填写" name="teacher">
              <div class="tab-grid">
                <section class="panel-card soft-card" v-loading="feedbackLoading">
                  <div class="soft-title">教师补充评价</div>
                  <el-alert
                    class="teacher-sync-alert"
                    type="info"
                    :closable="false"
                    title="这里填写的是老师对本阶段学生表现的判断。保存后，系统会立刻重算本阶段画像、五维结果和期末总画像。"
                  />
                  <el-form label-width="88px" size="small">
                    <el-form-item label="评价阶段">
                      <el-select v-model="selectedStageId" placeholder="选择阶段" style="width: 100%" :disabled="!stageHistory.length">
                        <el-option v-for="item in stageHistory" :key="item.stage_id" :label="item.stage_title" :value="item.stage_id" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="评价标签">
                      <el-select v-model="feedbackForm.feedback_tag" placeholder="选择标签" clearable style="width: 100%">
                        <el-option v-for="item in feedbackTagOptions" :key="item" :label="item" :value="item" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="快捷模板">
                      <div class="feedback-templates">
                        <el-button
                          v-for="item in feedbackQuickTemplates"
                          :key="item"
                          size="small"
                          @click="applyQuickTemplate(item)"
                        >
                          {{ item }}
                        </el-button>
                      </div>
                    </el-form-item>
                    <el-form-item label="教师评语">
                      <el-input v-model="feedbackForm.comment" type="textarea" :rows="4" placeholder="填写该学生在本阶段的补充评价和建议" />
                    </el-form-item>
                    <el-form-item>
                      <el-button type="primary" :loading="savingFeedback" @click="saveStageFeedback">保存教师评语</el-button>
                    </el-form-item>
                  </el-form>
                </section>

                <section class="panel-card soft-card">
                  <div class="soft-title">教师评语历史</div>
                  <div v-if="feedbackHistory.length" class="feedback-history-list">
                    <button
                      v-for="item in feedbackHistory"
                      :key="item.id"
                      type="button"
                      class="feedback-history-item"
                      @click="applyHistoryComment(item)"
                    >
                      <div class="feedback-history-item__top">
                        <span>{{ item.stage_title || `阶段 ${item.stage_id}` }}</span>
                        <el-tag size="small" type="info">{{ item.feedback_tag || "阶段评语" }}</el-tag>
                      </div>
                      <div class="feedback-history-item__comment">{{ item.comment || "（无文字内容）" }}</div>
                      <div class="feedback-history-item__meta">
                        {{ item.updated_by || "教师" }} · {{ new Date(item.updated_at).toLocaleString() }}
                      </div>
                    </button>
                  </div>
                  <div v-else class="empty-help empty-help--compact">
                    <el-empty description="暂无历史评语" :image-size="72" />
                    <div class="empty-help__text">保存过阶段评语后，这里会自动形成历史记录。</div>
                  </div>
                </section>

                <section class="panel-card soft-card" v-loading="teacherIndicatorLoading">
                  <div class="soft-title">老师补充填写</div>
                  <el-alert
                    class="teacher-sync-alert"
                    type="info"
                    :closable="false"
                    title="这部分用于补充系统自动看不出的高阶能力。保存后会直接进入阶段雷达图和最终画像结果。"
                  />
                  <div v-if="teacherIndicators.length" class="indicator-input-list">
                    <div v-for="item in teacherIndicators" :key="item.indicator_id" class="indicator-input-card">
                      <div class="indicator-input-card__head">
                        <div>
                          <div class="indicator-row__title">{{ item.indicator_title }}</div>
                          <div class="indicator-row__meta">{{ item.dimension_title }} · 比重 {{ Number(item.weight || 0).toFixed(1) }}</div>
                        </div>
                        <el-input-number v-model="item.score" :min="0" :max="1" :step="0.05" size="small" />
                      </div>
                      <el-input v-model="item.note" type="textarea" :rows="2" placeholder="简单写下老师观察到的情况" />
                    </div>
                    <div class="indicator-input-actions">
                      <el-button type="primary" :loading="savingTeacherIndicators" @click="saveTeacherIndicators">保存老师填写内容</el-button>
                    </div>
                  </div>
                  <div v-else class="empty-help empty-help--compact">
                    <el-empty description="这门课还没有启用需要老师填写的内容" :image-size="72" />
                    <div class="empty-help__text">先到“这门课看哪些内容”里启用老师填写类型的内容，这里才会出现。</div>
                  </div>
                </section>
              </div>
            </el-tab-pane>

            <el-tab-pane label="学习记录" name="records">
              <div class="tab-grid">
                <section class="panel-card soft-card">
                  <div class="soft-title">薄弱知识点</div>
                  <div class="weak-list">
                    <div v-for="item in weakPoints" :key="item.kp_id" class="weak-item">
                      <div>
                        <div class="weak-code">{{ item.code }}</div>
                        <div class="weak-title">{{ item.title }}</div>
                      </div>
                      <el-tag type="warning">{{ Math.round((item.mastery || 0) * 100) }}%</el-tag>
                    </div>
                  </div>
                </section>

                <section class="panel-card soft-card">
                  <div class="soft-title">知识点掌握详情</div>
                  <el-table :data="detail.mastery_map" size="small" max-height="320">
                    <el-table-column prop="code" label="编码" width="120" />
                    <el-table-column prop="title" label="知识点" min-width="180" />
                    <el-table-column prop="status" label="状态" width="100" />
                    <el-table-column prop="mastery" label="掌握度" width="100">
                      <template #default="{ row }">
                        {{ Math.round((row.mastery || 0) * 100) }}%
                      </template>
                    </el-table-column>
                    <el-table-column prop="reason_summary" label="依据" min-width="220" />
                  </el-table>
                </section>

                <section class="panel-card soft-card">
                  <div class="soft-title">行为轨迹</div>
                  <div class="timeline-list">
                    <div v-for="item in detail.behavior_timeline" :key="item.id" class="timeline-item">
                      <div class="timeline-type">{{ item.event_type }}</div>
                      <div class="timeline-time">{{ new Date(item.created_at).toLocaleString() }}</div>
                      <div class="timeline-json">{{ item.value_json }}</div>
                    </div>
                  </div>
                </section>

                <section class="panel-card soft-card">
                  <div class="soft-title">最近推荐记录</div>
                  <div class="timeline-list">
                    <div v-for="item in detail.recommendations" :key="item.id" class="timeline-item">
                      <div class="timeline-type">推荐到知识点 {{ item.target_kp_id }}</div>
                      <div class="timeline-time">{{ new Date(item.created_at).toLocaleString() }}</div>
                      <div class="timeline-json">{{ item.reason_summary }}</div>
                    </div>
                  </div>
                </section>

                <section class="activity-grid">
                  <el-card class="panel-card soft-card" shadow="never">
                    <div class="soft-title">最近练习记录</div>
                    <el-table :data="detail.recent_practice" size="small" max-height="260">
              <el-table-column prop="kp_id" label="知识点ID" width="110" />
              <el-table-column prop="question_id" label="题目ID" width="100" />
              <el-table-column prop="correct" label="结果" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.correct ? 'success' : 'danger'">{{ row.correct ? "正确" : "错误" }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="duration_ms" label="耗时(ms)" width="110" />
              <el-table-column prop="created_at" label="提交时间" min-width="180">
                <template #default="{ row }">
                  {{ new Date(row.created_at).toLocaleString() }}
                </template>
              </el-table-column>
                    </el-table>
                  </el-card>

                  <el-card class="panel-card soft-card" shadow="never">
                    <div class="soft-title">最近视频学习</div>
                    <el-table :data="detail.recent_video" size="small" max-height="260">
              <el-table-column prop="kp_id" label="知识点ID" width="110" />
              <el-table-column label="观看进度" min-width="180">
                <template #default="{ row }">
                  <div class="progress-cell">
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
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="completed" label="完成" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.completed ? 'success' : 'info'">{{ row.completed ? "已完成" : "进行中" }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="updated_at" label="更新时间" min-width="180">
                <template #default="{ row }">
                  {{ new Date(row.updated_at).toLocaleString() }}
                </template>
              </el-table-column>
                    </el-table>
                  </el-card>
                </section>
              </div>
            </el-tab-pane>
          </el-tabs>
        </section>
      </div>

      <div v-else class="detail-empty">
        <el-empty :description="emptyDetailMessage" />
        <el-alert
          class="detail-empty__tip"
          type="info"
          :closable="false"
          title="如果这里没有内容，请按这个顺序检查：先选课程，再创建阶段，再导入阶段数据，最后回来看学生详情。"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.student-detail-shell {
  display: grid;
  gap: 16px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.detail-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.detail-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-ink-soft);
}

.detail-grid {
  display: grid;
  gap: 16px;
}

.detail-empty {
  display: grid;
  gap: 14px;
}

.detail-empty__tip {
  margin-top: -6px;
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

.detail-tabs {
  display: grid;
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.tab-grid {
  display: grid;
  gap: 16px;
}

.activity-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.hero-card {
  padding: 22px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
  color: var(--app-ink);
  display: grid;
  gap: 10px;
}

.hero-label {
  font-size: 12px;
  color: #5c7da8;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 700;
}

.hero-name {
  font-size: 28px;
  font-weight: 800;
  color: #22395b;
}

.hero-meta {
  font-size: 14px;
  font-weight: 700;
  color: #35577f;
}

.hero-text {
  font-size: 14px;
  line-height: 1.7;
  color: #587596;
}

.hero-stats {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.hero-stat {
  padding: 12px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: none;
  display: grid;
  gap: 4px;
}

.hero-stat span {
  font-size: 12px;
  color: #6f86a3;
}

.hero-stat strong {
  font-size: 20px;
  font-weight: 800;
  color: #2a4d78;
}

.soft-card {
  border-radius: 20px;
}

.soft-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
  margin-bottom: 12px;
}

.stage-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.stage-item {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--app-border);
  background: #fcfdff;
  display: grid;
  gap: 8px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.stage-item:hover,
.stage-item--active {
  border-color: #bfd3ea;
  box-shadow: var(--app-shadow-soft);
  transform: translateY(-1px);
}

.stage-item__top,
.stage-item__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.stage-item__top {
  font-size: 12px;
  color: #567290;
}

.stage-item__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-ink);
}

.stage-item__meta {
  font-size: 12px;
  color: #66809a;
}

.stage-focus-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.stage-focus-card {
  padding: 14px;
  border-radius: 16px;
  background: #fcfdff;
  border: 1px solid var(--app-border);
  display: grid;
  gap: 6px;
}

.stage-focus-card span {
  font-size: 12px;
  color: #5b7797;
}

.stage-focus-card strong {
  font-size: 22px;
  font-weight: 800;
  color: var(--app-ink);
}

.stage-reason {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: #fcfdff;
  border: 1px solid var(--app-border);
  color: var(--app-ink);
  line-height: 1.7;
}

.portrait-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.portrait-card {
  padding: 14px;
  border-radius: 16px;
  background: #f8fbfd;
  border: 1px solid #dde7ef;
  display: grid;
  gap: 6px;
}

.portrait-card span {
  font-size: 12px;
  color: #5b7797;
}

.portrait-card strong {
  font-size: 22px;
  font-weight: 800;
  color: var(--app-ink);
}

.indicator-stack {
  display: grid;
  gap: 10px;
}

.indicator-row {
  padding: 12px 14px;
  border-radius: 16px;
  background: #f8fbfd;
  border: 1px solid #dde7ef;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.indicator-row__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
}

.indicator-row__meta {
  margin-top: 4px;
  font-size: 12px;
  color: #66809a;
}

.indicator-row__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #59708f;
}

.indicator-row__evidence {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.indicator-row__evidence span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #eef4ff;
  color: #5f76a8;
  font-size: 12px;
}

.feedback-templates {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.teacher-sync-alert {
  margin-bottom: 14px;
}

.feedback-history-list {
  display: grid;
  gap: 10px;
}

.feedback-history-item {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #dce7ef;
  background: #f8fbfd;
  text-align: left;
  display: grid;
  gap: 6px;
  cursor: pointer;
}

.feedback-history-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #597493;
}

.feedback-history-item__comment {
  font-size: 13px;
  color: var(--app-ink);
  line-height: 1.6;
}

.feedback-history-item__meta {
  font-size: 12px;
  color: #6b819c;
}

.weak-list,
.timeline-list {
  display: grid;
  gap: 10px;
}

.weak-item,
.timeline-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: #f8fbfd;
  border: 1px solid #dee7ef;
}

.weak-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.weak-code,
.timeline-type {
  font-size: 12px;
  color: #577493;
}

.weak-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
}

.timeline-time {
  margin-top: 4px;
  font-size: 12px;
  color: #6a829b;
}

.timeline-json {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-ink-soft);
  word-break: break-all;
}

.progress-cell {
  width: 100%;
}

@media (max-width: 1100px) {
  .activity-grid,
  .stage-focus-grid,
  .hero-stats {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .activity-grid,
  .stage-focus-grid,
  .hero-stats {
    grid-template-columns: 1fr;
  }
}
</style>
