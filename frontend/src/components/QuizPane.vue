<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type Question = {
  id: number;
  kp_id: number;
  type: string;
  prompt: string;
  options: string[];
  answer?: string;
  cognitive_level?: string;
  ability_subtags?: string;
};

type QuizTab = "practice" | "records" | "wrong" | "review";

const props = defineProps<{
  kpId: number | null;
  preview?: boolean;
  /**
   * 若外层使用子路由，则通过此字段驱动当前标签页。
   * 不传/为 null 时保持组件内部默认行为。
   */
  routeView?: QuizTab | null;
}>();
const emit = defineEmits<{
  (e: "mastery-updated"): void;
  (e: "view-change", view: QuizTab): void;
}>();

const loading = ref(false);
const questions = ref<Question[]>([]);
const currentQuestion = ref<Question | null>(null);
const totalQuestions = ref(0);
const attemptedQuestions = ref(0);
const difficultyRange = ref<string | null>(null);
const done = ref(false);
const modelUsed = ref<boolean>(false);
const predictedCorrect = ref<number | null>(null);
const reason = ref<string | null>(null);
const selected = ref<string>("");
const blankAnswer = ref<string>("");
const selfReport = ref<"guess" | "sure" | "unknown">("unknown");
const startedAt = ref<number>(0);
const lastResult = ref<{ correct: boolean; explanation: string } | null>(null);
const viewTab = ref<QuizTab>("practice");
const historyLoading = ref(false);
const historyItems = ref<any[]>([]);
const historyStats = ref<{ total: number; correct: number; incorrect: number; accuracy: number }>({
  total: 0,
  correct: 0,
  incorrect: 0,
  accuracy: 0,
});
const wrongItems = ref<any[]>([]);
const wrongLoading = ref(false);
const wrongPage = ref(1);
const wrongPageSize = 10;
const wrongTotal = ref(0);
const wrongDays = ref(0);
const wrongType = ref("");
const wrongMinDiff = ref<number | null>(null);
const wrongMaxDiff = ref<number | null>(null);
const wrongOrder = ref("recent");
const reviewItems = ref<any[]>([]);
const reviewLoading = ref(false);
const reviewTotal = ref(0);
const reviewDue = ref(0);
const statsDetail = ref<{ total: number; correct: number; incorrect: number; accuracy: number; daily: any[] }>({
  total: 0,
  correct: 0,
  incorrect: 0,
  accuracy: 0,
  daily: [],
});
const trendMode = ref<"daily" | "weekly" | "monthly">("daily");
const wrongPractice = ref({
  active: false,
  queue: [] as any[],
  index: 0,
});

watch(
  () => props.routeView,
  (v) => {
    if (!v) return;
    viewTab.value = v;
  },
  { immediate: true },
);

watch(viewTab, (v) => {
  // 若外层已经按同一路由驱动了当前视图，就不需要反向再 push。
  if (props.routeView && v === props.routeView) return;
  emit("view-change", v);
});

const current = computed(() => currentQuestion.value);
const recentItems = computed(() => historyItems.value.slice(0, 10).reverse());

const HIGH_ORDER_LEVELS = new Set(["apply", "analyze", "evaluate", "create"]);

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

const practiceQuestionMeta = computed(() => {
  const q = current.value;
  if (!q) return null;
  const level = q.cognitive_level || "understand";
  const tags = (q.ability_subtags || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const isHigh = HIGH_ORDER_LEVELS.has(level);
  if (!isHigh && level === "understand" && tags.length === 0) return null;
  return { levelLabel: bloomLevelLabel(level), tags, isHigh };
});
const correctRatio = computed(() => {
  if (!historyStats.value.total) return 0;
  return historyStats.value.correct / historyStats.value.total;
});
const exportUrl = computed(() => (props.kpId ? `/practice/export?kp_id=${props.kpId}` : "#"));
const trendItems = computed(() => {
  const daily = statsDetail.value.daily ?? [];
  if (trendMode.value === "daily") return daily;
  const grouped: Record<string, { key: string; total: number; correct: number }> = {};
  const getKey = (dateStr: string) => {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return dateStr;
    if (trendMode.value === "monthly") {
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    }
    const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const dayNum = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
    return `${tmp.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
  };
  for (const item of daily) {
    const key = getKey(item.date);
    if (!grouped[key]) grouped[key] = { key, total: 0, correct: 0 };
    grouped[key].total += Number(item.total || 0);
    grouped[key].correct += Number(item.correct || 0);
  }
  return Object.values(grouped).map((g) => ({
    date: g.key,
    total: g.total,
    correct: g.correct,
    accuracy: g.total ? g.correct / g.total : 0,
  }));
});

async function load() {
  if (!props.kpId) return;
  loading.value = true;
  try {
    if (props.preview) {
      const res = await api.get(`/admin/questions?kp_id=${props.kpId}&page=1&page_size=200`);
      questions.value = res.data.items ?? [];
      currentQuestion.value = null;
      done.value = false;
      totalQuestions.value = 0;
      attemptedQuestions.value = 0;
      difficultyRange.value = null;
    } else {
      await loadNext();
      await loadHistory();
    }
    wrongPage.value = 1;
    await loadWrong();
    await loadReview();
    selected.value = "";
    blankAnswer.value = "";
    selfReport.value = "unknown";
    startedAt.value = Date.now();
    lastResult.value = null;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载题目失败");
  } finally {
    loading.value = false;
  }
}

async function loadNext() {
  if (!props.kpId) return;
  const res = await api.get(`/practice/next?kp_id=${props.kpId}`);
  done.value = Boolean(res.data.done);
  totalQuestions.value = Number(res.data.total_questions ?? 0);
  attemptedQuestions.value = Number(res.data.attempted_questions ?? 0);
  difficultyRange.value = res.data.difficulty_range ?? null;
  currentQuestion.value = res.data.question ?? null;
  modelUsed.value = Boolean(res.data.model_used);
  predictedCorrect.value =
    typeof res.data.predicted_correct === "number" ? Number(res.data.predicted_correct) : null;
  reason.value = res.data.reason ?? null;
  selected.value = "";
  blankAnswer.value = "";
  selfReport.value = "unknown";
  startedAt.value = Date.now();
  lastResult.value = null;
}

async function loadHistory() {
  if (!props.kpId) return;
  historyLoading.value = true;
  try {
    const res = await api.get(`/practice/history?kp_id=${props.kpId}&limit=50`);
    historyItems.value = res.data.items ?? [];
    historyStats.value = {
      total: Number(res.data.total ?? 0),
      correct: Number(res.data.correct ?? 0),
      incorrect: Number(res.data.incorrect ?? 0),
      accuracy: Number(res.data.accuracy ?? 0),
    };
    await loadStats();
    await loadWrong();
    await loadReview();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载做题记录失败");
  } finally {
    historyLoading.value = false;
  }
}

async function loadStats() {
  if (!props.kpId) return;
  try {
    const res = await api.get(`/practice/stats?kp_id=${props.kpId}&days=14`);
    statsDetail.value = {
      total: Number(res.data.total ?? 0),
      correct: Number(res.data.correct ?? 0),
      incorrect: Number(res.data.incorrect ?? 0),
      accuracy: Number(res.data.accuracy ?? 0),
      daily: res.data.daily ?? [],
    };
  } catch (e: any) {
    // ignore
  }
}

async function loadWrong() {
  if (!props.kpId) return;
  wrongLoading.value = true;
  try {
    const query = new URLSearchParams({
      kp_id: String(props.kpId),
      page: String(wrongPage.value),
      page_size: String(wrongPageSize),
    });
    if (wrongDays.value > 0) {
      query.set("days", String(wrongDays.value));
    }
    if (wrongType.value) query.set("q_type", wrongType.value);
    if (wrongMinDiff.value !== null) query.set("min_difficulty", String(wrongMinDiff.value));
    if (wrongMaxDiff.value !== null) query.set("max_difficulty", String(wrongMaxDiff.value));
    if (wrongOrder.value) query.set("order", wrongOrder.value);
    const res = await api.get(`/practice/wrong/page?${query.toString()}`);
    wrongItems.value = res.data.items ?? [];
    wrongTotal.value = Number(res.data.total ?? 0);
  } catch (e: any) {
    // ignore
  } finally {
    wrongLoading.value = false;
  }
}

async function loadReview() {
  if (!props.kpId) return;
  reviewLoading.value = true;
  try {
    const res = await api.get(`/practice/review/queue?kp_id=${props.kpId}&days=7`);
    reviewItems.value = res.data.items ?? [];
    reviewTotal.value = Number(res.data.total ?? 0);
    reviewDue.value = Number(res.data.due ?? 0);
  } catch {
    // ignore
  } finally {
    reviewLoading.value = false;
  }
}

async function submit() {
  if (!current.value || !props.kpId) return;
  const answer = current.value.type === "mcq" ? selected.value : blankAnswer.value;
  if (!answer) {
    ElMessage.warning("请作答后提交");
    return;
  }
  if (selfReport.value === "unknown") {
    ElMessage.warning("请选择“蒙的 / 确定”");
    return;
  }
  const duration_ms = Math.max(0, Date.now() - startedAt.value);
  try {
    const res = await api.post("/practice/submit", {
      kp_id: props.kpId,
      question_id: current.value.id,
      answer,
      self_report: selfReport.value,
      duration_ms,
    });
    ElMessage.success(res.data.correct ? "回答正确" : "回答错误");
    emit("mastery-updated");
    lastResult.value = {
      correct: Boolean(res.data.correct),
      explanation: String(res.data.explanation ?? ""),
    };
    await loadHistory();
    await loadStats();
    await loadWrong();
    await loadReview();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "提交失败");
  }
}

function nextQuestion() {
  loadNext();
}

async function loadWrongQuestionByIndex() {
  const item = wrongPractice.value.queue[wrongPractice.value.index];
  if (!item) {
    wrongPractice.value.active = false;
    ElMessage.success("错题重练已完成");
    await loadNext();
    return;
  }
  try {
    const res = await api.get(`/practice/question/${item.question_id}`);
    const q = res.data;
    currentQuestion.value = q;
    done.value = false;
    difficultyRange.value = null;
    modelUsed.value = false;
    predictedCorrect.value = null;
    reason.value = "错题重练";
    selected.value = "";
    blankAnswer.value = "";
    selfReport.value = "unknown";
    startedAt.value = Date.now();
    lastResult.value = null;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载错题失败");
  }
}

async function startWrongPractice() {
  if (!props.kpId) return;
  const queue: any[] = [];
  let page = 1;
  const pageSize = 50;
  const days = wrongDays.value;
  while (true) {
    const query = new URLSearchParams({
      kp_id: String(props.kpId),
      page: String(page),
      page_size: String(pageSize),
    });
    if (days > 0) query.set("days", String(days));
    if (wrongType.value) query.set("q_type", wrongType.value);
    if (wrongMinDiff.value !== null) query.set("min_difficulty", String(wrongMinDiff.value));
    if (wrongMaxDiff.value !== null) query.set("max_difficulty", String(wrongMaxDiff.value));
    if (wrongOrder.value) query.set("order", String(wrongOrder.value));
    const res = await api.get(`/practice/wrong/page?${query.toString()}`);
    const items = res.data.items ?? [];
    queue.push(...items);
    const total = Number(res.data.total ?? 0);
    if (queue.length >= total || items.length === 0) break;
    page += 1;
  }
  if (queue.length === 0) {
    ElMessage.info("暂无错题可重练");
    return;
  }
  wrongPractice.value.active = true;
  wrongPractice.value.queue = queue;
  wrongPractice.value.index = 0;
  viewTab.value = "practice";
  await loadWrongQuestionByIndex();
}

function stopWrongPractice() {
  wrongPractice.value.active = false;
  wrongPractice.value.queue = [];
  wrongPractice.value.index = 0;
  ElMessage.info("已退出错题重练");
}

async function nextAfterAnswer() {
  if (wrongPractice.value.active) {
    wrongPractice.value.index += 1;
    await loadWrongQuestionByIndex();
    return;
  }
  await loadNext();
}

async function redoWrong(row: any) {
  wrongPractice.value.active = true;
  wrongPractice.value.queue = [row];
  wrongPractice.value.index = 0;
  viewTab.value = "practice";
  await loadWrongQuestionByIndex();
}

async function resetPractice() {
  if (!props.kpId) return;
  try {
    await api.post("/practice/reset", { kp_id: props.kpId });
    ElMessage.success("已重置做题进度");
    lastResult.value = null;
    await loadNext();
    await loadHistory();
    await loadStats();
    await loadWrong();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "重置失败");
  }
}

watch(
  () => props.kpId,
  () => load(),
  { immediate: true }
);

watch(
  () => wrongDays.value,
  () => {
    wrongPage.value = 1;
    loadWrong();
  }
);

watch(
  () => [wrongType.value, wrongMinDiff.value, wrongMaxDiff.value, wrongOrder.value],
  () => {
    wrongPage.value = 1;
    loadWrong();
  }
);
</script>

<template>
  <el-card class="quiz-card">
    <template #header>
      <div class="quiz-card__header">
        <div>
          <div class="quiz-card__eyebrow">Practice</div>
          <div class="quiz-card__title">练习题</div>
        </div>
        <div class="quiz-card__caption">
          聚焦当前知识点的作答、错题回练与复习节奏。此为<strong>题库练习</strong>，与图谱节点上的<strong>成套小测</strong>数据来源不同。
        </div>
      </div>
    </template>
    <div v-if="!kpId" class="empty-state">
      <el-text type="info">请选择知识点后加载题目</el-text>
    </div>
    <div v-else-if="loading">
      <el-skeleton :rows="4" animated />
    </div>
    <div v-else-if="preview">
      <div v-if="questions.length === 0" class="empty-state">
        <el-text type="info">暂无题目</el-text>
      </div>
      <div class="preview-list">
        <div v-for="(q, i) in questions" :key="q.id" class="question-item">
          <div class="question-prompt">Q{{ i + 1 }}. {{ q.prompt }}</div>
          <div v-if="q.type === 'mcq'" class="question-options">
            <div v-for="(opt, j) in q.options" :key="j" class="option-item">
              {{ String.fromCharCode(65 + j) }}. {{ opt }}
            </div>
          </div>
          <div class="answer-info">
            <el-text type="success">答案：{{ q.answer ?? "" }}</el-text>
          </div>
        </div>
      </div>
    </div>
    <div v-else>
      <el-tabs v-model="viewTab" type="border-card">
        <el-tab-pane label="作答" name="practice">
          <el-alert type="info" :closable="false" show-icon class="quiz-view-help">
            <template #title>功能范围与操作说明</template>
            <div>功能范围：仅处理当前题的作答与提交反馈。操作顺序：先答题并选择「蒙的/确定」→ 点击「提交」→ 查看解析后进入下一题或继续错题。</div>
          </el-alert>
          <div v-if="done">
            <el-result icon="success" title="已完成本知识点练习" sub-title="可点击“推荐下一步”查看建议" />
            <div class="action-row">
              <el-button type="primary" @click="resetPractice">重做</el-button>
            </div>
          </div>
          <div v-else-if="current" class="question-container">
            <div class="question-header">
              <div class="question-counter">Q{{ attemptedQuestions + 1 }} / {{ totalQuestions }}</div>
              <div class="question-meta">
                <el-text v-if="difficultyRange" type="info">{{ difficultyRange }}</el-text>
                <el-tag size="small" :type="modelUsed ? 'success' : 'info'">
                  {{ modelUsed ? "模型推荐" : "规则推荐" }}
                </el-tag>
              </div>
            </div>
            <div class="question-surface">
            <div v-if="wrongPractice.active" class="wrong-practice-indicator">
              <el-tag type="warning">错题重练中</el-tag>
              <el-text type="info">
                {{ wrongPractice.index + 1 }} / {{ wrongPractice.queue.length }}
              </el-text>
              <el-button size="small" type="default" @click="stopWrongPractice">退出</el-button>
            </div>
            <div class="question-prompt">{{ current.prompt }}</div>
            <div v-if="practiceQuestionMeta" class="question-cognitive-meta">
              <el-tag size="small" type="info">认知：{{ practiceQuestionMeta.levelLabel }}</el-tag>
              <el-tag v-if="practiceQuestionMeta.isHigh" size="small" type="warning">高阶题</el-tag>
              <el-tag v-for="t in practiceQuestionMeta.tags" :key="t" size="small" effect="plain">{{ t }}</el-tag>
            </div>
            <div v-if="current.type === 'mcq'" class="question-options">
              <el-radio-group v-model="selected">
                <el-radio v-for="(opt, i) in current.options" :key="i" :label="String.fromCharCode(65 + i)" class="option-item">
                  {{ String.fromCharCode(65 + i) }}. {{ opt }}
                </el-radio>
              </el-radio-group>
            </div>
            <div v-else class="blank-answer-wrap">
              <el-input v-model="blankAnswer" placeholder="输入你的答案" />
            </div>
            <div class="self-report-container">
              <div class="self-report-label">自信度：</div>
              <el-radio-group v-model="selfReport">
                <el-radio label="guess">蒙的</el-radio>
                <el-radio label="sure">确定</el-radio>
              </el-radio-group>
            </div>
            <div v-if="lastResult" class="result-container">
              <el-alert
                :type="lastResult.correct ? 'success' : 'warning'"
                :title="lastResult.correct ? '回答正确' : '回答错误'"
                :description="lastResult.explanation || '暂无解析'"
                show-icon
              />
              <div class="action-row">
                <el-button type="primary" @click="nextAfterAnswer">
                  {{ wrongPractice.active ? "继续错题" : "下一题" }}
                </el-button>
              </div>
            </div>
            <div v-else class="action-row">
              <el-button type="primary" @click="submit">提交</el-button>
            </div>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="记录概览" name="records">
          <el-alert type="info" :closable="false" show-icon class="quiz-view-help">
            <template #title>功能范围与操作说明</template>
            <div>功能范围：查看总题数、正确率与趋势统计，并支持导出。操作顺序：先看统计卡片与趋势，再按需「刷新」或「导出 CSV」。</div>
          </el-alert>
          <div v-if="historyLoading">
            <el-skeleton :rows="4" animated />
          </div>
          <div v-else>
            <div class="history-header">
              <el-button type="primary" plain size="small" @click="loadHistory">刷新</el-button>
              <el-button size="small" type="success" :href="exportUrl" target="_blank">导出 CSV</el-button>
            </div>

            <div class="stats-grid">
              <el-card shadow="never" class="stat-card">
                <div class="stat-label">总题数</div>
                <div class="stat-value">{{ statsDetail.total }}</div>
              </el-card>
              <el-card shadow="never" class="stat-card">
                <div class="stat-label">正确</div>
                <div class="stat-value">{{ statsDetail.correct }}</div>
              </el-card>
              <el-card shadow="never" class="stat-card">
                <div class="stat-label">错误</div>
                <div class="stat-value">{{ statsDetail.incorrect }}</div>
              </el-card>
              <el-card shadow="never" class="stat-card">
                <div class="stat-label">正确率</div>
                <div class="stat-value">{{ Math.round((statsDetail.accuracy || 0) * 100) }}%</div>
              </el-card>
            </div>

            <div v-if="statsDetail.daily?.length" class="trend-container section-card">
              <div class="section-header">
                <div class="section-title">趋势统计</div>
                <el-select v-model="trendMode" size="small" style="width: 120px">
                  <el-option label="按天" value="daily" />
                  <el-option label="按周" value="weekly" />
                  <el-option label="按月" value="monthly" />
                </el-select>
              </div>
              <el-table :data="trendItems" size="small" style="width: 100%" max-height="220">
                <el-table-column prop="date" label="时间" width="120" />
                <el-table-column prop="total" label="作答数" width="100" />
                <el-table-column prop="correct" label="正确数" width="100" />
                <el-table-column
                  label="正确率"
                  width="100"
                  :formatter="(row: any) => `${Math.round((row.accuracy || 0) * 100)}%`"
                />
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="错题" name="wrong">
          <el-alert type="info" :closable="false" show-icon class="quiz-view-help">
            <template #title>功能范围与操作说明</template>
            <div>功能范围：筛选错题并发起重练。操作顺序：先设置时间/题型筛选，再点击「重练错题」或对单题点「重做」。</div>
          </el-alert>
          <div class="wrong-container section-card">
            <div class="section-header">
              <div class="section-title">错题</div>
            </div>
            <div class="filter-controls">
              <el-select v-model="wrongDays" size="small" style="width: 120px" @change="loadWrong">
                <el-option label="全部时间" :value="0" />
                <el-option label="近7天" :value="7" />
                <el-option label="近14天" :value="14" />
                <el-option label="近30天" :value="30" />
              </el-select>
              <el-select v-model="wrongType" size="small" style="width: 100px">
                <el-option label="全部类型" value="" />
                <el-option label="选择题" value="mcq" />
                <el-option label="填空题" value="blank" />
              </el-select>
              <el-button size="small" type="primary" @click="startWrongPractice">重练错题</el-button>
            </div>
            <el-table
              :data="wrongItems"
              size="small"
              style="width: 100%"
              max-height="240"
              v-loading="wrongLoading"
              empty-text="暂无错题"
            >
              <el-table-column prop="created_at" label="时间" width="160" />
              <el-table-column prop="prompt" label="题干" />
              <el-table-column prop="difficulty" label="难度" width="80" />
              <el-table-column prop="type" label="类型" width="80" />
              <el-table-column width="100" label="操作">
                <template #default="{ row }">
                  <el-button size="small" type="primary" @click="redoWrong(row)">重做</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-container">
              <el-pagination
                background
                layout="prev, pager, next"
                :page-size="wrongPageSize"
                :total="wrongTotal"
                v-model:current-page="wrongPage"
                @current-change="loadWrong"
              />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="复习" name="review">
          <el-alert type="info" :closable="false" show-icon class="quiz-view-help">
            <template #title>功能范围与操作说明</template>
            <div>功能范围：查看复习队列与到期状态。操作顺序：优先处理「已到期」题目，必要时点击「刷新」同步最新复习安排。</div>
          </el-alert>
          <div class="review-container section-card">
            <div class="section-header">
              <div class="section-title">复习</div>
              <el-text type="info">待复习 {{ reviewTotal }}，已到期 {{ reviewDue }}</el-text>
              <el-button size="small" @click="loadReview" :loading="reviewLoading">刷新</el-button>
            </div>
            <el-table
              :data="reviewItems"
              size="small"
              style="width: 100%"
              max-height="220"
              v-loading="reviewLoading"
              empty-text="暂无复习任务"
            >
              <el-table-column prop="due_at" label="到期时间" width="180" />
              <el-table-column prop="prompt" label="题干" />
              <el-table-column prop="difficulty" label="难度" width="80" />
              <el-table-column prop="interval_days" label="间隔" width="80" />
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.overdue ? 'danger' : 'info'">
                    {{ row.overdue ? "已到期" : "待复习" }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-card>
</template>

<style scoped>
.quiz-card {
  border-radius: 28px;
  border: 1px solid rgba(31, 41, 55, 0.14);
  box-shadow: 0 16px 34px rgba(31, 41, 55, 0.08);
  background: linear-gradient(180deg, #f5f9ff 0%, #ffffff 100%);
  overflow: hidden;
}

.quiz-card__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.quiz-card__eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 800;
  color: #1f2937;
  display: inline-flex;
  width: fit-content;
  padding: 5px 10px;
  border-radius: 999px;
  background: #d7f9a8;
}

.quiz-card__title {
  margin-top: 8px;
  font-size: 24px;
  line-height: 1.2;
  font-weight: 800;
  color: #1f2937;
}

.quiz-card__caption {
  max-width: 360px;
  font-size: 13px;
  line-height: 1.7;
  color: #667d9b;
}

.quiz-card :deep(.el-card__header) {
  font-weight: 600;
  font-size: 16px;
  color: #1f2937;
  border-bottom: 1px solid rgba(31, 41, 55, 0.1);
  background: linear-gradient(180deg, #f4f8ff 0%, #ffffff 100%);
}

.quiz-card :deep(.el-card__body) {
  padding: 20px;
}

.quiz-card :deep(.el-tabs__nav-wrap)::after,
.quiz-card :deep(.el-tabs__active-bar) {
  display: none;
}

.quiz-card :deep(.el-tabs__item) {
  min-height: 42px;
  border-radius: 999px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  color: #1f2937;
  padding: 6px 16px;
  margin-right: 8px;
  transition: all 0.2s ease;
}

.quiz-card :deep(.el-tabs__item.is-active) {
  background: linear-gradient(180deg, #eef8ff 0%, #ffffff 100%);
  border-color: rgba(34, 197, 94, 0.28);
  color: #166534;
  box-shadow: 0 8px 14px rgba(31, 41, 55, 0.08);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 18px;
  text-align: center;
}

.preview-list {
  display: grid;
  gap: 16px;
}

.question-container {
  display: grid;
  gap: 16px;
}

.question-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--app-border);
}

.question-counter {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%);
  border: 1px solid rgba(31, 41, 55, 0.14);
  font-weight: 800;
  color: #1f2937;
  font-size: 13px;
}

.question-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.question-surface {
  display: grid;
  gap: 18px;
  padding: 20px;
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.wrong-practice-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px;
  background: rgba(255, 193, 7, 0.08);
  border-radius: 12px;
  border: 1px solid rgba(255, 193, 7, 0.22);
}

.question-cognitive-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
}

.question-prompt {
  font-weight: 800;
  margin-bottom: 4px;
  color: #243851;
  line-height: 1.65;
  font-size: 17px;
}

.question-options {
  display: grid;
  gap: 12px;
  margin-bottom: 4px;
}

.question-options :deep(.el-radio-group) {
  display: grid;
  gap: 12px;
}

.option-item {
  margin-right: 0;
  padding: 14px 16px;
  border-radius: 16px;
  transition: all 0.2s ease;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  line-height: 1.6;
  width: 100%;
}

.option-item:hover {
  background: #fff8ee;
  border-color: rgba(34, 197, 94, 0.22);
}

.question-options :deep(.el-radio__input.is-checked + .el-radio__label) {
  color: #24406b;
  font-weight: 700;
}

.question-options :deep(.el-radio__label) {
  white-space: normal;
  line-height: 1.65;
}

.blank-answer-wrap {
  padding: 14px;
  border-radius: 16px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.self-report-container {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin: 4px 0;
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1.5px solid rgba(31, 41, 55, 0.14);
}

.self-report-label {
  font-weight: 700;
  color: #29415f;
}

.result-container {
  margin-top: 8px;
}

.action-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.history-container {
  display: grid;
  gap: 20px;
}

.history-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.quiz-view-help {
  margin-bottom: 14px;
}

.stats-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  margin-bottom: 20px;
}

.stat-card {
  border-radius: 18px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  padding: 16px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.stat-label {
  font-size: 12px;
  color: var(--app-ink-soft);
  margin-bottom: 4px;
}

.stat-value {
  font-weight: 600;
  font-size: 18px;
  color: var(--app-ink);
}

.trend-container {
  margin-top: 20px;
}

.section-card {
  padding: 18px;
  border-radius: 22px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.section-title {
  font-weight: 600;
  color: var(--app-ink);
  font-size: 14px;
}

.filter-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border-radius: 16px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
}

.wrong-container,
.review-container {
  margin-top: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.question-item {
  padding: 16px;
  border-radius: 18px;
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.answer-info {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--app-border);
}

@media (max-width: 768px) {
  .quiz-card :deep(.el-card__body) {
    padding: 16px;
  }

  .quiz-card__header {
    align-items: flex-start;
  }
  
  .question-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .question-surface,
  .section-card {
    padding: 16px;
  }
  
  .question-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .action-row {
    flex-direction: column;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .filter-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
