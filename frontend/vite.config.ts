import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
  },
  build: {
    // 优化构建输出
    target: "es2015",
    minify: "esbuild",
    // 启用 gzip 压缩
    cssCodeSplit: true,
    // 配置代码分割
    rollupOptions: {
      output: {
        manualChunks: {
          // 将第三方库单独打包
          vendor: ['vue', 'vue-router'],
          elementPlus: ['element-plus'],
          axios: ['axios'],
        },
      },
    },
  },
  // 优化静态资源处理
  assetsInclude: ['**/*.svg', '**/*.png', '**/*.jpg', '**/*.jpeg', '**/*.gif'],
  // 启用 CSS 模块化
  css: {
    modules: {
      localsConvention: 'camelCase',
    },
  },
});
