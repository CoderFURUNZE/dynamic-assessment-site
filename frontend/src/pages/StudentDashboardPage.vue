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
const currentCourse = computed(() => courses.value.find((item) => item.title === subject.value) ?? null);

watch(
  [subject, isStudent],
  () => {
    if (isStudent.value && subject.value) {
      saveStudentSubject(subject.value);
    }
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
  return "先完成当前知识点学习，再根据推荐调整下一步重点。";
});
const dashboardTaskTitle = computed(() => currentKp.value?.title || "当前暂无学习任务");
const dashboardTaskCode = computed(() => currentKp.value?.code || "未选择知识点");
const dashboardTaskSummary = computed(() => currentKp.value?.description || "当前课程下还没有可展示的知识点描述。");
const knowledgeAchievement = computed(() =>
  tripleSummary.value ? `${tripleSummary.value.knowledge_achieved ?? 0}/${tripleSummary.value.knowledge_total ?? 0}` : "--",
);
const nextActionText = computed(() => {
  if (recommendedTarget.value) return `下一步建议：${recommendedTarget.value.title}`;
  if (currentKp.value) return `继续完成 ${currentKp.value.title}`;
  return "先选择课程并进入知识点学习";
});
const dashboardStats = computed(() => [
  { label: "动态评分", value: `${Math.round((profile.value?.dynamic_score || 0) * 100)}%`, hint: "综合当前学习投入与成效" },
  { label: "风险提醒", value: profile.value?.risk_level || "正常", hint: "结合近期学习状态判断" },
  { label: "知识达成", value: knowledgeAchievement.value, hint: "当前课程已达成的知识点数量" },
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
    const data = await api.get("/graph/courses");
    courses.value = (data.data ?? []).map((item: any) => ({
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
      active: item.active !== false,
      enroll_status: String(item.enroll_status || ""),
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
    if (saved && kps.value.some((item) => item.id === saved)) currentKpId.value = saved;
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
    const res = await api.get(`/eval/profile?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
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

function openGraphWorkspace() {
  router.push({
    path: "/student/graph-workspace",
    query: studentQuery({
      subject: subject.value || undefined,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
    }),
  });
}

function openReport() {
  router.push({
    path: "/student/report",
    query: studentQuery({
      subject: subject.value || undefined,
    }),
  });
}

function openQuestionnaire() {
  router.push({
    path: "/student/questionnaire",
    query: studentQuery({
      subject: subject.value || undefined,
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
        <div class="student-dashboard__hero-copy">
          <span class="student-dashboard__hero-eyebrow">学习中心</span>
          <h2>{{ currentCourse?.title || subject || "学习总览" }}</h2>
          <p>{{ dashboardLead }}</p>

          <div class="student-dashboard__hero-actions">
            <el-select v-model="subject" placeholder="切换课程" @change="onCourseChange" style="width: 220px">
              <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
            </el-select>
            <el-button type="primary" @click="openCurrentLearning()">继续学习</el-button>
            <el-button @click="openGraphWorkspace">知识图谱</el-button>
          </div>

          <div class="student-dashboard__hero-meta">
            <span>当前阶段：{{ currentStageSummary }}</span>
            <span>当前知识点：{{ dashboardTaskCode }}</span>
          </div>
        </div>

        <div v-if="currentKp" class="student-dashboard__hero-card">
          <div class="student-dashboard__hero-card-top">
            <span>{{ dashboardTaskCode }}</span>
            <strong>{{ Math.round(mastery * 100) }}%</strong>
          </div>
          <h3>{{ dashboardTaskTitle }}</h3>
          <p>{{ dashboardTaskSummary }}</p>
          <div class="student-dashboard__progress-box">
            <div class="student-dashboard__progress-head">
              <span>当前掌握度</span>
              <strong>{{ masteryStageLabel }}</strong>
            </div>
            <el-progress :percentage="Math.round(mastery * 100)" :stroke-width="10" />
          </div>
        </div>
      </section>

      <section class="student-dashboard__stats-shell">
        <div class="student-dashboard__stats">
          <article v-for="item in dashboardStats" :key="item.label" class="student-dashboard__stat-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.hint }}</small>
          </article>
        </div>
      </section>

      <section class="student-dashboard__action-shell">
        <div class="student-dashboard__action-strip">
          <button class="student-dashboard__action-card student-dashboard__action-card--primary" type="button" @click="openCurrentLearning()">
            <span>继续学习</span>
            <strong>{{ currentKp ? currentKp.title : "进入当前知识点" }}</strong>
            <small>优先完成当前知识点学习与练习</small>
          </button>
          <button class="student-dashboard__action-card" type="button" @click="openCurrentLearning(recommendedTarget?.id || null)">
            <span>推荐内容</span>
            <strong>{{ recommendedTarget ? recommendedTarget.title : "继续当前学习任务" }}</strong>
            <small>{{ reco?.recommendation_stage_label || "根据当前状态推荐下一步内容" }}</small>
          </button>
          <button class="student-dashboard__action-card" type="button" @click="openReport">
            <span>学习报告</span>
            <strong>查看阶段反馈</strong>
            <small>把当前表现和建议放在一起看</small>
          </button>
        </div>
      </section>

      <section class="student-dashboard__simple-grid">
        <section class="student-dashboard__simple-panel">
          <div class="student-dashboard__section-top">
            <span class="student-dashboard__section-eyebrow">课程内容</span>
            <el-select v-model="currentKpId" @change="onKpChange" placeholder="切换知识点" style="width: 220px">
              <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
            </el-select>
          </div>

          <div class="student-dashboard__simple-course" v-if="currentKp">
            <h3>{{ dashboardTaskTitle }}</h3>
            <p>{{ dashboardTaskSummary }}</p>
            <div class="student-dashboard__simple-actions">
              <el-button type="primary" @click="openCurrentLearning()">开始学习</el-button>
              <el-button @click="openQuestionnaire">补充问卷</el-button>
            </div>
          </div>
          <el-empty v-else description="当前课程暂时没有可学习的知识点" />
        </section>

        <section class="student-dashboard__simple-panel">
          <div class="student-dashboard__section-top">
            <span class="student-dashboard__section-eyebrow">学习建议</span>
          </div>

          <div class="student-dashboard__simple-list">
            <article class="student-dashboard__simple-item">
              <span>下一步</span>
              <strong>{{ nextActionText }}</strong>
              <p>{{ reco?.reason_summary || profile?.persona_intro || "系统会根据当前掌握度推荐下一步内容。" }}</p>
            </article>
            <article class="student-dashboard__simple-item">
              <span>知识达成</span>
              <strong>{{ knowledgeAchievement }}</strong>
              <p>当前课程已完成的知识点数量。</p>
            </article>
            <article class="student-dashboard__simple-item">
              <span>关键信号</span>
              <strong>{{ personaSignals.length }} 项</strong>
              <p v-if="personaSignals.length">{{ personaSignals[0]?.label }}：{{ personaSignals[0]?.detail }}</p>
              <p v-else>当前暂无额外画像信号，继续保持当前学习节奏。</p>
            </article>
          </div>
        </section>
      </section>
    </template>

    <section v-else class="preview-mode">
      <div class="preview-mode__copy">
        <span class="student-dashboard__section-eyebrow">学生端预览</span>
        <h2>先选课程，再定位知识点</h2>
        <p>用于管理员快速查看学生端学习内容与页面状态，不影响真实学生操作。</p>
      </div>

      <div class="preview-mode__selectors">
        <div class="preview-mode__field">
          <label>预览课程</label>
          <el-select v-model="subject" placeholder="请选择课程" @change="onCourseChange">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
          </el-select>
        </div>
        <div class="preview-mode__field">
          <label>预览知识点</label>
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
  display: grid;
  gap: 18px;
  padding: 0;
  min-width: 0;
}

.student-dashboard__hero,
.student-dashboard__stats-shell,
.student-dashboard__simple-panel,
.student-dashboard__action-shell,
.preview-mode {
  border: 3px solid #1f2937;
  border-radius: 32px;
  background: #fffdf8;
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
  min-width: 0;
  max-width: 100%;
}

.student-dashboard__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 22px;
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(201, 237, 255, 0.4), transparent 28%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
}

.student-dashboard__hero-copy {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.student-dashboard__hero-eyebrow,
.student-dashboard__section-eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: #d7f9a8;
  font-size: 12px;
  font-weight: 800;
  color: #1f2937;
}

.student-dashboard__hero-copy h2,
.student-dashboard__hero-card h3,
.student-dashboard__simple-course h3,
.student-dashboard__simple-item strong,
.preview-mode__copy h2 {
  margin: 0;
  font-family: "Fredoka", "Nunito", sans-serif;
  color: #1d2433;
}

.student-dashboard__hero-copy h2 {
  font-size: clamp(34px, 4vw, 52px);
  line-height: 1;
  overflow-wrap: anywhere;
}

.student-dashboard__hero-copy p,
.student-dashboard__hero-card p,
.student-dashboard__simple-course p,
.student-dashboard__simple-item p,
.preview-mode__copy p {
  margin: 0;
  color: #636b7a;
  line-height: 1.7;
}

.student-dashboard__hero-actions,
.student-dashboard__simple-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  min-width: 0;
}

.student-dashboard__hero-actions :deep(.el-select) {
  max-width: 100%;
}

.student-dashboard__hero-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.student-dashboard__hero-meta span,
.student-dashboard__hero-card-top span,
.student-dashboard__hero-card-top strong {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: #f6faff;
  font-size: 12px;
  font-weight: 800;
  color: #29476a;
}

.student-dashboard__hero-card {
  display: grid;
  gap: 12px;
  align-content: start;
  padding: 18px;
  border-radius: 24px;
  border: 1.5px solid #c6d8ef;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  min-width: 0;
}

.student-dashboard__hero-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.student-dashboard__progress-box {
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 20px;
  border: 1.5px solid #c6d8ef;
  background: #f8fbff;
}

.student-dashboard__progress-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.student-dashboard__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  min-width: 0;
}

.student-dashboard__stats-shell {
  padding: 14px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
}

.student-dashboard__stat-card,
.student-dashboard__action-card,
.student-dashboard__simple-item {
  border: 1.5px solid #c6d8ef;
  border-radius: 24px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
  min-width: 0;
}

.student-dashboard__stat-card {
  display: grid;
  gap: 8px;
  padding: 18px;
}

.student-dashboard__stat-card span,
.student-dashboard__action-card span,
.student-dashboard__simple-item span {
  font-size: 12px;
  font-weight: 800;
  color: #6b7280;
}

.student-dashboard__stat-card strong {
  font-size: 28px;
  line-height: 1.05;
  color: #1d2433;
}

.student-dashboard__stat-card small {
  color: #6b7280;
  line-height: 1.6;
}

.student-dashboard__action-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  min-width: 0;
}

.student-dashboard__action-shell {
  padding: 14px;
  border-width: 3px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.student-dashboard__action-card {
  display: grid;
  gap: 10px;
  padding: 20px 22px;
  text-align: left;
  cursor: pointer;
  align-content: start;
  min-height: 148px;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.student-dashboard__action-card:hover {
  border-color: #96b6e2;
  background: #eef5ff;
  transform: translateY(-2px);
  box-shadow: 0 10px 18px rgba(31, 41, 55, 0.08);
}

.student-dashboard__action-card strong {
  font-family: "Fredoka", "Nunito", sans-serif;
  font-size: 20px;
  color: #1d2433;
  overflow-wrap: anywhere;
}

.student-dashboard__action-card small {
  color: #6b7280;
  line-height: 1.6;
}

.student-dashboard__action-card--primary {
  border-color: #96b6e2;
  background: linear-gradient(180deg, #eef5ff 0%, #ffffff 100%);
  box-shadow: 0 10px 18px rgba(31, 41, 55, 0.08);
}

.student-dashboard__action-card--primary span {
  color: #355070;
}

.student-dashboard__action-card--primary strong {
  color: #16355c;
}

.student-dashboard__simple-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  min-width: 0;
}

.student-dashboard__simple-panel {
  padding: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  min-width: 0;
}

.student-dashboard__section-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.student-dashboard__simple-course {
  display: grid;
  gap: 12px;
}

.student-dashboard__simple-list {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.student-dashboard__simple-item {
  display: grid;
  gap: 8px;
  padding: 18px;
}

.student-dashboard__simple-item strong {
  overflow-wrap: anywhere;
}

.preview-mode {
  display: grid;
  gap: 18px;
  padding: 22px;
}

.preview-mode__copy {
  display: grid;
  gap: 10px;
}

.preview-mode__selectors {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.preview-mode__field {
  display: grid;
  gap: 8px;
}

.preview-mode__field label {
  font-size: 13px;
  font-weight: 700;
  color: #4c6488;
}

@media (max-width: 1100px) {
  .student-dashboard__hero,
  .student-dashboard__action-shell,
  .student-dashboard__action-strip,
  .student-dashboard__simple-grid,
  .student-dashboard__stats,
  .preview-mode__selectors {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .student-dashboard__hero,
  .student-dashboard__stats-shell,
  .student-dashboard__action-shell,
  .student-dashboard__simple-panel,
  .preview-mode {
    padding: 18px;
  }

  .student-dashboard__action-shell {
    padding: 14px;
  }

  .student-dashboard__hero-copy h2 {
    font-size: 40px;
  }
}
</style>
