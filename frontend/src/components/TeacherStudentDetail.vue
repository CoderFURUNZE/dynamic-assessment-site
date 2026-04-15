<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";
import PortraitRadarChart from "./PortraitRadarChart.vue";
import TeacherStudentHeaderBar from "./TeacherStudentHeaderBar.vue";

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
const teacherToolsExpanded = ref(false);
const detailTab = ref("records");
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
const teacherIndicators = ref<
  Array<{
    dimension_id: number;
    dimension_title: string;
    indicator_id: number;
    indicator_title: string;
    indicator_code: string;
    weight: number;
    score: number | null;
    note: string;
  }>
>([]);

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

function percent(value?: number | null) {
  return Math.round((Number(value ?? 0) || 0) * 100);
}

function eventTypeLabel(eventType?: string) {
  const key = String(eventType || "").trim();
  const map: Record<string, string> = {
    practice_submit: "提交练习",
    login: "登录学习",
    resource_visit: "访问资源",
    note_create: "创建笔记",
    video_progress: "观看视频",
    quiz_submit: "提交测验",
    graph_view: "查看知识图谱",
    recommendation_click: "点击推荐",
    recommend_click: "点击推荐内容",
    course_view: "查看课程页",
    resource_download: "下载资源",
  };
  return map[key] || key || "学习行为";
}

function parseJsonSafely(raw: unknown) {
  if (typeof raw !== "string") return typeof raw === "object" && raw ? raw : null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function formatDateTime(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
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
const previousStage = computed<StageHistoryItem | null>(() => {
  if (!selectedStage.value) return null;
  const currentIndex = stageHistory.value.findIndex((item) => item.stage_id === selectedStage.value?.stage_id);
  if (currentIndex <= 0) return null;
  return stageHistory.value[currentIndex - 1] ?? null;
});

const learningBehaviorOverview = computed(() => detail.value?.learning_behavior_overview ?? null);

function riskTone(level?: string) {
  const raw = String(level || "");
  if (raw.includes("高")) return "danger";
  if (raw.includes("中") || raw.includes("风险")) return "warning";
  return "success";
}

function statusLabel(level?: string, persona?: string) {
  const tone = riskTone(level);
  if (tone === "danger") return "高风险";
  if (tone === "warning") return "重点关注";
  if (String(persona || "").includes("拖延")) return "需持续跟进";
  return "平稳发展";
}

function scoreTone(value: number) {
  if (value < 0.35) return "danger";
  if (value < 0.65) return "warning";
  return "success";
}

function trendMeta(current?: number, previous?: number) {
  const currentValue = Number(current ?? 0);
  const previousValue = Number(previous ?? currentValue);
  const diff = currentValue - previousValue;
  const tone = scoreTone(currentValue);
  if (diff < -0.08) return { symbol: "↓", label: "需关注", tone: "danger" };
  if (diff < -0.03) return { symbol: "↓", label: "略低", tone: "warning" };
  if (diff > 0.08) return { symbol: "↑", label: "较好", tone: "success" };
  if (diff > 0.03) return { symbol: "↑", label: tone === "success" ? "较好" : "稳定" , tone: tone === "success" ? "success" : "neutral" };
  if (tone === "danger") return { symbol: "→", label: "需关注", tone: "danger" };
  if (tone === "warning") return { symbol: "→", label: "略低", tone: "warning" };
  return { symbol: "→", label: "稳定", tone: "neutral" };
}

const studentProfile = computed(() => detail.value?.profile ?? {});
const studentName = computed(() => detail.value?.student?.full_name || detail.value?.student?.username || "未命名学生");
const currentRiskTone = computed(() => riskTone(studentProfile.value?.risk_level));
const currentStatusLabel = computed(() => statusLabel(studentProfile.value?.risk_level, studentProfile.value?.persona_label));

const summarySentence = computed(() => {
  const mastery = percent(studentProfile.value?.course_mastery);
  const reason = String(selectedStage.value?.reason_summary || studentProfile.value?.reason_summary || "").trim();
  if (reason) return reason;
  if (currentRiskTone.value === "danger") return `当前存在明显风险，课程掌握度 ${mastery}%，建议优先干预。`;
  if (currentRiskTone.value === "warning") return `学习状态存在波动，课程掌握度 ${mastery}%，建议持续关注。`;
  return `学习状态稳定，掌握度 ${mastery}%，暂无明显风险。`;
});

const summarySupportText = computed(() => {
  const stageTitle = selectedStage.value?.stage_title || studentProfile.value?.current_stage_title || "当前阶段";
  if (currentRiskTone.value === "danger") return `${stageTitle} 表现偏弱，建议尽快查看最近练习与投入情况。`;
  if (currentRiskTone.value === "warning") return `${stageTitle} 有轻微波动，适合通过补练和复盘持续跟进。`;
  return `${stageTitle} 状态整体平稳，可继续保持当前节奏并定期复盘。`;
});

const metricCards = computed(() => {
  const profile = studentProfile.value;
  const prev = previousStage.value;
  return [
    {
      key: "dynamic",
      label: "动态评分",
      value: percent(profile.dynamic_score),
      trend: trendMeta(profile.dynamic_score, prev?.dynamic_score),
      tone: scoreTone(profile.dynamic_score || 0),
    },
    {
      key: "mastery",
      label: "课程掌握",
      value: percent(profile.course_mastery),
      trend: trendMeta(profile.course_mastery, prev?.course_mastery),
      tone: scoreTone(profile.course_mastery || 0),
    },
    {
      key: "engagement",
      label: "学习投入",
      value: percent((selectedStage.value?.engagement ?? profile.engagement) || 0),
      trend: trendMeta(selectedStage.value?.engagement ?? profile.engagement, prev?.engagement),
      tone: scoreTone((selectedStage.value?.engagement ?? profile.engagement) || 0),
    },
    {
      key: "achievement",
      label: "学习成效",
      value: percent((selectedStage.value?.achievement ?? profile.achievement) || 0),
      trend: trendMeta(selectedStage.value?.achievement ?? profile.achievement, prev?.achievement),
      tone: scoreTone((selectedStage.value?.achievement ?? profile.achievement) || 0),
    },
  ];
});

const riskPoints = computed(() => {
  const raw = String(selectedStage.value?.reason_summary || studentProfile.value?.reason_summary || "").trim();
  const segments = raw
    .split(/[，。；]/)
    .map((item) => item.replace(/^主要判断[:：]/, "").trim())
    .filter(Boolean);
  const weak = weakPoints.value.slice(0, 2).map((item: any) => `${item.title} 掌握偏弱`);
  const fallback = currentRiskTone.value === "success" ? ["当前未发现明显风险点"] : ["学习节奏需要持续观察"];
  return [...segments, ...weak, ...fallback].slice(0, 3);
});

const riskSuggestion = computed(() => {
  if (currentRiskTone.value === "danger") return "建议立即查看最近练习与作业完成情况，并优先安排补弱练习。";
  if (currentRiskTone.value === "warning") return "建议增加练习频率，持续观察阶段变化和课堂投入。";
  return "建议保持当前学习节奏，并定期复盘薄弱知识点。";
});

const actionSuggestions = computed(() => {
  if (currentRiskTone.value === "danger") {
    return ["优先复习薄弱知识点", "本周追加 1 次针对性练习", "重点关注作业完成与练习正确率"];
  }
  if (currentRiskTone.value === "warning") {
    return ["保持当前学习节奏", "补做 1 次薄弱知识点练习", "继续观察近一周学习投入变化"];
  }
  return ["继续保持当前学习节奏", "定期复习薄弱知识点", "本周可追加 1 次针对性练习"];
});

const learningRecordOverviewCards = computed(() => [
  {
    key: "login",
    label: "最近 30 天登录次数",
    value: learningBehaviorOverview.value?.login_count_30d ?? 0,
    hint: `覆盖天数 ${learningBehaviorOverview.value?.login_days_30d ?? 0}`,
  },
  {
    key: "active",
    label: "最近 14 天活跃天数",
    value: learningBehaviorOverview.value?.active_days_14d ?? 0,
    hint: `连续 ${learningBehaviorOverview.value?.consecutive_days_14d ?? 0} 天`,
  },
  {
    key: "duration",
    label: "最近 14 天学习时长",
    value: `${Math.round((learningBehaviorOverview.value?.study_duration_minutes_14d ?? 0) as number)} 分钟`,
    hint: "视频、练习、测验合计",
  },
  {
    key: "completion",
    label: "最近 30 天任务完成率",
    value: `${percent(learningBehaviorOverview.value?.avg_video_completion_30d)}%`,
    hint: `开始 ${learningBehaviorOverview.value?.video_started_30d ?? 0} 次，完成 ${learningBehaviorOverview.value?.video_completed_30d ?? 0} 次`,
  },
]);

const practiceSummaryItems = computed(() => [
  { label: "练习次数", value: learningBehaviorOverview.value?.practice_attempts_30d ?? 0 },
  { label: "练习正确率", value: `${percent(learningBehaviorOverview.value?.practice_accuracy_30d)}%` },
  { label: "测验通过数", value: (detail.value?.recent_quiz ?? []).filter((item: any) => item.passed).length },
]);

const behaviorTimelineRecords = computed(() =>
  (detail.value?.behavior_timeline ?? []).map((item: any) => {
    const payload = parseJsonSafely(item.value_json);
    const descriptionMap: Record<string, string> = {
      login: "进入系统开始学习",
      resource_visit: "查看课程资源或材料",
      note_create: "记录学习笔记",
      recommend_click: "查看系统推荐内容",
      recommendation_click: "查看系统推荐内容",
      graph_view: "查看知识图谱",
      course_view: "进入课程页面",
      resource_download: "下载学习资源",
      practice_submit: "完成一次练习提交",
      quiz_submit: "完成一次测验提交",
      video_progress: "更新视频观看进度",
    };
    const extras: string[] = [];
    if (payload && typeof payload === "object") {
      const typedPayload = payload as Record<string, unknown>;
      if (typedPayload.kp_id) extras.push(`知识点 ${typedPayload.kp_id}`);
      if (typedPayload.resource_id) extras.push(`资源 ${typedPayload.resource_id}`);
      if (typedPayload.question_id) extras.push(`题目 ${typedPayload.question_id}`);
      if (typedPayload.duration_ms) extras.push(`耗时 ${typedPayload.duration_ms}ms`);
      if (typedPayload.score != null) extras.push(`得分 ${Math.round(Number(typedPayload.score) * 100)}%`);
    }
    return {
      id: item.id,
      title: eventTypeLabel(item.event_type),
      description: descriptionMap[item.event_type] || "记录了一次学习行为",
      time: formatDateTime(item.created_at),
      extra: extras.join(" · ") || "暂无补充信息",
    };
  })
);

const changeEvents = computed(() => {
  const events: Array<{ key: string; title: string; summary: string; value: string; tone: string }> = [];
  const activeDays = Number(learningBehaviorOverview.value?.active_days_14d ?? 0);
  if (activeDays > 0) {
    events.push({
      key: "active",
      title: "活跃度变化",
      summary: activeDays >= 7 ? "最近两周活跃度较稳定" : "最近两周活跃度一般，建议继续观察",
      value: `${activeDays} 天`,
      tone: activeDays >= 7 ? "success" : "warning",
    });
  }
  const duration = Number(learningBehaviorOverview.value?.study_duration_minutes_14d ?? 0);
  if (duration > 0) {
    events.push({
      key: "duration",
      title: "学习时长变化",
      summary: duration >= 120 ? "最近两周学习时长较充足" : "最近两周学习时长偏少",
      value: `${Math.round(duration)} 分钟`,
      tone: duration >= 120 ? "success" : "warning",
    });
  }
  const accuracy = Number(learningBehaviorOverview.value?.practice_accuracy_30d ?? 0);
  if (accuracy > 0) {
    events.push({
      key: "accuracy",
      title: "正确率变化",
      summary: accuracy >= 0.6 ? "练习正确率整体稳定" : "练习正确率偏低，建议复习薄弱点",
      value: `${percent(accuracy)}%`,
      tone: accuracy >= 0.6 ? "success" : "danger",
    });
  }
  const mastery = Number(studentProfile.value?.course_mastery ?? 0);
  if (mastery > 0) {
    events.push({
      key: "mastery",
      title: "掌握度变化",
      summary: mastery >= 0.6 ? "课程掌握度处于较好区间" : "课程掌握度仍需提升",
      value: `${percent(mastery)}%`,
      tone: mastery >= 0.6 ? "success" : mastery >= 0.35 ? "warning" : "danger",
    });
  }
  return events.slice(0, 4);
});

const videoProgressList = computed(() =>
  (detail.value?.recent_video ?? []).map((item: any) => {
    const progress =
      Number(item.duration_seconds || 0) > 0
        ? Math.round(Math.min(100, (Number(item.watched_seconds || 0) / Number(item.duration_seconds || 1)) * 100))
        : 0;
    return {
      ...item,
      title: item.title || item.kp_title || `知识点 ${item.kp_id}`,
      subtitle: item.code || item.kp_code || `KP-${item.kp_id}`,
      progress,
    };
  })
);

const recommendationCards = computed(() =>
  (detail.value?.recommendations ?? []).map((item: any) => ({
    ...item,
    title: item.target_kp_title || item.title || `推荐知识点 ${item.target_kp_id}`,
    source: item.source_type ? sourceTypeLabel(item.source_type) : "",
  }))
);

function jumpToRecords() {
  detailTab.value = "records";
}

function markAttention() {
  ElMessage.info(`已将 ${studentName.value} 标记为重点关注`);
}

function assignPractice() {
  ElMessage.info(`可继续接入“布置练习”流程，当前已为 ${studentName.value} 预留操作入口`);
}

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
    const res = await api.get(`/portrait/teacher-input?course_id=${courseId}&user_id=${selectedUserId.value}&stage_id=${selectedStageId.value}`);
    teacherIndicators.value = res.data?.items ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载老师型指标失败");
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
    ElMessage.success("教师补充评价已保存，系统已重新计算该阶段画像");
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
    ElMessage.success("老师补充指标已保存，系统已同步更新阶段画像和总画像");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存老师型指标失败");
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
    <el-card class="panel-card detail-card" shadow="never" v-loading="loading">
      <template #header>
        <TeacherStudentHeaderBar
          :students="students"
          :selected-user-id="selectedUserId"
          @update:selected-user-id="selectedUserId = $event"
        />
      </template>

      <div v-if="detail" class="detail-layout" v-loading="detailLoading">
        <section class="core-panel" :class="`core-panel--${currentRiskTone}`">
          <div class="core-panel__main">
            <div class="section-kicker">学生核心信息</div>
            <div class="core-panel__headline">
              <h2>{{ studentName }}</h2>
              <span class="status-pill" :class="`status-pill--${currentRiskTone}`">{{ currentStatusLabel }}</span>
            </div>
            <p class="core-panel__summary">{{ summarySentence }}</p>
            <p class="core-panel__support">{{ summarySupportText }}</p>
            <div class="core-panel__meta">
              <span>{{ studentProfile.persona_label || "学习画像待生成" }}</span>
              <span>当前阶段：{{ selectedStage?.stage_title || studentProfile.current_stage_title || "暂无阶段数据" }}</span>
            </div>
          </div>
          <div class="core-panel__side">
            <div class="core-panel__actions">
              <el-button type="primary" @click="jumpToRecords">查看学习记录</el-button>
              <el-button @click="assignPractice">布置练习</el-button>
              <el-button @click="markAttention">标记关注</el-button>
            </div>
            <div class="core-panel__side-note">建议先查看学习记录，再决定是否补练或标记重点关注。</div>
          </div>
        </section>

        <section class="metric-section">
          <div v-for="item in metricCards" :key="item.key" class="metric-card" :class="`metric-card--${item.tone}`">
            <div class="metric-card__label">{{ item.label }}</div>
            <div class="metric-card__value">{{ item.value }}%</div>
            <div class="metric-card__trend" :class="`metric-card__trend--${item.trend.tone}`">
              <span>{{ item.trend.symbol }}</span>
              <span>{{ item.trend.label }}</span>
            </div>
          </div>
        </section>

        <section class="analysis-grid">
          <section class="analysis-card">
            <div class="section-kicker">当前分析</div>
            <div class="section-title">学习状态分析</div>
            <div class="risk-list">
              <div v-for="(item, index) in riskPoints" :key="`${item}-${index}`" class="risk-list__item">
                <span class="risk-list__dot" :class="`risk-list__dot--${currentRiskTone}`"></span>
                <span>{{ item }}</span>
              </div>
            </div>
            <div class="analysis-note">
              <div class="analysis-note__label">当前判断</div>
              <div>{{ currentStatusLabel }}，{{ summarySentence }}</div>
            </div>
            <div class="analysis-note">
              <div class="analysis-note__label">简要原因</div>
              <div>{{ selectedStage?.reason_summary || studentProfile.reason_summary || "当前暂无系统生成的原因摘要。" }}</div>
            </div>
            <div class="analysis-note analysis-note--accent">
              <div class="analysis-note__label">建议老师这样做</div>
              <div class="action-suggestion">
                <div class="action-suggestion__summary">{{ riskSuggestion }}</div>
                <div class="action-suggestion__list">
                  <div v-for="item in actionSuggestions" :key="item" class="action-suggestion__item">
                    <span class="action-suggestion__dot"></span>
                    <span>{{ item }}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="analysis-card" :class="{ 'analysis-card--compact': !stageHistory.length }">
            <div class="section-kicker">学习变化</div>
            <div class="section-title">阶段变化</div>
            <div v-if="stageHistory.length" class="stage-timeline">
              <button
                v-for="item in stageHistory"
                :key="item.stage_id"
                type="button"
                class="stage-node"
                :class="{ 'is-active': item.stage_id === selectedStageId }"
                @click="selectedStageId = item.stage_id"
              >
                <div class="stage-node__top">
                  <span>{{ item.stage_title }}</span>
                  <strong>{{ percent(item.course_mastery) }}%</strong>
                </div>
                <div class="stage-node__meta">
                  <span>{{ item.persona_label || "阶段画像" }}</span>
                  <span>{{ item.trend_label || formatDateTime(item.updated_at) }}</span>
                </div>
                <div class="stage-node__bar">
                  <span :style="{ width: `${percent(item.course_mastery)}%` }"></span>
                </div>
              </button>
            </div>
            <div v-else class="empty-strip empty-strip--stage">
              <div class="empty-strip__title">暂无阶段评价数据</div>
              <div class="empty-strip__desc">请先完成数据导入或执行阶段计算</div>
            </div>
          </section>
        </section>

        <section class="detail-tabs">
          <el-tabs v-model="detailTab">
            <el-tab-pane label="学习记录" name="records">
              <section class="tab-panel">
                <div class="section-kicker">学习记录</div>
                <div class="section-title">最近行为、练习与变化</div>
                <div class="tab-tip">
                  <span>使用说明</span>
                  <HoverTip content="先看总览快速判断学习状态，再切换到视频、练习、时间线、推荐和知识点查看具体证据。" />
                </div>
                <div class="record-overview-grid record-overview-grid--compact">
                  <el-card v-for="item in learningRecordOverviewCards" :key="item.key" shadow="never" class="record-metric-card">
                    <div class="record-metric-card__label">{{ item.label }}</div>
                    <div class="record-metric-card__value">{{ item.value }}</div>
                    <div class="record-metric-card__hint">{{ item.hint }}</div>
                  </el-card>
                </div>
                <el-tabs v-model="recordTab" class="record-tabs">
                  <el-tab-pane label="行为记录" name="overview">
                    <div v-if="behaviorTimelineRecords.length" class="behavior-timeline">
                      <div v-for="item in behaviorTimelineRecords" :key="item.id" class="behavior-item">
                        <div class="behavior-item__dot"></div>
                        <div class="behavior-item__content">
                          <div class="behavior-item__top">
                            <div class="behavior-item__title">{{ item.title }}</div>
                            <div class="behavior-item__time">{{ item.time }}</div>
                          </div>
                          <div class="behavior-item__desc">{{ item.description }}</div>
                          <div class="behavior-item__extra">{{ item.extra }}</div>
                        </div>
                      </div>
                    </div>
                    <div v-else class="empty-strip empty-strip--panel">
                      <div class="empty-strip__title">暂无行为记录</div>
                      <div class="empty-strip__desc">系统暂未采集到可展示的学习行为。</div>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="练习记录" name="practice">
                    <div class="practice-stack">
                      <div class="practice-summary practice-summary--hero">
                        <div v-for="item in practiceSummaryItems" :key="item.label" class="practice-summary__item">
                          <span>{{ item.label }}</span>
                          <strong>{{ item.value }}</strong>
                        </div>
                      </div>
                      <section class="record-panel">
                        <div class="record-panel__head">
                          <div>
                            <div class="record-panel__title">最近练习记录</div>
                            <div class="record-panel__desc">查看最近完成的练习作答情况和提交时间。</div>
                          </div>
                        </div>
                        <el-table :data="detail.recent_practice" size="small" max-height="320" class="record-table">
                          <el-table-column prop="kp_id" label="知识点" width="110" />
                          <el-table-column prop="question_id" label="题目" width="100" />
                          <el-table-column prop="correct" label="结果" width="90">
                            <template #default="{ row }">
                              <el-tag :type="row.correct ? 'success' : 'danger'">{{ row.correct ? "正确" : "错误" }}</el-tag>
                            </template>
                          </el-table-column>
                          <el-table-column prop="duration_ms" label="耗时(ms)" width="110" />
                          <el-table-column prop="created_at" label="提交时间" min-width="180">
                            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                          </el-table-column>
                        </el-table>
                      </section>

                      <section class="record-panel">
                        <div class="record-panel__head">
                          <div>
                            <div class="record-panel__title">最近测验记录</div>
                            <div class="record-panel__desc">重点关注测验通过情况、得分和耗时表现。</div>
                          </div>
                        </div>
                        <el-table :data="detail.recent_quiz" size="small" max-height="320" class="record-table">
                          <el-table-column prop="kp_id" label="知识点" width="110" />
                          <el-table-column prop="score" label="得分" width="90">
                            <template #default="{ row }">{{ percent(row.score) }}%</template>
                          </el-table-column>
                          <el-table-column prop="passed" label="通过" width="90">
                            <template #default="{ row }">
                              <el-tag :type="row.passed ? 'success' : 'info'">{{ row.passed ? "通过" : "未通过" }}</el-tag>
                            </template>
                          </el-table-column>
                          <el-table-column prop="duration_ms" label="耗时(ms)" width="110" />
                          <el-table-column prop="created_at" label="提交时间" min-width="180">
                            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                          </el-table-column>
                        </el-table>
                      </section>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="变化轨迹" name="timeline">
                    <div v-if="changeEvents.length" class="change-track">
                      <div v-for="item in changeEvents" :key="item.key" class="change-track__item" :class="`change-track__item--${item.tone}`">
                        <div class="change-track__top">
                          <div class="change-track__title">{{ item.title }}</div>
                          <div class="change-track__value">{{ item.value }}</div>
                        </div>
                        <div class="change-track__summary">{{ item.summary }}</div>
                      </div>
                    </div>
                    <div v-else class="empty-strip empty-strip--panel">
                      <div class="empty-strip__title">暂无显著变化记录</div>
                      <div class="empty-strip__desc">最近学习状态整体平稳。</div>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="视频学习" name="video">
                    <div v-if="videoProgressList.length" class="video-progress-list">
                      <div v-for="item in videoProgressList" :key="`${item.kp_id}-${item.updated_at}`" class="video-progress-item">
                        <div class="video-progress-item__meta">
                          <div>
                            <div class="video-progress-item__title">{{ item.title }}</div>
                            <div class="video-progress-item__code">{{ item.subtitle }}</div>
                          </div>
                          <div class="video-progress-item__status">
                            <strong>{{ item.progress }}%</strong>
                            <el-tag :type="item.completed ? 'success' : 'info'">{{ item.completed ? "已完成" : "进行中" }}</el-tag>
                          </div>
                        </div>
                        <div class="progress-cell">
                          <el-progress :percentage="item.progress" :stroke-width="8" />
                        </div>
                        <div class="video-progress-item__time">更新时间：{{ formatDateTime(item.updated_at) }}</div>
                      </div>
                    </div>
                    <div v-else class="empty-strip empty-strip--panel">
                      <div class="empty-strip__title">暂无视频学习记录</div>
                      <div class="empty-strip__desc">最近没有可展示的视频观看进度。</div>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="推荐记录" name="reco">
                    <div v-if="recommendationCards.length" class="recommendation-list">
                      <div v-for="item in recommendationCards" :key="item.id" class="recommendation-item">
                        <div class="recommendation-item__top">
                          <div>
                            <div class="recommendation-item__title">{{ item.title }}</div>
                            <div v-if="item.source" class="recommendation-item__source">推荐来源：{{ item.source }}</div>
                          </div>
                          <div class="timeline-time">{{ formatDateTime(item.created_at) }}</div>
                        </div>
                        <div class="recommendation-item__reason">{{ item.reason_summary || "系统根据当前学习状态生成推荐。" }}</div>
                      </div>
                    </div>
                    <div v-else class="empty-strip empty-strip--panel">
                      <div class="empty-strip__title">暂无推荐记录</div>
                      <div class="empty-strip__desc">系统还没有生成最近推荐。</div>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="知识点掌握" name="kps">
                    <div class="record-split-grid">
                      <section class="record-panel record-panel--flat">
                        <div class="record-panel__head">
                          <div>
                            <div class="record-panel__title">薄弱知识点 Top6</div>
                            <div class="record-panel__desc">优先关注掌握度最低的知识点。</div>
                          </div>
                        </div>
                        <div class="weak-list">
                          <div v-for="item in weakPoints" :key="item.kp_id" class="weak-item">
                            <div>
                              <div class="weak-code">{{ item.code }}</div>
                              <div class="weak-title">{{ item.title }}</div>
                            </div>
                            <div class="weak-item__meta">
                              <el-tag type="warning">{{ percent(item.mastery) }}%</el-tag>
                              <div class="weak-item__progress">
                                <span :style="{ width: `${percent(item.mastery)}%` }"></span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </section>

                      <section class="record-panel record-panel--flat">
                        <div class="record-panel__head">
                          <div>
                            <div class="record-panel__title">知识点掌握情况</div>
                            <div class="record-panel__desc">查看知识点状态、掌握度和判断依据。</div>
                          </div>
                        </div>
                        <el-table :data="detail.mastery_map" size="small" max-height="420" class="record-table">
                          <el-table-column prop="code" label="编码" width="120" />
                          <el-table-column prop="title" label="知识点" min-width="180" />
                          <el-table-column prop="status" label="状态" width="100" />
                          <el-table-column prop="mastery" label="掌握度" width="100">
                            <template #default="{ row }">{{ percent(row.mastery) }}%</template>
                          </el-table-column>
                          <el-table-column prop="reason_summary" label="依据" min-width="220">
                            <template #default="{ row }">
                              <el-tooltip v-if="String(row.reason_summary || '').length > 24" :content="row.reason_summary" placement="top">
                                <span>{{ String(row.reason_summary || "").slice(0, 24) }}...</span>
                              </el-tooltip>
                              <span v-else>{{ row.reason_summary || "-" }}</span>
                            </template>
                          </el-table-column>
                        </el-table>
                      </section>
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </section>
            </el-tab-pane>

            <el-tab-pane label="老师记录" name="teacher">
              <div class="teacher-tool">
                <section class="teacher-tool__composer" v-loading="feedbackLoading">
                  <div class="teacher-tool__header">
                    <div>
                      <div class="section-kicker">教师评语工具</div>
                      <div class="teacher-tool__title">阶段评语</div>
                      <div class="teacher-tool__subtitle">为学生生成本阶段总结与建议</div>
                    </div>
                    <div class="teacher-tool__filters">
                      <el-select v-model="selectedStageId" placeholder="选择阶段" class="teacher-tool__select" :disabled="!stageHistory.length">
                        <el-option v-for="item in stageHistory" :key="item.stage_id" :label="item.stage_title" :value="item.stage_id" />
                      </el-select>
                      <el-select v-model="feedbackForm.feedback_tag" placeholder="选择标签" clearable class="teacher-tool__select">
                        <el-option v-for="item in feedbackTagOptions" :key="item" :label="item" :value="item" />
                      </el-select>
                    </div>
                  </div>

                  <div class="teacher-tool__section">
                    <div class="teacher-tool__section-title">快捷模板 / 智能建议</div>
                    <div class="feedback-chips">
                      <button
                        v-for="item in feedbackQuickTemplates"
                        :key="item"
                        type="button"
                        class="feedback-chip"
                        @click="applyQuickTemplate(item)"
                      >
                        {{ item }}
                      </button>
                    </div>
                  </div>

                  <div class="teacher-tool__section">
                    <div class="teacher-tool__section-title">评价标签</div>
                    <div class="feedback-chips">
                      <button
                        v-for="item in feedbackTagOptions"
                        :key="item"
                        type="button"
                        class="feedback-chip feedback-chip--tag"
                        :class="{ 'is-active': feedbackForm.feedback_tag === item }"
                        @click="feedbackForm.feedback_tag = feedbackForm.feedback_tag === item ? '' : item"
                      >
                        {{ item }}
                      </button>
                    </div>
                  </div>

                  <div class="teacher-tool__section">
                    <div class="teacher-tool__section-title">教师评语</div>
                    <el-input
                      v-model="feedbackForm.comment"
                      type="textarea"
                      :rows="6"
                      placeholder="请输入本阶段的学习状态、主要问题和建议，例如：学习状态整体稳定，但练习正确率有波动，建议先复习薄弱知识点，再追加一次针对性练习。"
                    />
                  </div>

                  <div class="teacher-tool__actions">
                    <el-button type="primary" :loading="savingFeedback" @click="saveStageFeedback">保存评语</el-button>
                  </div>
                </section>

                <section class="teacher-history">
                  <div class="teacher-tool__title teacher-tool__title--sub">评语历史</div>
                  <div v-if="feedbackHistory.length" class="feedback-history-list">
                    <button
                      v-for="item in feedbackHistory"
                      :key="item.id"
                      type="button"
                      class="feedback-history-item"
                      @click="applyHistoryComment(item)"
                    >
                      <div class="feedback-history-item__top">
                        <span>{{ formatDateTime(item.updated_at) }}</span>
                        <el-tag size="small" type="info">{{ item.feedback_tag || "阶段评语" }}</el-tag>
                      </div>
                      <div class="feedback-history-item__stage">{{ item.stage_title || `阶段 ${item.stage_id}` }}</div>
                      <div class="feedback-history-item__comment">{{ item.comment || "暂无文字内容" }}</div>
                      <div class="feedback-history-item__meta">{{ item.updated_by || "教师" }}</div>
                    </button>
                  </div>
                  <div v-else class="empty-strip empty-strip--panel">
                    <div class="empty-strip__title">暂无历史评语</div>
                    <div class="empty-strip__desc">保存过阶段评语后，这里会自动形成历史记录。</div>
                  </div>
                </section>

                <section class="teacher-indicators" v-loading="teacherIndicatorLoading">
                  <button type="button" class="teacher-indicators__toggle" @click="teacherToolsExpanded = !teacherToolsExpanded">
                    <span>教师补充指标</span>
                    <span>{{ teacherToolsExpanded ? "收起" : "展开" }}</span>
                  </button>
                  <div v-if="teacherToolsExpanded" class="teacher-indicators__body">
                    <div class="tab-tip">
                      <span>补充说明</span>
                      <HoverTip content="用于补充系统自动看不出的情况，保存后会直接进入学生画像计算。" />
                    </div>
                    <div v-if="teacherIndicators.length" class="indicator-input-list">
                      <div v-for="item in teacherIndicators" :key="item.indicator_id" class="indicator-input-card">
                        <div class="indicator-input-card__head">
                          <div>
                            <div class="indicator-row__title">{{ item.indicator_title }}</div>
                            <div class="indicator-row__meta">{{ item.dimension_title }} · 权重 {{ Number(item.weight || 0).toFixed(1) }}</div>
                          </div>
                          <el-input-number v-model="item.score" :min="0" :max="1" :step="0.05" size="small" />
                        </div>
                        <el-input v-model="item.note" type="textarea" :rows="2" placeholder="简要写下老师观察到的情况" />
                      </div>
                      <div class="indicator-input-actions">
                        <el-button type="primary" :loading="savingTeacherIndicators" @click="saveTeacherIndicators">保存</el-button>
                      </div>
                    </div>
                    <div v-else class="empty-strip empty-strip--panel">
                      <div class="empty-strip__title">当前课程未启用老师补充指标</div>
                      <div class="empty-strip__desc">到课程配置中启用后，这里会自动出现可填写项。</div>
                    </div>
                  </div>
                </section>
              </div>
            </el-tab-pane>

            <el-tab-pane label="学生情况" name="summary">
              <div class="tab-grid">
                <section v-if="selectedStage" class="panel-card sub-card">
                  <div class="sub-card__title">学期总结</div>
                  <div class="summary-grid">
                    <div class="summary-metric">
                      <span>覆盖阶段</span>
                      <strong>{{ termSummary.stage_count || 0 }}</strong>
                    </div>
                    <div class="summary-metric">
                      <span>学期参考分</span>
                      <strong>{{ percent(termSummary.final_score_reference) }}%</strong>
                    </div>
                    <div class="summary-metric">
                      <span>进步次数</span>
                      <strong>{{ termSummary.progress_stages || 0 }}</strong>
                    </div>
                    <div class="summary-metric">
                      <span>回落次数</span>
                      <strong>{{ termSummary.regress_stages || 0 }}</strong>
                    </div>
                  </div>
                  <div class="analysis-note">{{ termSummary.final_reason_summary || "系统会把整个学期的结果汇总到这里。" }}</div>
                </section>

                <section v-if="finalPortraitDimensions.length" class="panel-card sub-card">
                  <div class="sub-card__title">学期结果图</div>
                  <PortraitRadarChart
                    title="学期结果图"
                    subtitle="展示整个学期的综合结果"
                    :items="finalPortraitDimensions"
                    accent="#22c55e"
                    empty-text="当前还没有可展示的学期结果"
                  />
                  <div class="portrait-grid">
                    <div v-for="item in finalPortraitDimensions" :key="item.dimension_title" class="portrait-card">
                      <span>{{ item.dimension_title }}</span>
                      <strong>{{ item.score == null ? "待补充" : `${percent(item.score)}%` }}</strong>
                    </div>
                  </div>
                </section>

                <section v-if="selectedStage" class="panel-card sub-card">
                  <div class="sub-card__title">当前阶段</div>
                  <div class="summary-grid">
                    <div class="summary-metric">
                      <span>学习投入</span>
                      <strong>{{ percent(selectedStage.engagement) }}%</strong>
                    </div>
                    <div class="summary-metric">
                      <span>学习成效</span>
                      <strong>{{ percent(selectedStage.achievement) }}%</strong>
                    </div>
                    <div class="summary-metric">
                      <span>学习习惯</span>
                      <strong>{{ percent(selectedStage.habit) }}%</strong>
                    </div>
                    <div class="summary-metric">
                      <span>学习特征</span>
                      <strong>{{ percent(selectedStage.characteristic) }}%</strong>
                    </div>
                  </div>
                  <div class="analysis-note">{{ selectedStage.reason_summary || "当前阶段暂无系统总结。" }}</div>
                </section>

                <section v-if="selectedStage" class="panel-card sub-card">
                  <div class="sub-card__title">当前阶段结果图</div>
                  <PortraitRadarChart
                    title="当前阶段结果图"
                    subtitle="展示当前阶段的画像概况"
                    :items="selectedStage.portrait_dimensions ?? []"
                    accent="#3b82f6"
                    empty-text="当前阶段还没有足够数据生成结果图"
                  />
                  <div v-if="selectedStage.portrait_dimensions?.length" class="portrait-grid">
                    <div v-for="item in selectedStage.portrait_dimensions" :key="item.dimension_title" class="portrait-card">
                      <span>{{ item.dimension_title }}</span>
                      <strong>{{ item.score == null ? "待补充" : `${percent(item.score)}%` }}</strong>
                    </div>
                  </div>
                  <div v-else class="empty-strip empty-strip--panel">
                    <div class="empty-strip__title">当前阶段暂无结果图</div>
                    <div class="empty-strip__desc">阶段数据不足时，这里会自动弱化显示。</div>
                  </div>
                </section>

                <section v-if="selectedStage" class="panel-card sub-card">
                  <div class="sub-card__title">详细指标</div>
                  <div v-if="selectedStage.portrait_indicators?.length" class="indicator-stack">
                    <div
                      v-for="item in selectedStage.portrait_indicators.filter((row) => row.available)"
                      :key="item.title"
                      class="indicator-row"
                    >
                      <div>
                        <div class="indicator-row__title">{{ item.title }}</div>
                        <div class="indicator-row__meta">
                          {{ sourceTypeLabel(item.source_type) }} · {{ scoreSourceLabel(item.score_source) }} · 权重
                          {{ Number(item.weight || 0).toFixed(1) }}
                        </div>
                        <div v-if="item.formula_text" class="indicator-row__desc">{{ item.formula_text }}</div>
                        <div v-if="item.evidence_metrics?.length" class="indicator-row__evidence">
                          <span v-for="metric in item.evidence_metrics" :key="`${item.title}-${metric.metric_label}`">
                            {{ metric.metric_label }} {{ metric.metric_percent }}%
                          </span>
                        </div>
                      </div>
                      <strong>{{ item.score == null ? "待补充" : `${percent(item.score)}%` }}</strong>
                    </div>
                  </div>
                  <div v-else class="empty-strip empty-strip--panel">
                    <div class="empty-strip__title">当前阶段暂无详细指标</div>
                    <div class="empty-strip__desc">系统会根据阶段数据、老师填写和学生补充内容自动生成这里的结果。</div>
                  </div>
                </section>
              </div>
            </el-tab-pane>
          </el-tabs>
        </section>
      </div>

      <div v-else class="detail-empty">
        <el-empty :description="emptyDetailMessage" />
        <div class="tab-tip">
          <span>排查提示</span>
          <HoverTip content="如果这里没有内容，请先确认已选择课程、已创建阶段并已导入阶段数据。" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.student-detail-shell {
  display: grid;
}

.detail-card {
  border-radius: 32px;
  border: 3px solid #1f2937 !important;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%) !important;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12) !important;
  overflow: hidden;
}

.detail-card :deep(.el-card__body) {
  padding: 18px;
}

.detail-layout {
  display: grid;
  gap: 24px;
}

.core-panel,
.analysis-card,
.tab-panel,
.sub-card {
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  border-radius: 24px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.core-panel {
  padding: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}

.core-panel--danger {
  border-color: #fecaca;
}

.core-panel--warning {
  border-color: #fed7aa;
}

.core-panel--success {
  border-color: #bbf7d0;
}

.core-panel__main {
  display: grid;
  gap: 12px;
}

.section-kicker {
  font-size: 12px;
  font-weight: 700;
  color: #3b82f6;
}

.section-title {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
}

.core-panel__headline {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.core-panel__headline h2 {
  margin: 0;
  font-size: 36px;
  line-height: 1.1;
  color: #0f172a;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 7px 13px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  border: 1.5px solid #c6d8ef;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.status-pill--danger {
  color: #b91c1c;
  background: linear-gradient(180deg, #fff7f7 0%, #fff1f1 100%);
  border-color: #fecaca;
}

.status-pill--warning {
  color: #c2410c;
  background: linear-gradient(180deg, #fffaf2 0%, #fff4e6 100%);
  border-color: #fed7aa;
}

.status-pill--success {
  color: #15803d;
  background: linear-gradient(180deg, #f4fff8 0%, #effcf4 100%);
  border-color: #bbf7d0;
}

.core-panel__summary {
  margin: 0;
  font-size: 16px;
  line-height: 1.7;
  color: #0f172a;
}

.core-panel__support {
  margin: -4px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.core-panel__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

.core-panel__side {
  min-width: 280px;
  padding: 18px 0 18px 24px;
  border-left: 1.5px solid #c6d8ef;
  display: grid;
  gap: 14px;
  align-content: start;
}

.core-panel__actions {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

.core-panel__side-note {
  max-width: 320px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.metric-section {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  padding: 20px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  border-radius: 20px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
  display: grid;
  gap: 10px;
}

.metric-card__label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}
.metric-card__value {
  font-size: 30px;
  line-height: 1;
  font-weight: 800;
  color: #0f172a;
}

.metric-card__trend {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
}

.metric-card__trend--success,
.metric-card--success .metric-card__value {
  color: #15803d;
}

.metric-card__trend--danger,
.metric-card--danger .metric-card__value {
  color: #b91c1c;
}

.metric-card__trend--neutral,
.metric-card__trend--warning,
.metric-card--warning .metric-card__value {
  color: #c2410c;
}

.metric-card__trend--success {
  background: #f0fdf4;
}

.metric-card__trend--danger {
  background: #fef2f2;
}

.metric-card__trend--neutral,
.metric-card__trend--warning {
  background: #fff7ed;
}

.analysis-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.analysis-card {
  padding: 22px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.analysis-card--compact {
  padding-bottom: 18px;
  gap: 12px;
}

.analysis-card--compact .section-title {
  font-size: 22px;
}

.risk-list,
.stage-timeline,
.indicator-stack,
.weak-list,
.timeline-list,
.feedback-history-list,
.indicator-input-list,
.tab-grid {
  display: grid;
  gap: 12px;
}

.risk-list__item {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.6;
}

.risk-list__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex: 0 0 auto;
}

.risk-list__dot--danger {
  background: #ef4444;
}

.risk-list__dot--warning {
  background: #f59e0b;
}

.risk-list__dot--success {
  background: #22c55e;
}

.analysis-note {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  color: #475569;
  line-height: 1.7;
  font-size: 14px;
}

.analysis-note__label {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #2563eb;
}

.analysis-note--accent {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.action-suggestion {
  display: grid;
  gap: 10px;
}

.action-suggestion__summary {
  color: #0f172a;
}

.action-suggestion__list {
  display: grid;
  gap: 8px;
}

.action-suggestion__item {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #475569;
}

.action-suggestion__dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #2563eb;
  flex: 0 0 auto;
}

.stage-node {
  width: 100%;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  display: grid;
  gap: 8px;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.stage-node:hover {
  background: #f8fafc;
  transform: translateY(-1px);
}

.stage-node.is-active {
  border-color: #bfdbfe;
  background: #f8fbff;
}

.stage-node__top,
.timeline-item__top,
.feedback-history-item__top,
.indicator-input-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.stage-node__top span,
.sub-card__title,
.indicator-row__title,
.weak-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.stage-node__top strong {
  font-size: 13px;
  color: #2563eb;
}

.stage-node__meta,
.summary-metric span,
.portrait-card span,
.indicator-row__meta,
.weak-code,
.timeline-type,
.timeline-time,
.feedback-history-item__meta,
.record-metric-card__label,
.record-metric-card__hint {
  font-size: 12px;
  color: #64748b;
}

.stage-node__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.stage-node__bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.stage-node__bar span {
  display: block;
  height: 100%;
  background: #3b82f6;
  border-radius: inherit;
}
.empty-strip {
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
}

.empty-strip--panel {
  margin-top: 4px;
}

.empty-strip--stage {
  padding: 14px 16px;
  min-height: 0;
}

.empty-strip__title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.empty-strip__desc {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.detail-tabs {
  display: grid;
}

.detail-tabs :deep(.el-tabs__header),
.record-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  background: #e5e7eb;
}

.detail-tabs :deep(.el-tabs__item) {
  height: 40px;
  font-weight: 700;
  color: #64748b;
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: #2563eb;
}

.tab-panel,
.sub-card {
  padding: 20px;
}

.tab-tip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
}

.record-overview-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.record-overview-grid--compact {
  margin-top: 6px;
}

.record-metric-card {
  border-radius: 18px;
  border: 1.5px solid #c6d8ef;
  box-shadow: none;
  min-height: 128px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.record-metric-card--wide {
  grid-column: 1 / -1;
}

.record-metric-card__value,
.summary-metric strong,
.portrait-card strong,
.indicator-row strong {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
}

.record-chips,
.indicator-row__evidence,
.feedback-templates {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.record-chips span,
.indicator-row__evidence span {
  padding: 5px 11px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f4f9ff 0%, #edf6ff 100%);
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.record-split-grid,
.summary-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.practice-stack,
.video-progress-list,
.recommendation-list,
.behavior-timeline,
.change-track {
  display: grid;
  gap: 16px;
}

.practice-summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.practice-summary--hero {
  padding: 4px 0 2px;
}

.practice-summary__item,
.behavior-item,
.change-track__item,
.video-progress-item,
.recommendation-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
}

.practice-summary__item {
  display: grid;
  gap: 6px;
  min-height: 82px;
  align-content: center;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border-color: #c6d8ef;
  box-shadow: none;
}

.practice-summary__item span,
.behavior-item__desc,
.behavior-item__time,
.behavior-item__extra,
.change-track__summary,
.video-progress-item__code,
.video-progress-item__time,
.recommendation-item__source,
.recommendation-item__reason {
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.practice-summary__item strong,
.change-track__value {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.record-panel {
  padding: 0;
  display: grid;
  gap: 10px;
}

.record-panel--flat {
  gap: 12px;
}

.record-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.record-panel__title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.record-panel__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.record-table {
  border: 1.5px solid #c6d8ef;
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  box-shadow: none;
}

.portrait-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.summary-metric,
.portrait-card,
.indicator-row,
.weak-item,
.timeline-item,
.feedback-history-item,
.indicator-input-card {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
}

.summary-metric {
  display: grid;
  gap: 6px;
}

.indicator-row,
.weak-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.weak-item {
  align-items: flex-start;
}

.weak-list {
  border: 1.5px solid #c6d8ef;
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  gap: 0;
}

.weak-item__meta {
  min-width: 120px;
  display: grid;
  gap: 10px;
  justify-items: end;
}

.weak-item__progress {
  width: 120px;
  height: 6px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.weak-item__progress span {
  display: block;
  height: 100%;
  background: #f59e0b;
}

.weak-item {
  padding: 14px 16px;
  border: 0;
  border-bottom: 1px solid #d9e6f6;
  border-radius: 0;
  background: transparent;
}

.weak-item:last-child {
  border-bottom: 0;
}

.behavior-item {
  display: grid;
  grid-template-columns: 12px 1fr;
  gap: 12px;
}

.behavior-item__dot {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 999px;
  background: #3b82f6;
}

.behavior-item__content {
  display: grid;
  gap: 4px;
}

.behavior-item__top,
.change-track__top,
.video-progress-item__meta,
.recommendation-item__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.behavior-item__title,
.change-track__title,
.video-progress-item__title,
.recommendation-item__title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.change-track__item--success {
  border-color: #bbf7d0;
}

.change-track__item--warning {
  border-color: #fed7aa;
}

.change-track__item--danger {
  border-color: #fecaca;
}

.video-progress-item__status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.video-progress-item__status strong {
  font-size: 15px;
  color: #2563eb;
}

.recommendation-item__reason {
  margin-top: 8px;
  color: #475569;
}

.teacher-tool {
  display: grid;
  gap: 18px;
}

.teacher-tool__composer,
.teacher-history,
.teacher-indicators {
  padding: 20px;
  border-radius: 20px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
}

.teacher-tool__composer {
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  display: grid;
  gap: 18px;
}

.teacher-tool__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.teacher-tool__title {
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
}

.teacher-tool__title--sub {
  font-size: 18px;
  margin-bottom: 12px;
}

.teacher-tool__subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #64748b;
}

.teacher-tool__filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.teacher-tool__select {
  width: 180px;
}

.teacher-tool__section {
  display: grid;
  gap: 10px;
}

.teacher-tool__section-title {
  font-size: 13px;
  font-weight: 700;
  color: #475569;
}

.feedback-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #f4f9ff 0%, #edf6ff 100%);
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.feedback-chip:hover {
  background: linear-gradient(180deg, #eaf3ff 0%, #dfeeff 100%);
}

.feedback-chip--tag {
  border-color: #d9e7f6;
  background: linear-gradient(180deg, #fbfdff 0%, #f3f8fd 100%);
  color: #475569;
}

.feedback-chip--tag.is-active {
  border-color: #93c5fd;
  background: linear-gradient(180deg, #eef6ff 0%, #e0efff 100%);
  color: #2563eb;
}

.teacher-tool__actions {
  display: flex;
  justify-content: flex-end;
}

.feedback-history-item {
  background: #ffffff;
}

.feedback-history-item__stage {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.teacher-indicators {
  padding: 14px 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.teacher-indicators__toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 0;
  background: transparent;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.teacher-indicators__body {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}

.indicator-row__desc,
.timeline-json,
.feedback-history-item__comment {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

.indicator-input-actions {
  display: flex;
  justify-content: flex-end;
}

.detail-empty {
  display: grid;
  gap: 14px;
}

.progress-cell {
  width: 100%;
}

.detail-layout :deep(.el-table) {
  --el-table-border-color: #e5e7eb;
  --el-table-header-bg-color: #f8fafc;
  --el-table-row-hover-bg-color: #f8fbff;
  border-radius: 14px;
  overflow: hidden;
}

.record-table :deep(.el-table__header-wrapper th.el-table__cell) {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

.record-table :deep(.el-table__body-wrapper td.el-table__cell) {
  color: #0f172a;
}

.detail-layout :deep(.el-form-item__label) {
  font-weight: 700;
  color: #475569;
}

.detail-layout :deep(.el-input__wrapper),
.detail-layout :deep(.el-select__wrapper),
.detail-layout :deep(.el-textarea__inner),
.detail-layout :deep(.el-input-number) {
  border-radius: 12px;
}

.detail-layout :deep(.el-textarea__inner) {
  min-height: 120px;
}

@media (max-width: 1200px) {
  .metric-section,
  .record-overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .core-panel,
  .analysis-grid,
  .record-split-grid,
  .summary-grid,
  .practice-summary {
    grid-template-columns: 1fr;
  }

  .core-panel {
    flex-direction: column;
  }

  .core-panel__side {
    min-width: 0;
    padding-left: 0;
    border-left: none;
    border-top: 1px solid #e5e7eb;
    padding-top: 16px;
  }

  .core-panel__actions {
    justify-content: flex-start;
  }

  .teacher-tool__header {
    flex-direction: column;
  }

  .teacher-tool__filters {
    width: 100%;
  }

  .teacher-tool__select {
    width: 100%;
  }
}

@media (max-width: 760px) {
  .metric-section,
  .record-overview-grid {
    grid-template-columns: 1fr;
  }

  .core-panel__headline h2 {
    font-size: 28px;
  }

  .section-title {
    font-size: 24px;
  }
}
</style>
