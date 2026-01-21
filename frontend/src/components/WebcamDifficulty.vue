<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { getToken } from "../token";

const props = defineProps<{
  kpId: number | null;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const wsRef = ref<WebSocket | null>(null);
const running = ref(false);
const enabled = ref<boolean>(localStorage.getItem("da_webcam_enabled") !== "0");

const difficulty = ref<number>(0.5);
const label = ref<string>("idle");
const confidence = ref<number>(0);

const isDragging = ref(false);
const dragOffset = ref({ x: 0, y: 0 });

function onDragStart(ev: MouseEvent) {
  const target = ev.currentTarget as HTMLElement | null;
  if (!target) return;
  isDragging.value = true;
  dragOffset.value = { x: ev.offsetX, y: ev.offsetY };
}

function onDragMove(ev: MouseEvent) {
  if (!isDragging.value) return;
  const win = window;
  const x = Math.max(0, Math.min(win.innerWidth - 420, ev.clientX - dragOffset.value.x));
  const y = Math.max(0, Math.min(win.innerHeight - 280, ev.clientY - dragOffset.value.y));
  win.document.documentElement.style.setProperty("--float-x", `${x}px`);
  win.document.documentElement.style.setProperty("--float-y", `${y}px`);
}

function onDragEnd() {
  isDragging.value = false;
}

const labelText = computed(() => {
  if (label.value === "strained") return "吃力/皱眉";
  if (label.value === "confused") return "困惑";
  if (label.value === "neutral") return "中性";
  if (label.value === "focused") return "专注";
  if (label.value === "relaxed") return "轻松";
  if (label.value === "fidgeting") return "抓耳挠腮/烦躁";
  if (label.value === "distracted") return "吃东西/分心";
  if (label.value === "no_face") return "未检测到人脸";
  return label.value;
});

async function startCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  if (!videoRef.value) return;
  videoRef.value.srcObject = stream;
  await videoRef.value.play();
  running.value = true;
}

function stopCamera() {
  const v = videoRef.value;
  const stream = v?.srcObject as MediaStream | null;
  if (stream) stream.getTracks().forEach((t) => t.stop());
  if (v) v.srcObject = null;
  running.value = false;
}

function connectWs() {
  const token = getToken();
  if (!token) return;
  wsRef.value?.close();
  wsRef.value = new WebSocket(`ws://localhost:8000/api/vision/ws?token=${encodeURIComponent(token)}`);
  wsRef.value.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data?.type === "error") {
        ElMessage.error(String(data?.detail ?? "表情服务错误"));
        enabled.value = false;
        return;
      }

      const d = Number(data?.difficulty);
      const c = Number(data?.confidence);
      const l = data?.label;
      if (Number.isFinite(d)) difficulty.value = d;
      if (Number.isFinite(c)) confidence.value = c;
      if (typeof l === "string" && l) label.value = l;
    } catch {
      // ignore
    }
  };
  wsRef.value.onerror = () => {
    ElMessage.error("WebSocket 连接失败");
  };
  wsRef.value.onclose = () => {
    if (enabled.value) {
      ElMessage.warning("表情服务连接已断开");
      enabled.value = false;
    }
  };
}

function sendFrame() {
  const ws = wsRef.value;
  const v = videoRef.value;
  const c = canvasRef.value;
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!v || !c) return;
  if (!props.kpId) return;

  const w = 480;
  const h = Math.round((v.videoHeight / v.videoWidth) * w) || 240;
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d");
  if (!ctx) return;
  ctx.drawImage(v, 0, 0, w, h);
  const dataUrl = c.toDataURL("image/jpeg", 0.6);
  const image_b64 = dataUrl.split(",")[1];
  ws.send(JSON.stringify({ type: "frame", image_b64, kp_id: props.kpId, ts: Date.now() }));
}

let timer: number | null = null;

function startLoop() {
  if (timer) window.clearInterval(timer);
  timer = window.setInterval(() => sendFrame(), 350);
}

function stopLoop() {
  if (timer) window.clearInterval(timer);
  timer = null;
}

watch(
  () => props.kpId,
  () => {
    // keep running, frames will include current kpId
  }
);

async function startAll() {
  if (!enabled.value) return;
  if (running.value) return;
  try {
    await startCamera();
    connectWs();
    startLoop();
  } catch (e: any) {
    ElMessage.error(e?.message ?? "无法打开摄像头（请允许权限，并使用 http://localhost 访问）");
    enabled.value = false;
    localStorage.setItem("da_webcam_enabled", "0");
  }
}

function stopAll() {
  stopLoop();
  wsRef.value?.close();
  stopCamera();
  label.value = "idle";
  difficulty.value = 0.5;
  confidence.value = 0;
}

watch(
  () => enabled.value,
  (v) => {
    localStorage.setItem("da_webcam_enabled", v ? "1" : "0");
    if (v) startAll();
    else stopAll();
  }
);

onMounted(async () => {
  window.addEventListener("mousemove", onDragMove);
  window.addEventListener("mouseup", onDragEnd);
  await startAll();
});

onBeforeUnmount(() => {
  stopAll();
  window.removeEventListener("mousemove", onDragMove);
  window.removeEventListener("mouseup", onDragEnd);
});
</script>

<template>
  <el-card class="panel-card float-panel-card">
    <template #header>
      <div
        style="cursor: move; user-select: none"
        @mousedown="onDragStart"
      >
        实时表情（不保存视频）
      </div>
    </template>
    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-bottom: 8px">
      <el-text type="info">表情采集</el-text>
      <el-switch v-model="enabled" active-text="开启" inactive-text="关闭" />
    </div>
    <el-alert
      style="margin-bottom: 10px"
      type="info"
      :closable="false"
      title="隐私提示"
      description="仅在本机摄像头实时采集并上传低清压缩帧用于表情难度估计；系统不保存视频帧，只记录难度/置信度等数值。"
      show-icon
    />
    <div style="display: grid; grid-template-columns: 220px 1fr; gap: 12px; align-items: start">
      <div>
        <video
          ref="videoRef"
          style="width: 100%; border-radius: 8px; background: #000; transform: scaleX(-1)"
          playsinline
          muted
        />
        <canvas ref="canvasRef" style="display: none" />
      </div>
      <div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="状态">{{ running ? "采集中" : "未启动" }}</el-descriptions-item>
          <el-descriptions-item label="标签">{{ labelText }}</el-descriptions-item>
          <el-descriptions-item label="困难度">{{ difficulty.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ confidence.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="知识点">
            <el-text type="info">{{ props.kpId ?? "未选择" }}</el-text>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </el-card>
</template>
