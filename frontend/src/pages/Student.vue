<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import { getRole, getUsername } from "../token";
import HoverTip from "../components/HoverTip.vue";

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

const courses = ref<Course[]>([]);
const subject = ref<string>("");
const grade = ref<string>("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);

const mastery = ref<number>(0);
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

function kpStorageKey() {
  const username = getUsername() || localStorage.getItem("da_last_user") || "guest";
  return `da_kp_${username}_${subject.value}`;
}

async function loadCourses() {
  try {
    const data = await api.get("/graph/courses");
    courses.value = data.data ?? [];
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
    query: {
      subject: subject.value,
      kp: String(recommendedTargetId.value),
    },
  });
}

function resetReco() {
  reco.value = null;
}

async function onCourseChange() {
  currentKpId.value = null;
  reco.value = null;
  await loadKps();
  await refreshMastery();
}

async function onKpChange() {
  if (currentKpId.value) localStorage.setItem(kpStorageKey(), String(currentKpId.value));
  reco.value = null;
  await refreshMastery();
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
    router.push("/student/overview");
    return;
  }
  if (key === "questionnaire") {
    router.push({ path: "/student/questionnaire", query: { subject: subject.value || undefined } });
    return;
  }
  if (key === "report") {
    router.push({ path: "/student/report", query: { subject: subject.value || undefined } });
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
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载失败（请先在管理端准备课程与知识点数据）");
  }
});
</script>

<template>
  <div class="page-shell">
    <template v-if="isStudent">
      <WorkspaceTopbar
        v-model="subject"
        :courses="courses"
        badge="学生端"
        title="学习首页"
        @change="onCourseChange"
      />

      <section class="panel-card simple-intro">
        <strong>最简单的使用方法</strong>
        <span>先选课程和知识点，再点“打开图谱”或“去学习”，最后看报告。</span>
        <div class="simple-intro__actions">
          <el-button type="primary" @click="openGraphWorkspace" :disabled="!currentKpId">打开图谱</el-button>
          <el-button @click="router.push({ path: '/student/report', query: { subject: subject || undefined } })">看报告</el-button>
          <el-button @click="router.push({ path: '/student/questionnaire', query: { subject: subject || undefined } })">填问卷</el-button>
        </div>
      </section>

      <div class="page-grid">
      <section class="panel-card info-panel">
        <div class="section-block">
          <div class="panel-title">我的课程</div>
        </div>

        <div class="section-block section-block--spaced">
          <div class="panel-title">学习导航</div>
        </div>
        <div v-if="courses.length === 0" class="student-tip-inline" style="margin-bottom: 8px">
          <span>暂无课程</span>
          <HoverTip content="请先在管理员端配置课程，学生端这里才会显示可学习课程。" />
        </div>

        <div class="step-card">
          <div class="step-card__index">1</div>
          <div class="step-card__body">
            <div class="step-card__title">先选知识点</div>
            <el-select
              v-model="currentKpId"
              placeholder="选择知识点"
              style="width: 100%"
              :disabled="courses.length === 0 || kps.length === 0"
              @change="onKpChange"
            >
              <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
            </el-select>
          </div>
        </div>

        <div v-if="currentKp" class="kp-meta">
          <div class="kp-code">{{ currentKp.code }}</div>
          <div class="kp-title">{{ currentKp.title }}</div>
        </div>

        <div v-if="currentKpId" class="kp-progress">
          <div class="metric-head">
            <span>当前掌握度</span>
            <strong>{{ Math.round(mastery * 100) }}%</strong>
          </div>
          <el-progress :percentage="Math.round(mastery * 100)" />
        </div>

        <div class="step-card step-card--action">
          <div class="step-card__index">2</div>
          <div class="step-card__body">
            <div class="step-card__title">接下来做什么</div>
            <div class="action-row">
              <el-button type="primary" :disabled="!currentKpId" @click="openGraphWorkspace">打开图谱</el-button>
              <el-button :disabled="!currentKpId" @click="getReco">给我建议</el-button>
              <el-button :disabled="!currentKpId" @click="router.push({ path: '/student/report', query: { subject: subject || undefined } })">看报告</el-button>
            </div>
          </div>
        </div>

        <el-card v-if="reco" class="sub-card" shadow="never">
          <template #header>下一步建议</template>
          <div class="reco-body">
            <div class="reco-highlight">
              <div class="reco-label">建议先学</div>
              <div class="reco-target">
                {{ reco.target_kp.code }} {{ reco.target_kp.title }}
              </div>
              <div class="reco-text">{{ reco.reason_summary }}</div>
              <div class="reco-text">{{ reco.advice_text }}</div>
            </div>
            <div class="action-row">
              <el-button @click="resetReco">关闭</el-button>
              <el-button type="primary" :disabled="!recommendedTarget" @click="goToRecommended">去这个知识点</el-button>
            </div>
          </div>
        </el-card>
      </section>

      <section class="panel-card content-panel">
        <div class="tab-panel">
          <OverviewPane :subject="subject" :grade="grade" />

          <div class="feature-grid">
            <button class="feature-card" @click="openGraphWorkspace">
              <strong>打开图谱</strong>
              <span>在图谱里点知识点，然后进入学习页面。</span>
            </button>
            <button class="feature-card" @click="router.push({ path: '/student/questionnaire', query: { subject: subject || undefined } })">
              <strong>填写问卷</strong>
              <span>补充你的学习情况。</span>
            </button>
            <button class="feature-card" @click="router.push({ path: '/student/report', query: { subject: subject || undefined } })">
              <strong>查看报告</strong>
              <span>看看你学得怎么样，下一步该做什么。</span>
            </button>
            <button class="feature-card" :disabled="!recommendedTargetId" @click="goToRecommended">
              <strong>系统建议</strong>
              <span>{{ recommendedTarget ? `${recommendedTarget.code} ${recommendedTarget.title}` : "先点“给我建议”再看这里" }}</span>
            </button>
          </div>
        </div>
      </section>
      </div>
    </template>

    <section v-else class="panel-card">
      <div class="panel-title">学习内容预览</div>
      <div class="control-row">
        <el-select v-model="subject" placeholder="选择课程" style="width: 100%" @change="onCourseChange">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
        </el-select>
        <el-select
          v-model="currentKpId"
          placeholder="选择知识点"
          style="width: 100%"
          :disabled="courses.length === 0 || kps.length === 0"
          @change="onKpChange"
        >
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
        </el-select>
      </div>
      <div class="preview-note">
        预览模式已收敛到知识图谱工作区。资源和练习统一从图谱节点进入学习内容页。
      </div>
    </section>
  </div>

</template>

<style scoped>
.preview-note {
  padding: 20px;
  border-radius: var(--app-radius);
  background: var(--app-bg-alt);
  border: 1px solid var(--app-border);
  color: var(--app-ink-soft);
  line-height: 1.7;
  font-size: 14px;
}

.page-shell {
  display: grid;
  gap: 16px;
}

.simple-intro {
  padding: 16px 18px;
  display: grid;
  gap: 10px;
}

.simple-intro strong {
  font-size: 18px;
  color: var(--app-ink);
}

.simple-intro span {
  color: var(--app-ink-soft);
  line-height: 1.7;
}

.simple-intro__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.page-grid {
  display: grid;
  grid-template-columns: minmax(300px, 360px) 1fr;
  gap: 16px;
  align-items: start;
}

.section-block {
  display: grid;
  gap: 10px;
}

.section-block--spaced {
  margin-top: 10px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--app-ink);
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title::before {
  content: '';
  width: 4px;
  height: 20px;
  border-radius: 4px;
  background: var(--app-green);
}

.panel-help {
  margin-bottom: 14px;
  color: var(--app-ink-soft);
  font-size: 13px;
  line-height: 1.6;
}

.info-panel {
  padding: 18px;
}

.content-panel {
  overflow: hidden;
  padding: 0;
}

.feature-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.feature-card {
  text-align: left;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  background: #ffffff;
  padding: 14px;
  display: grid;
  gap: 6px;
  cursor: pointer;
  box-shadow: none;
}

.feature-card strong {
  font-size: 14px;
  color: var(--app-ink);
}

.feature-card span {
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-ink-soft);
}

.feature-card:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.tab-panel {
  display: grid;
  gap: 12px;
}

.tab-panel__intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 320px);
  gap: 12px;
  padding: 0 0 12px;
  border-bottom: 1px solid var(--app-border);
}

.tab-panel__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6b84aa;
}

.tab-panel__title {
  margin-top: 6px;
  font-size: 18px;
  line-height: 1.25;
  font-weight: 800;
  color: #203657;
}

.tab-panel__desc {
  align-self: end;
  font-size: 12px;
  line-height: 1.6;
  color: #5e7697;
}

.control-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 0 16px;
  padding-top: 16px;
}

.step-card {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  border-radius: var(--app-radius);
  background: #ffffff;
  border: 1px solid var(--app-border);
  margin-bottom: 12px;
  box-shadow: none;
}

.step-card--action {
  align-items: start;
}

.step-card__index {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: #eef4ff;
  color: var(--app-green-dark);
  font-weight: 600;
}

.step-card__body {
  display: grid;
  gap: 10px;
}

.step-card__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--app-ink);
}

.kp-meta {
  margin-top: 4px;
  padding: 16px;
  background: #fbfcfe;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  display: grid;
  gap: 6px;
}

.kp-code {
  font-size: 12px;
  color: var(--app-ink-soft);
}

.kp-title {
  font-weight: 600;
  color: var(--app-ink);
  font-size: 15px;
}

.kp-progress {
  margin-top: 4px;
  display: grid;
  gap: 10px;
  padding: 16px;
  background: #fbfcfe;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
}

.metric-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  color: var(--app-ink-soft);
}

.metric-head strong {
  color: var(--app-ink);
  font-weight: 600;
}

.action-row {
  display: grid;
  gap: 12px;
}

.sub-card {
  margin-top: 20px;
}

.graph-entry {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  padding: 0;
}

.graph-entry__main,
.graph-entry__side {
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  background: #ffffff;
}

.graph-entry__main {
  padding: 20px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.graph-entry__kicker {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--app-ink-soft);
}

.graph-entry__title {
  font-size: 22px;
  line-height: 1.2;
  font-weight: 600;
  color: var(--app-ink);
}

.graph-entry__text {
  max-width: 680px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--app-ink-soft);
}

.graph-entry__meta {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.graph-entry__item {
  padding: 16px;
  display: grid;
  gap: 8px;
  border-radius: var(--app-radius);
  background: #fbfcfe;
  border: 1px solid var(--app-border);
}

.graph-entry__item span {
  font-size: 13px;
  color: var(--app-ink-soft);
}

.graph-entry__item strong {
  font-size: 18px;
  line-height: 1.4;
  color: var(--app-ink);
  font-weight: 600;
}

.graph-entry__side {
  padding: 20px;
  display: grid;
  gap: 20px;
  align-content: start;
}

.graph-entry__side :deep(.el-button) {
  width: 100%;
}

.graph-entry__tips {
  padding: 16px 20px;
  border-radius: var(--app-radius);
  background: #fbfcfe;
  border: 1px solid var(--app-border);
  display: grid;
  gap: 12px;
  color: var(--app-ink-soft);
  line-height: 1.5;
  font-size: 14px;
}

.student-tip-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #7c6750;
  font-size: 13px;
  font-weight: 700;
}

.reco-body {
  display: grid;
  gap: 14px;
  padding: 0;
}

.reco-summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.reco-summary > div,
.reco-box {
  padding: 16px;
  border-radius: var(--app-radius);
  background: #fbfcfe;
  border: 1px solid var(--app-border);
}

.reco-label {
  font-size: 12px;
  color: var(--app-ink-soft);
  font-weight: 600;
  text-transform: uppercase;
}

.reco-highlight {
  padding: 18px;
  border-radius: var(--app-radius);
  background: #fbfcfe;
  color: var(--app-ink);
  display: grid;
  gap: 8px;
  border: 1px solid var(--app-border);
}

.reco-target {
  font-size: 18px;
  font-weight: 600;
}

.reco-text {
  font-size: 14px;
  line-height: 1.7;
}

.reco-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.reco-item {
  padding: 10px 0;
  border-bottom: 1px dashed var(--app-border);
  font-size: 14px;
  color: var(--app-ink);
}

.dify-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  padding: 0 20px;
  background: var(--app-bg);
  border-bottom: 1px solid var(--app-border);
}

.dify-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--app-border);
}

.dify-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  padding: 16px 24px;
  color: var(--app-ink-soft);
}

.dify-tabs :deep(.el-tabs__item:hover) {
  color: var(--app-green);
}

.dify-tabs :deep(.el-tabs__item.is-active) {
  color: var(--app-green);
  font-weight: 600;
  position: relative;
}

.dify-tabs :deep(.el-tabs__item.is-active::after) {
  content: '';
  position: absolute;
  bottom: 0;
  left: 24px;
  right: 24px;
  height: 2px;
  background: var(--app-green);
  border-radius: 2px;
}

.dify-tabs :deep(.el-tabs__content) {
  padding: 24px;
  min-height: 400px;
}

@media (max-width: 1100px) {
  .page-grid {
    grid-template-columns: 1fr;
  }

  .graph-entry,
  .tab-panel__intro,
  .feature-grid,
  .graph-entry__meta,
  .reco-summary,
  .reco-grid {
    grid-template-columns: 1fr;
  }
  
  .info-panel,
  .content-panel {
    width: 100%;
  }
  
  .graph-entry__main {
    padding: 24px 20px;
  }
  
  .graph-entry__title {
    font-size: 20px;
  }
}

@media (max-width: 768px) {
  .page-grid {
    gap: 16px;
  }
  
  .info-panel {
    padding: 20px;
  }
  
  .dify-tabs :deep(.el-tabs__header) {
    padding: 0 12px;
  }
  
  .dify-tabs :deep(.el-tabs__item) {
    padding: 12px 16px;
    font-size: 13px;
  }
  
  .dify-tabs :deep(.el-tabs__content) {
    padding: 16px;
  }
  
  .graph-entry {
    padding: 16px;
    gap: 16px;
  }
  
  .graph-entry__main {
    padding: 20px;
  }
  
  .graph-entry__title {
    font-size: 18px;
  }
  
  .graph-entry__item {
    padding: 16px;
  }
  
  .graph-entry__side {
    padding: 20px;
  }
}
</style>
