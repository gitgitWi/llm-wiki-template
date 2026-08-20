---
title: Effect.ts와 결정적 시뮬레이션 테스트(DST) — 팩트체크
type: synthesis
visibility: public
domains: [dev, ai]
tags: [effect-ts, testclock, deterministic-simulation-testing, virtual-clock, pglite, test-strategy]
status: living
created: 2026-08-20
updated: 2026-08-20
description: Effect.ts의 TestClock으로 가상 시간을 돌려 E2E를 단위 테스트 속도로 만든다는 주장을 항목별로 검증하고, 빠진 전제와 대안을 보강한다.
read_when: Effect 도입을 시간 제어·테스트 속도 근거로 검토할 때, 또는 "가상 시계 = DST" 라는 등식을 점검할 때.
agent: claude-opus-5 / claude-code
related: ["[[deterministic-simulation-testing]]", "[[effect-ts]]", "[[2026-08-20-ewind-dev]]", "[[agentic-coding-design-and-code-review]]"]
---

# Effect.ts와 결정적 시뮬레이션 테스트(DST) — 팩트체크

> 2026-08-20 검증. 검증 대상은 [[2026-08-20-ewind-dev]] 원문(중국어 X 포스트)과, 그 글을 AI가 한국어로 풀어 쓴 설명이다.
> 결론부터: **큰 줄기는 맞고, 코드 예제는 그대로 쓰면 안 되며, "가상 시계 = DST" 는 과장이다.**

---

## 0. 먼저, 원문의 성격

원문은 중립적인 소개 글이 아니다. `@ThaddeusJiang` 의 "나는 이 프레임워크를 못 받아들이겠다, 왜 좋아하는지 모르겠다" 라는 질문에 `@ewind_dev` 가 **반론으로 답한 글**이다.

그래서 원문은 장점 한 축(시간 제어)에 무게를 몰아 싣는다. AI가 만든 한국어 설명은 이걸 "단점 / 장점" 이라는 균형 잡힌 목록으로 재배치했다. 재배치 과정에서 원문에 없던 균형이 생기고, 원문에 있던 조건절이 사라졌다.

원문에 있었지만 한국어 설명에서 빠진 것:

- **flaky 의 원인을 순서 비결정성으로 지목한 부분** — 원문은 "네이티브 `setTimeout` 과 마이크로태스크 스케줄링이 시점을 통제 불가능하게 만든다" 고 썼다.
- **Ryan Dahl(Node 창시자)의 celld 사례 인용** — DST 아이디어의 최근 근거로 든 것이다. [[2026-08-20-rough-sea]] 참조.
- **테스트 입도에 대한 단서** — "필드 세부는 테스트하지 않고, 최종적으로 보이는 메시지 내용만 테스트한다"(BDD).
- **직업적 문맥** — 원문 끝에 기술 컨설팅 홍보가 붙어 있다. 중립 기술 문서가 아니다.

---

## 1. 판정 요약

| # | 주장 | 판정 | 근거 |
|---|---|---|---|
| 1 | Effect는 부작용을 서비스로 추상화하고 DI로 통제한다 | **맞음** | `Effect<A, E, R>` 의 `R` 이 요구 서비스, `Layer` 가 그 구현 |
| 2 | RxJS 스타일이다 | **부분적으로 틀림** | `pipe` 표기만 닮았다. 실행 모델이 다르다 (§4) |
| 3 | `yield` 문법을 강제한다 | **틀림** | `Effect.gen` 은 관용구지 강제가 아니다. pipe 스타일로 전부 쓸 수 있다 |
| 4 | Layer 개념이 진입 장벽이다 | **맞음** | 널리 공유된 평가 |
| 5 | boilerplate 가 많다 | **맞음** | 원문 스스로 "최대 단점" 으로 꼽는다 |
| 6 | TestClock 으로 시간을 앞으로 당길 수 있다 | **맞음** | `adjust`, `setTime`, `withLive` 실재 |
| 7 | 예제 코드가 타임아웃을 검증한다 | **틀림 — 컴파일·실행 모두 실패** | §3 |
| 8 | `it.effect` 가 TestClock 을 자동 제공한다 | **맞음** | `@effect/vitest` README |
| 9 | 시간은 저절로 흐르지 않는다 | **맞음** | 공식 문서: 수동으로 조정할 때만 전진 |
| 10 | `setTimeout` 때문에 느리고 flaky 하다 | **절반** | 느린 건 맞다. flaky 원인 설명이 부정확하다 (§5) |
| 11 | 이것을 DST 라고 부른다 | **용어는 맞고 범위는 과장** | §6 |
| 12 | Ryan Dahl 이 celld 에서 DST 를 언급했다 | **맞음(간접 확인)** | §6 |
| 13 | 프론트·백을 한 프로세스 가상 시계에서 함께 돌린다 | **개념은 가능, 장벽 큼** | §7 |
| 14 | PGlite 로 전체 스택 인프로세스 결정적 테스트 | **절반** | §7 |
| 15 | (파생 오해) Effect 가 DST 프레임워크를 제공한다 | **아니다** | §6 |

---

## 2. 버전 상황 — 이게 예제 오류의 뿌리

2026-08-20 npm 기준:

| 패키지 | latest | beta | rc |
|---|---|---|---|
| `effect` | **3.22.1** | 4.0.0-beta.107 | 4.0.0-rc.111 |
| `@effect/vitest` | 0.30.0 (v3 라인) | — | 4.0.0-rc.111 (저장소 main) |

**Effect 4.0 은 아직 rc 다.** 그런데 v3 과 v4 는 테스트 API 이름이 다르다.

| | v3 (3.22.x, 현재 stable) | v4 (rc) |
|---|---|---|
| TestClock 임포트 | `import { TestClock } from "effect"` | `import { TestClock } from "effect/testing"` |
| 주입 | `Effect.provide(TestContext.TestContext)` | `Effect.provide(TestClock.layer())` |
| fork | `Effect.fork` | `Effect.forkChild` / `forkIn` / `forkScoped` / `forkDetach` — **`Effect.fork` 없음** |
| 타임아웃을 값으로 | `Effect.timeoutTo({ duration, onSuccess, onTimeout })` | `Effect.timeoutOption` 또는 `Effect.timeoutOrElse({ duration, orElse })` |
| 시드 난수 | `Random.make(seed)`, `Random.fixed(values)` | `Random.withSeed` |
| 테스트 서비스 | `TestClock`, `TestContext`, `TestConfig`, `TestLive`, `TestSized`, `TestAnnotation*` | `effect/testing`: `TestClock`, `TestConsole`, `FastCheck`, `TestSchema` |

**두 버전 모두 `TestRandom` 이 없다.** ZIO 에는 있지만 Effect 에는 없다. 시드 난수는 `Random` 서비스를 직접 교체해서 만든다.

---

## 3. 예제 코드는 두 군데가 틀렸다

원문 설명에 실린 코드:

```ts
import { Effect, Fiber } from "effect"
import { TestClock } from "effect/testing"     // ← v4 경로

const test = Effect.gen(function* () {
  const fiber = yield* Effect.sleep("5 minutes").pipe(
    Effect.timeout("1 minute"),                // ← 실패로 끝난다
    Effect.fork                                // ← v4 에 없다
  )
  yield* TestClock.adjust("1 minute")
  const result = yield* Fiber.join(fiber)
  // → 타임아웃 발생                            // ← 값이 아니라 실패가 온다
})
```

**오류 1 — 버전 혼합.** `effect/testing` 은 v4 경로다. `Effect.fork` 는 v3 이름이다. v4 `Effect.ts` 에는 `forkChild`, `forkIn`, `forkScoped`, `forkDetach` 만 있고 맨 이름 `fork` 는 없다. 두 줄이 같은 파일에서 함께 성립하지 않는다.

**오류 2 — 타임아웃을 값으로 받지 않았다.** `Effect.timeout` 은 성공값을 돌려주지 않는다. 실패 채널에 에러를 넣는다 (v4 `Cause.TimeoutError`, v3 `TimeoutException`). `Fiber.join` 은 그 실패를 그대로 전파한다. 그래서 `const result = yield* Fiber.join(fiber)` 는 "타임아웃 발생" 을 알려주는 대신 **테스트를 실패시킨다.** 주석이 실제 동작과 반대다.

공식 문서가 `timeoutTo`(v3) / `timeoutOrElse`(v4) 를 쓰는 이유가 이것이다. 타임아웃을 **에러가 아니라 `Option` 값으로** 바꿔서 단정(assert)할 수 있게 만든다.

고쳐 쓴 v4(rc) 버전:

```ts
import { Effect, Fiber, Option } from "effect"
import { TestClock } from "effect/testing"
import * as assert from "node:assert"

const test = Effect.gen(function* () {
  const fiber = yield* Effect.sleep("5 minutes").pipe(
    Effect.map(Option.some),
    Effect.timeoutOrElse({
      duration: "1 minute",
      orElse: () => Effect.succeed(Option.none<void>()),
    }),
    Effect.forkChild,
  )

  yield* TestClock.adjust("1 minute")           // 가상 1분

  const result = yield* Fiber.join(fiber)
  assert.ok(Option.isNone(result))              // None = 타임아웃
}).pipe(Effect.provide(TestClock.layer()))
```

고쳐 쓴 v3(현재 stable) 버전:

```ts
import { Effect, Fiber, Option, TestClock, TestContext } from "effect"

const test = Effect.gen(function* () {
  const fiber = yield* Effect.sleep("5 minutes").pipe(
    Effect.timeoutTo({
      duration: "1 minute",
      onSuccess: Option.some,
      onTimeout: () => Option.none<void>(),
    }),
    Effect.fork
  )
  yield* TestClock.adjust("1 minute")
  const result = yield* Fiber.join(fiber)
  // Option.isNone(result) === true
}).pipe(Effect.provide(TestContext.TestContext))
```

`fork` 가 왜 필수인가: fork 하지 않으면 테스트 파이버가 `sleep` 에서 멈춘다. 시계를 앞으로 당길 주체가 사라진다. 공식 권장 패턴은 **fork → adjust → 검증** 순서다.

`TestClock` 실제 인터페이스(v4):

```ts
interface TestClock extends Clock {
  adjust(duration: Input): Effect<void>       // 가장 많이 쓴다
  setTime(timestamp: number): Effect<void>    // epoch 밀리초. "5 minutes" 같은 문자열 아님
  withLive<A, E, R>(effect: Effect<A, E, R>): Effect<A, E, R>  // 이 구간만 실제 시계
}
```

한국어 설명의 API 표는 `setTime(time)` 을 "특정 시점으로 설정" 이라고만 적었다. **인자는 duration 문자열이 아니라 epoch 밀리초 숫자다.** 그리고 표에 없던 `withLive` 가 실무에서 필요하다 — 가상 시계 안에서 실제 대기가 필요한 구간을 빠져나가는 탈출구다.

`it.effect` 는 사실이 맞다. `@effect/vitest` README 는 `it.effect` 를 "TestClock, TestConsole 같은 테스트 서비스와 함께 scoped 테스트를 실행" 이라고 적는다. 두 가지만 덧붙인다. **TestClock 은 0 에서 시작한다** — 실제 현재 시각이 아니다. 실제 시계가 필요하면 `it.live` 를 쓴다.

---

## 4. "RxJS 스타일" 은 오해를 만든다

닮은 건 `pipe(...)` 표기 하나다. 실행 모델은 다르다.

| | RxJS `Observable` | Effect `Effect<A, E, R>` |
|---|---|---|
| 모델 | push 기반 이벤트 스트림 | 아직 실행되지 않은 계산 1건의 설명서 |
| 값 개수 | 0..n 개 | 성공하면 1개 |
| 에러 | 런타임 채널, 타입에 안 남는다 | `E` 로 타입에 남는다 |
| 의존성 | 없음 | `R` 로 타입에 남는다 |
| 계보 | ReactiveX | Scala ZIO |

Effect 에도 스트림이 있지만(`Stream`) pull 기반이다. RxJS 를 알아서 Effect 를 안다고 생각하면 오히려 헷갈린다. 정확한 비유는 **"TypeScript 로 옮긴 ZIO"** 다. `R` 채널이 곧 DI 이고, 그게 시간 교체를 가능하게 하는 장치다.

`yield` 강제도 사실이 아니다. `Effect.gen(function* () {...})` 는 관용구로 굳었을 뿐, 모든 조합은 `pipe` 로도 쓸 수 있다. 다만 실무 코드베이스 대부분이 `gen` 을 쓰므로 **체감상 강제에 가깝다** 는 원문의 인상 자체는 이해할 만하다.

---

## 5. flaky 의 원인 — 원문도, 요약도 정확하지 않다

한국어 설명: "`setTimeout` 은 실제 시간을 기다려야 해서 테스트가 느리고 flaky 해진다."

**느림과 flaky 는 원인이 다르다.**

- **느림** 의 원인은 실제 대기다. 이건 맞다. 가상 시계가 정확히 이 문제를 없앤다.
- **flaky** 의 원인은 대기가 아니라 **순서 비결정성**이다.

원문은 비결정성의 원인으로 "마이크로태스크 스케줄링" 을 든다. 이건 부정확하다. 마이크로태스크 큐는 규격상 FIFO 로 결정적으로 비워진다. 실제 비결정성은 다른 데서 온다.

- I/O 완료 시점 (디스크, 소켓)
- 타이머 클램핑과 병합, 백그라운드 탭 스로틀링
- 프로세스·머신 경계 (브라우저 ↔ 서버 ↔ DB)
- 네트워크 지연과 재시도
- 테스트 러너의 병렬 실행, 공유 상태

Effect 는 이 중 **"내 코드가 시간과 자원을 요청하는 방식"** 만 결정적으로 만든다. OS 와 네트워크의 비결정성 자체를 없애지는 못한다. 없애는 방법은 그 경계를 인프로세스 구현으로 **교체**하는 것이고, 그게 §7 의 구상이다.

---

## 6. "이걸 DST 라고 부른다" — 용어는 맞지만 범위가 다르다

DST(Deterministic Simulation Testing)의 표준적 정의는 세 축을 모두 결정적으로 만드는 것이다. 자세한 내용은 [[deterministic-simulation-testing]].

| 축 | 무슨 뜻인가 | Effect TestClock |
|---|---|---|
| **시계** | 시간이 코드의 명령으로만 흐른다 | **제공** |
| **스케줄** | 동시 실행 인터리빙을 시드로 탐색하고 재현한다 | **없음** |
| **난수·결함** | 난수를 시드로 고정하고, 실패를 주입한다 | 난수는 수동 교체, 결함 주입 **없음** |

**가상 시계는 DST 의 필요조건 하나일 뿐이다.** FoundationDB·TigerBeetle·Antithesis 계열 DST 의 핵심 가치는 "시드 하나로 실패를 재현한다" 와 "스케줄 공간을 탐색해 못 보던 인터리빙을 찾는다" 에 있다. TestClock 은 탐색을 하지 않는다. 개발자가 `adjust` 로 지정한 시나리오만 재생한다.

**Effect 코어에 시드 스케줄러는 없다.** 관련 시도가 있었다는 점은 확인된다.

- 커뮤니티 PR [Effect-TS/effect#6216](https://github.com/Effect-TS/effect/pull/6216) `feat: deterministic simulation testing (DST) framework` — 시드 PCG 스케줄러, `it.dst()` 다중 시드 테스트, liveness 체커(굶주림·데드락 탐지), 실패 축소까지 담은 제안. **2026-05-06 열렸고 같은 날 닫혔다. 머지되지 않았다.**
- v4 `effect/testing` 에 실제로 있는 것: `TestClock`, `TestConsole`, `FastCheck`, `TestSchema`. `FastCheck` 통합은 property-based 테스트 쪽이고, DST 의 스케줄 탐색과는 다르다.

시드 난수는 직접 만들어야 한다. v3 는 `Random.make(seed)` 또는 `Random.fixed([...])` 를 `Effect.withRandom` 으로 주입하고, v4 는 `Random.withSeed` 를 쓴다.

**celld 인용은 사실이다.** Ryan Dahl(@rough__sea)이 celld 를 공개했다 — V8 + S3 + SQLite + LTX + Tokio 로 만든 자체 호스팅 분산 Durable Objects·Workers 구현이다. DST 를 진지하게 붙이고 나서야 설계가 자리를 잡았다고 말한 것으로 전해진다. 다만 **공개 발표 트윗 본문 자체에는 DST 언급이 없다**(후속 발언으로 전해지며, 스레드 전문은 직접 확인하지 못했다). 방향은 맞지만 근거의 강도는 원문이 암시하는 정도보다 약하다.

---

## 7. 풀스택 인프로세스 구상 — 어디까지 진짜인가

원문의 구상: IM 앱을 Effect 로 풀스택 구성하고, 프론트 데이터층은 SQLite, 백엔드는 PG, 전부 한 Node 프로세스의 TestClock 하나로 "PG 초기화 → A가 메시지 전송 → 철회 → B 접속 → 수신" 같은 복잡한 시퀀스를 결정적으로 재생한다.

**진짜인 부분:** PGlite 는 실제로 존재하고 실제로 인프로세스다. WASM Postgres 빌드이고, gzip 3MB 정도이며, Node·브라우저·Bun·Deno 에서 돌고, pgvector·PostGIS 같은 확장도 상당수 지원한다(현재 0.5.5). testcontainers 로 Docker 를 띄우는 것과 비교하면 시작 비용 차이가 크다.

**빠진 전제 네 가지:**

1. **브라우저가 없으면 E2E 가 아니다.** 한 Node 프로세스에서 돌리는 것은 렌더링·레이아웃·실제 이벤트 루프·실제 네트워크 스택이 빠진 **통합 테스트**다. 유용하지만, "E2E 를 단위 테스트 속도로" 라는 문장은 대상을 바꿔치기한다. CSS 회귀, 포커스 처리, 브라우저별 동작은 여전히 실제 브라우저가 필요하다.
2. **PGlite 는 단일 커넥션이다.** Emscripten 으로 컴파일한 프로세스는 fork 를 못 하므로 Postgres 의 single-user 모드를 쓴다. v0.4 에서 커넥션 다중화가 들어왔지만 내부 커넥션은 여전히 하나다. 그래서 **락 경합, 격리 수준, 데드락, 커넥션 풀 고갈 같은 동시성 버그는 재현되지 않는다.** IM 의 "동시에 같은 방에 쓰기" 는 정확히 그 부류다.
3. **DB 안의 시간은 TestClock 을 따르지 않는다.** `SELECT now()` 는 WASM 안에서 시스템 시계를 읽는다. PGlite 는 시계 주입 API 를 문서화하지 않았고, Postgres 에는 시간 함수를 얼리는 기능이 없다. 시간 의존 로직을 결정적으로 만들려면 **시각을 DB 에서 얻지 말고 애플리케이션이 파라미터로 넘겨야 한다** — 즉 설계 제약이 코드 전체로 번진다.
4. **Effect 밖의 시간은 우회한다.** `Date.now()` 나 raw `setTimeout` 을 직접 부르는 코드는 TestClock 을 지나지 않는다. 자기 코드는 규율로 막을 수 있지만, **서드파티 라이브러리 대부분은 Clock 을 모른다.** 전면 가상화는 의존성 선택까지 구속한다.

정리하면, 원문의 구상은 "가능하다" 가 아니라 **"도메인 로직을 그 제약에 맞게 설계하면 그 범위 안에서 가능하다"** 다. 그 제약이 곧 진짜 도입 비용이고, boilerplate 보다 비싸다.

---

## 8. Effect 없이 가상 시간을 얻는 법 — 여기가 원문의 최대 공백

"시간을 앞으로 당겨 테스트를 빠르게 만든다" 는 Effect 고유 기능이 아니다. 원문은 이 대안들을 언급하지 않는다.

| 방법 | 가상화 대상 | 범위 | 구조 | 한계 |
|---|---|---|---|---|
| vitest `vi.useFakeTimers()` | `Date`, `setTimeout`, `setInterval` 등 전역 | 한 프로세스 | **전역 몽키패치** | 실제 I/O·DB 는 그대로, 서드파티가 실제 타이머를 잡고 있으면 깨짐, 테스트 간 누출 위험 |
| `@sinonjs/fake-timers` | 같음 (vitest 내부 구현체) | 한 프로세스 | 전역 몽키패치 | 같음 |
| Playwright `page.clock` (1.45+) | 페이지의 `Date`·타이머·`rAF`·`requestIdleCallback`·`performance` | **실제 브라우저 E2E** | 브라우저 컨텍스트 주입 | 서버 시간은 안 움직인다 |
| Effect `TestClock` | Effect 를 통과하는 모든 `sleep`·`timeout`·`schedule`·`retry` | Effect 로 감싼 코드 | **의존성 교체(DI)** | Effect 밖 코드는 우회 |

핵심 차이는 "시간을 당길 수 있는가" 가 아니다. **어떻게 당기는가** 다.

- fake timers 는 **전역을 바꾼다.** 싸고 즉시 되지만, 격리가 약하고 시간 축 하나만 다룬다.
- `page.clock` 은 진짜 브라우저 안에서 시간을 당긴다. 그래서 "느린 E2E" 문제에는 오히려 Effect 보다 직접적인 답이다. 대신 서버 쪽은 그대로 실제 시간이다.
- TestClock 은 **의존성을 갈아끼운다.** 전역을 건드리지 않으므로 병렬 테스트와 함께 쓸 수 있고, 시간·난수·콘솔·네트워크·DB 를 **같은 한 가지 메커니즘(Layer)** 으로 교체한다.

**Effect 의 진짜 판매 논지는 "가상 시계" 가 아니라 "가상화의 균일성" 이다.** 시간만 필요하면 fake timers 나 `page.clock` 이 훨씬 싸다. 시간·난수·외부 API·DB·큐를 전부 같은 방식으로 바꿔 끼우고, 그걸 타입으로 강제받고 싶을 때 Effect 가 값을 한다. 그 대가로 **모든 코드가 Effect 안에 있어야 한다.**

---

## 9. "AI 가 써주니 boilerplate 는 문제가 아니다" 는 논지

원문의 마지막 문장이자 가장 논쟁적인 부분이다. "Effect 의 최대 단점은 boilerplate 지만, 앞으로 사람이 정말 코드를 손으로 써야 하는가?"

반은 맞다. 작성 비용은 실제로 내려갔다. 그러나 [[agentic-coding-design-and-code-review]] 에 정리한 것과 같은 이유로, **작성이 싸진다고 이해·리뷰·디버그가 싸지지는 않는다.** Effect 코드의 비용은 타이핑이 아니라 다음 쪽에 있다.

- 타입 에러 메시지가 길다. `R` 채널이 안 맞을 때 원인을 읽어내는 건 사람 몫이다.
- Layer 조립이 틀리면 런타임까지 안 가고 타입에서 막히지만, **어디를 고쳐야 하는지는 타입이 알려주지 않는다.**
- 스택 트레이스가 파이버 경계를 넘는다. AI 가 만든 코드에서 문제가 생기면 추적 비용이 더 든다.

반대 방향의 논지도 있고, 이쪽이 더 강하다. **에이전트가 코드를 대량 생산하는 상황에서는 "검증 표면" 이 병목이다.** Effect 는 에러와 의존성을 타입에 올려놓기 때문에, 에이전트가 놓친 실패 경로를 컴파일러가 잡는다. 여기에 결정적 테스트가 붙으면 "빠르고 반복 가능한 검증" 이라는 방어선이 하나 더 생긴다. 이건 agentic 워크플로에서 실제로 값이 큰 조합이다.

그래서 정확한 결론은 "boilerplate 는 AI 가 해결한다" 가 아니라 이렇다. **AI 는 Effect 도입 비용의 일부(타이핑)를 깎아주고, Effect 는 AI 도입 비용의 일부(검증)를 깎아준다. 남는 비용은 사람이 읽는 비용이고, 그건 아직 아무도 깎아주지 않는다.**

---

## 10. 그래서 언제 도입할 만한가

**값을 할 조건 — 많이 겹칠수록 유리**

- 시간·재시도·백오프·스케줄이 도메인 로직의 핵심이다 (결제 정산, 알림, 워크플로 엔진, 실시간 협업)
- 외부 시스템 경계가 많고, 그걸 전부 교체 가능하게 만들 의지가 있다
- 팀이 함수형 스타일과 긴 타입 에러를 감당할 수 있다
- 새로 시작하는 코드베이스다 — 부분 도입은 두 세계의 비용을 다 낸다

**말릴 조건**

- 필요한 게 "느린 시간 의존 테스트 고치기" 뿐이다 → `vi.useFakeTimers()` 나 `page.clock` 먼저
- 이미 큰 명령형 코드베이스가 있고 점진적 도입만 가능하다
- 팀 규모가 작고 이탈 위험이 크다 — Effect 코드는 Effect 를 아는 사람만 유지할 수 있다
- v4 API 를 지금 채택한다면 **rc 의존을 감수하는 것이다** (2026-08-20 기준 stable 은 3.22.1)

**중간 지대가 있다.** 시간을 서비스로 다루는 것 자체는 Effect 없이도 할 수 있다. `Clock` 인터페이스를 직접 정의하고 주입하는 패턴만으로도 §5 의 "느림" 문제와 순서 비결정성 상당 부분이 사라진다. 원문의 통찰 중 이식 가능한 핵심은 **"시간을 의존성으로 취급하라"** 이고, 그건 Effect 도입 결정과 분리할 수 있다.

---

## 11. 확인 방법 (재현용)

```bash
npm view effect dist-tags                  # 3.22.1 stable / 4.0.0-rc.x
npm view @electric-sql/pglite version      # 0.5.5

# v4 에 Effect.fork 가 없다는 확인
gh api repos/Effect-TS/effect/contents/packages/effect/src/Effect.ts \
  --jq '.content' | base64 -d | grep -nE "^export const fork"

# v3 / v4 테스트 모듈 목록 차이
gh api repos/Effect-TS/effect/contents/packages/effect/src/testing --jq '.[].name'
gh api "repos/Effect-TS/effect/contents/packages/effect/src?ref=v3" --jq '.[].name|select(startswith("Test"))'
```

---

## 관련

- [[deterministic-simulation-testing]] — DST 개념 자체, 세 축과 계보
- [[effect-ts]] — 라이브러리 팩트 시트
- [[2026-08-20-ewind-dev]] — 검증 대상 원문
- [[2026-08-20-rough-sea]] — celld 발표, DST 인용의 출처
- [[agentic-coding-design-and-code-review]] — "작성은 싸졌지만 이해는 비싸다" 와 검증 방어선

## 출처

- 원문: <https://x.com/ewind_dev/status/2090311368117473382>
- Effect v4 TestClock 문서: <https://www.effect.website/docs/v4/testing/testclock>
- Effect v3 TestClock 문서: <https://effect.website/docs/testing/testclock/>
- Effect DST PR (미머지): <https://github.com/Effect-TS/effect/pull/6216>
- PGlite: <https://pglite.dev/docs/> · v0.4 커넥션 다중화 <https://electric.ax/blog/2026/03/25/announcing-pglite-v04>
- Playwright Clock: <https://playwright.dev/docs/api/class-clock>
- DST 개념: <https://antithesis.com/docs/resources/deterministic_simulation_testing/> · <https://journal.resonatehq.io/p/deterministic-simulation-testing>
