<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import ResourcePane from "../components/ResourcePane.vue";
import MiniQuizPane from "../components/MiniQuizPane.vue";
import QuizPane from "../components/QuizPane.vue";
import { getUsername } from "../token";

type KP = { id: number; code: string; title: string; subject: string; grade: string };

const router = useRouter();
const subject = ref("数据结构");
const grade = ref("通用");
const kps = ref<KP[]>([]);
const currentKpId = ref<number | null>(null);
const activeSection = ref<"resource" | "quiz" | "practice">("resource");

function kpStorageKey() {
  const username = getUsername() || localStorage.getItem("da_last_user") || "guest";
  return `da_kp_preview_${username}_${subject.value}`;
}

async function loadKps() {
  try {
    const res = await api.get(`/graph/kps?subject=${encodeURIComponent(subject.value)}&grade=${encodeURIComponent(grade.value)}`);
    kps.value = res.data;
    const saved = localStorage.getItem(kpStorageKey());
    if (saved) {
      const savedId = Number(saved);
      const exists = kps.value.some((k) => k.id === savedId);
      if (exists) {
        currentKpId.value = savedId;
        return;
      }
    }
    if (!currentKpId.value && kps.value.length) currentKpId.value = kps.value[0].id;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载知识点失败");
  }
}

function onKpChange() {
  if (currentKpId.value) {
    localStorage.setItem(kpStorageKey(), String(currentKpId.value));
  }
}

onMounted(() => loadKps());
</script>

<template>
  <el-card class="panel-card" shadow="never">
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap">
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
        <el-select v-model="subject" style="width: 180px" @change="loadKps">
          <el-option label="数据结构" value="数据结构" />
          <el-option label="计算机组成原理" value="计算机组成原理" />
          <el-option label="操作系统" value="操作系统" />
          <el-option label="计算机网络" value="计算机网络" />
        </el-select>
        <el-select v-model="currentKpId" placeholder="选择知识点" style="width: 320px" @change="onKpChange">
          <el-option v-for="kp in kps" :key="kp.id" :label="`${kp.code} ${kp.title}`" :value="kp.id" />
        </el-select>
      </div>
      <el-button type="default" @click="router.push('/admin/config')">返回管理端</el-button>
    </div>
  </el-card>

  <div style="height: 10px" />

  <el-tabs v-model="activeSection" type="border-card" class="panel-card">
    <el-tab-pane label="学习资源" name="resource">
      <ResourcePane :kp-id="currentKpId" />
    </el-tab-pane>
    <el-tab-pane label="小测预览" name="quiz">
      <MiniQuizPane :kp-id="currentKpId" preview />
    </el-tab-pane>
    <el-tab-pane label="练习题预览" name="practice">
      <QuizPane :kp-id="currentKpId" preview />
    </el-tab-pane>
  </el-tabs>
</template>
