<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import AdminIntroHero from "../components/AdminIntroHero.vue";
import AdminPersonaManager from "../components/AdminPersonaManager.vue";

type Course = {
  id: number;
  code: string;
  title: string;
};

const props = defineProps<{ mode: "settings" | "results" }>();

const route = useRoute();
const router = useRouter();

const defaultSubject = "计算机网络";
const defaultGrade = "通用";
const gradeOptions = ["通用", "大一", "大二", "大三", "大四"];
const subjectOptions = ref<string[]>([defaultSubject]);

const pageItems = [
  { key: "settings", title: "默认规则模板", eyebrow: "模板设置" },
  { key: "results", title: "默认规则模板", eyebrow: "模板设置" },
] as const;

const currentPage = computed(() => pageItems.find((item) => item.key === props.mode) ?? pageItems[0]);

const personaSubject = computed({
  get: () => String(route.query.subject || defaultSubject),
  set: (value: string) => {
    router.replace({
      path: route.path,
      query: { ...route.query, subject: value || defaultSubject },
    });
  },
});

const personaGrade = computed({
  get: () => String(route.query.grade || defaultGrade),
  set: (value: string) => {
    router.replace({
      path: route.path,
      query: { ...route.query, grade: value || defaultGrade },
    });
  },
});

function normalizeSubjectOptions(courses: Course[]) {
  const titles = courses
    .map((item) => String(item.title || item.code || "").trim())
    .filter(Boolean);
  subjectOptions.value = Array.from(new Set([defaultSubject, personaSubject.value, ...titles]));
}

async function loadSubjectOptions() {
  try {
    const res = await api.get("/graph/courses");
    normalizeSubjectOptions(res.data ?? []);
  } catch (error: any) {
    normalizeSubjectOptions([]);
    ElMessage.warning(error?.response?.data?.detail ?? "课程列表加载失败，已使用默认学科选项");
  }
}

onMounted(loadSubjectOptions);
</script>

<template>
  <div class="admin-persona-page">
    <AdminIntroHero
      eyebrow="评价配置"
      title="画像规则模板"
      description="管理员负责维护平台默认模板，供教师在具体课程中选择、复用和微调。"
    />

    <section class="admin-persona-step-card">
      <div class="admin-persona-step-card__header">
        <div>
          <div class="admin-persona-step-card__eyebrow">{{ currentPage.eyebrow }}</div>
          <div class="admin-persona-step-card__title">{{ currentPage.title }}</div>
        </div>
        <div class="admin-persona-step-card__badge">当前功能</div>
      </div>

      <div class="admin-context">
        <label class="admin-context__field">
          <span>学科</span>
          <el-select
            v-model="personaSubject"
            class="admin-context__select"
            placeholder="请选择学科"
            filterable
          >
            <el-option
              v-for="subject in subjectOptions"
              :key="subject"
              :label="subject"
              :value="subject"
            />
          </el-select>
        </label>
        <label class="admin-context__field">
          <span>年级 / 规则层级</span>
          <el-select
            v-model="personaGrade"
            class="admin-context__select"
            placeholder="请选择层级"
          >
            <el-option
              v-for="grade in gradeOptions"
              :key="grade"
              :label="grade"
              :value="grade"
            />
          </el-select>
        </label>
      </div>

      <div class="admin-persona-step-card__content">
        <AdminPersonaManager
          :subject="personaSubject"
          :grade="personaGrade"
          :step="props.mode"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-persona-page {
  display: grid;
  gap: 20px;
}

.admin-persona-step-card {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.admin-persona-step-card__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.admin-persona-step-card__eyebrow {
  font-size: 12px;
  font-weight: 800;
  color: #25645b;
}

.admin-persona-step-card__title {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 800;
  color: #18463e;
}

.admin-persona-step-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1.5px solid #c6d8ef;
  background: #eef5ff;
  color: #355070;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.admin-context {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr 1fr;
}

.admin-context__field {
  display: grid;
  gap: 8px;
}

.admin-context__field span {
  font-size: 13px;
  font-weight: 700;
  color: #4f6c61;
}

.admin-context__select {
  width: 100%;
}

.admin-persona-step-card__content {
  padding-top: 4px;
}

.admin-persona-step-card__content :deep(.persona-card) {
  border-radius: 22px;
}

@media (max-width: 960px) {
  .admin-context {
    grid-template-columns: 1fr;
  }

  .admin-persona-step-card__header {
    flex-direction: column;
  }
}
</style>
