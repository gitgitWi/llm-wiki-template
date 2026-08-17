# llm-wiki-template

LLM이 관리하는 개인 지식베이스 템플릿. 마크다운 + git만으로 동작하고, 위키 유지는 Claude Code(또는 Codex)가 맡는다. 파일은 평범한 마크다운 + `[[위키링크]]` 라서 제텔카스텐 방식을 지원하는 에디터에서 그대로 열린다 — 특정 앱에 묶이지 않는다.

[Karpathy의 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 패턴을 기반으로, Zettelkasten의 원자성·연결 원칙과 커뮤니티에서 나온 쓰기 게이트 규칙을 얹었다. 배경 조사는 [`wiki/synthesis/llm-wiki-methodology.md`](wiki/synthesis/llm-wiki-methodology.md), 구조 결정 근거는 [`wiki/meta/adr-0001-structure.md`](wiki/meta/adr-0001-structure.md) 참조.

## 무엇이 다른가

일반 RAG는 질문할 때마다 원본에서 지식을 다시 찾아낸다. 축적이 없다.

이 구조는 **소스를 넣는 시점에 LLM이 위키를 갱신**한다. 요약 페이지를 만들고, 관련 개념 페이지를 고치고, 크로스링크를 걸고, 인덱스를 갱신한다. 지식이 한 번 정리되어 계속 유지되고, 쓸수록 복리로 쌓인다.

사람이 위키를 직접 쓰지 않는다. 사람은 소싱·방향·질문을 맡고, 북키핑은 LLM이 한다.

## 구조 — 폴더가 곧 쓰기 권한

| 계층 | 내용 | LLM 권한 |
|---|---|---|
| `raw/` | 외부 원본 (기사·스레드·영상·논문·공고) | **읽기 전용** |
| `notes/` | 직접 쓴 글 (메모·아이디에이션·커리어) | **제안만** |
| `wiki/` | LLM이 생성·유지하는 페이지 | **자유 쓰기** |

```
raw/      articles/ threads/ videos/ papers/ jobs/ assets/   ← 소스 타입별 (공개 repo에선 gitignore)
notes/    inbox/ ideas/ career/ logs/                        ← 목적별
wiki/     index.md digests/ concepts/ entities/ synthesis/ meta/   (log.md 는 .dev/ 로 이동)
tools/    article_archive/
.dev/     log.md llm-wiki-setup/                           ← 개발·운영 로그, Phase 문서
CLAUDE.md                                                    ← 운영 스키마
```

**분야는 폴더가 아니라 frontmatter로 나눈다.** 폴더는 하나만 고를 수 있어서 여러 분야에 걸친 자료를 담지 못한다.

```yaml
domains: [ai, career]     # 닫힌 어휘 — 내비게이션용
tags: [llm, hiring]       # 열린 어휘 — LLM이 추출
visibility: private       # 누락·오타 시 private 취급
```

## 연산

`.claude/commands/` 에 정의되어 있다.

| 커맨드 | 하는 일 |
|---|---|
| `/ingest <url>` | raw 저장 → 요약 페이지 작성 → 관련 개념·엔티티 갱신·크로스링크 → index·log 갱신 |
| `/query <question>` | index부터 드릴다운 → 인용 포함 답변 → **좋은 답변은 페이지로 저장** |
| `/lint` | 고아 페이지·깨진 링크·모순·스키마 위반·공개 안전 점검 |
| `/publish <path>` | 개인정보·회사정보·저작권·private 링크 체크 후 공개 전환 |

## 수집 파이프라인

[`tools/article_archive`](tools/article_archive) 가 URL을 마크다운으로 바꾼다 — defuddle / fxtwitter / 브라우저 폴백의 3단 추출, 한국어 요약·번역, 스키마대로 쓰인 frontmatter까지. Python은 stdlib만 쓰고 node 의존성은 `defuddle` 하나다.

```bash
python3 tools/article_archive/cli.py scrap <url> --json     # -> raw/articles/<stem>.md
python3 tools/article_archive/cli.py summarize <stem>        # -> wiki/digests/<stem>.md
```

프론트엔드에 묶여 있지 않아서 `/ingest`(Claude Code)와 Discord 봇이 같은 도구를 쓰고 같은 파일을 만든다.

**`scrap`은 모델을 호출하지 않는다.** 추출은 결정적 스크립팅이고, 요약·번역만 에이전트(`cline`) 세션 한 번으로 처리한다. 프롬프트에 본문을 싣는 대신 **격리된 작업 디렉토리에 파일을 넣고 경로만 알려주므로**, 청크를 나눌 일도 용어가 청크마다 달라질 일도 없다. 에이전트는 저장소를 보지 못한다.

**원문과 전문 번역은 `raw/` 에, 요약은 `wiki/digests/` 에 쓴다.** 앞의 둘은 남의 글이고 전문 번역은 오히려 더 명확한 파생 저작물이라 공개 대상이 아니다. 요약은 내가 쓴 것이라 공개할 수 있다.

## 쓰기 게이트

LLM에게 전권을 주지도, 전부 승인받게 하지도 않는다.

| 유형 | 처리 |
|---|---|
| 재도출 가능 — 요약·태그·크로스링크 | 자유롭게 자동 작성 |
| 되돌릴 수 있음 — 구조 변경 | 작성하되 log에 남김 |
| 비가역적·사람에 대한 주장 — 삭제·인물 평가 | 제안만, 승인 대기 |

**모순은 이원화한다.** 날짜·수치처럼 재계산 가능한 불일치는 바로 고치고, 두 산문 주장이 충돌하면 위키에 확정하지 않고 사람에게 보고한다. 모델의 추론이 지식 기반에 고착되는 것을 막기 위함이다.

git이 최종 안전망이라 LLM이 잘못 써도 되돌릴 수 있다.

## 시작하기

```bash
# 1. 이 저장소를 받는다
git clone https://github.com/gitgitWi/llm-wiki-template.git my-wiki
cd my-wiki

# 2. 예시 콘텐츠를 비운다 (원하면)
rm wiki/synthesis/*.md

# 3. 이 폴더에서 Claude Code를 띄운다
#    그래프·백링크 탐색이 필요하면 제텔카스텐 방식 에디터로 같은 폴더를 열면 된다 (선택)
#    브라우저 클리퍼 확장을 쓴다면 저장 경로를 raw/articles/ 로 맞춘다

# 4. 첫 소스를 넣는다
#    /ingest https://example.com/article
```

### 비공개로 쓰려면

개인 자료를 넣을 거라면 private 저장소가 필요하다. **fork는 안 된다** — public repo의 fork는 항상 public이고 private으로 바꿀 수 없다.

```bash
git clone https://github.com/gitgitWi/llm-wiki-template.git my-wiki
cd my-wiki
git remote rename origin template
git remote set-url --push template no_push    # 콘텐츠가 위로 새는 사고 방지
gh repo create my-wiki --private --source=. --push --remote=origin

# 이후 템플릿 업데이트를 받을 때
git merge template/main
```

## 로드맵

- [x] **Phase 0** — 3계층 구조, 운영 스키마, 슬래시 커맨드
- [ ] **Phase 1** — Astro + Cloudflare Workers 웹앱, Pagefind 검색, 그래프 뷰
- [ ] **Phase 2** — GitHub OAuth, private 문서 열람, 누출 가드 CI
- [ ] **Phase 3** — 웹 편집, 모바일 퀵캡처, 로컬 임베딩 기반 관련 문서 제안

## 라이선스

구조·스키마·커맨드는 MIT. `wiki/` 아래 문서는 각 문서의 출처 표기를 따른다.
