<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import { getRole, getUsername } from "../token";

import NotePane from "../components/NotePane.vue";
import ResourcePane from "../components/ResourcePane.vue";
import WebcamDifficulty from "../components/WebcamDifficulty.vue";
import MiniQuizPane from "../components/MiniQuizPane.vue";
import QuizPane from "../components/QuizPane.vue";
import OverviewPane from "../components/OverviewPane.vue";

// 类型定义
type KP = { id: number; code: string; title: string; description: string; subject: string; grade: string };
type Course = { id: number; code: string; title: string };
type EvidenceItem = { key: string; label: string; ok: boolean };
type RemedySuggestion = string | null;

type RecoEvidence = {
  items: Record<string, boolean>;
  missing: string[];
};

type RecoRemedy = {
  action: string;
  reason?: string;
};

type RecoUnlock = {
  can_unlock_next: boolean;
  next_candidates: number[];
};

type RecoDiagnosis = {
  mastery: number;
};

type RecoData = {
  diagnosis?: RecoDiagnosis;
  unlock?: RecoUnlock;
  evidence?: RecoEvidence;
  remedy?: RecoRemedy;
};

// 响应式数据
const courses = ref<Course[]>([]);
const subject = ref<string>("");
const grade = ref<string>("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);

const mastery = ref<number>(0);
const reco = ref<RecoData | null>(null);
const unlockInfo = ref<RecoUnlock>({
  can_unlock_next: false,
  next_candidates: [],
});
const isStudent = computed(() => getRole() === "student");
const lastVideoRefreshAt = ref<number>(0);
const route = useRoute();
const router = useRouter();
const studentSections = ["overview", "resource", "quiz", "practice", "notes"] as const;
const activeSection = computed<"overview" | "resource" | "quiz" | "practice" | "notes">({
  get() {
    if (route.path.startsWith("/student/")) {
      const seg = route.path.split("/")[2] as "overview" | "resource" | "quiz" | "practice" | "notes";
      if (studentSections.includes(seg)) return seg;
    }
    return "resource";
  },
  set(value) {
    const target = `/student/${String(value || "resource")}`;
    if (route.path !== target) router.push(target);
  },
});

const currentKp = computed(() => kps.value.find((k) => k.id === currentKpId.value) ?? null);
const recommendedNextId = computed<number | null>(() => {
  const ids = reco.value?.unlock?.next_candidates as number[] | undefined;
  if (!ids || ids.length === 0) return null;
  return ids[0];
});
const recommendedNext = computed<KP | null>(() => {
  if (!recommendedNextId.value) return null;
  return kps.value.find((k) => k.id === recommendedNextId.value) ?? null;
});

const evidenceItems = computed<EvidenceItem[]>(() => {
  const items = reco.value?.evidence?.items ?? {};
  const labels: Record<string, string> = {
    mcq_correct: "选择题 ≥ 1",
    blank_correct: "填空题 ≥ 1",
    medium_correct: "中等题 ≥ 1",
    hard_or_two_medium: "困难题 ≥ 1 或 中等题 ≥ 2",
  };
  return Object.keys(labels).map((key) => ({
    key,
    label: labels[key],
    ok: Boolean(items[key]),
  }));
});

const evidenceMissing = computed<string[]>(() => {
  const missing = reco.value?.evidence?.missing ?? [];
  const map: Record<string, string> = {
    mcq_correct: "选择题",
    blank_correct: "填空题",
    medium_correct: "中等题",
    hard_or_two_medium: "困难题/中等题",
  };
  return missing.map((m: string) => map[m] ?? m);
});

const remedySuggestion = computed<RemedySuggestion>(() => {
  const r = reco.value?.remedy;
  if (!r) return null;
  if (r.action === "retry_same_level") return "可能是失误，建议再做一道同难度题复核。";
  if (r.action === "remedial_path") return "建议先进入补救通道，回顾关键概念。";
  return null;
});

function kpStorageKey() {
  const username = getUsername() || localStorage.getItem("da_last_user") || "guest";
  return `da_kp_${username}_${subject.value}`;
}

async function loadCourses() {
  try {
    const data = await getWithCache("/graph/courses");
    courses.value = data ?? [];
    if (!subject.value && courses.value.length) {
      subject.value = courses.value[0].title;
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

async function loadKps() {
  if (!subject.value) return;
  try {
    const data = await getWithCache("/graph/kps", {
      subject: subject.value,
      grade: grade.value
    });
    kps.value = data;
    const saved = localStorage.getItem(kpStorageKey());
    if (saved) {
      const savedId = Number(saved);
      const exists = kps.value.some((k) => k.id === savedId);
      if (exists) {
        currentKpId.value = savedId;
        return;
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
    const data = await getWithCache("/eval/mastery", {
      kp_id: currentKpId.value
    });
    mastery.value = Number(data.value);
    await refreshUnlockInfo();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "刷新掌握度失败");
  }
}

async function refreshUnlockInfo() {
  if (!currentKpId.value) return;
  try {
    const data = await getWithCache("/reco", {
      kp_id: currentKpId.value
    });
    unlockInfo.value = data?.unlock ?? unlockInfo.value;
  } catch {
    // keep previous unlock info
  }
}

async function getReco() {
  if (!currentKpId.value) return;
  try {
    const data = await getWithCache("/reco", {
      kp_id: currentKpId.value
    });
    reco.value = data;
    unlockInfo.value = data?.unlock ?? unlockInfo.value;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "获取推荐失败");
  }
}

async function goToRecommended() {
  if (!recommendedNextId.value) return;
  currentKpId.value = recommendedNextId.value;
  await refreshMastery();
  reco.value = null;
}

function skipReco() {
  reco.value = null;
}

function isLocked(kpId: number): boolean {
  const nextIds = unlockInfo.value?.next_candidates ?? [];
  if (!nextIds.includes(kpId)) return false;
  return !unlockInfo.value?.can_unlock_next;
}

function onVideoProgress() {
  if (!isStudent.value) return;
  const now = Date.now();
  if (now - lastVideoRefreshAt.value < 10_000) return;
  lastVideoRefreshAt.value = now;
  refreshMastery();
}

onMounted(async () => {
  try {
    await loadCourses();
    await loadKps();
    await refreshMastery();
    await refreshUnlockInfo();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载失败（请先在管理端 Seed 数据）");
  }
});

function onKpChange() {
  if (currentKpId.value) {
    localStorage.setItem(kpStorageKey(), String(currentKpId.value));
  }
  refreshMastery();
}
</script>

<template>
  <div class="page-shell">
    <div v-if="isStudent" class="page-grid">
      <section class="panel-card info-panel">
        <div class="panel-title">知识点与掌握度</div>
        <div v-if="courses.length === 0" style="margin-bottom: 8px">
          <el-alert type="warning" title="暂无课程，请在管理端添加课程" show-icon />
        </div>
        <div class="control-row">
          <el-select v-model="subject" style="width: 200px" @change="loadKps">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
          </el-select>
        </div>
        <el-select v-model="currentKpId" placeholder="选择知识点" style="width: 100%" @change="onKpChange">
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id">
            <span class="kp-option">
              <span>{{ isLocked(kp.id) ? "🔒" : "🔓" }}</span>
              <span>{{ kp.code }} {{ kp.title }}</span>
            </span>
          </el-option>
        </el-select>
        <div class="kp-meta">
          <div class="kp-title">{{ currentKp?.title ?? "" }}</div>
          <el-text type="info">{{ currentKp?.description ?? "" }}</el-text>
        </div>
        <div class="kp-progress">
          <el-progress :percentage="Math.round(mastery * 100)" />
        </div>
        <div class="action-row">
          <el-button type="primary" @click="refreshMastery">刷新掌握度</el-button>
          <el-button type="success" @click="getReco">推荐下一步</el-button>
        </div>
        <el-card v-if="reco" class="sub-card" shadow="never">
          <template #header>推荐结果</template>
          <div class="reco-body">
            <el-text>掌握度：{{ Number(reco.diagnosis?.mastery ?? 0).toFixed(2) }}</el-text>
            <el-text>可解锁：{{ reco.unlock?.can_unlock_next ? "是" : "否" }}</el-text>
            <el-text v-if="recommendedNext">
              推荐知识点：{{ recommendedNext.code }} {{ recommendedNext.title }}
            </el-text>
            <el-text v-else>推荐知识点：暂无</el-text>

            <div class="reco-section">
              <div class="reco-title">证据清单</div>
              <div class="reco-list">
                <div v-for="item in evidenceItems" :key="item.key" class="reco-item">
                  <div class="reco-label">{{ item.label }}</div>
                  <el-tag size="small" :type="item.ok ? 'success' : 'warning'">
                    {{ item.ok ? "已满足" : "缺失" }}
                  </el-tag>
                </div>
              </div>
              <el-text v-if="evidenceMissing.length" type="warning" style="font-size: 12px">
                缺失：{{ evidenceMissing.join("，") }}
              </el-text>
              <el-text v-else type="success" style="font-size: 12px">已满足全部证据</el-text>
            </div>

            <div v-if="remedySuggestion" class="reco-section">
              <div class="reco-title">补救建议</div>
              <el-alert type="info" :title="remedySuggestion" show-icon />
            </div>

            <div class="action-row">
              <el-button type="default" @click="skipReco">跳过</el-button>
              <el-button type="primary" :disabled="!recommendedNextId || !unlockInfo.can_unlock_next" @click="goToRecommended">
                立即前往
              </el-button>
            </div>
          </div>
        </el-card>
      </section>

      <section class="panel-card content-panel">
        <el-tabs v-model="activeSection" type="border-card" class="dify-tabs">
          <el-tab-pane label="学习总览" name="overview">
            <OverviewPane :subject="subject" :grade="grade" />
          </el-tab-pane>
          <el-tab-pane label="学习资源" name="resource">
            <ResourcePane :kp-id="currentKpId" @progress-updated="onVideoProgress" />
          </el-tab-pane>
          <el-tab-pane label="小测" name="quiz">
            <MiniQuizPane :kp-id="currentKpId" @mastery-updated="refreshMastery" />
          </el-tab-pane>
          <el-tab-pane label="练习题" name="practice">
            <QuizPane :kp-id="currentKpId" @mastery-updated="refreshMastery" />
          </el-tab-pane>
          <el-tab-pane label="笔记" name="notes">
            <NotePane :kp-id="currentKpId" />
          </el-tab-pane>
        </el-tabs>
      </section>
    </div>

    <section v-else class="panel-card">
      <div class="panel-title">学习资源与练习题（管理端预览）</div>
      <div v-if="courses.length === 0" style="margin-bottom: 8px">
        <el-alert type="warning" title="暂无课程，请在管理端添加课程" show-icon />
      </div>
      <div class="control-row">
        <el-select v-model="subject" style="width: 220px" @change="loadKps">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.title" />
        </el-select>
        <el-select v-model="currentKpId" placeholder="选择知识点" style="width: 320px" @change="onKpChange">
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id">
            <span class="kp-option">
              <span>{{ isLocked(kp.id) ? "🔒" : "🔓" }}</span>
              <span>{{ kp.code }} {{ kp.title }}</span>
            </span>
          </el-option>
        </el-select>
      </div>
      <el-tabs v-model="activeSection" type="border-card" class="dify-tabs">
        <el-tab-pane label="学习资源" name="resource">
          <ResourcePane :kp-id="currentKpId" />
        </el-tab-pane>
        <el-tab-pane label="小测预览" name="quiz">
          <MiniQuizPane :kp-id="currentKpId" preview />
        </el-tab-pane>
        <el-tab-pane label="练习题预览" name="practice">
          <QuizPane :kp-id="currentKpId" preview />
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>

  <div
    v-if="isStudent"
    class="float-panel"
    style="position: fixed; left: var(--float-x, auto); top: var(--float-y, auto); right: 20px; bottom: 20px; width: var(--float-w, 420px); z-index: 1000"
  >
    <WebcamDifficulty :kp-id="currentKpId" />
  </div>
</template>

<style scoped>
.page-shell {
  display: grid;
  gap: 24px;
}

.page-grid {
  display: grid;
  grid-template-columns: minmax(280px, 340px) 1fr;
  gap: 24px;
  align-items: start;
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--app-ink);
}

.control-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.kp-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.kp-meta {
  margin-top: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
}

.kp-title {
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--app-ink);
}

.kp-progress {
  margin-top: 16px;
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
  overflow: hidden;
}

.reco-body {
  display: grid;
  gap: 12px;
  padding: 12px;
}

.reco-section {
  margin-top: 8px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
}

.reco-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--app-ink);
}

.reco-list {
  display: grid;
  gap: 8px;
}

.reco-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  background: #ffffff;
  border-radius: var(--app-radius);
  border: 1px solid var(--app-border);
}

.reco-label {
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

/* 响应式调整 */
@media (max-width: 1100px) {
  .page-grid {
    grid-template-columns: 1fr;
  }
  
  .control-row {
    flex-direction: column;
  }
  
  .action-row {
    justify-content: center;
  }
}
</style>

