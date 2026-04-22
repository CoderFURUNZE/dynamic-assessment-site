<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ArrowDown, ChatLineRound, Compass, DataAnalysis, WarningFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";

type PersonaStep = "all" | "settings" | "thresholds" | "rules" | "results";
type ManagerRole = "admin" | "teacher";
type PersonaKey = "smart_capable" | "diligent" | "struggling_persistent" | "procrastinating_risk" | "steady_progress";
type ThresholdKey = "procrastinating_e" | "smart_a" | "smart_f" | "diligent_e" | "diligent_a" | "struggling_e" | "struggling_a";
type DimensionKey = "engagement" | "achievement" | "habit" | "characteristic";
type PresetKey = "steady" | "balanced" | "strict" | "custom";

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

type StageDimensionState = Record<DimensionKey, { enabled: boolean; weight: number }>;
type StrategyState = Record<PersonaKey, string>;
type ThresholdState = Record<ThresholdKey, number>;

const props = withDefaults(
  defineProps<{
    subject: string;
    grade: string;
    showStudentDetailAction?: boolean;
    readonly?: boolean;
    step?: PersonaStep;
    managerRole?: ManagerRole;
  }>(),
  {
    showStudentDetailAction: false,
    readonly: false,
    step: "settings",
    managerRole: "admin",
  },
);

const emit = defineEmits<{
  (e: "view-student", userId: number): void;
}>();

const presetOptions = [
  { key: "steady", title: "稳妥型", desc: "先跑通系统，避免一次识别过多风险学生。", tag: "保守识别", icon: Compass },
  { key: "balanced", title: "平衡型", desc: "适合大多数课程，兼顾识别与预警。", tag: "默认推荐", icon: DataAnalysis },
  { key: "strict", title: "严格型", desc: "更早发现拖延、低投入和低成效学生。", tag: "提前预警", icon: WarningFilled },
] as const;

const personaOptions = [
  { label: "聪明能干型", value: "smart_capable" },
  { label: "踏实学习型", value: "diligent" },
  { label: "困难坚持型", value: "struggling_persistent" },
  { label: "拖延风险型", value: "procrastinating_risk" },
  { label: "平稳发展型", value: "steady_progress" },
] as const;

const dimensionOptions = [
  { key: "engagement", label: "学习投入" },
  { key: "achievement", label: "学习成效" },
  { key: "habit", label: "学习习惯" },
  { key: "characteristic", label: "学习特征" },
] as const;

const loading = ref(false);
const saving = ref(false);
const recalculating = ref(false);
const students = ref<PersonaStudent[]>([]);
const selectedPreset = ref<PresetKey>("balanced");
const strategiesEditing = ref(false);
const rulesConfigExpanded = ref(false);
const weightText = ref("");
const resultKeyword = ref("");
const resultPersonaFilter = ref("all");
const resultRiskFilter = ref("all");
const selectedOverride = reactive<Record<number, string>>({});

const stageDimensions = reactive<StageDimensionState>({
  engagement: { enabled: true, weight: 0.3 },
  achievement: { enabled: true, weight: 0.35 },
  habit: { enabled: true, weight: 0.2 },
  characteristic: { enabled: true, weight: 0.15 },
});

const strategies = reactive<StrategyState>({
  smart_capable: "更高难度+精讲提要",
  diligent: "结构化路径+阶段反馈",
  struggling_persistent: "补救前置点+低阶练习",
  procrastinating_risk: "最短任务链+提醒",
  steady_progress: "标准推荐",
});

const thresholds = reactive<ThresholdState>({
  procrastinating_e: 0.4,
  smart_a: 0.75,
  smart_f: 0.75,
  diligent_e: 0.75,
  diligent_a: 0.6,
  struggling_e: 0.6,
  struggling_a: 0.6,
});

const showRulesStep = computed(() => props.step === "all" || props.step === "settings" || props.step === "rules");
const showResultsStep = computed(() => props.step === "all" || props.step === "results");
const showPresetStep = computed(() => props.step === "all" || props.step === "settings");
const canManage = computed(() => getRole() === props.managerRole && !props.readonly);
const isReadonlyView = computed(() => !canManage.value);
const saveActionLabel = computed(() => (props.managerRole === "teacher" ? "保存课程规则" : "保存模板"));
const enabledDimensionCount = computed(() => dimensionOptions.filter((item) => stageDimensions[item.key].enabled).length);
const enabledDimensionWeightTotal = computed(() => Number(dimensionOptions.filter((item) => stageDimensions[item.key].enabled).reduce((sum, item) => sum + Number(stageDimensions[item.key].weight || 0), 0).toFixed(2)));
const isDimensionWeightValid = computed(() => enabledDimensionCount.value > 0 && Math.abs(enabledDimensionWeightTotal.value - 1) < 0.001);
const riskyCount = computed(() => students.value.filter((item) => item.risk_level === "风险").length);

const filteredStudents = computed(() => {
  const keyword = resultKeyword.value.trim().toLowerCase();
  return students.value.filter((item) => {
    const matchesKeyword = !keyword || [item.username, item.full_name, item.student_no, item.class_name, item.persona_label, item.reason_summary].join(" ").toLowerCase().includes(keyword);
    const matchesPersona = resultPersonaFilter.value === "all" || item.persona_type === resultPersonaFilter.value;
    const matchesRisk = resultRiskFilter.value === "all" || item.risk_level === resultRiskFilter.value;
    return matchesKeyword && matchesPersona && matchesRisk;
  });
});

function clamp01(value: number) {
  return Math.max(0, Math.min(1, Number((Number.isFinite(value) ? value : 0).toFixed(2))));
}

function normalizeStageDimensions() {
  const enabledKeys = dimensionOptions.filter((item) => stageDimensions[item.key].enabled).map((item) => item.key);
  if (!enabledKeys.length) {
    stageDimensions.engagement.enabled = true;
    stageDimensions.engagement.weight = 1;
    return;
  }
  let total = enabledKeys.reduce((sum, key) => sum + Number(stageDimensions[key].weight || 0), 0);
  if (total <= 0) {
    const average = Number((1 / enabledKeys.length).toFixed(2));
    enabledKeys.forEach((key, index) => {
      stageDimensions[key].weight = index === enabledKeys.length - 1 ? clamp01(1 - average * (enabledKeys.length - 1)) : average;
    });
    return;
  }
  let allocated = 0;
  enabledKeys.forEach((key, index) => {
    if (index === enabledKeys.length - 1) {
      stageDimensions[key].weight = clamp01(1 - allocated);
      return;
    }
    const next = clamp01(Number(stageDimensions[key].weight || 0) / total);
    stageDimensions[key].weight = next;
    allocated = clamp01(allocated + next);
  });
}

function getDimensionMax(key: DimensionKey) {
  const otherTotal = dimensionOptions.filter((item) => item.key !== key && stageDimensions[item.key].enabled).reduce((sum, item) => sum + Number(stageDimensions[item.key].weight || 0), 0);
  return clamp01(1 - otherTotal);
}

function updateDimensionWeight(key: DimensionKey, nextValue: number | undefined) {
  if (!stageDimensions[key].enabled) return;
  const max = getDimensionMax(key);
  stageDimensions[key].weight = clamp01(Math.min(Number(nextValue ?? 0), max));
}

function toggleDimension(key: DimensionKey, enabled: boolean) {
  stageDimensions[key].enabled = enabled;
  if (!enabled) {
    stageDimensions[key].weight = 0;
  } else if (enabledDimensionCount.value <= 1) {
    stageDimensions[key].weight = 1;
  } else {
    normalizeStageDimensions();
  }
}

function fillState<T extends Record<string, any>>(target: T, source?: Record<string, any>) {
  if (!source) return;
  Object.keys(target).forEach((key) => {
    if (source[key] !== undefined) target[key] = source[key];
  });
}

function applyPresetConfig(presetKey: Exclude<PresetKey, "custom">) {
  const presets = {
    steady: {
      thresholds: { procrastinating_e: 0.32, smart_a: 0.8, smart_f: 0.8, diligent_e: 0.78, diligent_a: 0.65, struggling_e: 0.55, struggling_a: 0.55 },
      stageDimensions: {
        engagement: { enabled: true, weight: 0.25 },
        achievement: { enabled: true, weight: 0.4 },
        habit: { enabled: true, weight: 0.2 },
        characteristic: { enabled: true, weight: 0.15 },
      },
    },
    balanced: {
      thresholds: { procrastinating_e: 0.4, smart_a: 0.75, smart_f: 0.75, diligent_e: 0.75, diligent_a: 0.6, struggling_e: 0.6, struggling_a: 0.6 },
      stageDimensions: {
        engagement: { enabled: true, weight: 0.3 },
        achievement: { enabled: true, weight: 0.35 },
        habit: { enabled: true, weight: 0.2 },
        characteristic: { enabled: true, weight: 0.15 },
      },
    },
    strict: {
      thresholds: { procrastinating_e: 0.48, smart_a: 0.7, smart_f: 0.72, diligent_e: 0.72, diligent_a: 0.58, struggling_e: 0.65, struggling_a: 0.65 },
      stageDimensions: {
        engagement: { enabled: true, weight: 0.35 },
        achievement: { enabled: true, weight: 0.3 },
        habit: { enabled: true, weight: 0.2 },
        characteristic: { enabled: true, weight: 0.15 },
      },
    },
  } as const;
  const preset = presets[presetKey];
  fillState(thresholds, preset.thresholds as Record<string, any>);
  dimensionOptions.forEach((item) => {
    stageDimensions[item.key].enabled = preset.stageDimensions[item.key].enabled;
    stageDimensions[item.key].weight = preset.stageDimensions[item.key].weight;
  });
  normalizeStageDimensions();
}

function selectPreset(presetKey: Exclude<PresetKey, "custom">) {
  if (selectedPreset.value === presetKey && rulesConfigExpanded.value) {
    rulesConfigExpanded.value = false;
    return;
  }
  selectedPreset.value = presetKey;
  applyPresetConfig(presetKey);
  rulesConfigExpanded.value = true;
}

function getRulesPayload() {
  return {
    preset: selectedPreset.value,
    subject: props.subject,
    grade: props.grade,
    thresholds: { ...thresholds },
    stage_dimensions: Object.fromEntries(dimensionOptions.map((item) => [item.key, { enabled: stageDimensions[item.key].enabled, weight: stageDimensions[item.key].enabled ? stageDimensions[item.key].weight : 0 }])) as Record<string, { enabled: boolean; weight: number }>,
    strategies: { ...strategies },
    weight_text: weightText.value,
  };
}

function resolvePresetFromPayload(presetValue: unknown): PresetKey {
  if (presetValue === "steady" || presetValue === "balanced" || presetValue === "strict" || presetValue === "custom") return presetValue;
  return "balanced";
}

async function loadRules() {
  loading.value = true;
  try {
    const res = await api.get(`/admin/persona/rules?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
    const data = res.data ?? {};
    selectedPreset.value = resolvePresetFromPayload(data.preset);
    fillState(thresholds, data.thresholds);
    fillState(strategies, data.strategies);
    if (data.stage_dimensions) {
      dimensionOptions.forEach((item) => {
        const next = data.stage_dimensions[item.key];
        if (next) {
          stageDimensions[item.key].enabled = Boolean(next.enabled);
          stageDimensions[item.key].weight = Number(next.weight ?? 0);
        }
      });
    }
    weightText.value = String(data.weight_text ?? "");
    normalizeStageDimensions();
    rulesConfigExpanded.value = false;
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "规则配置加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadStudents() {
  loading.value = true;
  try {
    const res = await api.get(`/admin/persona/students?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
    const list = Array.isArray(res.data) ? res.data : Array.isArray(res.data?.items) ? res.data.items : [];
    students.value = list;
    Object.keys(selectedOverride).forEach((key) => delete selectedOverride[Number(key)]);
    list.forEach((item: PersonaStudent) => {
      selectedOverride[item.user_id] = item.override_source || "";
    });
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "画像结果加载失败");
  } finally {
    loading.value = false;
  }
}

async function saveRules() {
  if (!canManage.value) return;
  if (!isDimensionWeightValid.value) {
    ElMessage.error("启用维度的权重合计必须等于 1.00");
    return;
  }
  saving.value = true;
  try {
    await api.put(`/admin/persona/rules?subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`, getRulesPayload());
    ElMessage.success(saveActionLabel.value + "成功");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? (saveActionLabel.value + "失败"));
  } finally {
    saving.value = false;
  }
}

async function recalculate() {
  if (!canManage.value) return;
  recalculating.value = true;
  try {
    await api.post("/admin/persona/recalculate", { subject: props.subject, grade: props.grade });
    ElMessage.success("重算完成");
    await loadStudents();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "重算失败");
  } finally {
    recalculating.value = false;
  }
}

async function saveOverride(row: PersonaStudent) {
  if (!canManage.value) return;
  try {
    await api.put("/admin/persona/override", {
      user_id: row.user_id,
      subject: props.subject,
      grade: props.grade,
      persona_type: selectedOverride[row.user_id] || null,
    });
    ElMessage.success("人工覆盖已保存");
    await loadStudents();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "人工覆盖保存失败");
  }
}

async function clearOverride(row: PersonaStudent) {
  if (!canManage.value) return;
  try {
    await api.delete(`/admin/persona/override?user_id=${row.user_id}&subject=${encodeURIComponent(props.subject)}&grade=${encodeURIComponent(props.grade)}`);
    selectedOverride[row.user_id] = "";
    ElMessage.success("已恢复系统判定");
    await loadStudents();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "恢复系统判定失败");
  }
}

function scorePercent(value: number) {
  const num = Number(value || 0);
  if (Number.isNaN(num)) return "0%";
  return `${Math.round(num * 100)}%`;
}

function scoreToneClass(value: number) {
  const num = Number(value || 0) * 100;
  if (num >= 60) return "is-good";
  if (num >= 30) return "is-mid";
  return "is-bad";
}

function personaToneClass(label: string) {
  if (label.includes("高风险")) return "is-danger";
  if (label.includes("拖延")) return "is-warning";
  return "is-steady";
}

function levelToneClass(level: string) {
  if (level.includes("风险")) return "is-risk";
  if (level.includes("预警")) return "is-warning";
  return "is-stable";
}

function summarizeReason(row: PersonaStudent) {
  const summary = String(row.reason_summary || "").trim();
  if (!summary) return `${row.persona_label || "未分类"}；掌握度 ${Number(row.course_mastery || 0).toFixed(2)}`;
  return summary.replace(/\s+/g, " ");
}

function riskTagType(level: string) {
  return level === "风险" ? "danger" : "success";
}

watch(
  () => [props.subject, props.grade, props.step],
  async () => {
    if (!props.subject || !props.grade) return;
    await loadRules();
    if (showResultsStep.value) {
      await loadStudents();
    }
  },
  { immediate: true },
);
</script>
<template>
  <div class="persona-shell" v-loading="loading">
    <section v-if="!isReadonlyView && (showPresetStep || showRulesStep)" class="persona-card persona-unified-card">
      <div class="persona-step-header">
        <div>
          <h3 class="persona-title">规则配置</h3>
          <p class="persona-step-header__desc">先选方案，再调整维度和策略。</p>
        </div>
        <div class="persona-action-group persona-action-group--top">
          <el-button round @click="loadRules">刷新</el-button>
          <el-button round type="primary" :loading="saving" :disabled="!canManage || (showRulesStep && !isDimensionWeightValid)" @click="saveRules">{{ saveActionLabel }}</el-button>
        </div>
      </div>

      <div v-if="showPresetStep" class="persona-block">
        <div class="persona-block__title persona-block__title--with-icon">
          <el-icon><Compass /></el-icon>
          <span>规则方案选择</span>
        </div>
        <div class="persona-block__desc">先选一种判定风格，再继续配置。</div>
        <div class="persona-preset-grid">
          <div
            v-for="preset in presetOptions"
            :key="preset.key"
            class="persona-preset-card"
            :class="{ 'is-active': selectedPreset === preset.key }"
            @click="selectPreset(preset.key)"
            @keydown.enter.prevent="selectPreset(preset.key)"
            @keydown.space.prevent="selectPreset(preset.key)"
            role="button"
            tabindex="0"
          >
            <div class="persona-preset-card__head">
              <span class="persona-preset-card__icon">
                <el-icon><component :is="preset.icon" /></el-icon>
              </span>
              <span class="persona-preset-card__tag">{{ preset.tag }}</span>
            </div>
            <div class="persona-preset-card__title">{{ preset.title }}</div>
            <div class="persona-preset-card__desc">{{ preset.desc }}</div>
          </div>
        </div>
      </div>

      <div v-if="showRulesStep" class="persona-block">
        <div class="persona-block__header">
          <div>
            <div class="persona-block__title persona-block__title--with-icon">
              <el-icon><DataAnalysis /></el-icon>
              <span>规则与策略配置</span>
            </div>
            <div class="persona-block__desc">调整维度权重，并设置默认建议。</div>
          </div>
          <div class="persona-block__header-actions">
            <button
              type="button"
              class="persona-collapse-toggle-icon"
              @click="rulesConfigExpanded = !rulesConfigExpanded"
              :aria-label="rulesConfigExpanded ? '收起配置' : '展开配置'"
            >
              <el-icon class="persona-collapse-hint__arrow" :class="{ 'is-expanded': rulesConfigExpanded }"><ArrowDown /></el-icon>
            </button>
            <div class="persona-config-wrap__meta">{{ enabledDimensionCount }} 个维度 / {{ personaOptions.length }} 类模板</div>
          </div>
        </div>
        <div v-if="!rulesConfigExpanded" class="persona-collapse-hint">
          <div class="persona-collapse-hint__text">
            <span class="persona-collapse-hint__title">当前默认收起</span>
            <span class="persona-collapse-hint__desc">选择上方风格卡后，自动展开对应维度和策略信息。</span>
          </div>
        </div>
        <transition name="persona-expand">
          <div v-if="rulesConfigExpanded" class="persona-grid persona-grid--two">
            <section class="persona-section">
              <div class="section-title section-title--with-icon">
                <el-icon><DataAnalysis /></el-icon>
                <span>阶段维度配置</span>
              </div>
              <div class="section-desc">控制动态评价更看重哪一类学习表现。</div>
              <div class="dimension-summary" :class="{ 'is-error': !isDimensionWeightValid }">
                <span>当前启用维度 {{ enabledDimensionCount }} 个</span>
                <span>权重合计 {{ enabledDimensionWeightTotal.toFixed(2) }} / 1.00</span>
              </div>
              <div class="dimension-grid">
                <div v-for="item in dimensionOptions" :key="item.key" class="dimension-card">
                  <div class="dimension-card__head">
                    <div class="dimension-card__title">{{ item.label }}</div>
                    <el-switch
                      :model-value="stageDimensions[item.key].enabled"
                      :disabled="!canManage"
                      @update:model-value="(value:boolean) => { toggleDimension(item.key, value); selectedPreset = 'custom'; }"
                    />
                  </div>
                  <div class="dimension-card__body">
                    <span>权重</span>
                    <el-input-number
                      :model-value="stageDimensions[item.key].weight"
                      :min="0"
                      :max="getDimensionMax(item.key)"
                      :step="0.05"
                      :precision="2"
                      :controls="true"
                      :disabled="!canManage || !stageDimensions[item.key].enabled"
                      @update:model-value="(value:number | undefined) => { updateDimensionWeight(item.key, value); selectedPreset = 'custom'; }"
                    />
                  </div>
                </div>
              </div>
              <div v-if="!isDimensionWeightValid" class="persona-tip-inline">启用维度的权重总和必须等于 1.00，系统才允许保存。</div>
            </section>

            <section class="persona-section">
              <div class="persona-section__header">
                <div>
                  <div class="section-title section-title--with-icon">
                    <el-icon><ChatLineRound /></el-icon>
                    <span>策略模板</span>
                  </div>
                  <div class="section-desc">给不同画像准备一条默认建议。</div>
                </div>
                <el-button
                  v-if="canManage"
                  round
                  @click="strategiesEditing = !strategiesEditing"
                >
                  {{ strategiesEditing ? '完成编辑' : '编辑策略' }}
                </el-button>
              </div>
              <div class="strategy-list">
                <div v-for="item in personaOptions" :key="item.value" class="strategy-item">
                  <label>{{ item.label }}</label>
                  <el-input
                    v-if="strategiesEditing && canManage"
                    v-model="strategies[item.value]"
                    placeholder="请输入默认反馈策略"
                    @input="selectedPreset = 'custom'"
                  />
                  <div v-else class="strategy-display">
                    {{ strategies[item.value] || '未设置默认策略' }}
                  </div>
                </div>
              </div>
            </section>
          </div>
        </transition>
      </div>
    </section>

    <section v-if="!showResultsStep && isReadonlyView" class="persona-card persona-readonly">
      <div class="persona-step-header">
        <div>
          <h3 class="persona-title">当前模板摘要</h3>
          <p class="persona-step-header__desc">当前页面只展示平台默认模板，教师实际在课程中查看画像结果并使用这些模板。</p>
        </div>
      </div>
      <div class="persona-readonly__grid">
        <div class="persona-readonly__card">
          <div class="persona-readonly__title">启用维度</div>
          <div class="persona-readonly__value">{{ enabledDimensionCount }} 个</div>
        </div>
        <div class="persona-readonly__card">
          <div class="persona-readonly__title">权重合计</div>
          <div class="persona-readonly__value">{{ enabledDimensionWeightTotal.toFixed(2) }}</div>
        </div>
        <div class="persona-readonly__card">
          <div class="persona-readonly__title">当前方案</div>
          <div class="persona-readonly__value">{{ presetOptions.find((item) => item.key === selectedPreset)?.title || '平衡型' }}</div>
        </div>
      </div>
    </section>

    <section v-if="showResultsStep" class="persona-results-page">
      <div class="results-header">
        <div>
          <div class="results-header__eyebrow">结果查看</div>
          <h3 class="persona-title persona-title--results">画像结果</h3>
        </div>
      </div>

      <div class="results-toolbar">
        <div class="results-toolbar__filters">
          <el-input v-model="resultKeyword" placeholder="搜索账号、姓名、学号、班级或判定摘要" clearable />
          <el-select v-model="resultPersonaFilter" placeholder="全部类型">
            <el-option label="全部类型" value="all" />
            <el-option v-for="item in personaOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="resultRiskFilter" placeholder="全部等级">
            <el-option label="全部等级" value="all" />
            <el-option label="预警" value="预警" />
            <el-option label="风险" value="风险" />
            <el-option label="普通" value="普通" />
          </el-select>
        </div>
        <div class="results-toolbar__actions">
          <el-button @click="loadStudents">刷新</el-button>
          <el-button v-if="canManage" plain>导出结果</el-button>
        </div>
      </div>

      <div class="results-summary">
        <div>共 <strong>{{ students.length }}</strong> 名学生，当前显示 <strong>{{ filteredStudents.length }}</strong> 名</div>
        <div>风险学生 <strong class="results-summary__risk">{{ riskyCount }}</strong> 名</div>
      </div>

      <div class="results-table-card">
      <el-table :data="filteredStudents">
        <el-table-column prop="username" label="账号" min-width="110" />
        <el-table-column prop="full_name" label="姓名" min-width="100" />
        <el-table-column label="当前类型" min-width="130">
          <template #default="{ row }">
            <span class="persona-type-pill" :class="personaToneClass(row.persona_label)">{{ row.persona_label || "未分类" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="动态评分" min-width="100">
          <template #default="{ row }">
            <span class="score-text" :class="scoreToneClass(row.dynamic_score)">{{ scorePercent(row.dynamic_score) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="课程掌握度" min-width="110">
          <template #default="{ row }">
            <span class="score-text" :class="scoreToneClass(row.course_mastery)">{{ scorePercent(row.course_mastery) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="等级" min-width="90">
          <template #default="{ row }">
            <span class="level-pill" :class="levelToneClass(row.risk_level || '普通')">{{ row.risk_level || '普通' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="判定摘要" min-width="280">
          <template #default="{ row }">
            <el-tooltip :content="summarizeReason(row)" placement="top">
              <span class="reason-summary">{{ summarizeReason(row) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column v-if="showStudentDetailAction" label="详情" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" plain class="results-view-btn" @click="emit('view-student', row.user_id)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column v-if="canManage" label="人工覆盖" min-width="220" fixed="right">
          <template #default="{ row }">
            <div class="override-cell">
              <el-select v-model="selectedOverride[row.user_id]" placeholder="选择覆盖类型" clearable>
                <el-option v-for="item in personaOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-button size="small" type="primary" @click="saveOverride(row)">保存</el-button>
              <el-button size="small" @click="clearOverride(row)">恢复</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.persona-shell {
  display: grid;
  gap: 20px;
}

.persona-card {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.18), transparent 42%),
    radial-gradient(circle at bottom left, rgba(187, 247, 208, 0.14), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 18px 36px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.persona-unified-card {
  gap: 24px;
}

.persona-block {
  display: grid;
  gap: 16px;
}

.persona-block__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.persona-block__header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.persona-block__title {
  font-size: 20px;
  font-weight: 800;
  color: #183153;
}

.persona-block__title--with-icon,
.section-title--with-icon {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.persona-block__title--with-icon .el-icon,
.section-title--with-icon .el-icon {
  width: 32px;
  height: 32px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #dff2fb 0%, #fff1df 100%);
  color: #334155;
  font-size: 16px;
  box-shadow: 0 8px 18px rgba(184, 228, 246, 0.16);
}

.persona-block__desc {
  color: #6b86aa;
  font-size: 14px;
  line-height: 1.6;
}

.persona-actions-card {
  padding: 14px 24px;
}

.persona-step-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.persona-title {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: #1f2937;
}

.persona-step-header__desc {
  margin: 8px 0 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.6;
}

.persona-action-group {
  display: flex;
  gap: 10px;
}

.persona-action-group--top {
  justify-content: flex-end;
}

.persona-preset-grid,
.persona-threshold-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.persona-preset-card {
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  animation: personaFadeUp 0.45s ease both;
}

.persona-preset-card:nth-child(2) {
  animation-delay: 0.08s;
}

.persona-preset-card:nth-child(3) {
  animation-delay: 0.16s;
}

.persona-preset-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

.persona-preset-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.persona-preset-card__icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  color: #2563eb;
  font-size: 18px;
  box-shadow: 0 10px 22px rgba(184, 228, 246, 0.18);
}

.persona-preset-card__tag {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.persona-preset-card.is-active {
  border-color: rgba(34, 197, 94, 0.24);
  background: radial-gradient(circle at top left, rgba(187, 247, 208, 0.4), transparent 55%), #ffffff;
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.08);
  transform: translateY(-2px);
}

.persona-preset-card__title {
  font-size: 20px;
  font-weight: 800;
  color: #1f2937;
}

.persona-preset-card__desc {
  margin-top: 8px;
  color: #6b7280;
  line-height: 1.7;
}

.section-title,
.persona-threshold-card__title {
  font-size: 18px;
  font-weight: 800;
  color: #1f2937;
}

.section-desc,
.persona-threshold-card__desc,
.persona-tip-inline {
  margin-top: 6px;
  color: #6b7280;
  line-height: 1.8;
}

.persona-config-wrap__meta,
.persona-threshold-card__badge {
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  min-height: 38px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.persona-collapse-hint {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  padding: 16px 18px;
  border: 1px dashed rgba(31, 41, 55, 0.14);
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.persona-collapse-hint__text {
  display: grid;
  gap: 4px;
}

.persona-collapse-hint__title {
  font-size: 15px;
  font-weight: 800;
  color: #1f2937;
}

.persona-collapse-hint__desc {
  color: #6b7280;
  font-size: 13px;
}

.persona-collapse-toggle-icon {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #dff2fb;
  color: #334155;
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease;
}

.persona-collapse-toggle-icon:hover {
  background: #ebf8ff;
  transform: translateY(-1px);
}

.persona-collapse-hint__arrow {
  transition: transform 0.2s ease;
}

.persona-collapse-hint__arrow.is-expanded {
  transform: rotate(180deg);
}

.persona-grid--two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.persona-section {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.persona-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

.persona-threshold-cards {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.persona-threshold-card {
  display: grid;
  gap: 18px;
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(248,251,255,0.98) 100%);
}

.persona-threshold-card.is-risk { background: linear-gradient(135deg, #fff7f4 0%, #fffdfd 100%); }
.persona-threshold-card.is-smart { background: linear-gradient(135deg, #eef8ff 0%, #ffffff 100%); }
.persona-threshold-card.is-diligent { background: linear-gradient(135deg, #f6fff7 0%, #fcfffd 100%); }
.persona-threshold-card.is-persistent { background: linear-gradient(135deg, #fff9ef 0%, #fffdf9 100%); }

.persona-threshold-card__head,
.persona-section__header,
.dimension-card__head,
.dimension-card__body,
.persona-feedback-card,
.override-cell,
.persona-readonly__grid {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.persona-threshold-card__controls {
  display: grid;
  gap: 14px;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.persona-threshold-card__section-title {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
}

.persona-threshold-card__fields,
.strategy-list,
.dimension-grid,
.persona-readonly__grid {
  display: grid;
  gap: 14px;
}

.persona-threshold-field {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 16px;
  align-items: center;
}

.persona-threshold-stepper {
  padding: 6px;
  border-radius: 18px;
  background: linear-gradient(90deg, rgba(96, 165, 250, 0.18) var(--fill), rgba(248, 251, 255, 0.96) var(--fill));
}

.dimension-summary {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  border-radius: 16px;
  background: #dff2fb;
  color: #334155;
  font-size: 13px;
  font-weight: 700;
}

.dimension-summary.is-error {
  background: #fff4f1;
  color: #bf5f43;
}

.dimension-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dimension-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.dimension-card__title,
.strategy-item label,
.persona-threshold-field span,
.dimension-card__body span,
.persona-readonly__title {
  font-weight: 700;
  color: #334155;
}

.strategy-item {
  display: grid;
  gap: 8px;
}

.strategy-item :deep(.el-input) {
  width: 100%;
}

.strategy-item :deep(.el-input__wrapper) {
  min-height: 42px;
  padding: 0 14px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.2) inset !important;
}

.strategy-item :deep(.el-input__inner) {
  color: #6b7280;
}

.strategy-display {
  width: 100%;
  box-sizing: border-box;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #6b7280;
  display: flex;
  align-items: center;
  line-height: 1;
}

.persona-expand-enter-active,
.persona-expand-leave-active {
  overflow: hidden;
  transition:
    max-height 0.28s ease,
    opacity 0.24s ease,
    transform 0.24s ease;
  transform-origin: top center;
}

.persona-expand-enter-from,
.persona-expand-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-8px) scaleY(0.98);
}

.persona-expand-enter-to,
.persona-expand-leave-from {
  max-height: 1600px;
  opacity: 1;
  transform: translateY(0) scaleY(1);
}

@keyframes personaFadeUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.persona-readonly__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.persona-readonly__card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.persona-readonly__value {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 800;
  color: #1f2937;
}

.persona-result-toolbar {
  display: grid;
  grid-template-columns: 1.4fr 220px 220px;
  gap: 12px;
}

.persona-feedback-card {
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #6b7280;
  font-size: 13px;
  font-weight: 700;
}

.override-cell {
  align-items: stretch;
}

.override-cell .el-select {
  min-width: 120px;
}

.persona-results-page {
  display: grid;
  gap: 16px;
  padding: 20px 22px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.18), transparent 42%),
    radial-gradient(circle at bottom left, rgba(187, 247, 208, 0.14), transparent 24%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow:
    0 18px 36px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.results-header,
.results-toolbar,
.results-toolbar__filters,
.results-toolbar__actions,
.results-summary {
  display: flex;
  align-items: center;
}

.results-header,
.results-toolbar,
.results-summary {
  justify-content: space-between;
  gap: 16px;
}

.results-header__eyebrow {
  font-size: 12px;
  font-weight: 700;
  color: #8a6740;
}

.persona-title--results {
  font-size: 28px;
  color: #0f172a;
}

.results-header__actions,
.results-toolbar__actions,
.results-toolbar__filters {
  gap: 12px;
}

.results-toolbar {
  padding: 0;
}

.results-toolbar__filters {
  flex: 1 1 auto;
}

.results-toolbar__filters > *:first-child {
  flex: 1 1 460px;
}

.results-toolbar__filters :deep(.el-select),
.results-toolbar__actions :deep(.el-button),
.results-header__actions :deep(.el-button),
.results-toolbar__filters :deep(.el-input) {
  min-height: 40px;
}

.results-summary {
  padding: 6px 2px 0;
  color: #64748b;
  font-size: 14px;
}

.results-summary strong {
  color: #0f172a;
}

.results-summary__risk {
  color: #ef4444 !important;
}

.results-table-card {
  border: 1.5px solid rgba(31, 41, 55, 0.14);
  border-radius: 22px;
  overflow: hidden;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.persona-type-pill,
.level-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}

.persona-type-pill.is-steady {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #475569;
}

.persona-type-pill.is-warning {
  background: #fff7ed;
  border-color: #fed7aa;
  color: #c2410c;
}

.persona-type-pill.is-danger {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}

.level-pill.is-warning {
  background: #fefce8;
  border-color: #fde68a;
  color: #a16207;
}

.level-pill.is-risk {
  background: #fff7ed;
  border-color: #fdba74;
  color: #c2410c;
}

.level-pill.is-stable {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #15803d;
}

.score-text {
  font-weight: 700;
}

.score-text.is-good {
  color: #16a34a;
}

.score-text.is-mid {
  color: #d97706;
}

.score-text.is-bad {
  color: #dc2626;
}

.reason-summary {
  display: inline-block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #475569;
}

.results-view-btn {
  border-radius: 10px;
  border-color: rgba(31, 41, 55, 0.14);
  color: #16a34a;
  background: #ffffff;
}

.results-view-btn:hover {
  background: #f2fbe5;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 16px;
}

:deep(.el-input-number) {
  width: 190px;
}

:deep(.el-input-number .el-input__wrapper) {
  border-radius: 16px;
}

.persona-results-page :deep(.el-input__wrapper),
.persona-results-page :deep(.el-select__wrapper) {
  min-height: 40px;
  border-radius: 10px;
}

.persona-results-page :deep(.el-table) {
  --el-table-border-color: #e5e7eb;
  --el-table-header-bg-color: #f8fafc;
  --el-table-row-hover-bg-color: #fff7ef;
}

.persona-results-page :deep(.el-table th.el-table__cell) {
  color: #64748b;
  font-weight: 700;
}

.persona-results-page :deep(.el-table td.el-table__cell) {
  color: #0f172a;
}

@media (max-width: 1200px) {
  .persona-preset-grid,
  .persona-grid--two,
  .persona-threshold-cards,
  .dimension-grid,
  .persona-readonly__grid,
  .persona-result-toolbar {
    grid-template-columns: 1fr;
  }

  .results-toolbar,
  .results-header,
  .results-summary {
    flex-direction: column;
    align-items: stretch;
  }

  .results-toolbar__filters {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .persona-card {
    padding: 18px;
  }

  .persona-step-header,
  .persona-block__header,
  .persona-block__header-actions,
  .persona-action-group,
  .persona-threshold-card__head,
  .dimension-summary,
  .persona-feedback-card {
    flex-direction: column;
    align-items: stretch;
  }

  .persona-threshold-field {
    grid-template-columns: 1fr;
  }
}
</style>
