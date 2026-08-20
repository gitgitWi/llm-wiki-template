---
title: Effect (Effect-TS)
type: entity
visibility: public
domains: [dev]
tags: [effect-ts, typescript, layer, dependency-injection, fiber, testclock]
status: living
created: 2026-08-20
updated: 2026-08-20
description: TypeScript 이펙트 시스템 라이브러리 팩트 시트 — 타입 채널, Layer 온보딩, 버전 상황(3.22.1 stable / 4.0 rc), v3↔v4 API 차이.
read_when: Effect 도입을 검토할 때, Layer·DI 구조를 처음 배울 때, 또는 v3/v4 API 이름이 헷갈릴 때.
agent: claude-opus-5 / claude-code
related: ["[[effect-ts-dst-testing]]"]
---

# Effect (Effect-TS)

TypeScript 로 이펙트 시스템과 표준 라이브러리를 제공하는 프레임워크. Scala 의 **ZIO** 계보다. RxJS 와는 `pipe` 표기만 닮았고 실행 모델이 다르다.

핵심은 타입 하나다.

```ts
Effect<A, E, R>
//     │  │  └─ R: 이 계산이 요구하는 서비스 (= DI 채널)
//     │  └──── E: 실패할 수 있는 방식 (타입에 남는다)
//     └─────── A: 성공값
```

`R` 이 비어야 실행할 수 있다. `Layer` 가 `R` 을 채운다. **시간·난수·네트워크·DB 를 테스트에서 갈아끼울 수 있는 이유가 전부 이 `R` 채널이다.**

---

## 버전 상황 (2026-08-20, npm)

| 태그 | 버전 |
|---|---|
| `effect@latest` | **3.22.1** |
| `effect@rc` | 4.0.0-rc.111 |
| `effect@beta` | 4.0.0-beta.107 |
| `@effect/vitest@latest` | 0.30.0 (v3 라인) |

**4.0 은 아직 rc 다.** 공식 문서 사이트가 v3 와 v4 를 함께 서비스하므로, 검색으로 찾은 예제가 어느 쪽인지 확인하지 않으면 섞인 코드를 쓰게 된다.

---

## v3 ↔ v4 이름 대응 (테스트 관련)

| | v3 (stable) | v4 (rc) |
|---|---|---|
| TestClock 위치 | `import { TestClock } from "effect"` | `import { TestClock } from "effect/testing"` |
| 테스트 서비스 주입 | `Effect.provide(TestContext.TestContext)` | `Effect.provide(TestClock.layer())` |
| fork | `Effect.fork` | `Effect.forkChild` / `forkIn` / `forkScoped` / `forkDetach` (맨 `fork` 없음) |
| 타임아웃 → 값 | `Effect.timeoutTo` | `Effect.timeoutOption` / `Effect.timeoutOrElse` |
| 타임아웃 → 실패 | `Effect.timeout` (`TimeoutException`) | `Effect.timeout` (`Cause.TimeoutError`) |
| 시드 난수 | `Random.make(seed)`, `Random.fixed([...])` | `Random.withSeed` |

**테스트 모듈 목록**

- v3: `TestClock`, `TestContext`, `TestConfig`, `TestLive`, `TestSized`, `TestAnnotation*`, `TestServices`
- v4 `effect/testing`: `TestClock`, `TestConsole`, `FastCheck`, `TestSchema`

**두 버전 모두 `TestRandom` 이 없다.** ZIO 에는 있다.

---

## TestClock 인터페이스 (v4)

```ts
interface TestClock extends Clock {
  adjust(duration: Input): Effect<void>       // 가상 시간을 그만큼 전진
  setTime(timestamp: number): Effect<void>    // epoch 밀리초 숫자
  withLive<A, E, R>(effect: Effect<A, E, R>): Effect<A, E, R>
}
```

시간은 저절로 흐르지 않는다. 권장 패턴은 **fork → adjust → 검증**. `@effect/vitest` 의 `it.effect` 는 TestClock·TestConsole 을 자동 주입하고 **시계를 0 에서 시작**한다. 실제 시계가 필요하면 `it.live`.

---

## Layer 온보딩 — 왜 어렵고, 무엇만 알면 되는가

원문이 "Layer 개념이 난해하다" 고 꼽은 그 부분이다. 어려운 이유는 개념이 복잡해서가 아니다. **다른 언어에 대응물이 없어서** 처음에 무엇에 비유할지 모르기 때문이다.

### 한 문장

**Layer 는 서비스가 아니다. 서비스를 만드는 조립법이다.**

```ts
Layer<ROut, E, RIn>
//    │     │  └─ RIn:  이걸 만들려면 무엇이 필요한가
//    │     └──── E:    만들다가 실패할 수 있는 방식
//    └────────── ROut: 무엇을 만들어내는가
```

대응 관계로 보면 이렇다.

| | 무엇인가 | 실행하면 |
|---|---|---|
| `Effect<A, E, R>` | 할 일 1건의 설명서 | 값 `A` 가 나온다 |
| `Layer<ROut, E, RIn>` | **도구를 만드는 설명서** | `R` 채널에 꽂을 서비스가 나온다 |

즉 Layer 는 애플리케이션의 **의존성 그래프를 값으로 다루는 방법**이다. 그래서 조립하고, 재사용하고, 통째로 갈아끼울 수 있다.

### 왜 그냥 `new Service()` 로 안 하는가

Layer 가 별개 개념으로 존재하는 이유는 네 가지다. 이 네 가지가 곧 Layer 가 값을 하는 지점이다.

1. **메모이제이션** — 같은 Layer 를 두 곳에서 참조해도 인스턴스는 **하나**다. DB 커넥션 풀이 두 개 생기는 사고를 구조적으로 막는다.
2. **자원 수명** — 획득과 해제를 함께 기술한다. 프로그램이 끝나면 역순으로 정리된다.
3. **비동기·실패 가능한 생성** — 생성 자체가 실패할 수 있고(설정 파일 없음, 접속 실패) 그 실패가 `E` 로 타입에 남는다. 생성자는 이걸 못 한다.
4. **교체** — 테스트에서 한 줄만 바꿔 다른 구현을 꽂는다. TestClock 이 정확히 이 사례다.

### 3단계

**1단계 — 서비스 정의.** v3 의 `Effect.Service` 는 Tag 와 기본 Layer(`.Default`)를 한 번에 만든다.

```ts
import { Effect } from "effect"

class Config extends Effect.Service<Config>()("Config", {
  sync: () => ({ url: "postgres://localhost" }),
}) {}

class Db extends Effect.Service<Db>()("Db", {
  effect: Effect.gen(function* () {
    const cfg = yield* Config                       // 의존성은 그냥 yield* 한다
    return { query: (sql: string) => Effect.succeed(`${cfg.url} << ${sql}`) }
  }),
  dependencies: [Config.Default],                   // 여기서 그래프가 연결된다
}) {}
```

**2단계 — 조립.** 헷갈리는 세 함수의 차이가 여기서 갈린다.

| 함수 | 하는 일 | 결과의 `RIn` | 언제 |
|---|---|---|---|
| `Layer.merge(a, b)` | 둘을 나란히 놓는다. 둘 다 밖에 노출된다 | 양쪽 요구가 남는다 | 서로 독립인 서비스 |
| `Layer.provide(바깥, 공급자)` | 공급자가 바깥의 요구를 채운다. **공급자는 밖에 안 보인다** | 채워진 만큼 줄어든다 | 내부 구현 세부를 감출 때 |
| `Layer.provideMerge(바깥, 공급자)` | 채우고, 공급자도 밖에 노출한다 | 줄어든다 | 공급자를 상위에서도 쓸 때 |

pipe 형태로는 `바깥.pipe(Layer.provide(공급자))` 로 쓴다.

**3단계 — 실행.** `Effect.provide` 로 `R` 채널을 비운다. `R` 이 비지 않으면 실행 함수가 타입에서 막는다.

```ts
const program = Effect.gen(function* () {
  const db = yield* Db
  return yield* db.query("SELECT 1")
})

Effect.runPromise(program.pipe(Effect.provide(Db.Default)))
```

### 처음에 반드시 걸리는 네 곳

1. **"타입 에러가 무슨 말인지 모르겠다"** — 대부분 `R` 이 안 비었다는 뜻이다. 즉 **Layer 를 하나 안 줬다.** 긴 에러 메시지에서 서비스 식별자 문자열(`"Db"` 같은 것)을 찾으면 범인이 나온다. 이게 Effect 타입 에러의 90%다.
2. **인스턴스가 두 개 생겼다** — 같은 Layer 를 두 번 **호출**하면 서로 다른 Layer 가 된다. 메모이제이션은 **같은 값을 참조할 때만** 동작한다. Layer 는 모듈 최상단에서 한 번 만들어 상수로 공유한다. 반대로 일부러 따로 만들려면 `Layer.fresh` 를 쓴다.
3. **자원이 안 닫힌다** — v3 은 `Layer.scoped` 로 획득·해제를 기술한다. **v4 에는 `Layer.scoped` 가 없다** — `Layer.effect` 안에서 Scope 를 다룬다.
4. **테스트 교체를 어떻게 하나** — 같은 서비스에 다른 Layer 를 주면 끝이다. 전체를 구현하기 싫으면 `Layer.mock`(3.17+)으로 **필요한 메서드만** 구현한다. 구현하지 않은 멤버는 호출되는 순간 unimplemented 결함으로 시끄럽게 실패한다. 조용히 `undefined` 를 돌려주지 않는다.

```ts
const DbTest = Layer.mock(Db, {
  query: () => Effect.succeed("고정 응답"),          // 이것만 쓴다
})                                                  // 나머지는 부르면 즉시 실패
```

### v3 ↔ v4 Layer 차이

| | v3 | v4 |
|---|---|---|
| 서비스 선언 | `Effect.Service<Self>()("Key", {...})` — Tag + `.Default` Layer 동시 생성 | `Context.Service<Self, Shape>()("Key")` — 키만 만들고 Layer 는 따로 |
| 자원 수명 | `Layer.scoped` | `Layer.effect` 안에서 처리 (`Layer.scoped` 없음) |
| 공통 | `succeed` · `sync` · `effect` · `merge` · `provide` · `provideMerge` · `fresh` · `mock` · `empty` · `launch` | 같음 |

### 그리고 TestClock 으로 이어진다

`Effect.provide(TestClock.layer())` 는 새 기능이 아니다. **Clock 서비스를 다른 Layer 로 갈아끼운 것뿐이다.** 시간 교체가 특별해 보이는 이유는 시간이 특별해서가 아니라, Effect 안에서는 시간도 그냥 하나의 서비스이기 때문이다.

이 구조를 이해하면 다음이 자동으로 따라온다 — 네트워크·DB·난수·콘솔도 같은 방식으로 교체할 수 있다. 그리고 그 균일성이 [[effect-ts-dst-testing]] 에서 정리한 Effect 의 진짜 판매 논지다.

---

## 평가 요약

**강점**: 에러와 의존성이 타입에 남는다 · 구조적 동시성(Fiber) · 재시도·스케줄이 일급 · 테스트에서 외부 세계를 균일하게 교체 가능.

**약점**: boilerplate · 긴 타입 에러 · Layer 학습 곡선 · 전면 도입 전제(Effect 밖 코드는 통제 밖) · 유지보수 인력 종속.

판단 근거와 도입 조건은 [[effect-ts-dst-testing]] §8~10.

---

## 링크

- 공식: <https://effect.website>
- v4 문서: <https://www.effect.website/docs/v4/>
- 저장소: <https://github.com/Effect-TS/effect>
