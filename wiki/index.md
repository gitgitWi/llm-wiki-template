---
title: 위키 인덱스
type: note
visibility: public
domains: [misc]
tags: [index]
status: living
created: 2026-08-17
updated: 2026-08-20
description: 위키 전체 카탈로그 — digests/concepts/entities/synthesis/meta 페이지 목록과 한 줄 요약, domains 어휘.
read_when: 위키에 무엇이 있는지 확인할 때. 모든 쿼리는 여기서 시작한다.
agent: claude-opus-5 / claude-code
---

# 위키 인덱스

> 이 위키의 전체 카탈로그. **모든 쿼리는 여기서 시작한다.**
> 페이지를 만들거나 지우면 즉시 반영한다.

- 페이지 13 · 소스 3 · 최종 갱신 2026-08-20
- 공개 페이지는 웹앱(`apps/web`)에서도 볼 수 있다. 목록·검색·그래프는 이 파일이 아니라 frontmatter 에서 생성된다.

---

## Synthesis — 비교·종합

| 페이지 | 요약 | domains |
|---|---|---|
| [[agentic-coding-design-and-code-review]] | Agentic Coding 시대 소프트웨어 설계, AI 생성 코드의 리뷰 피로 해소와 5단계 방어선, 풀스택 관리 방법론 | `ai` `dev` |
| [[llm-wiki-methodology]] | LLM Wiki(Karpathy) 패턴과 Zettelkasten·PARA·NotebookLM·mem0·qmd 비교, 개인 문서 정리 설계안 | `ai` |
| [[on-device-stt-macos]] | M1 Pro에서 한영 혼용 개발자용 완전 로컬 STT 도구 비교 | `ai` `dev` |
| [[yaml-vs-toml]] | YAML·TOML 문법·철학 비교, AI 파싱·토큰 절약 관점과 선택 가이드 | `dev` |
| [[pi-vs-oh-my-pi]] | 원본 Pi(플러그인) vs oh-my-pi(omp) 포크 비교 — 코딩 작업 컨텍스트/토큰 관리·성능·hashline | `ai` `dev` |
| [[pi-vs-oh-my-pi-vs-fx]] | Pi·omp·fx 3자 비교 — edit 포맷·컨텍스트/토큰·확장성·권한·샌드박스·프로바이더 게이트웨이 | `ai` `dev` |
| [[effect-ts-dst-testing]] | Effect.ts TestClock·DST 주장 팩트체크 — 예제 코드 오류, v3/v4 API 차이, 가상 시계 대안 비교 | `dev` `ai` |

## Concepts — 개념·주제

| 페이지 | 요약 | domains |
|---|---|---|
| [[deterministic-simulation-testing]] | DST 의 세 축(시계·스케줄·난수/결함), 계보, 가상 시계와의 차이와 도입 비용 | `dev` |

## Entities — 사람·회사·제품·도구

| 페이지 | 요약 | domains |
|---|---|---|
| [[effect-ts]] | Effect 팩트 시트 — `Effect<A, E, R>` 채널, 3.22.1 stable / 4.0 rc, v3↔v4 테스트 API 대응 | `dev` |

## Digests — 소스 요약

| 페이지 | 요약 | domains |
|---|---|---|
| [[2026-08-17-llm-wiki]] | Karpathy의 LLM Wiki gist — RAG와 달리 지식을 축적하는 3계층 위키 패턴 | `ai` |
| [[2026-08-20-ewind-dev]] | Effect 옹호론 — 부작용 전면 통제의 대가로 얻는 결정적·초고속 테스트 | `dev` |
| [[2026-08-20-rough-sea]] | Ryan Dahl 의 celld 발표, DST 인용의 1차 출처 확인 | `infra` `dev` |

## Meta — 결정 기록

| 페이지 | 요약 |
|---|---|
| [[adr-0001-structure]] | 3계층 구조, 분야 분류를 frontmatter로 두는 결정, 공개/비공개 분리와 웹앱 아키텍처 |

---

## 개발 · 과제

| 문서 | 요약 |
|---|---|
| [구현 현황](../.dev/llm-wiki-setup/260817-implementation-status.md) | plan 대비 진행률, Phase 1~3 미완료 항목, 잡힌 함정 |
| [Phase 1 리뷰](../.dev/llm-wiki-setup/260817-review-phase1-branch.md) | feat/phase1-webapp 브랜치 구현 검토 결과 |
| [Phase 1 인수인계](../.dev/llm-wiki-setup/260817-handoff-phase1-webapp.md) | 웹앱 시작 전 읽을 인수인계 — 상태·스택·함정·누출 벡터 |

---

## 분야(domains) 어휘

`ai` · `dev` · `career` · `product` · `infra` · `misc`

새 값이 필요하면 사용자에게 확인하고 이 목록과 `.rules/frontmatter.md` 를 함께 갱신한다.
