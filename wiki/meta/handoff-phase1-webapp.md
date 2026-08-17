---
title: Handoff — Phase 1 웹앱부터
type: note
visibility: public
domains: [dev]
tags: [handoff, roadmap, astro, cloudflare-workers, webapp]
status: living
created: 2026-08-17
updated: 2026-08-17
related: ["[[adr-0001-structure]]"]
---

# Handoff — Phase 1 웹앱부터

> Phase 0(구조·스키마·수집 파이프라인)은 끝났다. 이 문서는 **웹앱을 처음 만드는 사람/에이전트가 읽고 바로 시작할 수 있게** 현재 상태와 결정, 함정을 정리한 것이다.
> 구조 결정의 근거는 [[adr-0001-structure]] 에 있다. 여기서는 그 결정을 **웹앱 관점에서 무엇을 뜻하는지**로 옮겨 적는다.

---

## 1. 지금 있는 것

| 영역 | 상태 |
|---|---|
| 3계층 구조 (`raw/` `notes/` `wiki/`) | 완료 |
| 운영 스키마 `CLAUDE.md` | 완료 |
| 슬래시 커맨드 `/ingest` `/query` `/lint` `/publish` | 완료 |
| 수집 파이프라인 `tools/article_archive` | 완료. Discord(Hermes)와 Claude Code가 공용 |
| 웹앱 | **없음. 여기서 시작한다** |

저장소는 지금 public 템플릿 겸 공개 위키다. private 분리는 사용에 익숙해진 뒤로 미뤄져 있다([[adr-0001-structure]] §6).

### 문서가 실제로 어떻게 생겼는지

빌드 대상을 정하기 전에 `wiki/digests/2026-08-17-llm-wiki.md` 를 열어보면 실물 frontmatter를 볼 수 있다. 스키마 정의는 `CLAUDE.md` §2 이고, 파서를 새로 쓸 필요는 없다 — Astro content collections의 zod 스키마가 그 역할을 겸한다(§3 참조).

주의할 점 하나: `summary:` 같은 **중첩 블록이 있다**. 도구가 어떤 모델로 요약했는지 기록하는 자리다. zod 스키마에 빠뜨리면 빌드가 깨진다.

---

## 2. Phase 1 범위

**목표**: `*.workers.dev` 에서 public 문서를 읽고 그래프를 탐색할 수 있다. 인증은 Phase 2다.

- [ ] `apps/web` — Astro + `@astrojs/cloudflare`, Workers 배포
- [ ] content collections + zod 스키마 (= frontmatter 검증기 겸용)
- [ ] `[[wikilink]]` → `/wiki/<slug>` remark 플러그인
- [ ] public 문서 목록·상세 렌더, `domains` 기반 내비게이션
- [ ] Pagefind 정적 검색
- [ ] 그래프 뷰 — v1은 graphify HTML 산출물 임베드로 충분
- [ ] 누출 가드 CI (§5)

**Phase 1에서 하지 않는 것**: 인증, private 문서 노출, 웹 편집, 임베딩. 전부 Phase 2~3.

---

## 3. 스택 — 확인된 사실만

Astro 공식 문서에서 확인한 내용이다(2026-08 기준). 추측이 아니라 그대로 쓰면 된다.

```bash
npx astro add cloudflare
```

```js
// astro.config.mjs
import { defineConfig } from 'astro/config';
import cloudflare from '@astrojs/cloudflare';
export default defineConfig({ adapter: cloudflare() });
```

```jsonc
// wrangler.jsonc
{
  "main": "dist/_worker.js/index.js",
  "name": "wiki",
  "compatibility_date": "YYYY-MM-DD",
  "compatibility_flags": ["nodejs_compat", "global_fetch_strictly_public"],
  "assets": { "binding": "ASSETS", "directory": "./dist" },
  "observability": { "enabled": true }
}
```

배포는 `npx astro build && npx wrangler deploy`.

### content collections

`base` 를 `apps/web` 바깥으로 잡아 repo 루트의 마크다운을 직접 읽는다. 콘텐츠를 복사하거나 심볼릭 링크할 필요 없다.

```ts
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const wiki = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../../wiki', deferRender: true }),
  schema: z.object({ /* CLAUDE.md §2 그대로 */ }),
});
```

`deferRender: true` 는 마크다운 컬렉션이 커졌을 때 빌드 중 메모리 고갈을 막는 옵션이다. 지금은 문서가 몇 개뿐이라 체감되지 않지만, 나중에 붙이려면 로더 설정을 다시 만지게 되니 처음부터 켜두는 편이 낫다.

**`raw/` 는 컬렉션에 넣지 않는다.** 외부 기사 전문이라 웹에 나가지 않는다([[adr-0001-structure]] §5). 지금은 gitignore까지 되어 있어서 CI 체크아웃에는 존재하지도 않는다 — 로컬에서 되던 빌드가 CI에서 "파일 없음"으로 깨진다면 대개 이것이다.

---

## 4. 반드시 알아야 할 함정

### Workers Static Assets는 Worker보다 먼저 응답한다

`dist/` 에 prerender된 파일은 **URL만 알면 인증 없이 받아진다.** Phase 2에서 인증을 붙일 때 라우트 핸들러에 검사를 넣는 것만으로는 막히지 않는다.

→ **private 문서는 prerender하지 않는 것이 1차 방어선**이다(`prerender = false`, 콘텐츠가 Worker 번들 안에만 존재). wrangler assets의 `run_worker_first` 로 특정 경로를 Worker에 먼저 태울 수도 있으니 구현 시 현행 스펙을 확인해 이중으로 막는다.

Phase 1은 public만 다루므로 당장 문제는 아니지만, **디렉토리 구조와 라우트를 이때 정해두지 않으면 Phase 2에서 갈아엎게 된다.** 처음부터 `/wiki/[slug]` 를 public 전용으로 두고 private은 별도 라우트 prefix로 분리해두는 편이 낫다.

### `[[wikilink]]` 는 Astro가 처리하지 못한다

문서들이 서로 `[[slug]]` 로 연결되어 있는데 마크다운 표준이 아니다. remark 플러그인으로 `/wiki/<slug>` 로 변환해야 한다. 이게 없으면 문서 간 이동이 전부 죽는다 — Phase 1의 필수 항목이지 나중 일이 아니다.

슬러그 규칙은 파일명과 같다(ASCII kebab-case, `CLAUDE.md` §3-1). 한글 제목이어도 파일명은 ASCII라 URL 인코딩 문제가 없다.

### `visibility` 누락은 public이 아니라 private

스키마 기본값을 반드시 `private` 으로 둔다. zod에서 `.default('private')`. 실수로 `.optional()` 만 걸어두면 누락된 문서가 public으로 새어나간다.

---

## 5. 누출 벡터 — CI 가드에 넣을 것

문서 페이지만 막으면 된다고 착각하기 쉬운데 실제 누출은 부산물에서 난다.

| 벡터 | 왜 새는가 |
|---|---|
| Pagefind 인덱스 | 정적 파일이라 그냥 다운로드된다. **public 출력만 인덱싱**하면 구조적으로 해결됨 |
| `graph.json` | 노드 라벨에 private 문서 제목이 들어간다. public용 필터링 버전을 따로 생성 |
| RSS · sitemap | 필터 누락 단골 |
| OG 이미지 | 제목을 그대로 렌더한다 |
| `/api/*` 목록 응답 | Phase 2에서 추가될 때 |

**CI 가드**: 빌드 산출물 전체를 grep해서 private 문서의 슬러그·제목이 public 번들에 없음을 검증하는 테스트를 배포 파이프라인에 넣는다. Phase 1에 만들어두면 Phase 2에서 인증을 붙일 때 안전망이 이미 있다.

---

## 6. Phase 2~3 예고 (지금 설계에 영향 주는 것만)

- **Phase 2 인증**: Worker 내 GitHub OAuth, allowlist 단일 사용자, **HMAC 서명 쿠키**(사용자 1명이라 KV 불필요). private 문서는 SSR.
- **Phase 2 private 검색**: Pagefind는 정적 인덱스를 그대로 fetch하는 구조라 인증 뒤에 두기 어렵다. title·tags·domains만 담은 경량 JSON을 인증 라우트로 내려 클라이언트 필터링하는 것으로 시작한다.
- **Phase 3 웹 편집**: GitHub Contents API 커밋 → CI 재빌드. 반영에 1~2분 걸린다. 거슬리면 콘텐츠를 Workers KV에 싱크하는 구조로 전환.
- **Phase 3 임베딩**: ingest 시점에 로컬에서만 돌고 결과(`related:` 링크)만 정적으로 반영. 웹앱에 런타임 추론 없음. 한글+영문 혼용이라 **다국어 모델 필수**(`bge-m3`·`multilingual-e5`). `all-MiniLM` 계열은 영어 전용이라 무의미해진다.

비용 목표는 $0이다. 정적 asset은 무과금이고 Worker 호출은 private SSR에서만 발생한다. 외부 API·벡터 DB를 쓰지 않는 이유가 이것이다.

---

## 7. private repo로 분리할 때

지금은 단일 public 저장소다. 개인 자료를 넣기 시작하면 분리한다.

**fork는 안 된다** — public repo의 fork는 항상 public이고 private으로 바꿀 수 없다. `clone` 후 새 private repo로 push하면 히스토리가 이어져 `git merge template/main` 이 깔끔하게 동작한다.

```bash
git remote rename origin template
git remote set-url --push template no_push   # 콘텐츠가 위로 새는 사고 방지
gh repo create wiki --private --source=. --push --remote=origin
```

분리 후 바꿀 것:
- `.gitignore` 의 `raw/` 블록 제거 (private에서는 원문도 버전 관리)
- `tools/article_archive/config.json` 에 `uri_mode: "github"` + `github_repo` → Discord 카드가 경로 대신 GitHub 링크를 단다
- Hermes `plugins/article_archive/settings.json` 의 `wiki_tool` 을 private repo 경로로

**방향 규칙**: 앱·스키마 수정은 public 템플릿에서 하고 private으로 merge해 내린다. 반대 방향 push는 위 리모트 설정으로 막혀 있다.

---

## 8. 열려 있는 것

- 커스텀 도메인 없음 — `*.workers.dev` 로 진행하기로 되어 있다. 나중에 붙이면 OAuth 콜백 URL을 함께 바꿔야 한다.
- `domains` 닫힌 어휘(`ai` `dev` `career` `product` `infra` `misc`)가 내비게이션 구조를 정한다. 늘리려면 `CLAUDE.md` §2와 `tools/article_archive/passes.py` 의 `DOMAINS` 를 **함께** 고쳐야 한다.
- 그래프 뷰 v2(sigma.js 네이티브)로 갈 때 `graph.json` 을 public 노드만 남기고 필터링하는 단계가 필요하다.
