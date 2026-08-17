---
title: 구현 현황 — plan 대비 진행률
type: note
visibility: public
domains: [dev]
tags: [roadmap, phase, task-tracking, astro, cloudflare]
status: draft
created: 2026-08-17
updated: 2026-08-17
source:
  url: https://github.com/gitgitWi/llm-wiki-template
---

# 구현 현황 — plan 대비 진행률

> 원본 플래닝: [`plan_llm-wiki-setup.md`](https://github.com/gitgitWi/agents-home/blob/main/plan_llm-wiki-setup.md)
> 결정 기록: [[adr-0001-structure]] · [[260817-handoff-phase1-webapp]]

---

## 현황 요약

| Phase | 명칭 | 상태 | 완료율 |
|---|---|---|---|
| 0 | 베이스 (구조·스키마·수집 파이프라인) | ✅ 완료 | 100% |
| 1 | 공개 열람 | ✅ 구현 완료 (feat/phase1-webapp) | 100% |
| 2 | 인증·비공개 | ⬜ 대기 | 0% |
| 3 | 쓰기·심화 | ⬜ 대기 | 0% |

---

## Phase 0 — 완료 확인

| 항목 | 상태 | 비고 |
|---|---|---|
| 3계층 구조 (`raw/` `notes/` `wiki/`) | ✅ | 폴더 스켈레톤 + `.gitkeep` |
| `CLAUDE.md` 운영 스키마 | ✅ | domains/tags 이원화, 쓰기 게이트, 하드 룰 |
| `.claude/commands/` (ingest·query·lint·publish) | ✅ | 4개 커맨드 모두 구현 |
| `tools/article_archive` 수집 파이프라인 | ✅ | scrap·summarize·translate·browser CLI |
| digest 페이지 4건 생성 | ✅ | llm-wiki, stripe-job, pelicans, 2024-llms |
| ADR-0001 구조 결정 | ✅ | wiki/meta/adr-0001-structure.md |
| `index.md`·`log.md` | ✅ | 인덱스와 이벤트 로그 모두 작성됨 |
| Obsidian Web Clipper 설정 안내 | ⚠️ | README에 언급되나 실제 설정은 private fork 시점 |

### Phase 0에서 누락된 것

| 항목 | 이유 | 향후 처리 |
|---|---|---|
| `fixtures/` 샘플 문서 | plan §2에 "타입·visibility 조합 샘플"로 명시되었으나 미생성 | Phase 1 시작 전 만들기 좋음 (public 빌드 검증용) |
| private repo 분리 | plan §9, §7에서 "사용에 익숙해진 뒤"로 미루기로 한 대로 유지 | — |

---

## Phase 1 — 공개 열람

**목표**: `*.workers.dev`에서 public 문서 열람 + 그래프 탐색.

**현황**: worktree `~/Codes/llm-wiki-phase1-webapp`, branch `feat/phase1-webapp`에 22 commit 전체 구현 완료. 빌드 통과 확인.

### 구현 완료 항목

| # | 항목 | 상태 | 구현 위치 | 비고 |
|---|---|---|---|---|
| 1.1 | `apps/web` Astro + Cloudflare | ✅ | `apps/web/` | `npx astro add cloudflare`, `wrangler.jsonc` 설정 |
| 1.2 | content collections + zod 스키마 | ✅ | `src/content.config.ts` | `base: ../../wiki`, raw 제외, `deferRender: true` |
| 1.3 | `[[wikilink]]` → `/wiki/<slug>` | ✅ | `src/lib/wikilink-plugin.mjs` | Sätteri 플러그인, 미해결 링크는 텍스트로 남김 |
| 1.4 | public 문서 목록 (`/wiki`) | ✅ | `src/pages/wiki/index.astro` | domains 카드 + 최근 갱신 리스트 |
| 1.5 | public 문서 상세 (`/wiki/[slug]`) | ✅ | `src/pages/wiki/[slug].astro` | frontmatter + 연결 문서 ego 그래프 |
| 1.6 | Pagefind 정적 검색 | ✅ | `src/pages/search.astro` | script 태그 로드, 한국어 번역 |
| 1.7 | 그래프 뷰 | ✅ | `src/pages/graph.astro` + `GraphCanvas.astro` | d3-force 캔버스 네이티브 (graphify HTML 아님) |
| 1.8 | 누출 가드 CI | ✅ | `scripts/leak-guard.mjs` + `.github/workflows/web.yml` | dist 전체 grep, private 슬러그+제목 검사 |
| 1.9 | `fixtures/` 샘플 문서 | ⬜ | — | public 빌드 검증용, 아직 미생성 |

### 추가 구현 (계획 외)

- **제목 헤딩 자동 제거**: `title-heading-plugin.mjs` — 본문 첫 H1 제거하여 제목 중복 방지
- **라벨 없는 위키링크 제목 표시**: 대상 문서 제목 자동 주입
- **그래프 노드 크기 시각화**: degree(연결 수)에 따라 반경 조정, focus 노드 링 표시
- **태그 엣지 개수 제한**: `TAG_EDGE_MAX_DOCS=8` — 인기 태그가 그래프 뭉게는 것 방지
- **라벨 충돌 방지**: 충돌 반경에 라벨 너비 반영
- **캔버스 리사이즈**: ResizeObserver 기반 동적 대응
- **노드 드래그 앤 드롭**: pointer events 기반 시뮬레이션 고정 위치
- **404 커스텀 페이지 + graph.json 누출 방지**

| Phase 1에서 **하지 않는 것** (Phase 2~3로 미룸) |

### Phase 1에서 **하지 않는 것** (Phase 2~3로 미룸)

- GitHub OAuth 인증
- private 문서 노출 / SSR 라우트
- 웹 편집 (GitHub Contents API 커밋)
- 로컬 임베딩
- 네이티브 그래프 뷰: sigma.js 대신 **d3-force 캔버스**로 구현 (계획 변경됨)

### 함정 미리보기 (handoff 문서 §4 참조)

1. **Workers Static Assets는 Worker보다 먼저 응답** — private 문서를 prerender하면 URL만 알면 인증 없이 노출됨. 해결: private는 `prerender: false`, SSR.
2. **`[[wikilink]]`는 Astro가 기본 처리 못 함** — remark 플러그인 필수.
3. **`visibility` 누락은 public이 아님** — zod 스키마에서 `.default('private')` 필수.
4. **링크 1개 아카이브할 때마다 main이 푸시됨** — 배포 워크플로우에 `paths` 필터 권장.

---

## Phase 2 — 인증·비공개 (준비 단계)

| 항목 | 상태 | 비고 |
|---|---|---|
| private repo 분리 | ⬜ | clone → 새 private repo push (fork 금지) |
| GitHub OAuth + HMAC 서명 쿠키 | ⬜ | Worker 내 구현, KV 불필요 |
| private 문서 SSR 라우트 | ⬜ | `prerender: false` + 세션 검사 |
| public용 `graph.json` 필터링 | ⬜ | 노드 라벨에서 private 제목 제거 |
| private 검색 경량 JSON 인덱스 | ⬜ | Pagefind 대신 클라이언트 필터링 |
| 누출 가드 CI 완성 | ⬜ | Phase 1에서 기본 마련, private grep 추가 |

---

## Phase 3 — 쓰기·심화 (준비 단계)

| 항목 | 상태 | 비고 |
|---|---|---|
| 웹 편집 (GitHub Contents API) | ⬜ | 커밋 → CI 재빌드, 1~2분 지연 |
| 모바일 퀵캡처 (`notes/inbox`) | ⬜ | 웹앱에서 바로 메모 작성 |
| 로컬 임베딩 (`bge-m3` 등 다국어) | ⬜ | ingest 시점에만 로컬 실행, 결과 정적 반영 |
| `/lint` 주기 실행 | ⬜ | cron 또는 수동 실행 |

---

## 폴더 분리 이력

| 일자 | 작업 | 상세 |
|---|---|---|
| 2026-08-17 | `dev/` 생성 | 앱 개발 관련 문서와 wiki 내용을 분리 |
| 2026-08-17 | `wiki/meta/handoff-phase1-webapp.md` → `dev/` 이동 | 위키 콘텐츠가 아닌 개발 안내서이므로 분리 |
| 2026-08-17 | `dev/` → `.dev/llm-wiki-setup/` 개편 | 숨김 폴더로 전환 + 주제별 하위폴더, 파일명에 `260817-` 날짜 prefix |

이후 생성될 개발 노트, 기술 리서치, 구현 일지 등은 모두 `.dev/<주제>/`에 둔다. 파일명은 `yymmdd-<슬러그>.md` 로 시작해 시간순으로 정렬되게 한다. `wiki/meta/`는 ADR(결정 기록)만 남긴다.
