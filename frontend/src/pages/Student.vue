<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import { getRole, getUsername } from "../token";

import ResourcePane from "../components/ResourcePane.vue";
import MiniQuizPane from "../components/MiniQuizPane.vue";
import QuizPane from "../components/QuizPane.vue";
import OverviewPane from "../components/OverviewPane.vue";
import KnowledgeGraphPane from "../components/KnowledgeGraphPane.vue";
import LearnerReportPane from "../components/LearnerReportPane.vue";

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
const isStudent = computed(() => getRole() === "student");
const lastVideoRefreshAt = ref<number>(0);
const route = useRoute();
const router = useRouter();
const studentSections = ["overview", "graph", "resource", "quiz", "practice", "report"] as const;
const activeSection = computed<"overview" | "graph" | "resource" | "quiz" | "practice" | "report">({
  get() {
    if (route.path.startsWith("/student/")) {
      const seg = route.path.split("/")[2] as "overview" | "graph" | "resource" | "quiz" | "practice" | "report";
      if (studentSections.includes(seg)) return seg;
    }
    return "overview";
  },
  set(value) {
    const target = `/student/${String(value || "overview")}`;
    if (route.path !== target) router.push(target);
  },
});

const currentKp = computed(() => kps.value.find((k) => k.id === currentKpId.value) ?? null);
const recommendedTargetId = computed<number | null>(() => reco.value?.target_kp?.id ?? null);
const recommendedTarget = computed<KP | null>(() => {
  if (!recommendedTargetId.value) return null;
  return kps.value.find((item) => item.id === recommendedTargetId.value) ?? null;
});
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
    const data = await getWithCache("/graph/courses");
    courses.value = data ?? [];
    if (!subject.value && courses.value.length) subject.value = courses.value[0].title;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
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

function onVideoProgress() {
  if (!isStudent.value) return;
  const now = Date.now();
  if (now - lastVideoRefreshAt.value < 10_000) return;
  lastVideoRefreshAt.value = now;
  refreshMastery();
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
  router.push({
    path: "/student/graph-workspace",
    query: {
      subject: subject.value,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
    },
  });
}

onMounted(async () => {
  try {
    await loadCourses();
    await loadKps();
    await refreshMastery();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载失败（请先在管理端准备课程与知识点数据）");
  }
});
</script>

<template>
  <div class="page-shell">
    <div v-if="isStudent" class="page-grid">
      <section class="panel-card info-panel">
        <div class="panel-title">学习导航</div>
        <div v-if="courses.length === 0" style="margin-bottom: 8px">
          <el-alert type="warning" title="暂无课程，请先在管理员端配置课程" :closable="false" show-icon />
        </div>
        <div class="control-row">
          <el-select v-model="subject" placeholder="选择课程" style="width: 100%" @change="onCourseChange">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
          </el-select>
        </div>
        <el-select
          v-model="currentKpId"
          placeholder="选择知识点"
          style="width: 100%"
          :disabled="courses.length === 0 || kps.length === 0"
          @change="onKpChange"
        >
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
        </el-select>

        <div v-if="currentKp" class="kp-meta">
          <div class="kp-code">{{ currentKp.code }}</div>
          <div class="kp-title">{{ currentKp.title }}</div>
          <el-text type="info">{{ currentKp.description || "暂无描述" }}</el-text>
        </div>

        <div v-if="currentKpId" class="kp-progress">
          <div class="metric-head">
            <span>当前知识点掌握度</span>
            <strong>{{ Math.round(mastery * 100) }}%</strong>
          </div>
          <el-progress :percentage="Math.round(mastery * 100)" />
        </div>

        <div class="action-row">
          <el-button type="primary" :disabled="!currentKpId" @click="refreshMastery">刷新掌握度</el-button>
          <el-button type="success" :disabled="!currentKpId" @click="getReco">生成学习建议</el-button>
          <el-button :disabled="!currentKpId" @click="openGraphWorkspace">打开知识图谱</el-button>
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
              <el-tag size="small" type="info">{{ reco.persona_strategy_tag }}</el-tag>
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
                <div class="reco-item">推荐动作：{{ reco.remedy?.action || "current" }}</div>
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
        <el-tabs v-model="activeSection" type="border-card" class="dify-tabs">
          <el-tab-pane label="课程总览" name="overview">
            <OverviewPane :subject="subject" :grade="grade" />
          </el-tab-pane>
          <el-tab-pane label="知识图谱" name="graph">
            <div class="graph-showcase">
              <section class="graph-showcase__intro">
                <div class="graph-showcase__copy">
                  <div class="graph-showcase__kicker">Knowledge Graph Workspace</div>
                  <div class="graph-showcase__title">知识图谱工作区</div>
                  <div class="graph-showcase__text">
                    把课程结构、前置依赖、节点资源和系统推荐放到同一块工作台里。进入全屏后可以按知识点查看学习资源、任务、小测和推荐路径。
                  </div>
                </div>
                <div class="graph-showcase__signal">
                  <div class="graph-showcase__signal-label">当前知识状态</div>
                  <div class="graph-showcase__signal-value">{{ Math.round(mastery * 100) }}%</div>
                  <el-progress :percentage="Math.round(mastery * 100)" :show-text="false" />
                  <div class="graph-showcase__signal-meta">
                    <span>{{ masteryStageLabel }}</span>
                    <span>{{ recommendedTarget ? "已生成推荐目标" : "建议先生成学习建议" }}</span>
                  </div>
                </div>
              </section>

              <section class="graph-showcase__stats">
                <div class="graph-showcase__stat-card">
                  <span>当前课程</span>
                  <strong>{{ subject || "未选择课程" }}</strong>
                </div>
                <div class="graph-showcase__stat-card">
                  <span>当前知识点</span>
                  <strong>{{ currentKp ? `${currentKp.code} ${currentKp.title}` : "未选择知识点" }}</strong>
                </div>
                <div class="graph-showcase__stat-card">
                  <span>当前掌握阶段</span>
                  <strong>{{ masteryStageLabel }}</strong>
                </div>
                <div class="graph-showcase__stat-card">
                  <span>推荐目标</span>
                  <strong>{{ recommendedTarget ? `${recommendedTarget.code} ${recommendedTarget.title}` : "暂未生成" }}</strong>
                </div>
              </section>

              <section class="graph-showcase__workspace">
                <div class="graph-showcase__preview">
                  <div class="graph-showcase__preview-head">
                    <div>
                      <div class="graph-showcase__preview-kicker">Workspace Preview</div>
                      <div class="graph-showcase__preview-title">全屏图谱工作台预览</div>
                    </div>
                    <el-tag size="small" type="info">全屏交互模式</el-tag>
                  </div>

                  <div class="graph-showcase__preview-stage">
                    <div class="graph-showcase__preview-orbit graph-showcase__preview-orbit--center">
                      <span>{{ currentKp?.code || "CURRENT" }}</span>
                      <strong>{{ currentKp?.title || "当前知识点" }}</strong>
                    </div>
                    <div class="graph-showcase__preview-orbit graph-showcase__preview-orbit--upper">
                      <span>Prerequisite</span>
                      <strong>前置知识</strong>
                    </div>
                    <div class="graph-showcase__preview-orbit graph-showcase__preview-orbit--lower">
                      <span>Related</span>
                      <strong>关联拓展</strong>
                    </div>
                    <div class="graph-showcase__preview-orbit graph-showcase__preview-orbit--right">
                      <span>Recommendation</span>
                      <strong>{{ recommendedTarget?.title || "推荐目标" }}</strong>
                    </div>
                    <div class="graph-showcase__preview-line graph-showcase__preview-line--upper"></div>
                    <div class="graph-showcase__preview-line graph-showcase__preview-line--lower"></div>
                    <div class="graph-showcase__preview-line graph-showcase__preview-line--right"></div>
                  </div>

                  <div class="graph-showcase__preview-foot">
                    <span><i class="graph-dot graph-dot--mastered"></i>已掌握</span>
                    <span><i class="graph-dot graph-dot--learning"></i>学习中</span>
                    <span><i class="graph-dot graph-dot--risk"></i>风险</span>
                    <span><i class="graph-dot graph-dot--idle"></i>未开始</span>
                  </div>
                </div>

                <div class="graph-showcase__aside">
                  <div class="graph-showcase__action-card">
                    <div class="graph-showcase__action-kicker">Launch</div>
                    <div class="graph-showcase__action-title">进入知识图谱工作区</div>
                    <div class="graph-showcase__action-text">
                      在全屏界面里集中查看知识关系、节点内容、掌握状态和系统推荐，不再被其他模块挤压。
                    </div>
                    <div class="graph-showcase__actions">
                      <el-button type="primary" size="large" :disabled="!currentKpId" @click="openGraphWorkspace">
                        打开全屏知识图谱
                      </el-button>
                      <el-button size="large" :disabled="!recommendedTargetId" @click="goToRecommended">
                        直达推荐知识点
                      </el-button>
                    </div>
                  </div>

                  <div class="graph-showcase__guide-card">
                    <div class="graph-showcase__guide-title">进入后可以做什么</div>
                    <div class="graph-showcase__guide-list">
                      <div class="graph-showcase__guide-item">查看当前知识点的前置关系和后续路径</div>
                      <div class="graph-showcase__guide-item">点击节点查看资源、任务、练习和小测</div>
                      <div class="graph-showcase__guide-item">根据掌握状态定位薄弱点和系统推荐点</div>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </el-tab-pane>
          <el-tab-pane label="学习资源" name="resource">
            <ResourcePane :kp-id="currentKpId" @progress-updated="onVideoProgress" />
          </el-tab-pane>
          <el-tab-pane label="小测" name="quiz">
            <MiniQuizPane :kp-id="currentKpId" @mastery-updated="refreshMastery" />
          </el-tab-pane>
          <el-tab-pane label="练习/测验" name="practice">
            <QuizPane :kp-id="currentKpId" @mastery-updated="refreshMastery" />
          </el-tab-pane>
          <el-tab-pane label="学习报告" name="report">
            <LearnerReportPane :subject="subject" :grade="grade" />
          </el-tab-pane>
        </el-tabs>
      </section>
    </div>

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
      <el-tabs v-model="activeSection" type="border-card" class="dify-tabs">
        <el-tab-pane label="知识图谱" name="graph">
          <KnowledgeGraphPane :subject="subject" :grade="grade" :current-kp-id="currentKpId" />
        </el-tab-pane>
        <el-tab-pane label="学习资源" name="resource">
          <ResourcePane :kp-id="currentKpId" />
        </el-tab-pane>
        <el-tab-pane label="小测预览" name="quiz">
          <MiniQuizPane :kp-id="currentKpId" preview />
        </el-tab-pane>
        <el-tab-pane label="练习预览" name="practice">
          <QuizPane :kp-id="currentKpId" preview />
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>

</template>

<style scoped>
.page-shell {
  display: grid;
  gap: 24px;
}

.page-grid {
  display: grid;
  grid-template-columns: minmax(300px, 360px) 1fr;
  gap: 24px;
  align-items: start;
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--app-ink);
}

.info-panel {
  padding: 20px;
}

.content-panel {
  overflow: hidden;
}

.control-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.kp-meta {
  margin-top: 16px;
  padding: 14px;
  background: #f8fafc;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
  display: grid;
  gap: 4px;
}

.kp-code {
  font-size: 12px;
  color: #557291;
}

.kp-title {
  font-weight: 700;
  color: var(--app-ink);
}

.kp-progress {
  margin-top: 16px;
  display: grid;
  gap: 8px;
}

.metric-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: #5f7894;
}

.metric-head strong {
  color: var(--app-ink);
}

.action-row {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.sub-card {
  margin-top: 16px;
  border-radius: var(--app-radius);
}

.graph-showcase {
  display: grid;
  gap: 18px;
}

.graph-showcase__intro {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.7fr);
  gap: 16px;
}

.graph-showcase__copy,
.graph-showcase__signal,
.graph-showcase__stat-card,
.graph-showcase__action-card,
.graph-showcase__guide-card {
  border-radius: 22px;
  border: 1px solid #dce7f0;
  background: linear-gradient(180deg, #fbfdff, #f5f9fd);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.graph-showcase__copy {
  padding: 24px 26px;
  display: grid;
  gap: 10px;
  align-content: start;
}

.graph-showcase__kicker,
.graph-showcase__preview-kicker,
.graph-showcase__action-kicker {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #6a88a8;
}

.graph-showcase__title {
  font-size: 28px;
  line-height: 1.08;
  font-weight: 800;
  color: var(--app-ink);
}

.graph-showcase__text {
  max-width: 720px;
  font-size: 14px;
  line-height: 1.75;
  color: #57718f;
}

.graph-showcase__signal {
  padding: 22px;
  display: grid;
  gap: 10px;
  align-content: start;
}

.graph-showcase__signal-label {
  font-size: 12px;
  color: #6884a1;
}

.graph-showcase__signal-value {
  font-size: 34px;
  font-weight: 800;
  line-height: 1;
  color: var(--app-ink);
}

.graph-showcase__signal-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #6884a1;
}

.graph-showcase__stats {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.graph-showcase__stat-card {
  padding: 16px 18px;
  display: grid;
  gap: 6px;
}

.graph-showcase__stat-card span {
  font-size: 12px;
  color: #6884a1;
}

.graph-showcase__stat-card strong {
  font-size: 18px;
  line-height: 1.45;
  color: var(--app-ink);
}

.graph-showcase__workspace {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(0, 1.25fr) minmax(300px, 0.75fr);
}

.graph-showcase__preview {
  padding: 20px;
  border-radius: 28px;
  background:
    radial-gradient(circle at 16% 20%, rgba(107, 165, 255, 0.22), transparent 28%),
    radial-gradient(circle at 80% 82%, rgba(73, 118, 188, 0.18), transparent 24%),
    linear-gradient(135deg, #0b1830, #12355d 58%, #174877);
  color: #f5f9ff;
  display: grid;
  gap: 16px;
  min-height: 360px;
}

.graph-showcase__preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.graph-showcase__preview-title {
  margin-top: 4px;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.1;
}

.graph-showcase__preview-stage {
  position: relative;
  min-height: 220px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.06), transparent 52%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  overflow: hidden;
}

.graph-showcase__preview-orbit {
  position: absolute;
  display: grid;
  align-content: center;
  justify-items: center;
  text-align: center;
  border-radius: 999px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 38px rgba(7, 17, 34, 0.24);
}

.graph-showcase__preview-orbit span {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(227, 238, 252, 0.72);
}

.graph-showcase__preview-orbit strong {
  margin-top: 6px;
  font-size: 14px;
  line-height: 1.35;
  max-width: 150px;
}

.graph-showcase__preview-orbit--center {
  left: 50%;
  top: 50%;
  width: 180px;
  height: 180px;
  transform: translate(-50%, -50%);
  background: rgba(106, 167, 255, 0.18);
  border-color: rgba(157, 201, 255, 0.42);
}

.graph-showcase__preview-orbit--upper {
  left: 18%;
  top: 16%;
  width: 126px;
  height: 126px;
}

.graph-showcase__preview-orbit--lower {
  left: 20%;
  bottom: 12%;
  width: 126px;
  height: 126px;
}

.graph-showcase__preview-orbit--right {
  right: 11%;
  top: 50%;
  width: 152px;
  height: 152px;
  transform: translateY(-50%);
  background: rgba(255, 208, 112, 0.14);
  border-color: rgba(255, 227, 158, 0.34);
}

.graph-showcase__preview-line {
  position: absolute;
  background: linear-gradient(90deg, rgba(182, 211, 255, 0.2), rgba(243, 248, 255, 0.78), rgba(182, 211, 255, 0.2));
  transform-origin: left center;
  height: 1px;
}

.graph-showcase__preview-line--upper {
  left: 32%;
  top: 34%;
  width: 190px;
  transform: rotate(19deg);
}

.graph-showcase__preview-line--lower {
  left: 34%;
  bottom: 30%;
  width: 180px;
  transform: rotate(-15deg);
}

.graph-showcase__preview-line--right {
  left: 57%;
  top: 50%;
  width: 180px;
}

.graph-showcase__preview-foot {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  align-items: center;
  font-size: 12px;
  color: rgba(230, 239, 251, 0.86);
}

.graph-dot {
  display: inline-flex;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  margin-right: 7px;
}

.graph-dot--mastered {
  background: #2dcc84;
}

.graph-dot--learning {
  background: #4c92ff;
}

.graph-dot--risk {
  background: #ff9553;
}

.graph-dot--idle {
  background: #90a7c0;
}

.graph-showcase__aside {
  display: grid;
  gap: 16px;
  align-content: start;
}

.graph-showcase__action-card,
.graph-showcase__guide-card {
  padding: 20px;
  display: grid;
  gap: 10px;
}

.graph-showcase__action-title,
.graph-showcase__guide-title {
  font-size: 20px;
  line-height: 1.2;
  font-weight: 800;
  color: var(--app-ink);
}

.graph-showcase__action-text {
  font-size: 14px;
  line-height: 1.75;
  color: #5c7692;
}

.graph-showcase__actions {
  margin-top: 6px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.graph-showcase__guide-list {
  display: grid;
  gap: 10px;
}

.graph-showcase__guide-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: #f2f7fb;
  border: 1px solid #dde9f2;
  color: #486480;
  line-height: 1.65;
}

.reco-body {
  display: grid;
  gap: 14px;
}

.reco-summary {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.reco-summary > div,
.reco-box {
  padding: 12px;
  border-radius: 16px;
  background: #f7fafc;
  border: 1px solid #e1e9f0;
}

.reco-label {
  font-size: 12px;
  color: #5d7693;
}

.reco-highlight {
  padding: 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, #15395e, #29577d);
  color: #f8fbff;
  display: grid;
  gap: 6px;
}

.reco-target {
  font-size: 22px;
  font-weight: 800;
}

.reco-text {
  font-size: 13px;
  line-height: 1.65;
}

.reco-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.reco-item {
  padding: 8px 0;
  border-bottom: 1px dashed #d8e4ef;
  font-size: 13px;
  color: var(--app-ink);
}

.dify-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
  padding: 0 16px;
}

.dify-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--app-border);
}

.dify-tabs :deep(.el-tabs__content) {
  padding: 16px;
}

@media (max-width: 1100px) {
  .page-grid {
    grid-template-columns: 1fr;
  }

  .graph-showcase__intro,
  .graph-showcase__workspace,
  .graph-showcase__stats,
  .reco-summary,
  .reco-grid {
    grid-template-columns: 1fr;
  }
  .graph-showcase__preview {
    min-height: 300px;
  }

  .graph-showcase__preview-orbit--center {
    width: 152px;
    height: 152px;
  }

  .graph-showcase__preview-orbit--upper,
  .graph-showcase__preview-orbit--lower {
    width: 108px;
    height: 108px;
  }

  .graph-showcase__preview-orbit--right {
    width: 124px;
    height: 124px;
    right: 6%;
  }

  .graph-showcase__preview-line--upper,
  .graph-showcase__preview-line--lower,
  .graph-showcase__preview-line--right {
    width: 120px;
  }
}
</style>
