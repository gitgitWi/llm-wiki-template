---
title: WebSocket full-duplex — TanStack AI 구현으로 읽기
type: synthesis
visibility: public
domains: [dev, ai]
tags: [websocket, full-duplex, resumable-stream, tanstack-ai, sse, stream-durability]
status: living
created: 2026-08-20
updated: 2026-08-21
description: TanStack AI 의 WebSocket 전송 발표에서 말한 full-duplex 가 정확히 무엇인지, SSE·NDJSON 과 무엇이 다른지, 그리고 소켓을 직접 열어 쓰는 것과 이 구현의 차이를 실제 소스 코드로 확인한다.
read_when: LLM 채팅에 WebSocket 을 쓸지 판단할 때, 또는 "WebSocket 그냥 쓰면 되지" 라는 결론을 검증할 때.
agent: claude-opus-5 / claude-code
related: ["[[full-duplex-transport]]", "[[tanstack-ai]]", "[[2026-08-20-tan-stack]]"]
---

# WebSocket full-duplex — TanStack AI 구현으로 읽기

> 2026-08-20 작성. 근거는 [[2026-08-20-tan-stack]] 원문(42단어)과 `TanStack/ai` `0.47.0` 소스다.
> 결론부터: **원문의 네 주장은 모두 코드로 확인된다.** 다만 "full-duplex" 가 주는 실익은 흔히 상상하는 것과 다르다. 그리고 **"WebSocket 을 그냥 쓰는 것" 과의 차이는 프로토콜이 아니라 전부 실패 처리에 있다.**

---

## 0. 원문이 실제로 말한 것

원문은 트윗 한 건이다. 주장은 네 개뿐이다.

1. WebSocket 전송이 TanStack AI 에 들어갔다
2. **대화 전체에 소켓 하나** (one socket for the whole conversation)
3. **Full-duplex**
4. 스트리밍 중 끊기면 클라이언트가 **마지막 offset 에서 다시 열고 빈 구간만 재생한다. 모델을 두 번 호출하지 않는다**
5. Node(`ws`) 와 Cloudflare(`toWebSocketResponse`) 에서 동작한다

트윗에는 근거가 없다. 아래는 전부 소스에서 확인한 내용이다.

---

## 1. 여기서 full-duplex 는 무슨 뜻인가

용어 정의와 전송 방식별 비교표는 [[full-duplex-transport]] 에 따로 정리했다. 요약만 옮기면:

- **simplex** — 한 방향. SSE 가 이것이다.
- **half-duplex** — 양방향이지만 교대. HTTP 요청/응답이 이것이다.
- **full-duplex** — 양방향 동시, 서로 독립. WebSocket 이 이것이다.

중요한 단서 하나: **TCP 는 원래 full-duplex 다.** 그래서 "SSE 는 full-duplex 가 아니다" 는 전송 계층에 대한 말이 아니라 **응용 프로토콜 규칙**에 대한 말이다. SSE 로도 물리적으로는 상향 전송이 가능하지만, `EventSource` 라는 API 가 그것을 허용하지 않는다.

### LLM 채팅에서 이 차이가 실제로 걸리는 지점

기존 방식(SSE·NDJSON)은 **턴 하나 = 연결 하나**다. 사용자가 메시지를 보내면 POST 를 하나 열고, 응답 본문으로 청크를 받고, `RUN_FINISHED` 가 오면 연결이 끝난다. 다음 메시지는 새 연결이다.

이 구조에서 불편한 것은 하나뿐이다. **스트리밍이 진행되는 동안 서버에 뭔가 말할 방법이 없다.** 응답 본문을 읽는 중이고, 그 요청의 본문은 이미 다 보냈다.

가장 아픈 사례가 **취소**다. 사용자가 정지를 누르면, SSE 에서는 클라이언트가 읽기를 멈출 뿐이다. 서버는 계속 생성한다. 계속 과금된다. 진짜로 멈추려면 별도 HTTP 요청을 열고, 그 요청이 어느 run 을 가리키는지 상관관계를 직접 맞춰야 한다.

full-duplex 소켓에서는 그냥 위로 프레임 하나를 보낸다. 하향 청크가 흐르는 **동시에**.

---

## 2. 이 구현이 full-duplex 를 실제로 쓰는 곳 — 세 군데뿐

여기가 이 페이지에서 가장 실용적인 부분이다. 자랑 문구가 아니라 코드가 근거다.

### (1) 스트리밍 중 상향 제어 프레임 — abort

서버는 진행 중인 턴을 `runId` 로 색인해 들고 있다. `packages/ai/src/stream-to-websocket.ts`:

```ts
const activeTurns = new Map<string, AbortController>()
```

abort 프레임이 오면 **그 턴만** 중단한다. 소켓은 살아 있다.

```ts
if (frame.kind === 'abort') {
  const turn = activeTurns.get(frame.runId)
  if (turn) turn.abort()
  else earlyAborts.add(frame.runId)   // 등록보다 먼저 온 abort
  return
}
```

클라이언트 쪽(`packages/ai-client/src/connection-adapters.ts`)에서 `useChat` 의 `stop()` 이 이 프레임을 보낸다. 코드 주석이 이유를 직접 적어 두었다 — 소켓이 턴보다 오래 살기 때문에, abort 프레임이 없으면 모델이 계속 생성하고 계속 과금된다.

### (2) 한 소켓에 여러 run 동시 진행

`activeTurns` 가 `Map` 이라는 사실 자체가 설계 의도다. **같은 소켓에서 턴 N 개가 동시에 흐를 수 있다.** 요청 스코프 전송으로는 연결 N 개가 필요한 일이다.

### (3) 턴 사이에 핸드셰이크가 없다

소켓은 `RUN_FINISHED` 뒤에도 열려 있다. 클라이언트가 닫거나, idle 타임아웃이 걸리거나, 프로세스가 죽을 때까지. 도구 호출 재제출과 다음 사용자 메시지가 같은 소켓을 탄다.

### 반대로, 쓰지 **않는** 것 — 서버 주도 push

여기가 원문을 균형 있게 읽어야 하는 지점이다. 공식 문서가 스스로 선을 긋는다:

> 이 페이지는 요청/응답 경우만 다룬다. 서버가 먼저 보내는 push 는 그 위에 직접 프레이밍을 얹어야 한다.
> — `docs/resumable-streams/websockets.md`

즉 **내장 프로토콜은 여전히 요청/응답 모양이다.** full-duplex 능력은 위 세 가지(취소·다중 턴·핸드셰이크 절약)에 쓰이고, presence 나 브로드캐스트 같은 진짜 서버 주도 push 는 사용자가 직접 만들어야 한다. "full-duplex 니까 아무 때나 서버가 밀어 준다" 는 이 구현에 대한 설명이 아니다.

---

## 3. 클라이언트 타입이 full-duplex 를 드러낸다

전송 방식의 차이가 API 모양에 그대로 나온다. 이게 이 SDK 에서 가장 깔끔한 부분이다.

요청 스코프 어댑터는 `connect()` 하나다 — 요청 1건이 스트림 1건을 돌려준다.

지속 채널 어댑터는 **둘로 갈라진다** (`SubscribeConnectionAdapter`):

```ts
subscribe(abortSignal?): AsyncIterable<StreamChunk>              // 한 번만 호출. 오래 산다
send(messages, data?, abortSignal?, runContext?): Promise<void>   // 사용자 메시지마다 1회
```

`send()` 는 **프레임을 썼으면 곧바로 반환한다.** 청크는 그 반환값이 아니라 `subscribe()` 로 따로 온다.

**보내기와 받기가 타입 수준에서 분리된 것 — 이게 full-duplex 의 정의 그대로다.** 요청/응답 모델에서는 둘이 하나의 값으로 묶여 있어서 이렇게 쓸 수 없다. 공식 문서도 `stream()`/`connect()` 로는 지속 채널을 깔끔히 표현할 수 없다고 적는다. "요청마다 async iterable 하나" 를 전제하기 때문이다.

그러면 어느 청크가 어느 run 인지는 어떻게 아는가. 런타임이 상관관계를 맞춘다: `send()` 이후 다음 종료 이벤트(`RUN_FINISHED`/`RUN_ERROR`)까지 구독 큐에 올라온 청크를 그 run 에 귀속시킨다.

---

## 4. "빈 구간만 재생, 모델 재호출 없음" 은 어떻게 성립하는가

트윗의 네 번째 주장이 가장 중요한 부분이고, **full-duplex 와는 별개 기능**이다. 이걸 헷갈리면 안 된다.

재개는 전송에 붙은 기능이 아니라 **`StreamDurability` 라는 별도 심(seam)** 이다 ([[tanstack-ai]] §2). 계약은 두 줄로 요약된다:

- `append(chunks)` — 배달 **전에** 저장하고, 청크마다 offset 을 정확히 1개씩 같은 순서로 반환
- `read(offset)` — 그 offset **이후만** 재생

핵심은 **저장이 배달보다 먼저**라는 순서다. 클라이언트가 받은 모든 청크는 이미 로그에 있다. 그래서 클라이언트가 "여기까지 받았다" 고 말하면 서버는 그 뒤만 보내면 된다. 모델은 관여하지 않는다.

### 서버: 재개 경로에 모델이 아예 없다

`resumeWebSocketStream` 은 로그만 읽는다. 프로듀서 자리에 **빈 async generator** 를 넣는다. 소스 주석이 그 이유를 적어 둔다 — 재개는 전부 로그에서 나오므로 반복할 프로듀서가 없다.

```ts
function emptyDurableSource(): AsyncIterable<StreamChunk> {
  return (async function* () {})()
}
```

재개할 offset 이 없으면 `1008` 로 닫는다. 재생할 게 없기 때문이다.

라우팅 규칙도 단순하다. **URL 에 `?offset=` 이 있으면 재개, 없으면 새 턴.** `ws` 예제의 분기가 그 두 줄이다.

### 왜 offset 이 헤더가 아니라 URL 에 실리는가

이 부분이 SSE 와 갈리는 실질적 차이다.

SSE·NDJSON 은 `Last-Event-ID` **헤더**로 재개한다. `fetch`/XHR 는 요청을 열기 전에 아무 헤더나 넣을 수 있다.

브라우저의 `WebSocket` 생성자는 **핸드셰이크에 커스텀 헤더를 넣을 수 없다.** 그래서 offset 이 URL 로 내려간다: `?runId=<id>&offset=<lastId>`.

같은 보장, 다른 운반 수단이다. 그리고 이건 브라우저 API 의 제약이지 프로토콜의 선택이 아니다.

### 클라이언트: 재연결을 언제 하고 언제 포기하는가

`webSocket()` 어댑터의 판단 순서가 명확하다. 소켓이 닫힐 때:

| 상태 | 처리 |
|---|---|
| 더 새 연결에 밀려 은퇴한 소켓 | 무시. 끊김이 아니다 |
| run 세션이 없음 | 실패를 올린다. 죽은 소켓에 구독자를 세워 두지 않는다 |
| abort 됐거나 종료 청크를 이미 봤음 | 정상 종료. 아무것도 안 한다 |
| **offset 을 한 번도 못 봤음 (비재개 run)** | **하드 실패.** 재개할 근거가 없다 |
| 그 외 | offset 에서 재연결 |

네 번째 줄이 중요하다. **서버가 `durability` 를 안 걸었으면 재연결을 시도하지 않는다.** offset 을 절대 붙이지 않는 서버를 상대로 영원히 재연결하는 대신 실패를 드러낸다.

중복 제거와 재연결 상한은 `createReconnectTracker` 하나에 모여 있고, **SSE 경로와 같은 코드를 쓴다.** 상한 규칙이 미묘하다:

> 진전 없는 **연속** 재연결만 센다. 진전이 있으면 카운터가 0으로 돌아간다.

그래서 이벤트마다 소켓을 끊는 프록시 뒤의 정상적인 장기 run 은 상한에 닿지 않고, 진짜로 막힌 run(재연결해도 새 게 안 옴)만 실패한다. 기본값은 5회, 250ms 간격이다.

---

## 5. 그래서 "WebSocket 을 그냥 쓰는 것" 과 무엇이 다른가

프로토콜은 같다. RFC 6455 그대로다. 차이는 **전부 실패 처리**다. 아래는 직접 구현하면 하나하나 다시 만나는 것들이고, 전부 소스에 방어 코드와 그 이유가 남아 있다.

| # | 직접 구현하면 놓치는 것 | 놓치면 생기는 일 |
|---|---|---|
| 1 | offset 봉투 + 재개 | 끊기면 턴을 처음부터 다시 돈다 = **모델 두 번 호출, 두 번 과금** |
| 2 | abort 프레임 | 정지를 눌러도 서버가 끝까지 생성하고 과금한다 |
| 3 | heartbeat | 유휴 소켓을 끊는 프록시 뒤에서 조용히 죽는다 |
| 4 | 스트리밍 중에는 idle 타임아웃 금지 | 5분 넘는 에이전트 루프가 살아 있는데 잘린다 |
| 5 | 대화 소켓과 재개 소켓 분리 | 열린 소켓을 재사용하면 `?offset` 이 버려져 **재생 요청이 서버에 도달하지 않는다** |
| 6 | 은퇴한 소켓의 핸들러 무시 | 소켓 둘이 같은 리스너에 청크를 밀어 넣는다 |
| 7 | 등록 전에 도착한 abort 보관 | 본문 검증을 `await` 하는 창에 들어온 abort 가 조용히 사라진다 |
| 8 | 같은 `runId` 재제출 시 이전 턴 중단 | 이전 컨트롤러가 덮여서 close·abort 가 그 턴에 닿지 못한다 |
| 9 | 정리 시 소유권 확인 (TOCTOU) | **오래된** 턴의 정리가 **새** 턴의 살아 있는 컨트롤러를 지운다 |
| 10 | close 전에 버퍼 비우기 | 같은 macrotask 에 몰려온 청크 + close 에서 **마지막 `RUN_FINISHED` 를 잃고 영구 hang** |
| 11 | 턴 실패를 `RUN_ERROR` 프레임으로 통보 | 소켓이 대화 스코프라 안 닫힌다. 종료 청크도 close 도 없다 = **영구 hang** |
| 12 | `error` 이벤트 리스너 | `ws`(EventEmitter) 에서 리스너 없는 `error` 는 **uncaught exception** 이다. 타이머와 턴도 누수된다 |
| 13 | 소켓별 open promise 메모이제이션 | 핸드셰이크 중 두 번째 `send()` 가 첫 번째의 핸들러를 덮어 **영구 pending** |
| 14 | 재연결 상한 + 중복 제거 | 펄럭이는 서버를 상대로 무한 재연결, 또는 경계 청크 중복 |
| 15 | 턴별 durability 팩토리 | 대화 소켓은 턴이 여러 개다. 로그를 하나로 잡으면 턴이 서로 섞인다 |
| 16 | 재개 핸드셰이크에서 `offset` 제거 | 잘못 라우팅된 재개가 새 턴의 durability 를 **조용히 재생 분기로 보낸다** |

여섯 개 항목(1·2·5·10·11·13)이 **사용자에게 보이는 hang 이나 중복 과금**으로 직결된다. 나머지는 조용한 누수다.

### 판단

- **소켓 하나 열고 JSON 주고받는 프로토타입** — 직접 쓰면 된다. 위 목록은 전부 실패 경로다. 성공 경로만 필요하면 30줄이면 된다.
- **프로덕션 LLM 채팅** — 직접 쓰지 않는 게 낫다. 위 16개 중 절반은 재현이 어렵고(경합·타임아웃·프록시), 증상이 "가끔 멈춘다" 로 나온다. 디버깅 비용이 구현 비용보다 크다.

프로토콜 지식이 아니라 **누가 이 16개를 이미 밟았는지**가 차이다.

---

## 6. 팩트체크

| # | 원문 주장 | 판정 | 근거 |
|---|---|---|---|
| 1 | WebSocket 전송이 들어갔다 | **맞음** | `@tanstack/ai` 0.46.0, PR #969. 현재 0.47.0 |
| 2 | 대화 전체에 소켓 하나 | **맞음** | 소켓이 `RUN_FINISHED` 뒤에도 열려 있다. `activeTurns` 가 턴을 다중화한다 |
| 3 | Full-duplex | **맞음, 단 범위 주의** | abort 프레임·동시 턴은 실재. **서버 주도 push 는 미포함** (§2) |
| 4 | 끊기면 마지막 offset 에서 빈 구간만 재생 | **맞음** | `resumeWebSocketStream` + `?offset=` 라우팅 |
| 5 | 모델을 두 번 호출하지 않는다 | **맞음** | 재개 경로의 프로듀서가 빈 generator 다 |
| 6 | Node(`ws`) 와 Cloudflare 동작 | **맞음** | `ws` 소켓이 `WebSocketLike` 를 구조적으로 만족. Cloudflare 는 `WebSocketPair` |
| 7 | (파생 오해) full-duplex 라서 SSE 보다 빠르다 | **근거 없음** | 소스·문서 어디에도 지연이나 처리량 주장이 없다 |
| 8 | (파생 오해) WebSocket 이 SSE 를 대체한다 | **아니다** | 공식 문서의 기본값은 여전히 SSE. WebSocket 은 세 번째 선택지 |

### 5번에 붙는 단서

"모델 재호출 없음" 은 **`durability` 를 걸었을 때만** 성립한다. 안 걸면 offset 이 없고, 끊김은 재개 대신 하드 실패가 된다. 트윗에는 이 전제가 없다.

---

## 7. 그래서 언제 쓰나

공식 문서의 기준이 그대로 쓸 만하다. 아래 중 하나라도 참이면 지속 채널:

1. 연결 하나가 run 여러 개를 다중화한다
2. 서버가 요청 밖에서 청크를 보낸다 (presence, 브로드캐스트, 서버 주도 도구 호출)
3. 여러 탭이나 워커가 연결 하나를 공유한다 (`BroadcastChannel`)

셋 다 아니면 SSE 다. 문서가 이유를 직접 적는다 — 더 단순하고, 연결 수명을 관리할 코드가 없다.

여기에 하나 더 붙이면: **취소를 정확히 하고 싶고 별도 취소 엔드포인트를 만들기 싫으면** WebSocket 이 이득이 있다. 이게 §2 (1)에서 확인한, full-duplex 의 가장 현실적인 실익이다.

---

## 8. 확인하지 못한 것

- **성능 수치가 없다.** SSE 대비 지연·처리량·연결당 메모리를 비교한 자료를 찾지 못했다. 트윗도 성능을 주장하지 않는다.
- **`durableStream` 의 백엔드별 특성**을 읽지 않았다. 실제 프로덕션 재개는 `memoryStream` 이 아니라 이쪽에 달려 있다.
- **인터럽트(0.47.0 `defineInterrupt`)와 WebSocket 의 상호작용**을 확인하지 않았다. 사용자 개입이 full-duplex 의 네 번째 용도가 될 수 있는데, 근거가 없어 남겨 둔다.
- **WebTransport 로 넘어갈 이득**을 판단하지 않았다. 2026-03 에 Baseline 이 됐으므로([[full-duplex-transport]] §4) 검토할 이유는 있지만, 이 SDK 에 어댑터는 없다.

---

## 참고

- 원문: [[2026-08-20-tan-stack]]
- `TanStack/ai` (MIT, Tanner Linsley) — 아래 코드 인용은 전부 이 저장소 `0.47.0` 에서 가져온 짧은 발췌다
- `TanStack/ai` `packages/ai/src/stream-to-websocket.ts` — 서버 코어
- `TanStack/ai` `packages/ai-client/src/connection-adapters.ts` — `webSocket()`, `createReconnectTracker`
- `TanStack/ai` `packages/ai/src/stream-durability.ts` — `StreamDurability` 계약
- `TanStack/ai` `docs/resumable-streams/websockets.md`, `docs/chat/connection-adapters.md`
- 개념 정리: [[full-duplex-transport]] · 라이브러리 팩트: [[tanstack-ai]]
