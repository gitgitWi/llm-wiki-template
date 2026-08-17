import { fileURLToPath } from 'node:url';
import path from 'node:path';

/**
 * 빌드 시점에만 쓰는 파일시스템 경로. **페이지에서 import하지 않는다** —
 * prerender는 workerd에서 돌고 거기엔 `node:fs` 가 없다.
 * 슬러그 규칙처럼 페이지도 알아야 하는 것은 `slug.mjs` 에 있다.
 */

/** apps/web/ */
export const APP_ROOT = fileURLToPath(new URL('../../', import.meta.url));

/** 저장소 루트 — 콘텐츠는 앱 바깥에 있고, 복사하지 않고 그 자리에서 읽는다. */
export const REPO_ROOT = path.resolve(APP_ROOT, '../..');

export const WIKI_DIR = path.join(REPO_ROOT, 'wiki');
export const NOTES_DIR = path.join(REPO_ROOT, 'notes');
export const DIST_DIR = path.join(APP_ROOT, 'dist');
