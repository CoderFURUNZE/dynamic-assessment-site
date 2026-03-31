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
  border: 1px solid #dce6f2;
  border-radius: 12px;
  background: #ffffff;
  color: #3c587d;
  min-height: 44px;
  padding: 0 10px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.student-content-workflow__step.active {
  border-color: #a8c5f8;
  background: linear-gradient(165deg, #f5f9ff 0%, #eef4fc 100%);
  color: #22549b;
}

@media (max-width: 1080px) {
  .student-content-workflow {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
