---
title: Pi vs oh-my-pi — 코딩 하네스 비교
type: synthesis
visibility: public
domains: [ai, dev]
tags: [pi, oh-my-pi, omp, coding-agent, harness, hashline, context-management, token-optimization]
status: living
created: 2026-08-20
updated: 2026-08-20
description: Tradeoff comparison between minimally extending the original Pi (pi-mono) and using the oh-my-pi (omp) fork — focusing on context/token management and performance in coding work.
read_when: When choosing a Pi-family terminal coding agent and deciding between "just adding plugins" vs "using the omp fork".
agent: glm-5.2 (xhigh) / fx
related: []
---

# Pi vs oh-my-pi — 코딩 하네스 비교

> 2026-08-20 조사·정리. "AI Coding Harness Pi에 그냥 provider, web-search plugin 정도 붙여서 쓰는 것"과
> [oh-my-pi](https://github.com/can1357/oh-my-pi)(`omp`)를 쓰는 것의 장단점을, 특히 **코딩 작업의 컨텍스트/토큰 관리와 성능** 측면에서 비교한다.

---

## 핵심 관계 — 둘은 같은 뿌리의 다른 가지

| | 원본 Pi | oh-my-pi (omp) |
|---|---|---|
| **저장소** | [badlogic/pi-mono](https://github.com/badlogic/pi-mono) (→ [earendil-works/pi](https://github.com/earendil-works/pi)로 이동) | [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi) |
| **만든 사람** | Mario Zechner | Can Bölük (Pi 포크) |
| **철학** | 미니멀 — 4개 도구(read·write·edit·bash), 짧은 시스템 프롬프트, 나머지는 TypeScript 확장 | 하네스가 곧 제품 — edit 포맷·서브에이전트·LSP/DAP까지 하네스 측에서 해결 |
| **런타임** | TypeScript / Node | TypeScript + Rust 네이티브 엔진 (~80k lines) |
| **edit 도구** | `str_replace` (문자열 검색·치환) | **hashline** (콘텐츠 해시 앵커) |
| **프로바이더** | 15+ (pi-ai 통합 API) | 60+ |
| **컨텍스트 관리** | auto-compaction + branch summarization | Pi의 compaction 계승 + stream rules·advisor·서브에이전트·역할 라우팅 |

**중요**: omp는 Pi의 *포크*다. 즉 "Pi에 provider/web-search plugin만 붙이는 방식"과 "omp를 쓰는 방식"은 같은 Pi를 출발점으로 삼되, **하네스를 어디까지 튜닝하느냐**의 스펙트럼 양끝에 가깝다.

---

## 원본 Pi — "모델에 맞춰라, 하네스는 얇게"

Mario Zechner의 Pi는 의도적으로 얇다. 핵심 주장은 "4개 API(OpenAI Completions/Responses, Anthropic Messages, Google Generative AI)면 모든 LLM 프로바이더와 대화할 수 있다"는 것에서 출발해, 에이전트 루프·TUI·세션 관리까지 최소로 쌓는다 ([그의 회고](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)).

### 컨텍스트/토큰 관리

Pi는 두 가지 요약 메커니즘을 내장한다 ([pi.dev compaction 문서](https://pi.dev/docs/latest/compaction)):

- **Auto-compaction** — `contextTokens > contextWindow - reserveTokens`일 때 트리거. `reserveTokens`(기본 16384)는 LLM 응답용 여유, `keepRecentTokens`(기본 20000)만큼 최근 토큰은 보존하고 그 이전 메시지를 LLM으로 요약. `/compact [instructions]`로 수동 트리거도 가능.
- **Branch summarization** — `/tree`로 브랜치를 전환할 때 컨텍스트를 보존. 같은 구조화된 요약 포맷을 쓰고 파일 조작을 누적 추적.

설정은 `~/.pi/agent/settings.json` 또는 프로젝트 `.pi/settings.json`에서:

```json
"compaction": {
  "enabled": true,
  "reserveTokens": 16384,
  "keepRecentTokens": 20000
}
```

### 확장 모델

원하는 provider나 web-search는 **TypeScript 확장**으로 붙인다 — Skills(마크다운 정의 도구세트), Prompt Templates, Themes, Extensions(`jiti`로 동적 로드)가 전부 이 얇은 층 위에서 동작한다. Pi 내부를 포크·수정할 필요 없이 워크플로우에 맞춘다.

### 이 방식의 본질

"모델이 제일 중요하고, 하네스는 모델과 디스크 사이의 얇은 다리"라는 전제. edit는 `str_replace`에 의존하므로, 모델이 변경할 줄을 **그대로 다시 타이핑**해서 패치를 만든다. 잘 튜닝된 모델에서는 잘 작동하지만, 모델과 하네스가 딱 맞지 않으면 whitespace 배틀·string-not-found 루프·재시도 사이클이 토큰을 잡아먹는다.

---

## oh-my-pi (omp) — "하네스가 곧 제품"

Can Bölük의 프레이밍: **"The model is the moat. The harness is the bridge."** ([blog.can.ac, 2026-02-12](https://blog.can.ac/2026/02/12/the-harness-problem/)). omp는 이 다리를 제품 서피스로 취급한다.

### 1 · Hashline — 해시 앵커드 에디트 (가장 큰 차별점)

`edit` 도구를 `str_replace`에서 [hashline](https://github.com/can1357/oh-my-pi/blob/main/packages/hashline/README.md)으로 교체했다.

- 하네스가 읽은 **모든 줄에 2-3 hex content hash**를 태그로 단다.
- 패치는 `[PATH#TAG]` 전체 파일 콘텐츠 해시에 앵커된다.
- 파일이 변경됐으면 **패치 적용 전에 거부** — 손상이 일어나기 전에 차단.
- 모델은 변경할 줄을 **다시 타이핑하지 않는다** — 앵커를 가리키기만 하면 하네스가 SWAP/INS/DEL을 해석·적용.
- stale anchor는 3-way-merge로 복구.

**왜 토큰에 영향이 큰가**: `str_replace`는 모델이 원본 줄 전체를 출력에 재생성해야 한다. hashline은 앵커만 가리키면 되므로 출력 토큰이 줄어들고, 실패·재시도 루프 자체가 사라진다.

### 2 · 컨텍스트/토큰 관리 — Pi 위에 쌓은 추가층

omp는 Pi의 compaction을 계승하면서, 토큰을 아끼고 컨텍스트를 분산하는 메커니즘을 더한다:

| 메커니즘 | 하는 일 | 토큰/컨텍스트 효과 |
|---|---|---|
| **Stream rules** | 정규식 매치가 스트리밍 출력을 mid-token에 중단 → 룰을 system reminder로 주입 → 같은 지점에서 재시도 | "매 턴 룰을 컨텍스트에 안 넣고도 코스 코렉션" — 컨텍스트 텍스(tax) 없음. 인젝션은 compaction 이후에도 생존 |
| **Advisor 모델** | `advisor` 역할의 두 번째 모델이 매 턴을 읽고 인라인으로 노트 주입 | 메인 에이전트와 **별도 컨텍스트·별도 모델**에서 시맨틱 드리프트를 잡음 — 메인 컨텍스트를 오염시키지 않음 |
| **서브에이전트 (`task`)** | isolated worktrees에 팬아웃, 결과는 스키마 검증된 객체로 부모가 직접 읽음 | 메인 세션 컨텍스트 폭발을 막음 — 무거운 작업을 별도 컨텍스트로 격리. `agent://<id>/findings.0.path` URI로 결과 필드 접근 |
| **역할 라우팅** (10 역할) | `default`/`smol`/`slow`/`plan`/`commit`/`vision`/`designer`/`task`/`advisor`/`tiny` — 인텐트별 모델 할당 | `smol`로 싼 모델을 서브에이전트에 → 비용 절감. `slow`로 깊은 추론만 비싼 모델에 할당 |
| **rewind** | 탐색적 컨텍스트를 정리하고 간결한 리포트만 보존 | 컨텍스트에서 잡음(탐색 실패 등)을 제거 |
| **snapcompact** | 비트맵 프레임 래스터화 + PNG 인코드로 이미지 컨텍스트 압축 | 이미지가 컨텍스트를 잡아먹는 비용 절감 |
| **네이티브 토큰 카운팅** | tiktoken-rs (O200k/Cl100k BPE) — 테이블 임베디드 | 정확한 토큰 추정으로 compaction 타이밍 최적화 |

### 3 · LSP/DAP — IDE급 인텔리전스

14 LSP ops + 28 DAP ops. rename이 전파되고, 실제 디버거를 구동한다. Pi에는 없는 층.

### 4 · 배터리 포함

60+ 프로바이더, 31 내장 도구, 8포맷 config import(Cursor MDC·Cline `.clinerules`·Codex `AGENTS.md`·Copilot `applyTo`를 원형 그대로 읽음), 16개 내부 URI 스킴(`pr://`·`issue://`·`agent://`·`skill://` 등), 네이티브 Windows(WSL 브릿지 없음), hindsight memory, plan mode.

---

## 성능 비교 — hashline 벤치마크

omp의 README가 발행한 벤치마크는 **540 태스크, 16 모델, 태스크당 3회, 매회 fresh session**이다. 핵심은 **같은 모델·같은 가중치·같은 프롬프트에서 하네스(edit 포맷)만 바꿨을 때**의 차이:

| 모델 | metric | 무엇이 바뀌었는가 |
|---|---|---|
| Grok Code Fast 1 | 6.7% → 68.3% | edit 포맷이 모델을 잡아먹지 않을 때 10배 상승 |
| Gemini 3 Flash | +5 pp | `str_replace` 대비 — Google 자체 최선 시도도 능가 |
| Grok 4 Fast | −61% tokens | bad diff 재시도 루프가 사라지자 출력이 붕괴 |
| MiniMax | 2.1× | 같은 가중치·같은 프롬프트에서 pass rate 2배 이상 |

> **주의**: 네 수치 모두 *프로젝트 자체 발행·자기 귀속*이다. 하네스 기여가 낼 수 있는 **오더 오브 매그니튜드**로 읽어야지, 계약서급 보증이 아니다 ([lesbass 분석](https://news.lesbass.com/articles/oh-my-pi-ai-coding-agent-harness/)). 독립 재현이 아직 없다.

**해석**: Pi(플러그인 방식)의 `str_replace`는 위 벤치마크의 str_replace baseline에 해당한다. 즉, 하네스가 모델에 딱 맞게 튜닝되지 않으면, 같은 모델이라도 패치 실패→재시도→토큰 낭비 사이클이 성능을 깎는다. hashline은 이 사이클 자체를 제거한다.

---

## 코딩 작업에서의 실질적 장단점

### "Pi에 provider/web-search plugin만 붙인다"의 장단점

**장점**
- **미니멀** — 시스템 프롬프트 짧고, 컨텍스트가 깔끔. 무엇이 들어가는지 투명하다.
- **유연한 커스터마이징** — 원하는 provider/web-search만 TypeScript 확장으로 붙인다. Pi 내부를 포크할 필요 없음.
- **compaction으로 충분한 경우가 많음** — 중소 규모 작업에서는 auto-compaction + branch summarization이 컨텍스트를 잘 관리한다.
- **의존성 얇음** — 공급망 리스크 적음. 업스트림 Pi(65.7k stars, 240 releases)에 가깝고 안정적.
- **배우기 쉬움** — 4개 도구 + 확장 레이어. 소스를 읽을 수 있고, 고장 나도 원인 범위가 좁다.

**단점**
- **`str_replace`의 토큰 비용** — 모델이 변경할 줄을 다시 타이핑 → 출력 토큰 낭비. 실패 시 재시도 루프가 추가로 잡아먹는다.
- **모델-하네스 정합도에 민감** — 특정 모델에 튜닝되지 않은 harness는 패치 실패율이 올라간다(omp 벤치마크의 str_replace baseline 참조).
- **컨텍스트 분산 부재** — 서브에이전트가 없거나 약해, 큰 작업이 메인 세션 컨텍스트를 채운다.
- **LSP/DAP 없음** — rename 전파, 실제 디버깅 같은 IDE급 인텔리전스 부재.
- **드리프트 캐치 없음** — stream rules나 advisor 같은 "모델이 빗나갈 때 잡아주는" 메커니즘이 없다.

### oh-my-pi(omp)를 쓰는 것의 장단점

**장점**
- **hashline edit** — 토큰 절약(Grok 4 Fast −61%), 실패율 급감(Grok Code Fast 1 10배), 모델 비의존적. 코딩 작업의 가장 빈번한 도구(edit)가 가장 크게 개선된다.
- **컨텍스트 분산** — 퍼스트클래스 서브에이전트가 메인 세션 컨텍스트 폭발을 막는다. `smol` 역할로 싼 모델을 서브에이전트에 돌려 비용 절감.
- **컨텍스트 텍스 없는 코스 코렉션** — stream rules가 매 턴 룰을 컨텍스트에 넣지 않고도 모델을 바로잡는다. advisor는 별도 컨텍스트에서 시맨틱 드리프트를 잡는다.
- **역할 라우팅으로 비용/성능 최적화** — 인텐트별로 모델을 다르게 할당(싼 작업은 `smol`, 깊은 추론은 `slow`).
- **LSP/DAP** — rename 전파, 실제 디버거 구동. 코딩 정확도 상승.
- **배터리 포함** — 60+ 프로바이더, config import, URI 스킴 등 마이그레이션 비용 낮음.

**단점**
- **복잡도** — ~80k lines Rust core + TypeScript. 학습 곡선이 있고, 무엇이 컨텍스트에 들어가는지 추적이 Pi보다 어렵다.
- **공급망 리스크** — 60+ 프로바이더 SDK, 14 web-search 백엔드, MCP/ACP/Discord까지 표면이 넓다.
- **포크 불확실성** — 업스트림 Pi와의 동기화가 보장되지 않는다(fork, not vendor branch). 1인 maintainer(Can Bölük), vouch 기반 기여 모델.
- **자체 발행 벤치마크** — 10배 등 수치는 self-attributed. 독립 재현 필요.
- **빠른 릴리스 케이던스** — 18시간 단위 릴리스는 속도 신호이지 안정성 신호가 아니다. 369 open issues / 10,671 commits.
- **`my.omp.sh` relay** — 서드파티 의존성. 프레임은 클라이언트에서 봉인되지만 가용성 보장은 없다.

---

## 컨텍스트/토큰 관리 — 한눈에 비교

| 축 | Pi (플러그인) | omp |
|---|---|---|
| **compaction** | auto-compaction + branch summarization (계승) | 동일 + 추가층 |
| **edit 토큰** | `str_replace` — 줄 재타이핑 → 비용 높음 | hashline — 앵커만 가리킴 → 비용 낮음 (최대 −61%) |
| **실패 재시도 루프** | 발생 → 추가 토큰 소모 | 앵커 기반 거부로 루프 자체 제거 |
| **컨텍스트 분산** | 없음 (메인 세션에 집중) | 서브에이전트 + isolated worktrees |
| **코스 코렉션 비용** | 룰을 매번 컨텍스트에 넣어야 → 텍스 | stream rules → 컨텍스트 텍스 없음 |
| **드리프트 감지** | 없음 | advisor 모델 (별도 컨텍스트) |
| **비용 최적화** | 단일 모델 | 역할 라우팅 (`smol`/`slow` 등) |
| **토큰 카운팅** | 추정치 | 네이티브 tiktoken-rs (정확) |
| **이미지 컨텍스트** | 원본 그대로 | snapcompact 압축 |

**결론**: 컨텍스트/토큰 관리 측면에서 omp는 Pi의 compaction을 기본으로 두고, 그 위에 "edit에서 토큰을 아끼고(Grok 4 Fast −61%), 컨텍스트를 분산하고(서브에이전트), 코스 코렉션에 텍스를 안 내고(stream rules), 드리프트를 별도 컨텍스트에서 잡고(advisor), 비용을 역할별로 최적화한다(라우팅)"는 층을 쌓는다. Pi(플러그인) 방식은 compaction 하나로 커버하는 구조라, edit 실패·재시도가 토큰을 잡아먹는 구멍이 가장 크다.

---

## 언제 뭘 고를까

| 상황 | 추천 | 이유 |
|---|---|---|
| 작은~중간 프로젝트, 익숙한 모델 하나로 충분 | **Pi + plugin** | 미니멀이 주는 단순함·투명성이 이득. compaction으로 충분 |
| 컨텍스트를 최대한 아�야 하는 큰 작업·장기 세션 | **omp** | 서브에이전트 분산 + hashline 토큰 절약이 결정적 |
| 여러 모델을 인텐트별로 섞어 쓰고 싶음 | **omp** | 역할 라우팅(`smol`/`slow`)이 비용/성능 균형을 줌 |
| 모델-하네스 정합도가 의심되거나 다양한 모델을 시도 중 | **omp** | hashline이 모델 비의존적. str_replace 실패율에 덜 노출 |
| LSP rename 전파·DAP 디버깅이 코딱에 필요 | **omp** | Pi에는 없는 층 |
| 최소 의존성·공급망 리스크 회피 최우선 | **Pi + plugin** | omp는 표면이 넓다 (60+ SDK, relay 등) |
| 소스를 읽고 고장을 좁은 범위에서 잡고 싶음 | **Pi + plugin** | 4개 도구 + 얇은 확장. omp는 80k lines Rust |
| 업스트림 안정성·커뮤니티 규모 우선 | **Pi + plugin** | Pi 65.7k stars / omp는 1인 maintainer 포크 |
| 마이그레이션 비용 최소(Cursor/Cline/Codex 설정 유지) | **omp** | 8포맷 config import를 원형으로 읽음 |

---

## 주의사항

- omp의 벤치마크 수치(10배 등)는 **전부 프로젝트 자체 발행**이다. 독립 재현이 없으므로 오더 오브 매그니튜드로만 읽는다.
- omp는 **포크**다 — 업스트림 Pi와 동기화가 보장되지 않고, maintainer 한 명에게 의존한다. 안정적인 사용을 원하면 **릴리스 태그를 고정(pin)** 한다.
- `my.omp.sh` relay는 서드파티 의존성이다 — 프레임 콘텐츠는 클라이언트에서 봉인되지만, 가용성은 보장되지 않는다.
- Pi의 compaction 설정은 `~/.pi/agent/settings.json`에서 튜닝 가능하다. `keepRecentTokens`를 늘리면 더 많은 최근 컨텍스트를 보존하지만, 빈도가 올라간다.

---

## 출처

- [can1357/oh-my-pi — GitHub](https://github.com/can1357/oh-my-pi) (MIT, 포크 관계·60+ 프로바이더·31 도구·14 LSP·28 DAP·~80k Rust)
- [oh-my-pi main README](https://raw.githubusercontent.com/can1357/oh-my-pi/main/README.md) (hashline·서브에이전트·stream rules·advisor·역할 라우팅·벤치마크 표)
- [@oh-my-pi/hashline README](https://github.com/can1357/oh-my-pi/blob/main/packages/hashline/README.md) (`[PATH#TAG]` 앵커·SWAP/INS/DEL·stale anchor 거부·3-way-merge 복구)
- [Can Bölük — I Improved 15 LLMs at Coding in One Afternoon (blog.can.ac, 2026-02-12)](https://blog.can.ac/2026/02/12/the-harness-problem/) (540-태스크·16-모델 벤치마크, 하네스 문제 프레이밍)
- [lesbass — oh-my-pi: a terminal agent that treats the harness as the product](https://news.lesbass.com/articles/oh-my-pi-ai-coding-agent-harness/) (독립 분석, 리스크·캐버얻 정리)
- [badlogic/pi-mono — GitHub](https://github.com/badlogic/pi-mono) (원본 Pi, 4개 도구·확장 모델)
- [Mario Zechner — What I learned building an opinionated and minimal coding agent](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) (Pi 설계 철학)
- [pi.dev — Compaction 문서](https://pi.dev/docs/latest/compaction) (auto-compaction·branch summarization·설정값)
- [explainx.ai — oh-my-pi (omp) 가이드](https://explainx.ai/blog/oh-my-pi-terminal-coding-agent-omp-mario-zechner-2026) (요약·차별점 정리)
