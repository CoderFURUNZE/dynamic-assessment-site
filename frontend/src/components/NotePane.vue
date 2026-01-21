<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const props = defineProps<{ kpId: number | null }>();

type Status = { kp_id: number; total_questions: number; attempted_questions: number; completed: boolean };
type Note = { id: number; kp_id: number; author: string; content: string; created_at: string };

const status = ref<Status | null>(null);
const notes = ref<Note[]>([]);
const content = ref("");
const loading = ref(false);

const completed = computed(() => Boolean(status.value?.completed));

async function loadStatus() {
  if (!props.kpId) return;
  const res = await api.get(`/practice/status?kp_id=${props.kpId}`);
  status.value = res.data;
}

async function loadNotes() {
  if (!props.kpId) return;
  const res = await api.get(`/notes?kp_id=${props.kpId}`);
  notes.value = res.data;
}

async function refresh() {
  if (!props.kpId) return;
  loading.value = true;
  try {
    await loadStatus();
    if (completed.value) {
      await loadNotes();
    } else {
      notes.value = [];
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载笔记失败");
  } finally {
    loading.value = false;
  }
}

async function post() {
  if (!props.kpId) return;
  if (!completed.value) {
    ElMessage.warning("完成全部练习题后才能发表笔记");
    return;
  }
  const text = content.value.trim();
  if (text.length < 3) {
    ElMessage.warning("笔记内容太短");
    return;
  }
  try {
    await api.post("/notes", { kp_id: props.kpId, content: text });
    content.value = "";
    ElMessage.success("已发布");
    await loadNotes();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "发布失败");
  }
}

watch(
  () => props.kpId,
  () => refresh(),
  { immediate: true }
);

onMounted(() => refresh());
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between">
        <div>学习笔记（完成练习后可见）</div>
        <el-button size="small" @click="refresh" :loading="loading">刷新</el-button>
      </div>
    </template>

    <div v-if="!kpId">
      <el-text type="info">请选择知识点</el-text>
    </div>
    <div v-else>
      <el-alert
        v-if="status"
        type="info"
        :title="`练习进度：${status.attempted_questions}/${status.total_questions}`"
        :description="completed ? '已完成练习：可以发表笔记并查看同学笔记。' : '完成全部练习题后才能查看同学笔记与发表笔记。'"
        show-icon
      />

      <div style="margin-top: 10px">
        <el-input
          v-model="content"
          type="textarea"
          :rows="3"
          placeholder="写下你对该知识点的总结/易错点/解题技巧…"
        />
        <div style="margin-top: 8px; display: flex; gap: 8px">
          <el-button type="primary" :disabled="!completed" @click="post">发布笔记</el-button>
        </div>
      </div>

      <div style="margin-top: 12px">
        <el-empty v-if="completed && notes.length === 0" description="暂无笔记" />
        <el-timeline v-else-if="completed">
          <el-timeline-item v-for="n in notes" :key="n.id" :timestamp="n.created_at">
            <div style="font-weight: 600">{{ n.author }}</div>
            <div style="white-space: pre-wrap">{{ n.content }}</div>
          </el-timeline-item>
        </el-timeline>
        <el-text v-else type="info">完成练习后将显示同学笔记列表。</el-text>
      </div>
    </div>
  </el-card>
</template>
