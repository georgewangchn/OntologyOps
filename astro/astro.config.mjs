// https://astro.build/config
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
const SITE_URL = process.env.PUBLIC_SITE_URL || 'https://senlinpubu.top';
export default defineConfig({
  devToolbar: {
    enabled: false,
  },
  markdown: {
    shikiConfig: {
    theme: "github-dark",
    wrap: true,
    }
  },
  envPrefix: 'PUBLIC_',
  site: SITE_URL,
  base: '/',
  integrations: [sitemap({
    changefreq: 'weekly',
    priority: 0.7,
    lastmod: new Date(),
    customPages: ['https://senlinpubu.top/book/index.html'],
    serialize(item) {
      // 给书籍页面更高优先级
      if (item.url.includes('/book/')) {
        item.priority = 0.8;
        item.changefreq = 'monthly';
      }
      return item;
    },
  }), mdx()],
  css: {
    preprocessorOptions: {
      sass: {
        api: "modern",
      },
    },
  },
})