<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

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
    <section class="hero panel-card">
      <div>
        <p class="eyebrow">Extensions</p>
        <h1>扩展与答辩说明</h1>
        <p>{{ overview.version_scope?.positioning || "当前页用于说明版本边界、方法论和后续可扩展能力。" }}</p>
      </div>
      <el-tag type="info" size="large">{{ overview.version_scope?.current_version || "V1" }}</el-tag>
    </section>

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
.extensions-page { display: grid; gap: 20px; }
.hero { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.eyebrow { margin: 0 0 8px; font-size: 12px; font-weight: 800; color: #6b7d91; text-transform: uppercase; }
h1 { margin: 0; font-size: 28px; color: #1f2d3d; }
p { color: #62748a; line-height: 1.7; }
.feature-list { display: grid; gap: 14px; }
.feature-card { padding: 16px; border: 1px solid #e3ebf5; border-radius: 18px; background: #fff; display: grid; gap: 8px; }
.feature-card__top { display: flex; justify-content: space-between; gap: 12px; }
.meta { color: #6b7d91; font-size: 13px; }
.chip-list { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 6px 10px; border-radius: 999px; background: #f3f7fc; color: #4f6988; font-size: 12px; }
.note-list { display: grid; gap: 10px; }
.note-item { padding: 12px 14px; border-radius: 14px; background: #f8fbff; border: 1px solid #e3ebf5; }
</style>
