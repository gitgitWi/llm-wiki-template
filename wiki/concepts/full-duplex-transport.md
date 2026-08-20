---
title: Full-duplex 전송 — simplex·half·full 과 웹 전송 방식 비교
type: concept
visibility: public
domains: [dev]
tags: [full-duplex, websocket, sse, webtransport, http-streaming, transport-protocol]
status: living
created: 2026-08-20
updated: 2026-08-21
description: simplex·half-duplex·full-duplex 의 정의, 어느 계층의 성질인지, 그리고 SSE·HTTP 스트리밍·fetch 업로드 스트리밍·WebSocket·WebTransport·gRPC 의 방향성 비교.
read_when: "실시간 채널을 고를 때, 또는 \"SSE 는 왜 full-duplex 가 아닌가\" 를 정확히 답해야 할 때."
agent: claude-opus-5 / claude-code
related: ["[[websocket-full-duplex-tanstack-ai]]", "[[tanstack-ai]]"]
---

# Full-duplex 전송

용어 자체는 통신 공학에서 왔다. 채널 하나에서 **데이터가 몇 방향으로, 동시에 흐를 수 있는지**를 가리킨다.

| 용어 | 뜻 | 비유 |
|---|---|---|
| **simplex** | 한 방향으로만 흐른다 | 라디오 방송 |
| **half-duplex** | 양방향이지만 한 번에 한 방향 | 무전기 — 말할 때는 못 듣는다 |
| **full-duplex** | 양방향이 동시에, 서로 독립적으로 | 전화 통화 |

---

## 1. 먼저 계층을 고정한다 — 여기서 실수가 나온다

TCP 는 그 자체로 full-duplex 다. 연결 하나에 송신 스트림과 수신 스트림이 따로 있다.

그래서 **"SSE 는 full-duplex 가 아니다" 는 TCP 에 대한 말이 아니다.** 응용 프로토콜에 대한 말이다. TCP 가 양방향을 허용해도, 그 위에 올린 프로토콜이 "클라이언트는 요청을 다 보낸 뒤에만 응답을 받는다" 라고 규정하면 응용 계층은 half-duplex 다.

정리하면:

- **물리·전송 계층** — 이더넷과 TCP 는 오래전부터 full-duplex
- **응용 계층** — 프로토콜이 규정한 대화 규칙. 실무에서 논쟁이 되는 건 항상 이쪽

이 페이지의 표는 전부 응용 계층 기준이다.

---

## 2. 웹 전송 방식 비교

| 방식 | 응용 계층 방향성 | 연결 수명 | 스트리밍 중 상향 채널 | 브라우저 |
|---|---|---|---|---|
| HTTP/1.1 요청/응답 | half-duplex (교대) | 요청 1건 | 요청 본문뿐 (스트림 전에 확정) | 전부 |
| Long polling | 교대를 반복해 모방 | 요청 1건(대기) | 다음 요청에서만 | 전부 |
| **SSE** (`EventSource`) | **simplex** — 서버→클라 | 응답 1건 | **없음.** 별도 HTTP 요청이 필요하다 | 전부 |
| HTTP 청크 스트리밍 (NDJSON) | simplex 하향 | 응답 1건 | 없음 | 전부 |
| `fetch` 업로드 스트리밍 | **half-duplex 로 명시** | 요청 1건 | 요청 본문 스트림 | 제약 큼 (§3) |
| **WebSocket** (RFC 6455) | **full-duplex** | 임의 — 대화 전체 가능 | **같은 소켓** | 전부 |
| **WebTransport** (HTTP/3) | full-duplex + 다중 스트림 + datagram | 세션 | 같은 세션 | 2026-03 Baseline (§4) |
| gRPC bidi streaming (HTTP/2) | full-duplex | 호출 1건 | 같은 호출 | **브라우저 직접 불가** (§5) |

---

## 3. `fetch` 업로드 스트리밍은 full-duplex 가 아니다

요청 본문에 `ReadableStream` 을 넣는 기능이 있다. 이름만 보면 양방향 스트리밍처럼 보인다. 아니다.

- 호출할 때 `duplex: 'half'` 를 **명시해야 한다**. 스펙이 half-duplex 임을 이름으로 박아 두었다.
- Chrome 문서는 명확하다: 서버가 응답을 더 일찍 보내도, **요청 본문을 다 보내기 전에는 응답을 읽을 수 없다.**
- HTTP/2 이상이 필요하다. HTTP/1.x 면 `fetch` 가 거부한다.
- `Content-Length` 가 없으므로 CORS preflight 가 강제된다. `no-cors` 스트리밍은 금지다.
- 리다이렉트가 거의 막힌다 (303 만 허용).

그래서 Chrome 문서가 권하는 우회책이 곧 이 방식의 한계다: **요청용 스트림과 응답용 스트림을 별도 요청 2개로 열고, URL 파라미터 같은 식별자로 둘을 묶어라.** 채널 하나로 양방향을 하는 게 아니다.

## 4. WebTransport

HTTP/3(QUIC) 기반이다. 세션 하나에 **여러 개의 양방향 스트림**과 순서·재전송을 보장하지 않는 **datagram** 을 함께 얹는다. WebSocket 이 못 하는 두 가지를 준다: 스트림 간 head-of-line blocking 회피, 그리고 신뢰성을 포기해도 되는 경로.

2026-03 Safari 26.4 가 지원을 넣으면서 Baseline 에 들어왔다. 즉 2026-08 기준으로는 "쓸 수 있다" 가 맞다. 다만 서버·프록시·사내 인프라의 HTTP/3 지원은 별개 문제다.

## 5. gRPC 양방향 스트리밍

HTTP/2 위에서 진짜 full-duplex 다. 단 **브라우저에서 직접 못 쓴다.** 브라우저용인 gRPC-Web 은 양방향 스트리밍과 클라이언트 스트리밍을 지원하지 않는다. 브라우저에서 gRPC 로 full-duplex 를 하려면 프록시나 다른 전송으로 갈아타야 한다.

---

## 6. 그래서 언제 full-duplex 가 실제로 필요한가

방향성 자체가 목적인 경우는 드물다. 아래 중 하나가 참일 때 이득이 있다:

1. **하향 스트리밍이 진행되는 동안 상향 제어 신호를 보내야 한다.** 취소, 우선순위 변경, 사용자 개입. SSE 로는 별도 요청을 열어야 하고, 그 요청은 진행 중인 스트림과 상관관계를 직접 맞춰야 한다.
2. **한 연결에 여러 작업이 동시에 진행된다.** 작업마다 연결을 열면 핸드셰이크와 커넥션 수가 곱해진다.
3. **서버가 요청 없이 먼저 보낸다.** presence, 브로드캐스트, 서버가 시작한 도구 호출.
4. **핸드셰이크 비용이 아깝다.** 모바일에서 메시지마다 TLS 재협상을 피하고 싶을 때.

셋 다 아니면 SSE 가 낫다. SSE 는 프록시를 잘 통과하고, 디버깅이 쉽고, 연결 수명을 관리할 코드가 없다.

LLM 채팅에서 이 판단이 어떻게 갈리는지는 [[websocket-full-duplex-tanstack-ai]] 에 실제 구현 코드로 정리했다.

---

## 참고

- Chrome, "Streaming requests with the fetch API" — `duplex: 'half'`, HTTP/2 요구, 응답 지연
- MDN, WebTransport API
- WebKit, Safari 26.4 WebTransport 지원 (2026-03)
- RFC 6455 (WebSocket), RFC 9114 (HTTP/3)
