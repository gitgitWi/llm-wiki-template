---
title: TanStack AI
type: entity
visibility: public
domains: [dev, ai]
tags: [tanstack-ai, ag-ui, connection-adapter, streaming, typescript, llm-sdk]
status: living
created: 2026-08-20
updated: 2026-08-21
description: TanStack AI 팩트 시트 — 프로바이더 무관 TypeScript LLM SDK, connection adapter 로 전송을 분리한 구조, delivery-durability 심(seam), 0.46.0 WebSocket 전송.
read_when: TanStack AI 의 전송 계층이나 재개 가능 스트림 구조를 확인할 때, 또는 SDK 후보를 비교할 때.
agent: claude-opus-5 / claude-code
related: ["[[websocket-full-duplex-tanstack-ai]]", "[[full-duplex-transport]]", "[[2026-08-20-tan-stack]]", "[[agentic-coding-design-and-code-review]]"]
---

# TanStack AI

프로바이더 무관 TypeScript LLM SDK. 스트리밍 채팅, 도구 호출, 에이전트, 멀티모달을 다룬다. TanStack 계열이라 React·Vue·Svelte·Solid·Angular·Preact 각각의 `useChat` 바인딩이 있다.

| 항목 | 값 (2026-08-20 확인) |
|---|---|
| 저장소 | `github.com/TanStack/ai` |
| 핵심 패키지 | `@tanstack/ai` `0.47.0` |
| 라이선스 | MIT |
| 작성자 | Tanner Linsley |
| 프레임워크 패키지 | `ai-react` `ai-vue` `ai-svelte` `ai-solid` `ai-angular` `ai-preact` `ai-client` |

---

## 1. 구조의 핵심 — 전송을 한 군데로 몰아 넣었다

이 SDK 의 설계 결정 하나가 나머지를 설명한다: **네트워크를 만지는 건 connection adapter 하나뿐이다.** 청크 처리, 메시지 재조립, 도구 호출, UI 갱신은 전부 전송에 무관하다.

모든 어댑터가 같은 `StreamChunk` 이벤트를 낸다. 이 이벤트 규격은 **AG-UI 프로토콜**을 따른다 (`RUN_STARTED` `TEXT_MESSAGE_CONTENT` `TOOL_CALL_*` `RUN_FINISHED` `RUN_ERROR`).

어댑터 목록:

| 어댑터 | 전송 | 성격 |
|---|---|---|
| `fetchServerSentEvents` | SSE | 기본값 |
| `fetchHttpStream` | NDJSON | SSE 가 막힌 환경 |
| `xhrServerSentEvents` / `xhrHttpStream` | XHR | React Native·Expo |
| `stream` / `fetcher` | 인프로세스 async iterable, 서버 함수 | 네트워크 없음 |
| `rpcStream` | Cap'n Web·gRPC-Web·tRPC | RPC |
| `webSocket` | WebSocket | 0.46.0 신규. 대화 단위 지속 소켓 |

앞의 다섯은 **요청 스코프**다. 어댑터가 `connect()` 로 요청 1건 = 스트림 1건을 만든다.
`webSocket` 만 **지속 채널**이다. `subscribe()` / `send()` 로 나뉘어 있다. 이 타입 차이가 곧 full-duplex 의 코드 수준 표현이다 — [[websocket-full-duplex-tanstack-ai]] §3 참조.

## 2. delivery-durability 심 — 재개의 근거

재개(resume)는 전송 기능이 아니라 **별도 심(seam)** 이다. `StreamDurability` 인터페이스 하나로 추상화된다:

- `append(chunks)` — 배달 전에 저장하고, 청크마다 offset 을 정확히 1개씩 같은 순서로 돌려준다
- `read(offset)` — 그 offset **이후만** 재생한다
- `resumeFrom()` — 요청에서 뽑은 offset 또는 `null`
- `snapshot()` — 기다리지 않고 현재까지 저장된 것을 반환
- `close()` — 로그를 종결 상태로 만든다

**offset 은 어댑터 소유의 불투명 토큰이다.** 전송 계층도, 클라이언트도 파싱하지 않는다. 그래서 SSE 는 이 토큰을 `id:` 줄에, NDJSON 은 `{ id, chunk }` 봉투에, WebSocket 은 같은 봉투를 프레임으로 실어 보낸다 — **전송 3종이 재개 로직을 공유하는 이유가 이 한 겹이다.**

내장 구현은 `memoryStream(request)` 과 `durableStream` 이다. 둘 다 요청 URL 의 `?runId` / `?offset` 을 읽어 키를 잡는다.

`durability` 를 넘기지 않으면 offset 이 없다. 그러면 동작은 평범한 단발 fetch 와 같고, 끊기면 재개할 근거가 없다.

## 3. 관측한 코드 특성

소스를 읽으면 주석 밀도가 비정상적으로 높다. 그리고 그 주석이 대부분 **"왜 이 방어가 필요한가"** 를 적고 있다 — TOCTOU, 은퇴한 소켓, 등록 전에 도착한 abort, 버퍼가 남은 채로 온 close. 실패 사례를 주석으로 고정해 둔 형태다.

이건 [[agentic-coding-design-and-code-review]] 가 말하는 "사라진 의도(Vanished Intent)" 문제에 대한 하나의 실물 답변으로 읽을 수 있다. 판단은 §참고로만 남긴다 — 이 저장소에 그 코드가 사람 손인지 에이전트 손인지 확인할 근거는 없다.
