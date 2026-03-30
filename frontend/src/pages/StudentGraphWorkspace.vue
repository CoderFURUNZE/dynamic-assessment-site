<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api, getWithCache } from "../api";
import HoverTip from "../components/HoverTip.vue";
import KnowledgeGraphWorkspace from "../components/KnowledgeGraphWorkspace.vue";

type Course = { id: number; code: string; title: string };
type KP = { id: number; code: string; title: string };
type WorkspaceState = {
  kpCount: number;
  categoryCount: number;
  filteredCount: number;
  selectedType: "kp" | "category";
  selectedKpId: number | null;
  selectedCategory: string | null;
};

type RecoData = {
  target_kp: { id: number; code: string; title: string; chapter?: string; mastery?: number };
  reason_summary: string;
  recommendation_stage?: string;
  recommendation_stage_label?: string;
  advice_text: string;
  persona_strategy_tag: string;
  persona_label: string;
  dynamic_score: number;
  risk_level: string;
  evidence?: { missing?: string[] };
  remedy_path?: { blocked_prereqs?: number[]; path?: number[] };
  unlock?: { can_unlock_next: boolean; next_candidates: number[] };
};

type PathData = {
  kp_id: number;
  prereq_chain: number[];
  blocked_prereqs: number[];
  blocked_titles: string[];
  next_candidates: number[];
  next_titles: string[];
  can_unlock_next: boolean;
  path_summary: string;
};

const route = useRoute();
const router = useRouter();

const courses = ref<Course[]>([]);
const subject = ref<string>("");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);
const reco = ref<RecoData | null>(null);
const pathInfo = ref<PathData | null>(null);
const workspaceState = ref<WorkspaceState>({
  kpCount: 0,
  categoryCount: 0,
  filteredCount: 0,
  selectedType: "kp",
  selectedKpId: null,
  selectedCategory: null,
});

/** 路径 / 解锁 / 推荐 默认折叠，避免首页被多段说明撑得过长 */
const insightsOpen = ref<string[]>([]);

const currentKp = computed(() => kps.value.find((item) => item.id === currentKpId.value) ?? null);
const recommendedKp = computed(() => {
  const id = reco.value?.target_kp?.id;
  if (!id) return null;
  return kps.value.find((item) => item.id === id) ?? null;
});
const blockedPrereqTitles = computed(() => {
  const ids = reco.value?.remedy_path?.blocked_prereqs ?? [];
  return ids.map((id) => kps.value.find((item) => item.id === id)?.title).filter((item): item is string => !!item);
});
const recommendedPathIds = computed(() => {
  const path = reco.value?.remedy_path?.path ?? [];
  if (path.length) return path;
  return reco.value?.target_kp?.id ? [reco.value.target_kp.id] : [];
});
const recommendedPathTitles = computed(() =>
  recommendedPathIds.value
    .map((id) => {
      const kp = kps.value.find((item) => item.id === id);
      return kp ? `${kp.code} ${kp.title}` : "";
    })
    .filter((item): item is string => !!item),
);
const recommendationStageLabel = computed(() => {
  if (reco.value?.recommendation_stage_label) return reco.value.recommendation_stage_label;
  if (blockedPrereqTitles.value.length) return "先补前面的";
  if (reco.value?.unlock?.can_unlock_next) return "可以继续";
  return "系统建议";
});
const pathSummary = computed(() => pathInfo.value?.path_summary || reco.value?.reason_summary || "先看路径，再开始学习。");
const lockSummary = computed(() => {
  if (!pathInfo.value) return "";
  if (pathInfo.value.can_unlock_next) {
    return "当前知识点已解锁，可以继续进入后继知识点或直接开始学习。";
  }
  if (pathInfo.value.blocked_titles.length) {
    return `当前知识点被锁定，因为前置知识点尚未完成：${pathInfo.value.blocked_titles.join("、")}。`;
  }
  return "当前知识点暂未解锁，建议先补齐相关前置知识点。";
});
const lockNextTips = computed(() => {
  if (!pathInfo.value) return [];
  if (pathInfo.value.can_unlock_next) {
    return pathInfo.value.next_titles.slice(0, 3);
  }
  return pathInfo.value.blocked_titles.slice(0, 3);
});

/** 传给图谱抽屉的「路径 / 解锁」摘要（与 currentKpId 同源） */
const graphPathHint = computed(() => {
  const p = pathInfo.value;
  if (!p) return null;
  return {
    next_candidate_ids: p.next_candidates ?? [],
    next_titles: p.next_titles ?? [],
    can_unlock_next: p.can_unlock_next,
    blocked_titles: p.blocked_titles ?? [],
    path_summary: p.path_summary || pathSummary.value,
  };
});

const graphRecoHint = computed(() => {
  const r = reco.value;
  if (!r?.target_kp?.id) return null;
  return {
    reason_summary: r.reason_summary,
    advice_text: r.advice_text,
    target_kp_id: r.target_kp.id,
    target_code: r.target_kp.code,
    target_title: r.target_kp.title,
  };
});

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    const raw = res.data ?? [];
    courses.value = raw.map((item: any) => ({
      id: Number(item.id),
      code: String(item.code || ""),
      title: String(item.title || ""),
    }));
    const targetSubject = String(route.query.subject || "");
    subject.value = targetSubject || courses.value[0]?.title || "";
  } catch (e: any) {
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载课程失败");
  }
}

async function loadKps() {
  if (!subject.value) return;
  try {
    const data = await getWithCache("/graph/kps", { subject: subject.value, grade: grade.value });
    kps.value = data ?? [];
    const queryKp = Number(route.query.kp || 0);
    currentKpId.value = queryKp && kps.value.some((item) => item.id === queryKp) ? queryKp : (kps.value[0]?.id ?? null);
  } catch (e: any) {
    if (e?.response?.status === 401) return;
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
  }
}

async function loadRecommendation() {
  if (!currentKpId.value) {
    reco.value = null;
    return;
  }
  try {
    const res = await api.get(`/reco?kp_id=${currentKpId.value}`);
    reco.value = res.data ?? null;
  } catch (e: any) {
    reco.value = null;
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.detail ?? "加载推荐失败");
    }
  }
}

async function loadPathInfo() {
  if (!currentKpId.value) {
    pathInfo.value = null;
    return;
  }
  try {
    const res = await api.get(`/graph/path/${currentKpId.value}`);
    pathInfo.value = res.data ?? null;
  } catch {
    pathInfo.value = null;
  }
}

function syncQuery() {
  const preview = String(route.query.preview || "");
  router.replace({
    path: "/student/graph-workspace",
    query: {
      subject: subject.value || undefined,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
      preview: preview || undefined,
    },
  });
}

async function onCourseChange() {
  currentKpId.value = null;
  reco.value = null;
  pathInfo.value = null;
  await loadKps();
  await loadRecommendation();
  await loadPathInfo();
  syncQuery();
}

function handleSelectKp(id: number) {
  currentKpId.value = id;
  syncQuery();
}

async function goKpContent(kpId?: number | null) {
  const targetId = kpId ?? currentKpId.value;
  if (!targetId) {
    ElMessage.warning("请先选择一个知识点");
    return;
  }
  try {
    const detailRes = await api.get(`/graph/node/${targetId}`);
    const blockedReason = detailRes.data?.overlay?.blocked_reason;
    if (blockedReason) {
      ElMessage.warning(blockedReason);
      return;
    }
  } catch (e: any) {
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.detail ?? "加载知识点信息失败");
    }
    return;
  }
  const preview = String(route.query.preview || "");
  router.push({
    path: `/student/kp-content/${targetId}`,
    query: {
      subject: subject.value || undefined,
      grade: grade.value || undefined,
      preview: preview || undefined,
    },
  });
}

function updateWorkspaceState(payload: WorkspaceState) {
  workspaceState.value = payload;
}

watch(
  () => route.query,
  async (query) => {
    const nextSubject = String(query.subject || "");
    if (nextSubject && nextSubject !== subject.value) {
      subject.value = nextSubject;
      await loadKps();
      return;
    }
    const nextKp = Number(query.kp || 0);
    if (nextKp && kps.value.some((item) => item.id === nextKp)) {
      currentKpId.value = nextKp;
    }
  }
);

watch(currentKpId, async (value, oldValue) => {
  if (value === oldValue) return;
  await loadRecommendation();
  await loadPathInfo();
});

onMounted(async () => {
  await loadCourses();
  await loadKps();
  await loadRecommendation();
  await loadPathInfo();
});
</script>

<template>
  <div class="workspace-page">
    <div class="workspace-page__toolbar">
      <div class="workspace-page__left">
        <button
          class="workspace-page__back"
          @click="router.push({ path: '/student/graph', query: route.query })"
        >
          返回学习页
        </button>
        <div>
          <div class="workspace-page__title">知识图谱工作台（学习视图）</div>
          <div class="workspace-page__subtitle">
            与学生端同源课程数据；节点三色环一致——内绿知识、中黄能力、外紫素养。
          </div>
        </div>
      </div>

      <div class="workspace-page__right">
        <el-select v-model="subject" style="width: 240px" @change="onCourseChange">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="workspace-page__minor-btn" type="button" @click="loadCourses">刷新</button>
        <button class="workspace-page__minor-btn" @click="goKpContent()">进入学习内容页</button>
        <div class="workspace-page__chip">{{ currentKp ? `${currentKp.code} ${currentKp.title}` : "未选择知识点" }}</div>
      </div>
    </div>

    <section class="workspace-simple-note">
      <strong>当前状态</strong>
      <span>分类 {{ workspaceState.categoryCount }} 个，已选知识点 {{ workspaceState.selectedKpId ? 1 : 0 }} 个。</span>
      <HoverTip content="在知识点上完成练习与小测后，图谱色环与右侧证据会同步更新能力/素养达成情况。" />
    </section>

    <el-collapse v-if="pathInfo || reco" v-model="insightsOpen" class="workspace-insights">
      <el-collapse-item title="学习路径 · 解锁状态 · 智能推荐（可选展开）" name="insights">
        <div class="workspace-insights__inner">
          <section v-if="pathInfo" class="workspace-path workspace-path--compact">
            <div class="workspace-path__body">
              <div class="workspace-path__eyebrow">知识路径解释</div>
              <div class="workspace-path__title">{{ pathInfo.path_summary }}</div>
              <div class="workspace-path__summary">{{ pathSummary }}</div>
              <div class="workspace-path__meta">
                <span>前置链：{{ pathInfo.prereq_chain.length }} 个节点</span>
                <span>后继候选：{{ pathInfo.next_candidates.length }} 个节点</span>
                <span>{{ pathInfo.can_unlock_next ? "当前可继续推进" : "仍需补前置" }}</span>
              </div>
              <div v-if="pathInfo.blocked_titles.length" class="workspace-path__tips">
                需先补：{{ pathInfo.blocked_titles.join("、") }}
              </div>
              <div v-else-if="pathInfo.next_titles.length" class="workspace-path__tips">
                可继续：{{ pathInfo.next_titles.slice(0, 3).join("、") }}
              </div>
            </div>
            <div class="workspace-path__actions">
              <button class="workspace-page__minor-btn" type="button" @click="loadPathInfo">刷新路径</button>
              <button class="workspace-page__primary-btn" type="button" :disabled="!currentKpId" @click="goKpContent()">进入学习</button>
            </div>
          </section>

          <section
            v-if="pathInfo"
            class="workspace-lockbox workspace-lockbox--compact"
            :class="{ 'workspace-lockbox--open': pathInfo.can_unlock_next }"
          >
            <div class="workspace-lockbox__header">
              <div>
                <div class="workspace-lockbox__eyebrow">解锁说明</div>
                <div class="workspace-lockbox__title">{{ pathInfo.can_unlock_next ? "当前已解锁" : "当前暂时锁定" }}</div>
              </div>
              <el-tag :type="pathInfo.can_unlock_next ? 'success' : 'warning'">{{
                pathInfo.can_unlock_next ? "可继续" : "需补前置"
              }}</el-tag>
            </div>
            <div class="workspace-lockbox__summary">{{ lockSummary }}</div>
            <div v-if="lockNextTips.length" class="workspace-lockbox__tips">
              <span v-for="item in lockNextTips" :key="item" class="workspace-lockbox__pill">{{ item }}</span>
            </div>
            <div class="workspace-lockbox__footer">
              <span>规则：满足前置掌握后，系统才开放后继知识点。</span>
              <button class="workspace-page__minor-btn" type="button" @click="loadPathInfo">重新检查</button>
            </div>
          </section>

          <section v-if="reco" class="workspace-reco workspace-reco--compact">
            <div class="workspace-reco__body">
              <div class="workspace-reco__eyebrow">知识图谱推荐</div>
              <div class="workspace-reco__title workspace-reco__title--compact">
                {{ recommendedKp ? `${recommendedKp.code} ${recommendedKp.title}` : `${reco.target_kp.code} ${reco.target_kp.title}` }}
              </div>
              <p class="workspace-reco__desc">{{ reco.reason_summary }}</p>
              <div class="workspace-reco__meta">
                <span>{{ recommendationStageLabel }}</span>
                <span>建议先学这个点</span>
              </div>
              <div v-if="blockedPrereqTitles.length" class="workspace-reco__tips">需要先补：{{ blockedPrereqTitles.join("、") }}</div>
              <div v-else-if="reco.unlock?.can_unlock_next" class="workspace-reco__tips">当前知识点已具备进入下一步学习的条件。</div>
              <div v-if="recommendedPathTitles.length > 1" class="workspace-reco__path">
                <strong>推荐路径：</strong>
                <span>{{ recommendedPathTitles.join(" → ") }}</span>
              </div>
            </div>
            <div class="workspace-reco__actions">
              <button class="workspace-page__minor-btn" type="button" @click="handleSelectKp(reco.target_kp.id)">定位推荐点</button>
              <button class="workspace-page__primary-btn" type="button" @click="goKpContent(reco.target_kp.id)">去学习</button>
            </div>
          </section>
        </div>
      </el-collapse-item>
    </el-collapse>

    <div class="workspace-page__graph-host">
      <KnowledgeGraphWorkspace
        embedded
        :subject="subject"
        :grade="grade"
        :current-kp-id="currentKpId"
        :recommended-kp-id="reco?.target_kp?.id ?? null"
        :highlighted-kp-ids="recommendedPathIds"
        :graph-path-hint="graphPathHint"
        :graph-reco-hint="graphRecoHint"
        @select-kp="handleSelectKp"
        @open-content="goKpContent"
        @state-change="updateWorkspaceState"
      />
    </div>
  </div>
</template>

<style scoped>
.workspace-page {
  /* 与教师端 TeacherGraphWorkspace 同一套垂直节奏；略减扣减项，多留高度给图谱主区 */
  height: calc(100dvh - 96px - 4px);
  max-height: calc(100dvh - 96px - 4px);
  padding: 6px 10px 8px;
  box-sizing: border-box;
  background: var(--app-bg);
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-x: hidden;
  overflow-y: auto;
  min-height: 0;
  width: 100%;
  max-width: 100%;
}

.workspace-page__graph-host {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspace-insights {
  flex-shrink: 0;
  border-radius: var(--app-radius);
  overflow: hidden;
  border: 1px solid var(--app-border);
  background: var(--app-card);
  box-shadow: var(--app-shadow-soft);
}

.workspace-insights :deep(.el-collapse-item__header) {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-text-main);
  padding: 10px 12px;
  background: var(--app-surface-muted);
}

.workspace-insights :deep(.el-collapse-item__wrap) {
  border-top: 1px solid var(--app-border);
}

.workspace-insights :deep(.el-collapse-item__content) {
  padding: 12px;
  background: var(--app-card);
}

.workspace-insights__inner {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: min(38vh, 360px);
  overflow-y: auto;
}

.workspace-path--compact,
.workspace-lockbox--compact,
.workspace-reco--compact {
  padding: 12px 14px;
  margin: 0;
  box-shadow: none;
  border-radius: var(--app-radius-sm);
}

.workspace-path--compact {
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
}

.workspace-path--compact .workspace-path__actions {
  justify-content: flex-start;
}

.workspace-reco__title--compact {
  font-size: 17px;
}

.workspace-page__toolbar {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: var(--app-radius);
  background: var(--app-card);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.workspace-page__left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workspace-page__back {
  border: 1px solid var(--app-border);
  border-radius: 999px;
  padding: 0 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
  color: #39506d;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-shadow: var(--app-shadow-soft);
}

.workspace-page__left > div:last-child {
  display: grid;
  gap: 4px;
}

.workspace-page__title {
  font-size: 18px;
  font-weight: 800;
  color: #243449;
  line-height: 1.25;
}

.workspace-page__subtitle {
  color: #718097;
  font-size: 12px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.workspace-page__right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.workspace-page__minor-btn {
  border: 1px solid var(--app-border);
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
  color: #39506d;
  border-radius: 999px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-shadow: var(--app-shadow-soft);
}

.workspace-page__primary-btn {
  border: 1px solid var(--app-green);
  background: linear-gradient(180deg, #3f7af0 0%, var(--app-green) 100%);
  color: #ffffff;
  border-radius: 999px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(47, 111, 237, 0.18);
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.workspace-page__chip {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  background: #fafbfd;
  border: 1px solid var(--app-border);
  color: #314661;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.workspace-simple-note {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: var(--app-radius-sm);
  background: var(--app-card);
  border: 1px solid var(--app-border);
  color: var(--app-ink-soft);
  font-size: 12px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  box-shadow: var(--app-shadow-soft);
}

.workspace-guide {
  flex-shrink: 0;
  background: var(--app-card);
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  padding: 10px 14px;
  box-shadow: var(--app-shadow-soft);
}

.workspace-guide--simple {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.workspace-path {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.workspace-path__body {
  display: grid;
  gap: 8px;
}

.workspace-path__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #6c84a7;
  text-transform: uppercase;
}

.workspace-path__title {
  font-size: 18px;
  font-weight: 800;
  color: #243449;
  line-height: 1.5;
}

.workspace-path__summary {
  color: #5f748e;
  font-size: 13px;
  line-height: 1.7;
}

.workspace-path__meta,
.workspace-path__tips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.workspace-path__meta span,
.workspace-path__tips {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(198, 212, 238, 0.92);
  background: rgba(255, 255, 255, 0.78);
  color: #4b6282;
  font-size: 13px;
  font-weight: 700;
}

.workspace-path__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.workspace-lockbox {
  display: grid;
  gap: 10px;
  padding: 18px 20px;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.workspace-lockbox--open {
  border-color: rgba(98, 179, 111, 0.35);
}

.workspace-lockbox__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.workspace-lockbox__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #6c84a7;
  text-transform: uppercase;
}

.workspace-lockbox__title {
  margin-top: 4px;
  font-size: 18px;
  font-weight: 800;
  color: #243449;
}

.workspace-lockbox__summary {
  color: #5f748e;
  line-height: 1.8;
}

.workspace-lockbox__tips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.workspace-lockbox__pill {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-radius: 999px;
  background: #edf4ff;
  border: 1px solid rgba(89, 132, 210, 0.18);
  color: #3c5b89;
  font-size: 13px;
  font-weight: 700;
}

.workspace-lockbox__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: #60758f;
  font-size: 13px;
}

.workspace-reco {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow);
}

.workspace-reco__body {
  display: grid;
  gap: 8px;
}

.workspace-reco__eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #6580af;
}

.workspace-reco__title {
  font-size: 24px;
  font-weight: 800;
  color: #243449;
}

.workspace-reco__desc {
  margin: 0;
  color: #536883;
  line-height: 1.7;
}

.workspace-reco__meta,
.workspace-reco__tips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.workspace-reco__path {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  color: #47607e;
  font-size: 13px;
  line-height: 1.7;
}

.workspace-reco__path strong {
  color: #2b4364;
}

.workspace-reco__meta span,
.workspace-reco__tips {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(198, 212, 238, 0.92);
  background: rgba(255, 255, 255, 0.78);
  color: #4b6282;
  font-size: 13px;
  font-weight: 700;
}

.workspace-reco__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 1180px) {
  .workspace-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-page__left {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-page__right {
    width: 100%;
  }

  .workspace-reco {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-path {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
