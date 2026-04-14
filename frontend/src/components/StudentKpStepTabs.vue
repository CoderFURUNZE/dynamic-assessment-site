<script setup lang="ts">
export type WorkspaceView = "overview" | "resource" | "practice" | "review" | "next";

defineProps<{
  activeView: WorkspaceView;
  nextDisabled: boolean;
  nextDisabledReason: string;
}>();

const emit = defineEmits<{
  switch: [view: WorkspaceView];
}>();
</script>

<template>
  <section class="student-content-workflow">
    <button class="student-content-workflow__step" :class="{ active: activeView === 'overview' }" @click="emit('switch', 'overview')">
      1. 学习总览
    </button>
    <button class="student-content-workflow__step" :class="{ active: activeView === 'resource' }" @click="emit('switch', 'resource')">
      2. 资源学习
    </button>
    <button class="student-content-workflow__step" :class="{ active: activeView === 'practice' }" @click="emit('switch', 'practice')">
      3. 练习作答
    </button>
    <button class="student-content-workflow__step" :class="{ active: activeView === 'review' }" @click="emit('switch', 'review')">
      4. 错题复盘
    </button>
    <button
      class="student-content-workflow__step"
      :class="{ active: activeView === 'next' }"
      :disabled="nextDisabled"
      :title="nextDisabled ? nextDisabledReason : ''"
      @click="emit('switch', 'next')"
    >
      5. 下一步建议
    </button>
  </section>
</template>

<style scoped>
.student-content-workflow {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.student-content-workflow__step {
  border: 1.5px solid #c6d8ef;
  border-radius: 999px;
  background: #f8fbff;
  color: #3c587d;
  min-height: 44px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

.student-content-workflow__step.active {
  border-color: #96b6e2;
  background: #e8f1ff;
  color: #1f3a5c;
  box-shadow: 0 8px 14px rgba(31, 41, 55, 0.08);
}

.student-content-workflow__step:hover:not(:disabled) {
  border-color: #96b6e2;
  color: #1f3a5c;
}

@media (max-width: 1080px) {
  .student-content-workflow {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
