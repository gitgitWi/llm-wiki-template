---
title: macOS on-device STT 조사 (M1 Pro, 한영 혼용)
type: synthesis
visibility: public
domains: [ai, dev]
tags: [stt, speech-to-text, whisper, on-device, macos, apple-silicon, korean]
status: living
created: 2026-08-17
updated: 2026-08-17
related: []
---

# macOS(M1 Pro) on-device STT 조사

> 조사 날짜: 2026-08-17
> 대상 환경: Apple M1 Pro (arm64), macOS 26.6.1, 16GB RAM
> 조사 목적: 한국어 + 영어 기술용어를 혼용해 사용하는 개발자가, 다른 프로그램들과 병행하며 쓸 on-device(완전 로컬) STT 찾기

---

## 한눈에 보는 결론

- 한국어 + 영어 기술용어 혼용, 완전 로컬, 다른 개발 프로그램과 병행 → **Whisper 계열을 on-device로** (특히 `whisper.cpp` 또는 `mlx-whisper`)
- **macOS 내장 STT(SFSpeechRecognizer)는 이 용도에 부적합**
- 한국어는 Whisper에서 상대적으로 어려운 축 → **반드시 multilingual 모델(`large`/`medium`/`small`/`turbo`)** 사용, `.en` 전용 모델 금지
- 기술용어 오인식을 줄이려면 **초기 프롬프트(`initial_prompt`)에 용어 사전 주입**

---

## 선택지 개요

| 옵션 | on-device 여부 | 한국어 지원 | 기술용어·혼용 언어 | 리소스 (M1 Pro) |
|------|---------------|------------|-------------------|----------------|
| **macOS 내장 STT** (SFSpeechRecognizer) | 언어에 따라 다름. **한국어는 보통 온라인** | ✅ (온라인 의존) | ❌ 커스텀 사전 불가, 언어 1개만 | 거의 0 |
| **whisper.cpp** | ✅ 완전 로컬 | ✅ | 🟡 → 강력 (초기 프롬프트로 사전 주입) | 매우 낮음~중간 |
| **faster-whisper** | ✅ | ✅ | 🟡 | 중간 |
| **mlx-whisper** | ✅ | ✅ | 🟡 | 낮음~중간 |
| **Vosk** | ✅ | △(품질 낮음) | ❌ | 낮음 |

---

## 왜 macOS 내장 STT는 비추천인가

`SFSpeechRecognizer`는 리소스를 거의 안 쓰고 스트리밍 실시간이 가능하다는 장점이 있으나, 이 요구에 치명적 단점이 셋.

1. **"on-device"가 보장되지 않음.**
   - Apple 문서: 언어에 따라 인터넷 연결 필요, `supportsOnDeviceRecognition`으로 확인해야 함.
   - **macOS에서 한국어 on-device 인식은 일반적으로 미지원** → 한국어는 서버 기반.
   - 즉 "완전 로컬" 요구에 부합하지 않음.

2. **언어 혼용 불가.**
   - `SFSpeechRecognizer`는 **생성 시 지정한 단일 언어만** 처리.
   - 한국어 문장 속 `deploy`, `kubernetes`, `lambda`, 함수명 등 영어 기술용어가 섞이면 한 스트림에서 제대로 못 받음.

3. **커스텀 어휘/기술용어 사전이 없음.**
   - Whisper처럼 초기 프롬프트로 용어를 지정할 수단이 없어 희귀 용어·라이브러리명·식별자 오인식.
   - **URL 인식 1분 제한, 일일 사용량 제한**까지 있음.

→ 현재 자동 인식 품질은 "일반 대화 수준"이며 기술 콘텐츠 혼용엔 부적합.

---

## Whisper 계열 — 한국어 + 영어 기술용어 혼용 성능

- Whisper는 99개 언어로 훈련된 **multilingual 모델**. 코드스위칭(한·영 혼용) 처리 가능.
- **`.en` 전용 모델은 한국어 인식 불가** → 한국어는 반드시 multilingual(`large`/`medium`/`small`/`turbo`) 사용.

### 한국어 인식률 (중요)
- 한국어는 Whisper에서 **상대적으로 어려운 축**(교착어, 높은 WER). `large-v2` 기준 Fleurs 한국어 CER ~15–20%대 (영어 ~5% 대비 훨씬 높음).
- **`large-v3`에서 한국어 크게 개선** → 일반 받아쓰기 수준에선 실용적.
- 다만 종성/외래어 표기/띄어쓰기 오류는 여전히 잦음.

### 기술용어·혼용 처리
- 코드스위칭 음성은 인식하나 **한 방향으로 정규화**하려는 경향 (영어 단어 → 한글 외래어 표기 등).
- 희귀 라이브러리명·함수명·`k8s` 등은 첫 시도에 틀리기 쉬움.
- **해법: `initial_prompt`에 기술용어 사전을 넣는다.**
  - 예: `"Kubernetes, Lambda, deploy, CI/CD, 타입스크립트, 네이티브, 몽고DB ..."`
  - 모델이 해당 토큰을 더 잘 선택하게 됨. (224토큰 제한 주의)

---

## 시스템 리소스 — 다른 프로그램과 병행 가능한가

M1 Pro 기준 **on-device 실시간 변환은 충분히 가능**.

### whisper.cpp 벤치마크 (M1 Pro, CPU NEON, 30초 오디오 창당 인코딩 시간)
| 모델 | 인코딩 시간(ms) |
|------|----------------|
| tiny | ~102 |
| base | ~220 |
| small | ~685 |
| medium | ~1,928 |
| large | ~3,350 |

- 30초(30,000ms) 창 기준이므로 **전 모델 실시간보다 빠름**.
- 이는 **CPU(NEON)만** 쓴 값이고, **Metal/CoreML 가속** 시 더 빨라짐.

### 리소스 특성
- **whisper.cpp**: C/C++ 단일 구현, **런타임 제로 할당**, 양자화(Q5/Q8). CoreML 백엔드 → **ANE로 CPU 부담 최소화** → IDE·브라우저·터미널과 병행 유리. 메모리: `small` 양자화 ~1GB 미만, `large` 4–8bit ~4GB 수준.
- **mlx-whisper**: Apple MLX 프레임워크로 **M1/M2 GPU·ANE 직접 활용**, fp16/4bit 양자화. Apple Silicon 전용.
- **faster-whisper**: openai 대비 **최대 4배 빠르고 메모리 적음**(int8). 다만 Python/CTranslate2, Mac에선 CPU(Accelerate)로 동작.
- **openai/whisper(원조 PyTorch)**: 가장 느리고 메모리 큼 → M1 Pro 비추천.

### 병행 사용 실무 팁
- **실시간 연속 딕테이션 + 개발 작업**: `small` 또는 `base` — 지연·전력 부담 작음.
- **품질 우선(녹음 후 일괄 변환)**: `large-v3`(양자화) + 기술용어 프롬프트.
- GPU/ANE 사용(whisper.cpp CoreML, mlx-whisper)이 CPU 코어를 개발 툴에 남기는 데 유리.

---

## 최종 추천

1. **정답**: `whisper.cpp`(또는 `mlx-whisper`) + **`large-v3`(양자화)** + **기술용어 `initial_prompt`**. M1 Pro 실시간 가능, 한·영 기술용어 혼용 최상.
2. **가벼운 실시간 딕테이션**: `small` 모델.
3. **macOS 내장 STT**: 리소스 최소지만 한국어 on-device 아님, 혼용·기술용어 불가 → 제외.

---

## 참고 자료
- whisper.cpp (Apple Silicon 최적화, CoreML/Metal 지원, 벤치마크): https://github.com/ggml-org/whisper.cpp
- MLX 기반 Apple Silicon 전용 Whisper: https://github.com/ml-explore/mlx-examples/tree/main/whisper
- faster-whisper (CTranslate2, int8, 4배 속도): https://github.com/SYSTRAN/faster-whisper
- Apple SFSpeechRecognizer 문서: https://developer.apple.com/documentation/speech/sfspeechrecognizer
- OpenAI Whisper GitHub (모델 크기·성능, 다국어 지원): https://github.com/openai/whisper

---

## 실측 기록 (본 머신에서 직접 측정)

> 이 섹션은 `whisper.cpp`(commit `1fe009c`)를 실제 설치·빌드 후 직접 측정한 결과.
> 측정 환경: **Apple M1 Pro, macOS 26.6.1, 16GB RAM, CPU 백엔드, 8 threads** (아래 "설치 시 겪은 문제" 참고 — Metal 미사용)

### 1) 설치·빌드 요약
- `git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git` 후 `cmake -B build -DWHISPER_BUILD_TESTS=OFF && cmake --build build --config Release -j8`
- **cmake 필요** (현재 whisper.cpp Makefile은 cmake 래퍼). `brew install cmake` 로 설치.
- 생성된 바이너리: `build/bin/whisper-cli`, `whisper-bench`, `whisper-stream` 등.

### 2) 모델 다운로드 (GGML 바이너리, fp16)
| 모델 | 파일 크기 |
|------|----------|
| `base` | 147 MB |
| `small` | 487 MB |
| `medium` | 1.53 GB |
| `large-v3-turbo` | 1.62 GB |
| `large-v3` | 3.10 GB |

### 3) 벤치마크 — 속도 · 실시간 배수(RTF) · 피크 메모리
- 측정 오디오: 한국어+영어 혼용을 반복해 만든 **94.5초 WAV**
- `/usr/bin/time -l` 로 피크 RSS 측정, CPU 8 threads (`-ng -t 8`)
- **RTF = 총 처리시간 / 94.5초** (1.0 미만이면 실시간보다 빠름)

| 모델 | 파일 | 인코딩(ms/30s창) | 총 처리(ms) | **RTF** | 피크 메모리(RSS) |
|------|------|------------------|------------|---------|------------------|
| `base` | 147MB | 294 | 19,729 | **0.21** | **0.56 GB** |
| `small` | 487MB | 966 | 19,043 | **0.20** | 1.09 GB |
| `medium` | 1.53GB | 2,787 | 35,312 | **0.37** | 2.52 GB |
| `large-v3-turbo` | 1.62GB | 4,573 | 29,124 | **0.31** | 2.33 GB |
| `large-v3` | 3.10GB | 5,636 | 185,504 | **1.96** | 4.47 GB |

**해석:**
- `base`/`small`은 **실시간보다 ~5배 빠름** (0.20~0.21), 피크 메모리 1GB 미만 → 다른 개발 프로그램과 병행하며 쓰기에 부담 없음.
- `medium`/`large-v3-turbo`는 **실시간보다 ~3배 빠름** (0.31~0.37), 메모리 ~2.3~2.5GB → 실시간 딕테이션 가능.
- `large-v3`은 **CPU에서 실시간보다 2배 느림** (RTF 1.96) → 실시간엔 부적합, **비동기(녹음 후 일괄 변환)용**으로만 권장.
- 위 수치는 **CPU 전용**(Metal 비활성). Apple GPU(Metal/ANE)를 쓰면 특히 large 계열이 크게 빨라지므로 실기기에서는 더 좋아짐.

### 4) 한국어 + 영어 기술용어 혼용 인식 품질
- 테스트: TTS로 생성한 한국어+영어 혼용(개발 용어 포함) 31.5초 오디오, `-l ko` 강제, 모델별 비교.
- 원문(의도한 내용): "쿠버네티스 배포 자동화 / GitHub Action / C 파이프라인 / 프로덕션 / 디플로이 / 몽고DB 데이터베이스 마이그레이션 스크립트 / API 엔드포인트 모니터링"

| 모델 | 인식 결과 요약 |
|------|---------------|
| `small` | ❌ 커버네티스(오류), **기퍼브 액션**(영어를 한글로 로마자화), 몽고 디비, c pipeline — 기술용어 오인식 + **환각**(반복 문장 생성) |
| `medium` | ✅ 쿠버네티스, GitHub 액션, C 파이프라인, **MongoDB**, API 엔드포인트, 디플로이 — 거의 정확, 사소한 환각 |
| `large-v3-turbo` | ✅ 쿠버네티스, **GitHub Action**, **몽고DB**, C 파이프라인, API 엔드포인트 — 매우 정확, 사소한 환각 |
| `large-v3` | ✅ **Kubernetes**(영어 유지), **GitHub**, **MongoDB**, C 파이프라인, API 엔드포인트 — 최고 정확도 |

**해석:**
- 큰 모델일수록 한국어 문장에 섞인 **영어 기술용어를 정확히 유지** (small은 로마자화·오인식).
- `medium` 이상이면 개발 용어 혼용을 실용적으로 처리. `large-v3-turbo`가 **속도·품질 균형**에서 최적.
- 실사용 추천: `medium` 이상 + 기술용어 `initial_prompt` 사전으로 더 정확도 향상 가능.

### 5) 설치·사용 시 겪은 문제 (트러블슈팅 기록)
다음은 이 머신에서 실제 겪었던 이슈와 해결책 — "맥북 앱 설치가 잘 안 됐던" 경험의 원인 후보들.

1. **cmake가 없어 `make` 빌드 실패** — `make: cmake: No such file or directory`.
   → `brew install cmake` 로 해결 (현재 whisper.cpp는 cmake 기반).
2. **Metal 초기화 크래시** — 이 빌드(M1 Pro + 최신 macOS)에서 Metal 백엔드가
   `GGML_ASSERT([rsets->data count] == 0) failed` 오류로 실패.
   → `-ng`(CPU 모드) 또는 `WHISPER_METAL=OFF`로 빌드해 회피. CPU로도 충분히 실시간.
3. **불완전한 모델 파일로 크래시** — 다운로드가 중단되면 파일이 잘려
   `ERROR not all tensors loaded from model file - expected 245, got 239` 발생.
   → 다운로드 **완료를 확인**하고, 의심되면 해당 `.bin` 삭제 후 재다운로드.
4. **백그라운드 다운로드가 타임아웃에 끊김** — 툴 실행 30초 제한 때문에 대용량 모델 다운로드가 잘림.
   → `nohup bash 스크립트 & disown`으로 완전 분리 실행 후 완료 마커로 확인.
   ※ macOS에는 `setsid`가 없어 이를 쓰면 실패 (`command not found`).
5. **AIFF 직접 입력 시 빈 출력/문자 깨짐** — `say`가 만든 big-endian AIFF(22050Hz)를 그대로 넣으면
   디코딩 문제로 빈 결과 또는 `` (U+FFFD) 문자가 나옴.
   → `ffmpeg -i in.aiff -ar 16000 -ac 1 out.wav` 로 **16kHz 모노 WAV로 정규화** 후 입력하면 완벽 동작.

### 6) 실측 결론
- **속도/리소스**: 개발 툴과 병행하며 실시간 딕테이션을 쓴다면 `base`~`medium·turbo` 모두 충분.
  16GB M1 Pro에서 `large-v3-turbo`는 RTF 0.31, 피크 메모리 2.3GB로 실시간 OK.
- **정확도(한·영 기술용어)**: `medium` 이상에서 실용적. 최고는 `large-v3`(+`Kubernetes`/`MongoDB` 영어 유지).
- **균형 추천**: `large-v3-turbo` + 기술용어 `initial_prompt`. 실시간 가능 + 품질 최상급.
  정확도에 여유가 있으면(비동기 처리) `large-v3` 사용.
