<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
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

const dimensionForm = reactive({
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
  if (!dimensionForm.code.trim() || !dimensionForm.title.trim()) {
    ElMessage.warning("请填写维度编码和标题");
    return;
  }
  saving.value = true;
  try {
    await api.post("/portrait/dimensions", { ...dimensionForm });
    ElMessage.success("维度已创建");
    dimensionForm.code = "";
    dimensionForm.title = "";
    dimensionForm.description = "";
    dimensionForm.sort_order = 10;
    dimensionForm.active = true;
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
</script>

<template>
  <div class="dimension-manager">
    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-header-row">
          <div>
            <div class="panel-kicker">Portrait Dimension Pool</div>
            <div class="panel-title">一级维度与二级指标池</div>
          </div>
          <el-button size="small" :loading="loading" @click="loadTree">刷新</el-button>
        </div>
      </template>

      <div class="dimension-layout" v-loading="loading">
        <div class="dimension-sidebar">
          <div
            v-for="item in dimensions"
            :key="item.id"
            class="dimension-card"
            :class="{ 'is-active': item.id === selectedDimensionId }"
            @click="selectedDimensionId = item.id; fillDimensionForm()"
          >
            <div class="dimension-card__code">{{ item.code }}</div>
            <div class="dimension-card__title">{{ item.title }}</div>
            <div class="dimension-card__meta">{{ item.indicators.length }} 个二级指标</div>
          </div>
        </div>

        <div class="dimension-main">
          <el-card class="inner-card" shadow="never">
            <template #header>编辑当前一级维度</template>
            <el-empty v-if="!selectedDimension" description="暂无维度" :image-size="72" />
            <el-form v-else label-width="88px" size="small">
              <el-form-item label="编码"><el-input v-model="dimensionForm.code" /></el-form-item>
              <el-form-item label="标题"><el-input v-model="dimensionForm.title" /></el-form-item>
              <el-form-item label="说明"><el-input v-model="dimensionForm.description" type="textarea" :rows="3" /></el-form-item>
              <el-form-item label="排序">
                <el-input-number v-model="dimensionForm.sort_order" :min="1" :max="999" />
              </el-form-item>
              <el-form-item label="启用"><el-switch v-model="dimensionForm.active" /></el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="saveDimension">保存一级维度</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card class="inner-card" shadow="never">
            <template #header>新增一级维度</template>
            <el-form label-width="88px" size="small">
              <el-form-item label="编码"><el-input v-model="dimensionForm.code" placeholder="例如 learning_behavior" /></el-form-item>
              <el-form-item label="标题"><el-input v-model="dimensionForm.title" placeholder="例如 学习行为与过程" /></el-form-item>
              <el-form-item label="说明"><el-input v-model="dimensionForm.description" type="textarea" :rows="2" /></el-form-item>
              <el-form-item label="排序"><el-input-number v-model="dimensionForm.sort_order" :min="1" :max="999" /></el-form-item>
              <el-form-item label="启用"><el-switch v-model="dimensionForm.active" /></el-form-item>
              <el-form-item>
                <el-button type="success" :loading="saving" @click="createDimension">创建一级维度</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <div class="dimension-detail">
          <el-card class="inner-card" shadow="never">
            <template #header>
              当前二级指标
            </template>
            <el-empty v-if="!selectedDimension" description="先选择一级维度" :image-size="72" />
            <el-table v-else :data="selectedDimension.indicators" size="small" border>
              <el-table-column prop="code" label="编码" min-width="140" />
              <el-table-column prop="title" label="标题" min-width="180" />
              <el-table-column prop="source_type" label="来源" width="92" />
              <el-table-column prop="default_weight" label="默认权重" width="96" />
              <el-table-column prop="active" label="启用" width="70">
                <template #default="scope">{{ scope.row.active ? '是' : '否' }}</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card class="inner-card" shadow="never">
            <template #header>新增二级指标</template>
            <el-form label-width="88px" size="small">
              <el-form-item label="编码"><el-input v-model="indicatorForm.code" placeholder="例如 resource_preference" /></el-form-item>
              <el-form-item label="标题"><el-input v-model="indicatorForm.title" placeholder="例如 资源偏好" /></el-form-item>
              <el-form-item label="说明"><el-input v-model="indicatorForm.description" type="textarea" :rows="2" /></el-form-item>
              <el-form-item label="来源">
                <el-select v-model="indicatorForm.source_type" style="width: 100%">
                  <el-option label="系统自动" value="auto" />
                  <el-option label="教师评价" value="teacher" />
                  <el-option label="问卷采集" value="questionnaire" />
                </el-select>
              </el-form-item>
              <el-form-item label="权重"><el-input-number v-model="indicatorForm.default_weight" :min="0" :max="10" :step="0.1" /></el-form-item>
              <el-form-item label="排序"><el-input-number v-model="indicatorForm.sort_order" :min="1" :max="999" /></el-form-item>
              <el-form-item label="启用"><el-switch v-model="indicatorForm.active" /></el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="createIndicator">创建二级指标</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.dimension-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 16px;
}

.dimension-sidebar,
.dimension-main,
.dimension-detail {
  display: grid;
  gap: 16px;
  align-content: start;
}

.dimension-card,
.inner-card {
  border-radius: 22px;
}

.dimension-card {
  border: 1px solid rgba(109, 146, 211, 0.28);
  background: linear-gradient(180deg, rgba(244, 248, 255, 0.98), rgba(236, 243, 255, 0.98));
  padding: 16px;
  cursor: pointer;
  transition: 0.2s ease;
}

.dimension-card.is-active {
  border-color: rgba(74, 120, 213, 0.58);
  box-shadow: 0 16px 32px rgba(43, 79, 145, 0.16);
}

.dimension-card__code {
  font-size: 12px;
  color: #6f86ab;
  font-weight: 700;
}

.dimension-card__title {
  margin-top: 8px;
  font-size: 18px;
  font-weight: 800;
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
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #6d8fc3;
  font-weight: 800;
}

.panel-title {
  margin-top: 6px;
  font-size: 24px;
  font-weight: 800;
  color: #22395b;
}

@media (max-width: 1280px) {
  .dimension-layout {
    grid-template-columns: 1fr;
  }
}
</style>
