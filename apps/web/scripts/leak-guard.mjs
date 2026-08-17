#!/usr/bin/env node
/**
 * 누출 가드 — 빌드 산출물에 비공개 문서의 흔적이 없는지 검사한다.
 *
 * 문서 페이지만 막으면 된다고 착각하기 쉬운데, 실제 누출은 부산물에서 난다.
 * Pagefind 인덱스·graph.json·sitemap·OG 는 전부 정적 파일이라 URL만 알면 받아진다.
 * 그래서 라우트를 하나씩 검사하지 않고 **dist 전체를 문자열로 훑는다** — 새 산출물이
 * 생겨도 자동으로 검사 범위에 들어온다.
 *
 * Phase 1은 public만 렌더하므로 지금은 통과하는 게 정상이다. 이 스크립트의 값어치는
 * Phase 2에서 인증을 붙일 때 안전망이 이미 자리에 있다는 것이다.
 */
import fs from 'node:fs';
import path from 'node:path';

import { DIST_DIR, NOTES_DIR, WIKI_DIR } from '../src/lib/paths.mjs';
import { assertUniqueSlugs, scanDocs } from '../src/lib/scan-docs.mjs';

/** 산출물에 그대로 나와도 누출이 아닌 것들. */
const IGNORED_FILES = new Set(['wrangler.json', '.assetsignore']);

/** 너무 짧거나 흔한 제목은 우연히 일치한다 — 슬러그로만 검사한다. */
const MIN_TITLE_LENGTH = 6;

function collectFiles(dir) {
  const found = [];
  const stack = [dir];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (IGNORED_FILES.has(entry.name)) continue;
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (entry.isFile()) found.push(full);
    }
  }
  return found;
}

function main() {
  const clientDir = path.join(DIST_DIR, 'client');
  if (!fs.existsSync(clientDir)) {
    console.error(`누출 가드: 빌드 산출물이 없다 (${clientDir}). 먼저 astro build 를 돌려라.`);
    process.exit(1);
  }

  // notes/ 는 사이트에 렌더하지 않지만, 제목이 새는지는 검사 대상이다.
  const wikiDocs = assertUniqueSlugs(scanDocs(WIKI_DIR, { exclude: ['index.md'] }));
  const noteDocs = scanDocs(NOTES_DIR);
  const allDocs = [...wikiDocs, ...noteDocs];

  const publicSlugs = new Set(
    wikiDocs.filter((doc) => doc.visibility === 'public').map((doc) => doc.slug),
  );

  /** 검사 대상: private 문서의 슬러그와 제목. 같은 슬러그가 public에도 있으면 제외. */
  const needles = [];
  for (const doc of allDocs) {
    if (doc.visibility === 'public') continue;
    if (!publicSlugs.has(doc.slug)) {
      needles.push({ kind: '슬러그', value: doc.slug, doc });
    }
    if (doc.title.length >= MIN_TITLE_LENGTH && doc.title !== doc.slug) {
      needles.push({ kind: '제목', value: doc.title, doc });
    }
  }

  const files = collectFiles(clientDir);
  const hits = [];

  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    for (const needle of needles) {
      if (content.includes(needle.value)) {
        hits.push({ file: path.relative(clientDir, file), ...needle });
      }
    }
  }

  const summary = `비공개 문서 ${allDocs.length - publicSlugs.size}건 · 검사 문자열 ${needles.length}개 · 산출물 파일 ${files.length}개`;

  if (hits.length > 0) {
    console.error(`\n✗ 누출 가드 실패 — ${summary}\n`);
    for (const hit of hits) {
      console.error(`  ${hit.file}\n    ${hit.kind} "${hit.value}"  ← ${hit.doc.file}`);
    }
    console.error(
      '\n비공개 문서의 슬러그나 제목이 공개 번들에 들어갔다.',
      '\npublic 문서가 비공개 문서를 이름으로 언급하고 있거나, 렌더 필터가 빠졌다.\n',
    );
    process.exit(1);
  }

  console.log(`✓ 누출 가드 통과 — ${summary}`);
}

main();
