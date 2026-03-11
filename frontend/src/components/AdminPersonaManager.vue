<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";

const props = withDefaults(defineProps<{ subject: string; grade: string; showStudentDetailAction?: boolean }>(), {
  showStudentDetailAction: false,
});
const emit = defineEmits<{
  (e: "view-student", userId: number): void;
}>();

type PersonaStudent = {
  user_id: number;
  username: string;
  full_name: string;
  student_no: string;
  class_name: string;
  persona_type: string;
  persona_label: string;
  dynamic_score: number;
  course_mastery: number;
  risk_level: string;
  override_source: string;
  reason_summary: string;
  updated_at: string;
  latest_stage_title?: string;
  stage_trend?: string;
};

const loading = ref(false);
const saving = ref(false);
const students = ref<PersonaStudent[]>([]);
const weightText = ref("");
const stageDimensions = reactive<Record<string, { enabled: boolean; weight: number }>>({
  engagement: { enabled: true, weight: 0.3 },
  achievement: { enabled: true, weight: 0.35 },
  habit: { enabled: true, weight: 0.2 },
  characteristic: { enabled: true, weight: 0.15 },
});
const strategies = reactive<Record<string, string>>({
  smart_capable: "",
  diligent: "",
  struggling_persistent: "",
  procrastinating_risk: "",
  steady_progress: "",
});
const thresholds = reactive({
  procrastinating_e: 0.4,
  smart_a: 0.75,
  smart_f: 0.75,
  diligent_e: 0.75,
  diligent_a: 0.6,
  struggling_e: 0.6,
  struggling_a: 0.6,
});
const selectedOverride = reactive<Record<number, string>>({});

const personaOptions = [
  { label: "聪明能干型", value: "smart_capable" },
  { label: "踏实学习型", value: "diligent" },
  { label: "困难坚持型", value: "struggling_persistent" },
  { label: "拖延风险型", value: "procrastinating_risk" },
  { label: "平稳发展型", value: "steady_progress" },
];
const dimensionOptions = [
  { key: "engagement", label: "学习投入" },
  { key: "achievement", label: "学习成效" },
  { key: "habit", label: "学习习惯" },
  { key: "characteristic", label: "学习特征" },
];

const riskyCount = computed(() => students.value.filter((item) => item.risk_level === "风险").length);
const canManage = computed(() => getRole() === "admin");

async function loadRules() {
  const res = await api.get(
    `/admin/persona/rules?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
  );
  Object.assign(thresholds, res.data.thresholds ?? {});
  Object.assign(strategies, res.data.strategies ?? {});
  const weights = res.data.weights ?? {};
  const dimensionConfig = weights.stage_dimensions ?? {};
  for (const item of dimensionOptions) {
    stageDimensions[item.key] = {
      enabled: Boolean(dimensionConfig[item.key]?.enabled ?? true),
      weight: Number(dimensionConfig[item.key]?.weight ?? stageDimensions[item.key]?.weight ?? 0),
    };
  }
  weightText.value = JSON.stringify(weights, null, 2);
}

async function loadStudents() {
  const res = await api.get(
    `/admin/persona/students?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
  );
  students.value = res.data.items ?? [];
  for (const row of students.value) {
    selectedOverride[row.user_id] = row.persona_type;
  }
}

async function reloadAll() {
  if (!props.subject) return;
  loading.value = true;
  try {
    await Promise.all([loadRules(), loadStudents()]);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载画像配置失败");
  } finally {
    loading.value = false;
  }
}

async function saveRules() {
  try {
    saving.value = true;
    const weights = JSON.parse(weightText.value || "{}");
    weights.stage_dimensions = weights.stage_dimensions ?? {};
    for (const item of dimensionOptions) {
      weights.stage_dimensions[item.key] = {
        ...(weights.stage_dimensions[item.key] ?? {}),
        enabled: Boolean(stageDimensions[item.key]?.enabled),
        weight: Number(stageDimensions[item.key]?.weight ?? 0),
      };
    }
    weightText.value = JSON.stringify(weights, null, 2);
    await api.put(`/admin/persona/rules?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`, {
      thresholds,
      weights,
      strategies,
    });
    ElMessage.success("画像规则已保存");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "规则保存失败，请检查权重 JSON 格式");
  } finally {
    saving.value = false;
  }
}

async function recalc(refreshMastery = false) {
  try {
    saving.value = true;
    await api.post("/admin/persona/recalculate", {
      subject: props.subject,
      grade: props.grade,
      refresh_mastery: refreshMastery,
    });
    ElMessage.success("已完成画像重算");
    await loadStudents();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "画像重算失败");
  } finally {
    saving.value = false;
  }
}

async function saveOverride(row: PersonaStudent) {
  try {
    await api.put("/admin/persona/override", {
      user_id: row.user_id,
      subject: props.subject,
      grade: props.grade,
      persona_type: selectedOverride[row.user_id],
      note: `管理员人工覆盖：${selectedOverride[row.user_id]}`,
    });
    ElMessage.success("已保存人工覆盖");
    await loadStudents();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存覆盖失败");
  }
}

async function clearOverride(row: PersonaStudent) {
  try {
    await api.delete(
      `/admin/persona/override?user_id=${row.user_id}&subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`
    );
    ElMessage.success("已清除人工覆盖");
    await loadStudents();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "清除覆盖失败");
  }
}

watch(
  () => [props.subject, props.grade],
  () => reloadAll(),
  { immediate: true }
);
</script>

<template>
  <div class="persona-shell" v-loading="loading">
    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="persona-header">
          <div>
            <div class="persona-title">学习者画像规则</div>
            <div class="persona-subtitle">管理员在这里配置分型阈值、策略模板，并可一键重算全体学生画像。</div>
          </div>
          <div class="persona-actions">
            <el-button size="small" @click="reloadAll">刷新</el-button>
            <el-button size="small" @click="recalc(false)" :loading="saving" :disabled="!canManage">重算画像</el-button>
            <el-button size="small" type="warning" @click="recalc(true)" :loading="saving" :disabled="!canManage">重算画像+掌握度</el-button>
            <el-button size="small" type="primary" @click="saveRules" :loading="saving" :disabled="!canManage">保存规则</el-button>
          </div>
        </div>
      </template>

      <div class="persona-grid">
        <section class="persona-section">
          <div class="section-title">分型阈值</div>
          <div class="threshold-grid">
            <label>
              <span>拖延阈值 E</span>
              <el-input-number v-model="thresholds.procrastinating_e" :min="0" :max="1" :step="0.01" />
            </label>
            <label>
              <span>聪明型 A</span>
              <el-input-number v-model="thresholds.smart_a" :min="0" :max="1" :step="0.01" />
            </label>
            <label>
              <span>聪明型 F</span>
              <el-input-number v-model="thresholds.smart_f" :min="0" :max="1" :step="0.01" />
            </label>
            <label>
              <span>踏实型 E</span>
              <el-input-number v-model="thresholds.diligent_e" :min="0" :max="1" :step="0.01" />
            </label>
            <label>
              <span>踏实型 A</span>
              <el-input-number v-model="thresholds.diligent_a" :min="0" :max="1" :step="0.01" />
            </label>
            <label>
              <span>困难型 E</span>
              <el-input-number v-model="thresholds.struggling_e" :min="0" :max="1" :step="0.01" />
            </label>
            <label>
              <span>困难型 A</span>
              <el-input-number v-model="thresholds.struggling_a" :min="0" :max="1" :step="0.01" />
            </label>
          </div>
        </section>

        <section class="persona-section">
          <div class="section-title">策略模板</div>
          <div class="strategy-grid">
            <label v-for="item in personaOptions" :key="item.value">
              <span>{{ item.label }}</span>
              <el-input v-model="strategies[item.value]" />
            </label>
          </div>
        </section>

        <section class="persona-section">
          <div class="section-title">阶段维度配置</div>
          <div class="dimension-grid">
            <label v-for="item in dimensionOptions" :key="item.key" class="dimension-card">
              <div class="dimension-card__top">
                <span>{{ item.label }}</span>
                <el-switch v-model="stageDimensions[item.key].enabled" />
              </div>
              <div class="dimension-card__bottom">
                <span>权重</span>
                <el-input-number v-model="stageDimensions[item.key].weight" :min="0" :max="1" :step="0.05" />
              </div>
            </label>
          </div>
        </section>

        <section class="persona-section persona-section--full">
          <div class="section-title">画像权重 JSON</div>
          <el-input
            v-model="weightText"
            type="textarea"
            :rows="10"
            placeholder="请输入画像维度权重 JSON"
          />
        </section>
      </div>
    </el-card>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="persona-summary">
          <div>学生画像列表</div>
          <el-tag type="danger">风险学生 {{ riskyCount }}</el-tag>
        </div>
      </template>

      <el-table :data="students" size="small" style="width: 100%">
        <el-table-column prop="username" label="账号" width="130" />
        <el-table-column prop="full_name" label="姓名" width="110" />
        <el-table-column prop="persona_label" label="当前类型" width="140" />
        <el-table-column prop="latest_stage_title" label="最新阶段" width="160" />
        <el-table-column prop="stage_trend" label="阶段变化" width="100" />
        <el-table-column prop="dynamic_score" label="动态评分" width="110">
          <template #default="{ row }">
            {{ Math.round((row.dynamic_score || 0) * 100) }}%
          </template>
        </el-table-column>
        <el-table-column prop="course_mastery" label="课程掌握度" width="120">
          <template #default="{ row }">
            {{ Math.round((row.course_mastery || 0) * 100) }}%
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="等级" width="90" />
        <el-table-column prop="reason_summary" label="判定依据" min-width="220" />
        <el-table-column v-if="props.showStudentDetailAction" label="详情" width="100">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="emit('view-student', row.user_id)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column label="人工覆盖" width="250">
          <template #default="{ row }">
            <div class="override-cell">
              <el-select v-model="selectedOverride[row.user_id]" size="small" style="width: 140px">
                <el-option v-for="item in personaOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-button size="small" type="primary" @click="saveOverride(row)" :disabled="!canManage">保存</el-button>
              <el-button size="small" @click="clearOverride(row)" :disabled="!canManage || row.override_source !== 'manual'">清除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.persona-shell {
  display: grid;
  gap: 16px;
}

.persona-header,
.persona-summary {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.persona-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.persona-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-ink-soft);
}

.persona-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.persona-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.persona-section {
  padding: 18px;
  border-radius: 18px;
  background: #f7fafc;
  border: 1px solid #e1eaf1;
}

.persona-section--full {
  grid-column: 1 / -1;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-ink);
  margin-bottom: 14px;
}

.threshold-grid,
.strategy-grid,
.dimension-grid {
  display: grid;
  gap: 12px;
}

.threshold-grid label,
.strategy-grid label {
  display: grid;
  gap: 6px;
  color: #5c7592;
  font-size: 12px;
}

.dimension-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dimension-card {
  padding: 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #dbe6ef;
  display: grid;
  gap: 12px;
}

.dimension-card__top,
.dimension-card__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dimension-card__top {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-ink);
}

.dimension-card__bottom {
  font-size: 12px;
  color: #5c7592;
}

.override-cell {
  display: flex;
  gap: 8px;
  align-items: center;
}

@media (max-width: 960px) {
  .persona-grid {
    grid-template-columns: 1fr;
  }

  .dimension-grid {
    grid-template-columns: 1fr;
  }
}
</style>
