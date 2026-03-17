<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import { getRole, getUsername } from "../token";

import OverviewPane from "../components/OverviewPane.vue";
import HintButton from "../components/HintButton.vue";
import WorkspaceTopbar from "../components/WorkspaceTopbar.vue";
import SimpleStepsBar from "../components/SimpleStepsBar.vue";
import StarterGuideCard from "../components/StarterGuideCard.vue";

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
        badge="Student Workspace"
        title="学习中心"
        @change="onCourseChange"
      >
        <HintButton tip="进入单独报名页面，查看审核状态与通知。" @click="router.push('/student/enroll')">
          课程报名
        </HintButton>
      </WorkspaceTopbar>

      <StarterGuideCard
        title="使用顺序"
        intro="先总览，再图谱，再学习。"
        :items="[
          { title: '先看总览', desc: '先知道这门课学什么、现在学到哪里。' },
          { title: '再看图谱', desc: '图谱能告诉你知识点之间的关系，先学什么、后学什么。' },
          { title: '进入学习内容页', desc: '在图谱里点知识点，再进入学习内容页学习资源和练习。' },
          { title: '最后看报告', desc: '报告页会显示学习情况、建议和需要补充填写的内容。' },
        ]"
        :actions="[
          { key: 'overview', label: '先看总览', primary: true },
          { key: 'graph-workspace', label: '打开知识图谱' },
          { key: 'questionnaire', label: '去补充问卷' },
          { key: 'report', label: '去看报告' },
        ]"
        storage-key="student-main"
        @action="handleGuideAction"
      />

      <div class="page-grid">
      <section class="panel-card info-panel">
        <div class="section-block">
          <div class="panel-title">我的课程</div>
        </div>

        <div class="section-block section-block--spaced">
          <div class="panel-title">学习导航</div>
        </div>
        <div v-if="courses.length === 0" style="margin-bottom: 8px">
          <el-alert type="warning" title="暂无课程，请先在管理员端配置课程" :closable="false" show-icon />
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
            <div class="step-card__title">再开始操作</div>
            <div class="action-row">
              <HintButton tip="重新读取这个知识点的最新掌握度。" type="primary" :disabled="!currentKpId" @click="refreshMastery">
                刷新掌握度
              </HintButton>
              <HintButton tip="根据当前知识点和学习状态生成下一步建议。" type="success" :disabled="!currentKpId" @click="getReco">
                生成学习建议
              </HintButton>
              <HintButton tip="进入大图谱页面，查看知识关系、资源和推荐路径。" :disabled="!currentKpId" @click="openGraphWorkspace">
                打开知识图谱
              </HintButton>
            </div>
          </div>
        </div>

        <el-card v-if="reco" class="sub-card" shadow="never">
          <template #header>个性化推荐</template>
          <div class="reco-body">
            <div class="reco-summary">
              <div>
                <div class="reco-label">当前画像</div>
                <strong>{{ reco.persona_label }}</strong>
              </div>
              <div>
                <div class="reco-label">动态评分</div>
                <strong>{{ Math.round((reco.dynamic_score || 0) * 100) }}%</strong>
              </div>
              <div>
                <div class="reco-label">评价等级</div>
                <strong>{{ reco.risk_level }}</strong>
              </div>
            </div>

            <div class="reco-highlight">
              <div class="reco-label">推荐目标</div>
              <div class="reco-target">
                {{ reco.target_kp.code }} {{ reco.target_kp.title }}
              </div>
              <div class="action-row action-row--compact">
                <el-tag size="small" type="primary">{{ recommendationStageLabel }}</el-tag>
                <el-tag size="small" type="info">{{ reco.persona_strategy_tag }}</el-tag>
              </div>
              <div class="reco-text">{{ reco.reason_summary }}</div>
              <div class="reco-text">{{ reco.advice_text }}</div>
            </div>

            <div class="reco-grid">
              <div class="reco-box">
                <div class="reco-label">推荐依据</div>
                <div class="reco-item">当前掌握度：{{ Math.round((reco.diagnosis?.mastery || 0) * 100) }}%</div>
                <div class="reco-item">当前状态：{{ reco.diagnosis?.status || "未知" }}</div>
                <div class="reco-item">{{ reco.diagnosis?.reason_summary || "暂无掌握度解释" }}</div>
                <div class="reco-item">证据覆盖：{{ Math.round(((reco.evidence?.score || 0) * 100)) }}%</div>
              </div>
              <div class="reco-box">
                <div class="reco-label">解锁与补救</div>
                <div class="reco-item">推荐动作：{{ recommendationStageLabel }}</div>
                <div class="reco-item">缺失条件：{{ (reco.evidence?.missing?.length ?? 0) > 0 ? reco.evidence?.missing?.join("、") : "已满足主要条件" }}</div>
                <div class="reco-item">路径长度：{{ reco.remedy_path?.path?.length ?? 0 }} 个节点</div>
                <div class="reco-item">{{ reco.unlock?.can_unlock_next ? "当前可解锁下一节点" : "当前仍需先补强再解锁" }}</div>
              </div>
            </div>

            <div class="reco-grid">
              <div class="reco-box">
                <div class="reco-label">推荐资源</div>
                <div v-if="reco.resource_list.length === 0" class="reco-text">暂无资源推荐</div>
                <div v-for="item in reco.resource_list" :key="item.id" class="reco-item">
                  {{ item.title }} · {{ item.type }}
                </div>
              </div>
              <div class="reco-box">
                <div class="reco-label">推荐练习</div>
                <div v-if="reco.practice_list.length === 0" class="reco-text">暂无练习推荐</div>
                <div v-for="item in reco.practice_list" :key="item.question_id" class="reco-item">
                  {{ item.type }} · 难度 {{ Math.round((item.difficulty || 0) * 100) }}
                </div>
              </div>
            </div>

            <div class="action-row">
              <el-button @click="resetReco">关闭</el-button>
              <el-button type="primary" :disabled="!recommendedTarget" @click="goToRecommended">前往推荐知识点</el-button>
            </div>
          </div>
        </el-card>
      </section>

      <section class="panel-card content-panel">
        <div class="content-steps">
          <SimpleStepsBar :items="['先看总览', '再进图谱', '再去学习内容页', '单独补问卷', '单独看报告']" />
        </div>
        <div class="tab-panel">
          <OverviewPane :subject="subject" :grade="grade" />

          <div class="feature-grid">
            <button class="feature-card" @click="openGraphWorkspace">
              <strong>知识图谱</strong>
              <span>查看知识结构，定位当前知识点，再进入学习内容页。</span>
            </button>
            <button class="feature-card" @click="router.push({ path: '/student/questionnaire', query: { subject: subject || undefined } })">
              <strong>补充问卷</strong>
              <span>单独填写学习偏好和当前状态，不再和其它内容混在一起。</span>
            </button>
            <button class="feature-card" @click="router.push({ path: '/student/report', query: { subject: subject || undefined } })">
              <strong>学习报告</strong>
              <span>单独查看画像结果、阶段变化和下一步建议。</span>
            </button>
            <button class="feature-card" :disabled="!recommendedTargetId" @click="goToRecommended">
              <strong>推荐知识点</strong>
              <span>{{ recommendedTarget ? `${recommendedTarget.code} ${recommendedTarget.title}` : "等待系统推荐结果" }}</span>
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

.content-steps {
  padding: 14px 16px 0;
  border-bottom: 1px solid var(--app-border);
  padding-bottom: 14px;
  background: #ffffff;
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
