import fs from 'node:fs';
import path from 'node:path';
import { parse as parseYaml } from 'yaml';

import { slugFromPath } from './slug.mjs';

/** frontmatter 블록만 떼어낸다. 없으면 null. */
function extractFrontmatter(text) {
  if (!text.startsWith('---')) return null;
  const end = text.indexOf('\n---', 3);
  if (end === -1) return null;
  return text.slice(text.indexOf('\n', 3) + 1, end);
}

function* walk(dir) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return; // 디렉토리가 없으면 (예: gitignore된 raw/) 조용히 건너뛴다
  }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else if (entry.isFile() && entry.name.endsWith('.md')) yield full;
  }
}

/**
 * 디렉토리를 훑어 문서의 슬러그·제목·visibility 만 뽑는다.
 *
 * content collection과 별개로 존재하는 이유가 두 가지 있다:
 * 1. remark 플러그인은 컬렉션이 로드되기 전에 동작하므로 링크 대상 목록을 따로 알아야 한다.
 * 2. 누출 가드는 빌드 산출물만 보고 판단해야 하므로 Astro 런타임에 의존하면 안 된다.
 *
 * @returns {{slug: string, title: string, visibility: 'public'|'private', file: string}[]}
 */
export function scanDocs(dir, { exclude = [] } = {}) {
  const docs = [];
  for (const file of walk(dir)) {
    const rel = path.relative(dir, file);
    if (exclude.includes(rel)) continue;

    const raw = fs.readFileSync(file, 'utf8');
    const block = extractFrontmatter(raw);
    let data = {};
    if (block !== null) {
      try {
        data = parseYaml(block) ?? {};
      } catch {
        data = {}; // 깨진 frontmatter는 visibility 누락과 같게 취급 → private
      }
    }

    docs.push({
      slug: slugFromPath(file),
      title: typeof data.title === 'string' ? data.title : slugFromPath(file),
      // 정확히 'public' 이 아니면 전부 private. 누락·오타는 공개가 아니다 (CLAUDE.md §3-3).
      visibility: data.visibility === 'public' ? 'public' : 'private',
      file: rel,
    });
  }
  return docs.sort((a, b) => a.slug.localeCompare(b.slug));
}

/** 같은 슬러그를 가진 파일이 둘 이상이면 링크가 조용히 엉킨다 — 빌드를 세운다. */
export function assertUniqueSlugs(docs) {
  const seen = new Map();
  const clashes = [];
  for (const doc of docs) {
    const prev = seen.get(doc.slug);
    if (prev) clashes.push(`${doc.slug}: ${prev} ↔ ${doc.file}`);
    else seen.set(doc.slug, doc.file);
  }
  if (clashes.length > 0) {
    throw new Error(
      `슬러그가 중복됐다. 파일명이 곧 URL이라 폴더가 달라도 충돌한다:\n  ${clashes.join('\n  ')}`,
    );
  }
  return docs;
}
