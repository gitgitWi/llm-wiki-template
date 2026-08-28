---
title: Styling Linear for the future with StyleX
type: source
visibility: public
domains: [dev, infra]
tags: [stylex, styled-components, css-in-js, codemod, linting, react]
status: living
created: 2026-08-28
updated: 2026-08-28
source:
  url: "https://linear.app/now/styling-linear-for-the-future-stylex"
  author: Kenneth Skovhus
  site: Linear
  published: August 26,
  captured: 2026-08-28
  word_count: 2538
  extractor: "defuddle:http"
summary:
  updated: 2026-08-28T18:42:03+09:00
  provider: cline
  model: "cline:deepseek/deepseek-v4-flash"
  backend: cline
  thinking: high
related: []
---

# Styling Linear for the future with StyleX

Linear이 자사의 React 애플리케이션에서 CSS-in-JS 라이브러리인 styled-components를 Meta가 만든 StyleX로 전면 마이그레이션한 사례를 다룬 글이다. 1,000개가 넘는 PR을 통해 대규모·활성 코드베이스를 제품 개발을 멈추지 않고 전환하는 과정에서, 결정론적 툴링(codemod)·코딩 에이전트·인간의 판단을 상황에 따라 적절히 배분한 접근과 성능·유지보수성 관점의 실질적 성과를 공유한다. 스타일링 경계(boundary)를 "기술적으로 강제"하는 것이 더 커지는 팀과 에이전트가 점점 더 코드를 작성하는 코드베이스에서 왜 중요한지 보여준다.

**핵심 내용**

- **이유**: styled-components의 무한한 유연성이 오히려 부채가 됐다. `styled(Button)` 같은 패턴이 스타일링 계약을 명시하지 않은 채 밖에서 컴포넌트를 수정하는 것을 정상화했고, 최근 리디자인 이후 UI 회귀(regression)가 이어지는 원인이 됐다. 여기에 React 18의 concurrent rendering 도입 후 성능 회귀가 발생한 것이 결정타였으며, styled-components가 유지보수 모드로 접어든 점도 고려했다.
- **StyleX 선택 배경**: 요구사항은 ①스타일 생성이 런타임이 아닌 빌드 타임에 일어날 것 ②원격 스타일링을 '의도적으로 어렵게' 만들 것 ③스타일 병합이 동일한 파일 간 명확한 규칙에 따라 결정적일 것 ④타입 안전한 스타일링 계약 ⑤React 호환성·활발한 유지보수였다. vanilla-extract가 후보에 올랐지만 API 분산과 컴포넌트/스타일 파일 분리에 대한 선호로 탈락했고 StyleX가 최적의 밸런스였다.
- **마이그레이션 전략**: 전문화된 것을 handover하기 어려워 결정론적 codemod([`styled-components-to-stylex-codemod`](https://github.com/skovhus/styled-components-to-stylex-codemod))를 시작점으로 했고, 에이전트가 이를 확장하도록 했다. 온라인 playground, cross-file selector 처리, 대부분의 edge case에 대한 회귀 테스트를 포함한다. 당시 styled-components가 Turing-complete 언어이자 열린 API라 에이전트가 결과물처럼 하지만 틀린 것을 만들기 쉬워, Fable·Sol이 출시되기 전에는 자동화가 어려웠다.
- **리스크 완화**: ①먼저 StyleX의 변수·상수·공유 primitive를 정의, ②좁은 스코프·codemod runner·예시·검증 스크립트·체크리스트를 갖춘 에이전트를 스폰(단, 복잡한 hover·theming·레이아웃 차이 검증은 Fable/Sol 이전에는 수동 테스트가 필요), ③다른 스타일 컴포넌트를 감싸거나 재스타일링하지 않는 leaf node부터 마이그레이션했다.
- **채택 촉진**: dev 툴바에 스타일드컴포넌트 CSS 규칙 수 카운터, 스타일드컴포넌트 vs StyleX 사용 컴포넌트 하이라이트 툴, 진행도 그래프를 매주 생성. PR에서 새 styled-components에 지적하는 bot을 도입해 회귀가 스며드는 것을 막았다. 2026년 3월 100%에서 8월 6일 0%까지 스타일드컴포넌트 파일 비중을 내렸다.
- **규칙 강제 툴링**: Oxlint가 빠른 로컬 규칙(작성 실수, 디자인 토큰 사용, React props가 생성된 StyleX 출력을 덮어쓰는 경우)을 처리하며, 파일 경계 넘는 문맥이 필요한 것은 커스텀 타입 인지 저장소 checker가 처리. 대상은 ①기존 스타일링 시스템 재등장 방지·정리 ②`sx` prop을 표준 스타일링 인터페이스로, 컴포넌트 경계를 넘는 스타일 전파 ③`className`/`style`/JSX spread/`sx`/`stylex.props()` 병합 conflict와 shorthand 조건부 병합 ④색·typography 등 공유 변수 사용, hover/press/link 통일(예: `highlightMixin`은 pointer에 `:hover`/touch에 `:active`, 외부 링크 밑줄은 link-underline 선호도 공유 mixin) ⑤컴파일러·런타임·테마 안전(defineConsts 산술방식, undefined 동적 값 가드, raw CSS 변수→타입 `defineVars()` 등)으로 나뉜다.
- **StyleX는 폐쇄계가 아님**: 전역 선택자나 서드파티 DOM 재스타일링 같은 근본적으로 CSS적인 문제는 CSS Modules을 스코프된 명시적 폴백으로 제공하고, 테마는 StyleX 빌트인 대신 `ThemeProvider`가 StyleX가 생성한 hashed 커스텀 프로퍼티를 추출해 런타임에 주입하는 방식으로 확장했다. 커스텀 테마는 base/accent/contrast 같은 적은 입력에서 LCH 색공간 기준 100개 이상의 변수를 도출한다.
- **성과**: Fable로 3월 vs 현재 클라이언트 프로파일을 비교한 결과, view-heavy 페이지에서 런타임 스타일 주입 제거로 메인 스레드 CPU 작업이 대략 20~35% 줄었고, 테스트상 mid-tier 기기에서 약 30% 빨라졌다. 네비게이션 중 주입하던 CSS 규칙 수백 개가 0이 됐다. 다만 엔드 투 엔드 영향은 지속적 최적화와 얽혀 정확히 귀속(attribute)하기 어렵다.

**결론**

Linear는 1,000개 이상의 PR에 걸친 결정론적 codemod, 에이전트, 인간 판단의 결합으로 styled-components를 StyleX로 전환해 런타임에서 더 빠르고, 오용하기 어려우며, 점점 에이전트가 작성하는 코드베이스에 더 적합한 스타일링 시스템을 만들었다. 핵심은 단순히 라이브러리를 바꾸는 것이 아니라 툴링·린트·명시적 계약으로 스타일링 경계를 기술적으로 강제한 점이다.

> 원문: <https://linear.app/now/styling-linear-for-the-future-stylex>
> 아카이브: `articles/2026-08-28-styling-linear-for-the-future-with-stylex.md`
