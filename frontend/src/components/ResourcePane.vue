<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type Resource = { id: number; kp_id: number; type: string; title: string; url: string };

const props = defineProps<{ kpId: number | null }>();
const emit = defineEmits<{ (e: "progress-updated"): void }>();

const resources = ref<Resource[]>([]);
const currentVideoId = ref<number | null>(null);
const videoRef = ref<HTMLVideoElement | null>(null);
const lastTick = ref<number>(Date.now());

const progressById = ref<Record<number, { watched_seconds: number; duration_seconds: number; completed: boolean }>>({});

const currentVideo = computed(() => resources.value.find((r) => r.id === currentVideoId.value) ?? null);
const videoResources = computed(() => resources.value.filter((r) => r.type === "video"));
const isBilibiliEmbed = computed(() => {
  const url = currentVideo.value?.url ?? "";
  return url.includes("player.bilibili.com/player.html");
});
const apiBase = (api.defaults.baseURL || "").replace(/\/api\/?$/, "");
const resolvedVideoUrl = computed(() => {
  const raw = currentVideo.value?.url ?? "";
  if (!raw) return "";
  if (raw.startsWith("http://") || raw.startsWith("https://") || raw.startsWith("//")) return raw;
  if (raw.startsWith("/")) return `${apiBase}${raw}`;
  return raw;
});
const isHls = computed(() => resolvedVideoUrl.value.includes(".m3u8"));
const videoSrc = computed(() => (isHls.value ? "" : resolvedVideoUrl.value));
const currentProgress = computed(() => {
  const id = currentVideoId.value;
  if (!id) return null;
  return progressById.value[id] ?? null;
});

async function loadProgress() {
  if (!props.kpId) return;
  try {
    const res = await api.get(`/content/video/progress?kp_id=${props.kpId}`);
    const map: Record<number, { watched_seconds: number; duration_seconds: number; completed: boolean }> = {};
    for (const row of res.data ?? []) {
      map[row.resource_id] = {
        watched_seconds: Number(row.watched_seconds ?? 0),
        duration_seconds: Number(row.duration_seconds ?? 0),
        completed: Boolean(row.completed),
      };
    }
    progressById.value = map;
  } catch {
    // ignore
  }
}

async function load() {
  if (!props.kpId) return;
  try {
    const res = await api.get(`/content/resources?kp_id=${props.kpId}`);
    resources.value = res.data;
    const firstVideo = videoResources.value[0];
    currentVideoId.value = firstVideo ? firstVideo.id : null;
    await loadProgress();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载资源失败");
  }
}

async function postProgress(payload: any) {
  const res = await api.post("/content/video/progress", payload);
  const rid = Number(res.data.resource_id);
  progressById.value[rid] = {
    watched_seconds: Number(res.data.watched_seconds ?? 0),
    duration_seconds: Number(res.data.duration_seconds ?? 0),
    completed: Boolean(res.data.completed),
  };
  emit("progress-updated");
}

async function tickMp4() {
  const v = videoRef.value;
  const r = currentVideo.value;
  if (!v || !r || !props.kpId) return;
  if (v.paused || v.ended) return;
  if (document.hidden) return;

  const now = Date.now();
  const delta = Math.max(0, (now - lastTick.value) / 1000);
  lastTick.value = now;

  try {
    await postProgress({
      kp_id: props.kpId,
      resource_id: r.id,
      position_seconds: v.currentTime,
      duration_seconds: Number.isFinite(v.duration) ? v.duration : 0,
      watched_delta_seconds: delta,
      playback_rate: v.playbackRate,
    });
  } catch {
    // ignore
  }
}

async function tickEmbed() {
  const r = currentVideo.value;
  if (!r || !props.kpId) return;
  if (document.hidden) return;

  const now = Date.now();
  const delta = Math.max(0, (now - lastTick.value) / 1000);
  lastTick.value = now;

  try {
    await postProgress({
      kp_id: props.kpId,
      resource_id: r.id,
      position_seconds: 0,
      duration_seconds: 0,
      watched_delta_seconds: delta,
      playback_rate: 1.0,
    });
  } catch {
    // ignore
  }
}

let timer: number | null = null;
let hls: any = null;

async function attachHls(url: string) {
  const v = videoRef.value;
  if (!v) return;
  if (hls?.destroy) {
    hls.destroy();
    hls = null;
  }
  try {
    const mod: any = await import(
      /* @vite-ignore */ "https://cdn.jsdelivr.net/npm/hls.js@1.5.15/dist/hls.min.js"
    );
    const HlsCtor = mod?.default ?? mod;
    if (HlsCtor && HlsCtor.isSupported && HlsCtor.isSupported()) {
      hls = new HlsCtor();
      hls.loadSource(url);
      hls.attachMedia(v);
      return;
    }
  } catch {
    // fall back to direct src
  }
  v.src = url;
}

function startTimer() {
  stopTimer();
  lastTick.value = Date.now();
  timer = window.setInterval(() => {
    if (isBilibiliEmbed.value) return tickEmbed();
    return tickMp4();
  }, 5000);
}

function stopTimer() {
  if (timer) window.clearInterval(timer);
  timer = null;
}

function onPlay() {
  lastTick.value = Date.now();
}

function onEmbedVisible() {
  lastTick.value = Date.now();
}

watch(
  () => props.kpId,
  () => load(),
  { immediate: true }
);

watch(
  () => currentVideoId.value,
  () => {
    lastTick.value = Date.now();
  }
);

watch(
  () => resolvedVideoUrl.value,
  (url) => {
    if (!url || isBilibiliEmbed.value) return;
    if (isHls.value) {
      attachHls(url);
    } else if (videoRef.value) {
      if (hls?.destroy) {
        hls.destroy();
        hls = null;
      }
      videoRef.value.src = url;
    }
  }
);

onMounted(() => {
  startTimer();
});

onBeforeUnmount(() => {
  stopTimer();
  if (hls?.destroy) hls.destroy();
});
</script>

<template>
  <el-card>
    <template #header>学习资源（视频嵌入 + 进度上报）</template>
    <div v-if="!kpId">
      <el-text type="info">请选择知识点</el-text>
    </div>
    <div v-else>
      <div v-if="videoResources.length > 1" style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px">
        <el-select v-model="currentVideoId" placeholder="选择视频资源" style="width: 100%">
          <el-option v-for="r in videoResources" :key="r.id" :label="r.title" :value="r.id" />
        </el-select>
      </div>

      <div v-if="currentVideo">
        <iframe
          v-if="isBilibiliEmbed"
          :src="currentVideo.url"
          style="width: 100%; height: 520px; border: 0; border-radius: 8px; background: #000"
          allowfullscreen
          @load="onEmbedVisible"
        />
        <video
          v-else
          ref="videoRef"
          :src="videoSrc"
          controls
          style="width: 100%; border-radius: 8px; background: #000"
          @play="onPlay"
        />

        <el-alert
          style="margin-top: 10px"
          type="info"
          title="说明"
          description="系统只保存观看/停留进度（秒数/完成度），不保存视频画面。B站 iframe 只能记录停留时长。"
          show-icon
        />

        <el-text v-if="currentProgress" type="info" style="display: inline-block; margin-top: 8px">
          已记录：{{ Math.round(currentProgress.watched_seconds) }} 秒
          <span v-if="currentProgress.duration_seconds > 0">
            （约 {{ Math.round((currentProgress.watched_seconds / currentProgress.duration_seconds) * 100) }}%）
          </span>
        </el-text>
      </div>

      <div v-else>
        <el-text type="warning">当前知识点未配置视频资源</el-text>
      </div>
    </div>
  </el-card>
</template>
