// @ts-check
import { defineConfig } from 'astro/config';
import cloudflare from '@astrojs/cloudflare';
import { satteri } from '@astrojs/markdown-satteri';

import { wikilinkPlugin } from './src/lib/wikilink-plugin.mjs';

// https://astro.build/config
// workers.dev 서브도메인은 계정마다 다르고 커스텀 도메인도 아직 없다.
// 배포 환경에서 SITE_URL 을 주고, 없으면 상대 경로만 쓰는 로컬 기본값으로 둔다.
const site = process.env.SITE_URL || 'https://llm-wiki.workers.dev';

export default defineConfig({
  site,
  adapter: cloudflare({
    // 콘텐츠가 앱 바깥(repo 루트 `wiki/`)에 있어서 prerender 중에 파일시스템을 읽는다.
    // 기본값인 workerd 에는 `node:fs` 가 없어 정적 경로 생성 단계에서 죽는다.
    prerenderEnvironment: 'node',
    // 어댑터 기본값은 Cloudflare Images 바인딩이다. 붙일 이미지가 아직 없고,
    // 바인딩이 하나 늘면 배포에 프로비저닝할 리소스가 하나 늘어난다.
    imageService: 'compile',
  }),
  // 세션을 끄면 어댑터가 KV 바인딩을 요구하지 않는다. Phase 1은 전부 정적이라
  // 세션을 쓸 곳이 없고, 비용 목표가 $0 이라 프로비저닝할 리소스를 남기지 않는다.
  // Phase 2 인증은 KV 없이 HMAC 서명 쿠키로 가기로 되어 있다.
  session: false,
  // Phase 1은 public 문서만 다루므로 전부 정적 산출한다.
  // Phase 2에서 private 문서를 붙일 때 그 라우트에만 `prerender = false` 를 건다
  // — Workers Static Assets는 Worker보다 먼저 응답하므로, prerender된 파일은
  //   라우트 핸들러에 인증을 넣어도 URL만 알면 받아진다.
  output: 'static',
  markdown: {
    processor: satteri({ mdastPlugins: [wikilinkPlugin()] }),
    shikiConfig: { themes: { light: 'github-light', dark: 'github-dark' } },
  },
});
