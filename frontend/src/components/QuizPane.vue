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
};

const props = defineProps<{ kpId: number | null; preview?: boolean }>();
const emit = defineEmits<{ (e: "mastery-updated"): void }>();

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
const startedAt = ref<number>(0);
const lastResult = ref<{ correct: boolean; explanation: string } | null>(null);
const viewTab = ref<"practice" | "history">("practice");
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

const current = computed(() => currentQuestion.value);
const recentItems = computed(() => historyItems.value.slice(0, 10).reverse());
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
    // weekly
    const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const dayNum = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil((((tmp.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
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
    selected.value = "";
    blankAnswer.value = "";
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
    const res = await api.get(`/practice/wrong/page?${query.toString()}`);
    wrongItems.value = res.data.items ?? [];
    wrongTotal.value = Number(res.data.total ?? 0);
  } catch (e: any) {
    // ignore
  } finally {
    wrongLoading.value = false;
  }
}

async function submit() {
  if (!current.value || !props.kpId) return;
  const answer = current.value.type === "mcq" ? selected.value : blankAnswer.value;
  if (!answer) {
    ElMessage.warning("请作答后提交");
    return;
  }
  const duration_ms = Math.max(0, Date.now() - startedAt.value);
  try {
    const res = await api.post("/practice/submit", {
      kp_id: props.kpId,
      question_id: current.value.id,
      answer,
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
</script>

<template>
  <el-card>
    <template #header>练习题（选择 + 填空）</template>
    <div v-if="!kpId">
      <el-text type="info">请选择知识点后加载题目</el-text>
    </div>
    <div v-else-if="loading">
      <el-skeleton :rows="4" animated />
    </div>
    <div v-else-if="preview">
      <div v-if="questions.length === 0">
        <el-text type="info">暂无题目</el-text>
      </div>
      <div v-else style="display: grid; gap: 12px">
        <div v-for="(q, i) in questions" :key="q.id">
          <div style="font-weight: 600; margin-bottom: 6px">Q{{ i + 1 }}. {{ q.prompt }}</div>
          <div v-if="q.type === 'mcq'" style="display: grid; gap: 4px">
            <div v-for="(opt, j) in q.options" :key="j">
              {{ String.fromCharCode(65 + j) }}. {{ opt }}
            </div>
          </div>
          <div style="margin-top: 6px">
            <el-text type="success">答案：{{ q.answer ?? "" }}</el-text>
          </div>
        </div>
      </div>
    </div>
    <div v-else>
      <el-tabs v-model="viewTab" type="border-card">
        <el-tab-pane label="作答" name="practice">
          <div v-if="done">
            <el-result icon="success" title="已完成本知识点题目" sub-title="可点击“推荐下一步”查看建议" />
            <div style="margin-top: 10px; display: flex; gap: 8px">
              <el-button type="primary" @click="resetPractice">重做</el-button>
            </div>
          </div>
          <div v-else-if="current">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px">
              <div style="font-weight: 600">Q{{ attemptedQuestions + 1 }} / {{ totalQuestions }}</div>
              <div style="display: flex; gap: 10px; align-items: center">
                <el-text v-if="difficultyRange" type="info">难度区间 {{ difficultyRange }}</el-text>
                <el-tag size="small" :type="modelUsed ? 'success' : 'info'">
                  {{ modelUsed ? "模型推荐" : "规则推荐" }}
                </el-tag>
              </div>
            </div>
            <div
              v-if="wrongPractice.active"
              style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px"
            >
              <el-tag type="warning">错题重练中</el-tag>
              <el-text type="info">
                {{ wrongPractice.index + 1 }} / {{ wrongPractice.queue.length }}
              </el-text>
              <el-button size="small" type="default" @click="stopWrongPractice">退出错题</el-button>
            </div>
            <div style="font-weight: 600; margin-bottom: 8px">{{ current.prompt }}</div>
            <div v-if="current.type === 'mcq'">
              <el-radio-group v-model="selected">
                <el-radio v-for="(opt, i) in current.options" :key="i" :label="String.fromCharCode(65 + i)">
                  {{ String.fromCharCode(65 + i) }}. {{ opt }}
                </el-radio>
              </el-radio-group>
            </div>
            <div v-else>
              <el-input v-model="blankAnswer" placeholder="输入你的答案" />
            </div>
            <div v-if="lastResult" style="margin-top: 10px">
              <el-alert
                :type="lastResult.correct ? 'success' : 'warning'"
                :title="lastResult.correct ? '回答正确' : '回答错误'"
                :description="lastResult.explanation || '暂无解析'"
                show-icon
              />
              <div style="margin-top: 10px; display: flex; gap: 8px">
                <el-button type="primary" @click="nextAfterAnswer">
                  {{ wrongPractice.active ? "继续错题" : "下一题" }}
                </el-button>
              </div>
            </div>
            <div v-else style="margin-top: 10px">
              <el-button type="primary" @click="submit">提交</el-button>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="做题记录" name="history">
          <div v-if="historyLoading">
            <el-skeleton :rows="4" animated />
          </div>
          <div v-else>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px">
              <el-button type="primary" plain size="small" @click="loadHistory">刷新</el-button>
              <el-button size="small" type="success" :href="exportUrl" target="_blank">导出 CSV</el-button>
            </div>

            <div style="display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 10px">
              <el-card shadow="never">
                <div style="font-size: 12px; color: #666">总题数</div>
                <div style="font-weight: 600; font-size: 20px">{{ statsDetail.total }}</div>
              </el-card>
              <el-card shadow="never">
                <div style="font-size: 12px; color: #666">正确</div>
                <div style="font-weight: 600; font-size: 20px">{{ statsDetail.correct }}</div>
              </el-card>
              <el-card shadow="never">
                <div style="font-size: 12px; color: #666">错误</div>
                <div style="font-weight: 600; font-size: 20px">{{ statsDetail.incorrect }}</div>
              </el-card>
              <el-card shadow="never">
                <div style="font-size: 12px; color: #666">正确率</div>
                <div style="font-weight: 600; font-size: 20px">{{ Math.round((statsDetail.accuracy || 0) * 100) }}%</div>
              </el-card>
            </div>

            <div style="display: flex; gap: 16px; flex-wrap: wrap">
              <el-card shadow="never" style="width: 240px">
                <div style="font-weight: 600; margin-bottom: 8px">正确率</div>
                <div
                  style="width: 140px; height: 140px; border-radius: 50%; margin: 0 auto; background: #f3f3f3; position: relative"
                  :style="{ background: `conic-gradient(#5fbf7a 0 ${Math.round(correctRatio * 100)}%, #f2b5b5 ${Math.round(correctRatio * 100)}% 100%)` }"
                />
                <div style="text-align: center; margin-top: 8px">
                  <div style="font-weight: 600">{{ Math.round(correctRatio * 100) }}%</div>
                  <div style="font-size: 12px; color: #666">正确 {{ historyStats.correct }} / 错误 {{ historyStats.incorrect }}</div>
                </div>
              </el-card>
              <el-card shadow="never" style="flex: 1; min-width: 260px">
                <div style="font-weight: 600; margin-bottom: 8px">最近 10 次作答</div>
                <div style="display: flex; gap: 6px; align-items: flex-end; height: 120px">
                  <div
                    v-for="item in recentItems"
                    :key="item.id"
                    :title="item.correct ? '正确' : '错误'"
                    :style="{
                      height: item.correct ? '100%' : '40%',
                      width: '16px',
                      background: item.correct ? '#5fbf7a' : '#f2b5b5',
                      borderRadius: '6px',
                    }"
                  />
                </div>
                <div style="font-size: 12px; color: #666; margin-top: 6px">绿色=正确，粉色=错误</div>
              </el-card>
            </div>

            <div v-if="statsDetail.daily?.length" style="margin-top: 12px">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px">
                <div style="font-weight: 600">趋势统计</div>
                <el-select v-model="trendMode" size="small" style="width: 120px">
                  <el-option label="按天" value="daily" />
                  <el-option label="按周" value="weekly" />
                  <el-option label="按月" value="monthly" />
                </el-select>
              </div>
              <div style="display: flex; gap: 6px; align-items: flex-end; height: 120px; margin-bottom: 6px">
                <div
                  v-for="item in trendItems"
                  :key="item.date"
                  :title="`${item.date} 正确率 ${Math.round((item.accuracy || 0) * 100)}%`"
                  :style="{
                    height: `${Math.max(6, Math.round((item.accuracy || 0) * 100))}%`,
                    width: '18px',
                    background: '#5fbf7a',
                    borderRadius: '6px',
                  }"
                />
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

            <div style="margin-top: 12px">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px">
                <div style="font-weight: 600">错题</div>
                <el-text type="info">支持分页与时间筛选</el-text>
              </div>
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
                <el-select v-model="wrongDays" size="small" style="width: 140px" @change="loadWrong">
                  <el-option label="全部时间" :value="0" />
                  <el-option label="近7天" :value="7" />
                  <el-option label="近14天" :value="14" />
                  <el-option label="近30天" :value="30" />
                  <el-option label="近90天" :value="90" />
                </el-select>
                <el-button size="small" type="primary" @click="startWrongPractice">一键重练全部错题</el-button>
              </div>
              <el-table :data="wrongItems" size="small" style="width: 100%" max-height="240" v-loading="wrongLoading" empty-text="暂无错题">
                <el-table-column prop="created_at" label="时间" width="160" />
                <el-table-column prop="prompt" label="题干" />
                <el-table-column prop="difficulty" label="难度" width="80" />
                <el-table-column prop="type" label="类型" width="80" />
                <el-table-column width="120" label="操作">
                  <template #default="{ row }">
                    <el-button size="small" type="primary" @click="redoWrong(row)">重做</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div style="display: flex; justify-content: flex-end; margin-top: 8px">
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

            <div style="margin-top: 12px">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px">
                <div style="font-weight: 600">全部作答记录</div>
                <el-text type="info">最多展示 50 条</el-text>
              </div>
              <el-table :data="historyItems" size="small" style="width: 100%" max-height="260">
                <el-table-column prop="created_at" label="时间" width="180" />
                <el-table-column prop="prompt" label="题干" />
                <el-table-column prop="difficulty" label="难度" width="80" />
                <el-table-column label="结果" width="80">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.correct ? 'success' : 'danger'">
                      {{ row.correct ? "正确" : "错误" }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-card>
</template>
