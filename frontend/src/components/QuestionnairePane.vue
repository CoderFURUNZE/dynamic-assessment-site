<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type Item = {
  dimension_id: number;
  dimension_title: string;
  indicator_id: number;
  indicator_title: string;
  indicator_code: string;
  weight: number;
  score: number | null;
  note: string;
};

type LocalItem = Item & {
  questionTexts: string[];
  questionAnswers: Array<number | null>;
};

const SCORE_OPTIONS = [
  { label: "很少", value: 0.2 },
  { label: "偶尔", value: 0.4 },
  { label: "一般", value: 0.6 },
  { label: "经常", value: 0.8 },
  { label: "总是", value: 1.0 },
];

const QUESTION_BANK: Record<string, string[]> = {
  creative_thinking: ["我会主动尝试不同解法。", "我会把旧知识用到新问题中。", "我愿意提出自己的新想法。"],
  value_judgement: ["我会思考这种做法是否合理。", "我会比较不同方案的利弊。", "我会结合目标做选择。"],
  academic_background: ["我了解自己当前的基础水平。", "我知道自己在哪些前置知识上较弱。", "我清楚这门课和自己背景的关系。"],
  interest_type: ["我对这门课的内容有兴趣。", "我愿意主动探索课外资料。", "我愿意持续投入学习时间。"],
  intelligence_advantage: ["我知道自己擅长哪种学习方式。", "我会优先用擅长方式解决问题。", "我会在小组中发挥自己的优势。"],
  resource_preference: ["我会选择适合自己的资源类型。", "我会根据目标调整学习资源。", "我会复看关键资源内容。"],
  learning_strategy: ["我会先定学习计划再执行。", "我会根据效果调整学习方法。", "我会在阶段结束后复盘。"],
  text_interaction: ["我愿意通过文字讨论问题。", "我会在讨论区表达观点。", "我会阅读并吸收他人反馈。"],
  practice_interaction: ["我愿意做动手练习。", "我会把知识用于实际任务。", "遇到问题时我会反复练习直到掌握。"],
};

const props = defineProps<{
  courseId: number | null;
}>();

const emit = defineEmits<{
  (e: "saved"): void;
}>();

const loading = ref(false);
const saving = ref(false);
const items = ref<LocalItem[]>([]);

function scoreOptionLabel(score: number | null | undefined) {
  const option = SCORE_OPTIONS.find((item) => item.value === score);
  return option?.label ?? "未选择";
}

const groupedItems = computed(() => {
  const bucket = new Map<string, LocalItem[]>();
  for (const item of items.value) {
    const key = item.dimension_title || "未分组";
    const rows = bucket.get(key) ?? [];
    rows.push(item);
    bucket.set(key, rows);
  }
  return Array.from(bucket.entries()).map(([title, rows]) => ({ title, rows }));
});

const completedCount = computed(() => items.value.filter((item) => typeof item.score === "number").length);
const progressText = computed(() => `${completedCount.value}/${items.value.length}`);
const answeredQuestionCount = computed(() =>
  items.value.reduce((count, item) => count + item.questionAnswers.filter((value) => typeof value === "number").length, 0),
);
const totalQuestionCount = computed(() => items.value.reduce((count, item) => count + item.questionAnswers.length, 0));
const completionPercent = computed(() => {
  if (!items.value.length) return 0;
  return Math.round((completedCount.value / items.value.length) * 100);
});
const avgScore = computed(() => {
  const scored = items.value.filter((item) => typeof item.score === "number");
  if (!scored.length) return null;
  const sum = scored.reduce((acc, item) => acc + Number(item.score || 0), 0);
  return Number((sum / scored.length).toFixed(2));
});
const dimensionSummary = computed(() => {
  const bucket = new Map<string, number[]>();
  for (const item of items.value) {
    if (typeof item.score !== "number") continue;
    const key = item.dimension_title || "未分组";
    const rows = bucket.get(key) ?? [];
    rows.push(item.score);
    bucket.set(key, rows);
  }
  return Array.from(bucket.entries())
    .map(([title, values]) => ({
      title,
      avg: Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2)),
      count: values.length,
    }))
    .sort((a, b) => b.avg - a.avg);
});
const strongestItem = computed(() => {
  const scored = items.value.filter((item) => typeof item.score === "number");
  if (!scored.length) return null;
  return [...scored].sort((a, b) => Number(b.score) - Number(a.score))[0];
});
const weakestItem = computed(() => {
  const scored = items.value.filter((item) => typeof item.score === "number");
  if (!scored.length) return null;
  return [...scored].sort((a, b) => Number(a.score) - Number(b.score))[0];
});
const canSave = computed(() => items.value.some((item) => item.questionAnswers.some((value) => typeof value === "number")));

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}

function getQuestionTexts(item: Item): string[] {
  const byCode = QUESTION_BANK[item.indicator_code];
  if (byCode?.length) return byCode.slice(0, 3);
  return [
    `在“${item.indicator_title}”上，我近期表现稳定。`,
    `针对“${item.indicator_title}”，我会主动调整学习方式。`,
    `我能在“${item.indicator_title}”上持续改进。`,
  ];
}

function scoreToAnswers(score: number | null, count: number): Array<number | null> {
  if (typeof score !== "number") return new Array(count).fill(null);
  return new Array(count).fill(clamp01(score));
}

function calcAutoScore(item: LocalItem): number | null {
  const answered = item.questionAnswers.filter((value): value is number => typeof value === "number");
  if (!answered.length) return null;
  const avg = answered.reduce((sum, value) => sum + value, 0) / answered.length;
  return Number(clamp01(avg).toFixed(2));
}

function applyAutoScore(item: LocalItem) {
  item.score = calcAutoScore(item);
}

async function load() {
  if (!props.courseId) {
    items.value = [];
    return;
  }
  loading.value = true;
  try {
    const res = await api.get(`/portrait/questionnaire-input?course_id=${props.courseId}`);
    const rows: Item[] = res.data?.items ?? [];
    items.value = rows.map((item) => {
      const questionTexts = getQuestionTexts(item);
      return {
        ...item,
        questionTexts,
        questionAnswers: scoreToAnswers(item.score, questionTexts.length),
      };
    });
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载补充问卷失败");
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!props.courseId) {
    ElMessage.warning("请先选择课程");
    return;
  }
  if (!canSave.value) {
    ElMessage.warning("请至少完成一项问卷作答");
    return;
  }
  saving.value = true;
  try {
    await api.put(`/portrait/questionnaire-input?course_id=${props.courseId}`, {
      inputs: items.value.map((item) => ({
        indicator_id: item.indicator_id,
        score: calcAutoScore(item),
        note: item.note || "",
      })),
    });
    ElMessage.success(`补充内容已保存，已更新 ${completedCount.value} 项`);
    await load();
    emit("saved");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
  } finally {
    saving.value = false;
  }
}

watch(
  () => props.courseId,
  () => {
    load();
  },
  { immediate: true },
);
</script>

<template>
  <el-card class="panel-card questionnaire-pane" shadow="never" v-loading="loading">
    <template #header>
      <div class="questionnaire-pane__header">
        <div>
          <div class="questionnaire-pane__title">补充问卷</div>
          <div class="questionnaire-pane__subtitle">按课程要求补充填写，系统会用于更新学习画像结果。</div>
        </div>
        <div class="questionnaire-pane__meta">
          <span>完成度 {{ progressText }}</span>
          <span>题项进度 {{ answeredQuestionCount }}/{{ totalQuestionCount }}</span>
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
        </div>
      </div>
    </template>

    <div v-if="!courseId" class="questionnaire-pane__empty">
      <el-empty description="请先在顶部选择课程" :image-size="90" />
    </div>

    <div v-else-if="items.length === 0" class="questionnaire-pane__empty">
      <el-empty description="这门课还没有启用补充问卷项" :image-size="90" />
      <div class="questionnaire-pane__hint">老师启用问卷型指标后，这里会自动出现可填写内容。</div>
    </div>

    <div v-else class="questionnaire-pane__content">
      <section class="questionnaire-summary">
        <div class="questionnaire-summary__cards">
          <div class="questionnaire-summary__card">
            <span>问卷完成度</span>
            <strong>{{ completionPercent }}%</strong>
          </div>
          <div class="questionnaire-summary__card">
            <span>平均得分</span>
            <strong>{{ avgScore == null ? "未计算" : `${Math.round(avgScore * 100)}%` }}</strong>
          </div>
          <div class="questionnaire-summary__card">
            <span>优势指标</span>
            <strong>{{ strongestItem ? strongestItem.indicator_title : "暂无" }}</strong>
          </div>
          <div class="questionnaire-summary__card">
            <span>待提升指标</span>
            <strong>{{ weakestItem ? weakestItem.indicator_title : "暂无" }}</strong>
          </div>
        </div>

        <div class="questionnaire-summary__chart">
          <div class="questionnaire-summary__title">按维度结果</div>
          <div v-if="dimensionSummary.length === 0" class="questionnaire-summary__empty">填写后这里会显示维度结果</div>
          <div v-else class="dimension-bars">
            <div v-for="row in dimensionSummary" :key="row.title" class="dimension-bars__row">
              <div class="dimension-bars__head">
                <span>{{ row.title }}</span>
                <strong>{{ Math.round(row.avg * 100) }}%</strong>
              </div>
              <div class="dimension-bars__track">
                <div class="dimension-bars__value" :style="{ width: `${Math.round(row.avg * 100)}%` }" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-for="group in groupedItems" :key="group.title" class="questionnaire-group">
        <div class="questionnaire-group__title">{{ group.title }}</div>
        <div class="questionnaire-group__list">
          <article v-for="item in group.rows" :key="item.indicator_id" class="questionnaire-item">
            <div class="questionnaire-item__head">
              <strong>{{ item.indicator_title }}</strong>
              <span>学生补充项</span>
            </div>
            <div class="questionnaire-item__question-title">题项作答</div>
            <div class="questionnaire-item__questions">
              <div v-for="(text, qIndex) in item.questionTexts" :key="`${item.indicator_id}-${qIndex}`" class="question-row">
                <div class="question-row__text">{{ qIndex + 1 }}. {{ text }}</div>
                <el-radio-group v-model="item.questionAnswers[qIndex]" size="small" @change="applyAutoScore(item)">
                  <el-radio-button
                    v-for="option in SCORE_OPTIONS"
                    :key="`${item.indicator_id}-${qIndex}-${option.value}`"
                    :label="option.value"
                  >
                    {{ option.label }}
                  </el-radio-button>
                </el-radio-group>
              </div>
            </div>
            <div class="questionnaire-item__score-row">
              <span>系统换算结果：{{ scoreOptionLabel(calcAutoScore(item)) }}</span>
            </div>
            <div class="questionnaire-item__hint">
              完成上面的题项后，系统会自动换算当前指标结果，不需要你手动设置权重或评分规则。
            </div>
            <el-input v-model="item.note" type="textarea" :rows="2" placeholder="可选：补充说明、标签或当前学习感受" />
          </article>
        </div>
      </section>

      <div class="questionnaire-pane__actions">
        <el-button type="primary" :loading="saving" :disabled="!canSave" @click="save">保存补充内容</el-button>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.questionnaire-pane__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.questionnaire-pane__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.questionnaire-pane__subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--app-ink-soft);
}

.questionnaire-pane__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #4f6782;
}

.questionnaire-pane__empty {
  display: grid;
  justify-items: center;
  gap: 8px;
}

.questionnaire-pane__hint {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.questionnaire-pane__content {
  display: grid;
  gap: 14px;
}

.questionnaire-summary {
  border: 1px solid #dce6f2;
  border-radius: 16px;
  padding: 12px;
  background: #f7fbff;
  display: grid;
  gap: 12px;
}

.questionnaire-summary__cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.questionnaire-summary__card {
  border: 1px solid #e1eaf4;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  display: grid;
  gap: 4px;
}

.questionnaire-summary__card span {
  font-size: 12px;
  color: #5d7694;
}

.questionnaire-summary__card strong {
  font-size: 16px;
  color: #2a456b;
}

.questionnaire-summary__chart {
  border: 1px solid #e1eaf4;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.questionnaire-summary__title {
  font-size: 13px;
  font-weight: 700;
  color: #37557f;
  margin-bottom: 8px;
}

.questionnaire-summary__empty {
  font-size: 12px;
  color: #68819e;
}

.dimension-bars {
  display: grid;
  gap: 8px;
}

.dimension-bars__row {
  display: grid;
  gap: 4px;
}

.dimension-bars__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #4a6485;
}

.dimension-bars__track {
  height: 10px;
  border-radius: 999px;
  background: #e7eef8;
  overflow: hidden;
}

.dimension-bars__value {
  height: 100%;
  border-radius: inherit;
  background: #6d92cf;
}

.questionnaire-group {
  border: 1px solid var(--app-border);
  border-radius: 16px;
  padding: 12px;
  background: #fcfdff;
}

.questionnaire-group__title {
  font-size: 14px;
  font-weight: 700;
  color: #2e4668;
  margin-bottom: 10px;
}

.questionnaire-group__list {
  display: grid;
  gap: 10px;
}

.questionnaire-item {
  border: 1px solid var(--app-border);
  border-radius: 14px;
  padding: 10px;
  background: #fff;
  display: grid;
  gap: 8px;
}

.questionnaire-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #476182;
  font-size: 12px;
}

.questionnaire-item__question-title {
  font-size: 12px;
  color: #587294;
  font-weight: 700;
}

.questionnaire-item__questions {
  display: grid;
  gap: 8px;
}

.question-row {
  border: 1px solid var(--app-border);
  border-radius: 12px;
  padding: 8px;
  display: grid;
  gap: 6px;
  background: #fcfdff;
}

.question-row__text {
  font-size: 12px;
  color: #2d486d;
}

.questionnaire-item__score-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  font-size: 12px;
  color: #486487;
}

.questionnaire-item__hint {
  font-size: 12px;
  color: #6d7f98;
  line-height: 1.5;
}

.questionnaire-pane__actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1100px) {
  .questionnaire-summary__cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .questionnaire-summary__cards {
    grid-template-columns: 1fr;
  }
}
</style>
