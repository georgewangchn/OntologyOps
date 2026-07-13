// ── 森林瀑布的博客 — 站点配置 ──

export const siteConfig = {
    siteName: import.meta.env.PUBLIC_SITE_NAME,
    siteUrl: import.meta.env.PUBLIC_SITE_URL,
}

interface NavItem { label: string; href: string; target?: string }

interface Nav { avatar?: string; items?: NavItem[] }

export const nav: Nav = {
	avatar:'/assets/author.png',
    items: [
        { label: '首页', href: '/', target: '_self' },
        { label: '著作', href: '/book/index.html', target: '_self' },
        { label: '项目', href: '/project/', target: '_self' },
        { label: '博客', href: '/blog/', target: '_self' },
        { label: '关于', href: '/about/', target: '_self' },
    ],
};

export const footerText = `© ${new Date().getFullYear()} 森林瀑布. All Rights Reserved.`

// ── SEO TDK ──

interface SeoTdk { title?: string; description?: string; keywords?: string }

export const homeTdk: SeoTdk = {
	title: '森林瀑布的博客 — 本体推理、知识工程与 AI 探索',
	description: '《当LLM不够用了——本体推理的企业决策实践》作者。专注知识图谱、本体推理、LLM 与企业决策系统的融合落地。',
	keywords: '森林瀑布,本体推理,知识图谱,LLM,OWL,SWRL,Prolog,Jena,模糊推理,Agent,企业决策',
}

export const blogTdk: SeoTdk = {
	title: '博客 — 森林瀑布',
	description: '多范式推理实战营：P1-P4 系列文章，从 OWL/HermiT 到模糊逻辑，同一问题四种推理范式。',
	keywords: '本体推理,OWL,Prolog,Jena,SPARQL,模糊逻辑,多范式推理',
}

export const aboutTdk: SeoTdk = {
	title: '关于 — 森林瀑布',
	description: '《当LLM不够用了——本体推理的企业决策实践》作者，知识图谱与本体推理领域实践者。',
	keywords: '森林瀑布,本体推理,知识图谱,作者',
}

export const seriesTdk: SeoTdk = {
	title: '《当LLM不够用了》— 森林瀑布',
	description: '从 OWL 公理到企业落地 — 完整 12 章在线阅读。本体推理的企业决策实践。',
	keywords: '本体推理,OWL,企业决策,知识工程,书籍,森林瀑布',
}

export const projectTdk: SeoTdk = {
	title: '开源项目 — 森林瀑布',
	description: 'GovernanceOps 企业治理运维 + OntologyOps 本体即代码 — 两个基于本体推理的开源项目。',
	keywords: '本体推理,GovernanceOps,OntologyOps,开源,OWL,企业治理',
}

export const notFoundTdk: SeoTdk = {
	title: '404 — 森林瀑布的博客',
	description: '404 Not Found — 这里什么都没有。',
	keywords: '404',
}

// ── 社交链接 ──

export const socialLinks = [
	{
		name: 'Github',
		url: 'https://github.com/georgewangchn/OntologyOps',
		icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>`
	},
	{
	  name: 'Zhihu',
	  url: 'https://www.zhihu.com/people/senlinpubu',
	  icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M13.325 17.32h-2.65v-2.66h2.65v2.66zM8.9 6.84h4.425v1.62H8.9v-1.62zm5.77 1.62h-1.35V6.84h1.35v1.62zM13.3 13.3h-2.65v-2.66h2.65v2.66zm-4.4 0H6.25v-2.66H8.9v2.66zm5.75 0h-1.35v-2.66h1.35v2.66zm-4.4 4.02H7.6v-2.66h2.65v2.66zm5.75 0h-1.35v-2.66h1.35v2.66zM13.3 9.18h-2.65V6.52h2.65v2.66zM5.42 12c0-5.51 4.47-10 9.98-10 5.52 0 10 4.49 10 10s-4.48 10-10 10c-5.51 0-9.98-4.49-9.98-10z"/></svg>`
	},
	{
		name: 'RSS',
		url: '/rss.xml',
		icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/></svg>`
	},
];

// ── 页面 Tag ──

interface PageTag { index: string; about: string; blog: string; project: string }
export const pageTag: PageTag = {
	index: 'ONTOLOGY',
	about: 'ABOUT',
	blog: 'BLOG',
	project: 'OPEN SOURCE',
}

// ── 页面描述 ──

interface PageDescription { index?: string; project?: string; blog?: string; about?: string }
export const pageDescription: PageDescription = {
	index: '《当LLM不够用了——本体推理的企业决策实践》作者。专注知识图谱、本体推理、LLM 与企业决策系统的融合落地。',
	project: '两个基于本体推理的开源项目 — GovernanceOps · OntologyOps',
	about: '知识图谱与本体推理领域实践者',
	blog: '记录我在本体推理、知识工程与 AI 探索过程中的思考和笔记。',
}

// ── 首页分类筛选 ──

export interface FilterItem { content: string; dataGroup: string }
export const filterItems: FilterItem[] = [
	{ content: "OWL", dataGroup: "owl" },
	{ content: "Prolog", dataGroup: "prolog" },
	{ content: "Jena", dataGroup: "jena" },
	{ content: "模糊逻辑", dataGroup: "fuzzy" },
	{ content: "贝叶斯", dataGroup: "bayesian" },
	{ content: "仲裁", dataGroup: "arbiter" },
	{ content: "Agent", dataGroup: "agent" },
];