<script setup lang="ts">
defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<{
  tip: string;
  placement?: "top" | "top-start" | "top-end" | "bottom" | "bottom-start" | "bottom-end" | "left" | "right";
  trigger?: "hover" | "click";
  delay?: number;
  hideAfter?: number;
  popperClass?: string;
}>(), {
  placement: "top",
  trigger: "hover",
  delay: 700,
  hideAfter: 100,
  popperClass: "app-tooltip-popper",
});
</script>

<template>
  <el-tooltip
    :content="tip"
    :placement="placement"
    :trigger="trigger"
    :show-after="delay"
    :hide-after="hideAfter"
    :popper-class="popperClass"
  >
    <el-button v-bind="$attrs" class="hint-button__inner">
      <slot />
    </el-button>
  </el-tooltip>
</template>
