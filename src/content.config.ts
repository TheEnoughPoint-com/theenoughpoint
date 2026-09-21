import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    cover: z.string(),
    date: z.string(),
    category: z.string(),
    tags: z.array(z.string()).optional().default([]),
    readTime: z.number(),
    featured: z.boolean().optional().default(false),
    trending: z.boolean().optional().default(false),
    popular: z.boolean().optional().default(false),
    authorId: z.string(),
    excerpt: z.string(),
    sponsored: z.boolean().optional().default(false),
    sponsorName: z.string().optional(),
    showDisclosure: z.boolean().optional().default(false),
    // Articles that end in a long endnotes block place the share row themselves,
    // just above those notes. Without this the template appends it after the
    // legal disclaimer, which is the worst spot on the page to ask for a share.
    inlineShare: z.boolean().optional().default(false),
    /** Three or four lines of argument shown before the article starts. */
    takeaways: z.array(z.string()).optional().default([]),
    /** Rendered under the takeaways, e.g. "30 June 2026". */
    figuresAsOf: z.string().optional(),
    /** Set when a published piece is materially revised; feeds dateModified. */
    updated: z.string().optional(),
    lifeStage: z.array(z.string()).optional().default([]),
    /** A single featured TikTok video in the sidebar, between Our Tools and
     *  the newsletter box. Structured rather than raw embed HTML so a future
     *  article can feature a different video by filling in data. */
    tiktokEmbed: z.object({
      videoId:      z.string(),
      cite:         z.string(),
      authorHandle: z.string(),
      caption:      z.string(),
      hashtag:      z.string().optional(),
      mention:      z.string().optional(),
      musicLabel:   z.string(),
      musicHref:    z.string(),
    }).optional(),
  }),
});

const pages = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/pages' }),
  schema: z.object({
    title: z.string(),
    label: z.string(),
    icon: z.string(),
    date: z.string(),
    description: z.string().optional(),
  }),
});

export const collections = { blog, pages };
