<script setup lang="ts">
withDefaults(defineProps<{
  content: string;
  placement?: "top" | "top-start" | "top-end" | "bottom" | "bottom-start" | "bottom-end" | "left" | "right";
  trigger?: "hover" | "click";
  showAfter?: number;
}>(), {
  placement: "top",
  trigger: "hover",
  showAfter: 300,
});
</script>

<template>
  <span class="hover-tip" aria-hidden="true"></span>
</template>

<style scoped>
.hover-tip {
  display: none;
}
</style>
