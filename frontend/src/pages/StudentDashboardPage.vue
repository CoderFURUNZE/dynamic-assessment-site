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

type Course = {
  id: number;
  code: string;
  title: string;
  active?: boolean;
  enroll_status?: string;
  completed?: boolean;
  learning_available?: boolean;
};

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
const isPreview = computed(() => String(route.query.preview || "") === "1");
const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);

watch(
  [subject, isStudent],
  () => {
    if (isStudent.value && subject.value) saveStudentSubject(subject.value);
  },
  { immediate: true },
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
const dashboardLead = computed(() => {
  if (profile.value?.reason_summary) return profile.value.reason_summary;
  if (reco.value?.reason_summary) return reco.value.reason_summary;
  return "先完成当前知识点的学习，再根据推荐调整下一步的学习重点。";
});
const dashboardTaskTitle = computed(() => currentKp.value?.title || "当前暂无学习任务");
const dashboardTaskCode = computed(() => currentKp.value?.code || "未选择知识点");
const dashboardTaskSummary = computed(
  () => currentKp.value?.description || "当前课程下还没有可展示的知识点说明。",
);
const knowledgeAchievement = computed(() =>
  tripleSummary.value
    ? `${tripleSummary.value.knowledge_achieved ?? 0}/${tripleSummary.value.knowledge_total ?? 0}`
    : "--",
);
const nextActionText = computed(() => {
  if (recommendedTarget.value) return `下一步建议：${recommendedTarget.value.title}`;
  if (currentKp.value) return `继续完成 ${currentKp.value.title}`;
  return "先选择课程并进入知识点学习";
});
const dashboardStats = computed(() => [
  {
    label: "动态评分",
    value: `${Math.round((profile.value?.dynamic_score || 0) * 100)}%`,
    hint: "综合当前学习投入与成效",
    accent: "blue",
  },
  {
    label: "风险提醒",
    value: profile.value?.risk_level || "正常",
    hint: "结合近期学习状态判断",
    accent: "peach",
  },
  {
    label: "知识达成",
    value: knowledgeAchievement.value,
    hint: "当前课程已达成的知识点数量",
    accent: "green",
  },
]);
const focusCards = computed(() => [
  {
    eyebrow: "继续学习",
    title: dashboardTaskTitle.value,
    summary: "优先完成当前知识点学习与练习",
    action: "进入当前知识点",
    onClick: () => openCurrentLearning(),
    accent: "blue",
  },
  {
    eyebrow: "推荐内容",
    title: recommendedTarget.value?.title || "等待推荐内容",
    summary: reco.value?.reason_summary || "完成当前学习后系统会继续给出推荐路径",
    action: "去学习",
    onClick: () => openCurrentLearning(recommendedTarget.value?.id ?? null),
    accent: "green",
  },
  {
    eyebrow: "学习报告",
    title: "查看阶段反馈",
    summary: "把当前表现、阶段变化和建议放在一起看",
    action: "查看报告",
    onClick: () => openReport(),
    accent: "peach",
  },
]);

const journeyCards = computed(() => [
  {
    eyebrow: "当前任务",
    title: dashboardTaskTitle.value,
    detail: dashboardTaskSummary.value,
    accent: "blue",
  },
  {
    eyebrow: "下一推荐",
    title: recommendedTarget.value?.title || "等待推荐内容",
    detail: reco.value?.reason_summary || "系统会结合你的当前掌握度与画像结果自动更新推荐路径。",
    accent: "green",
  },
  {
    eyebrow: "画像状态",
    title: profile.value?.persona_label || "画像生成中",
    detail: profile.value?.persona_intro || "继续完成学习和问卷后，系统会生成更清晰的学习画像。",
    accent: "peach",
  },
]);

function percent(value?: number | null) {
  return Math.round((Number(value ?? 0) || 0) * 100);
}

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
    const data = await api.get("/graph/courses");
    courses.value = (data.data ?? []).map((item: any) => ({
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
      active: item.active !== false,
      enroll_status: String(item.enroll_status || ""),
      completed: item.completed === true,
      learning_available: item.learning_available !== false,
    }));
    subject.value = resolveStudentSubject(String(route.query.subject || ""), subject.value, courses.value, {
      allowCompleted: true,
      allowUnavailable: true,
    });
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
    let data = await getWithCache("/graph/kps", { subject: subject.value, grade: grade.value });
    if ((!Array.isArray(data) || data.length === 0) && grade.value !== "通用") {
      grade.value = "通用";
      data = await getWithCache("/graph/kps", { subject: subject.value, grade: grade.value });
    }
    kps.value = Array.isArray(data) ? data : [];
    const routeKp = Number(route.query.kp || 0);
    const saved = Number(localStorage.getItem(kpStorageKey()) || 0);
    if (routeKp && kps.value.some((item) => item.id === routeKp)) currentKpId.value = routeKp;
    if (!currentKpId.value && saved && kps.value.some((item) => item.id === saved)) currentKpId.value = saved;
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
      `/eval/profile?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`,
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
    const res = await api.get(`/reco?kp_id=${currentKpId.value}&ai=true`);
    reco.value = res.data ?? null;
  } catch (e: any) {
    if (e?.response?.status !== 401) ElMessage.error(e?.response?.data?.detail ?? "获取推荐失败");
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

function openLearningPath() {
  router.push({
    path: "/student/graph-workspace",
    query: studentQuery({
      subject: subject.value || undefined,
      kp: String(currentKpId.value || ""),
    }),
  });
}

function openReport() {
  router.push({
    path: "/student/report",
    query: studentQuery({ subject: subject.value || undefined }),
  });
}

function openQuestionnaire() {
  router.push({
    path: "/student/questionnaire",
    query: studentQuery({ subject: subject.value || undefined }),
  });
}

onMounted(async () => {
  await loadCourses();
  await loadKps();
  await refreshMastery();
  await loadProfile();
  await loadReco();
});
</script>

<template>
  <div class="student-dashboard-page">
    <section class="dashboard-hero shell-card">
      <div class="hero-copy">
        <span class="hero-eyebrow">学习中心</span>
        <div class="hero-heading">
          <div>
            <h1>{{ subject || "选择课程" }}</h1>
            <p class="hero-lead">{{ dashboardLead }}</p>
          </div>
          <div class="hero-badge">
            <span>{{ dashboardTaskCode }}</span>
            <strong>{{ masteryStageLabel }}</strong>
          </div>
        </div>

        <div class="hero-controls">
          <el-select v-model="subject" placeholder="选择课程" @change="onCourseChange">
            <el-option v-for="item in courses" :key="item.id" :label="item.title" :value="item.title" />
          </el-select>
          <button class="primary-cta" type="button" @click="openCurrentLearning()">
            <span>继续学习</span>
          </button>
          <button class="secondary-cta" type="button" @click="openLearningPath">学习路径</button>
        </div>

        <div class="hero-pills">
          <span class="meta-pill">当前阶段：{{ currentStageSummary }}</span>
          <span class="meta-pill">当前知识点：{{ dashboardTaskCode }}</span>
          <span v-if="profile?.persona_label" class="meta-pill">画像类型：{{ profile.persona_label }}</span>
        </div>

        <div class="hero-glance-grid">
          <article class="glance-card blue">
            <span>当前任务</span>
            <strong>{{ dashboardTaskTitle }}</strong>
            <p>{{ dashboardTaskSummary }}</p>
          </article>
          <article class="glance-card peach">
            <span>推荐路径</span>
            <strong>{{ recommendedTarget?.title || "等待推荐内容" }}</strong>
            <p>{{ reco?.reason_summary || "根据当前表现自动生成下一步推荐。" }}</p>
          </article>
        </div>
      </div>

      <div class="hero-spotlight">
        <article class="spotlight-card">
          <div class="spotlight-topline">
            <span>{{ dashboardTaskCode }}</span>
            <strong>{{ percent(mastery) }}%</strong>
          </div>
          <h2>{{ dashboardTaskTitle }}</h2>
          <p>{{ dashboardTaskSummary }}</p>
          <div class="spotlight-progress">
            <div class="spotlight-progress-head">
              <span>当前掌握度</span>
              <strong>{{ masteryStageLabel }}</strong>
            </div>
            <div class="progress-track">
              <div class="progress-bar" :style="{ width: `${percent(mastery)}%` }" />
            </div>
            <div class="progress-meta">
              <span>学习状态：{{ masteryStageLabel }}</span>
              <span>{{ percent(mastery) }}%</span>
            </div>
          </div>
        </article>

        <article class="spotlight-note">
          <span class="note-eyebrow">学习建议</span>
          <strong>{{ nextActionText }}</strong>
          <p>{{ reco?.recommendation_stage_label || "完成当前目标后，可继续推进推荐路径。" }}</p>
          <button type="button" class="note-action" @click="openCurrentLearning(recommendedTarget?.id ?? null)">
            直接进入
          </button>
        </article>
      </div>
    </section>

    <section class="dashboard-metrics">
      <article
        v-for="item in dashboardStats"
        :key="item.label"
        class="metric-card shell-card"
        :class="`accent-${item.accent}`"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <p>{{ item.hint }}</p>
      </article>

      <article class="breakdown-card shell-card">
        <div class="panel-head">
          <div>
            <span class="panel-eyebrow">学习切面</span>
            <h3>当前表现拆解</h3>
          </div>
          <span class="panel-note">{{ profile?.persona_intro || "根据动态画像自动更新" }}</span>
        </div>
        <div class="breakdown-grid">
          <div v-for="item in breakdownMini" :key="item.label" class="mini-progress">
            <div class="mini-progress-head">
              <span>{{ item.label }}</span>
              <strong>{{ percent(item.value) }}%</strong>
            </div>
            <div class="mini-track">
              <div class="mini-bar" :style="{ width: `${percent(item.value)}%` }" />
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="journey-strip">
      <article
        v-for="card in journeyCards"
        :key="card.eyebrow"
        class="journey-card shell-card"
        :class="`journey-${card.accent}`"
      >
        <span class="journey-card__eyebrow">{{ card.eyebrow }}</span>
        <h3>{{ card.title }}</h3>
        <p>{{ card.detail }}</p>
      </article>
    </section>

    <section class="focus-grid">
      <article
        v-for="card in focusCards"
        :key="card.eyebrow"
        class="focus-card shell-card"
        :class="`focus-${card.accent}`"
      >
        <span class="focus-eyebrow">{{ card.eyebrow }}</span>
        <h3>{{ card.title }}</h3>
        <p>{{ card.summary }}</p>
        <button type="button" class="focus-action" @click="card.onClick">{{ card.action }}</button>
      </article>
    </section>

    <section class="studio-grid">
      <div class="studio-main shell-card">
        <div class="panel-head">
          <div>
            <span class="panel-eyebrow">课程内容</span>
            <h3>{{ dashboardTaskTitle }}</h3>
          </div>
          <el-select v-model="currentKpId" placeholder="选择知识点" @change="onKpChange">
            <el-option v-for="item in kps" :key="item.id" :label="`${item.code} ${item.title}`" :value="item.id" />
          </el-select>
        </div>

        <div class="lesson-stage-card">
          <div>
            <span class="lesson-label">{{ dashboardTaskCode }}</span>
            <h2>{{ dashboardTaskTitle }}</h2>
            <p>{{ dashboardTaskSummary }}</p>
          </div>
          <div class="lesson-actions">
            <button type="button" class="primary-cta" @click="openCurrentLearning()">开始学习</button>
            <button type="button" class="secondary-cta" @click="openQuestionnaire">补充问卷</button>
          </div>
        </div>

        <div class="content-preview-grid">
          <article class="preview-card soft-blue">
            <span>知识达成</span>
            <strong>{{ knowledgeAchievement }}</strong>
            <p>当前课程已完成的知识点数量</p>
          </article>
          <article class="preview-card soft-green">
            <span>能力目标</span>
            <strong>
              {{ tripleSummary ? `${tripleSummary.ability_achieved ?? 0}/${tripleSummary.ability_target_total ?? 0}` : "--" }}
            </strong>
            <p>面向能力维度的阶段目标完成情况</p>
          </article>
          <article class="preview-card soft-peach">
            <span>素养目标</span>
            <strong>
              {{
                tripleSummary
                  ? `${tripleSummary.literacy_achieved ?? 0}/${tripleSummary.literacy_target_total ?? 0}`
                  : "--"
              }}
            </strong>
            <p>综合素养达成节奏</p>
          </article>
        </div>
      </div>

      <aside class="coach-rail">
        <article class="coach-card shell-card">
          <span class="panel-eyebrow">下一步</span>
          <h3>{{ nextActionText }}</h3>
          <p>{{ reco?.reason_summary || "系统会根据当前知识点和画像结果推荐下一步。" }}</p>
        </article>

        <article class="coach-card shell-card">
          <span class="panel-eyebrow">关键信号</span>
          <ul class="signal-list">
            <li v-for="signal in personaSignals.slice(0, 3)" :key="signal.key || signal.label">
              <strong>{{ signal.label }}</strong>
              <p>{{ signal.detail }}</p>
            </li>
            <li v-if="!personaSignals.length">
              <strong>暂无画像信号</strong>
              <p>完成课程学习与问卷后会生成更清晰的信号提示。</p>
            </li>
          </ul>
        </article>

        <article class="coach-card shell-card">
          <span class="panel-eyebrow">阶段摘要</span>
          <h3>{{ currentStageSummary }}</h3>
          <p>{{ profile?.persona_intro || "当前总结会结合动态表现持续更新。" }}</p>
        </article>
      </aside>
    </section>

    <section v-if="isPreview" class="preview-mode shell-card">
      <div>
        <span class="panel-eyebrow">预览模式</span>
        <h3>当前为课堂演示视图</h3>
        <p>可切换课程与知识点，快速预览学生端总览页的整体结构。</p>
      </div>
      <div class="preview-controls">
        <el-select v-model="subject" placeholder="选择课程" @change="onCourseChange">
          <el-option v-for="item in courses" :key="item.id" :label="item.title" :value="item.title" />
        </el-select>
        <el-select v-model="currentKpId" placeholder="选择知识点" @change="onKpChange">
          <el-option v-for="item in kps" :key="item.id" :label="item.title" :value="item.id" />
        </el-select>
      </div>
    </section>
  </div>
</template>

<style scoped>
.student-dashboard-page {
  --ink-strong: #0f172a;
  --ink-soft: #64748b;
  --warm-bg: #f5f7fb;
  --warm-surface: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  --warm-panel: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(244, 247, 251, 0.98) 100%);
  --warm-border: rgba(148, 163, 184, 0.24);
  --warm-shadow: 0 16px 32px rgba(15, 23, 42, 0.07);
  --accent-lime-soft: #eefbf3;
  --accent-lime-deep: #166534;
  --accent-blue: #eff6ff;
  --accent-blue-strong: #2563eb;
  --accent-peach: #fff4ec;
  --accent-primary-solid: #22c55e;
  --accent-primary-solid-hover: #16a34a;
  display: flex;
  flex-direction: column;
  gap: 26px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 0 56px;
  color: var(--ink-strong);
}

.student-dashboard-page :deep(.el-select) {
  width: 100%;
  max-width: 260px;
}

.student-dashboard-page :deep(.el-select__wrapper) {
  min-height: 48px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  background: rgba(255, 255, 255, 0.96);
}

.shell-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--warm-border);
  border-radius: 24px;
  background: var(--warm-surface);
  box-shadow: var(--warm-shadow);
}

.shell-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.2), transparent 24%),
    radial-gradient(circle at top right, rgba(220, 252, 231, 0.18), transparent 24%),
    radial-gradient(circle at bottom center, rgba(254, 242, 242, 0.18), transparent 28%);
  pointer-events: none;
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.78fr);
  gap: 24px;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(219, 234, 254, 0.46), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(244, 247, 251, 0.98) 100%);
}

.hero-copy,
.hero-spotlight,
.studio-main,
.coach-rail,
.preview-mode,
.breakdown-card,
.metric-card,
.focus-card {
  position: relative;
  z-index: 1;
}

.hero-eyebrow,
.panel-eyebrow,
.focus-eyebrow,
.note-eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  background: #eefbf3;
  color: #166534;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  border: 1px solid rgba(34, 197, 94, 0.18);
}

.hero-heading {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-top: 16px;
}

.hero-heading h1 {
  margin: 0;
  font-size: clamp(28px, 3.6vw, 44px);
  line-height: 1.08;
  letter-spacing: -0.03em;
  font-weight: 800;
}

.hero-lead {
  max-width: 760px;
  margin: 16px 0 0;
  color: var(--ink-soft);
  font-size: 15px;
  line-height: 1.75;
}

.hero-badge {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 170px;
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
}

.hero-badge span {
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 700;
}

.hero-badge strong {
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
}

.hero-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 24px;
}

.primary-cta,
.secondary-cta,
.focus-action,
.note-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 18px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.primary-cta,
.focus-action,
.note-action {
  background: var(--accent-primary-solid);
  color: #fff;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.secondary-cta {
  background: rgba(255, 255, 255, 0.94);
  color: var(--ink-strong);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
}

.primary-cta:hover,
.secondary-cta:hover,
.focus-action:hover,
.note-action:hover {
  transform: translateY(-2px);
}

.primary-cta:hover,
.focus-action:hover,
.note-action:hover {
  background: var(--accent-primary-solid-hover);
}

.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.84);
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.hero-glance-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.glance-card {
  padding: 20px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.92);
}

.glance-card.blue {
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.96), rgba(255, 255, 255, 0.92));
}

.glance-card.peach {
  background: linear-gradient(180deg, rgba(255, 244, 236, 0.96), rgba(255, 255, 255, 0.92));
}

.glance-card span,
.spotlight-topline span,
.panel-note,
.preview-card span,
.metric-card span,
.focus-eyebrow,
.focus-card p,
.lesson-label,
.coach-card p,
.signal-list p {
  color: var(--ink-soft);
}

.glance-card strong,
.preview-card strong,
.metric-card strong,
.focus-card h3,
.lesson-stage-card h2,
.coach-card h3 {
  display: block;
  margin-top: 8px;
  font-size: 22px;
  line-height: 1.15;
  font-weight: 800;
}

.glance-card p,
.preview-card p,
.focus-card p,
.lesson-stage-card p,
.coach-card p,
.signal-list p {
  margin: 10px 0 0;
  line-height: 1.65;
}

.hero-spotlight {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.spotlight-card,
.spotlight-note,
.lesson-stage-card,
.preview-card,
.coach-card {
  padding: 22px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
}

.spotlight-card h2 {
  margin: 14px 0 8px;
  font-size: 30px;
  line-height: 1.08;
  font-weight: 800;
}

.spotlight-card p,
.spotlight-note p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.65;
}

.spotlight-topline,
.spotlight-progress-head,
.progress-meta,
.mini-progress-head,
.panel-head,
.preview-mode,
.lesson-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.spotlight-topline strong {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  background: rgba(255, 240, 208, 0.9);
  color: #7d5d28;
}

.spotlight-progress {
  margin-top: 18px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 243, 222, 0.78);
}

.progress-track,
.mini-track {
  width: 100%;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(39, 50, 77, 0.08);
}

.progress-track {
  height: 12px;
  margin-top: 14px;
}

.mini-track {
  height: 10px;
  margin-top: 8px;
}

.progress-bar,
.mini-bar {
  height: 100%;
  border-radius: inherit;
  background: #d4bb61;
}

.spotlight-note {
  background: linear-gradient(180deg, rgba(255, 244, 233, 0.96), rgba(255, 252, 246, 0.9));
}

.spotlight-note strong {
  display: block;
  margin: 12px 0 8px;
  font-size: 30px;
  line-height: 1.15;
  font-weight: 900;
}

.note-action {
  margin-top: 16px;
  width: fit-content;
}

.dashboard-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.journey-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.journey-card {
  padding: 22px;
}

.journey-card__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  background: linear-gradient(180deg, #eef8ff 0%, #ffffff 100%);
  color: #365314;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.journey-card h3 {
  margin: 14px 0 0;
  font-size: 28px;
  line-height: 1.08;
  font-weight: 900;
}

.journey-card p {
  margin: 12px 0 0;
  color: var(--ink-soft);
  line-height: 1.7;
}

.journey-blue {
  background: linear-gradient(180deg, rgba(244, 249, 255, 0.98), rgba(255, 247, 235, 0.94));
}

.journey-green {
  background: linear-gradient(180deg, rgba(245, 255, 238, 0.98), rgba(255, 248, 240, 0.94));
}

.journey-peach {
  background: linear-gradient(180deg, rgba(255, 247, 239, 0.98), rgba(255, 251, 245, 0.94));
}

.metric-card,
.breakdown-card {
  padding: 20px;
}

.metric-card strong {
  font-size: 42px;
  line-height: 1.05;
}

.metric-card p {
  margin: 12px 0 0;
  color: var(--ink-soft);
  line-height: 1.6;
}

.metric-card.accent-blue::after,
.metric-card.accent-peach::after,
.metric-card.accent-green::after {
  content: "";
  position: absolute;
  right: 18px;
  top: 18px;
  width: 68px;
  height: 68px;
  border-radius: 20px;
  opacity: 0.8;
}

.metric-card.accent-blue::after {
  background: linear-gradient(135deg, rgba(143, 216, 255, 0.46), rgba(77, 132, 255, 0.08));
}

.metric-card.accent-peach::after {
  background: linear-gradient(135deg, rgba(255, 199, 160, 0.52), rgba(255, 118, 90, 0.08));
}

.metric-card.accent-green::after {
  background: linear-gradient(135deg, rgba(216, 255, 125, 0.62), rgba(77, 208, 111, 0.1));
}

.breakdown-card {
  grid-column: 1 / -1;
}

.panel-head {
  margin-bottom: 18px;
}

.panel-head h3 {
  margin: 6px 0 0;
  font-size: 30px;
  line-height: 1.05;
  font-weight: 900;
}

.panel-note {
  max-width: 420px;
  text-align: right;
  line-height: 1.6;
}

.breakdown-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.mini-progress {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 249, 241, 0.78);
  border: 2px solid rgba(39, 50, 77, 0.08);
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.focus-card {
  padding: 24px;
}

.focus-card h3 {
  margin: 12px 0 0;
}

.focus-action {
  margin-top: 18px;
  width: fit-content;
}

.focus-blue {
  background: linear-gradient(180deg, rgba(244, 249, 255, 0.98), rgba(255, 247, 235, 0.94));
}

.focus-green {
  background: linear-gradient(180deg, rgba(249, 255, 240, 0.98), rgba(255, 248, 235, 0.94));
}

.focus-peach {
  background: linear-gradient(180deg, rgba(255, 245, 238, 0.98), rgba(255, 249, 243, 0.94));
}

.studio-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.72fr);
  gap: 20px;
}

.studio-main {
  padding: 24px;
}

.lesson-stage-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  background: linear-gradient(180deg, rgba(255, 245, 232, 0.96), rgba(255, 252, 246, 0.9));
}

.lesson-label {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 237, 202, 0.94);
  color: #7d5d28;
  font-size: 13px;
  font-weight: 800;
}

.content-preview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.preview-card.soft-blue {
  background: linear-gradient(180deg, rgba(242, 248, 255, 0.94), rgba(255, 250, 244, 0.9));
}

.preview-card.soft-green {
  background: linear-gradient(180deg, rgba(248, 255, 241, 0.94), rgba(255, 250, 244, 0.9));
}

.preview-card.soft-peach {
  background: linear-gradient(180deg, rgba(255, 246, 236, 0.96), rgba(255, 250, 244, 0.9));
}

.coach-rail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.signal-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.signal-list li {
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 249, 241, 0.8);
  border: 2px solid rgba(39, 50, 77, 0.08);
}

.signal-list strong {
  display: block;
  font-size: 18px;
  line-height: 1.2;
  font-weight: 900;
}

.preview-mode {
  padding: 22px 24px;
}

.preview-mode h3 {
  margin: 8px 0 10px;
  font-size: 28px;
  line-height: 1.05;
  font-weight: 900;
}

.preview-mode p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.6;
}

.preview-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

@media (max-width: 1180px) {
  .dashboard-hero,
  .studio-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-metrics,
  .journey-strip,
  .focus-grid,
  .content-preview-grid,
  .breakdown-grid,
  .hero-glance-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 860px) {
  .student-dashboard-page {
    gap: 20px;
    padding: 16px 0 36px;
  }

  .dashboard-hero,
  .metric-card,
  .breakdown-card,
  .focus-card,
  .studio-main,
  .coach-card {
    padding: 20px;
  }

  .hero-heading,
  .panel-head,
  .lesson-stage-card,
  .preview-mode {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-heading h1 {
    font-size: 42px;
  }

  .dashboard-metrics,
  .journey-strip,
  .focus-grid,
  .content-preview-grid,
  .breakdown-grid,
  .hero-glance-grid {
    grid-template-columns: 1fr;
  }

  .hero-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .student-dashboard-page :deep(.el-select) {
    max-width: none;
  }
}
</style>
