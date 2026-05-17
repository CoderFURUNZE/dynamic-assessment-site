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

type MasteryMapRecord = {
  kp_id?: number | string;
  code?: string | null;
  title?: string | null;
  status?: string | null;
  mastery?: number | null;
  reason_summary?: string | null;
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
const recordPageSize = 10;
const recordPages = reactive<Record<string, number>>({
  behavior: 1,
  practice: 1,
  quiz: 1,
  timeline: 1,
  video: 1,
  reco: 1,
  mastery: 1,
});
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

function shortText(value?: string | null, max = 42) {
  const text = String(value || "").trim();
  if (!text) return "暂无判定依据";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function masteryStatusTone(status?: string | null) {
  const raw = String(status || "").trim().toLowerCase();
  if (["mastered", "stable", "good"].some((item) => raw.includes(item))) return "success";
  if (["partial", "learning", "developing"].some((item) => raw.includes(item))) return "warning";
  if (["weak", "risk", "unmastered"].some((item) => raw.includes(item))) return "danger";
  return "neutral";
}

function masteryStatusLabel(status?: string | null) {
  const raw = String(status || "").trim().toLowerCase();
  if (raw.includes("mastered")) return "已掌握";
  if (raw.includes("partial")) return "部分掌握";
  if (raw.includes("learning")) return "学习中";
  if (raw.includes("developing")) return "待巩固";
  if (raw.includes("weak")) return "偏薄弱";
  if (raw.includes("risk")) return "需关注";
  if (raw.includes("unmastered")) return "未掌握";
  return status || "待判断";
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

const weakPointAverage = computed(() => {
  if (!weakPoints.value.length) return 0;
  const total = weakPoints.value.reduce((sum: number, item: any) => sum + Number(item.mastery ?? 0), 0);
  return Math.round((total / weakPoints.value.length) * 100);
});

const stageHistory = computed<StageHistoryItem[]>(() => detail.value?.stage_history ?? []);
const finalPortraitDimensions = computed<PortraitDimensionItem[]>(() => detail.value?.profile?.final_portrait_dimensions ?? []);
const termSummary = computed<TermSummary>(() => {
  const base = { ...(detail.value?.profile?.term_summary ?? {}) } as TermSummary;
  const history = [...stageHistory.value].sort((a, b) => Number(a.stage_order || 0) - Number(b.stage_order || 0));
  if (!history.length) return base;
  let progress = 0;
  let steady = 0;
  let regress = 0;
  for (let index = 1; index < history.length; index += 1) {
    const delta = Number(history[index]?.dynamic_score ?? 0) - Number(history[index - 1]?.dynamic_score ?? 0);
    if (delta > 0.01) progress += 1;
    else if (delta < -0.01) regress += 1;
    else steady += 1;
  }
  const scores = history.map((item) => Number(item.dynamic_score ?? 0)).filter((value) => Number.isFinite(value));
  const avg = scores.length ? scores.reduce((sum, value) => sum + value, 0) / scores.length : Number(base.avg_dynamic_score ?? 0);
  const latest = scores.length ? scores[scores.length - 1] : Number(base.latest_dynamic_score ?? 0);
  return {
    ...base,
    stage_count: history.length,
    progress_stages: progress,
    steady_stages: steady,
    regress_stages: regress,
    avg_dynamic_score: avg,
    latest_dynamic_score: latest,
    final_score_reference: Number.isFinite(Number(base.final_score_reference))
      ? Number(base.final_score_reference)
      : Math.max(0, Math.min(1, 0.6 * avg + 0.4 * latest)),
  };
});
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

const recentPracticeRecords = computed(() => detail.value?.recent_practice ?? []);
const recentQuizRecords = computed(() => detail.value?.recent_quiz ?? []);
const masteryMapRecords = computed<MasteryMapRecord[]>(() => detail.value?.mastery_map ?? []);

function pageSlice<T>(items: T[], key: string) {
  const page = Math.max(1, recordPages[key] || 1);
  const start = (page - 1) * recordPageSize;
  return items.slice(start, start + recordPageSize);
}

const visibleBehaviorTimelineRecords = computed(() => pageSlice(behaviorTimelineRecords.value, "behavior"));
const visiblePracticeRecords = computed(() => pageSlice(recentPracticeRecords.value, "practice"));
const visibleQuizRecords = computed(() => pageSlice(recentQuizRecords.value, "quiz"));
const visibleChangeEvents = computed(() => pageSlice(changeEvents.value, "timeline"));
const visibleVideoProgressList = computed(() => pageSlice(videoProgressList.value, "video"));
const visibleRecommendationCards = computed(() => pageSlice(recommendationCards.value, "reco"));
const visibleMasteryMapRecords = computed(() => pageSlice(masteryMapRecords.value, "mastery"));

const recordCounts = computed(() => ({
  behavior: behaviorTimelineRecords.value.length,
  practice: recentPracticeRecords.value.length,
  quiz: recentQuizRecords.value.length,
  timeline: changeEvents.value.length,
  video: videoProgressList.value.length,
  reco: recommendationCards.value.length,
  mastery: masteryMapRecords.value.length,
}));

const totalRecordCount = computed(() => Object.values(recordCounts.value).reduce((sum, count) => sum + Number(count || 0), 0));

function recordHeaderTitle(title: string, count: number) {
  return `${title}（${count} 条）`;
}

function recordPageCount(total: number) {
  return Math.max(1, Math.ceil(Number(total || 0) / recordPageSize));
}

function recordPageLabel(key: string, total: number) {
  return `${recordPages[key] || 1} / ${recordPageCount(total)} 页`;
}

function setRecordPage(key: string, total: number, delta: number) {
  const next = Math.min(recordPageCount(total), Math.max(1, (recordPages[key] || 1) + delta));
  recordPages[key] = next;
}

function resetRecordPages() {
  Object.keys(recordPages).forEach((key) => {
    recordPages[key] = 1;
  });
}

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
    resetRecordPages();
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
    resetRecordPages();
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
  <div class="student-detail-shell" v-loading="loading">
      <div class="student-detail-shell__header">
        <TeacherStudentHeaderBar
          :students="students"
          :selected-user-id="selectedUserId"
          @update:selected-user-id="selectedUserId = $event"
        />
      </div>

      <div class="student-detail-shell__body">
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

                  <el-tab-pane :label="recordHeaderTitle('知识点掌握', recordCounts.mastery)" name="kps">
                    <div class="record-list-box">
                      <div class="mastery-board">
                        <section class="record-panel record-panel--flat mastery-panel mastery-panel--weak">
                          <div class="record-panel__head">
                            <div>
                              <div class="record-panel__title">薄弱知识点 Top6</div>
                              <div class="record-panel__desc">按掌握度从低到高汇总，优先用于安排补练和讲解。</div>
                            </div>
                          </div>

                          <div class="mastery-highlight">
                            <div class="mastery-highlight__label">待巩固知识点</div>
                            <div class="mastery-highlight__value">{{ weakPoints.length }} 个</div>
                            <div class="mastery-highlight__meta">平均掌握度 {{ weakPointAverage }}%</div>
                          </div>

                          <div v-if="weakPoints.length" class="weak-card-list">
                            <article v-for="item in weakPoints" :key="item.kp_id" class="weak-card">
                              <div class="weak-card__top">
                                <div>
                                  <div class="weak-code">{{ item.code }}</div>
                                  <div class="weak-title">{{ item.title }}</div>
                                </div>
                                <div class="weak-card__score">{{ percent(item.mastery) }}%</div>
                              </div>
                              <div class="weak-card__bar">
                                <span :style="{ width: `${percent(item.mastery)}%` }"></span>
                              </div>
                              <div class="weak-card__foot">
                                <span class="weak-card__hint">薄弱原因</span>
                                <span class="weak-card__hint">{{ shortText(item.reason_summary, 22) }}</span>
                              </div>
                            </article>
                          </div>
                          <div v-else class="empty-strip empty-strip--panel">
                            <div class="empty-strip__title">暂无薄弱知识点</div>
                            <div class="empty-strip__desc">当前学生的知识点掌握情况较稳定。</div>
                          </div>
                        </section>

                        <section class="record-panel record-panel--flat mastery-panel mastery-panel--map">
                          <div class="record-panel__head">
                            <div>
                              <div class="record-panel__title">知识点掌握明细</div>
                              <div class="record-panel__desc">查看各知识点掌握度、状态和系统判断依据。</div>
                            </div>
                          </div>

                          <div v-if="visibleMasteryMapRecords.length" class="mastery-card-list">
                            <article v-for="item in visibleMasteryMapRecords" :key="`${item.code || item.kp_id}-${item.title}`" class="mastery-card">
                              <div class="mastery-card__top">
                                <div>
                                  <div class="mastery-card__code">{{ item.code || `KP-${item.kp_id}` }}</div>
                                  <div class="mastery-card__title">{{ item.title }}</div>
                                </div>
                                <span class="mastery-card__status" :class="`mastery-card__status--${masteryStatusTone(item.status)}`">
                                  {{ masteryStatusLabel(item.status) }}
                                </span>
                              </div>

                              <div class="mastery-card__metrics">
                                <div class="mastery-card__metric">
                                  <strong>{{ percent(item.mastery) }}%</strong>
                                  <span>掌握度</span>
                                </div>
                                <div class="mastery-card__reason">{{ shortText(item.reason_summary, 58) }}</div>
                              </div>

                              <div class="mastery-card__bar">
                                <span :style="{ width: `${percent(item.mastery)}%` }"></span>
                              </div>
                            </article>
                          </div>
                          <div v-else class="empty-strip empty-strip--panel">
                            <div class="empty-strip__title">暂无知识点掌握记录</div>
                            <div class="empty-strip__desc">完成练习或阶段评价后，这里会显示掌握明细。</div>
                          </div>

                          <div
                            v-if="recordCounts.mastery > recordPageSize"
                            class="record-pagination"
                          >
                            <el-button size="small" :disabled="recordPages.mastery <= 1" @click="setRecordPage('mastery', recordCounts.mastery, -1)">
                              上一页
                            </el-button>
                            <span>{{ recordPageLabel("mastery", recordCounts.mastery) }}</span>
                            <el-button
                              size="small"
                              :disabled="recordPages.mastery >= recordPageCount(recordCounts.mastery)"
                              @click="setRecordPage('mastery', recordCounts.mastery, 1)"
                            >
                              下一页
                            </el-button>
                          </div>
                        </section>
                      </div>
                    </div>
                  </el-tab-pane>
                </el-tabs>
                <div class="record-count-footer">共 {{ totalRecordCount }} 条记录</div>
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
      </div>
  </div>
</template>

<style scoped>
.student-detail-shell {
  display: grid;
  gap: 16px;
}

.student-detail-shell__header,
.student-detail-shell__body {
  display: grid;
}

.detail-layout {
  display: grid;
  gap: 16px;
}

.core-panel,
.analysis-card,
.tab-panel,
.sub-card {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 24px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.core-panel {
  padding: 18px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.core-panel--danger {
  border-color: #f0c2b7;
}

.core-panel--warning {
  border-color: #eccb95;
}

.core-panel--success {
  border-color: #cfe3a5;
}

.core-panel__main {
  display: grid;
  gap: 12px;
}

.section-kicker {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
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
  font-size: 28px;
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
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.status-pill--danger {
  color: #b6544a;
  background: linear-gradient(180deg, #fff7f0 0%, #fff1e9 100%);
  border-color: #f0c2b7;
}

.status-pill--warning {
  color: #b27a25;
  background: linear-gradient(180deg, #fff7eb 0%, #fff1df 100%);
  border-color: #eccb95;
}

.status-pill--success {
  color: #5c8b32;
  background: linear-gradient(180deg, #f8fce9 0%, #f3f7df 100%);
  border-color: #cfe3a5;
}

.core-panel__summary {
  margin: 0;
  font-size: 16px;
  line-height: 1.7;
  color: #334155;
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
  border-left: 1.5px solid rgba(31, 41, 55, 0.14);
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #475569;
  line-height: 1.7;
  font-size: 14px;
}

.analysis-note__label {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #16a34a;
}

.analysis-note--accent {
  background: #f2fbe5;
  border-color: rgba(34, 197, 94, 0.24);
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
  background: #22c55e;
  flex: 0 0 auto;
}

.stage-node {
  width: 100%;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  border-color: rgba(34, 197, 94, 0.24);
  background: #f2fbe5;
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
  color: #16a34a;
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
  background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
  border-radius: inherit;
}
.empty-strip {
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.14);
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
  color: #16a34a;
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

.record-list-box {
  padding: 4px 0;
  contain: layout paint;
}

.record-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.record-count-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
}

.record-metric-card {
  border-radius: 18px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  box-shadow: none;
  min-height: 128px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  color: #334155;
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
  gap: 8px;
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
  padding: 10px 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.practice-summary__item {
  display: grid;
  gap: 6px;
  min-height: 64px;
  align-content: center;
  background: #ffffff;
  border-color: rgba(31, 41, 55, 0.14);
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

.mastery-board {
  display: grid;
  grid-template-columns: minmax(280px, 0.92fr) minmax(360px, 1.08fr);
  gap: 18px;
  align-items: start;
}

.mastery-panel {
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(8, 145, 178, 0.14);
  background:
    radial-gradient(circle at top left, rgba(34, 211, 238, 0.14), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(236, 254, 255, 0.92) 100%);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}

.mastery-panel--weak {
  border-color: rgba(249, 115, 22, 0.16);
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 247, 237, 0.94) 100%);
}

.mastery-highlight {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 20px;
  border: 1px solid rgba(249, 115, 22, 0.16);
  background: linear-gradient(135deg, rgba(255, 247, 237, 0.98) 0%, rgba(255, 237, 213, 0.88) 100%);
}

.mastery-highlight__label,
.mastery-card__code,
.weak-card__hint,
.mastery-card__metric span {
  font-size: 12px;
  color: #64748b;
}

.mastery-highlight__value {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
}

.mastery-highlight__meta {
  font-size: 13px;
  color: #9a3412;
  font-weight: 600;
}

.weak-card-list,
.mastery-card-list {
  display: grid;
  gap: 12px;
}

.weak-card,
.mastery-card {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.weak-card {
  display: grid;
  gap: 12px;
}

.weak-card__top,
.mastery-card__top,
.mastery-card__metrics {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.weak-card__score {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 237, 213, 0.9);
  color: #ea580c;
  font-size: 13px;
  font-weight: 700;
}

.weak-card__bar,
.mastery-card__bar {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(226, 232, 240, 0.92);
}

.weak-card__bar span,
.mastery-card__bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.weak-card__bar span {
  background: linear-gradient(90deg, #f97316 0%, #facc15 100%);
}

.mastery-card__bar span {
  background: linear-gradient(90deg, #06b6d4 0%, #22c55e 100%);
}

.weak-card__foot {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.weak-card__hint:first-child {
  color: #c2410c;
  font-weight: 700;
}

.mastery-card {
  display: grid;
  gap: 14px;
}

.mastery-card__title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.mastery-card__status {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  white-space: nowrap;
}

.mastery-card__status--success {
  color: #15803d;
  background: rgba(220, 252, 231, 0.92);
  border-color: rgba(34, 197, 94, 0.22);
}

.mastery-card__status--warning {
  color: #b45309;
  background: rgba(254, 243, 199, 0.94);
  border-color: rgba(245, 158, 11, 0.24);
}

.mastery-card__status--danger {
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.94);
  border-color: rgba(239, 68, 68, 0.22);
}

.mastery-card__status--neutral {
  color: #475569;
  background: rgba(241, 245, 249, 0.96);
  border-color: rgba(148, 163, 184, 0.24);
}

.mastery-card__metric {
  min-width: 86px;
  display: grid;
  gap: 2px;
}

.mastery-card__metric strong {
  font-size: 24px;
  line-height: 1;
  color: #0f172a;
}

.mastery-card__reason {
  flex: 1;
  font-size: 13px;
  line-height: 1.7;
  color: #475569;
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
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.14);
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
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  background: linear-gradient(90deg, #ffd6cb 0%, #f59e0b 100%);
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
  gap: 10px;
}

.behavior-item__dot {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 999px;
  background: #22c55e;
}

.behavior-item__content {
  display: grid;
  gap: 2px;
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
  font-size: 13px;
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
  color: #16a34a;
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.14);
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
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  color: #334155;
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
  border-color: rgba(34, 197, 94, 0.24);
  background: linear-gradient(180deg, #f2fbe5 0%, #e6f7cb 100%);
  color: #355a28;
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
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
  --el-table-row-hover-bg-color: #fff7ef;
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
  .mastery-board,
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

  .weak-card__top,
  .mastery-card__top,
  .mastery-card__metrics {
    flex-direction: column;
  }

  .mastery-card__status {
    align-self: flex-start;
  }

  .core-panel__headline h2 {
    font-size: 28px;
  }

  .section-title {
    font-size: 24px;
  }
}
</style>
