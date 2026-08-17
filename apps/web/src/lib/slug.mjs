/**
 * 슬러그 규칙 — **의존성 없는 순수 모듈**.
 *
 * content collection 설정이 이걸 쓰고, 그 설정은 페이지 번들에 딸려 들어간다.
 * `node:path` 를 쓰면 prerender가 도는 workerd 환경에서 터지므로 문자열만 다룬다.
 */

/** content collection 의 `base` (apps/web 기준). 콘텐츠는 앱 바깥에 있고 복사하지 않는다. */
export const WIKI_BASE = '../../wiki';

/**
 * 파일 경로 → 슬러그. 파일명이 곧 슬러그다 (CLAUDE.md §3-5, ASCII kebab-case).
 * 폴더는 슬러그에 들어가지 않는다 — `[[wikilink]]` 가 폴더를 모르기 때문이다.
 *
 * @param {string} filePath
 * @returns {string}
 */
export function slugFromPath(filePath) {
  const name = filePath.split(/[\\/]/).pop() ?? filePath;
  const dot = name.lastIndexOf('.');
  return dot > 0 ? name.slice(0, dot) : name;
}
