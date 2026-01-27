<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import NotePane from "../components/NotePane.vue";
import ResourcePane from "../components/ResourcePane.vue";
import WebcamDifficulty from "../components/WebcamDifficulty.vue";
import MiniQuizPane from "../components/MiniQuizPane.vue";
import QuizPane from "../components/QuizPane.vue";
import OverviewPane from "../components/OverviewPane.vue";
import InterviewPane from "../components/InterviewPane.vue";
import { getRole, getUsername } from "../token";

type KP = { id: number; code: string; title: string; description: string; subject: string; grade: string };

const subject = ref("数据结构");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);

const mastery = ref<number>(0);
const reco = ref<any | null>(null);
const unlockInfo = ref<{ can_unlock_next: boolean; next_candidates: number[] }>({
  can_unlock_next: false,
  next_candidates: [],
});
const isStudent = computed(() => getRole() === "student");
const lastVideoRefreshAt = ref<number>(0);
const route = useRoute();
const router = useRouter();
const activeSection = computed<"overview" | "resource" | "quiz" | "practice" | "notes" | "interview">({
  get: () => {
    if (route.path.startsWith("/student/")) {
      const seg = route.path.split("/")[2];
      if (seg === "overview" || seg === "quiz" || seg === "practice" || seg === "notes" || seg === "interview") return seg;
    }
    return "resource";
  },
  set: (value) => {
    router.push(`/student/${value}`);
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
const diagnosisSignals = computed(() => {
  const reasons = reco.value?.diagnosis?.reasons ?? [];
  const labels: Record<string, string> = {
    quiz_accuracy: "小测正确率",
    practice_accuracy: "练习正确率",
    practice_completed: "练习完成",
    mastery: "掌握度",
    expression_difficulty: "表情困难度",
  };
  return reasons.map((r: any) => {
    const signal = String(r.signal ?? "");
    const value = r.value;
    const threshold = r.threshold;
    let pass = false;
    if (typeof threshold === "boolean") {
      pass = Boolean(value) === threshold;
    } else if (typeof value === "number" && typeof threshold === "number") {
      pass = signal === "expression_difficulty" ? value <= threshold : value >= threshold;
    }
    return {
      signal,
      label: labels[signal] ?? signal,
      value,
      threshold,
      pass,
    };
  });
});

function kpStorageKey() {
  const username = getUsername() || localStorage.getItem("da_last_user") || "guest";
  return `da_kp_${username}_${subject.value}`;
}

async function loadKps() {
  const res = await api.get(`/graph/kps?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
  kps.value = res.data;
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
}

async function refreshMastery() {
  if (!currentKpId.value) return;
  const res = await api.get(`/eval/mastery?kp_id=${currentKpId.value}`);
  mastery.value = Number(res.data.value);
  await refreshUnlockInfo();
}

async function refreshUnlockInfo() {
  if (!currentKpId.value) return;
  try {
    const res = await api.get(`/reco?kp_id=${currentKpId.value}`);
    unlockInfo.value = res.data?.unlock ?? unlockInfo.value;
  } catch {
    // keep previous unlock info
  }
}

async function getReco() {
  if (!currentKpId.value) return;
  const res = await api.get(`/reco?kp_id=${currentKpId.value}`);
  reco.value = res.data;
  unlockInfo.value = res.data?.unlock ?? unlockInfo.value;
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
  <el-row v-if="isStudent" :gutter="16">
    <el-col :span="8">
      <el-card class="panel-card">
        <template #header>知识点与掌握度</template>
        <div style="display: flex; gap: 8px; margin-bottom: 8px">
          <el-select v-model="subject" style="width: 180px" @change="loadKps">
            <el-option label="数据结构" value="数据结构" />
            <el-option label="计算机组成原理" value="计算机组成原理" />
            <el-option label="操作系统" value="操作系统" />
            <el-option label="计算机网络" value="计算机网络" />
          </el-select>
        </div>
        <el-select v-model="currentKpId" placeholder="选择知识点" style="width: 100%" @change="onKpChange">
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id">
            <span style="display: inline-flex; align-items: center; gap: 6px">
              <span>{{ isLocked(kp.id) ? "🔒" : "🔓" }}</span>
              <span>{{ kp.code }} {{ kp.title }}</span>
            </span>
          </el-option>
        </el-select>
        <div style="margin-top: 10px">
          <div style="font-weight: 600">{{ currentKp?.title ?? "" }}</div>
          <el-text type="info">{{ currentKp?.description ?? "" }}</el-text>
        </div>
        <div style="margin-top: 10px">
          <el-progress :percentage="Math.round(mastery * 100)" />
        </div>
        <div style="margin-top: 10px; display: flex; gap: 8px">
          <el-button type="primary" @click="refreshMastery">刷新掌握度</el-button>
          <el-button type="success" @click="getReco">推荐下一步</el-button>
        </div>
        <el-card v-if="reco" style="margin-top: 12px" shadow="never">
          <template #header>推荐结果</template>
          <div style="display: grid; gap: 6px">
            <el-text>掌握度：{{ Number(reco.diagnosis?.mastery ?? 0).toFixed(2) }}</el-text>
            <el-text>可解锁：{{ reco.unlock?.can_unlock_next ? "是" : "否" }}</el-text>
            <el-text v-if="recommendedNext">
              推荐知识点：{{ recommendedNext.code }} {{ recommendedNext.title }}
            </el-text>
            <el-text v-else>推荐知识点：暂无</el-text>
            <div style="margin-top: 6px">
              <div style="font-weight: 600; margin-bottom: 4px">解锁依据</div>
              <div style="display: grid; gap: 4px">
                <div v-for="item in diagnosisSignals" :key="item.signal" style="display: flex; align-items: center; justify-content: space-between">
                  <div style="font-size: 12px">{{ item.label }}</div>
                  <div style="display: flex; align-items: center; gap: 6px">
                    <el-text type="info" style="font-size: 12px">
                      {{
                        typeof item.value === "number"
                          ? item.value.toFixed(2)
                          : item.value === null || item.value === undefined
                            ? "无"
                            : String(item.value)
                      }}
                      /
                      {{
                        typeof item.threshold === "number"
                          ? item.threshold.toFixed(2)
                          : item.threshold === null || item.threshold === undefined
                            ? "无"
                            : String(item.threshold)
                      }}
                    </el-text>
                    <el-tag size="small" :type="item.pass ? 'success' : 'warning'">
                      {{ item.pass ? "达标" : "未达标" }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 6px">
              <el-button type="default" @click="skipReco">跳过</el-button>
              <el-button type="primary" :disabled="!recommendedNextId || !unlockInfo.can_unlock_next" @click="goToRecommended">
                立即前往
              </el-button>
            </div>
          </div>
        </el-card>
      </el-card>
    </el-col>

    <el-col :span="16">
      <el-tabs v-model="activeSection" type="border-card" class="panel-card">
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
        <el-tab-pane label="模拟复试" name="interview">
          <InterviewPane :kp-id="currentKpId" />
        </el-tab-pane>
        <el-tab-pane label="笔记" name="notes">
          <NotePane :kp-id="currentKpId" />
        </el-tab-pane>
      </el-tabs>
    </el-col>
  </el-row>

  <el-row v-else :gutter="16">
    <el-col :span="24">
      <el-card class="panel-card">
        <template #header>学习资源与练习题（管理端预览）</template>
        <div style="display: flex; gap: 8px; margin-bottom: 8px">
          <el-select v-model="subject" style="width: 180px" @change="loadKps">
            <el-option label="数据结构" value="数据结构" />
            <el-option label="计算机组成原理" value="计算机组成原理" />
            <el-option label="操作系统" value="操作系统" />
            <el-option label="计算机网络" value="计算机网络" />
          </el-select>
          <el-select v-model="currentKpId" placeholder="选择知识点" style="width: 320px" @change="onKpChange">
            <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id">
              <span style="display: inline-flex; align-items: center; gap: 6px">
                <span>{{ isLocked(kp.id) ? "🔒" : "🔓" }}</span>
                <span>{{ kp.code }} {{ kp.title }}</span>
              </span>
            </el-option>
          </el-select>
        </div>
        <el-tabs v-model="activeSection" type="border-card" class="panel-card">
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
      </el-card>
    </el-col>
  </el-row>

  <div
    v-if="isStudent"
    class="float-panel"
    style="position: fixed; left: var(--float-x, auto); top: var(--float-y, auto); right: 20px; bottom: 20px; width: var(--float-w, 420px); z-index: 1000"
  >
    <WebcamDifficulty :kp-id="currentKpId" />
  </div>
</template>
