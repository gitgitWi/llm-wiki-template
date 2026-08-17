---
description: 소스를 raw/에 저장하고 위키에 통합한다
argument-hint: <url | 파일경로> [--public]
---

소스: `$ARGUMENTS`

아래 절차를 순서대로 수행한다. 중간에 건너뛰지 않는다.

## 1. 저장

소스 타입을 판별해 해당 폴더에 저장한다. **파일명은 ASCII kebab-case 슬러그 + `.md`.**

| 타입 | 저장 위치 |
|---|---|
| 블로그·뉴스·기술 문서 | `raw/articles/` |
| X(트위터)·HN·Reddit 스레드 | `raw/threads/` |
| 유튜브 등 영상 (자막·요약) | `raw/videos/` |
| arXiv·논문·PDF | `raw/papers/` |
| 채용 공고 | `raw/jobs/` |
| 이미지·첨부 | `raw/assets/` |

URL이면 본문을 가져와 마크다운으로 변환해 저장한다. 이미 로컬 파일이면 해당 폴더로 복사한다.
`graphify add <url>` 도 기본 저장 경로가 `./raw` 라 사용 가능하다.

frontmatter에 `source.url`, `source.author`, `source.captured` 를 기록한다. **`raw/` 는 항상 `visibility: private`.**

저장 후 **원본은 다시 수정하지 않는다.**

## 2. 읽기

저장한 원본을 처음부터 끝까지 읽는다. 요약본이나 발췌만 보고 판단하지 않는다.

## 3. digest 작성

`wiki/digests/<같은-슬러그>.md` 를 만든다.

- **내 언어로 재작성한다.** 원문 문장을 그대로 옮기지 않는다. 직접 인용이 꼭 필요하면 인용부호 + 출처를 붙인다.
- 구성: 핵심 주장 → 근거·세부 → 내가 쓸 수 있는 지점 → 원문 링크
- `type: source`, `source.url` 필수
- `visibility` 는 **기본 `private`**. 인자에 `--public` 이 있으면 `public`
- `tags` 는 내용에서 추출하고, `domains` 는 닫힌 어휘(`ai` `dev` `career` `product` `infra` `misc`)에서 고른다. 여러 분야에 걸치면 여러 개 넣는다

## 4. 관련 페이지 갱신 — 여기가 핵심

digest만 만들고 끝내면 위키가 자라지 않는다. 이 소스가 건드리는 개념·엔티티를 찾아 **기존 페이지를 갱신**한다.

- 이미 있는 `wiki/concepts/`·`wiki/entities/` 페이지 중 관련된 것을 찾아 새로 알게 된 내용을 반영한다
- 중요한 개념인데 페이지가 없으면 새로 만든다 (원자적으로, 하나의 개념만)
- 양방향으로 `[[링크]]` 를 건다. digest → 개념, 개념 → digest 둘 다
- 기존 주장과 충돌하는 내용이 있으면 §6으로

**고아 페이지를 만들지 않는다.** 새 페이지는 최소 1개 이상의 기존 페이지와 연결되어야 한다.

## 5. index·log 갱신

- `wiki/index.md` — 새로 만든 페이지를 해당 카테고리에 링크 + 한 줄 요약으로 추가
- `wiki/log.md` — 맨 아래에 덧붙인다. 기존 항목은 건드리지 않는다

```markdown
## [YYYY-MM-DD] ingest | <소스 제목>
- raw/articles/<slug>.md 저장
- wiki/digests/<slug>.md 생성
- wiki/concepts/<slug>.md 갱신
```

## 6. 보고

작업 후 사용자에게 짧게 보고한다:

- 만든 페이지 / 갱신한 페이지 목록
- **기존 위키와 모순되는 주장** — 위키에 확정해 넣지 말고 여기서 보고만 한다
- 다뤄지지 않은 갭, 이어서 읽으면 좋을 것
- digest가 `private` 이면 `/publish` 로 공개 전환 가능하다고 안내
