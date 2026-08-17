/**
 * `[[wikilink]]` 문법 처리 — **의존성 없는 순수 모듈**.
 *
 * 마크다운 플러그인(`wikilink-plugin.mjs`)과 그래프 생성이 같은 규칙을 써야 하는데,
 * 플러그인은 네이티브 모듈(satteri)을 끌고 온다. 규칙만 여기 따로 두어야
 * 페이지 번들에 네이티브 모듈이 딸려 들어가지 않는다.
 */

/** `[[slug]]` 또는 `[[slug|보이는 텍스트]]`. */
const WIKILINK = /\[\[([^[\]|]+?)(?:\|([^[\]]+?))?\]\]/g;

/**
 * 텍스트 한 조각을 위키링크 기준으로 쪼개 mdast 노드 배열로 만든다.
 * 링크가 하나도 없으면 `null` — 호출 측이 노드를 건드리지 않도록.
 *
 * @param {string} value
 * @param {(slug: string) => string | null} resolve 슬러그 → URL, 대상이 없으면 null
 */
export function splitWikilinks(value, resolve) {
  if (!value.includes('[[')) return null;

  const nodes = [];
  let cursor = 0;

  for (const match of value.matchAll(WIKILINK)) {
    const [whole, rawTarget, rawLabel] = match;
    const target = rawTarget.trim();
    const label = (rawLabel ?? rawTarget).trim();
    const href = resolve(target);

    if (match.index > cursor) {
      nodes.push({ type: 'text', value: value.slice(cursor, match.index) });
    }

    if (href) {
      nodes.push({
        type: 'link',
        url: href,
        title: null,
        data: { hProperties: { class: 'wikilink' } },
        children: [{ type: 'text', value: label }],
      });
    } else {
      // 해석 못 한 링크는 링크로 만들지 않는다. 깨진 링크보다 텍스트가 정직하다.
      nodes.push({
        rawHtml: `<span class="wikilink wikilink--unresolved" title="아직 없거나 비공개인 문서">${escapeHtml(label)}</span>`,
      });
    }

    cursor = match.index + whole.length;
  }

  if (nodes.length === 0) return null;
  if (cursor < value.length) {
    nodes.push({ type: 'text', value: value.slice(cursor) });
  }
  return nodes;
}

/**
 * 문서 본문에서 나가는 위키링크 슬러그를 뽑는다. 그래프 엣지를 만들 때 쓴다.
 * @param {string} body
 * @returns {string[]}
 */
export function extractWikilinks(body) {
  const found = new Set();
  // 코드 블록·인라인 코드 안의 예시를 엣지로 세지 않는다 — 렌더링 규칙과 맞춘다.
  const prose = body.replace(/```[\s\S]*?```/g, '').replace(/`[^`\n]*`/g, '');
  for (const match of prose.matchAll(WIKILINK)) {
    found.add(match[1].trim());
  }
  return [...found];
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
