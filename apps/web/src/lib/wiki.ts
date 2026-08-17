import { getCollection, type CollectionEntry } from 'astro:content';

import { DOMAINS, TYPES } from '../content.config';
import { extractWikilinks } from './wikilink.mjs';

export type Doc = CollectionEntry<'wiki'>;

export const DOMAIN_LABELS: Record<(typeof DOMAINS)[number], string> = {
  ai: 'AI',
  dev: '개발',
  career: '커리어',
  product: '프로덕트',
  infra: '인프라',
  misc: '기타',
};

export const TYPE_LABELS: Record<(typeof TYPES)[number], string> = {
  synthesis: '종합',
  concept: '개념',
  entity: '엔티티',
  source: '소스 요약',
  note: '노트',
};

/** 목록에 노출하는 타입 순서. index.md 의 카테고리 순서와 맞춘다. */
export const TYPE_ORDER = ['synthesis', 'concept', 'entity', 'source', 'note'] as const;

/**
 * **모든 페이지는 이 함수로만 문서를 가져온다.**
 *
 * public 필터를 라우트마다 반복하면 언젠가 한 군데를 빠뜨린다.
 * 여기 한 곳만 지키면 목록·상세·태그·그래프·검색 인덱스가 한꺼번에 안전해진다.
 */
export async function getPublicDocs(): Promise<Doc[]> {
  const docs = await getCollection('wiki', ({ data }) => data.visibility === 'public');
  return docs.sort(byUpdatedDesc);
}

export function byUpdatedDesc(a: Doc, b: Doc): number {
  const diff = b.data.updated.getTime() - a.data.updated.getTime();
  return diff !== 0 ? diff : a.data.title.localeCompare(b.data.title, 'ko');
}

export function groupByType(docs: Doc[]): { type: string; label: string; docs: Doc[] }[] {
  return TYPE_ORDER.map((type) => ({
    type,
    label: TYPE_LABELS[type],
    docs: docs.filter((doc) => doc.data.type === type),
  })).filter((group) => group.docs.length > 0);
}

export function countBy(docs: Doc[], key: 'domains' | 'tags'): Map<string, number> {
  const counts = new Map<string, number>();
  for (const doc of docs) {
    for (const value of doc.data[key]) {
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
  }
  return new Map([...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])));
}

export function formatDate(date: Date): string {
  // 빌드 머신의 타임존에 따라 하루가 밀리지 않도록 UTC로 고정한다.
  return date.toISOString().slice(0, 10);
}

/** 엣지가 어디서 나왔는지. 화면에서 실선(link)과 점선(tag)으로 구분한다. */
export type GraphEdgeKind = 'link' | 'tag';

export interface GraphNode {
  id: string;
  title: string;
  type: string;
  domains: string[];
  /** 인접 엣지 수. 노드 크기와 고아 판정에 쓴다. */
  degree: number;
  /** ego 그래프에서 중심 문서 표시. 전역 그래프에는 없다. */
  focus?: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: GraphEdgeKind;
  /** 공유 태그 수. link 엣지도 태그가 겹치면 1보다 커진다. */
  weight: number;
  /** 두 문서가 공유하는 태그. 툴팁에 쓴다. */
  tags: string[];
}

export interface Graph {
  nodes: GraphNode[];
  links: GraphEdge[];
}

/**
 * 이보다 많은 문서에 붙은 태그는 **관계가 아니라 분류**로 보고 엣지를 만들지 않는다.
 *
 * 태그는 열린 어휘라 상한이 없으면 엣지 수가 문서 수의 제곱으로 자란다 — 태그
 * 하나를 n개 문서가 공유하면 그 태그만으로 n(n-1)/2 개다. `#llm` 이 문서 20건에
 * 붙으면 그 태그 하나가 190개 엣지를 뿜고 그래프는 태그 덩어리로 뭉개진다.
 *
 * 8이면 한 태그가 만드는 엣지가 최대 28개로 묶인다. 위키가 커져서 이 상한에 자주
 * 걸리기 시작하면 숫자를 올리는 게 아니라 "공유 태그 2개 이상일 때만 연결" 쪽으로
 * 규칙을 바꾸는 것이 맞다.
 */
export const TAG_EDGE_MAX_DOCS = 8;

/** `related:` 는 `"[[slug]]"` 형태로 저장된다. */
function stripBrackets(value: string): string {
  return value.replace(/^\[\[|\]\]$/g, '').trim();
}

/** 방향 없는 쌍의 정규화된 키. `a→b` 와 `b→a` 를 같은 엣지로 본다. */
function pairKey(a: string, b: string): string {
  return a < b ? `${a} ${b}` : `${b} ${a}`;
}

/**
 * public 문서 사이의 연결 그래프.
 *
 * 엣지는 두 종류다:
 * - `link` — 본문 `[[wikilink]]` 와 frontmatter `related`. 사람이 직접 이은 것.
 * - `tag` — 태그를 공유하는 문서끼리. 명시적 연결은 아니지만 주제가 겹친다는 신호.
 *
 * 합치지 않고 구분해 내보내는 이유: 링크는 저자의 의도고 태그는 추론이라 같은
 * 무게로 보여주면 안 된다. 화면에서 태그 엣지만 끄는 것도 가능해야 한다.
 *
 * 대상이 public 문서가 아니면 엣지를 버린다. private 문서 제목이 노드 라벨로 새는
 * 것이 그래프의 대표적인 누출 경로다.
 */
export function buildGraph(docs: Doc[]): Graph {
  const publicSlugs = new Set(docs.map((doc) => doc.id));

  const nodes: GraphNode[] = docs.map((doc) => ({
    id: doc.id,
    title: doc.data.title,
    type: doc.data.type,
    domains: doc.data.domains,
    degree: 0,
  }));
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  // 1) 쌍마다 공유 태그를 먼저 모은다. link 엣지에도 붙여야 하므로 태그 계산이 앞선다.
  const docsByTag = new Map<string, string[]>();
  for (const doc of docs) {
    for (const tag of doc.data.tags) {
      const list = docsByTag.get(tag);
      if (list) list.push(doc.id);
      else docsByTag.set(tag, [doc.id]);
    }
  }

  const sharedTags = new Map<string, string[]>();
  for (const [tag, ids] of docsByTag) {
    if (ids.length < 2 || ids.length > TAG_EDGE_MAX_DOCS) continue;
    for (let i = 0; i < ids.length; i += 1) {
      for (let j = i + 1; j < ids.length; j += 1) {
        const key = pairKey(ids[i], ids[j]);
        const list = sharedTags.get(key);
        if (list) list.push(tag);
        else sharedTags.set(key, [tag]);
      }
    }
  }

  // 2) link 엣지. 태그도 겹치면 그 정보를 여기에 흡수하고 tag 엣지는 만들지 않는다
  //    — 같은 쌍에 선이 두 개 그려지는 것을 막는다.
  const links: GraphEdge[] = [];
  const claimed = new Set<string>();

  for (const doc of docs) {
    const targets = new Set([
      ...extractWikilinks(doc.body ?? ''),
      ...doc.data.related.map(stripBrackets),
    ]);

    for (const target of targets) {
      if (target === doc.id || !publicSlugs.has(target)) continue;
      const key = pairKey(doc.id, target);
      if (claimed.has(key)) continue;
      claimed.add(key);

      const tags = sharedTags.get(key) ?? [];
      links.push({ source: doc.id, target, kind: 'link', weight: 1 + tags.length, tags });
    }
  }

  // 3) 남은 쌍에서 tag 엣지.
  for (const [key, tags] of sharedTags) {
    if (claimed.has(key)) continue;
    const [source, target] = key.split(' ');
    links.push({ source, target, kind: 'tag', weight: tags.length, tags });
  }

  for (const link of links) {
    nodeById.get(link.source)!.degree += 1;
    nodeById.get(link.target)!.degree += 1;
  }

  return { nodes, links };
}

/**
 * 한 문서와 그 이웃만 남긴 depth 1 부분 그래프.
 *
 * 이웃 사이의 엣지도 포함한다 — "내 이웃끼리도 서로 아는가" 가 ego 그래프에서 가장
 * 읽을 만한 정보다. 별 모양이면 이 문서가 유일한 연결점이고, 삼각형이 보이면 이미
 * 서로 엮인 주제 덩어리다.
 *
 * 데이터가 작아서(이웃 수 + 1 노드) 페이지 HTML 에 인라인해도 부담이 없다. 문서마다
 * JSON 파일을 따로 내면 요청 수와 파일 수만 늘고 총량은 그대로다.
 */
export function egoGraph(slug: string, graph: Graph): Graph {
  const neighbours = new Set<string>([slug]);
  for (const link of graph.links) {
    if (link.source === slug) neighbours.add(link.target);
    else if (link.target === slug) neighbours.add(link.source);
  }

  const links = graph.links.filter(
    (link) => neighbours.has(link.source) && neighbours.has(link.target),
  );

  // degree 는 부분 그래프 안에서 다시 센다. 전역 degree 를 그대로 쓰면 화면에 선이
  // 2개인 노드가 8개짜리 크기로 그려진다.
  const nodes: GraphNode[] = graph.nodes
    .filter((node) => neighbours.has(node.id))
    .map((node) => ({ ...node, degree: 0, focus: node.id === slug }));
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  for (const link of links) {
    nodeById.get(link.source)!.degree += 1;
    nodeById.get(link.target)!.degree += 1;
  }

  return { nodes, links };
}

/**
 * 이 문서와 이어진 다른 public 문서들. 그래프의 목록 버전.
 *
 * 이미 만들어둔 그래프를 받는다 — 문서마다 `buildGraph()` 를 다시 돌리면 빌드가
 * O(문서수²) 가 된다.
 */
export function neighboursOf(
  slug: string,
  graph: Graph,
  docs: Doc[],
): { doc: Doc; kind: GraphEdgeKind; tags: string[] }[] {
  const edgeTo = new Map<string, GraphEdge>();
  for (const link of graph.links) {
    const other =
      link.source === slug ? link.target : link.target === slug ? link.source : null;
    if (other === null) continue;
    if (edgeTo.get(other)?.kind !== 'link') edgeTo.set(other, link);
  }

  return docs
    .filter((doc) => edgeTo.has(doc.id))
    .map((doc) => {
      const edge = edgeTo.get(doc.id)!;
      return { doc, kind: edge.kind, tags: edge.tags };
    })
    // 직접 이은 링크를 태그로만 이어진 문서보다 위에 둔다.
    .sort((a, b) => {
      const rank = (kind: GraphEdgeKind) => (kind === 'link' ? 0 : 1);
      return rank(a.kind) - rank(b.kind) || byUpdatedDesc(a.doc, b.doc);
    });
}
