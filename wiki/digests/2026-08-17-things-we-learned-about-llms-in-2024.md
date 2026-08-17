---
title: Things we learned about LLMs in 2024
type: source
visibility: public
domains: [ai, dev]
tags: [llm-trends, model-pricing, reasoning-models, open-source-llms, local-inference, evals]
status: living
created: 2026-08-17
updated: 2026-08-17
source:
  url: "https://simonwillison.net/2024/Dec/31/llms-in-2024/"
  author: Simon Willison
  site: Simon Willison’s Weblog
  captured: 2026-08-17
  word_count: 6931
  extractor: "defuddle:http"
summary:
  updated: 2026-08-17T21:03:00+09:00
  provider: cline
  model: "cline:deepseek/deepseek-v4-flash"
  backend: cline
  thinking: high
related: []
---

# Things we learned about LLMs in 2024

이 글은 Simon Willison이 2024년 한 해 동안 LLM 분야에서 확인된 사실들을 정리한 연례 회고다. GPT-4 장벽 붕괴, 가격 폭락, 로컬 추론, 추론 스케일링(reasoning) 모델의 등장, 합성 학습 데이터 등 한 해의 핵심 테마와 전환점을 실제 수치와 함께 정리해, 2024년 LLM 생태계가 어디로 움직였는지를 한눈에 보여준다.

**핵심 내용**

- **GPT-4 장벽이 완전히 무너졌다.** 18개 조직의 70개 모델이 Chatbot Arena 리더보드에서 2023년 3월의 원조 GPT-4(`GPT-4-0314`, 현재 약 70위)보다 높은 순위를 기록했다. Google Gemini 1.5 Pro가 2월에 100만(이후 200만) 토큰 컨텍스트와 비디오 입력을 도입했고, Anthropic은 3월 Claude 3 시리즈와 6월 Claude 3.5 Sonnet을 출시했다.
- **프롬프트 가격이 급락했다.** GPT-4가 $30/mTok이던 시절(2023년 12월)과 비교해 GPT-4o는 $2.50(12배 저렴), GPT-4o mini는 $0.15(200배 저렴), Gemini 1.5 Flash 8B는 $0.0375/mTok까지 떨어졌다. 저자는 68,000장의 사진에 대한 설명을 생성하는 데 총 **$1.68**밖에 들지 않았다고 계산했다.
- **GPT-4급 모델이 노트북에서 실행된다.** 64GB M2 MacBook Pro에서 Qwen2.5-Coder-32B(Apache 2.0)와 Llama 3.3 70B가 돌아가고, Llama 3.2 3B는 iPhone의 MLC Chat 앱에서 약 20 tokens/s로 실행된다. Apple의 MLX 라이브러리가 핵심 역할을 했고, Hugging Face의 mlx-community에는 1,000개 이상의 변환 모델이 있다.
- **추론 스케일링 "reasoning" 모델이 새 축으로 등장했다.** OpenAI o1(9월 12일)이 "reasoning tokens"로 문제를 먼저 생각한 뒤 답하는 방식을 도입했고, o3(12월 20일)는 ARC-AGI 벤치마크에서 인상적인 결과를 냈지만 추론 비용이 $100만 이상으로 추정된다. Google `gemini-2.0-flash-thinking-exp`, Qwen QwQ/QvQ, DeepSeek-R1-Lite-Preview도 같은 흐름이다.
- **DeepSeek v3가 오픈 라이선스 모델 중 최고 성능을 찍었다.** 685B 파라미터로 Llama 3.1 405B보다 크며, 2,788,000 H800 GPU 시간·약 $5,576,000에 학습되어 Llama 3.1 405B의 11분의 1 GPU 시간으로 더 나은 벤치마크 성능(Claude 3.5 Sonnet급, Chatbot Arena 7위)을 냈다.
- **Evals가 LLM 애플리케이션 개발의 핵심 스킬이 됐다.** Anthropic의 Amanda Askell은 "좋은 system prompt의 비결은 테스트 주도 개발"이라고 했고, Vercel의 Malte Ubl은 프롬프트 보호보다 evals·모델·UX가 중요하다고 말했다. 강력한 eval 스위트가 있으면 새 모델 채택과 제품 개선 속도가 빨라진다.
- **프롬프트 기반 앱 생성은 이미 상품이 됐고, 합성 학습 데이터가 표준이 됐다.** Claude Artifacts로 시작한 "프롬프트 하나로 HTML/CSS/JS 앱 생성"이 GitHub Spark, Mistral Canvas, Cerebras 기반 구현, WebDev Arena 리더보드까지 이어졌다. 한편 "model collapse"는 일어나지 않았고, DeepSeek v3는 R1의 reasoning 데이터를, Llama 3.3 70B는 2,500만 개 이상의 합성 예제를 학습에 사용했다.

**결론**

2024년은 모델 성능·가격·로컬 실행 가능성 모두에서 GPT-4 시대가 끝났음을 확인한 해였다. 다만 "agents"는 여전히 미완성이고(gullibility·prompt injection 문제), 최고 모델의 무료 공개도 ChatGPT Pro($200/월, o1 Pro 전용) 출시로 끝났으며, LLM은 점점 더 다루기 어려운 파워 유저 도구가 되어가고 있다.

> 원문: <https://simonwillison.net/2024/Dec/31/llms-in-2024/>
> 아카이브: `articles/2026-08-17-things-we-learned-about-llms-in-2024.md`
