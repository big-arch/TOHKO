// Only this public, maintained snapshot is fetched. Never accept a user URL.
export const KNOWLEDGE_URL = 'https://big-arch.github.io/TOHKO/data/assistant-knowledge.json';
export const KNOWLEDGE_LIMITS = Object.freeze({ ttlMs: 12 * 60 * 1000, retryMs: 2 * 60 * 1000, timeoutMs: 3500, bytes: 2 * 1024 * 1024, documents: 2500 });
const PAGES = new Set(['guide.html', 'atlas.html', 'nylon.html', 'men.html', 'read-product-card.html', 'packaging.html', 'lookbook.html', 'textures.html', 'leggings.html', 'videos.html', 'brand.html', 'brands.html', 'news.html', 'journal.html']);
const KINDS = new Set(['guide', 'brand', 'model', 'package', 'news']);
const INTENTS = new Set(['size', 'den', 'care', 'material', 'style', 'catalog', 'medical', 'news']);
const CORE_IDS = ['guide-choice', 'guide-den', 'guide-size', 'guide-medical'];
const ID = /^[a-z0-9][a-z0-9-]{0,100}$/;

function text(value, maximum, optional = false) {
  if (value === undefined && optional) return undefined;
  if (typeof value !== 'string' || !value.trim() || value.length > maximum || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(value)) throw new Error('invalid_knowledge_text');
  return value.trim();
}

function strings(value, maximum, allowed) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > 80) throw new Error('invalid_knowledge_list');
  return value.map(v => { const clean = text(v, maximum); if (allowed && !allowed.has(clean)) throw new Error('invalid_knowledge_tag'); return clean; });
}

function publicHref(value) {
  const href = text(value, 700);
  if (!/^[a-z0-9-]+\.html(?:[?#].*)?$/.test(href) || /[\s<>\\]/.test(href)) throw new Error('invalid_knowledge_href');
  const url = new URL(href, KNOWLEDGE_URL.replace('data/assistant-knowledge.json', ''));
  if (url.origin !== 'https://big-arch.github.io' || !PAGES.has(url.pathname.replace('/TOHKO/', '')) || !url.pathname.startsWith('/TOHKO/')) throw new Error('invalid_knowledge_href');
  return href;
}

export function validateKnowledge(data) {
  if (!data || data.version !== 1 || !Array.isArray(data.documents) || data.documents.length < CORE_IDS.length || data.documents.length > KNOWLEDGE_LIMITS.documents) throw new Error('invalid_knowledge');
  if (typeof data.contentHash !== 'string' || !/^[a-f0-9]{64}$/.test(data.contentHash)) throw new Error('invalid_knowledge_hash');
  const ids = new Set();
  const documents = data.documents.map(item => {
    if (!item || typeof item !== 'object' || typeof item.id !== 'string' || !ID.test(item.id) || ids.has(item.id) || !KINDS.has(item.kind)) throw new Error('invalid_knowledge_document');
    ids.add(item.id);
    const clean = { id: item.id, kind: item.kind, title: text(item.title, 220), text: text(item.text, 4000), href: publicHref(item.href),
      intents: strings(item.intents, 30, INTENTS), keywords: strings(item.keywords, 220), aliases: strings(item.aliases, 120) };
    for (const field of ['brand', 'brandKey']) { const value = text(item[field], 120, true); if (value !== undefined) clean[field] = value; }
    if (item.den !== undefined) {
      if (item.den !== null && (!Number.isInteger(item.den) || item.den < 0 || item.den > 2000)) throw new Error('invalid_knowledge_den');
      clean.den = item.den;
    }
    if (item.kind === 'news') {
      if (typeof item.publishedAt !== 'string' || !/^\d{4}-\d{2}-\d{2}T/.test(item.publishedAt) || !Number.isFinite(Date.parse(item.publishedAt))) throw new Error('invalid_knowledge_date');
      clean.publishedAt = item.publishedAt;
    }
    // Unknown object fields are discarded. Content remains untrusted prompt data.
    return clean;
  });
  if (CORE_IDS.some(id => !ids.has(id))) throw new Error('missing_core_knowledge');
  return { version: 1, contentHash: data.contentHash, documents };
}

async function readSnapshot(response, signal) {
  if (!response.ok || !/^application\/json(?:\s*;|$)/i.test(response.headers.get('content-type') || '')) throw new Error('knowledge_unavailable');
  if (Number(response.headers.get('content-length') || 0) > KNOWLEDGE_LIMITS.bytes || !response.body) throw new Error('knowledge_too_large');
  const reader = response.body.getReader(); const parts = []; let size = 0;
  const abort = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener('abort', abort, { once: true });
  try {
    while (true) {
      if (signal.aborted) throw new Error('knowledge_timeout');
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > KNOWLEDGE_LIMITS.bytes) { await reader.cancel(); throw new Error('knowledge_too_large'); }
      parts.push(value);
    }
    if (signal.aborted) throw new Error('knowledge_timeout');
    const bytes = new Uint8Array(size); let offset = 0;
    for (const part of parts) { bytes.set(part, offset); offset += part.byteLength; }
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
  } finally { signal.removeEventListener('abort', abort); reader.releaseLock(); }
}

/** One loader instance per Edge isolate: shared snapshot, retry window and Promise. */
export function createKnowledgeLoader({ embedded, fetcher = fetch, now = Date.now, timeoutMs = KNOWLEDGE_LIMITS.timeoutMs } = {}) {
  let lastGood = validateKnowledge(embedded);
  let nextAttemptAt = 0;
  let inFlight = null;
  return function loadKnowledge() {
    if (inFlight) return inFlight;
    if (now() < nextAttemptAt) return Promise.resolve(lastGood);
    inFlight = (async () => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await fetcher(KNOWLEDGE_URL, { method: 'GET', redirect: 'error', credentials: 'omit', cache: 'no-cache', headers: { Accept: 'application/json' }, signal: controller.signal });
        lastGood = validateKnowledge(await readSnapshot(response, controller.signal));
        nextAttemptAt = now() + KNOWLEDGE_LIMITS.ttlMs;
      } catch {
        // No secret/log output; retain the last validated or bundled snapshot.
        controller.abort();
        nextAttemptAt = now() + KNOWLEDGE_LIMITS.retryMs;
      } finally { clearTimeout(timeout); }
      return lastGood;
    })().finally(() => { inFlight = null; });
    return inFlight;
  };
}
