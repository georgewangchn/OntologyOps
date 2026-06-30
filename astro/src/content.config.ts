import { glob } from 'astro/loaders';
import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';

const blogCollection = defineCollection({
	loader: glob({
		base: './src/content/blog',
		pattern: '**/*.{md,mdx}',
		generateId: ({ entry }) =>
			entry.replace(/\\/g, '/').replace(/\/index\.(md|mdx)$/i, '').replace(/\.(md|mdx)$/i, ''),
	}),
	schema: z.object({
		title: z.string(),
		description: z.string().optional(),
		publishDate: z.coerce.date(),
		read: z.number().optional(),
		tags: z.array(z.string()).optional(),
		category: z.string().default('技术'),
		img: z.string().optional(),
		img_alt: z.string().optional(),
	}),
});

export const collections = {
	blog: blogCollection,
};
