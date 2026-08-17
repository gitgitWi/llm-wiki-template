---
title: ADR-0001 — 3계층 구조와 공개/비공개 분리
type: note
visibility: public
domains: [ai, dev]
tags: [adr, architecture, llm-wiki, cloudflare, astro]
status: living
created: 2026-08-17
updated: 2026-08-17
related: ["[[llm-wiki-methodology]]"]
---

# ADR-0001 — 3계층 구조와 공개/비공개 분리

> 상태: 채택 · 2026-08-17
> 근거 문서: [[llm-wiki-methodology]]

## 맥락

기술 블로그, X 스레드, 유튜브 요약, 개발 아이디에이션, 커리어 자료, job posting을 한곳에 모으고, LLM이 그 위에 상호연결된 위키를 자동 유지하게 하려 한다. 여기에 웹앱으로 열람·그래프 탐색·간단 편집까지 붙인다. 운영비는 $0을 목표로 한다.

기존에 PARA(Projects/Areas/Resources/Archives)로 정리를 시도했으나 이 저장소에는 Projects가 사실상 없고, 남는 것은 Resources와 Archives뿐이었다.

## 결정

### 1. 최상위 분류축은 주제가 아니라 소유권

| 계층 | 내용 | LLM 권한 |
|---|---|---|
| `raw/` | 외부 원본 | 읽기 전용 |
| `notes/` | 직접 쓴 글 | 제안만 |
| `wiki/` | LLM 생성·유지 | 자유 쓰기 |

**근거**: canonical/derived 쓰기 게이트를 폴더로 물리화하면 권한이 경로만 보고 자명해진다. 주제별 flat 구조는 이 구분을 표현하지 못한다.

### 2. 분야는 폴더가 아니라 frontmatter

`domains[]`(닫힌 어휘, 내비게이션용) + `tags[]`(열린 어휘, LLM 추출) 이원화.

**근거**: 폴더는 하나만 고를 수 있어 여러 분야에 걸친 자료를 담지 못한다. 배열이면 다중 소속이 기본이 된다. 하위 분류는 폴더 대신 `[[링크]]`가 담당한다.

### 3. Archives 폴더를 만들지 않는다

`status: archived` frontmatter로 대체.

**근거**: 파일을 옮기면 위키링크가 깨진다. 링크 기반 구조에서 폴더로 생명주기를 표현하는 것은 비용이 크다.

### 4. `visibility` 기본값은 private

누락·오타는 public이 아니라 private으로 폴백한다. 공개는 `/publish` 체크리스트를 통과한 명시적 행위여야 한다.

### 5. `raw/`는 웹앱 빌드에서 완전히 제외

**근거**: 외부 기사 전문을 재배포할 근거가 없다. digest가 원본 URL로 링크만 건다. 저작권 문제와 누출 경로를 동시에 없앤다.

### 6. public 템플릿 + private 콘텐츠 2-repo

구조·스키마·앱은 공개하고 콘텐츠는 비공개로 둔다.

**중요**: GitHub에서 public repo를 fork하면 fork도 항상 public이고 private으로 전환할 수 없다. `clone` 후 새 private repo로 push하는 방식을 쓴다 — 히스토리가 공유되어 `git merge template/main`이 깔끔하게 동작한다.

**방향 규칙**: 개발은 public에서, 콘텐츠는 private에서. private → public 방향 push는 리모트 설정으로 차단한다.

```bash
git remote add template <public-repo-url>
git remote set-url --push template no_push
```

### 7. 웹앱은 Astro + Cloudflare Workers, 정적 우선

- public 문서 → prerender (정적 asset)
- private 문서 → `prerender = false`, Worker SSR + 세션 검사
- 검색 → Pagefind 정적 인덱스. 외부 API·벡터 DB 미사용
- 세션 → HMAC 서명 쿠키 (KV 불필요, 사용자 1명)

**주의**: Workers Static Assets는 Worker보다 먼저 응답한다. prerender된 파일은 URL만 알면 인증 없이 받아지므로, **private 문서를 prerender하지 않는 것이 1차 방어선**이다.

**근거**: content collections의 zod 스키마가 frontmatter 검증기를 겸한다 — 스키마를 어긴 문서가 있으면 빌드가 실패하므로 별도 검증 도구가 필요 없다.

### 8. 임베딩은 로컬 전용

ingest 시점에 로컬에서 유사 문서를 찾고, 결과인 `related:` 링크만 정적으로 고정한다. 웹앱에는 런타임 추론이 없다.

**주의**: 콘텐츠가 한글+영문 혼용이므로 다국어 임베딩 모델이 필수다. 널리 쓰이는 `all-MiniLM` 계열은 영어 전용이라 한글 유사도가 무의미해진다. `bge-m3`·`multilingual-e5` 계열을 쓴다.

## 결과

- 위키는 웹앱 없이도 Obsidian + Claude Code 조합으로 즉시 사용 가능하다
- 공개 여부는 repo 가시성이 아니라 문서 단위 속성으로 제어된다
- 누출 경로가 `raw/` 제외 + private 미prerender로 구조적으로 차단된다

## 남은 리스크

- **부산물 누출**: `graph.json` 노드 라벨, 검색 인덱스, RSS·sitemap에 private 제목이 실릴 수 있다. 빌드 산출물을 grep해 검증하는 CI 가드가 필요하다
- **웹 편집 지연**: 커밋 → CI 재빌드 구조라 반영에 1~2분이 걸린다
- **private 전문 검색**: Pagefind는 정적 인덱스를 그대로 fetch하는 구조라 인증 뒤에 두기 어렵다. 초기에는 title·tags 수준의 경량 인덱스로 대체한다
