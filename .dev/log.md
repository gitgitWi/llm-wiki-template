---
updated: 2026-08-20
description: Chronological event log for the whole repo — wiki content, tools, and the web app. Newest entry on top.
read_when: You need to know what changed, when, and why before touching an area you did not build.
agent: claude-opus-5 / claude-code
tags: [log, changelog, dev]
---

# 개발 로그

> 이 저장소 전체(위키 콘텐츠 + 도구 + 웹앱)의 이벤트 로그. `wiki/log.md` 에서 이동했다.
> **최신이 맨 위.** 새 항목은 이 표시줄 바로 아래에 삽입한다. 기존 항목은 수정하지 않는다.
> 형식을 지켜야 `grep "^## \[" .dev/log.md | head -5` 같은 조회가 동작한다.

---

## [2026-08-20] publish | Effect.ts DST 팩트체크 5개 문서
- wiki/synthesis/effect-ts-dst-testing.md → public
- wiki/concepts/deterministic-simulation-testing.md → public
- wiki/entities/effect-ts.md → public
- wiki/digests/2026-08-20-ewind-dev.md → public
- wiki/digests/2026-08-20-rough-sea.md → public
- 체크리스트 통과: raw 원문 문장 그대로 옮긴 곳 0건(22개 문장 대조), 링크 대상 전부 public, 회사 정보 없음
- wiki/entities/effect-ts.md 에 Layer 온보딩 절 추가 (Layer<ROut,E,RIn> 모델, merge/provide/provideMerge 차이,
  메모이제이션·Layer.fresh, Layer.mock, v3 Effect.Service ↔ v4 Context.Service, TestClock 과의 연결)

## [2026-08-20] ingest | Effect.ts DST 주장 팩트체크
- raw/articles/2026-08-20-ewind-dev.md 저장 (중국어 X 포스트, private)
- raw/articles/2026-08-20-rough-sea.md 저장 (celld 발표, DST 인용 검증용, private)
- wiki/synthesis/effect-ts-dst-testing.md 생성 — 15개 주장 항목별 판정
- wiki/concepts/deterministic-simulation-testing.md 생성 (첫 concept 페이지)
- wiki/entities/effect-ts.md 생성 (첫 entity 페이지)
- wiki/digests/2026-08-20-ewind-dev.md, 2026-08-20-rough-sea.md 생성
- wiki/synthesis/agentic-coding-design-and-code-review.md related 링크 추가
- wiki/index.md 갱신 (Concepts·Entities 섹션 개설)
- 검증 결과: 예제 코드는 v3/v4 API 혼합 + `Effect.timeout` 실패 채널 오용으로 동작하지 않음.
  `effect` stable 은 3.22.1, 4.0 은 rc. Effect 코어에 시드 스케줄러 없음 (PR #6216 미머지).
- 미해결: index.md 에 공개 digest 2건(stripe, things-we-learned-2024) 누락 — 이번 작업 범위 밖

## [2026-08-20] synthesis | Pi vs oh-my-pi vs fx 3자 코딩 하네스 비교
- wiki/synthesis/pi-vs-oh-my-pi-vs-fx.md 생성 (원본 Pi·omp 포크·fx 3자 비교 — edit 포맷·컨텍스트/토큰·확장성·권한·샌드박스·프로바이더 게이트웨이)
- wiki/index.md Synthesis 테이블에 [[pi-vs-oh-my-pi-vs-fx]] 행 추가 (domains: [ai, dev]), 페이지 수 7→8
- fx 출처: https://fx.sh/llms-full.txt (전체 공식 문서) — Tools·Permissions·Sessions·Subagents·MCP·Authentication·Skills·Configuration
- 기존 [[pi-vs-oh-my-pi]]의 Pi·omp 인용은 계승, fx를 "거버넌스·게이트웨이 추상화" 축으로 추가
- 관련: [[pi-vs-oh-my-pi]]

## [2026-08-20] synthesis | Agentic Coding 시대의 소프트웨어 설계와 AI 코드 리뷰·관리 방법론
- wiki/synthesis/agentic-coding-design-and-code-review.md 생성 (AI 에이전트 도입에 따른 검증 병목, antirez/Liquid AI 루프 설계 철학, 5단계 스위스 치즈 방어 모델, 웹 풀스택 관리 전략)
- wiki/index.md Synthesis 테이블에 [[agentic-coding-design-and-code-review]] 행 추가 (domains: [ai, dev]), 페이지 수 6→7, updated 2026-08-20
- 조사 출처: GeekNews 원문(78bd15a7), Liquid AI agent-loops, Linear 보고서, Claude Code 세션 최적화, Boris Cherny 아키타입, GeekNews 관련 13개 토픽
- 원문 웹 URL 통합 참조 체계 구성 및 frontmatter 계약 준수

## [2026-08-20] translate | Liquid AI agent-loops 기사 전문 한국어 번역
- raw/articles/2026-08-20-designing-loops-for-production-grade-work.md 전문 한국어 번역 작성 → raw/articles/2026-08-20-designing-loops-for-production-grade-work.ko.md
- 원문의 파생 저작물 → visibility: private (공개 빌드 제외), frontmatter는 write_translation 규격 준수(title "…(한국어)", translation 블록, related: [[원본 stem]])

## [2026-08-20] synthesis | Pi vs oh-my-pi 코딩 하네스 비교
- wiki/synthesis/pi-vs-oh-my-pi.md 생성 (원본 Pi 플러그인 방식 vs oh-my-pi omp 포크 비교 — 컨텍스트/토큰 관리·성능·hashline edit)
- wiki/index.md Synthesis 테이블에 [[pi-vs-oh-my-pi]] 행 추가 (domains: [ai, dev]), 페이지 수 5→6, updated 2026-08-20
- 조사 출처: oh-my-pi README·hashline README·lesbass 독립 분석·pi.dev compaction 문서·mariozechner 회고
- 관련: [[yaml-vs-toml]], [[on-device-stt-macos]]

## [2026-08-19] rules | frontmatter 규칙 분리 및 개발 문서로 확대
- .rules/frontmatter.md 신설 (영문) — Tier A 위키/노트 스키마 + Tier B 개발 문서 5필드 블록, 공통 규칙, 면제 대상
- CLAUDE.md §2 는 한 줄 포인터만 남김 (AGENTS.md 는 심볼릭 링크라 함께 반영됨)
- description / read_when / agent 필드 도입 — apps/web/src/content.config.ts 스키마에 optional 로 추가
- .dev/log.md, .dev/llm-wiki-setup/ 3종, apps/web/README.md, tools/article_archive/README.md 에 Tier B frontmatter 적용
- 참조 경로 갱신: passes.py, wiki/index.md, apps/web/README.md, .claude/commands/lint.md
- 로그 헤더 사이에 잘못 삽입돼 있던 [2026-08-18] synthesis 항목을 제자리로 이동

## [2026-08-18] synthesis | YAML vs TOML 포맷 비교
- wiki/synthesis/yaml-vs-toml.md 생성 (YAML·TOML 문법/철학/AI 파싱·토큰 절약 관점, 선택 가이드)
- wiki/index.md Synthesis 테이블에 [[yaml-vs-toml]] 행 추가 (domains: [dev])
- 관련: [[llm-wiki-methodology]]

## [2026-08-18] restructure | 개발 로그를 wiki/ 밖으로 분리
- wiki/log.md → .dev/log.md 이동 (wiki/ 는 콘텐츠만, 개발 로그는 .dev/)
- 최신순 정렬 도입 — 새 항목은 맨 위에 삽입, 기존 항목 불변
- CLAUDE.md §1·§3·§5·§6·§7, .claude/commands/ 4종, wiki 내 참조 문서 경로·형식 갱신

## [2026-08-17] webapp | Phase 1 웹앱 구현
- apps/web/ 신설 — Astro 7 + @astrojs/cloudflare v14, 전부 정적, 바인딩 0개
- content collections 로 repo 루트 wiki/ 를 직접 읽음. zod 스키마가 frontmatter 검증기 겸용
- 라우트: `/`, `/wiki/`, `/wiki/<slug>`, `/domains/<domain>`, `/tags/<tag>`, `/search`, `/graph`, sitemap
- `[[wikilink]]` → `/wiki/<slug>` Sätteri mdast 플러그인. 라벨 없으면 대상 문서 제목으로 렌더
- Pagefind 정적 검색 (한국어 확인), 위키링크 그래프 뷰, public 노드만 담은 graph.json
- 누출 가드 `npm run guard` + GitHub Actions 빌드·배포 워크플로
- 인수인계 문서와 달라진 점 3건은 handoff §9 에 기록
- 부수 발견: 기존 문서 2건의 본문 H1 이 frontmatter title 과 불일치 (빌드 경고로 노출)

## [2026-08-17] adr | ADR-0001 구조 결정
- wiki/meta/adr-0001-structure.md 생성
- 소유권 3계층, domains/tags 이원화, raw 웹 노출 제외, public 템플릿 + private 콘텐츠 2-repo 채택

## [2026-08-17] ingest | Karpathy LLM Wiki gist
- raw/articles/2026-08-17-llm-wiki.md 저장 (defuddle:http, 1,959 words)
- wiki/digests/2026-08-17-llm-wiki.md 생성 (copilot/gpt-4.1)
- /publish 통과 → public 전환

## [2026-08-17] tool | article-archive 수집 파이프라인 도입
- tools/article_archive/ 추가 (Hermes 플러그인에서 이관)
- scrap·summarize·translate·browser·xarticle CLI, LLM 백엔드 자동 감지
- raw/ 를 gitignore 처리 — 공개 저장소에 외부 기사 전문을 두지 않는다

## [2026-08-17] tool | 번역 청크 크기 조정과 잘림 감지
- translate_chunk_chars 3500 → 12000 (5만자 기사 18청크 → 5청크)
- 청크는 서로 독립 세션이라 적을수록 용어가 일관됨
- _looks_truncated: 헤딩 수 비교 + 길이 하한으로 조용한 잘림 차단

## [2026-08-17] handoff | Phase 1 웹앱 인수인계 문서
- wiki/meta/handoff-phase1-webapp.md 생성
- Phase 0 완료 상태, Astro+Workers 확정 사항, 함정 3건, 누출 벡터 체크리스트

## [2026-08-17] tool | 청킹 제거 — AI 패스를 파일 기반 에이전트 실행으로
- llm.py·markdown.py 삭제, agent.py 신설. 프롬프트가 본문 대신 경로를 나른다
- 격리된 스크래치 디렉토리에 원문을 복사해 넣고 에이전트가 거기서만 작업
- scrap이 모델 호출 0회가 됨 (태그는 summarize에 흡수)
- Hermes: auxiliary task 등록 제거 — 도구가 더 이상 Hermes LLM을 쓰지 않음
- 측정: 11,923자 2m15s / 40,162자 14m38s (~22s per 1,000자), 둘 다 완전 번역
- translate_max_chars 120k → 80k: 타임아웃 안에 못 끝낼 원문을 미리 거절

## [2026-08-17] tool | 저장 후 자동 커밋·푸시
- vcs.py: commit → fetch → rebase → push. 충돌 시 rebase abort 후 커밋만 남김
- pathspec으로 커밋 범위 제한 — 다른 staged 변경을 쓸어담지 않는다
- visibility: private 문서와 gitignore 경로는 커밋 제외 (공개 저장소에선 커밋이 곧 공개)
- 이에 맞춰 digest 기본 visibility를 public으로 변경

## [2026-08-17] tool | HTTP 상태 검사와 GitHub URL 자동 전환
- 추출 전 ranged GET으로 4xx/5xx 거절 (404 페이지가 기사로 저장되던 문제)
- 401/403/429는 봇 차단이라 브라우저 티어로 넘김
- uri_mode: auto — 푸시된 파일은 GitHub blob URL, 아니면 로컬 경로.
  owner/repo는 git remote에서 읽으므로 private fork도 설정 불필요

## [2026-08-17] ingest | macOS on-device STT 조사
- wiki/synthesis/on-device-stt-macos.md 생성 (기존 리서치 문서 이관)

## [2026-08-17] ingest | LLM Wiki 방법론 리서치
- wiki/synthesis/llm-wiki-methodology.md 생성 (기존 리서치 문서 이관)
- 출처: Karpathy LLM Wiki gist

## [2026-08-17] init | 저장소 생성
- 3계층 구조 생성 (raw/ notes/ wiki/)
- CLAUDE.md 스키마 작성
- .claude/commands/ 에 ingest·query·lint·publish 추가
