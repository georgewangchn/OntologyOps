export interface ProjectItem {
	id?: number;
	title: string
	title_en?: string
	description?: string
	date?: string
	detail?: string
	url?: string
	tags?: string[]
	cover?: string[]
}
export const projectItems: ProjectItem[] = [
	{
		title: "GovernanceOps",
		title_en: "Ontology-Driven Governance Operations",
		description: "用本体推理替代人工流转，让企业决策可验证、可追踪、可审计。OWL + SWRL + HermiT 推理引擎驱动。",
		date: "2025-05-01",
		detail: "/demo/index.html",
		url: "/demo/index.html",
		tags: ['OWL', '推理引擎', '企业治理']
	},
	{
		title: "OntologyOps",
		title_en: "Ontology as Code — CI/CD for Knowledge",
		description: "让本体像代码一样被管理，让知识像软件一样持续交付。版本化本体管理 + 自动推理验证。",
		date: "2025-01-15",
		detail: "https://github.com/georgewangchn/OntologyOps",
		url: "https://github.com/georgewangchn/OntologyOps",
		tags: ['开源', '本体管理', 'CI/CD']
	},
];
