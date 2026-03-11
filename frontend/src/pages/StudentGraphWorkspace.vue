<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { getWithCache } from "../api";
import KnowledgeGraphWorkspace from "../components/KnowledgeGraphWorkspace.vue";

type Course = { id: number; code: string; title: string };
type KP = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();

const courses = ref<Course[]>([]);
const subject = ref<string>("");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);

const currentKp = computed(() => kps.value.find((item) => item.id === currentKpId.value) ?? null);

async function loadCourses() {
  try {
    const data = await getWithCache("/graph/courses");
    courses.value = data ?? [];
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

function syncQuery() {
  router.replace({
    path: "/student/graph-workspace",
    query: {
      subject: subject.value || undefined,
      kp: currentKpId.value ? String(currentKpId.value) : undefined,
    },
  });
}

async function onCourseChange() {
  currentKpId.value = null;
  await loadKps();
  syncQuery();
}

function handleSelectKp(id: number) {
  currentKpId.value = id;
  syncQuery();
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

onMounted(async () => {
  await loadCourses();
  await loadKps();
});
</script>

<template>
  <div class="workspace-page">
    <header class="workspace-page__nav">
      <button class="workspace-page__arrow" @click="router.push('/student/graph')">&laquo;</button>
      <span>课程介绍</span>
      <span>知识关系</span>
      <span>课程统计</span>
      <span>学习地图</span>
      <span class="active">知识图谱</span>
      <span>课程思政图谱</span>
      <button class="workspace-page__arrow workspace-page__arrow--right">&raquo;</button>
    </header>

    <div class="workspace-page__toolbar">
      <div class="workspace-page__left">
        <div class="workspace-page__title">知识图谱工作台</div>
        <div class="workspace-page__subtitle">面向课程结构、节点关系与学习路径的沉浸式工作区。</div>
      </div>

      <div class="workspace-page__right">
        <el-select v-model="subject" style="width: 220px" @change="onCourseChange">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <div class="workspace-page__chip">{{ currentKp ? `${currentKp.code} ${currentKp.title}` : "未选择知识点" }}</div>
      </div>
    </div>

    <KnowledgeGraphWorkspace
      :subject="subject"
      :grade="grade"
      :current-kp-id="currentKpId"
      @select-kp="handleSelectKp"
    />
  </div>
</template>

<style scoped>
.workspace-page {
  min-height: 100vh;
  padding: 14px;
  background: linear-gradient(180deg, #edf2f7 0%, #e7edf5 100%);
  display: grid;
  gap: 14px;
}

.workspace-page__nav {
  display: grid;
  grid-template-columns: auto repeat(6, max-content) auto;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 14px 18px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.88);
  color: #8f98aa;
  font-size: 18px;
  font-weight: 500;
}

.workspace-page__nav .active {
  padding: 14px 34px;
  border-radius: 999px;
  background: #e9eef7;
  color: #4f8fff;
  font-weight: 800;
}

.workspace-page__arrow {
  border: 0;
  background: transparent;
  color: #4f8fff;
  font-size: 28px;
  cursor: pointer;
}

.workspace-page__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 10px 12px 0;
}

.workspace-page__left {
  display: grid;
  gap: 6px;
}

.workspace-page__title {
  font-size: 32px;
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
}

.workspace-page__chip {
  padding: 14px 20px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #d8e2ef;
  color: #314661;
  font-weight: 700;
}

@media (max-width: 1180px) {
  .workspace-page__nav {
    grid-template-columns: repeat(3, max-content);
    justify-content: start;
    overflow: auto;
  }

  .workspace-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-page__right {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
