<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type KP = { id: number; code: string; title: string; practice_total?: number | null };
type QuestionRow = {
  id: number;
  kp_id: number;
  type: string;
  prompt: string;
  options: string[];
  answer: string;
  explanation: string;
  difficulty: number;
  source?: string | null;
  tags?: string | null;
  version?: string | null;
  attempts?: number | null;
  correct_rate?: number | null;
};
type AssignRow = { id: number; kp_id: number; question_id: number; order: number; type: string; prompt: string };

const props = defineProps<{ subject: string; grade: string }>();

const kps = ref<KP[]>([]);
const kpId = ref<number | null>(null);
const practiceTotal = ref<number | null>(null);
const practiceTotalSaving = ref(false);

const bankLoading = ref(false);
const bank = ref<QuestionRow[]>([]);
const bankTotal = ref(0);
const bankPage = ref(1);
const bankPageSize = 15;
const bankSelection = ref<number[]>([]);
const bankKeyword = ref("");
const bankType = ref("");
const bankMinDiff = ref<number | null>(null);
const bankMaxDiff = ref<number | null>(null);

function searchBank() {
  bankPage.value = 1;
  loadBank();
}

const importFile = ref<File | null>(null);
const importLoading = ref(false);
const importResult = ref<{ created: number; skipped: number; errors: string[] } | null>(null);
const editDialogOpen = ref(false);
const editingQuestion = ref<QuestionRow | null>(null);
const editForm = reactive({
  id: 0,
  type: "mcq",
  prompt: "",
  optionsText: "",
  answer: "",
  explanation: "",
  difficulty: 0.4,
  source: "",
  tags: "",
  version: "v1",
});

const quizLoading = ref(false);
const quizItems = ref<any[]>([]);
const quizPassAccuracy = ref(0.8);
const quizForm = reactive({
  type: "mcq",
  prompt: "",
  optionsText: "A选项,B选项,C选项,D选项",
  answer: "A",
  explanation: "",
  key_item: false,
});
const quizEditOpen = ref(false);
const quizEditForm = reactive({
  id: 0,
  type: "mcq",
  prompt: "",
  optionsText: "",
  answer: "",
  explanation: "",
  key_item: false,
});

const recalibrating = ref(false);
const recalib = reactive({
  min_attempts: 5,
  blend: 0.7,
  step: 0.1,
});

const assignedLoading = ref(false);
const assigned = ref<AssignRow[]>([]);
const assignedPage = ref(1);
const assignedPageSize = 15;
const assignedTotal = computed(() => assigned.value.length);
const assignedPaged = computed(() => {
  const start = (assignedPage.value - 1) * assignedPageSize;
  return assigned.value.slice(start, start + assignedPageSize);
});
const exportUrl = computed(() => {
  if (!kpId.value) return "#";
  const query = new URLSearchParams({
    kp_id: String(kpId.value),
    keyword: bankKeyword.value || "",
  });
  if (bankType.value) query.set("q_type", bankType.value);
  if (bankMinDiff.value !== null) query.set("min_difficulty", String(bankMinDiff.value));
  if (bankMaxDiff.value !== null) query.set("max_difficulty", String(bankMaxDiff.value));
  return `/admin/questions/export?${query.toString()}`;
});

const form = reactive({
  type: "mcq",
  prompt: "",
  optionsText: "A选项,B选项,C选项,D选项",
  answer: "A",
  explanation: "",
  difficulty: 0.4,
  source: "",
  tags: "",
  version: "v1",
});

const options = computed(() => {
  return form.optionsText
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
});

const editOptions = computed(() => {
  return editForm.optionsText
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
});

const quizOptions = computed(() => {
  return quizForm.optionsText
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
});

const quizEditOptions = computed(() => {
  return quizEditForm.optionsText
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
});

async function loadKps() {
  const res = await api.get(
    `/admin/kps?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}&page=1&page_size=100`
  );
  kps.value = res.data.items ?? [];
  if (!kpId.value && kps.value.length) kpId.value = kps.value[0].id;
}

function syncPracticeTotal() {
  const kp = kps.value.find((k) => k.id === kpId.value);
  practiceTotal.value = kp?.practice_total ?? null;
}

async function savePracticeTotal() {
  if (!kpId.value) return;
  practiceTotalSaving.value = true;
  try {
    const res = await api.put(`/admin/kps/${kpId.value}/practice_total`, {
      practice_total: practiceTotal.value,
    });
    const kp = kps.value.find((k) => k.id === kpId.value);
    if (kp) kp.practice_total = res.data.practice_total ?? null;
    ElMessage.success("已保存");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
  } finally {
    practiceTotalSaving.value = false;
  }
}

async function loadBank() {
  if (!kpId.value) return;
  bankLoading.value = true;
  try {
    const query = new URLSearchParams({
      kp_id: String(kpId.value),
      page: String(bankPage.value),
      page_size: String(bankPageSize),
    });
    if (bankKeyword.value.trim()) query.set("keyword", bankKeyword.value.trim());
    if (bankType.value) query.set("q_type", bankType.value);
    if (bankMinDiff.value !== null) query.set("min_difficulty", String(bankMinDiff.value));
    if (bankMaxDiff.value !== null) query.set("max_difficulty", String(bankMaxDiff.value));
    const res = await api.get(`/admin/questions?${query.toString()}`);
    bank.value = res.data.items ?? [];
    bankTotal.value = Number(res.data.total ?? 0);
    bankSelection.value = [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载题库失败");
  } finally {
    bankLoading.value = false;
  }
}

async function recalibrateDifficulty() {
  if (!kpId.value) return;
  recalibrating.value = true;
  try {
    const res = await api.post("/admin/questions/recalibrate-difficulty", {
      kp_id: kpId.value,
      min_attempts: recalib.min_attempts,
      blend: recalib.blend,
      step: recalib.step,
    });
    ElMessage.success(`已标定：更新 ${res.data.updated ?? 0} 道题`);
    await loadBank();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "标定失败");
  } finally {
    recalibrating.value = false;
  }
}

async function loadAssigned() {
  if (!kpId.value) return;
  assignedLoading.value = true;
  try {
    const res = await api.get(`/admin/kp-questions?kp_id=${kpId.value}`);
    assigned.value = (res.data ?? []).sort((a: any, b: any) => Number(a.order) - Number(b.order));
    assignedPage.value = 1;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载已布置题目失败");
  } finally {
    assignedLoading.value = false;
  }
}

async function loadQuiz() {
  if (!kpId.value) return;
  quizLoading.value = true;
  try {
    const res = await api.get(`/admin/quiz?kp_id=${kpId.value}`);
    quizItems.value = res.data.items ?? [];
    quizPassAccuracy.value = Number(res.data.pass_accuracy ?? 0.8);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载小测失败");
  } finally {
    quizLoading.value = false;
  }
}

async function saveQuizPassAccuracy() {
  if (!kpId.value) return;
  try {
    const res = await api.put(`/admin/quiz/${kpId.value}/pass_accuracy`, { pass_accuracy: quizPassAccuracy.value });
    quizPassAccuracy.value = Number(res.data.pass_accuracy ?? quizPassAccuracy.value);
    ElMessage.success("已保存");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败");
  }
}

async function addQuizItem() {
  if (!kpId.value) return;
  if (!quizForm.prompt.trim()) {
    ElMessage.warning("请输入题干");
    return;
  }
  if (quizForm.type === "mcq" && quizOptions.value.length < 2) {
    ElMessage.warning("选择题至少需要2个选项（用逗号分隔）");
    return;
  }
  try {
    await api.post("/admin/quiz/item", {
      kp_id: kpId.value,
      type: quizForm.type,
      prompt: quizForm.prompt,
      options: quizForm.type === "mcq" ? quizOptions.value : [],
      answer: quizForm.answer,
      explanation: quizForm.explanation,
      key_item: quizForm.key_item,
    });
    ElMessage.success("已添加小测题");
    quizForm.prompt = "";
    quizForm.explanation = "";
    await loadQuiz();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "添加失败");
  }
}

async function addBankToQuiz(row: QuestionRow) {
  if (!kpId.value) return;
  try {
    await api.post("/admin/quiz/item/from-question", {
      kp_id: kpId.value,
      question_id: row.id,
    });
    ElMessage.success("已加入小测");
    await loadQuiz();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加入失败");
  }
}

function openQuizEdit(row: any) {
  quizEditForm.id = row.id;
  quizEditForm.type = row.type;
  quizEditForm.prompt = row.prompt;
  quizEditForm.optionsText = (row.options ?? []).join(",");
  quizEditForm.answer = row.answer;
  quizEditForm.explanation = row.explanation;
  quizEditForm.key_item = Boolean(row.key_item);
  quizEditOpen.value = true;
}

async function saveQuizEdit() {
  if (!quizEditForm.prompt.trim()) {
    ElMessage.warning("请输入题干");
    return;
  }
  if (quizEditForm.type === "mcq" && quizEditOptions.value.length < 2) {
    ElMessage.warning("选择题至少需要2个选项（用逗号分隔）");
    return;
  }
  try {
    await api.put(`/admin/quiz/item/${quizEditForm.id}`, {
      type: quizEditForm.type,
      prompt: quizEditForm.prompt,
      options: quizEditForm.type === "mcq" ? quizEditOptions.value : [],
      answer: quizEditForm.answer,
      explanation: quizEditForm.explanation,
      key_item: quizEditForm.key_item,
    });
    ElMessage.success("已更新");
    quizEditOpen.value = false;
    await loadQuiz();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "更新失败");
  }
}

async function removeQuizItem(row: any) {
  try {
    await api.delete(`/admin/quiz/item/${row.id}`);
    ElMessage.success("已删除");
    await loadQuiz();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除失败");
  }
}

function onImportChange(file: any) {
  importFile.value = file?.raw ?? null;
  importResult.value = null;
}

async function importDocx() {
  if (!importFile.value) {
    ElMessage.warning("请选择 .docx 文件");
    return;
  }
  importLoading.value = true;
  try {
    const formData = new FormData();
    formData.append("file", importFile.value);
    const res = await api.post("/admin/questions/import-docx", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    importResult.value = res.data;
    ElMessage.success("导入完成");
    await loadBank();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "导入失败");
  } finally {
    importLoading.value = false;
  }
}

async function addToBank() {
  if (!kpId.value) return;
  if (!form.prompt.trim()) {
    ElMessage.warning("请输入题干");
    return;
  }
  if (form.type === "mcq" && options.value.length < 2) {
    ElMessage.warning("选择题至少需要2个选项（用逗号分隔）");
    return;
  }
  try {
    await api.post("/admin/questions", {
      kp_id: kpId.value,
      type: form.type,
      prompt: form.prompt,
      options: form.type === "mcq" ? options.value : [],
      answer: form.answer,
      explanation: form.explanation,
      difficulty: form.difficulty,
      source: form.source,
      tags: form.tags,
      version: form.version,
    });
    ElMessage.success("已加入题库");
    form.prompt = "";
    form.explanation = "";
    await loadBank();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "添加失败");
  }
}

function openEdit(row: QuestionRow) {
  editingQuestion.value = row;
  editForm.id = row.id;
  editForm.type = row.type;
  editForm.prompt = row.prompt;
  editForm.optionsText = (row.options ?? []).join(",");
  editForm.answer = row.answer;
  editForm.explanation = row.explanation;
  editForm.difficulty = row.difficulty;
  editForm.source = row.source ?? "";
  editForm.tags = row.tags ?? "";
  editForm.version = row.version ?? "v1";
  editDialogOpen.value = true;
}

async function saveEdit() {
  if (!editingQuestion.value) return;
  if (!editForm.prompt.trim()) {
    ElMessage.warning("请输入题干");
    return;
  }
  if (editForm.type === "mcq" && editOptions.value.length < 2) {
    ElMessage.warning("选择题至少需要2个选项（用逗号分隔）");
    return;
  }
  try {
    await api.put(`/admin/questions/${editForm.id}`, {
      kp_id: editingQuestion.value.kp_id,
      type: editForm.type,
      prompt: editForm.prompt,
      options: editForm.type === "mcq" ? editOptions.value : [],
      answer: editForm.answer,
      explanation: editForm.explanation,
      difficulty: editForm.difficulty,
      source: editForm.source,
      tags: editForm.tags,
      version: editForm.version,
    });
    ElMessage.success("已更新");
    editDialogOpen.value = false;
    await loadBank();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "更新失败");
  }
}

async function removeQuestion(row: QuestionRow) {
  try {
    await api.delete(`/admin/questions/${row.id}`);
    ElMessage.success("已删除");
    await loadBank();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "删除失败");
  }
}

async function assignSelected() {
  if (!kpId.value) return;
  if (bankSelection.value.length === 0) {
    ElMessage.warning("请先勾选题目");
    return;
  }
  try {
    await api.post("/admin/kp-questions", { kp_id: kpId.value, question_ids: bankSelection.value });
    ElMessage.success("已布置");
    await loadAssigned();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "布置失败");
  }
}

function onBankSelectionChange(rows: any[]) {
  bankSelection.value = (rows ?? []).map((r: any) => Number(r.id));
}

async function removeAssignment(row: AssignRow) {
  try {
    await api.delete(`/admin/kp-questions/${row.id}`);
    ElMessage.success("已移除");
    await loadAssigned();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "移除失败");
  }
}

async function saveOrder(next: AssignRow[]) {
  if (!kpId.value) return;
  assigned.value = next;
  const ids = next.map((r) => r.question_id);
  try {
    await api.put("/admin/kp-questions/reorder", { kp_id: kpId.value, ordered_question_ids: ids });
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存排序失败");
  }
}

async function moveUp(row: AssignRow) {
  const idx = assigned.value.findIndex((r) => r.id === row.id);
  if (idx <= 0) return;
  const next = assigned.value.slice();
  const tmp = next[idx - 1];
  next[idx - 1] = next[idx];
  next[idx] = tmp;
  await saveOrder(next);
}

async function moveDown(row: AssignRow) {
  const idx = assigned.value.findIndex((r) => r.id === row.id);
  if (idx < 0 || idx >= assigned.value.length - 1) return;
  const next = assigned.value.slice();
  const tmp = next[idx + 1];
  next[idx + 1] = next[idx];
  next[idx] = tmp;
  await saveOrder(next);
}

watch(
  () => [props.subject, props.grade],
  async () => {
    bankPage.value = 1;
    await loadKps();
    await loadBank();
    await loadAssigned();
    await loadQuiz();
    syncPracticeTotal();
  },
  { immediate: true }
);

watch(
  () => kpId.value,
  async () => {
    bankPage.value = 1;
    await loadBank();
    await loadAssigned();
    await loadQuiz();
    syncPracticeTotal();
  }
);

watch(
  () => bankPage.value,
  () => loadBank()
);

watch(
  () => [bankKeyword.value, bankType.value, bankMinDiff.value, bankMaxDiff.value],
  () => {
    bankPage.value = 1;
    loadBank();
  }
);

onMounted(() => loadKps());
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between">
        <div>题库（本知识点）→ 布置给学生</div>
        <el-button size="small" @click="() => { loadBank(); loadAssigned(); }" :loading="bankLoading || assignedLoading">
          刷新
        </el-button>
      </div>
    </template>

    <el-form label-width="90px" size="small" style="margin-bottom: 10px">
      <el-form-item label="知识点">
        <el-select v-model="kpId" filterable style="width: 100%">
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="练习题数">
        <div style="display: flex; gap: 8px; align-items: center; width: 100%">
          <el-input-number v-model="practiceTotal" :min="0" :max="200" :step="1" style="width: 160px" />
          <el-text type="info" style="font-size: 12px">留空则使用全局配置</el-text>
          <el-button size="small" type="primary" :loading="practiceTotalSaving" @click="savePracticeTotal">
            保存
          </el-button>
        </div>
      </el-form-item>
    </el-form>

    <el-tabs type="border-card">
      <el-tab-pane label="题库列表">
        <el-card shadow="never">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between">
              <div>题库（选择/填空）</div>
              <el-text type="info" style="font-size: 12px">题目由系统自动推荐，无需手动布置</el-text>
            </div>
          </template>

          <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 8px">
            <el-button size="small" type="primary" :loading="recalibrating" @click="recalibrateDifficulty">
              自动标定难度
            </el-button>
            <el-text type="info" style="font-size: 12px">基于历史正确率：difficulty≈1-正确率（按步长量化）</el-text>
          </div>

          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 8px">
            <el-input
              v-model="bankKeyword"
              size="small"
              placeholder="搜索题干关键词"
              style="width: 220px"
              @keyup.enter="searchBank"
            />
            <el-select v-model="bankType" size="small" style="width: 120px">
              <el-option label="全部题型" value="" />
              <el-option label="选择题" value="mcq" />
              <el-option label="填空题" value="blank" />
            </el-select>
            <el-input-number v-model="bankMinDiff" :min="0" :max="1" :step="0.1" size="small" style="width: 120px" />
            <el-input-number v-model="bankMaxDiff" :min="0" :max="1" :step="0.1" size="small" style="width: 120px" />
            <el-button size="small" type="primary" @click="searchBank" :disabled="!kpId">搜索</el-button>
            <el-button size="small" type="success" :href="exportUrl" target="_blank">导出 CSV</el-button>
          </div>

          <el-table :data="bank" size="small" v-loading="bankLoading" style="width: 100%">
            <el-table-column prop="type" label="题型" width="70" />
            <el-table-column prop="prompt" label="题干" />
            <el-table-column prop="answer" label="答案" width="80" />
            <el-table-column prop="difficulty" label="难度" width="80" />
            <el-table-column prop="source" label="来源" width="120" />
            <el-table-column prop="tags" label="标签" width="140" />
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="attempts" label="次数" width="80" />
            <el-table-column label="正确率" width="90">
              <template #default="{ row }">
                <span v-if="row.correct_rate !== null && row.correct_rate !== undefined">
                  {{ Math.round(Number(row.correct_rate) * 100) }}%
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300" align="center" header-align="center">
              <template #default="{ row }">
                <div class="op-actions-inline">
                  <el-button size="small" @click="openEdit(row)">&#20462;&#25913;</el-button>
                  <el-button size="small" type="danger" @click="removeQuestion(row)">&#21024;&#38500;</el-button>
                  <el-button size="small" type="primary" @click="addBankToQuiz(row)">&#21152;&#20837;&#23567;&#27979;</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div style="display: flex; justify-content: flex-end; margin-top: 8px">
            <el-pagination
              background
              layout="prev, pager, next"
              :page-size="bankPageSize"
              :total="bankTotal"
              v-model:current-page="bankPage"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="题库导入">
        <el-card shadow="never">
          <template #header>Word 导入题库</template>
          <el-alert type="info" :closable="false" show-icon>
            <template #default>
              <div style="white-space: pre-line; font-size: 12px; line-height: 1.5">
每题一个块，示例如下：
【题目】
知识点编码: MATH-G2-DER-001
题型: 选择
题干: 导数的几何意义是？
选项:
A. 斜率
B. 面积
C. 体积
D. 平均值
答案: A
解析: 切线斜率
难度: 0.3
（填空题省略“选项”，题型写“填空”）
              </div>
            </template>
          </el-alert>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px">
            <el-upload :auto-upload="false" :show-file-list="false" accept=".docx" :limit="1" @change="onImportChange">
              <el-button size="small">选择 .docx 文件</el-button>
            </el-upload>
            <el-button size="small" type="primary" :loading="importLoading" @click="importDocx">导入</el-button>
            <span v-if="importResult" style="font-size: 12px">
              已导入 {{ importResult.created }}，跳过 {{ importResult.skipped }}，错误 {{ importResult.errors?.length || 0 }}
            </span>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="新增题目">
        <el-card shadow="never">
          <template #header>新增题目到题库</template>
          <el-form label-width="80px" size="small">
            <el-form-item label="题型">
              <el-radio-group v-model="form.type">
                <el-radio label="mcq">选择</el-radio>
                <el-radio label="blank">填空</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="题干">
              <el-input v-model="form.prompt" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="来源">
              <el-input v-model="form.source" placeholder="例如：教材/真题/课堂例题" />
            </el-form-item>
            <el-form-item label="标签">
              <el-input v-model="form.tags" placeholder="用逗号分隔，如：哈希表,冲突,负载因子" />
            </el-form-item>
            <el-form-item label="版本">
              <el-input v-model="form.version" placeholder="如 v1/v2" />
            </el-form-item>
            <el-form-item v-if="form.type === 'mcq'" label="选项">
              <el-input v-model="form.optionsText" placeholder="用逗号分隔，例如 A,B,C,D" />
            </el-form-item>
            <el-form-item label="答案">
              <el-input v-model="form.answer" placeholder="选择题填 A/B/C/D；填空题填具体答案" />
            </el-form-item>
            <el-form-item label="解析">
              <el-input v-model="form.explanation" />
            </el-form-item>
            <el-form-item label="难度">
              <el-input-number v-model="form.difficulty" :min="0" :max="1" :step="0.1" />
            </el-form-item>
            <el-form-item>
              <el-button size="small" type="success" @click="addToBank">添加</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="小测管理">
        <el-card shadow="never">
          <template #header>小测管理</template>
          <el-form label-width="100px" size="small">
            <el-form-item label="小测通过阈值">
              <el-input-number v-model="quizPassAccuracy" :min="0" :max="1" :step="0.05" />
              <el-button size="small" style="margin-left: 8px" @click="saveQuizPassAccuracy">保存</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="quizItems" size="small" v-loading="quizLoading" style="width: 100%" height="360">
            <el-table-column prop="type" label="题型" width="70" />
            <el-table-column prop="prompt" label="题干" />
            <el-table-column prop="answer" label="答案" width="80" />
            <el-table-column label="操作" width="140" align="center" header-align="center">
              <template #default="{ row }">
                <div class="op-btn-wrap">
                  <el-button size="small" class="op-btn" @click="openQuizEdit(row)">修改</el-button>
                  <el-button size="small" type="danger" class="op-btn" @click="removeQuizItem(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div style="height: 8px" />

          <el-form label-width="80px" size="small">
            <el-form-item label="题型">
              <el-radio-group v-model="quizForm.type">
                <el-radio label="mcq">选择</el-radio>
                <el-radio label="blank">填空</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="题干">
              <el-input v-model="quizForm.prompt" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item v-if="quizForm.type === 'mcq'" label="选项">
              <el-input v-model="quizForm.optionsText" placeholder="用逗号分隔，例如 A,B,C,D" />
            </el-form-item>
            <el-form-item label="答案">
              <el-input v-model="quizForm.answer" placeholder="选择题填 A/B/C/D；填空题填具体答案" />
            </el-form-item>
            <el-form-item label="解析">
              <el-input v-model="quizForm.explanation" />
            </el-form-item>
            <el-form-item label="关键题">
              <el-switch v-model="quizForm.key_item" />
            </el-form-item>
            <el-form-item>
              <el-button size="small" type="success" @click="addQuizItem">添加小测题</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </el-card>

  <el-dialog v-model="quizEditOpen" title="修改小测题" width="560px">
    <el-form label-width="80px" size="small">
      <el-form-item label="题型">
        <el-radio-group v-model="quizEditForm.type">
          <el-radio label="mcq">选择</el-radio>
          <el-radio label="blank">填空</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="题干">
        <el-input v-model="quizEditForm.prompt" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item v-if="quizEditForm.type === 'mcq'" label="选项">
        <el-input v-model="quizEditForm.optionsText" placeholder="用逗号分隔，例如 A,B,C,D" />
      </el-form-item>
      <el-form-item label="答案">
        <el-input v-model="quizEditForm.answer" placeholder="选择题填 A/B/C/D；填空题填具体答案" />
      </el-form-item>
      <el-form-item label="解析">
        <el-input v-model="quizEditForm.explanation" />
      </el-form-item>
      <el-form-item label="关键题">
        <el-switch v-model="quizEditForm.key_item" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="quizEditOpen = false">取消</el-button>
      <el-button type="primary" @click="saveQuizEdit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editDialogOpen" title="修改题目" width="560px">
    <el-form label-width="80px" size="small">
      <el-form-item label="题型">
        <el-radio-group v-model="editForm.type">
          <el-radio label="mcq">选择</el-radio>
          <el-radio label="blank">填空</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="题干">
        <el-input v-model="editForm.prompt" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="来源">
        <el-input v-model="editForm.source" placeholder="例如：教材/真题/课堂例题" />
      </el-form-item>
      <el-form-item label="标签">
        <el-input v-model="editForm.tags" placeholder="用逗号分隔，如：哈希表,冲突,负载因子" />
      </el-form-item>
      <el-form-item label="版本">
        <el-input v-model="editForm.version" placeholder="如 v1/v2" />
      </el-form-item>
      <el-form-item v-if="editForm.type === 'mcq'" label="选项">
        <el-input v-model="editForm.optionsText" placeholder="用逗号分隔，例如 A,B,C,D" />
      </el-form-item>
      <el-form-item label="答案">
        <el-input v-model="editForm.answer" placeholder="选择题填 A/B/C/D；填空题填具体答案" />
      </el-form-item>
      <el-form-item label="解析">
        <el-input v-model="editForm.explanation" />
      </el-form-item>
      <el-form-item label="难度">
        <el-input-number v-model="editForm.difficulty" :min="0" :max="1" :step="0.1" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogOpen = false">取消</el-button>
      <el-button type="primary" @click="saveEdit">保存</el-button>
    </template>
  </el-dialog>
</template>
