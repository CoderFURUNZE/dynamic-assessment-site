<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminIntroHero from "../components/AdminIntroHero.vue";

type Course = { id: number; title: string; code: string };

const courses = ref<Course[]>([]);
const subject = ref("");
const grade = ref("通用");
const loading = ref(false);
const saving = ref(false);
const form = ref({
  weights: "{}",
  thresholds: "{}",
  window: "{}",
  personaThresholds: "{}",
  personaWeights: "{}",
  personaStrategies: "{}",
});

async function loadCourses() {
  const res = await api.get("/graph/courses");
  courses.value = res.data ?? [];
  if (!subject.value && courses.value.length) subject.value = courses.value[0].title;
}

async function loadConfig() {
  if (!subject.value) return;
  loading.value = true;
  try {
    const res = await api.get(`/admin/config?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
    form.value = {
      weights: JSON.stringify(res.data?.weights ?? {}, null, 2),
      thresholds: JSON.stringify(res.data?.thresholds ?? {}, null, 2),
      window: JSON.stringify(res.data?.window ?? {}, null, 2),
      personaThresholds: JSON.stringify(res.data?.persona?.thresholds ?? {}, null, 2),
      personaWeights: JSON.stringify(res.data?.persona?.weights ?? {}, null, 2),
      personaStrategies: JSON.stringify(res.data?.persona?.strategies ?? {}, null, 2),
    };
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载系统配置失败");
  } finally {
    loading.value = false;
  }
}

async function saveConfig() {
  if (!subject.value) return;
  saving.value = true;
  try {
    await api.put(`/admin/config?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`, {
      weights: JSON.parse(form.value.weights || "{}"),
      thresholds: JSON.parse(form.value.thresholds || "{}"),
      window: JSON.parse(form.value.window || "{}"),
      persona: {
        thresholds: JSON.parse(form.value.personaThresholds || "{}"),
        weights: JSON.parse(form.value.personaWeights || "{}"),
        strategies: JSON.parse(form.value.personaStrategies || "{}"),
      },
    });
    ElMessage.success("系统配置已保存");
    await loadConfig();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "保存失败，请检查 JSON 格式");
  } finally {
    saving.value = false;
  }
}

watch([subject, grade], () => {
  loadConfig();
});

onMounted(async () => {
  await loadCourses();
  await loadConfig();
});
</script>

<template>
  <div class="admin-config-page" v-loading="loading">
    <AdminIntroHero eyebrow="评价配置" title="系统配置" pill="参数配置" description="直接维护动态评价参数、评价窗口和画像规则，改动后可以通过真实接口立即保存。">
      <template #actions>
        <el-select v-model="subject" placeholder="选择课程" style="width: 220px">
          <el-option v-for="item in courses" :key="item.id" :label="item.title" :value="item.title" />
        </el-select>
        <el-input v-model="grade" placeholder="层级" style="width: 140px" />
        <el-button @click="loadConfig">刷新</el-button>
        <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
      </template>
    </AdminIntroHero>

    <section class="grid">
      <el-card shadow="never" class="panel-card">
        <template #header>动态评价权重</template>
        <el-input v-model="form.weights" type="textarea" :rows="14" />
      </el-card>
      <el-card shadow="never" class="panel-card">
        <template #header>动态评价阈值</template>
        <el-input v-model="form.thresholds" type="textarea" :rows="14" />
      </el-card>
      <el-card shadow="never" class="panel-card">
        <template #header>评价窗口</template>
        <el-input v-model="form.window" type="textarea" :rows="14" />
      </el-card>
      <el-card shadow="never" class="panel-card">
        <template #header>画像阈值</template>
        <el-input v-model="form.personaThresholds" type="textarea" :rows="14" />
      </el-card>
      <el-card shadow="never" class="panel-card">
        <template #header>画像权重</template>
        <el-input v-model="form.personaWeights" type="textarea" :rows="14" />
      </el-card>
      <el-card shadow="never" class="panel-card">
        <template #header>画像策略文案</template>
        <el-input v-model="form.personaStrategies" type="textarea" :rows="14" />
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.admin-config-page {
  display: grid;
  gap: 20px;
}

.admin-config-page .grid {
  padding: 18px;
  border-radius: 32px;
  border: 3px solid #1f2937;
  background:
    radial-gradient(circle at top left, rgba(201, 237, 255, 0.22), transparent 24%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.admin-config-page :deep(.el-card.panel-card) {
  border: 1.5px solid #c6d8ef !important;
  border-radius: 24px !important;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82) !important;
}

.admin-config-page :deep(.el-card__header) {
  border-bottom: 1px solid #d8e5f4;
  color: #16355c;
  font-weight: 800;
}

.grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 960px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
