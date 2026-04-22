import { createApp } from "vue";
import { ElLoading } from "element-plus";
import "element-plus/es/components/loading/style/css";
import "element-plus/es/components/message/style/css";
import "element-plus/es/components/message-box/style/css";
import "./fonts.css";
import "./styles.css";

import App from "./App.vue";
import { router } from "./router";

createApp(App).use(router).use(ElLoading).mount("#app");
