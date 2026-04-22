<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type Indicator = {
  id: number;
  dimension_id: number;
  code: string;
  title: string;
  description: string;
  source_type: string;
  default_weight: number;
  sort_order: number;
  active: boolean;
};

type Dimension = {
  id: number;
  code: string;
  title: string;
  description: string;
  sort_order: number;
  active: boolean;
  indicators: Indicator[];
};

const loading = ref(false);
const saving = ref(false);
const dimensions = ref<Dimension[]>([]);
const selectedDimensionId = ref<number | null>(null);
const editorDialogVisible = ref(false);
const editorDialogMode = ref<"current" | "create-dimension" | "create-indicator">("current");

const dimensionForm = reactive({
  code: "",
  title: "",
  description: "",
  sort_order: 10,
  active: true,
});

const newDimensionForm = reactive({
  code: "",
  title: "",
  description: "",
  sort_order: 10,
  active: true,
});

const indicatorForm = reactive({
  dimension_id: 0,
  code: "",
  title: "",
  description: "",
  source_type: "auto",
  default_weight: 1,
  sort_order: 10,
  active: true,
});

const selectedDimension = computed(
  () => dimensions.value.find((item) => item.id === selectedDimensionId.value) ?? null
);
const useIndicatorRail = computed(() => (selectedDimension.value?.indicators.length ?? 0) > 3);

const sourceTypeOptions = [
  { value: "auto", label: "系统自动", description: "来自系统自动采集的学习行为、图谱掌握度和过程数据。" },
  { value: "imported", label: "阶段导入", description: "来自老师每个阶段导入的成绩、考勤、任务和课堂记录。" },
  { value: "teacher", label: "教师补充", description: "来自老师对学生高阶表现和课堂观察的补充评分。" },
  { value: "questionnaire", label: "问卷自评", description: "来自学生基础信息、兴趣问卷和自评内容。" },
];

const editorDialogTitle = computed(() => {
  if (editorDialogMode.value === "current") return "修改大类";
  if (editorDialogMode.value === "create-dimension") return "新增大类";
  return "新增细项";
});

function sourceTypeLabel(sourceType: string) {
  return sourceTypeOptions.find((item) => item.value === sourceType)?.label ?? sourceType;
}

async function loadTree() {
  loading.value = true;
  try {
    const res = await api.get("/portrait/dimensions/tree");
    dimensions.value = res.data?.items ?? [];
    if (!selectedDimensionId.value && dimensions.value.length) {
      selectedDimensionId.value = dimensions.value[0].id;
    }
    if (selectedDimensionId.value && !dimensions.value.find((item) => item.id === selectedDimensionId.value)) {
      selectedDimensionId.value = dimensions.value[0]?.id ?? null;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载维度树失败");
  } finally {
    loading.value = false;
  }
}

function fillDimensionForm() {
  const current = selectedDimension.value;
  if (!current) {
    dimensionForm.code = "";
    dimensionForm.title = "";
    dimensionForm.description = "";
    dimensionForm.sort_order = 10;
    dimensionForm.active = true;
    return;
  }
  dimensionForm.code = current.code;
  dimensionForm.title = current.title;
  dimensionForm.description = current.description ?? "";
  dimensionForm.sort_order = current.sort_order ?? 10;
  dimensionForm.active = current.active;
  indicatorForm.dimension_id = current.id;
}

async function saveDimension() {
  if (!selectedDimension.value) return;
  saving.value = true;
  try {
    await api.put(`/portrait/dimensions/${selectedDimension.value.id}`, { ...dimensionForm });
    ElMessage.success("维度已保存");
    await loadTree();
    editorDialogVisible.value = false;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存维度失败");
  } finally {
    saving.value = false;
  }
}

async function createDimension() {
  if (!newDimensionForm.code.trim() || !newDimensionForm.title.trim()) {
    ElMessage.warning("请填写维度编码和标题");
    return;
  }
  saving.value = true;
  try {
    await api.post("/portrait/dimensions", { ...newDimensionForm });
    ElMessage.success("维度已创建");
    newDimensionForm.code = "";
    newDimensionForm.title = "";
    newDimensionForm.description = "";
    newDimensionForm.sort_order = 10;
    newDimensionForm.active = true;
    await loadTree();
    editorDialogVisible.value = false;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "创建维度失败");
  } finally {
    saving.value = false;
  }
}

async function createIndicator() {
  if (!indicatorForm.dimension_id) {
    ElMessage.warning("请先选择对应的大类");
    return;
  }
  if (!indicatorForm.code.trim() || !indicatorForm.title.trim()) {
    ElMessage.warning("请填写指标编码和标题");
    return;
  }
  saving.value = true;
  try {
    await api.post("/portrait/indicators", {
      ...indicatorForm,
    });
    ElMessage.success("二级指标已创建");
    indicatorForm.code = "";
    indicatorForm.title = "";
    indicatorForm.description = "";
    indicatorForm.source_type = "auto";
    indicatorForm.default_weight = 1;
    indicatorForm.sort_order = 10;
    indicatorForm.active = true;
    await loadTree();
    editorDialogVisible.value = false;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "创建二级指标失败");
  } finally {
    saving.value = false;
  }
}

function resetNewDimensionForm() {
  newDimensionForm.code = "";
  newDimensionForm.title = "";
  newDimensionForm.description = "";
  newDimensionForm.sort_order = 10;
  newDimensionForm.active = true;
}

function resetIndicatorForm() {
  indicatorForm.dimension_id = selectedDimensionId.value ?? dimensions.value[0]?.id ?? 0;
  indicatorForm.code = "";
  indicatorForm.title = "";
  indicatorForm.description = "";
  indicatorForm.source_type = "auto";
  indicatorForm.default_weight = 1;
  indicatorForm.sort_order = 10;
  indicatorForm.active = true;
}

function openEditorDialog(mode: "current" | "create-dimension" | "create-indicator") {
  if (mode === "current") {
    if (!selectedDimension.value) {
      ElMessage.warning("请先从左侧选择一个大类");
      return;
    }
    fillDimensionForm();
  } else if (mode === "create-dimension") {
    resetNewDimensionForm();
  } else {
    resetIndicatorForm();
  }
  editorDialogMode.value = mode;
  editorDialogVisible.value = true;
}

onMounted(async () => {
  await loadTree();
  fillDimensionForm();
});

watch(
  () => selectedDimensionId.value,
  () => {
    fillDimensionForm();
  }
);
</script>

<template>
  <div class="dimension-manager">
    <el-card class="panel-card dimension-manager__panel" shadow="never">
      <template #header>
        <div class="panel-header-row panel-header-row--toolbar">
          <div class="dimension-action-nav dimension-action-nav--toolbar">
            <button type="button" class="dimension-action-nav__item" @click="openEditorDialog('current')">修改大类</button>
            <button type="button" class="dimension-action-nav__item" @click="openEditorDialog('create-dimension')">新增大类</button>
            <button type="button" class="dimension-action-nav__item" @click="openEditorDialog('create-indicator')">新增细项</button>
          </div>
          <el-button size="small" :loading="loading" @click="loadTree">刷新</el-button>
        </div>
      </template>

      <div class="dimension-master" v-loading="loading">
        <div class="dimension-master__sidebar">
          <div
            v-for="item in dimensions"
            :key="item.id"
            class="dimension-card"
            :class="{ 'is-active': item.id === selectedDimensionId }"
            @click="selectedDimensionId = item.id; fillDimensionForm()"
          >
            <div class="dimension-card__title">{{ item.title }}</div>
          </div>
        </div>

        <div class="dimension-master__detail">
          <div class="indicator-table-header">
            <div>
              <div class="content-title">评价维度大类与细类</div>
              <div class="indicator-table-header__meta">
                {{ selectedDimension ? `${selectedDimension.title} · 默认展示该大类下的细项` : "先从左侧选择一个大类" }}
              </div>
            </div>
          </div>

          <el-empty v-if="!selectedDimension" description="先选择左侧大类" :image-size="72" />
          <div
            v-else
            class="indicator-list"
            :class="{ 'indicator-list--scroll': useIndicatorRail }"
          >
            <article
              v-for="item in selectedDimension.indicators"
              :key="item.id"
              class="indicator-list__item"
            >
              <div class="indicator-list__main">
                <div class="indicator-list__title-row">
                  <h4 class="indicator-list__title">{{ item.title }}</h4>
                  <span class="indicator-list__code">{{ item.code }}</span>
                </div>
                <p class="indicator-list__desc">{{ item.description || "暂未填写用途说明" }}</p>
              </div>

              <div class="indicator-list__meta">
                <span class="indicator-list__pill indicator-list__pill--source">
                  {{ sourceTypeLabel(item.source_type) }}
                </span>
                <span class="indicator-list__pill indicator-list__pill--weight">
                  权重 {{ item.default_weight }}
                </span>
                <span
                  class="indicator-list__pill"
                  :class="item.active ? 'indicator-list__pill--active' : 'indicator-list__pill--inactive'"
                >
                  {{ item.active ? "使用中" : "未使用" }}
                </span>
              </div>
            </article>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="editorDialogVisible" :title="editorDialogTitle" width="760px">
      <el-empty v-if="editorDialogMode === 'current' && !selectedDimension" description="还没有大类" :image-size="72" />

      <el-form v-else-if="editorDialogMode === 'current'" label-width="88px" size="small">
        <el-form-item label="大类">
          <el-select v-model="selectedDimensionId" style="width: 100%">
            <el-option
              v-for="item in dimensions"
              :key="item.id"
              :label="item.title"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip content="给一级维度一个唯一编码，建议用英文下划线写法。" :show-after="700">
              <span>代号</span>
            </el-tooltip>
          </template>
          <el-input v-model="dimensionForm.code" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip content="这里写老师和学生都能看懂的中文标题。" :show-after="700">
              <span>名称</span>
            </el-tooltip>
          </template>
          <el-input v-model="dimensionForm.title" />
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="dimensionForm.description" type="textarea" :rows="3" placeholder="简单写清这个大类是看什么的" /></el-form-item>
        <el-form-item label="顺序">
          <el-input-number v-model="dimensionForm.sort_order" :min="1" :max="999" />
        </el-form-item>
        <el-form-item label="使用"><el-switch v-model="dimensionForm.active" /></el-form-item>
      </el-form>

      <el-form v-else-if="editorDialogMode === 'create-dimension'" label-width="88px" size="small">
        <el-form-item>
          <template #label>
            <el-tooltip content="例如 learning_behavior，主要给系统识别用。" :show-after="700">
              <span>代号</span>
            </el-tooltip>
          </template>
          <el-input v-model="newDimensionForm.code" placeholder="例如 learning_behavior" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip content="例如 学习行为与过程，这是页面上主要展示的名字。" :show-after="700">
              <span>名称</span>
            </el-tooltip>
          </template>
          <el-input v-model="newDimensionForm.title" placeholder="例如 学习行为与过程" />
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="newDimensionForm.description" type="textarea" :rows="2" placeholder="简单写清这个大类是做什么的" /></el-form-item>
        <el-form-item label="顺序"><el-input-number v-model="newDimensionForm.sort_order" :min="1" :max="999" /></el-form-item>
        <el-form-item label="使用"><el-switch v-model="newDimensionForm.active" /></el-form-item>
      </el-form>

      <el-form v-else label-width="88px" size="small">
        <el-form-item label="大类">
          <el-select v-model="indicatorForm.dimension_id" style="width: 100%">
            <el-option
              v-for="item in dimensions"
              :key="item.id"
              :label="item.title"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip content="例如 resource_preference，建议保持简短且唯一。" :show-after="700">
              <span>代号</span>
            </el-tooltip>
          </template>
          <el-input v-model="indicatorForm.code" placeholder="例如 resource_preference" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <el-tooltip content="例如 资源偏好。老师后面选指标时主要看这个名字。" :show-after="700">
              <span>名称</span>
            </el-tooltip>
          </template>
          <el-input v-model="indicatorForm.title" placeholder="例如 资源偏好" />
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="indicatorForm.description" type="textarea" :rows="2" placeholder="简单写清这个细项怎么看" /></el-form-item>
        <el-form-item label="来源">
          <el-select v-model="indicatorForm.source_type" style="width: 100%">
            <el-option v-for="item in sourceTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="比重"><el-input-number v-model="indicatorForm.default_weight" :min="0" :max="10" :step="0.1" /></el-form-item>
        <el-form-item label="顺序"><el-input-number v-model="indicatorForm.sort_order" :min="1" :max="999" /></el-form-item>
        <el-form-item label="使用"><el-switch v-model="indicatorForm.active" /></el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editorDialogVisible = false">取消</el-button>
        <el-button
          v-if="editorDialogMode === 'current'"
          type="primary"
          :loading="saving"
          @click="saveDimension"
        >
          保存大类
        </el-button>
        <el-button
          v-else-if="editorDialogMode === 'create-dimension'"
          type="primary"
          :loading="saving"
          @click="createDimension"
        >
          创建大类
        </el-button>
        <el-button
          v-else
          type="primary"
          :loading="saving"
          @click="createIndicator"
        >
          创建细项
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.dimension-manager {
  display: grid;
  gap: 16px;
}

.dimension-manager__panel {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

.dimension-manager__panel::before {
  display: none;
}

.dimension-master {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  grid-template-areas: "sidebar detail";
  gap: 16px;
  align-items: start;
  min-height: 0;
}

.dimension-master__sidebar {
  grid-area: sidebar;
  display: grid;
  gap: 10px;
  align-content: start;
}

.dimension-master__detail {
  grid-area: detail;
  min-width: 0;
  display: grid;
  gap: 14px;
  align-content: start;
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.content-title {
  font-size: 18px;
  font-weight: 700;
  color: #22395b;
}

.content-subtitle {
  display: none;
}

.dimension-card,
.dimension-master__detail {
  border-radius: 24px;
}

.dimension-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  padding: 14px 16px;
  cursor: pointer;
  transition: 0.2s ease;
  min-height: 76px;
  display: flex;
  align-items: center;
}

.dimension-card.is-active {
  border-color: rgba(34, 197, 94, 0.24);
  background: radial-gradient(circle at top left, rgba(187, 247, 208, 0.4), transparent 55%), #ffffff;
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.08);
}

.dimension-card__title {
  margin-top: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.dimension-card.is-active .dimension-card__title {
  color: #1f2937;
}

.panel-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-header-row--toolbar {
  align-items: center;
}

.panel-kicker {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}

.panel-title {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.panel-subtitle {
  display: none;
}

.indicator-table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.indicator-table-header__meta {
  font-size: 12px;
  color: #6b7280;
}

.indicator-list {
  --indicator-card-height: 112px;
  display: grid;
  gap: 14px;
}

.indicator-list--scroll {
  max-height: calc(var(--indicator-card-height) * 3 + 28px);
  overflow-y: auto;
  padding-right: 6px;
}

.indicator-list__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
  padding: 18px 20px;
  min-height: var(--indicator-card-height);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: none;
}

.indicator-list__main {
  min-width: 0;
  display: grid;
  gap: 10px;
}

.indicator-list__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.indicator-list__title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.indicator-list__code {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.indicator-list__desc {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.7;
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.indicator-list__meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.indicator-list__pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: #ffffff;
  color: #334155;
  font-size: 13px;
  font-weight: 700;
}

.indicator-list__pill--source {
  background: #eff6ff;
  color: #334155;
}

.indicator-list__pill--weight {
  background: #f8fafc;
  color: #475569;
}

.indicator-list__pill--active {
  border-color: #c8dfbc;
  background: #f0f9eb;
  color: #48643d;
}

.indicator-list__pill--inactive {
  border-color: #e4e9f1;
  background: #f7f9fc;
  color: #7a889f;
}

.dimension-action-nav {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 14px;
  flex-wrap: wrap;
  padding: 8px 0 14px;
}

.dimension-action-nav--toolbar {
  flex: 1;
  min-width: 0;
  padding: 0;
  border-bottom: none;
}

.dimension-action-nav__item {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  min-height: 46px;
  padding: 0 22px;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 700;
  color: #334155;
  cursor: pointer;
  box-shadow: none;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.dimension-action-nav__item:hover {
  border-color: rgba(59, 130, 246, 0.24);
  background: radial-gradient(circle at top left, rgba(191, 219, 254, 0.26), transparent 55%), #ffffff;
  color: #1d4ed8;
}

.dimension-master__detail :deep(.el-table) {
  border-radius: 24px !important;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18) !important;
  box-shadow: none !important;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
}

.dimension-master__detail :deep(.el-table__inner-wrapper) {
  border-radius: 24px !important;
}

.dimension-master__detail :deep(.el-table::before),
.dimension-master__detail :deep(.el-table--border::before),
.dimension-master__detail :deep(.el-table--border::after) {
  background-color: #dbe5f1 !important;
}

.dimension-master__detail :deep(.el-table__border-left-patch) {
  background: #dbe5f1 !important;
}

.dimension-master__detail :deep(.el-table th.el-table__cell) {
  background: #f8fbff !important;
  color: #475569;
  font-weight: 800;
}

.dimension-master__detail :deep(.el-table td.el-table__cell),
.dimension-master__detail :deep(.el-table th.el-table__cell) {
  padding-top: 14px;
  padding-bottom: 14px;
  border-right: 1px solid #e6edf7 !important;
  border-bottom: 1px solid #e6edf7 !important;
}

.dimension-master__detail :deep(.el-table tr td:last-child),
.dimension-master__detail :deep(.el-table tr th:last-child) {
  border-right: none !important;
}

.dimension-master__detail :deep(.el-table__row:last-child td.el-table__cell) {
  border-bottom: none !important;
}

.panel-header-row :deep(.el-button),
:deep(.el-dialog .el-button) {
  border-radius: 999px !important;
  border: 1px solid rgba(31, 41, 55, 0.14) !important;
  background: linear-gradient(180deg, #dff2fb 0%, #ebf8ff 100%) !important;
  background-image: none !important;
  color: #334155 !important;
  font-weight: 700;
  box-shadow: none !important;
}

.panel-header-row :deep(.el-button:hover),
:deep(.el-dialog .el-button:hover) {
  border-color: rgba(31, 41, 55, 0.24) !important;
  background: #ebf8ff !important;
  background-image: none !important;
  color: #1f2937 !important;
}

:deep(.el-dialog .el-button--primary),
:deep(.el-dialog .el-button--success) {
  border-color: #1f2937 !important;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
  background-image: none !important;
  color: #ffffff !important;
}

@media (max-width: 1280px) {
  .dimension-master {
    grid-template-columns: 1fr;
    grid-template-areas:
      "sidebar"
      "detail";
  }

  .indicator-list__item {
    grid-template-columns: 1fr;
  }

  .indicator-list__meta {
    justify-content: flex-start;
  }

}
</style>
