<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const props = withDefaults(defineProps<{ compact?: boolean }>(), {
  compact: false,
});

const loading = ref(false);
const features = ref<Array<Record<string, any>>>([]);
const methodCards = ref<Array<Record<string, any>>>([]);
const demoFlow = ref<string[]>([]);
const emptyStates = ref<Array<Record<string, string>>>([]);

async function load() {
  loading.value = true;
  try {
    const [featureRes, methodRes] = await Promise.all([
      api.get("/extensions/overview"),
      api.get("/extensions/methodology"),
    ]);
    features.value = featureRes.data?.features ?? [];
    methodCards.value = methodRes.data?.method_cards ?? [];
    demoFlow.value = methodRes.data?.demo_flow ?? [];
    emptyStates.value = methodRes.data?.empty_states ?? [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载扩展说明失败");
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.compact,
  () => load(),
  { immediate: true }
);
</script>

<template>
  <div class="extension-shell" v-loading="loading">
    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="extension-header">
          <div>
            <div class="extension-title">系统说明与扩展占位</div>
            <div class="extension-subtitle">用于导师检查和答辩演示，说明当前主线怎么跑，以及哪些扩展功能已经预留入口。</div>
          </div>
          <el-button size="small" @click="load" :loading="loading">刷新</el-button>
        </div>
      </template>

      <div class="method-grid">
        <section v-for="card in methodCards" :key="card.key" class="method-card">
          <div class="method-card__title">{{ card.title }}</div>
          <div class="method-card__summary">{{ card.summary }}</div>
          <div class="method-card__list">
            <span v-for="item in card.focus || []" :key="item" class="method-pill">{{ item }}</span>
          </div>
        </section>
      </div>
    </el-card>

    <div class="extension-grid" :class="{ 'extension-grid--compact': compact }">
      <el-card class="panel-card" shadow="never">
        <template #header>扩展功能占位</template>
        <div class="feature-list">
          <div v-for="item in features" :key="item.key" class="feature-card">
            <div class="feature-card__top">
              <div>
                <div class="feature-card__title">{{ item.title }}</div>
                <div class="feature-card__owner">负责端：{{ item.owner }}</div>
              </div>
              <el-tag type="info">后续扩展</el-tag>
            </div>
            <div class="feature-card__summary">{{ item.summary }}</div>
            <div class="feature-card__scope">{{ item.scope }}</div>
          </div>
        </div>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>答辩演示路径</template>
        <ol class="demo-list">
          <li v-for="item in demoFlow" :key="item">{{ item }}</li>
        </ol>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>空状态兜底</template>
        <div class="empty-state-list">
          <div v-for="item in emptyStates" :key="item.scenario" class="empty-state-card">
            <div class="empty-state-card__title">{{ item.scenario }}</div>
            <div class="empty-state-card__text">{{ item.advice }}</div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.extension-shell {
  display: grid;
  gap: 16px;
}

.extension-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.extension-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-ink);
}

.extension-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-ink-soft);
}

.method-grid,
.extension-grid,
.feature-list,
.empty-state-list {
  display: grid;
  gap: 14px;
}

.method-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.extension-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.extension-grid--compact {
  grid-template-columns: 1fr;
}

.method-card,
.feature-card,
.empty-state-card {
  padding: 16px;
  border-radius: 18px;
  background: #f7fafc;
  border: 1px solid #dee7ef;
}

.method-card {
  display: grid;
  gap: 10px;
}

.method-card__title,
.feature-card__title,
.empty-state-card__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-ink);
}

.method-card__summary,
.feature-card__summary,
.feature-card__scope,
.empty-state-card__text {
  font-size: 13px;
  line-height: 1.7;
  color: #5b7797;
}

.method-card__list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.method-pill {
  padding: 4px 8px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #d8e4ee;
  font-size: 12px;
  color: #52708f;
}

.feature-card {
  display: grid;
  gap: 8px;
}

.feature-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.feature-card__owner {
  margin-top: 4px;
  font-size: 12px;
  color: #6b87a4;
}

.demo-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
  color: var(--app-ink);
  line-height: 1.7;
}

@media (max-width: 1100px) {
  .extension-grid,
  .method-grid {
    grid-template-columns: 1fr;
  }
}
</style>
