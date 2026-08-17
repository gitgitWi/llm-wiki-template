import type { APIRoute } from 'astro';

import { buildGraph, getPublicDocs } from '../lib/wiki';

/**
 * 그래프 뷰가 fetch하는 데이터. **public 노드만 들어간다.**
 *
 * 정적 파일이라 URL만 알면 누구나 받는다 — 라벨에 private 문서 제목이 섞이면
 * 문서 페이지를 아무리 막아도 제목은 이미 공개된 것이다.
 */
export const GET: APIRoute = async () => {
  const graph = buildGraph(await getPublicDocs());

  return new Response(JSON.stringify(graph), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
