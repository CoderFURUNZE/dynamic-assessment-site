<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const props = defineProps<{ kpId: number | null }>();

type Question = {
  id: number;
  kp_id: number;
  type: string;
  prompt: string;
  options: string[];
  difficulty: number;
};

const count = ref(5);
const durationMinutes = ref(15);
const sessionId = ref<number | null>(null);
const questions = ref<Question[]>([]);
const index = ref(0);
const selected = ref("");
const blankAnswer = ref("");
const rationale = ref("");
const lastResult = ref<{ correct: boolean; explanation: string } | null>(null);
const timer = ref<number | null>(null);
const remainingSeconds = ref(0);
const summary = ref<{ total: number; correct: number; accuracy: number } | null>(null);

const currentQuestion = computed(() => questions.value[index.value] ?? null);
const isRunning = computed(() => sessionId.value !== null && summary.value === null);
const progressText = computed(() => `${index.value + 1}/${questions.value.length || 0}`);
const timeText = computed(() => {
  const total = Math.max(0, remainingSeconds.value);
  const min = Math.floor(total / 60);
  const sec = total % 60;
  return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
});

function resetForm() {
  selected.value = "";
  blankAnswer.value = "";
  rationale.value = "";
  lastResult.value = null;
}

function stopTimer() {
  if (timer.value) window.clearInterval(timer.value);
  timer.value = null;
}

function startTimer() {
  stopTimer();
  timer.value = window.setInterval(() => {
    remainingSeconds.value -= 1;
    if (remainingSeconds.value <= 0) {
      remainingSeconds.value = 0;
      finishInterview();
    }
  }, 1000);
}

async function startInterview() {
  if (!props.kpId) {
    ElMessage.warning("请选择知识点");
    return;
  }
  try {
    const res = await api.post("/interview/start", {
      kp_id: props.kpId,
      count: count.value,
      duration_minutes: durationMinutes.value,
    });
    sessionId.value = res.data.session_id;
    questions.value = res.data.questions ?? [];
    index.value = 0;
    summary.value = null;
    remainingSeconds.value = Number(res.data.duration_minutes ?? durationMinutes.value) * 60;
    resetForm();
    startTimer();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "启动失败");
  }
}

async function submitAnswer() {
  if (!sessionId.value || !currentQuestion.value) return;
  const answer = currentQuestion.value.type === "mcq" ? selected.value : blankAnswer.value;
  if (!answer) {
    ElMessage.warning("请作答后提交");
    return;
  }
  try {
    const res = await api.post("/interview/submit", {
      session_id: sessionId.value,
      question_id: currentQuestion.value.id,
      answer,
      rationale: rationale.value,
    });
    lastResult.value = {
      correct: Boolean(res.data.correct),
      explanation: String(res.data.explanation ?? ""),
    };
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "提交失败");
  }
}

async function nextQuestion() {
  if (!questions.value.length) return;
  if (index.value + 1 >= questions.value.length) {
    await finishInterview();
    return;
  }
  index.value += 1;
  resetForm();
}

async function finishInterview() {
  if (!sessionId.value) return;
  stopTimer();
  try {
    const res = await api.post("/interview/finish", { session_id: sessionId.value });
    summary.value = {
      total: Number(res.data.total ?? 0),
      correct: Number(res.data.correct ?? 0),
      accuracy: Number(res.data.accuracy ?? 0),
    };
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "结束失败");
  }
}

function resetAll() {
  stopTimer();
  sessionId.value = null;
  questions.value = [];
  index.value = 0;
  remainingSeconds.value = 0;
  summary.value = null;
  resetForm();
}

onBeforeUnmount(() => stopTimer());
</script>

<template>
  <el-card>
    <template #header>模拟复试（限时答题 + 口述要点）</template>

    <div v-if="!isRunning && !summary" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
      <el-input-number v-model="count" :min="1" :max="20" :step="1" size="small" />
      <el-text type="info">题数</el-text>
      <el-input-number v-model="durationMinutes" :min="5" :max="120" :step="5" size="small" />
      <el-text type="info">分钟</el-text>
      <el-button type="primary" @click="startInterview">开始模拟</el-button>
    </div>

    <div v-else-if="summary">
      <el-result icon="success" title="模拟完成">
        <template #sub-title>
          正确 {{ summary.correct }} / {{ summary.total }}，正确率 {{ Math.round(summary.accuracy * 100) }}%
        </template>
      </el-result>
      <div style="display: flex; gap: 8px; justify-content: center">
        <el-button type="primary" @click="startInterview">再来一场</el-button>
        <el-button @click="resetAll">返回设置</el-button>
      </div>
    </div>

    <div v-else>
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px">
        <div style="display: flex; gap: 10px; align-items: center">
          <el-tag type="info">进度 {{ progressText }}</el-tag>
          <el-tag type="warning">剩余 {{ timeText }}</el-tag>
        </div>
        <el-button size="small" type="danger" @click="finishInterview">结束</el-button>
      </div>

      <div v-if="currentQuestion" style="display: grid; gap: 8px">
        <div style="font-weight: 600">{{ currentQuestion.prompt }}</div>
        <div v-if="currentQuestion.type === 'mcq'" style="display: grid; gap: 6px">
          <el-radio-group v-model="selected">
            <el-radio v-for="(opt, i) in currentQuestion.options" :key="i" :label="String.fromCharCode(65 + i)">
              {{ String.fromCharCode(65 + i) }}. {{ opt }}
            </el-radio>
          </el-radio-group>
        </div>
        <div v-else>
          <el-input v-model="blankAnswer" placeholder="输入你的答案" />
        </div>
        <el-input
          v-model="rationale"
          type="textarea"
          :rows="3"
          placeholder="口述要点：这题你会怎么解释给老师听？"
        />

        <div v-if="lastResult">
          <el-alert
            :type="lastResult.correct ? 'success' : 'warning'"
            :title="lastResult.correct ? '回答正确' : '回答错误'"
            :description="lastResult.explanation || '暂无解析'"
            show-icon
          />
          <div style="margin-top: 8px; display: flex; gap: 8px">
            <el-button type="primary" @click="nextQuestion">下一题</el-button>
          </div>
        </div>
        <div v-else>
          <el-button type="primary" @click="submitAnswer">提交</el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>
