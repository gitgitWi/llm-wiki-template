import { defineMdastPlugin } from 'satteri';

import { WIKI_DIR } from './paths.mjs';
import { scanDocs } from './scan-docs.mjs';
import { splitWikilinks } from './wikilink.mjs';

let cachedTargets = null;

/**
 * 링크 대상 = **public 문서만**. 슬러그 → `{ href, title }`.
 *
 * private 문서로 링크를 걸지 않는 이유는 404 회피가 아니라 누출 방지다.
 * `href="/wiki/<private-slug>"` 가 public HTML에 박히면 슬러그가 그대로 새어나간다.
 * 미해결 링크는 링크가 아닌 텍스트로 남고, 남은 텍스트는 누출 가드가 잡는다.
 */
function linkTargets() {
  if (cachedTargets === null) {
    cachedTargets = new Map(
      scanDocs(WIKI_DIR)
        .filter((doc) => doc.visibility === 'public')
        .map((doc) => [doc.slug, { href: `/wiki/${doc.slug}`, title: doc.title }]),
    );
  }
  return cachedTargets;
}

/**
 * `[[wikilink]]` → `/wiki/<slug>` 링크로 바꾸는 Sätteri mdast 플러그인.
 *
 * 마크다운 표준이 아니라서 그냥 두면 문서 간 이동이 전부 죽는다.
 * `code`·`inlineCode` 는 별도 노드 타입이라 text 방문자가 닿지 않는다 — 문서에 쓴
 * 예시 문법이 실제 링크로 바뀌는 사고가 자동으로 막힌다.
 *
 * @param {{ resolve?: (slug: string) => string | null }} [options]
 */
export function wikilinkPlugin(options = {}) {
  const resolve = options.resolve ?? ((slug) => linkTargets().get(slug) ?? null);

  return defineMdastPlugin({
    name: 'wikilink',
    text(node, ctx) {
      const parent = ctx.parent(node);
      if (parent?.type === 'link' || parent?.type === 'linkReference') return;

      const nodes = splitWikilinks(node.value, resolve);
      if (!nodes) return;

      ctx.insertBefore(node, nodes);
      ctx.removeNode(node);
    },
  });
}
