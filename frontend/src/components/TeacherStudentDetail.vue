<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";
import PortraitRadarChart from "./PortraitRadarChart.vue";
import TeacherStudentHeaderBar from "./TeacherStudentHeaderBar.vue";
import TeacherStudentHeroCard from "./TeacherStudentHeroCard.vue";
import TeacherStudentStageList from "./TeacherStudentStageList.vue";

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
const recordTab = ref("overview");
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

const learningBehaviorOverview = computed(() => detail.value?.learning_behavior_overview ?? null);

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
        <TeacherStudentHeaderBar :students="students" :selected-user-id="selectedUserId" @update:selected-user-id="selectedUserId = $event" />
      </template>

      <div v-if="detail" class="detail-grid" v-loading="detailLoading">
        <TeacherStudentHeroCard :detail="detail" :selected-stage="selectedStage" />

        <TeacherStudentStageList :stage-history="stageHistory" :selected-stage-id="selectedStageId" @select="selectedStageId = $event" />
        <section class="detail-tabs">
          <el-tabs v-model="detailTab">
            <el-tab-pane label="学生情况" name="summary">
              <div class="tab-grid">
                <section v-if="selectedStage" class="panel-card soft-card">
                  <div class="soft-title">学期总结果</div>
                  <div class="stage-focus-grid">
                    <div class="stage-focus-card">
                      <span>覆盖阶段</span>
                      <strong>{{ termSummary.stage_count || 0 }}</strong>
                    </div>
                    <div class="stage-focus-card">
                      <span>学期参考分</span>
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
                  <div class="stage-reason">{{ termSummary.final_reason_summary || "系统会把整个学期的结果汇总到这里。" }}</div>
                </section>

                <section v-if="finalPortraitDimensions.length" class="panel-card soft-card">
                  <div class="soft-title">学期结果图</div>
                  <PortraitRadarChart
                    title="学期结果图"
                    subtitle="这张图是整个学期的汇总结果。"
                    :items="finalPortraitDimensions"
                    accent="#2cb67d"
                    empty-text="当前还没有可展示的学期结果"
                  />
                  <div class="portrait-grid">
                    <div v-for="item in finalPortraitDimensions" :key="item.dimension_title" class="portrait-card">
                      <span>{{ item.dimension_title }}</span>
                      <strong>{{ item.score == null ? "待补充" : `${Math.round(item.score * 100)}%` }}</strong>
                    </div>
                  </div>
                </section>

                <section v-if="selectedStage" class="panel-card soft-card">
                  <div class="soft-title">当前阶段</div>
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
                  <div class="soft-title">当前阶段结果图</div>
                  <PortraitRadarChart
                    title="当前阶段结果图"
                    subtitle="这张图反映当前阶段的大致情况。"
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
                    <el-empty description="当前阶段还没生成结果" :image-size="72" />
                    <div class="empty-help__text">当前阶段的数据还不够，或者老师还没有配置完成。</div>
                  </div>
                </section>

                <section v-if="selectedStage" class="panel-card soft-card">
                  <div class="soft-title">详细结果</div>
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
                    <el-empty description="当前阶段还没有可显示的详细结果" :image-size="72" />
                    <div class="empty-help__text">系统会根据阶段数据、老师填写和学生补充内容自动生成这里的结果。</div>
                  </div>
                </section>
              </div>
            </el-tab-pane>

            <el-tab-pane label="老师填写" name="teacher">
              <div class="tab-grid">
                <section class="panel-card soft-card" v-loading="feedbackLoading">
                  <div class="soft-title">老师评语</div>
                  <div class="teacher-sync-inline">
                    <span>填写说明</span>
                    <HoverTip content="这里填写老师对本阶段表现的判断。保存后，系统会同步更新结果。" />
                  </div>
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
                      <el-button type="primary" :loading="savingFeedback" @click="saveStageFeedback">保存评语</el-button>
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
                  <div class="soft-title">老师补充内容</div>
                  <div class="teacher-sync-inline">
                    <span>补充说明</span>
                    <HoverTip content="这部分用于补充系统自动看不出的情况。保存后会直接进入结果图。" />
                  </div>
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
                      <el-button type="primary" :loading="savingTeacherIndicators" @click="saveTeacherIndicators">保存</el-button>
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
                <section class="panel-card soft-card record-shell">
                  <div class="soft-title">学习行为与记录（拆分视图）</div>
                  <div class="teacher-sync-inline" style="margin-bottom: 10px">
                    <span>操作说明</span>
                    <HoverTip content="先看“总览”快速判断学习情况，再分别到“视频/练习/时间线/推荐/知识点”查看证据。所有原有功能都保留，只是重新归位，减少拥挤。" />
                  </div>
                  <el-tabs v-model="recordTab" class="record-tabs">
                    <el-tab-pane label="总览" name="overview">
                      <div class="record-overview-grid">
                        <el-card shadow="never" class="record-metric-card">
                          <div class="record-metric-card__label">登录（30天）</div>
                          <div class="record-metric-card__value">
                            {{ learningBehaviorOverview?.login_count_30d ?? 0 }}
                          </div>
                          <div class="record-metric-card__hint">覆盖天数 {{ learningBehaviorOverview?.login_days_30d ?? 0 }}</div>
                        </el-card>
                        <el-card shadow="never" class="record-metric-card">
                          <div class="record-metric-card__label">活跃天数（14天）</div>
                          <div class="record-metric-card__value">
                            {{ learningBehaviorOverview?.active_days_14d ?? 0 }}
                          </div>
                          <div class="record-metric-card__hint">连续 {{ learningBehaviorOverview?.consecutive_days_14d ?? 0 }} 天</div>
                        </el-card>
                        <el-card shadow="never" class="record-metric-card">
                          <div class="record-metric-card__label">学习时长（14天）</div>
                          <div class="record-metric-card__value">
                            {{ Math.round((learningBehaviorOverview?.study_duration_minutes_14d ?? 0) as number) }} 分钟
                          </div>
                          <div class="record-metric-card__hint">视频+练习+小测时长合计</div>
                        </el-card>
                        <el-card shadow="never" class="record-metric-card">
                          <div class="record-metric-card__label">视频完成率（30天）</div>
                          <div class="record-metric-card__value">
                            {{ Math.round(((learningBehaviorOverview?.avg_video_completion_30d ?? 0) as number) * 100) }}%
                          </div>
                          <div class="record-metric-card__hint">
                            开始 {{ learningBehaviorOverview?.video_started_30d ?? 0 }} · 完成 {{ learningBehaviorOverview?.video_completed_30d ?? 0 }}
                          </div>
                        </el-card>
                        <el-card shadow="never" class="record-metric-card">
                          <div class="record-metric-card__label">练习正确率（30天）</div>
                          <div class="record-metric-card__value">
                            {{ Math.round(((learningBehaviorOverview?.practice_accuracy_30d ?? 0) as number) * 100) }}%
                          </div>
                          <div class="record-metric-card__hint">练习次数 {{ learningBehaviorOverview?.practice_attempts_30d ?? 0 }}</div>
                        </el-card>
                        <el-card shadow="never" class="record-metric-card record-metric-card--wide">
                          <div class="record-metric-card__label">最近行为类型（30天 Top10）</div>
                          <div v-if="(learningBehaviorOverview?.top_event_types_30d?.length ?? 0) > 0" class="record-chips">
                            <span v-for="row in learningBehaviorOverview.top_event_types_30d" :key="row.event_type">
                              {{ row.event_type }} {{ row.count }}
                            </span>
                          </div>
                          <div v-else class="record-metric-card__hint">暂无可汇总的行为类型</div>
                        </el-card>
                      </div>
                    </el-tab-pane>

                    <el-tab-pane label="视频学习" name="video">
                      <div class="teacher-sync-inline">
                        <span>功能范围</span>
                        <HoverTip content="查看最近视频进度、是否完成、更新时间；用于判断是否只打开不学习、是否卡在同一知识点视频。" />
                      </div>
                      <el-table :data="detail.recent_video" size="small" max-height="420">
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
                    </el-tab-pane>

                    <el-tab-pane label="练习与小测" name="practice">
                      <div class="teacher-sync-inline">
                        <span>功能范围</span>
                        <HoverTip content="查看最近练习作答、小测记录与耗时；用于判断练习量、正确率与耗时是否异常。" />
                      </div>
                      <div class="record-split-grid">
                        <el-card class="panel-card soft-card" shadow="never">
                          <div class="soft-title">最近练习记录</div>
                          <el-table :data="detail.recent_practice" size="small" max-height="360">
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
                          <div class="soft-title">最近小测记录</div>
                          <el-table :data="detail.recent_quiz" size="small" max-height="360">
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
                              <template #default="{ row }">
                                {{ new Date(row.created_at).toLocaleString() }}
                              </template>
                            </el-table-column>
                          </el-table>
                        </el-card>
                      </div>
                    </el-tab-pane>

                    <el-tab-pane label="行为时间线" name="timeline">
                      <div class="teacher-sync-inline">
                        <span>功能范围</span>
                        <HoverTip content="查看系统自动写入的行为事件原始记录（最多30条）。用于核对：登录、资源访问、练习提交、视频进度、图谱查看、推荐点击等是否真实发生。" />
                      </div>
                      <div class="timeline-list">
                        <div v-for="item in detail.behavior_timeline" :key="item.id" class="timeline-item">
                          <div class="timeline-type">{{ item.event_type }}</div>
                          <div class="timeline-time">{{ new Date(item.created_at).toLocaleString() }}</div>
                          <div class="timeline-json">{{ item.value_json }}</div>
                        </div>
                      </div>
                    </el-tab-pane>

                    <el-tab-pane label="推荐记录" name="reco">
                      <div class="teacher-sync-inline">
                        <span>功能范围</span>
                        <HoverTip content="查看系统推荐到哪些知识点、推荐理由与发生时间；用于核对推荐链路是否推动学习。" />
                      </div>
                      <div class="timeline-list">
                        <div v-for="item in detail.recommendations" :key="item.id" class="timeline-item">
                          <div class="timeline-type">推荐到知识点 {{ item.target_kp_id }}</div>
                          <div class="timeline-time">{{ new Date(item.created_at).toLocaleString() }}</div>
                          <div class="timeline-json">{{ item.reason_summary }}</div>
                        </div>
                      </div>
                    </el-tab-pane>

                    <el-tab-pane label="知识点" name="kps">
                      <div class="teacher-sync-inline">
                        <span>功能范围</span>
                        <HoverTip content="查看知识点掌握度、薄弱点与系统依据；用于定位学生卡在哪些知识点。" />
                      </div>
                      <div class="record-split-grid">
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
                          <div class="soft-title">知识点情况</div>
                          <el-table :data="detail.mastery_map" size="small" max-height="420">
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
                      </div>
                    </el-tab-pane>
                  </el-tabs>
                </section>
              </div>
            </el-tab-pane>
          </el-tabs>
        </section>
      </div>

      <div v-else class="detail-empty">
        <el-empty :description="emptyDetailMessage" />
        <div class="teacher-sync-inline">
          <span>排查提示</span>
          <HoverTip content="如果这里没有内容，请按这个顺序检查：先选课程，再创建阶段，再导入阶段数据，最后回来看学生详情。" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.student-detail-shell {
  display: grid;
  gap: 16px;
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

.record-shell :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.record-overview-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.record-metric-card {
  border-radius: 16px;
  border: 1px solid var(--app-border);
  box-shadow: none;
}

.record-metric-card--wide {
  grid-column: 1 / -1;
}

.record-metric-card__label {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.record-metric-card__value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 800;
  color: var(--app-ink);
}

.record-metric-card__hint {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-ink-soft);
}

.record-chips {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.record-chips span {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #dbe6f2;
  background: #f6faff;
  color: #46658b;
  font-size: 12px;
  font-weight: 700;
}

.record-split-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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

.detail-grid :deep(.el-form-item__label) {
  font-weight: 700;
  color: #48627f;
}

.detail-grid :deep(.el-textarea__inner),
.detail-grid :deep(.el-input__wrapper),
.detail-grid :deep(.el-input-number),
.detail-grid :deep(.el-select__wrapper) {
  border-radius: 14px;
}

.detail-grid :deep(.el-textarea__inner) {
  min-height: 112px;
  line-height: 1.7;
}

.detail-grid :deep(.el-button + .el-button) {
  margin-left: 10px;
}

.detail-grid :deep(.el-table) {
  --el-table-border-color: #e1eaf2;
  --el-table-header-bg-color: #f7faff;
  --el-table-row-hover-bg-color: #f5f9ff;
  border-radius: 16px;
  overflow: hidden;
}

.detail-grid :deep(.el-table th.el-table__cell) {
  font-weight: 700;
  color: #4f6883;
}

.detail-grid :deep(.el-table td.el-table__cell) {
  color: var(--app-ink);
}

.detail-grid :deep(.el-tabs__item) {
  height: 38px;
  font-weight: 700;
}

.detail-grid :deep(.el-tabs__item.is-active) {
  color: var(--app-primary);
}

.teacher-sync-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: #637995;
  font-size: 13px;
  font-weight: 700;
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
  .stage-focus-grid {
    grid-template-columns: 1fr 1fr;
  }

  .record-overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .record-split-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .activity-grid,
  .stage-focus-grid {
    grid-template-columns: 1fr;
  }

  .record-overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
