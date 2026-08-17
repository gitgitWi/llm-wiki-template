import type { APIRoute } from 'astro';

import { DOMAINS } from '../content.config';
import { countBy, getPublicDocs } from '../lib/wiki';

/**
 * sitemap은 필터 누락 단골이라 손으로 쓴다.
 * `getPublicDocs()` 하나만 통과시키면 private 문서가 들어올 자리가 없다.
 */
export const GET: APIRoute = async ({ site }) => {
  const base = (site ?? new URL('http://localhost/')).origin;
  const docs = await getPublicDocs();
  const tags = [...countBy(docs, 'tags').keys()];

  const entries = [
    { loc: '/', lastmod: docs[0]?.data.updated },
    { loc: '/wiki/', lastmod: docs[0]?.data.updated },
    { loc: '/graph', lastmod: docs[0]?.data.updated },
    { loc: '/search', lastmod: undefined },
    ...DOMAINS.map((domain) => ({ loc: `/domains/${domain}`, lastmod: undefined })),
    ...tags.map((tag) => ({ loc: `/tags/${encodeURIComponent(tag)}`, lastmod: undefined })),
    ...docs.map((doc) => ({ loc: `/wiki/${doc.id}`, lastmod: doc.data.updated })),
  ];

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries
  .map(
    ({ loc, lastmod }) =>
      `  <url><loc>${base}${loc}</loc>${
        lastmod ? `<lastmod>${lastmod.toISOString().slice(0, 10)}</lastmod>` : ''
      }</url>`,
  )
  .join('\n')}
</urlset>
`;

  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
