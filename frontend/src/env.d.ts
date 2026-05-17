/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";

  const component: DefineComponent<Record<string, never>, Record<string, never>, any>;
  export default component;
}

declare module "*.css";

declare module "https://cdn.jsdelivr.net/npm/hls.js@1.5.15/dist/hls.min.js" {
  const mod: any;
  export default mod;
}
