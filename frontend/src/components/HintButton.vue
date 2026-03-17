<script setup lang="ts">
defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<{
  tip: string;
  delay?: number;
}>(), {
  delay: 700,
});
</script>

<template>
  <el-tooltip :content="tip" :show-after="delay" placement="top">
    <el-button v-bind="$attrs">
      <slot />
    </el-button>
  </el-tooltip>
</template>
