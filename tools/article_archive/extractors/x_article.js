// Read an X Article from a browser that already holds an X session.
//
// Why this exists at all: an X Article (x.com/i/article/<id>) is a different
// content type from a tweet.  fxtwitter's tweet endpoint returns an empty body
// for it, and the page shows a login wall to logged-out clients, so there is
// no keyless path to the text.
//
// Why it talks raw CDP instead of using Playwright: `connectOverCDP` attaches
// to *every* target, and once you are signed in x.com registers a service
// worker and a shared worker that hang that handshake indefinitely (measured:
// a 120s timeout was not enough).  Attaching straight to one page target skips
// target discovery, and never trips the `debugger;` traps the login flow uses
// to freeze attached debuggers either.
//
//   node x_article.js <cdp-port> <url> [timeout-ms]
//
// Prints one JSON object on stdout: {ok, url, title, text, error}.
const WebSocket = require('ws');
const http = require('http');

const PORT = Number(process.argv[2] || 0);
const TARGET_URL = process.argv[3] || '';
const TIMEOUT = Number(process.argv[4] || 60000);

const fail = (msg) => {
  process.stdout.write(JSON.stringify({ ok: false, error: String(msg).slice(0, 300) }));
  process.exit(0);
};

const request = (path, method = 'GET') => new Promise((resolve, reject) => {
  const req = http.request(
    { host: '127.0.0.1', port: PORT, path, method, timeout: 10000 },
    (res) => {
      let body = '';
      res.on('data', (c) => (body += c));
      res.on('end', () => {
        try { resolve(JSON.parse(body)); } catch (e) { reject(e); }
      });
    },
  );
  req.on('error', reject);
  req.on('timeout', () => req.destroy(new Error('CDP HTTP timeout')));
  req.end();
});
const getJson = (path) => request(path, 'GET');

// The page body, minus the chrome X wraps around it.
const EXTRACT = `(() => {
  const drop = /^(To view keyboard shortcuts|View keyboard shortcuts|Skip to|Don.t miss what|Something went wrong)/i;
  const text = (document.body.innerText || '')
    .split('\\n')
    .filter((l) => !drop.test(l.trim()))
    .join('\\n')
    .trim();
  const wall = /Continue with (phone|Google|Apple)|Sign in to X|Happening now/i.test(text.slice(0, 400));
  const heading = document.querySelector('h1, [data-testid="twitterArticleTitle"]');
  return JSON.stringify({
    url: location.href,
    title: (heading && heading.innerText.trim()) || document.title || '',
    text: text,
    wall: wall,
  });
})()`;

(async () => {
  if (!PORT || !TARGET_URL) fail('usage: x_article.js <port> <url> [timeout-ms]');

  // A freshly launched headless browser often has no page target yet, and
  // /json/new is the documented way to open one (PUT since Chrome 111).
  let page = null;
  for (let attempt = 0; attempt < 12 && !page; attempt++) {
    const targets = await getJson('/json/list');
    page = targets.find((t) => t.type === 'page' && t.webSocketDebuggerUrl) || null;
    if (page) break;
    try {
      const made = await request('/json/new?about:blank', 'PUT');
      if (made && made.webSocketDebuggerUrl) page = made;
    } catch { /* fall through to the retry below */ }
    if (!page) await new Promise((r) => setTimeout(r, 700));
  }
  if (!page) fail('no page target on the CDP port');

  const ws = new WebSocket(page.webSocketDebuggerUrl, { perMessageDeflate: false });
  let seq = 0;
  const pending = new Map();

  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error(method + ' timed out')); }
    }, TIMEOUT);
  });

  ws.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    }
  });

  await new Promise((resolve, reject) => {
    ws.on('open', resolve);
    ws.on('error', reject);
    setTimeout(() => reject(new Error('websocket open timed out')), TIMEOUT);
  });

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.navigate', { url: TARGET_URL });

  // X renders the article client-side; poll until the body stops growing
  // rather than guessing a fixed wait.
  let last = -1;
  let info = null;
  for (let i = 0; i < 12; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    const out = await send('Runtime.evaluate', { expression: EXTRACT, returnByValue: true });
    info = JSON.parse(out.result.value);
    if (info.text.length > 400 && info.text.length === last) break;
    last = info.text.length;
  }

  ws.close();
  if (!info) fail('no response from the page');
  if (info.wall && info.text.length < 400) {
    fail('the browser profile is not signed in to X');
  }
  process.stdout.write(JSON.stringify({
    ok: true, url: info.url, title: info.title, text: info.text,
  }));
})().catch((e) => fail(e && e.message ? e.message : e));
