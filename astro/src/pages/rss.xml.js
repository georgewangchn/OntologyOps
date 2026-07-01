import rss from "@astrojs/rss";
import { getCollection } from "astro:content";

export async function GET(context) {
  const blog = await getCollection('blog');
  return rss({
    title: '森林瀑布的博客',
    description: '《当LLM不够用了——本体推理的企业决策实践》作者。专注知识图谱、本体推理、LLM 与企业决策系统的融合落地。',
    site: context.site,
    items: blog.map((post) => ({
      title: post.data.title,
      pubDate: post.data.pubDate,
      description: post.data.description,
      // ...post.data,
      link: `/blog/${post.id}/`,
      stylesheet: '/rss/pretty-feed-v3.xsl',
    })),
  });
}
