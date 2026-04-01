<script setup lang="ts">
defineOptions({ inheritAttrs: false });

defineProps<{
  tip?: string;
  placement?: "top" | "top-start" | "top-end" | "bottom" | "bottom-start" | "bottom-end" | "left" | "right";
  trigger?: "hover" | "click";
  delay?: number;
  hideAfter?: number;
  popperClass?: string;
}>();
</script>

<template>
  <el-button v-bind="$attrs" class="hint-button__inner">
    <slot />
  </el-button>
</template>
