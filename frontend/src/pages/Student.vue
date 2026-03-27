<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import { getRole, getUsername } from "../token";
import HoverTip from "../components/HoverTip.vue";
import HintButton from "../components/HintButton.vue";

import OverviewPane from "../components/OverviewPane.vue";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";

type KP = {
  id: number;
  code: string;
  title: string;
  description: string;
  subject: string;
  grade: string;
  chapter?: string;
};

type Course = { id: number; code: string; title: string };

type RecoData = {
  target_kp: { id: number; code: string; title: string; mastery?: number };
  reason_summary: string;
  recommendation_stage?: string;
  recommendation_stage_label?: string;
  resource_list: Array<Record<string, any>>;
  practice_list: Array<Record<string, any>>;
  advice_text: string;
  persona_strategy_tag: string;
  persona_label: string;
  dynamic_score: number;
  risk_level: string;
  diagnosis?: { mastery?: number; status?: string; reason_summary?: string };
  evidence?: { items?: Record<string, boolean>; missing?: string[]; score?: number };
  remedy?: { action?: string; persona?: string; reason_summary?: string };
  remedy_path?: { blocked_prereqs?: number[]; path?: number[] };
  unlock?: { can_unlock_next: boolean; next_candidates: number[] };
};

type ProfileSummary = {
  persona_label?: string;
  dynamic_score?: number;
  risk_level?: string;
  course_mastery?: number;
  reason_summary?: string;
  kp_dimension_summary?: {
    summary?: {
      knowledge_total?: number;
      knowledge_achieved?: number;
      ability_target_total?: number;
      ability_achieved?: number;
      literacy_target_total?: number;
      literacy_achieved?: number;
      top_abilities?: Array<{ label: string; achieved_count: number; target_count: number }>;
      top_literacies?: Array<{ label: string; achieved_count: number; target_count: number }>;
    };
  };
  current_stage?: {
    stage_title?: string;
    trend_label?: string;
    stage_order?: number;
  } | null;
};

const courses = ref<Course[]>([]);
const subject = ref<string>("");
const grade = ref<string>("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);

const mastery = ref<number>(0);
const profile = ref<ProfileSummary | null>(null);
const reco = ref<RecoData | null>(null);
const reportReloadKey = ref(0);
const isStudent = computed(() => getRole() === "student");
const route = useRoute();
const router = useRouter();
const selectedCourseId = computed<number | null>(() => {
  const current = courses.value.find((item) => item.title === subject.value);
  return current?.id ?? null;
});

const currentKp = computed(() => kps.value.find((k) => k.id === currentKpId.value) ?? null);
const recommendedTargetId = computed<number | null>(() => reco.value?.target_kp?.id ?? null);
const recommendedTarget = computed<KP | null>(() => {
  if (!recommendedTargetId.value) return null;
  return kps.value.find((item) => item.id === recommendedTargetId.value) ?? null;
});
const recommendationStageLabel = computed(() => reco.value?.recommendation_stage_label || "当前推荐");
const masteryStageLabel = computed(() => {
  if (mastery.value >= 0.85) return "已掌握";
  if (mastery.value >= 0.5) return "学习中";
  if (mastery.value > 0) return "待巩固";
  return "未开始";
});
const tripleSummary = computed(() => profile.value?.kp_dimension_summary?.summary ?? null);

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
    const endpoint = isStudent.value ? "/graph/available-courses" : "/graph/courses";
    const data = await api.get(endpoint);
    courses.value = (data.data ?? []).map((item: any) => ({
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
    }));
    if (!subject.value && courses.value.length) subject.value = courses.value[0].title;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

async function loadStudentCourses() {
  try {
    await loadCourses();
  } catch {
    // actual errors handled in child loaders
  }
}

async function loadKps() {
  if (!subject.value) return;
  try {
    const data = await getWithCache("/graph/kps", {
      subject: subject.value,
      grade: grade.value,
    });
    kps.value = data ?? [];
    const saved = localStorage.getItem(kpStorageKey());
    if (saved) {
      const savedId = Number(saved);
      const exists = kps.value.some((k) => k.id === savedId);
      if (exists) {
        currentKpId.value = savedId;
      }
    }
    if (!currentKpId.value && kps.value.length) currentKpId.value = kps.value[0].id;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
  }
}

async function refreshMastery() {
  if (!currentKpId.value) return;
  try {
    const res = await api.get(`/eval/mastery?kp_id=${currentKpId.value}`);
    mastery.value = Number(res.data.value ?? 0);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "刷新掌握度失败");
  }
}

async function getReco() {
  if (!currentKpId.value) return;
  try {
    const res = await api.get(`/reco?kp_id=${currentKpId.value}`);
    reco.value = res.data;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "获取推荐失败");
  }
}

async function goToRecommended() {
  if (!recommendedTargetId.value) return;
  currentKpId.value = recommendedTargetId.value;
  localStorage.setItem(kpStorageKey(), String(recommendedTargetId.value));
  await refreshMastery();
  router.push({
    path: "/student/graph-workspace",
    query: studentQuery({
      subject: subject.value,
      kp: String(recommendedTargetId.value),
    }),
  });
}

function resetReco() {
  reco.value = null;
}

async function loadProfile() {
  if (!subject.value) return;
  try {
    const res = await api.get(
      `/eval/profile?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`
    );
    profile.value = res.data ?? null;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载画像失败");
  }
}

async function onCourseChange() {
  currentKpId.value = null;
  reco.value = null;
  await loadKps();
  await refreshMastery();
  await loadProfile();
}

async function onKpChange() {
  if (currentKpId.value) localStorage.setItem(kpStorageKey(), String(currentKpId.value));
  reco.value = null;
  await refreshMastery();
  await loadProfile();
}

function openGraphWorkspace() {
  const preview = String(route.query.preview || "");
  router.push({
    path: "/student/graph-workspace",
    query: {
      subject: subject.value,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
      preview: preview || undefined,
    },
  });
}

function handleGuideAction(key: string) {
  if (key === "graph-workspace") {
    openGraphWorkspace();
    return;
  }
  if (key === "overview") {
    router.push({ path: "/student/overview", query: studentQuery() });
    return;
  }
  if (key === "questionnaire") {
    router.push({ path: "/student/questionnaire", query: studentQuery({ subject: subject.value || undefined }) });
    return;
  }
  if (key === "report") {
    router.push({ path: "/student/report", query: studentQuery({ subject: subject.value || undefined }) });
    return;
  }
  if (key === "recommended") {
    goToRecommended();
  }
}

function handleQuestionnaireSaved() {
  reportReloadKey.value += 1;
}

onMounted(async () => {
  try {
    await loadStudentCourses();
    await loadKps();
    await refreshMastery();
    await loadProfile();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载失败（请先在管理端准备课程与知识点数据）");
  }
});
</script>

<template>
  <div class="edu-page one-screen" v-loading="!courses.length && isStudent">
    <template v-if="isStudent">
      <header class="edu-header compact">
        <div class="edu-header__left">
          <h1 class="edu-header__title">学习中心</h1>
          <p class="edu-header__desc">欢迎回来！今天想学习哪门课程？</p>
        </div>
        <div class="edu-header__actions">
          <el-tag round type="info" style="margin-right: 12px">
            {{ profile?.persona_label || "画像生成中" }}
          </el-tag>
          <el-select v-model="subject" placeholder="切换课程" @change="onCourseChange" style="width: 180px">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
          </el-select>
        </div>
      </header>

      <section class="edu-stats-grid compact">
        <div class="edu-stat-card">
          <span class="edu-stat-card__label">动态评分</span>
          <strong class="edu-stat-card__value">{{ Math.round((profile?.dynamic_score || 0) * 100) }}%</strong>
        </div>
        <div class="edu-stat-card">
          <span class="edu-stat-card__label">知识达成</span>
          <strong class="edu-stat-card__value">
            {{ tripleSummary ? `${tripleSummary.knowledge_achieved ?? 0}/${tripleSummary.knowledge_total ?? 0}` : "—" }}
          </strong>
        </div>
        <div class="edu-stat-card">
          <span class="edu-stat-card__label">能力达成</span>
          <strong class="edu-stat-card__value">
            {{ tripleSummary ? `${tripleSummary.ability_achieved ?? 0}/${tripleSummary.ability_target_total ?? 0}` : "—" }}
          </strong>
        </div>
        <div class="edu-stat-card">
          <span class="edu-stat-card__label">素养达成</span>
          <strong class="edu-stat-card__value">
            {{ tripleSummary ? `${tripleSummary.literacy_achieved ?? 0}/${tripleSummary.literacy_target_total ?? 0}` : "—" }}
          </strong>
        </div>
      </section>

      <div class="main-layout-content">
        <div class="edu-grid-3">
          <section class="edu-panel student-main-panel">
            <header class="edu-panel__header">
              <h2 class="edu-panel__title">快速开始</h2>
            </header>
            <div class="quick-actions">
              <button class="action-card primary" @click="openGraphWorkspace" :disabled="!currentKpId">
                <div class="action-icon">🗺️</div>
                <div class="action-text">
                  <strong>打开图谱</strong>
                  <span>查看知识关联，开始探索</span>
                </div>
              </button>
              <button class="action-card" @click="router.push({ path: '/student/report', query: studentQuery({ subject: subject || undefined }) })">
                <div class="action-icon">📊</div>
                <div class="action-text">
                  <strong>学习报告</strong>
                  <span>查看进度与能力画像</span>
                </div>
              </button>
              <button class="action-card" @click="router.push({ path: '/student/questionnaire', query: studentQuery({ subject: subject || undefined }) })">
                <div class="action-icon">📝</div>
                <div class="action-text">
                  <strong>填写问卷</strong>
                  <span>提供反馈，优化推荐</span>
                </div>
              </button>
            </div>
          </section>

          <section class="edu-panel student-kp-panel">
            <header class="edu-panel__header">
              <h2 class="edu-panel__title">当前知识点</h2>
            </header>
            <div v-if="currentKp" class="kp-content">
              <div class="kp-header">
                <span class="kp-code">{{ currentKp.code }}</span>
                <h3 class="kp-title">{{ currentKp.title }}</h3>
              </div>
              <p class="kp-desc">{{ currentKp.description || '暂无详细描述' }}</p>
              <div class="kp-progress-box">
                <div class="progress-label">当前掌握度</div>
                <el-progress :percentage="Math.round(mastery * 100)" :stroke-width="12" />
              </div>
              <el-select v-model="currentKpId" @change="onKpChange" placeholder="切换知识点" class="kp-selector">
                <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
              </el-select>
            </div>
            <el-empty v-else description="请先选择一个知识点" />
          </section>

          <section class="edu-panel student-reco-panel">
            <header class="edu-panel__header">
              <h2 class="edu-panel__title">智能建议</h2>
              <el-button link type="primary" @click="getReco" :disabled="!currentKpId">刷新</el-button>
            </header>
            <div v-if="reco" class="reco-content">
              <div class="reco-highlight">
                <div class="reco-tag">下一步建议</div>
                <h3 class="reco-title">{{ reco.target_kp.title }}</h3>
                <p class="reco-reason">{{ reco.reason_summary }}</p>
              </div>
              <div class="reco-footer">
                <el-button type="primary" style="width: 100%" @click="goToRecommended">去学习</el-button>
              </div>
            </div>
            <div v-else class="reco-empty">
              <p>点击“刷新”获取智能推荐</p>
            </div>
          </section>
        </div>

        <section class="edu-panel overview-section">
          <header class="edu-panel__header">
            <h2 class="edu-panel__title">课程概览</h2>
          </header>
          <div class="scroll-area-internal">
            <OverviewPane :subject="subject" :grade="grade" />
          </div>
        </section>
      </div>
    </template>

    <section v-else class="edu-panel preview-mode">
      <header class="edu-panel__header">
        <h2 class="edu-panel__title">预览模式</h2>
      </header>
      <div class="preview-controls">
        <el-select v-model="subject" placeholder="选择课程" @change="onCourseChange">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
        </el-select>
        <el-select v-model="currentKpId" placeholder="选择知识点" @change="onKpChange">
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
        </el-select>
      </div>
      <p class="preview-tip">您当前正在以教师/管理员身份预览学生端界面。请从图谱工作区进入具体内容学习。</p>
    </section>
  </div>
</template>

<style scoped>
.one-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.edu-header.compact {
  margin-bottom: 16px;
  padding: 16px 24px;
}

.edu-stats-grid.compact {
  margin-bottom: 16px;
  gap: 16px;
}

.edu-stat-card {
  padding: 16px;
}

.edu-stat-card__value {
  font-size: 28px;
}

.main-layout-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.edu-grid-3 {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.edu-panel {
  padding: 20px;
}

.overview-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.scroll-area-internal {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.quick-actions {
  display: grid;
  gap: 8px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--app-border);
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.action-card:hover:not(:disabled) {
  border-color: var(--app-primary);
  background: var(--app-bg);
  transform: translateX(4px);
}

.action-card.primary {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #bfdbfe;
}

.action-icon {
  font-size: 20px;
}

.action-text strong {
  font-size: 14px;
}

.action-text span {
  font-size: 11px;
}

.kp-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kp-title {
  font-size: 16px;
  margin: 0;
}

.kp-desc {
  font-size: 12px;
  line-height: 1.4;
  height: 2.8em;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.kp-progress-box {
  padding: 12px;
  background: var(--app-bg);
  border-radius: 10px;
}

.reco-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reco-highlight {
  padding: 16px;
}

.reco-title {
  font-size: 16px;
}

.reco-reason {
  font-size: 12px;
}

.reco-empty {
  height: 140px;
}

@media (max-height: 800px) {
  .edu-header__title { font-size: 20px; }
  .edu-header__desc { display: none; }
  .edu-stat-card__value { font-size: 22px; }
  .action-card { padding: 8px; }
  .kp-desc { display: none; }
}
</style>
