import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

import { WIKI_BASE, slugFromPath } from './lib/slug.mjs';

/** CLAUDE.md §2 의 닫힌 어휘. 늘리려면 CLAUDE.md 와 tools/article_archive/passes.py 를 함께 고친다. */
export const DOMAINS = ['ai', 'dev', 'career', 'product', 'infra', 'misc'] as const;
export const TYPES = ['source', 'note', 'concept', 'entity', 'synthesis'] as const;
export const STATUSES = ['living', 'draft', 'archived'] as const;

/**
 * 정확히 `public` 일 때만 public. 누락·오타·null 은 전부 private (CLAUDE.md §3-3).
 * `.optional()` 로 두면 frontmatter가 빠진 문서가 조용히 공개된다.
 */
const visibility = z.preprocess(
  (value) => (value === 'public' ? 'public' : 'private'),
  z.enum(['public', 'private']),
);

/**
 * 수집 도구가 붙이는 블록들. 스키마에 없으면 빌드가 깨지므로 명시하되 느슨하게 받는다
 * (`looseObject` = 모르는 키를 그대로 통과). 도구가 필드를 하나 더 붙였다고
 * 위키 빌드가 멈추면 안 된다.
 */
const sourceBlock = z.looseObject({
  url: z.string().optional(),
  author: z.coerce.string().optional(),
  site: z.string().optional(),
  captured: z.coerce.date().optional(),
  word_count: z.number().optional(),
  extractor: z.string().optional(),
});

/** 어떤 모델이 요약했는지 기록하는 자리. 화면에는 출처 표기로만 쓴다. */
const summaryBlock = z.looseObject({
  updated: z.coerce.date().optional(),
  provider: z.string().optional(),
  model: z.string().optional(),
  backend: z.string().optional(),
  thinking: z.string().optional(),
});

const docSchema = z.object({
  title: z.string(),
  type: z.enum(TYPES),
  visibility,
  domains: z.array(z.enum(DOMAINS)).default(['misc']),
  tags: z.array(z.coerce.string()).default([]),
  status: z.enum(STATUSES).default('living'),
  created: z.coerce.date(),
  updated: z.coerce.date(),
  source: sourceBlock.optional(),
  summary: summaryBlock.optional(),
  related: z.array(z.string()).default([]),
});

export type DocData = z.infer<typeof docSchema>;

const wiki = defineCollection({
  loader: glob({
    // index.md 는 앱이 직접 생성하는 목록과 역할이 겹치고, `/wiki/` 라우트와 파일이 충돌한다.
    pattern: ['**/*.md', '!index.md'],
    base: WIKI_BASE,
    // 파일명이 곧 슬러그. 폴더를 붙이면 `[[wikilink]]` 가 대상을 찾지 못한다.
    generateId: ({ entry }) => slugFromPath(entry),
    deferRender: true,
  }),
  schema: docSchema,
});

export const collections = { wiki };
