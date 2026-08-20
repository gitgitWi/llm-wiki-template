---
title: Pi vs oh-my-pi vs fx — 코딩 하네스 3자 비교
type: synthesis
visibility: public
domains: [ai, dev]
tags: [pi, oh-my-pi, omp, fx, coding-agent, harness, hashline, str-replace, context-management, token-optimization, permissions, mcp, subagent]
status: living
created: 2026-08-20
updated: 2026-08-20
description: Three-way comparison of the original Pi, the oh-my-pi (omp) fork, and fx — an independent native harness — across edit format, context/token management, extensibility, and safety model.
read_when: When choosing a terminal coding-agent harness and comparing the Pi lineage (Pi/omp) against fx, or deciding which axis (edit-token cost vs context dispersion vs governance) matters most for the work.
agent: glm-5.2 (xhigh) / fx
related: ["[[pi-vs-oh-my-pi]]"]
---

# Pi vs oh-my-pi vs fx — 코딩 하네스 3자 비교

> 2026-08-20 조사·정리. 기존 [[pi-vs-oh-my-pi]] 비교에 **fx**를 추가해 세 축으로 벌린다.
> Pi 계열(원본 Pi · omp 포크)은 "모델↔하네스 정합도"와 "하네스 튜닝 깊이" 스펙트럼이고,
> fx는 같은 문제를 **거버넌스(권한·샌드박스) + 프로바이더 추상화(AI Gateway) + 네이티브 런타임**이라는 다른 각도에서 푼다.
> 출처: [fx.sh/llms-full.txt](https://fx.sh/llms-full.txt) (공식 문서 전체), 기존 비교 페이지의 인용들은 그대로 계승.

---

## 핵심 관계 — 세 가지 다른 출발점

| | 원본 Pi | oh-my-pi (omp) | fx |
|---|---|---|---|
| **저장소** | [badlogic/pi-mono](https://github.com/badlogic/pi-mono) (→ earendil-works/pi) | [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi) | [fx.sh](https://fx.sh) (closed-source native binary, `~/.local/bin`) |
| **만든 사람** | Mario Zechner | Can Bölük (Pi 포크) | Vercel |
| **철학** | 미니멀 — 4개 도구, 얇은 하네스 | 하네스가 곧 제품 — edit·서브에이전트·LSP/DAP까지 하네스 측에서 | **거버넌스 우선** — 권한·샌드박스·AI Gateway 추상화가 핵심 |
| **런타임** | TypeScript / Node | TypeScript + Rust (~80k lines) | **네이티브 바이너리(Zig)** — macOS/Linux, x86_64/arm64 |
| **edit 도구** | `str_replace` (문자열 치환) | **hashline** (콘텐츠 해시 앵커) | `edit_file` — `str_replace` 계열 (단일 정확 매치 old→new) |
| **프로바이더** | 15+ (pi-ai 통합 API) | 60+ (각 SDK 직접) | **AI Gateway 단일 통합** — 게이트웨이가 노출하는 모든 모델 |
| **컨텍스트 관리** | auto-compaction + branch summarization | Pi 계승 + stream rules·advisor·서브에이전트·역할 라우팅 | **턴 기반 응축**(8턴→최근 4턴 verbatim, 나머지 요약) + bounded tool results |
| **확장 모델** | TypeScript 확장(Skills·Themes·Extensions) | 하네스 내장(31 도구·14 LSP·28 DAP·8포맷 config import) | **MCP 네이티브** + Skills + Subagents (세 가지가 동등한 1급 시민) |
| **권한 모델** | **없음** (문서 명시: "does not include a built-in permission system" — 컨테이너화로 대체) | approvalMode(`always-ask`/`write`/`yolo` 기본값) + 도구별 `approval`(`allow`/`deny`/`prompt`) | **권한+샌드박스 분리**(ask/auto/yolo 모드) + **OS 샌드박스**(macOS) + 룰(allow/ask/deny) |

**중요**: fx는 Pi의 포크가 **아니다**. Pi 계열(원본↔omp)이 "하네스를 어디까지 튜닝하느냐"의 스펙트럼이라면, fx는 같은 코딩 에이전트 문제를 **전혀 다른 설계 축**에서 접근한다. 세 가지를 "선택지"로 놓고 비교할 때 기준이 되는 차원이 다르다 — Pi는 *미니멀리즘*, omp는 *edit/컨텍스트 기계화*, fx는 *거버넌스·추상화*가 각각 핵심 차별점이다.

---

## fx — "하네스는 안전망이자 추상화 계층"

fx의 핵심 주장은 문서에 명시적으로 드러나진 않지만, 설계 전체에서 읽힌다: **"모델은 교체 가능하고, 하네스는 권한·샌드박스·프로바이더 게이트웨이라는 인프라 층이다."** omp가 "하네스가 곧 제품"이라면, fx는 "하네스가 곧 정책(policy) 레이어"에 가깝다.

### 컨텍스트/토큰 관리 — 토큰 예산이 아니라 턴 구조

fx는 Pi/omp의 *토큰 임계치 기반 auto-compaction*을 쓰지 않는다. 대신 **구조적 턴 기반 응축**을 쓴다 ([Sessions 문서](https://fx.sh/docs/using-fx/sessions.md)):

- **8턴 완료 후** 최근 4턴은 verbatim 보존, 그 이전 턴은 "요청·결과·도구/파일 증거·백그라운드 작업·중단" 레코드로 응축.
- 이는 모델에 전달되는 컨텍스트만 바꾼다 — 저장된 transcript는 손상되지 않는다.
- `/compact`로 수동 트리거 가능하지만, 기본 메커니즘이 토큰 카운트가 아니라 **턴 경계**라는 점이 Pi/omp와 다르다.

**큰 도구 결과 처리**가 fx의 두 번째 토큰 전략이다 ([Tools 문서](https://fx.sh/docs/capabilities/tools.md)):

- 도구 결과가 곧바로 모델 응답에 들어가지 않는다 — bounded preview + retained byte count + 세션 스코프 handle.
- `read_tool_result`로 바이트 범위나 리터럴 쿼리로 뒷부분을 필요할 때만 가져온다.
- `max_tool_result_bytes`(기본 65536)로 한 결과당 보유 바이트 제어.
- → "한 명령/검색이 컨텍스트 창을 잡아먹는" 문제를 omp의 hashline(edit 출력 토큰)과는 **다른 지점**에서 해결한다.

### edit 도구 — str_replace 계열, 해시 앵커 없음

fx의 `edit_file`은 단일 정확 매치 `old_string`→`new_string` 치환이다. omp의 hashline(콘텐츠 해시 앵커로 줄 재타이핑 회피)와 대비된다.

- **장점**: 단순·투명. 모델이 바꿀 줄을 직접 제공하므로 의도가 명확.
- **비용**: omp가 지적한 `str_replace`의 근본 비용 — 모델이 변경 줄을 **재타이핑**해야 함 — 을 그대로 갖는다. 실패 시 재시도 루프가 토큰을 잡아먹을 수 있다.
- fx는 이 비용을 hashline으로 없애는 대신, **권한 게이트(편집 전 승인)**와 **bounded results**로 보완한다. 즉 edit 자체의 토큰 효율은 Pi와 같은 부류지만, "실패했을 때 폭발"을 정책 층에서 늦추는 구조.

### 거버넌스 — fx의 가장 큰 차별점

Pi는 권한 시스템이 **명시적으로 없다** — pi-mono README: "Pi does not include a built-in permission system for restricting filesystem, process, network, or credential access" — 컨테이너화(Gondolin·Docker·OpenShell)로 대체하라고 권한다. omp는 반대로 **approval 게이트가 있다** (`tools.approvalMode`: `always-ask`/`write`/`yolo`, 기본값 `yolo` + 도구별 `tools.approval` `allow`/`deny`/`prompt`). 하지만 omp에는 **OS 샌드박스가 없다** — 게이트가 "실행할까 말까"는 결정하지만 "허락된 명령이 무엇을 할 수 있는가"는 제한하지 않는다. fx는 이 둘을 **분리**한다: 권한(실행 여부)과 샌드박스(허용된 명령이 할 수 있는 일)를 별개 결정으로 취급한다 ([Permissions 문서](https://fx.sh/docs/configure-fx/permissions.md)):

| 축 | fx의 처리 |
|---|---|
| **권한 모드** | `ask`(미해결 민감 호출마다 승인) · `auto`(고정 모델 `openai/gpt-5.4`로 자동 검토, 추가 비용) · `yolo`(검사·샌드박스 전부 끔) |
| **룰** | 프로파일에 `allow`/`ask`/`deny` 저장 — 도구+타겟 매칭 |
| **샌드박스** | 권한과 **분리된 결정**. macOS `os` 샌드박스는 쓰기를 primary workspace·additional dirs·temp로 제한. 명령 승인과 샌드박스 확장은 별도 승인 |
| **읽기 도구** | `list/glob/grep/read_file`는 승인 불필요. `write/edit/delete/rename/copy/create_folder/run_command/open_file/install_skill/vision`는 승인 대상 |
| **경계 외 경로** | workspace 밖은 모든 파일 도구에 대해 정책 적용 |

이 층은 omp 벤치마크가 다루지 않는 차원이다 — "얼마나 토큰을 아끼는가"가 아니라 **"모델이 뭘 하도록 허락할 것인가"**. `auto` 모드의 자동 검토는 추가 모델 요청(비용)을 발생시키지만, 사람이 매번 승인하지 않아도 되는 타협점이다.

### 프로바이더 — 60+ SDK가 아니라 게이트웨이 1개

omp가 60+ 프로바이더 SDK를 직접 품고, Pi가 15+ 통합 API를 쓰는 것과 달리, fx는 **Vercel AI Gateway라는 단일 추상화** 뒤에 모든 모델을 둔다 ([Authentication 문서](https://fx.sh/docs/getting-started/authentication.md)):

- 게이트웨이가 노출하는 모델이면 즉시 사용 — SDK per provider가 아님.
- 인증은 Vercel 로그인 또는 게이트웨이 API 키. 팀 스코핑으로 모델 가용성이 팀마다 다를 수 있음.
- **공급망 리스크 관점**: omp의 60+ SDK 표면 vs fx의 게이트웨이 1개 — 표면은 좁지만 게이트웨이 가용성에 종속.
- 추가 모델 요청 2종(자동 권한 검토의 `gpt-5.4`, 비전 폴백의 `gemini-2.5-flash`)은 고정 모델이라 비용 예측 가능.

### 확장 — MCP가 1급 시민

Pi는 TypeScript 확장, omp는 하네스 내장 도구가 주축이다. fx는 **세 확장 축이 동등**하다:

- **MCP** — `2026-07-28` 스펙 풀 구현. 게으른 발견(`mcp_search_tools`→`mcp_select_tool`)으로 큰 카탈로그가 컨텍스트를 잡아먹지 않음. **repo-local MCP는 로드 안 함** — 클론만으로 서버 추가 불가(보안). 서브에이전트에 immutable·permission-filtered 뷰로 상속.
- **Skills** — 마크다운 정의 도구세트. 발견은 시작 시, 로드는 호출 시(컨텍스트 오염 방지). opencode·codex·claude·agents·claw 디렉토리까지 크로스 에이전트 발견.
- **Subagents** — 자식 fx 세션. one-off/persistent, 자체 모델·effort·권한·transcript. **부모-자식 메시지 큐가 durable** — 자식이 풀 transcript를 부모 컨텍스트에 복사 없이 작동. omp의 서브에이전트(isolated worktree 팬아웃)와 목적은 같지만 "스키마 검증된 객체 반환"보다는 **durable 메시지 큐 + inspect.wait** 모델.

### fx가 의도적으로 안 하는 것

- **LSP/DAP 없음** — omp의 14 LSP·28 DAP(IDE급 인텔리전스)에 대응하는 층이 없다. rename 전파·실제 디버거 구동은 불가.
- **hashline 없음** — edit 토큰 절약의 핵심 기법을 채택하지 않았다.
- **stream rules·advisor·역할 라우팅 없음** — omp의 "드리프트 캐치" 기계가 없다. 역할 라우팅 대신 서브에이전트에 모델을 따로 지정할 수는 있지만, 인텐트별 자동 라우팅은 아님.
- **snapcompact 없음** — 이미지 컨텍스트 압축 없음. 비전은 폴백 모델(`gemini-2.5-flash`)로 처리.
- **브라우저/CDP 없음** — 문서에 명시("fx does not currently include interactive browser or CDP tools").

---

## 3자 비교 — 컨텍스트/토큰 관리

| 축 | Pi (플러그인) | omp | fx |
|---|---|---|---|
| **compaction 트리거** | 토큰 임계치(`contextWindow - reserveTokens`) | 동일 계승 | **턴 수**(8턴 후 최근 4 verbatim) |
| **edit 토큰** | `str_replace` — 줄 재타이핑, 비용 높음 | hashline — 앵커만, 비용 낮음(최대 −61%) | `edit_file` — str_replace 계열, 비용 Pi와 동급 |
| **실패 재시도 루프** | 발생 → 토큰 소모 | 앵커 기반 거부로 루프 제거 | 발생 가능 — 권한 게이트가 실행 전 지연은 시켜도 토큰 절약은 아님 |
| **큰 도구 결과** | 컨텍스트에 직접 | 컨텍스트에 직접 | **bounded preview + handle**(`read_tool_result`) — 결과가 창을 잠식 안 함 |
| **컨텍스트 분산** | 없음 | 서브에이전트 + isolated worktrees | 서브에이전트(durable 큐, transcript 복사 없음) |
| **코스 코렉션** | 없음 | stream rules(컨텍스트 텍스 없음) | 없음 (대신 권한 `auto` 검토가 *실행* 차원에서 제어) |
| **드리프트 감지** | 없음 | advisor 모델(별도 컨텍스트) | 없음 |
| **비용 최적화** | 단일 모델 | 역할 라우팅(`smol`/`slow`) | 서브에이전트별 모델 지정 (자동 라우팅 아님) |
| **이미지 컨텍스트** | 원본 그대로 | snapcompact 압축 | 비전 폴백(`gemini-2.5-flash`) — 모델 비전 지원 시 네이티브 |
| **권한** | 없음 (컨테이너화 권장) | approvalMode(`always-ask`/`write`/`yolo`) + 도구별 approval | **권한+샌드박스 분리**(모드 + 룰) + **OS 샌드박스** |
| **프로바이더 표면** | 15+ 통합 API | 60+ SDK 직접 | 게이트웨이 1개 (모든 게이트웨이 모델) |
| **LSP/DAP** | 없음 | 14 LSP·28 DAP | 없음 |

**해석**: 세 harness는 토큰/컨텍스트 문제를 **각기 다른 지점**에서 잡는다.
- omp: **edit 출력 단**에서 토큰을 아끼고(hashline), 컨텍스트를 **분산**시키고(서브에이전트), **실시간 코스 코렉션**(stream rules)으로 드리프트를 잡는다. 가장 "토큰 엔지니어링"에 가깝다.
- fx: edit 자체는 Pi급이지만, **큰 결과를 창 밖으로 빼고**(bounded handle), 턴 구조로 응축하며, 무엇보다 **권한 게이트로 무엇이 실행될지 통제**한다. 토큰 절약이 아니라 **실행 통제**가 중심.
- Pi: 둘 다 없지만, 그래서 가장 투명하고 얇다. 모델이 좋으면 compaction 하나로 충분.

---

## 코딩 작업에서의 실질적 장단점 — fx 추가

### fx의 장점

- **거버넌스가 1급** — 권한 모드·룰·OS 샌드박스가 도구 실행 전에 작동. "모델이 `rm -rf`를 부르면?"에 대한 답이 하네스에 내장. Pi는 권한 시스템 자체가 없고(컨테이너화에 맡김), omp는 approval 게이트는 있지만 OS 샌드박스가 없어 "허락된 명령이 무슨 짓을 할지"는 통제 못 한다. fx만 이 둘을 분리해 둘 다 갖는다.
- **큰 결과 폭발 방지** — `max_tool_result_bytes` + `read_tool_result` handle. 한 번의 `grep`이나 `cat`이 컨텍스트를 잠식하지 않는다. omp의 hashline(edit 쪽)과 보완적이지 다른 축.
- **프로바이더 단일 통합** — 게이트웨이 하나로 모델 교체. 60+ SDK 의존성·공급망 표면 없음. 모델 추가가 게이트웨이 설정지고 SDK 설치가 아님.
- **MCP 네이티브 + repo-local MCP 거부** — 확장성과 보안을 동시에. 클론만으로 MCP 서버가 실행되는 일이 없다.
- **서브에이전트 durable 큐** — 자식이 풀 transcript를 부모에 복사 없이 작동. 부모 컨텍스트 폭발 없이 무거운 작업 위임.
- **네이티브 바이너리** — Zig 컴파일, Node 런타임 의존 없음. 시작 비용·메모리 풋프린트 이점.
- **ACP·WASM·headless** — `fx ask`(비대화), ACP 서버(에디터 통합), WebAssembly SDK(브라우저)로 동일 런타임을 여러 표면에서.

### fx의 단점

- **edit 토큰 비용** — `str_replace` 계열이므로 omp hashline의 "줄 재타이핑 회피" 이점이 없다. 모델-하네스 정합도가 안 맞으면 Pi와 같은 실패·재시도 루프 발생.
- **LSP/DAP 부재** — rename 전파·실제 디버거가 코딱에 필요하면 omp만의 영역. fx는 여기 경쟁하지 않는다.
- **게이트웨이 종속** — 프로바이더가 게이트웨이 뒤에 있으므로, 게이트웨이 가용성·비용 정책·팀 스코핑에 종속. 자체 로컬 프로바이더를 직접 붙이는 Pi/omp의 자유도와 다름.
- **자체 드리프트 캐치 없음** — stream rules·advisor가 없으므로, 모델이 빗나가면 사용자가 잡거나 재시도해야. `auto` 권한 검토는 *실행* 차원이지 *추론 드리프트* 차원이 아님.
- **폐쇄 소스** — Pi/omp는 오픈소스(소스 읽기·포크 가능). fx는 네이티브 바이너리 배포. 고장 원인 범위가 좁은 대신 소스 수준 검증 불가.
- **`auto` 검토 추가 비용** — 민감 호출마다 `gpt-5.4` 요청이 발생. 편의의 대가로 토큰 비용이 붙는다.

---

## 언제 뭘 고를까 — 3자 확장

| 상황 | 추천 | 이유 |
|---|---|---|
| 작은~중간 프로젝트, 익숙한 모델 하나로 충분 | **Pi + plugin** | 미니멀·투명. compaction으로 충분 |
| 컨텍스트를 최대한 아껴야 하는 큰 작업·장기 세션 | **omp** | hashline 토큰 절약 + 서브에이전트 분산 결정적 |
| 모델-하네스 정합도 의심·다양한 모델 시도 중 | **omp** | hashline이 모델 비의존적. str_replace 실패율에 덜 노출 |
| LSP rename·DAP 디버깅이 코딱에 필요 | **omp** | Pi·fx엔 없는 층 |
| **권한 통제·샌드박스가 최우선(신뢰 못 할 코드·多모델 환경)** | **fx** | 4단계 권한 + OS 샌드박스가 하네스에 내장. 유일 |
| **프로바이더를 게이트웨이로 단일화하고 싶음** | **fx** | SDK 60개 표면 없이 모든 게이트웨이 모델. 공급망 단순 |
| **MCP 확장이 주 확장 축** | **fx** | MCP가 1급·게으른 발견·repo-local 거부. Pi/omp보다 MCP 중심 |
| **에디터 통합(ACP)·헤드리스·WASM 동일 런타인 필요** | **fx** | ask/ACP/WASM 세 표면이 동일 런타임 |
| 최소 의존성·공급망 회피·오픈소스 검증 | **Pi + plugin** | fx는 폐쇄, omp는 60+ SDK 표면 |
| 소스 읽고 고장 좁은 범위에서 잡고 싶음 | **Pi + plugin** | 4 도구 + 얇은 확장. fx는 바이너리, omp는 80k Rust |
| 마이그레이션 비용 최소(Cursor/Cline/Codex 설정 유지) | **omp** | 8포맷 config import. fx는 자체 포맷 |
| 비용 최적화(싼 모델 서브에이전트·인텐트 라우팅) | **omp** | 역할 라우팅(`smol`/`slow`). fx는 서브에이전트별 모델 지정만 |

---

## 주의사항

- **fx는 독립 harness다.** Pi 포크가 아니므로 "Pi 계열 스펙트럼의 한 끝"이 아니라 별개 설계축. 기존 [[pi-vs-oh-my-pi]]의 "같은 뿌리" 프레임은 Pi↔omp에만 해당.
- omp의 벤치마크 수치(10배 등)는 **전부 프로젝트 자체 발행**이고 독립 재현이 없다 — fx는 동종의 벤치마크를 발행하지 않으므로, fx vs omp의 edit 성능은 **정성 비교**일 뿐이다.
- fx의 `auto` 권한 검토와 비전 폴백은 **고정 모델**(`gpt-5.4`·`gemini-2.5-flash`)을 쓴다 — 사용자 모델과 무관하게 추가 비용이 발생.
- fx 프로바이더는 AI Gateway 뒤에 있으므로, **게이트웨이가 안 지원하는 모델/로컬 엔드포인트**는 loopback 호환 엔드포인트가 있는 경우에만 가능 (문서상 "fully hermetic setup" 옵션).
- 세 harness 모두 **edit 실패→재시도 루프**의 근본 비용을 다루는 방식이 다르다: omp는 루프 자체 제거(hashline), fx는 실행 전 게이트(권한)로 지연·통제, Pi는 모델 튜닝에 맡김.

---

## 출처

### fx
- [fx.sh — 전체 문서(llms-full.txt)](https://fx.sh/llms-full.txt) — 본 페이지의 fx 설명 전체 근거
- [fx — Tools](https://fx.sh/docs/capabilities/tools.md) (built-in 도구 목록·bounded tool results·`read_tool_result`)
- [fx — Permissions](https://fx.sh/docs/configure-fx/permissions.md) (4단계 모드·룰·샌드박스·`auto` 검토)
- [fx — Sessions](https://fx.sh/docs/using-fx/sessions.md) (턴 기반 응축·`/compact`)
- [fx — Subagents](https://fx.sh/docs/capabilities/subagents.md) (one-off/persistent·durable 큐·6 branches)
- [fx — MCP](https://fx.sh/docs/capabilities/mcp.md) + [MCP protocol reference](https://fx.sh/docs/capabilities/mcp/protocol.md) (게으른 발견·repo-local 거부·2026-07-28)
- [fx — Authentication](https://fx.sh/docs/getting-started/authentication.md) (AI Gateway·Vercel 로그인·API 키)
- [fx — Skills](https://fx.sh/docs/capabilities/skills.md) (발견 vs 로드 분리·크로스 에이전트 루트)
- [fx — Configuration](https://fx.sh/docs/configure-fx/configuration.md) (`~/.fx/settings.json`·`.fx.json`·context limits)

### Pi · omp (기존 페이지에서 계승)
- [can1357/oh-my-pi — GitHub](https://github.com/can1357/oh-my-pi) (포크 관계·60+ 프로바이더·31 도구·14 LSP·28 DAP·~80k Rust)
- [oh-my-pi main README](https://raw.githubusercontent.com/can1357/oh-my-pi/main/README.md) (hashline·서브에이전트·stream rules·advisor·역할 라우팅·벤치마크)
- [Can Bölük — I Improved 15 LLMs at Coding in One Afternoon (blog.can.ac, 2026-02-12)](https://blog.can.ac/2026/02/12/the-harness-problem/)
- [badlogic/pi-mono — GitHub](https://github.com/badlogic/pi-mono) (원본 Pi, 4개 도구·확장 모델)
- [Mario Zechner — What I learned building an opinionated and minimal coding agent](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)
- [pi.dev — Compaction 문서](https://pi.dev/docs/latest/compaction)

---

## 관련

- [[pi-vs-oh-my-pi]] — 본 페이지의 2자 원본. Pi↔omp 비교의 상세(벤치마크·hashline 역학·철학)는 이쪽에. fx는 그 비교에 "거버넌스·게이트웨이 추상화" 축을 추가한 확장.
