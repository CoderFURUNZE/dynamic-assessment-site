<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type NodeDetail = {
  resource_list: Array<{ id: number; kp_id: number; type: string; title: string; url: string }>;
  task_list: Array<{ id: number; kp_id: number; type: string; title: string; description: string; link_url: string; sort_order: number }>;
  quiz_or_exam_list: Array<{ kind: string; id: number; title: string; item_count: number; pass_accuracy?: number | null; description?: string; link_url?: string }>;
};

type QuestionRow = {
  id: number;
  kp_id: number;
  type: string;
  prompt: string;
  options: string[];
  answer: string;
  explanation: string;
  difficulty: number;
};

type QuizRow = {
  quiz_id: number | null;
  pass_accuracy: number;
  items: Array<{ id: number; type: string; prompt: string; options: string[]; answer: string; explanation: string; key_item?: boolean }>;
};

const props = defineProps<{
  kpId: number | null;
  kpCode?: string;
  kpTitle?: string;
}>();

const loading = ref(false);
const detail = ref<NodeDetail | null>(null);
const practiceRows = ref<QuestionRow[]>([]);
const quiz = ref<QuizRow>({ quiz_id: null, pass_accuracy: 0.8, items: [] });

const resourceDialogOpen = ref(false);
const resourceEditingId = ref<number | null>(null);
const resourceForm = reactive({
  title: "",
  url: "",
  type: "note",
});

const taskDialogOpen = ref(false);
const taskEditingId = ref<number | null>(null);
const taskForm = reactive({
  title: "",
  description: "",
  link_url: "",
  type: "task",
  sort_order: 0,
});

const questionDialogOpen = ref(false);
const questionEditingId = ref<number | null>(null);
const questionForm = reactive({
  type: "mcq",
  prompt: "",
  options_text: "",
  answer: "",
  explanation: "",
  difficulty: 0.5,
});

const quizDialogOpen = ref(false);
const quizEditingId = ref<number | null>(null);
const quizForm = reactive({
  type: "mcq",
  prompt: "",
  options_text: "",
  answer: "",
  explanation: "",
  key_item: false,
});

const resourceSummary = computed(() => detail.value?.resource_list ?? []);
const taskSummary = computed(() => detail.value?.task_list ?? []);
const examSummary = computed(() => (detail.value?.quiz_or_exam_list ?? []).filter((item) => item.kind === "exam"));
const questionCount = computed(() => practiceRows.value.length);
const quizCount = computed(() => quiz.value.items.length);

function parseOptions(text: string) {
  return text
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function load() {
  if (!props.kpId) {
    detail.value = null;
    practiceRows.value = [];
    quiz.value = { quiz_id: null, pass_accuracy: 0.8, items: [] };
    return;
  }
  loading.value = true;
  try {
    const [detailRes, practiceRes, quizRes] = await Promise.all([
      api.get(`/graph/node/${props.kpId}`),
      api.get(`/admin/questions?kp_id=${props.kpId}&page=1&page_size=200`),
      api.get(`/admin/quiz?kp_id=${props.kpId}`),
    ]);
    detail.value = detailRes.data;
    practiceRows.value = practiceRes.data.items ?? [];
    quiz.value = {
      quiz_id: quizRes.data.quiz_id ?? null,
      pass_accuracy: Number(quizRes.data.pass_accuracy ?? 0.8),
      items: quizRes.data.items ?? [],
    };
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载节点内容失败");
  } finally {
    loading.value = false;
  }
}

function resetResourceForm() {
  resourceEditingId.value = null;
  resourceForm.title = "";
  resourceForm.url = "";
  resourceForm.type = "note";
}

function openResourceCreate() {
  resetResourceForm();
  resourceDialogOpen.value = true;
}

function openResourceEdit(row: { id: number; title: string; url: string; type: string }) {
  resourceEditingId.value = row.id;
  resourceForm.title = row.title;
  resourceForm.url = row.url;
  resourceForm.type = row.type;
  resourceDialogOpen.value = true;
}

async function saveResource() {
  if (!props.kpId) return;
  const payload = {
    kp_id: props.kpId,
    title: resourceForm.title,
    url: resourceForm.url,
    type: resourceForm.type,
  };
  try {
    if (resourceEditingId.value) {
      await api.put(`/admin/kp-resources/${resourceEditingId.value}`, payload);
      ElMessage.success("资源已更新");
    } else {
      await api.post("/admin/kp-resources", payload);
      ElMessage.success("资源已创建");
    }
    resourceDialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存资源失败");
  }
}

async function removeResource(id: number) {
  try {
    await api.delete(`/admin/kp-resources/${id}`);
    ElMessage.success("资源已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除资源失败");
  }
}

function resetTaskForm() {
  taskEditingId.value = null;
  taskForm.title = "";
  taskForm.description = "";
  taskForm.link_url = "";
  taskForm.type = "task";
  taskForm.sort_order = 0;
}

function openTaskCreate() {
  resetTaskForm();
  taskDialogOpen.value = true;
}

function openTaskEdit(row: { id: number; title: string; description: string; link_url: string; type: string; sort_order: number }) {
  taskEditingId.value = row.id;
  taskForm.title = row.title;
  taskForm.description = row.description;
  taskForm.link_url = row.link_url;
  taskForm.type = row.type;
  taskForm.sort_order = row.sort_order;
  taskDialogOpen.value = true;
}

async function saveTask() {
  if (!props.kpId) return;
  const payload = {
    kp_id: props.kpId,
    title: taskForm.title,
    description: taskForm.description,
    link_url: taskForm.link_url,
    type: taskForm.type,
    sort_order: taskForm.sort_order,
  };
  try {
    if (taskEditingId.value) {
      await api.put(`/admin/kp-tasks/${taskEditingId.value}`, payload);
      ElMessage.success("任务已更新");
    } else {
      await api.post("/admin/kp-tasks", payload);
      ElMessage.success("任务已创建");
    }
    taskDialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存任务失败");
  }
}

async function removeTask(id: number) {
  try {
    await api.delete(`/admin/kp-tasks/${id}`);
    ElMessage.success("任务已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除任务失败");
  }
}

function resetQuestionForm() {
  questionEditingId.value = null;
  questionForm.type = "mcq";
  questionForm.prompt = "";
  questionForm.options_text = "";
  questionForm.answer = "";
  questionForm.explanation = "";
  questionForm.difficulty = 0.5;
}

function openQuestionCreate() {
  resetQuestionForm();
  questionDialogOpen.value = true;
}

function openQuestionEdit(row: QuestionRow) {
  questionEditingId.value = row.id;
  questionForm.type = row.type;
  questionForm.prompt = row.prompt;
  questionForm.options_text = (row.options ?? []).join("\n");
  questionForm.answer = row.answer;
  questionForm.explanation = row.explanation;
  questionForm.difficulty = row.difficulty;
  questionDialogOpen.value = true;
}

async function saveQuestion() {
  if (!props.kpId) return;
  const payload = {
    kp_id: props.kpId,
    type: questionForm.type,
    prompt: questionForm.prompt,
    options: questionForm.type === "mcq" ? parseOptions(questionForm.options_text) : [],
    answer: questionForm.answer,
    explanation: questionForm.explanation,
    difficulty: questionForm.difficulty,
  };
  try {
    if (questionEditingId.value) {
      await api.put(`/admin/questions/${questionEditingId.value}`, payload);
      ElMessage.success("练习题已更新");
    } else {
      await api.post("/admin/questions", payload);
      ElMessage.success("练习题已创建");
    }
    questionDialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存练习题失败");
  }
}

async function removeQuestion(id: number) {
  try {
    await api.delete(`/admin/questions/${id}`);
    ElMessage.success("练习题已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除练习题失败");
  }
}

function resetQuizForm() {
  quizEditingId.value = null;
  quizForm.type = "mcq";
  quizForm.prompt = "";
  quizForm.options_text = "";
  quizForm.answer = "";
  quizForm.explanation = "";
  quizForm.key_item = false;
}

function openQuizCreate() {
  resetQuizForm();
  quizDialogOpen.value = true;
}

function openQuizEdit(row: QuizRow["items"][number]) {
  quizEditingId.value = row.id;
  quizForm.type = row.type;
  quizForm.prompt = row.prompt;
  quizForm.options_text = (row.options ?? []).join("\n");
  quizForm.answer = row.answer;
  quizForm.explanation = row.explanation;
  quizForm.key_item = Boolean(row.key_item);
  quizDialogOpen.value = true;
}

async function saveQuizItem() {
  if (!props.kpId) return;
  const payload = {
    kp_id: props.kpId,
    type: quizForm.type,
    prompt: quizForm.prompt,
    options: quizForm.type === "mcq" ? parseOptions(quizForm.options_text) : [],
    answer: quizForm.answer,
    explanation: quizForm.explanation,
    key_item: quizForm.key_item,
  };
  try {
    if (quizEditingId.value) {
      await api.put(`/admin/quiz/item/${quizEditingId.value}`, payload);
      ElMessage.success("小测题已更新");
    } else {
      await api.post("/admin/quiz/item", payload);
      ElMessage.success("小测题已创建");
    }
    quizDialogOpen.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存小测题失败");
  }
}

async function removeQuizItem(id: number) {
  try {
    await api.delete(`/admin/quiz/item/${id}`);
    ElMessage.success("小测题已删除");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除小测题失败");
  }
}

async function savePassAccuracy() {
  if (!props.kpId) return;
  try {
    await api.put(`/admin/quiz/${props.kpId}/pass_accuracy`, { pass_accuracy: quiz.value.pass_accuracy });
    ElMessage.success("通过阈值已更新");
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存通过阈值失败");
  }
}

watch(
  () => props.kpId,
  () => {
    resourceDialogOpen.value = false;
    taskDialogOpen.value = false;
    questionDialogOpen.value = false;
    quizDialogOpen.value = false;
    load();
  },
  { immediate: true }
);
</script>

<template>
  <section class="binder-card" v-loading="loading">
    <div class="binder-header">
      <div>
        <div class="binder-title">节点内容绑定</div>
        <div class="binder-subtitle">把资源、任务、练习和小测都挂到当前知识点上。</div>
      </div>
      <div class="binder-metrics" v-if="kpId">
        <span>{{ resourceSummary.length }} 资源</span>
        <span>{{ taskSummary.length + examSummary.length }} 任务</span>
        <span>{{ questionCount }} 练习</span>
        <span>{{ quizCount }} 小测题</span>
      </div>
    </div>

    <el-empty v-if="!kpId" description="先在左侧或画布中选择一个知识点" />

    <template v-else>
      <div class="binder-node-tag">
        <span>{{ kpCode }}</span>
        <strong>{{ kpTitle }}</strong>
      </div>

      <section class="binder-section">
        <div class="section-head">
          <div class="section-title">学习资源</div>
          <el-button size="small" @click="openResourceCreate">新增资源</el-button>
        </div>
        <div v-if="resourceSummary.length === 0" class="empty-copy">暂无资源，可直接补充视频、文档或案例链接。</div>
        <div v-else class="item-stack">
          <div v-for="item in resourceSummary" :key="item.id" class="item-row">
            <div class="item-main">
              <div class="item-title">{{ item.title }}</div>
              <div class="item-meta">
                <span class="item-chip">{{ item.type }}</span>
                <a :href="item.url" target="_blank" rel="noreferrer">{{ item.url }}</a>
              </div>
            </div>
            <div class="item-actions">
              <el-button size="small" @click="openResourceEdit(item)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeResource(item.id)">删除</el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="binder-section">
        <div class="section-head">
          <div class="section-title">任务与试卷</div>
          <el-button size="small" @click="openTaskCreate">新增任务</el-button>
        </div>
        <div v-if="taskSummary.length === 0 && examSummary.length === 0" class="empty-copy">暂无任务或试卷。</div>
        <div v-else class="item-stack">
          <div v-for="item in [...taskSummary, ...examSummary]" :key="`${item.type || item.kind}-${item.id}`" class="item-row">
            <div class="item-main">
              <div class="item-title">{{ item.title }}</div>
              <div class="item-meta">
                <span class="item-chip">{{ item.type || item.kind }}</span>
                <span v-if="item.description">{{ item.description }}</span>
                <a v-if="item.link_url" :href="item.link_url" target="_blank" rel="noreferrer">{{ item.link_url }}</a>
              </div>
            </div>
            <div class="item-actions">
              <el-button v-if="'sort_order' in item" size="small" @click="openTaskEdit(item as any)">编辑</el-button>
              <el-button v-if="'sort_order' in item" size="small" type="danger" @click="removeTask(item.id)">删除</el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="binder-section">
        <div class="section-head">
          <div class="section-title">练习题</div>
          <el-button size="small" @click="openQuestionCreate">新增练习题</el-button>
        </div>
        <div v-if="practiceRows.length === 0" class="empty-copy">暂无练习题。</div>
        <div v-else class="item-stack">
          <div v-for="item in practiceRows.slice(0, 8)" :key="item.id" class="item-row">
            <div class="item-main">
              <div class="item-title">{{ item.prompt }}</div>
              <div class="item-meta">
                <span class="item-chip">{{ item.type }}</span>
                <span>难度 {{ Math.round((item.difficulty ?? 0) * 100) }}</span>
              </div>
            </div>
            <div class="item-actions">
              <el-button size="small" @click="openQuestionEdit(item)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeQuestion(item.id)">删除</el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="binder-section">
        <div class="section-head">
          <div class="section-title">小测</div>
          <div class="section-head__actions">
            <el-input-number v-model="quiz.pass_accuracy" :min="0" :max="1" :step="0.05" size="small" />
            <el-button size="small" @click="savePassAccuracy">保存阈值</el-button>
            <el-button size="small" type="primary" @click="openQuizCreate">新增小测题</el-button>
          </div>
        </div>
        <div v-if="quiz.items.length === 0" class="empty-copy">当前知识点还没有配置小测题。</div>
        <div v-else class="item-stack">
          <div v-for="item in quiz.items" :key="item.id" class="item-row">
            <div class="item-main">
              <div class="item-title">{{ item.prompt }}</div>
              <div class="item-meta">
                <span class="item-chip">{{ item.type }}</span>
                <span v-if="item.key_item">关键题</span>
                <span>答案 {{ item.answer }}</span>
              </div>
            </div>
            <div class="item-actions">
              <el-button size="small" @click="openQuizEdit(item)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeQuizItem(item.id)">删除</el-button>
            </div>
          </div>
        </div>
      </section>
    </template>

    <el-dialog v-model="resourceDialogOpen" :title="resourceEditingId ? '编辑资源' : '新增资源'" width="560px">
      <el-form label-position="top">
        <el-form-item label="资源类型">
          <el-select v-model="resourceForm.type">
            <el-option label="视频" value="video" />
            <el-option label="文档/笔记" value="note" />
            <el-option label="案例/示例" value="example" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="resourceForm.title" />
        </el-form-item>
        <el-form-item label="链接">
          <el-input v-model="resourceForm.url" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resourceDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveResource">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taskDialogOpen" :title="taskEditingId ? '编辑任务' : '新增任务'" width="580px">
      <el-form label-position="top">
        <el-form-item label="任务类型">
          <el-select v-model="taskForm.type">
            <el-option label="学习任务" value="task" />
            <el-option label="试卷/考试" value="exam" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="taskForm.title" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="taskForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="跳转链接">
          <el-input v-model="taskForm.link_url" placeholder="可选，外部任务/试卷链接" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="taskForm.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveTask">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="questionDialogOpen" :title="questionEditingId ? '编辑练习题' : '新增练习题'" width="680px">
      <el-form label-position="top">
        <el-form-item label="题型">
          <el-select v-model="questionForm.type">
            <el-option label="选择题" value="mcq" />
            <el-option label="填空题" value="blank" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干">
          <el-input v-model="questionForm.prompt" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item v-if="questionForm.type === 'mcq'" label="选项（每行一个）">
          <el-input v-model="questionForm.options_text" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="答案">
          <el-input v-model="questionForm.answer" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="questionForm.explanation" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="难度">
          <el-input-number v-model="questionForm.difficulty" :min="0" :max="1" :step="0.05" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="quizDialogOpen" :title="quizEditingId ? '编辑小测题' : '新增小测题'" width="680px">
      <el-form label-position="top">
        <el-form-item label="题型">
          <el-select v-model="quizForm.type">
            <el-option label="选择题" value="mcq" />
            <el-option label="填空题" value="blank" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干">
          <el-input v-model="quizForm.prompt" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item v-if="quizForm.type === 'mcq'" label="选项（每行一个）">
          <el-input v-model="quizForm.options_text" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="答案">
          <el-input v-model="quizForm.answer" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="quizForm.explanation" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="关键题">
          <el-switch v-model="quizForm.key_item" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quizDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveQuizItem">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.binder-card {
  border-radius: 24px;
  border: 1px solid #dbe7f2;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fc 100%);
  box-shadow: 0 18px 48px rgba(15, 40, 73, 0.08);
  padding: 16px;
  display: grid;
  gap: 14px;
}

.binder-header,
.section-head,
.item-row,
.item-meta,
.item-actions,
.section-head__actions,
.binder-metrics {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.binder-header,
.section-head,
.item-row {
  justify-content: space-between;
}

.binder-title,
.section-title {
  font-size: 13px;
  font-weight: 800;
  color: var(--app-ink);
  letter-spacing: 0.04em;
}

.binder-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #667f99;
}

.binder-metrics span,
.item-chip {
  padding: 4px 8px;
  border-radius: 999px;
  background: #edf4fb;
  color: #36587a;
  font-size: 11px;
  font-weight: 700;
}

.binder-node-tag {
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(19, 50, 82, 0.06);
  display: grid;
  gap: 4px;
}

.binder-node-tag span {
  font-size: 12px;
  color: #5d7fa1;
}

.binder-node-tag strong {
  font-size: 16px;
  color: var(--app-ink);
}

.binder-section {
  display: grid;
  gap: 10px;
  padding-top: 2px;
}

.item-stack {
  display: grid;
  gap: 10px;
}

.item-row {
  padding: 12px 14px;
  border-radius: 18px;
  border: 1px solid #dce7f0;
  background: #f8fbfe;
  align-items: flex-start;
}

.item-main {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.item-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-ink);
  line-height: 1.5;
}

.item-meta {
  align-items: flex-start;
}

.item-meta span,
.item-meta a {
  font-size: 12px;
  color: #5f7892;
  word-break: break-all;
}

.empty-copy {
  font-size: 12px;
  color: #7b90a5;
}

@media (max-width: 900px) {
  .section-head__actions {
    justify-content: flex-start;
  }
}
</style>
