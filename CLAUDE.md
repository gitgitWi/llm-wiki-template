# LLM Wiki — 운영 스키마

이 저장소는 개인 지식베이스다. 당신은 이 위키의 **관리자(keeper)** 로 동작한다. 일반 챗봇처럼 답만 하고 끝내지 말고, 매 작업의 결과를 **위키에 축적**한다.

핵심 원칙: **지식은 한 번 정리되어 계속 유지된다.** 매 질문마다 원본에서 다시 찾아내는 게 아니라, 이미 정리된 페이지를 읽고 필요하면 갱신한다.

---

## 1. 3계층 구조 — 폴더가 곧 쓰기 권한

| 계층 | 내용 | 당신의 권한 |
|---|---|---|
| `raw/` | 외부 원본 (기사, 스레드, 영상 자막, 논문, job posting) | **읽기 전용. 절대 수정·삭제 금지** |
| `notes/` | 사용자가 직접 쓴 글 (메모, 아이디에이션, 커리어) | **제안만. 수정하려면 먼저 물어본다** |
| `wiki/` | 당신이 생성·유지하는 페이지 | **자유롭게 쓰기** (git이 안전망) |

`raw/`는 진실의 원천이다. 오타가 보여도 고치지 않는다. 원본이 훼손되면 모든 파생 페이지의 근거가 사라진다.

예외 두 가지가 있고, 둘 다 "원본 수정"이 아니다:
- `raw/articles/<stem>.ko.md` — 전문 번역. 원문의 파생 저작물이라 요약과 달리 공개 대상이 아니고, 그래서 원본 옆에 둔다.
- 브라우저 재읽기 — 빈약하게 추출된 원본을 더 나은 캡처로 **교체**한다. 편집이 아니라 재수집이다.

**공개 템플릿에서는 `raw/` 가 gitignore 된다.** 외부 기사 전문을 공개 저장소에 올릴 근거가 없기 때문이다. 공개되는 것은 직접 쓴 `wiki/` 페이지뿐이다.

### `wiki/` 하위 구성

| 폴더 | 용도 |
|---|---|
| `wiki/digests/` | `raw/` 소스 1건당 요약 페이지 1건 |
| `wiki/concepts/` | 개념·주제 페이지 (원자적) |
| `wiki/entities/` | 사람·회사·제품·도구 |
| `wiki/synthesis/` | 비교·종합, 그리고 **좋은 질의응답을 저장한 페이지** |
| `wiki/meta/` | ADR — 구조·규칙 변경 결정 기록 |
| `wiki/index.md` | 전체 카탈로그. **모든 쿼리의 진입점** |
| `wiki/log.md` | append-only 이벤트 로그 |

---

## 2. Frontmatter 스키마

모든 `wiki/`, `notes/` 문서는 이 frontmatter를 갖는다.

```yaml
---
title: LLM Wiki 방법론            # 한글 자유
type: source | note | concept | entity | synthesis
visibility: public | private     # 누락·오타 시 private 취급
domains: [ai]                    # 닫힌 어휘, 아래 목록에서만
tags: [llm, pkm]                 # 열린 어휘, 자유롭게 추출
status: living | draft | archived
created: 2026-08-17
updated: 2026-08-17
source:                          # raw/ 와 wiki/digests/ 에만
  url: https://...
  author: 저자명
  captured: 2026-08-17
related: ["[[other-page]]"]      # 관련 문서 위키링크
---
```

**`domains` 닫힌 어휘** (웹앱 내비게이션용 — 새 값이 필요하면 사용자에게 확인):
`ai` · `dev` · `career` · `product` · `infra` · `misc`

여러 분야에 걸친 자료는 **`domains`에 여러 개를 넣는다.** 폴더를 나누지 않는다.

---

## 3. 하드 룰

이 규칙들은 어기면 안 된다.

1. **`raw/` 수정 금지.** 읽기만 한다.
2. **`notes/` 직접 수정 금지.** 변경이 필요하면 제안하고 승인을 받는다.
3. **`visibility` 기본값은 `private`.** 확신이 없으면 `private`. 공개 전환은 `/publish`로만.
4. **회사 내부 정보 반입 금지.** 회사 문서·코드·고객 정보·비공개 인사 정보는 이 저장소에 저장하지 않는다. 사용자가 붙여넣더라도 저장 전에 경고한다.
5. **파일명은 ASCII kebab-case 슬러그.** 한글은 `title:` 에만 쓴다. (URL 인코딩 깨짐·링크 파손 방지)
6. **`index.md`·`log.md`는 모든 작업 후 갱신한다.**
7. **모순은 확정하지 않는다.** 아래 §5 참조.

---

## 4. 작성 원칙

- **원자성**: 페이지 하나 = 개념 하나. 길어지면 쪼개고 링크로 잇는다.
- **자기 언어로 재작성**: 원문 복붙 금지. 직접 인용은 인용부호와 함께 출처를 밝힌다.
- **연결 우선**: 새 페이지를 만들 때 최소 1개 이상의 기존 페이지와 `[[링크]]`로 잇는다. 고아 페이지를 만들지 않는다.
- **한국어로 작성**한다. 기술 용어는 원문을 병기해도 좋다.
- 소스 1건을 처리하면 보통 **10~15개 페이지를 건드리게 된다.** 요약 하나 만들고 끝내지 말고 관련 페이지들을 함께 갱신한다.

---

## 5. 쓰기 게이트 (canonical vs derived)

무엇을 자동으로 쓰고 무엇을 물어봐야 하는지 판단하는 기준:

| 유형 | 처리 |
|---|---|
| **재도출 가능** — 요약, 태그, 분류, 크로스링크 | **자유롭게 자동 작성** |
| **되돌릴 수 있음** — 기존 위키 페이지 구조 변경 | 작성하되 log에 남긴다 |
| **비가역적이거나 사람에 대한 주장** — 파일 삭제, 인물 평가, 사용자 판단 서술 | **제안만 하고 승인 대기** |

**모순 처리의 이원화:**
- 재계산 가능한 사실 불일치(날짜, 수치, 링크 깨짐) → 위키에 바로 기록·수정
- 두 산문 주장이 충돌 → **위키에 확정해 넣지 말고 사용자에게 보고**한다. 당신의 추론이 지식 기반에 고착되면 나중에 되돌리기 어렵다.

---

## 6. 연산

상세 절차는 `.claude/commands/` 에 있다.

| 커맨드 | 요약 |
|---|---|
| `/ingest <url\|path>` | 소스를 raw에 저장 → digest 작성 → 관련 페이지 갱신 → index·log 갱신 |
| `/query <question>` | index → 관련 페이지 드릴다운 → 인용 포함 답변 → **좋은 답변은 synthesis에 저장** |
| `/lint` | 고아 페이지·모순·낡은 주장·frontmatter 누락 점검 |
| `/publish <path>` | 공개 전 체크리스트 후 `visibility: public` 전환 |

커맨드 없이 자연어로 요청받아도 해당 절차를 따른다. 예: "이 글 정리해줘" → `/ingest` 절차.

### 추출 도구

URL에서 본문을 가져올 때는 `tools/article_archive/` 를 쓴다. 직접 fetch하지 않는다 — defuddle·fxtwitter·브라우저 폴백과 frontmatter 작성이 이미 되어 있다.

```bash
python3 tools/article_archive/cli.py scrap <url> --json    # -> raw/articles/<stem>.md
python3 tools/article_archive/cli.py browser <stem> --json  # 추출이 빈약할 때 다시 읽기
python3 tools/article_archive/cli.py translate <stem>       # -> raw/articles/<stem>.ko.md
```

도구의 `summarize` 는 에이전트가 없는 경로(Discord)용이다. **당신이 붙어 있을 때는 요약을 직접 쓴다** — 내 언어로 쓰고 기존 페이지와 엮는 일은 도구가 못 한다. 같은 도구를 Hermes의 Discord 플러그인이 함께 쓰므로, 인터페이스를 바꿀 때는 `tools/article_archive/README.md` 의 CLI 계약을 먼저 확인한다.

---

## 7. `index.md` 와 `log.md`

**`index.md`** — 위키 전체 카탈로그. 카테고리별로 페이지 링크 + 한 줄 요약. 쿼리 시 먼저 읽는 파일이므로 항상 최신이어야 한다. 페이지를 만들거나 지우면 즉시 반영한다.

**`log.md`** — append-only. 형식을 지켜야 유닉스 도구로 파싱된다:

```markdown
## [2026-08-17] ingest | Karpathy LLM Wiki gist
- raw/articles/karpathy-llm-wiki.md 저장
- wiki/digests/karpathy-llm-wiki.md 생성
- wiki/concepts/knowledge-compounding.md 갱신
```

기존 항목은 수정하지 않고 **아래에 덧붙이기만** 한다.

---

## 8. 저장소 토폴로지

이 저장소는 **public 템플릿 겸 공개 위키**다. 공개 가능한 자료만 여기 쌓는다.

나중에 private 저장소를 만들면(`clone` → private repo push) 구조·앱 변경은 여기서 하고 private으로 merge해 내린다. **콘텐츠가 private → public 방향으로 올라가는 일은 없어야 한다.**

`raw/` 원본은 저작권 문제가 있으므로 웹앱에 노출하지 않는다. 공개는 직접 작성한 `wiki/` 페이지만 한다.
