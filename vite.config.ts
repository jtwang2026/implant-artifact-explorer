import vinext from "vinext";
import { defineConfig } from "vite";

// 精简配置：移除 Cloudflare 专属插件（build/sites-vite-plugin 与 @cloudflare/vite-plugin），
// 使 demo 可在本地/通用静态托管（如 GitHub Pages）构建。
// 原配置备份于 vite.config.ts.bak。
export default defineConfig({
  plugins: [vinext()],
});
