<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import AdminIntroHero from "../components/AdminIntroHero.vue";

const loading = ref(false);
const overview = ref<any>({});
const methodology = ref<any>({});

async function load() {
  loading.value = true;
  try {
    const [overviewRes, methodRes] = await Promise.all([
      api.get("/extensions/overview"),
      api.get("/extensions/methodology"),
    ]);
    overview.value = overviewRes.data ?? {};
    methodology.value = methodRes.data ?? {};
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载扩展说明失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="extensions-page" v-loading="loading">
    <AdminIntroHero eyebrow="扩展说明" title="扩展与答辩" :pill="overview.version_scope?.current_version || 'V1'" :description="overview.version_scope?.positioning || '当前页面用于说明版本边界、方法论和后续可扩展能力。'" />

    <el-card shadow="never" class="panel-card">
      <template #header>版本边界</template>
      <div class="chip-list">
        <span v-for="item in overview.version_scope?.not_in_scope ?? []" :key="item" class="chip">{{ item }}</span>
      </div>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <template #header>扩展能力</template>
      <div class="feature-list">
        <article v-for="item in overview.features ?? []" :key="item.key" class="feature-card">
          <div class="feature-card__top">
            <strong>{{ item.title }}</strong>
            <el-tag size="small">{{ item.status }}</el-tag>
          </div>
          <p>{{ item.summary }}</p>
          <div class="meta">适用角色：{{ item.owner }}</div>
          <div class="meta">当前范围：{{ item.scope }}</div>
        </article>
      </div>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <template #header>方法说明</template>
      <div class="feature-list">
        <article v-for="item in methodology.method_cards ?? []" :key="item.key" class="feature-card">
          <strong>{{ item.title }}</strong>
          <p>{{ item.summary }}</p>
          <div class="chip-list">
            <span v-for="focus in item.focus ?? []" :key="focus" class="chip">{{ focus }}</span>
          </div>
        </article>
      </div>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <template #header>答辩提醒</template>
      <div class="note-list">
        <div v-for="item in methodology.delivery_notes ?? []" :key="item" class="note-item">{{ item }}</div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.extensions-page {
  display: grid;
  gap: 20px;
}

.panel-card {
  border: 3px solid #1f2937;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(210, 238, 255, 0.72), transparent 42%),
    linear-gradient(180deg, #fff9f2 0%, #fffdf8 100%);
  box-shadow: 0 12px 0 rgba(31, 41, 55, 0.12);
}

.panel-card :deep(.el-card__header) {
  padding: 22px 26px 0;
  border-bottom: none;
  color: #16355c;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.panel-card :deep(.el-card__body) {
  padding: 22px 26px 26px;
}

.feature-list {
  display: grid;
  gap: 14px;
}

.feature-card {
  padding: 18px;
  border: 1.5px solid #c6d8ef;
  border-radius: 24px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  display: grid;
  gap: 10px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.feature-card__top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.meta {
  color: #64748b;
  font-size: 13px;
}

.chip-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  padding: 6px 10px;
  border-radius: 999px;
  background: #eef5ff;
  border: 1.5px solid #c6d8ef;
  color: #355070;
  font-size: 12px;
  font-weight: 700;
}

.note-list {
  display: grid;
  gap: 10px;
}

.note-item {
  padding: 14px 16px;
  border-radius: 20px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1.5px solid #c6d8ef;
  color: #51685a;
}

.feature-card strong {
  color: #16355c;
}

.feature-card p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.feature-card :deep(.el-tag) {
  border-radius: 999px;
  border-color: #c6d8ef;
  background: #eef5ff;
  color: #355070;
  font-weight: 700;
}
</style>
