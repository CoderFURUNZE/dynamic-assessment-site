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
  difficulty?: number;
};

type QuizTab = "practice" | "records" | "wrong" | "review";

const props = defineProps<{
  kpId: number | null;
  preview?: boolean;
  routeView?: QuizTab | null;
}>();

const emit = defineEmits<{
  (e: "mastery-updated"): void;
  (e: "view-change", view: QuizTab): void;
}>();

const loading = ref(false);
const submitting = ref(false);
const currentQuestion = ref<Question | null>(null);
const previewQuestions = ref<Question[]>([]);
const totalQuestions = ref(0);
const correctQuestions = ref(0);
const done = ref(false);
const selected = ref("");
const blankAnswer = ref("");
const startedAt = ref(Date.now());
const lastResult = ref<{ correct: boolean; explanation: string; mastery?: number | null } | null>(null);

const current = computed(() => currentQuestion.value);
const selectedOptionText = computed(() => {
  if (!current.value || current.value.type !== "mcq" || !selected.value) return "";
  const optionIndex = selected.value.toUpperCase().charCodeAt(0) - 65;
  return current.value.options?.[optionIndex] ?? selected.value;
});
const answerValue = computed(() => current.value?.type === "mcq" ? selectedOptionText.value : blankAnswer.value.trim());
const progressPercent = computed(() => {
  if (!totalQuestions.value) return 0;
  return Math.min(100, Math.round((correctQuestions.value / totalQuestions.value) * 100));
});

async function loadPreview() {
  if (!props.kpId) return;
  const res = await api.get(`/admin/questions?kp_id=${props.kpId}&page=1&page_size=200`);
  previewQuestions.value = res.data.items ?? [];
  currentQuestion.value = null;
  done.value = false;
  totalQuestions.value = previewQuestions.value.length;
  correctQuestions.value = 0;
}

async function loadNext() {
  if (!props.kpId) return;
  loading.value = true;
  try {
    const res = await api.get(`/practice/next?kp_id=${props.kpId}`, { skipGlobalLoading: true } as any);
    done.value = Boolean(res.data.done);
    totalQuestions.value = Number(res.data.total_questions ?? 0);
    correctQuestions.value = Number(res.data.attempted_questions ?? 0);
    currentQuestion.value = res.data.question ?? null;
    selected.value = "";
    blankAnswer.value = "";
    lastResult.value = null;
    startedAt.value = Date.now();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载题目失败");
  } finally {
    loading.value = false;
  }
}

async function load() {
  if (!props.kpId) return;
  if (props.preview) {
    loading.value = true;
    try {
      await loadPreview();
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail ?? "加载题目失败");
    } finally {
      loading.value = false;
    }
    return;
  }
  await loadNext();
}

async function submit() {
  if (!current.value || !props.kpId || submitting.value) return;
  if (!answerValue.value) {
    ElMessage.warning("请先作答");
    return;
  }
  submitting.value = true;
  try {
    const res = await api.post("/practice/submit", {
      kp_id: props.kpId,
      question_id: current.value.id,
      answer: answerValue.value,
      self_report: "sure",
      duration_ms: Math.max(0, Date.now() - startedAt.value),
    }, { skipGlobalLoading: true } as any);
    lastResult.value = {
      correct: Boolean(res.data.correct),
      explanation: String(res.data.explanation || ""),
      mastery: typeof res.data.mastery?.value === "number" ? Number(res.data.mastery.value) : null,
    };
    if (lastResult.value.mastery !== null) {
      correctQuestions.value = Math.max(correctQuestions.value, Math.round((lastResult.value.mastery || 0) * totalQuestions.value));
    }
    emit("mastery-updated");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "提交失败");
  } finally {
    submitting.value = false;
  }
}

watch(
  () => props.kpId,
  () => load(),
  { immediate: true },
);

watch(
  () => props.routeView,
  (view) => {
    if (view && view !== "practice") emit("view-change", "practice");
  },
);
</script>

<template>
  <el-card class="quiz-card" shadow="never">
    <template #header>
      <div class="quiz-card__header">
        <div>
          <div class="quiz-card__eyebrow">练习</div>
          <div class="quiz-card__title">完成题目，提高掌握度</div>
        </div>
        <div class="quiz-card__progress">
          <span>{{ correctQuestions }} / {{ totalQuestions }}</span>
          <el-progress :percentage="progressPercent" :show-text="false" :stroke-width="8" color="#16a34a" />
        </div>
      </div>
    </template>

    <div v-if="!kpId" class="empty-state">请选择知识点后开始练习</div>
    <el-skeleton v-else-if="loading" :rows="4" animated />

    <div v-else-if="preview" class="preview-list">
      <div v-if="previewQuestions.length === 0" class="empty-state">当前知识点暂无题目</div>
      <article v-for="(q, i) in previewQuestions" :key="q.id" class="question-item">
        <strong>Q{{ i + 1 }}. {{ q.prompt }}</strong>
        <div v-if="q.type === 'mcq'" class="question-options">
          <div v-for="(opt, j) in q.options" :key="j">{{ String.fromCharCode(65 + j) }}. {{ opt }}</div>
        </div>
      </article>
    </div>

    <el-result
      v-else-if="done"
      icon="success"
      title="本轮练习已完成"
      sub-title="所有题目完成后，系统会结合掌握度决定是否解锁下一知识点。"
    />

    <div v-else-if="current" class="question-container">
      <div class="question-counter">Q{{ Math.min(correctQuestions + 1, totalQuestions) }} / {{ totalQuestions }}</div>
      <div class="question-surface">
        <div class="question-prompt">{{ current.prompt }}</div>
        <el-radio-group v-if="current.type === 'mcq'" v-model="selected" class="question-options" :disabled="Boolean(lastResult)">
          <el-radio v-for="(opt, i) in current.options" :key="i" :label="String.fromCharCode(65 + i)" class="option-item">
            {{ String.fromCharCode(65 + i) }}. {{ opt }}
          </el-radio>
        </el-radio-group>
        <el-input v-else v-model="blankAnswer" :disabled="Boolean(lastResult)" placeholder="输入答案" />

        <el-alert
          v-if="lastResult"
          :type="lastResult.correct ? 'success' : 'warning'"
          :title="lastResult.correct ? '回答正确，掌握度已更新' : '回答错误，可以再试一次'"
          :description="lastResult.explanation || '暂无解析'"
          show-icon
          :closable="false"
        />

        <div class="action-row">
          <el-button v-if="!lastResult" type="primary" :loading="submitting" @click="submit">提交答案</el-button>
          <el-button v-else type="primary" @click="loadNext">继续练习</el-button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">当前知识点暂无可练习题目</div>
  </el-card>
</template>

<style scoped>
.quiz-card {
  border-radius: 18px;
  border: 1px solid rgba(31, 41, 55, 0.12);
  overflow: hidden;
}

.quiz-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.quiz-card__eyebrow {
  width: fit-content;
  padding: 5px 10px;
  border-radius: 999px;
  background: #dcfce7;
  color: #166534;
  font-size: 12px;
  font-weight: 800;
}

.quiz-card__title {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 800;
  color: #1f2937;
}

.quiz-card__progress {
  width: min(260px, 100%);
  display: grid;
  gap: 8px;
  color: #475569;
  font-weight: 700;
}

.empty-state {
  padding: 28px 16px;
  text-align: center;
  color: #64748b;
}

.preview-list,
.question-container,
.question-surface {
  display: grid;
  gap: 16px;
}

.question-counter {
  width: fit-content;
  padding: 7px 12px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #334155;
  font-weight: 800;
}

.question-surface,
.question-item {
  padding: 18px;
  border: 1px solid rgba(31, 41, 55, 0.12);
  border-radius: 16px;
  background: #ffffff;
}

.question-prompt {
  color: #1f2937;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.7;
}

.question-options {
  display: grid;
  gap: 10px;
}

.option-item {
  width: 100%;
  margin-right: 0;
  padding: 12px 14px;
  border: 1px solid rgba(31, 41, 55, 0.12);
  border-radius: 12px;
}

.option-item :deep(.el-radio__label) {
  white-space: normal;
  line-height: 1.6;
}

.action-row {
  display: flex;
  gap: 12px;
}
</style>
