<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { getRole } from "../token";
import TeacherGraphWorkbench from "../components/TeacherGraphWorkbench.vue";
import { buildTeacherSubjectQuery, resolveTeacherSubject, saveTeacherSubject } from "../utils/teacherCourse";

type Course = { id: number; code: string; title: string };
type WorkbenchState = {
  kpCount: number;
  categoryCount: number;
  filteredCount: number;
  selectedType: "kp" | "category";
  selectedKpId: number | null;
  selectedCategory: string | null;
};

const route = useRoute();
const router = useRouter();
const isTeacher = computed(() => getRole() === "teacher");

const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const workbenchState = ref<WorkbenchState>({
  kpCount: 0,
  categoryCount: 0,
  filteredCount: 0,
  selectedType: "kp",
  selectedKpId: null,
  selectedCategory: null,
});

const teacherGuideSteps = computed(() => [
  {
    title: "第一步：先选课程",
    done: !!subject.value,
    text: subject.value ? `当前课程：${subject.value}` : "请先在右上角选择课程",
  },
  {
    title: "第二步：看左侧分类",
    done: workbenchState.value.categoryCount > 0,
    text:
      workbenchState.value.categoryCount > 0
        ? `已加载 ${workbenchState.value.categoryCount} 个分类`
        : "当前课程暂无分类，请先新建知识点",
  },
  {
    title: "第三步：点击中间节点",
    done: !!workbenchState.value.selectedKpId,
    text: workbenchState.value.selectedKpId ? "已选中知识点，可直接编辑" : "请点击中间画布中的知识点",
  },
  {
    title: "第四步：在右侧维护内容",
    done: !!workbenchState.value.selectedKpId,
    text: "右侧可编辑基本信息、关系和资源绑定",
  },
]);

async function loadCourses() {
  try {
    const res = await api.get("/graph/courses");
    courses.value = res.data ?? [];
    subject.value = resolveTeacherSubject(String(route.query.subject || ""), subject.value, courses.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载教师课程失败");
  }
}

function syncQuery() {
  saveTeacherSubject(subject.value);
  router.replace({
    path: "/teacher/graph-workspace",
    query: buildTeacherSubjectQuery(subject.value),
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

function updateWorkbenchState(payload: WorkbenchState) {
  workbenchState.value = payload;
}

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
    <div class="workspace-page__toolbar">
      <div class="workspace-page__left">
        <div>
          <div class="workspace-page__title">教师知识图谱工作台</div>
          <div class="workspace-page__subtitle">先选课程，再点节点直接编辑。</div>
        </div>
      </div>

      <div class="workspace-page__right">
        <el-select v-model="subject" style="width: 240px">
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.title" />
        </el-select>
        <button class="workspace-page__minor-btn" @click="loadCourses">刷新课程</button>
        <div class="workspace-page__chip">{{ subject || "未选择课程" }}</div>
      </div>
    </div>

    <section class="workspace-guide">
      <div class="workspace-guide__head">
        <h2>图谱操作清单</h2>
        <p>按顺序完成，页面会自动显示“已完成”。</p>
      </div>
      <div class="workspace-guide__grid">
        <div
          v-for="step in teacherGuideSteps"
          :key="step.title"
          class="workspace-guide__item"
          :class="{ 'workspace-guide__item--done': step.done }"
        >
          <strong>{{ step.title }}</strong>
          <span>{{ step.text }}</span>
        </div>
      </div>
    </section>

    <TeacherGraphWorkbench :subject="subject" :grade="grade" :fullscreen="true" @state-change="updateWorkbenchState" />
  </div>
</template>

<style scoped>
.workspace-page {
  min-height: 100vh;
  padding: 14px;
  background: var(--app-bg);
  display: grid;
  gap: 14px;
  overflow-x: hidden;
}

.workspace-page__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 12px 16px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
}

.workspace-page__left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.workspace-page__title {
  font-size: 26px;
  font-weight: 800;
  color: #243449;
}

.workspace-page__subtitle {
  color: #718097;
  margin-top: 4px;
}

.workspace-page__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.workspace-page__minor-btn {
  border: 1px solid var(--app-border);
  background: #f7f9fc;
  color: #39506d;
  border-radius: 999px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.workspace-page__chip {
  padding: 14px 20px;
  border-radius: 999px;
  background: #fafbfd;
  border: 1px solid var(--app-border);
  color: #314661;
  font-weight: 700;
}

.workspace-guide {
  background: #fff;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  padding: 14px 16px;
  box-shadow: var(--app-shadow-soft);
}

.workspace-guide__head h2 {
  margin: 0;
  font-size: 18px;
  color: #243449;
}

.workspace-guide__head p {
  margin: 4px 0 0;
  color: #617289;
  font-size: 13px;
}

.workspace-guide__grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.workspace-guide__item {
  border: 1px solid var(--app-border);
  border-radius: 14px;
  padding: 10px 12px;
  background: #fcfdff;
  display: grid;
  gap: 4px;
}

.workspace-guide__item strong {
  font-size: 13px;
  color: #334b70;
}

.workspace-guide__item span {
  font-size: 12px;
  color: #64758c;
  line-height: 1.45;
}

.workspace-guide__item--done {
  border-color: #cfe4d7;
  background: #f5faf6;
}

.workspace-page :deep(.workbench-shell) {
  min-height: calc(100vh - 190px);
}

@media (max-width: 1180px) {
  .workspace-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-page__right {
    width: 100%;
    flex-wrap: wrap;
  }

  .workspace-guide__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .workspace-guide__grid {
    grid-template-columns: 1fr;
  }
}
</style>
