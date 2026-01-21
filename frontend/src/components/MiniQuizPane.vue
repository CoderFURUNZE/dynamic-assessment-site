<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";

type Resource = { id: number; kp_id: number; type: string; title: string; url: string };
type QuizItem = {
  id: number;
  type: string;
  prompt: string;
  options: string[];
  answer?: string | null;
  explanation?: string | null;
};
type Quiz = { quiz_id: number; kp_id: number; items: QuizItem[] };
type QuizDetail = { item_id: number; correct: boolean; correct_answer?: string | null; hint?: string | null };

const props = defineProps<{ kpId: number | null; preview?: boolean }>();
const emit = defineEmits<{ (e: "mastery-updated"): void }>();

const loading = ref(false);
const ready = ref(false);
const quiz = ref<Quiz | null>(null);
const answers = ref<Record<number, string>>({});
const submitted = ref<{ accuracy: number; passed: boolean; details: QuizDetail[] } | null>(null);
const isStudent = computed(() => getRole() === "student");
const isPreview = computed(() => Boolean(props.preview) || !isStudent.value);
const startedAt = ref<number>(0);

const hasVideo = ref(false);
const allowQuiz = ref(true);
const progressHint = ref("");
const headerText = computed(() => (isPreview.value ? "小测预览" : "小测（看完视频后解锁）"));

async function checkVideoGate() {
  if (!props.kpId) return;
  if (isPreview.value) {
    allowQuiz.value = true;
    progressHint.value = "";
    return;
  }
  try {
    const res = await api.get(`/content/resources?kp_id=${props.kpId}`);
    const list: Resource[] = res.data ?? [];
    hasVideo.value = list.some((r) => r.type === "video");
    if (!hasVideo.value) {
      allowQuiz.value = true;
      progressHint.value = "";
      return;
    }
    const prog = await api.get(`/content/video/progress?kp_id=${props.kpId}`);
    const rows = prog.data ?? [];
    const done = rows.some((r: any) => Boolean(r.completed));
    const watchedSeconds = rows.reduce((acc: number, r: any) => acc + Number(r.watched_seconds ?? 0), 0);
    if (done || watchedSeconds >= 60) {
      allowQuiz.value = true;
      progressHint.value = "";
      return;
    }
    allowQuiz.value = false;
    progressHint.value = "请先观看视频（至少停留 1 分钟）后再进行小测。";
  } catch {
    allowQuiz.value = true;
    progressHint.value = "";
  }
}

async function loadQuiz() {
  if (!props.kpId) return;
  loading.value = true;
  try {
    await checkVideoGate();
    if (!allowQuiz.value) {
      ready.value = true;
      quiz.value = null;
      return;
    }
    const res = await api.get(`/content/quiz/${props.kpId}`);
    quiz.value = res.data;
    answers.value = {};
    submitted.value = null;
    startedAt.value = Date.now();
    ready.value = true;
  } catch (e: any) {
    const msg = e?.response?.data?.detail ?? "加载小测失败";
    ElMessage.error(msg);
    quiz.value = null;
    ready.value = true;
  } finally {
    loading.value = false;
  }
}

async function submit() {
  if (!props.kpId || !quiz.value) return;
  if (!allAnswered()) {
    ElMessage.warning("请先完成所有题目再提交");
    return;
  }
  const duration_ms = Math.max(0, Date.now() - startedAt.value);
  try {
    const payload = {
      quiz_id: quiz.value.quiz_id,
      kp_id: props.kpId,
      duration_ms,
      answers: quiz.value.items.map((it) => ({ item_id: it.id, answer: (answers.value[it.id] ?? "").trim() })),
    };
    const res = await api.post("/content/quiz/submit", payload);
    submitted.value = res.data;
    ElMessage.success("小测已提交");
    emit("mastery-updated");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "提交失败");
  }
}

function allAnswered(): boolean {
  if (!quiz.value) return false;
  return quiz.value.items.every((it) => (answers.value[it.id] ?? "").trim() !== "");
}

function retry() {
  submitted.value = null;
  startedAt.value = Date.now();
}

watch(
  () => props.kpId,
  () => loadQuiz(),
  { immediate: true }
);

onMounted(() => loadQuiz());
</script>

<template>
  <el-card>
    <template #header>{{ headerText }}</template>
    <div v-if="!kpId">
      <el-text type="info">请选择知识点</el-text>
    </div>
    <div v-else-if="loading">
      <el-skeleton :rows="4" animated />
    </div>
    <div v-else-if="!allowQuiz">
      <el-alert type="warning" :closable="false" :description="progressHint" show-icon />
    </div>
    <div v-else-if="ready && !quiz">
      <el-text type="info">当前知识点未配置小测</el-text>
    </div>
    <div v-else-if="quiz">
      <div style="display: grid; gap: 12px">
        <div v-for="(item, i) in quiz.items" :key="item.id">
          <div style="font-weight: 600; margin-bottom: 6px">Q{{ i + 1 }}. {{ item.prompt }}</div>
          <div v-if="item.type === 'mcq'">
            <el-radio-group v-model="answers[item.id]">
              <el-radio v-for="(opt, j) in item.options" :key="j" :label="String.fromCharCode(65 + j)">
                {{ String.fromCharCode(65 + j) }}. {{ opt }}
              </el-radio>
            </el-radio-group>
          </div>
          <div v-else>
            <el-input v-model="answers[item.id]" placeholder="输入你的答案" />
          </div>
          <div v-if="isPreview" style="margin-top: 6px">
            <el-text type="success">正确答案：{{ item.answer ?? "" }}</el-text>
            <el-text v-if="item.explanation" type="info" style="margin-left: 6px">解析：{{ item.explanation }}</el-text>
          </div>
        </div>
      </div>

      <div v-if="isStudent" style="margin-top: 12px">
        <el-button v-if="!submitted" type="primary" @click="submit">提交小测</el-button>
        <el-button v-else @click="retry">重新作答</el-button>
      </div>

      <el-card v-if="submitted" shadow="never" style="margin-top: 12px">
        <template #header>小测结果</template>
        <el-text>正确率：{{ Math.round(submitted.accuracy * 100) }}%</el-text>
        <el-text style="margin-left: 10px">通过：{{ submitted.passed ? "是" : "否" }}</el-text>
        <div style="margin-top: 8px; display: grid; gap: 6px">
          <div v-for="d in submitted.details" :key="d.item_id">
            <el-tag size="small" :type="d.correct ? 'success' : 'danger'">
              {{ d.correct ? "正确" : "错误" }}
            </el-tag>
            <el-text style="margin-left: 6px">正确答案：{{ d.correct_answer ?? "" }}</el-text>
            <el-text v-if="d.hint" type="info" style="margin-left: 6px">解析：{{ d.hint }}</el-text>
          </div>
        </div>
      </el-card>
    </div>
  </el-card>
</template>
