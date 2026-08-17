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

## [2026-08-17] adr | ADR-0001 구조 결정
- wiki/meta/adr-0001-structure.md 생성
- 소유권 3계층, domains/tags 이원화, raw 웹 노출 제외, public 템플릿 + private 콘텐츠 2-repo 채택
