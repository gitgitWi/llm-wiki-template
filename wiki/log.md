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
