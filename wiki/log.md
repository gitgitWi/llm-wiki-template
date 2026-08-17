---
title: 이벤트 로그
type: note
visibility: public
domains: [misc]
tags: [log]
status: living
created: 2026-08-17
updated: 2026-08-17
---

# 이벤트 로그

> append-only. 기존 항목은 수정하지 않고 아래에 덧붙이기만 한다.
> 형식을 지켜야 `grep "^## \[" log.md | tail -5` 같은 조회가 동작한다.

---

## [2026-08-17] init | 저장소 생성
- 3계층 구조 생성 (raw/ notes/ wiki/)
- CLAUDE.md 스키마 작성
- .claude/commands/ 에 ingest·query·lint·publish 추가

## [2026-08-17] ingest | LLM Wiki 방법론 리서치
- wiki/synthesis/llm-wiki-methodology.md 생성 (기존 리서치 문서 이관)
- 출처: Karpathy LLM Wiki gist

## [2026-08-17] ingest | macOS on-device STT 조사
- wiki/synthesis/on-device-stt-macos.md 생성 (기존 리서치 문서 이관)

## [2026-08-17] tool | HTTP 상태 검사와 GitHub URL 자동 전환
- 추출 전 ranged GET으로 4xx/5xx 거절 (404 페이지가 기사로 저장되던 문제)
- 401/403/429는 봇 차단이라 브라우저 티어로 넘김
- uri_mode: auto — 푸시된 파일은 GitHub blob URL, 아니면 로컬 경로.
  owner/repo는 git remote에서 읽으므로 private fork도 설정 불필요

## [2026-08-17] tool | 저장 후 자동 커밋·푸시
- vcs.py: commit → fetch → rebase → push. 충돌 시 rebase abort 후 커밋만 남김
- pathspec으로 커밋 범위 제한 — 다른 staged 변경을 쓸어담지 않는다
- visibility: private 문서와 gitignore 경로는 커밋 제외 (공개 저장소에선 커밋이 곧 공개)
- 이에 맞춰 digest 기본 visibility를 public으로 변경

## [2026-08-17] tool | 청킹 제거 — AI 패스를 파일 기반 에이전트 실행으로
- llm.py·markdown.py 삭제, agent.py 신설. 프롬프트가 본문 대신 경로를 나른다
- 격리된 스크래치 디렉토리에 원문을 복사해 넣고 에이전트가 거기서만 작업
- scrap이 모델 호출 0회가 됨 (태그는 summarize에 흡수)
- Hermes: auxiliary task 등록 제거 — 도구가 더 이상 Hermes LLM을 쓰지 않음
- 측정: 11,923자 2m15s / 40,162자 14m38s (~22s per 1,000자), 둘 다 완전 번역
- translate_max_chars 120k → 80k: 타임아웃 안에 못 끝낼 원문을 미리 거절

## [2026-08-17] handoff | Phase 1 웹앱 인수인계 문서
- wiki/meta/handoff-phase1-webapp.md 생성
- Phase 0 완료 상태, Astro+Workers 확정 사항, 함정 3건, 누출 벡터 체크리스트

## [2026-08-17] tool | 번역 청크 크기 조정과 잘림 감지
- translate_chunk_chars 3500 → 12000 (5만자 기사 18청크 → 5청크)
- 청크는 서로 독립 세션이라 적을수록 용어가 일관됨
- _looks_truncated: 헤딩 수 비교 + 길이 하한으로 조용한 잘림 차단

## [2026-08-17] tool | article-archive 수집 파이프라인 도입
- tools/article_archive/ 추가 (Hermes 플러그인에서 이관)
- scrap·summarize·translate·browser·xarticle CLI, LLM 백엔드 자동 감지
- raw/ 를 gitignore 처리 — 공개 저장소에 외부 기사 전문을 두지 않는다

## [2026-08-17] ingest | Karpathy LLM Wiki gist
- raw/articles/2026-08-17-llm-wiki.md 저장 (defuddle:http, 1,959 words)
- wiki/digests/2026-08-17-llm-wiki.md 생성 (copilot/gpt-4.1)
- /publish 통과 → public 전환

## [2026-08-17] adr | ADR-0001 구조 결정
- wiki/meta/adr-0001-structure.md 생성
- 소유권 3계층, domains/tags 이원화, raw 웹 노출 제외, public 템플릿 + private 콘텐츠 2-repo 채택

## [2026-08-17] webapp | Phase 1 웹앱 구현
- apps/web/ 신설 — Astro 7 + @astrojs/cloudflare v14, 전부 정적, 바인딩 0개
- content collections 로 repo 루트 wiki/ 를 직접 읽음. zod 스키마가 frontmatter 검증기 겸용
- 라우트: `/`, `/wiki/`, `/wiki/<slug>`, `/domains/<domain>`, `/tags/<tag>`, `/search`, `/graph`, sitemap
- `[[wikilink]]` → `/wiki/<slug>` Sätteri mdast 플러그인. 라벨 없으면 대상 문서 제목으로 렌더
- Pagefind 정적 검색 (한국어 확인), 위키링크 그래프 뷰, public 노드만 담은 graph.json
- 누출 가드 `npm run guard` + GitHub Actions 빌드·배포 워크플로
- 인수인계 문서와 달라진 점 3건은 handoff §9 에 기록
- 부수 발견: 기존 문서 2건의 본문 H1 이 frontmatter title 과 불일치 (빌드 경고로 노출)
