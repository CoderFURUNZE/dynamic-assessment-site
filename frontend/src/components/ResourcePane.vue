<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

type Resource = {
  id: number;
  kp_id: number;
  type: string;
  title: string;
  url: string;
  category?: string;
  description?: string;
  tags?: string;
  preview_type?: string;
  preview_status?: string;
  preview_error?: string;
  converted_preview_url?: string;
  original_file_url?: string;
  detected_resource_type?: string;
  original_file_name?: string;
};

const props = defineProps<{ kpId: number | null }>();
const emit = defineEmits<{ (e: "progress-updated"): void }>();

const resources = ref<Resource[]>([]);
const currentResourceId = ref<number | null>(null);
const videoRef = ref<HTMLVideoElement | null>(null);
const iframeRef = ref<HTMLIFrameElement | null>(null);
const lastTick = ref<number>(Date.now());

const progressById = ref<Record<number, { watched_seconds: number; duration_seconds: number; completed: boolean }>>({});

const currentResource = computed(() => resources.value.find((r) => r.id === currentResourceId.value) ?? null);
const learningResources = computed(() => resources.value.filter((r) => !["book", "recommend_book"].includes(r.type)));
const videoResources = computed(() => learningResources.value.filter((r) => r.preview_type === "video_inline"));
const isBilibiliEmbed = computed(() => {
  const url = currentResource.value?.url ?? "";
  return url.includes("player.bilibili.com/player.html");
});
const apiBase = (api.defaults.baseURL || "").replace(/\/api\/?$/, "");
const resolvedVideoUrl = computed(() => {
  const raw = currentResource.value?.converted_preview_url || currentResource.value?.url || "";
  if (!raw) return "";
  if (raw.startsWith("http://") || raw.startsWith("https://") || raw.startsWith("//")) return raw;
  if (raw.startsWith("/")) return `${apiBase}${raw}`;
  return raw;
});
const isHls = computed(() => resolvedVideoUrl.value.includes(".m3u8"));
const videoSrc = computed(() => (isHls.value ? "" : resolvedVideoUrl.value));
const currentProgress = computed(() => {
  const id = currentResourceId.value;
  if (!id) return null;
  return progressById.value[id] ?? null;
});
const canInlinePdfPreview = computed(
  () =>
    Boolean(
      resolvedVideoUrl.value &&
      currentResource.value &&
      currentResource.value.preview_status === "ready" &&
      ["pdf_inline", "pdf_after_convert"].includes(currentResource.value.preview_type || ""),
    ),
);
const currentPreviewLabel = computed(() => {
  const previewType = currentResource.value?.preview_type || "";
  if (previewType === "pdf_after_convert") return "预览版 PDF，原文件为 Office 文档";
  if (previewType === "pdf_inline") return "PDF 在线预览";
  if (previewType === "video_inline") return "视频在线播放";
  if (previewType === "image_inline") return "图片在线预览";
  return "资源访问";
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
    currentResourceId.value = learningResources.value[0]?.id ?? null;
    await loadProgress();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? "加载资源失败");
  }
}

function openSupportResource(resource: Resource) {
  window.open(resource.original_file_url || resource.url, "_blank", "noopener,noreferrer");
  emit("progress-updated");
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
  const r = currentResource.value;
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
  const r = currentResource.value;
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
  () => currentResourceId.value,
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
    <template #header>学习资源</template>
    <div v-if="!kpId">
      <el-text type="info">请选择知识点</el-text>
    </div>
    <div v-else>
      <div v-if="learningResources.length > 0" style="display: grid; gap: 10px; margin-bottom: 14px">
        <el-select v-model="currentResourceId" placeholder="选择学习资源" style="width: 100%">
          <el-option v-for="r in learningResources" :key="r.id" :label="r.title" :value="r.id" />
        </el-select>
        <div style="display: flex; gap: 8px; flex-wrap: wrap">
          <el-tag
            v-for="r in learningResources"
            :key="r.id"
            :type="r.id === currentResourceId ? 'primary' : 'info'"
            effect="plain"
            style="cursor: pointer"
            @click="currentResourceId = r.id"
          >
            {{ r.title }}
          </el-tag>
        </div>
      </div>

      <div v-if="currentResource">
        <el-alert
          v-if="currentResource.preview_status === 'processing'"
          type="warning"
          :title="`${currentResource.title} 还在处理中`"
          description="Office 文档会先转换成 PDF，稍后刷新即可在线预览。"
          show-icon
          style="margin-bottom: 12px"
        />
        <el-alert
          v-else-if="currentResource.preview_status === 'failed'"
          type="error"
          :title="`${currentResource.title} 预览转换失败`"
          :description="currentResource.preview_error || '当前资源暂时只能下载查看'"
          show-icon
          style="margin-bottom: 12px"
        />
        <div>
          <iframe
            v-if="isBilibiliEmbed"
            ref="iframeRef"
            :src="currentResource.url"
            style="width: 100%; height: 520px; border: 0; border-radius: 8px; background: #000"
            @load="onEmbedVisible"
          />
          <iframe
            v-else-if="canInlinePdfPreview"
            ref="iframeRef"
            :src="resolvedVideoUrl"
            style="width: 100%; height: 620px; border: 1px solid var(--app-border); border-radius: 12px; background: #fff"
          />
          <img
            v-else-if="currentResource.preview_type === 'image_inline' && resolvedVideoUrl"
            :src="resolvedVideoUrl"
            :alt="currentResource.title"
            style="max-width: 100%; max-height: 620px; border-radius: 12px; border: 1px solid var(--app-border); background: #fff; object-fit: contain"
          />
          <video
            v-else-if="currentResource.preview_type === 'video_inline'"
            ref="videoRef"
            :src="videoSrc"
            controls
            style="width: 100%; border-radius: 8px; background: #000"
            @play="onPlay"
          />
          <div
            v-else
            style="display: grid; gap: 12px; padding: 18px; border: 1px dashed var(--app-border); border-radius: 12px; background: #fafbfd"
          >
            <strong style="color: var(--app-ink)">{{ currentResource.title }}</strong>
            <el-text type="info">当前资源不支持直接内嵌，点击按钮查看或下载。</el-text>
            <div style="display: flex; gap: 10px; flex-wrap: wrap">
              <el-button type="primary" @click="openSupportResource(currentResource)">打开资源</el-button>
              <el-button v-if="currentResource.original_file_url" @click="openSupportResource({ ...currentResource, url: currentResource.original_file_url })">下载原文件</el-button>
            </div>
          </div>
        </div>

        <el-alert
          style="margin-top: 10px"
          type="info"
          :title="currentPreviewLabel"
          :description="currentResource.preview_type === 'video_inline'
            ? '系统只保存观看进度，不保存视频画面。B 站 iframe 只能记录停留时长。'
            : ['pdf_inline', 'pdf_after_convert'].includes(currentResource.preview_type || '')
              ? currentResource.preview_type === 'pdf_after_convert'
                ? '当前展示的是系统自动转换后的 PDF 预览版，学生无需先下载。需要原文件时可单独下载。'
                : '当前资源展示的是在线 PDF 预览版，学生无需先下载。'
              : currentResource.preview_type === 'image_inline'
                ? '当前资源以图片方式直接在线预览。'
                : '当前资源通过外部地址或原文件打开。'"
          show-icon
        />

        <el-text v-if="currentResource.preview_type === 'video_inline' && currentProgress" type="info" style="display: inline-block; margin-top: 8px">
          已记录：{{ Math.round(currentProgress.watched_seconds) }} 秒
          <span v-if="currentProgress.duration_seconds > 0">
            （约 {{ Math.round((currentProgress.watched_seconds / currentProgress.duration_seconds) * 100) }}%）
          </span>
        </el-text>
      </div>

      <div v-else>
        <el-text type="warning">当前知识点未配置学习资源</el-text>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
</style>
