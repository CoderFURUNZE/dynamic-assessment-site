<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import TeacherGraphWorkbench from "../components/TeacherGraphWorkbench.vue";

type Course = { id: number; code: string; title: string };

const route = useRoute();
const router = useRouter();
const isTeacher = computed(() => getRole() === "teacher");

const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    const querySubject = String(route.query.subject || "");
    subject.value = querySubject || courses.value[0]?.title || "";
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

function syncQuery() {
  router.replace({
    path: "/teacher/graph-workspace",
    query: {
      subject: subject.value || undefined,
    },
  });
}

watch(
  () => route.query.subject,
  (value) => {
    const next = String(value || "");
    if (next && next !== subject.value) subject.value = next;
  }
);

watch(subject, () => {
  syncQuery();
});

onMounted(async () => {
  if (!isTeacher.value) {
    ElMessage.warning("仅教师可访问教师图谱工作区");
    router.push("/login");
    return;
  }
  await loadCourses();
});
</script>

<template>
  <div v-if="isTeacher" class="workspace-page">
    <header class="workspace-page__nav">
      <button class="workspace-page__arrow" @click="router.push('/teacher/graph')">&laquo;</button>
      <span>课程建设</span>
      <span>阶段管理</span>
      <span>图谱关系</span>
      <span>学习分析</span>
      <span class="active">知识图谱</span>
      <span>资源绑定</span>
      <button class="workspace-page__arrow workspace-page__arrow--right" @click="router.push('/teacher/courses')">&raquo;</button>
    </header>

    <div class="workspace-page__toolbar">
      <div class="workspace-page__left">
        <div class="workspace-page__title">教师知识图谱工作台</div>
        <div class="workspace-page__subtitle">参考学习端工作区布局，在同一张图谱上直接编辑节点、关系和内容绑定。</div>
      </div>

      <div class="workspace-page__right">
        <el-select v-model="subject" style="width: 240px">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <div class="workspace-page__chip">{{ subject || "未选择课程" }}</div>
      </div>
    </div>

    <TeacherGraphWorkbench :subject="subject" :grade="grade" :fullscreen="true" />
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

.workspace-page :deep(.workbench-shell) {
  min-height: calc(100vh - 190px);
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
