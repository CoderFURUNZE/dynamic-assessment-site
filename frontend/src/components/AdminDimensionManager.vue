<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import HoverTip from "./HoverTip.vue";

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
const editorTab = ref("current");

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

const sourceTypeOptions = [
  { value: "auto", label: "系统自动", description: "来自系统自动采集的学习行为、图谱掌握度和过程数据。" },
  { value: "imported", label: "阶段导入", description: "来自老师每个阶段导入的成绩、考勤、任务和课堂记录。" },
  { value: "teacher", label: "教师补充", description: "来自老师对学生高阶表现和课堂观察的补充评分。" },
  { value: "questionnaire", label: "问卷自评", description: "来自学生基础信息、兴趣问卷和自评内容。" },
];

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
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "创建维度失败");
  } finally {
    saving.value = false;
  }
}

async function createIndicator() {
  if (!selectedDimension.value) {
    ElMessage.warning("请先选择一级维度");
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
      dimension_id: selectedDimension.value.id,
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
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "创建二级指标失败");
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await loadTree();
  fillDimensionForm();
});

watch(
  () => selectedDimensionId.value,
  () => {
    fillDimensionForm();
    if (!selectedDimension.value) editorTab.value = "create-dimension";
  }
);
</script>

<template>
  <div class="dimension-manager">
    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-header-row">
          <div>
            <div class="panel-kicker">Portrait Setup</div>
            <div class="panel-title">评价维度和细项设置</div>
            <div class="panel-subtitle">先把五大一级维度、二级细项和数据来源定清楚，后面的阶段画像、雷达图和期末评分都会按这里的结构计算。</div>
          </div>
          <el-button size="small" :loading="loading" @click="loadTree">刷新</el-button>
        </div>
      </template>

      <div class="dimension-layout" v-loading="loading">
        <div class="dimension-sidebar">
          <el-card class="source-card" shadow="never">
            <div class="source-card__title">标准来源</div>
            <div class="source-card__list">
              <div v-for="item in sourceTypeOptions" :key="item.value" class="source-card__item">
                <div class="source-card__label">{{ item.label }}</div>
                <div class="source-card__desc">{{ item.description }}</div>
              </div>
            </div>
          </el-card>
          <div class="dimension-tip-inline">
            <span>提示</span>
            <HoverTip content="管理员负责定五大维度和细项框架；老师只按课程选择哪些细项参与画像。" />
          </div>
          <div
            v-for="item in dimensions"
            :key="item.id"
            class="dimension-card"
            :class="{ 'is-active': item.id === selectedDimensionId }"
            @click="selectedDimensionId = item.id; fillDimensionForm()"
          >
            <div class="dimension-card__code">{{ item.code }}</div>
            <div class="dimension-card__title">{{ item.title }}</div>
            <div class="dimension-card__meta">{{ item.indicators.length }} 个细项</div>
          </div>
        </div>

        <div class="dimension-content">
          <el-card class="inner-card" shadow="never">
            <template #header>
              <div class="content-header">
                <div>
                  <div class="content-title">{{ selectedDimension?.title || "先从左边选择一个大类" }}</div>
                  <div class="content-subtitle">
                    {{ selectedDimension ? `当前共有 ${selectedDimension.indicators.length} 个细项` : "选中后再修改大类和细项" }}
                  </div>
                </div>
              </div>
            </template>

            <el-tabs v-model="editorTab" class="dimension-tabs">
              <el-tab-pane label="修改当前大类" name="current">
                <el-empty v-if="!selectedDimension" description="还没有大类" :image-size="72" />
                <el-form v-else label-width="88px" size="small">
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
                  <el-form-item>
                    <el-button type="primary" :loading="saving" @click="saveDimension">保存大类</el-button>
                  </el-form-item>
                </el-form>
              </el-tab-pane>

              <el-tab-pane label="新增大类" name="create-dimension">
                <el-form label-width="88px" size="small">
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
                  <el-form-item>
                    <el-button type="success" :loading="saving" @click="createDimension">创建大类</el-button>
                  </el-form-item>
                </el-form>
              </el-tab-pane>

	              <el-tab-pane label="新增细项" name="create-indicator">
                <el-form label-width="88px" size="small">
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
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="createIndicator">创建细项</el-button>
              </el-form-item>
            </el-form>
              </el-tab-pane>
            </el-tabs>
          </el-card>

	          <el-card class="inner-card" shadow="never">
	            <template #header>
                <div class="indicator-table-header">
                  <span>当前细项</span>
                  <span v-if="selectedDimension" class="indicator-table-header__meta">
                    {{ selectedDimension.title }} · {{ selectedDimension.indicators.length }} 项
                  </span>
                </div>
              </template>
	            <el-empty v-if="!selectedDimension" description="先选择左侧大类" :image-size="72" />
	            <el-table v-else :data="selectedDimension.indicators" size="small" border>
	              <el-table-column prop="code" label="代号" min-width="140" />
	              <el-table-column prop="title" label="名称" min-width="180" />
	              <el-table-column label="来源" min-width="110">
                  <template #default="scope">{{ sourceTypeLabel(scope.row.source_type) }}</template>
                </el-table-column>
                <el-table-column prop="description" label="用途说明" min-width="260" show-overflow-tooltip />
	              <el-table-column prop="default_weight" label="默认权重" width="96" />
	              <el-table-column prop="active" label="使用" width="70">
	                <template #default="scope">{{ scope.row.active ? '是' : '否' }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.dimension-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
}

.dimension-sidebar,
.dimension-content {
  display: grid;
  gap: 16px;
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
  margin-top: 4px;
  font-size: 12px;
  color: #7186a6;
}

.dimension-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.dimension-tip-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
  color: #637995;
  font-size: 13px;
  font-weight: 700;
}

.source-card {
  border-radius: 12px;
}

.source-card__title {
  font-size: 14px;
  font-weight: 700;
  color: #203a61;
}

.source-card__list {
  margin-top: 12px;
  display: grid;
  gap: 12px;
}

.source-card__item {
  padding: 10px 12px;
  border-radius: 12px;
  background: #f5f8ff;
  border: 1px solid #e2eaf6;
}

.source-card__label {
  font-size: 13px;
  font-weight: 700;
  color: #33558d;
}

.source-card__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #6f809f;
}

.dimension-card,
.inner-card {
  border-radius: 12px;
}

.dimension-card {
  border: 1px solid #e1eaf1;
  background: #ffffff;
  padding: 16px;
  cursor: pointer;
  transition: 0.2s ease;
}

.dimension-card.is-active {
  border-color: #4a78d5;
  box-shadow: 0 2px 8px rgba(74, 120, 213, 0.1);
}

.dimension-card__code {
  font-size: 12px;
  color: #6f86ab;
  font-weight: 700;
}

.dimension-card__title {
  margin-top: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1e3558;
}

.dimension-card__meta {
  margin-top: 6px;
  color: #7f8faa;
  font-size: 13px;
}

.panel-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-kicker {
  font-size: 12px;
  color: #6d8fc3;
  font-weight: 600;
}

.panel-title {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 600;
  color: #22395b;
}

.panel-subtitle {
  margin-top: 8px;
  max-width: 860px;
  font-size: 13px;
  line-height: 1.7;
  color: #6f809f;
}

.indicator-table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.indicator-table-header__meta {
  font-size: 12px;
  color: #6f809f;
}

@media (max-width: 1280px) {
  .dimension-layout {
    grid-template-columns: 1fr;
  }
}
</style>
