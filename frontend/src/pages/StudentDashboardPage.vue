<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import { getRole, getUsername } from "../token";
import { resolveStudentSubject, saveStudentSubject } from "../utils/studentCourse";

type KP = {
  id: number;
  code: string;
  title: string;
  description: string;
};

type Course = { id: number; code: string; title: string };

type RecoData = {
  target_kp: { id: number; code: string; title: string };
  reason_summary: string;
  recommendation_stage_label?: string;
};

type PersonaSignal = { key: string; label: string; detail: string; level: string };
type DynamicBreakdown = {
  engagement_score?: number;
  achievement_score?: number;
  efficiency_score?: number;
  risk_score?: number;
};
type ProfileSummary = {
  persona_label?: string;
  persona_intro?: string;
  persona_signals?: PersonaSignal[];
  dynamic_score?: number;
  risk_level?: string;
  reason_summary?: string;
  dynamic_breakdown?: DynamicBreakdown | null;
  kp_dimension_summary?: {
    summary?: {
      knowledge_total?: number;
      knowledge_achieved?: number;
      ability_target_total?: number;
      ability_achieved?: number;
      literacy_target_total?: number;
      literacy_achieved?: number;
    };
  };
  current_stage?: {
    stage_title?: string;
    trend_label?: string;
  } | null;
};

const route = useRoute();
const router = useRouter();

const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);
const mastery = ref(0);
const profile = ref<ProfileSummary | null>(null);
const reco = ref<RecoData | null>(null);
const isStudent = computed(() => getRole() === "student");

watch(
  [subject, isStudent],
  () => {
    if (isStudent.value && subject.value) {
      saveStudentSubject(subject.value);
    }
  },
  { immediate: true }
);

const currentKp = computed(() => kps.value.find((item) => item.id === currentKpId.value) ?? null);
const recommendedTarget = computed(() => {
  const id = reco.value?.target_kp?.id;
  return id ? kps.value.find((item) => item.id === id) ?? null : null;
});
const masteryStageLabel = computed(() => {
  if (mastery.value >= 0.85) return "已掌握";
  if (mastery.value >= 0.5) return "学习中";
  if (mastery.value > 0) return "待巩固";
  return "未开始";
});
const tripleSummary = computed(() => profile.value?.kp_dimension_summary?.summary ?? null);
const personaSignals = computed(() => profile.value?.persona_signals ?? []);
const breakdownMini = computed(() => {
  const b = profile.value?.dynamic_breakdown;
  if (!b) return [];
  return [
    { label: "投入", value: Number(b.engagement_score ?? 0) },
    { label: "成效", value: Number(b.achievement_score ?? 0) },
    { label: "效率", value: Number(b.efficiency_score ?? 0) },
    { label: "风险", value: Number(b.risk_score ?? 0) },
  ];
});
const currentStageSummary = computed(() => {
  const stage = profile.value?.current_stage;
  if (!stage?.stage_title) return "当前暂无阶段信息";
  return `${stage.stage_title}${stage.trend_label ? ` · ${stage.trend_label}` : ""}`;
});
const dashboardStats = computed(() => [
  { label: "动态评分", value: `${Math.round((profile.value?.dynamic_score || 0) * 100)}%` },
  { label: "风险提醒", value: profile.value?.risk_level || "正常" },
  { label: "当前状态", value: masteryStageLabel.value },
  {
    label: "知识达成",
    value: tripleSummary.value
      ? `${tripleSummary.value.knowledge_achieved ?? 0}/${tripleSummary.value.knowledge_total ?? 0}`
      : "--",
  },
]);

function kpStorageKey() {
  const username = getUsername() || localStorage.getItem("da_last_user") || "guest";
  return `da_kp_${username}_${subject.value}`;
}

function studentQuery(extra: Record<string, string | undefined> = {}) {
  const preview = String(route.query.preview || "");
  return {
    ...(preview === "1" ? { preview: "1" } : {}),
    ...extra,
  };
}

async function loadCourses() {
  try {
    const endpoint = "/graph/courses";
    const data = await api.get(endpoint);
    courses.value = (data.data ?? []).map((item: any) => ({
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
    }));
    subject.value = resolveStudentSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

async function loadKps() {
  if (!subject.value) {
    kps.value = [];
    currentKpId.value = null;
    return;
  }
  try {
    const data = await getWithCache("/graph/kps", { subject: subject.value, grade: grade.value });
    kps.value = data ?? [];
    const saved = Number(localStorage.getItem(kpStorageKey()) || 0);
    if (saved && kps.value.some((item) => item.id === saved)) {
      currentKpId.value = saved;
    }
    if (!currentKpId.value && kps.value.length) currentKpId.value = kps.value[0].id;
  } catch (e: any) {
    kps.value = [];
    currentKpId.value = null;
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
  }
}

async function refreshMastery() {
  if (!currentKpId.value) return;
  try {
    const res = await api.get(`/eval/mastery?kp_id=${currentKpId.value}`);
    mastery.value = Number(res.data.value ?? 0);
  } catch (e: any) {
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "刷新掌握度失败");
  }
}

async function loadProfile() {
  if (!subject.value) return;
  try {
    const res = await api.get(
      `/eval/profile?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`
    );
    profile.value = res.data ?? null;
  } catch (e: any) {
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载画像失败");
  }
}

async function loadReco() {
  if (!currentKpId.value) {
    reco.value = null;
    return;
  }
  try {
    const res = await api.get(`/reco?kp_id=${currentKpId.value}`);
    reco.value = res.data ?? null;
  } catch (e: any) {
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.detail ?? "获取推荐失败");
    }
  }
}

async function onCourseChange() {
  currentKpId.value = null;
  reco.value = null;
  await loadKps();
  await refreshMastery();
  await loadProfile();
  await loadReco();
}

async function onKpChange() {
  if (currentKpId.value) localStorage.setItem(kpStorageKey(), String(currentKpId.value));
  await refreshMastery();
  await loadProfile();
  await loadReco();
}

function openCurrentLearning(targetId?: number | null) {
  const kpId = targetId ?? currentKpId.value;
  if (!kpId) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  router.push({
    path: `/student/kp-content/${kpId}`,
    query: studentQuery({
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      from: "student-dashboard",
    }),
  });
}

onMounted(async () => {
  try {
    await loadCourses();
    await loadKps();
    await refreshMastery();
    await loadProfile();
    await loadReco();
  } catch (e: any) {
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载失败，请先准备课程和知识点数据");
  }
});
</script>

<template>
  <div class="edu-page student-dashboard" v-loading="!courses.length && isStudent">
    <template v-if="isStudent">
      <section class="student-dashboard__hero">
        <div class="student-dashboard__hero-main">
          <div class="student-dashboard__hero-copy">
            <h2>{{ currentKp ? currentKp.title : subject || "" }}</h2>
            <p>{{ currentStageSummary }}</p>
          </div>
          <div class="student-dashboard__hero-actions">
            <el-select v-model="subject" placeholder="切换课程" @change="onCourseChange" style="width: 220px">
              <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
            </el-select>
          </div>
        </div>

        <div class="student-dashboard__stats">
          <article v-for="item in dashboardStats" :key="item.label" class="student-dashboard__stat-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </div>
      </section>

      <section class="student-dashboard__main-grid">
        <section class="edu-panel student-dashboard__panel">
          <header class="edu-panel__header student-dashboard__panel-header">
            <div>
              <h2 class="edu-panel__title">当前知识点</h2>
              <p class="student-dashboard__panel-note">先看当前学习点，再决定是否切换到推荐内容。</p>
            </div>
            <el-tag round type="info">{{ profile?.persona_label || "学习中" }}</el-tag>
          </header>

          <div v-if="currentKp" class="student-dashboard__kp-card">
            <div class="student-dashboard__kp-top">
              <span class="student-dashboard__kp-code">{{ currentKp.code }}</span>
              <el-tag size="small" effect="plain">{{ masteryStageLabel }}</el-tag>
            </div>
            <h3>{{ currentKp.title }}</h3>
            <p>{{ currentKp.description || "" }}</p>
            <div class="student-dashboard__progress-box">
              <div class="student-dashboard__progress-head">
                <span>当前掌握度</span>
                <strong>{{ Math.round(mastery * 100) }}%</strong>
              </div>
              <el-progress :percentage="Math.round(mastery * 100)" :stroke-width="10" />
            </div>
            <el-select v-model="currentKpId" @change="onKpChange" placeholder="切换知识点">
              <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
            </el-select>
          </div>
          <el-empty v-else description="当前课程暂时没有可学习的知识点" />
        </section>
      </section>

      <section class="student-dashboard__actions-grid">
        <button class="student-dashboard__action-card" type="button" @click="openCurrentLearning()">
          <span>继续学习</span>
          <strong>{{ currentKp ? currentKp.title : "进入当前知识点" }}</strong>
        </button>
        <button class="student-dashboard__action-card" type="button" @click="openCurrentLearning(recommendedTarget?.id || null)">
          <span>推荐入口</span>
          <strong>{{ recommendedTarget ? recommendedTarget.title : "暂时没有推荐知识点" }}</strong>
        </button>
      </section>

      <section class="student-dashboard__quick-grid">
        <article class="student-dashboard__quick-card">
          <span>能力摘要</span>
          <strong>
            {{ tripleSummary ? `${tripleSummary.ability_achieved ?? 0}/${tripleSummary.ability_target_total ?? 0}` : "--" }}
          </strong>
        </article>
        <article class="student-dashboard__quick-card">
          <span>素养摘要</span>
          <strong>
            {{ tripleSummary ? `${tripleSummary.literacy_achieved ?? 0}/${tripleSummary.literacy_target_total ?? 0}` : "--" }}
          </strong>
        </article>
        <article class="student-dashboard__quick-card">
          <span>关键信号</span>
          <strong>{{ personaSignals.length }}</strong>
        </article>
        <article class="student-dashboard__quick-card">
          <span>分项评分</span>
          <strong>{{ breakdownMini.length ? `${Math.round((profile?.dynamic_score || 0) * 100)}%` : "--" }}</strong>
        </article>
      </section>
    </template>

    <section v-else class="edu-panel preview-mode">
      <div class="preview-mode__hero">
        <div class="preview-mode__copy">
          <span class="preview-mode__eyebrow">学生端预览</span>
          <h2 class="edu-panel__title">先选课程，再定位知识点</h2>
          <p>用于管理员快速查看学生端学习内容与页面状态，不影响真实学生操作。</p>
        </div>

        <div class="preview-mode__summary">
          <article class="preview-mode__summary-card">
            <span>当前课程</span>
            <strong>{{ subject || "未选择" }}</strong>
          </article>
          <article class="preview-mode__summary-card">
            <span>知识点数量</span>
            <strong>{{ kps.length }}</strong>
          </article>
          <article class="preview-mode__summary-card">
            <span>当前知识点</span>
            <strong>{{ currentKp ? currentKp.title : "未选择" }}</strong>
            <small v-if="currentKp">{{ currentKp.code }}</small>
          </article>
        </div>
      </div>

      <div class="preview-mode__selectors">
        <div class="preview-mode__field">
          <label class="preview-mode__label">预览课程</label>
          <el-select v-model="subject" placeholder="请选择课程" @change="onCourseChange">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
          </el-select>
        </div>
        <div class="preview-mode__field">
          <label class="preview-mode__label">预览知识点</label>
          <el-select v-model="currentKpId" placeholder="请选择知识点" @change="onKpChange">
            <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
          </el-select>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.student-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.student-dashboard__hero {
  display: grid;
  gap: 16px;
  padding: 24px;
  border-radius: var(--app-radius-lg);
  border: 1px solid color-mix(in srgb, var(--app-primary) 18%, var(--app-border));
  background: linear-gradient(135deg, #eef4ff 0%, #f5fbf7 52%, #ffffff 100%);
  box-shadow: var(--app-shadow-soft);
}

.student-dashboard__hero-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.student-dashboard__hero-copy {
  display: grid;
  gap: 8px;
  max-width: 60ch;
}

.student-dashboard__hero-copy h2 {
  margin: 0;
  font-size: clamp(24px, 4vw, 34px);
  line-height: 1.15;
  color: var(--app-text-main);
}

.student-dashboard__hero-copy p {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--app-text-soft);
}

.student-dashboard__hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.student-dashboard__stats,
.student-dashboard__quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.student-dashboard__stat-card,
.student-dashboard__quick-card {
  display: grid;
  gap: 8px;
  padding: 16px 18px;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.88);
}

.student-dashboard__stat-card span,
.student-dashboard__quick-card span {
  font-size: 12px;
  color: var(--app-text-soft);
}

.student-dashboard__stat-card strong,
.student-dashboard__quick-card strong {
  font-size: 24px;
  line-height: 1.1;
  color: var(--app-text-main);
}

.student-dashboard__main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.student-dashboard__panel {
  padding: 20px;
}

.student-dashboard__panel-header {
  align-items: flex-start;
}

.student-dashboard__panel-note {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--app-text-soft);
}

.student-dashboard__kp-card {
  display: grid;
  gap: 14px;
}

.student-dashboard__kp-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.student-dashboard__kp-code {
  display: inline-flex;
  width: fit-content;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.student-dashboard__kp-code {
  background: var(--app-primary-soft);
  color: var(--app-primary-deep);
}

.student-dashboard__kp-card h3 {
  margin: 0;
  font-size: 20px;
  color: var(--app-text-main);
}

.student-dashboard__kp-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--app-text-soft);
}

.student-dashboard__actions-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.student-dashboard__action-card {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  text-align: left;
  border-radius: 20px;
  border: 1px solid color-mix(in srgb, var(--app-primary) 18%, var(--app-border));
  background: linear-gradient(135deg, #f3f8ff 0%, #ffffff 100%);
  color: inherit;
  cursor: pointer;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}

.student-dashboard__action-card span {
  font-size: 12px;
  color: var(--app-text-soft);
}

.student-dashboard__action-card strong {
  font-size: 16px;
  line-height: 1.35;
  color: var(--app-text-main);
}

.student-dashboard__action-card:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--app-primary) 32%, var(--app-border));
  box-shadow: 0 14px 26px rgba(79, 140, 255, 0.12);
}

.student-dashboard__progress-box {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: var(--app-radius-sm);
  background: var(--app-surface-muted);
}

.student-dashboard__progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.student-dashboard__progress-head span {
  font-size: 12px;
  color: var(--app-text-soft);
}

.student-dashboard__progress-head strong {
  font-size: 14px;
  color: var(--app-text-main);
}

.preview-mode {
  display: grid;
  gap: 18px;
  padding: 28px;
  border-radius: 28px;
  border: 1px solid #d9e6f7;
  background:
    radial-gradient(circle at top right, rgba(79, 140, 255, 0.12), transparent 28%),
    linear-gradient(135deg, #f2f7ff 0%, #f8fbff 52%, #ffffff 100%);
  box-shadow: 0 20px 42px rgba(24, 51, 92, 0.08);
}

.preview-mode__hero {
  display: grid;
  gap: 18px;
}

.preview-mode__copy {
  display: grid;
  gap: 8px;
}

.preview-mode__eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.1);
  color: #3566b8;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.preview-mode__copy p {
  margin: 0;
  max-width: 62ch;
  color: var(--app-text-soft);
  line-height: 1.7;
}

.preview-mode__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.preview-mode__summary-card {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 20px;
  border: 1px solid #dce7f5;
  background: rgba(255, 255, 255, 0.88);
}

.preview-mode__summary-card span,
.preview-mode__summary-card small {
  color: var(--app-text-soft);
  font-size: 12px;
}

.preview-mode__summary-card strong {
  color: var(--app-text-main);
  font-size: 20px;
  line-height: 1.3;
}

.preview-mode__selectors {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid #dce7f5;
  background: rgba(255, 255, 255, 0.78);
}

.preview-mode__field {
  display: grid;
  gap: 10px;
}

.preview-mode__label {
  font-size: 13px;
  font-weight: 700;
  color: #4c6488;
}

.preview-mode__field :deep(.el-select) {
  width: 100%;
}

.preview-mode__field :deep(.el-input__wrapper) {
  min-height: 46px;
  border-radius: 16px;
  box-shadow: 0 0 0 1px #d6e3f5 inset !important;
}

@media (max-width: 1100px) {
  .student-dashboard__stats,
  .student-dashboard__main-grid,
  .student-dashboard__actions-grid,
  .student-dashboard__quick-grid,
  .preview-mode__summary,
  .preview-mode__selectors {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .student-dashboard__hero {
    padding: 18px;
  }

  .preview-mode {
    padding: 20px;
  }
}
</style>
