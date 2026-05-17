import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

export default defineConfig({
  plugins: [
    vue(),
    Components({
      dts: false,
      resolvers: [ElementPlusResolver({ importStyle: "css" })],
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // 优化构建输出
    target: "es2015",
    minify: "esbuild",
    // 启用 gzip 压缩
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/axios")) return "axios";
          if (id.includes("node_modules/vue") || id.includes("node_modules/vue-router")) {
            return "vendor";
          }
          return undefined;
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
