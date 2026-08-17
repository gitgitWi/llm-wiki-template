---
title: Phase 1 구현 결과 — feat/phase1-webapp 브랜치 검토
type: note
visibility: public
domains: [dev]
tags: [implementation, review, phase1, webapp, astro]
status: draft
created: 2026-08-17
updated: 2026-08-17
related: ["[[260817-handoff-phase1-webapp]]", "[[adr-0001-structure]]"]
---

# Phase 1 구현 결과 — feat/phase1-webapp 브랜치 검토

> 작업 위치: worktree `~/Codes/llm-wiki-phase1-webapp`, branch `feat/phase1-webapp`
> 계획 기준: `plan_llm-wiki-setup.md` Phase 1 항목, `260817-handoff-phase1-webapp.md`

---

## 총평

**Phase 1의 모든 P0·P1 항목이 구현되어 있음.** 빌드도 통과해 `dist/client/`에 정적 산출물이 생성됐고, GraphCanvas는 d3-force로 캔버스에 그리는 네이티브 그래프 뷰다(graphify HTML 임베드가 아닌). CI 가드·Pagefind·누출 체크리스트 모두 갖춰져 있다.

---

## 구현 확인 항목별 매핑

### P0 — 핵심 구조

| 항목 | 상태 | 구현 위치 | 비고 |
|---|---|---|---|
| `apps/web` Astro + Cloudflare | ✅ | `apps/web/` | `astro.config.mjs`, `wrangler.jsonc` |
| content collections + zod 스키마 | ✅ | `src/content.config.ts` | `base: ../../wiki`, raw 제외, `deferRender: true` |
| `visibility` default `'private'` | ✅ | `content.config.ts:18-21` | `.preprocess()` 로 오타·누락 모두 private 처리 |
| `[[wikilink]]` remark 플러그인 | ✅ | `src/lib/wikilink-plugin.mjs` | Sätteri 기반, 미해결 링크는 텍스트로 남김 |
| H1 중복 제거 | ✅ | `src/lib/title-heading-plugin.mjs` | 본문 첫 H1 제거 |
| public 문서 목록 렌더 | ✅ | `src/pages/wiki/index.astro` | domains 필터링 포함 |
| public 문서 상세 렌더 | ✅ | `src/pages/wiki/[slug].astro` | 연결된 문서(ego 그래프 + neighbours 목록) 함께 표시 |
| domains 내비게이션 | ✅ | `src/pages/domains/[domain].astro` | 카드 UI, `/domains/ai` 등 |
| tags 내비게이션 | ✅ | `src/pages/tags/[tag].astro` | |

### P1 — 검색·그래프·CI

| 항목 | 상태 | 구현 위치 | 비고 |
|---|---|---|---|
| Pagefind 정적 검색 | ✅ | `src/pages/search.astro` | script 태그로 로드 (import() 아님), 한국어 번역 포함 |
| 전역 그래프 뷰 | ✅ | `src/pages/graph.astro` | sigma.js 대신 d3-force 캔버스 직접 그리기 |
| 문서별 ego 그래프 | ✅ | `src/components/GraphCanvas.astro` | 노드 드래그·클릭 이동, 태그 엣지 on/off 토글 |
| graph.json | ✅ | `src/pages/graph.json.ts` | public 노드만 포함 (누출 방지) |
| 누출 가드 CI | ✅ | `scripts/leak-guard.mjs`, `.github/workflows/web.yml` | dist 전체 grep, private 슬러그+제목 검사 |
| 404 커스텀 페이지 | ✅ | `src/pages/404.astro` | `wrangler.jsonc`에서 `not_found_handling: "404-page"` |
| sitemap.xml | ✅ | `src/pages/sitemap.xml.ts` | |

### handoff 문서의 함정 대응 확인

| 함정 | 대응 |
|---|---|
| Workers Static Assets가 Worker보다 먼저 응답 | `output: 'static'`, private 문서는 Phase 2에서 별도 prefix · prerender=false 예정 |
| `[[wikilink]]` 기본 미처리 | Sätteri 플러그인으로 처리, 대상은 public 문서만 |
| `visibility` 누락 → public 노출 | zod `.preprocess()` 로 모든 경우 private으로 폴백 |
| 원본 푸시로 main 자동 변경 | 배포 워크플로우에 `concurrency` 그룹 + `paths` 필터 (향후) |
| graph.json에 private 제목 누출 | `buildGraph()` 가 public 문서만 노드로 삼음 |

---

## 추가 구현 (계획에 없는 것)

| 항목 | 내용 |
|---|---|
| 제목 헤딩 자동 제거 플러그인 | `title-heading-plugin.mjs` — 문서 내 첫 H1을 제거해 `<h1 class="page-title">` 와 중복 방지 |
| 라벨 없는 위키링크 제목 표시 | `wikilink-plugin.mjs` 의 `linkTargets()` 가 대상 문서 제목을 자동으로 넣음 |
| 그래프 노드 크기 시각화 | `degree` 에 따라 노드 반경 조정, focus 노드는 링 표시 |
| 태그 엣지 개수 제한 | `TAG_EDGE_MAX_DOCS = 8` — 너무 많은 태그가 그래프를 덩어리로 뭉개는 것 방지 |
| 라벨 충돌 방지 | 충돌 반경에 라벨 너비 반영 (`labelHalf`) |
| 캔버스 리사이즈 대응 | `ResizeObserver` 로 동적 리사이즈 |
| 노드 드래그 앤 드롭 | pointer events 기반, 고정 위치(`fx/fy`)로 시뮬레이션에 반영 |

---

## 누락·남은 것 (Phase 2~3로 이관)

| 항목 | 상태 | Phase |
|---|---|---|
| 인증 (GitHub OAuth + HMAC 서명 쿠키) | 미구현 | Phase 2 |
| private 문서 SSR 라우트 | 미구현 | Phase 2 |
| private 검색 경량 JSON 인덱스 | 미구현 | Phase 2 |
| 네이티브 그래프 뷰 v2 (sigma.js) | ❌ — 오히려 d3-force로 대체 | Phase 2~3 (재검토 필요) |
| 웹 편집 (GitHub Contents API 커밋) | 미구현 | Phase 3 |
| 모바일 퀵캡처 | 미구현 | Phase 3 |
| 로컬 임베딩 (`bge-m3`) | 미구현 | Phase 3 |
| fixtures/ 샘플 문서 | 미생성 | Phase 1~2 사이 |

---

## 빌드 산출물 확인 (dist/client)

```
/wiki/                6개 문서 렌더 완료
  2026-08-17-llm-wiki/
  adr-0001-structure/
  handoff-phase1-webapp/
  llm-wiki-methodology/
  log/
  on-device-stt-macos/
/domains/{ai,career,dev,infra,misc,product}/  6개
/tags/{30개}  → 태그별 페이지 자동 생성
/graph             전역 그래프
/search            Pagefind 검색
/sitemap.xml       사이트맵
/_pagefind/        Pagefind 번들 (한국어 인덱스 포함)
/graph.json        public 노드만
```

---

## 권장 다음 단계

1. **`.dev/llm-wiki-setup/260817-implementation-status.md` 갱신** — Phase 1 완료 상태로 marking
2. **branch merge 결정** — `feat/phase1-webapp` → `main` merge 방식 선택 (squash / rebase / merge commit)
3. **`fixtures/` 생성** — public 빌드 검증용 타입·visibility 조합 샘플 문서 3~5개
4. **`@astrojs/markdown-satteri` 의존성 확인** — 공식 astrojs 패키지가 아닌지 검토 (현재 `satteri` 로 import됨)
