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

const route = useRoute();
const router = useRouter();

const courses = ref<Course[]>([]);
const subject = ref<string>("");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);
const reco = ref<RecoData | null>(null);
const workspaceState = ref<WorkspaceState>({
  kpCount: 0,
  categoryCount: 0,
  filteredCount: 0,
  selectedType: "kp",
  selectedKpId: null,
  selectedCategory: null,
});

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

async function loadCourses() {
  try {
    const data = await api.get("/graph/courses");
    courses.value = data.data ?? [];
    const targetSubject = String(route.query.subject || "");
    subject.value = targetSubject || courses.value[0]?.title || "";
  } catch (e: any) {
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
    ElMessage.error(e?.response?.data?.detail ?? "加载推荐失败");
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
  await loadKps();
  await loadRecommendation();
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
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点信息失败");
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
});

onMounted(async () => {
  await loadCourses();
  await loadKps();
  await loadRecommendation();
});
</script>

<template>
  <div class="workspace-page">
    <div class="workspace-page__toolbar">
      <div class="workspace-page__left">
        <button
          class="workspace-page__back"
          @click="router.push({ path: '/student/graph', query: route.query.preview ? { preview: String(route.query.preview) } : undefined })"
        >
          返回学习页
        </button>
        <div>
          <div class="workspace-page__title">学习者知识图谱工作台</div>
          <div class="workspace-page__subtitle">先点左边章节，再点中间知识点，然后去学习。</div>
        </div>
      </div>

      <div class="workspace-page__right">
        <el-select v-model="subject" style="width: 220px" @change="onCourseChange">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="workspace-page__minor-btn" @click="goKpContent()">进入学习内容页</button>
        <div class="workspace-page__chip">{{ currentKp ? `${currentKp.code} ${currentKp.title}` : "未选择知识点" }}</div>
      </div>
    </div>

    <section class="workspace-guide workspace-guide--simple">
      <strong>使用方法</strong>
      <HoverTip content="左边选章节，中间点知识点，右边看内容，再点“去学习”即可。" />
    </section>

    <section v-if="reco" class="workspace-reco">
      <div class="workspace-reco__body">
        <div class="workspace-reco__eyebrow">知识图谱推荐</div>
        <div class="workspace-reco__title">
          {{ recommendedKp ? `${recommendedKp.code} ${recommendedKp.title}` : `${reco.target_kp.code} ${reco.target_kp.title}` }}
        </div>
        <p class="workspace-reco__desc">{{ reco.reason_summary }}</p>
        <div class="workspace-reco__meta">
          <span>{{ recommendationStageLabel }}</span>
          <span>建议先学这个点</span>
        </div>
        <div v-if="blockedPrereqTitles.length" class="workspace-reco__tips">
          需要先补：{{ blockedPrereqTitles.join("、") }}
        </div>
        <div v-else-if="reco.unlock?.can_unlock_next" class="workspace-reco__tips">
          当前知识点已具备进入下一步学习的条件。
        </div>
        <div v-if="recommendedPathTitles.length > 1" class="workspace-reco__path">
          <strong>推荐路径：</strong>
          <span>{{ recommendedPathTitles.join(" → ") }}</span>
        </div>
      </div>
      <div class="workspace-reco__actions">
        <button class="workspace-page__minor-btn" @click="handleSelectKp(reco.target_kp.id)">定位推荐点</button>
        <button class="workspace-page__primary-btn" @click="goKpContent(reco.target_kp.id)">去学习</button>
      </div>
    </section>

    <KnowledgeGraphWorkspace
      :subject="subject"
      :grade="grade"
      :current-kp-id="currentKpId"
      :recommended-kp-id="reco?.target_kp?.id ?? null"
      :highlighted-kp-ids="recommendedPathIds"
      @select-kp="handleSelectKp"
      @open-content="goKpContent"
      @state-change="updateWorkspaceState"
    />
  </div>
</template>

<style scoped>
.workspace-page {
  min-height: 100vh;
  padding: 16px;
  background: var(--app-bg);
  display: grid;
  gap: 16px;
}

.workspace-page__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 18px 22px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow);
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

.workspace-page__title {
  font-size: 28px;
  font-weight: 800;
  color: #243449;
}

.workspace-page__subtitle {
  color: #718097;
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

.workspace-guide {
  background: #fff;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  padding: 14px 16px;
  box-shadow: var(--app-shadow-soft);
}

.workspace-guide--simple {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
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
}
</style>
