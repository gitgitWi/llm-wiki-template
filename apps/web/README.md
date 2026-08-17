# apps/web — 공개 위키 웹앱

`wiki/` 의 **public 문서만** 읽어 정적 사이트로 만들고 Cloudflare Workers 에 올린다.
설계 근거는 [`wiki/meta/handoff-phase1-webapp.md`](../../wiki/meta/handoff-phase1-webapp.md),
스키마 정의는 저장소 루트 [`CLAUDE.md`](../../CLAUDE.md) §2 에 있다.

```bash
npm install
npm run dev        # 로컬 개발 서버
npm run build      # astro build → pagefind 색인 → 누출 가드
npm run preview    # 빌드 후 wrangler dev 로 Workers 환경 재현
npm run deploy     # 빌드 후 wrangler deploy
npm run check      # astro check (타입 + frontmatter 스키마)
```

## 콘텐츠를 어디서 읽는가

앱 바깥의 저장소 루트 `wiki/` 를 content collection 의 `base` 로 직접 잡는다.
복사도 심볼릭 링크도 없다. `raw/` 는 컬렉션에 넣지 않는다 — 외부 기사 전문이고,
공개 템플릿에서는 gitignore 되어 CI 체크아웃에 존재하지도 않는다.

`wiki/index.md` 는 컬렉션에서 뺀다. 앱이 만드는 `/wiki/` 목록과 역할이 겹치고
파일 경로도 충돌한다.

## 슬러그

**파일명이 곧 URL이다.** `wiki/digests/foo.md` → `/wiki/foo`. 폴더는 URL에 들어가지
않는데, `[[wikilink]]` 가 폴더를 모르기 때문이다. 그래서 폴더가 달라도 파일명이
겹치면 빌드가 선다 (`assertUniqueSlugs`).

## 공개/비공개

렌더링 경로는 전부 `getPublicDocs()` 하나를 통과한다. 라우트마다 필터를 반복하면
언젠가 한 군데를 빠뜨린다. `visibility` 가 정확히 `public` 이 아니면 — 누락이든
오타든 — private 이다.

`npm run guard` 는 빌드 산출물 전체를 문자열로 훑어 비공개 문서의 슬러그·제목이
없음을 검사한다. 라우트별이 아니라 `dist/client` 전체를 보므로 Pagefind 인덱스,
`graph.json`, `sitemap.xml` 같은 부산물이 자동으로 검사 범위에 들어온다.

## 파일 배치

| 경로 | 역할 |
|---|---|
| `src/content.config.ts` | zod 스키마 = frontmatter 검증기 |
| `src/lib/slug.mjs` | 슬러그 규칙. **의존성 없음** (prerender가 workerd에서 돈다) |
| `src/lib/wikilink.mjs` | `[[링크]]` 파싱 규칙. **의존성 없음** |
| `src/lib/wikilink-plugin.mjs` | 위 규칙을 Sätteri mdast 플러그인으로. 빌드 전용 |
| `src/lib/paths.mjs` | 파일시스템 경로. 빌드 전용, 페이지에서 import 금지 |
| `src/lib/scan-docs.mjs` | frontmatter 얕은 스캔. 플러그인과 누출 가드가 공용 |
| `src/lib/wiki.ts` | 페이지가 쓰는 질의 — `getPublicDocs()`, 그래프, 백링크 |
| `scripts/leak-guard.mjs` | 산출물 누출 검사 |

`paths.mjs` 와 `wikilink-plugin.mjs` 는 각각 `node:fs` 와 네이티브 모듈을 끌고 온다.
페이지에서 import하면 prerender(workerd) 또는 번들링에서 깨진다.

## Phase 2 를 위해 지금 지켜둔 것

Workers Static Assets 는 Worker 보다 **먼저** 응답한다. `dist/` 에 prerender된 파일은
URL만 알면 인증 없이 받아진다. 그래서 인증을 붙일 때 `/wiki/[slug]` 에 private 문서를
끼워 넣으면 안 된다 — `prerender = false` 인 별도 prefix 로 분리해야 한다.
이 라우트는 지금부터 public 전용이다.
