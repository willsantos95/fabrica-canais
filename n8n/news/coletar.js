// Lê os feeds RSS do canal e devolve as notícias recentes (uma lista só, para gravar de uma vez).
const c = $('Canal').first().json;
const cfg = typeof c.config === 'string' ? JSON.parse(c.config) : c.config;
const news = cfg.news || {};
const maxAgeMs = (news.max_age_hours || 18) * 3600e3;
const now = Date.now();

const dec = s => String(s || '')
  .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
  .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ')
  .replace(/\s+/g, ' ').trim();
const tag = (x, t) => {
  const m = x.match(new RegExp('<' + t + '(?:\\s[^>]*)?>([\\s\\S]*?)</' + t + '>', 'i'));
  return m ? dec(m[1]) : '';
};
const link = x => {
  const l = tag(x, 'link');
  if (l) return l;
  const m = x.match(/<link[^>]*href="([^"]+)"/i);
  return m ? m[1] : '';
};
// fora disso não é notícia para Short
const JUNK = /onde assistir|bonus code|bônus|odds|aposta|bet(mgm|365|ano)|cartola|fantasy|melhores momentos|ao vivo:|live:|podcast|newsletter/i;

const out = [];
const errors = [];
for (const f of news.feeds || []) {
  try {
    const xml = await this.helpers.httpRequest({ url: f.url, timeout: 20000, headers: { 'User-Agent': 'Mozilla/5.0 (LanceRapido news reader)' } });
    const items = String(xml).match(/<(item|entry)[\s>][\s\S]*?<\/(item|entry)>/gi) || [];
    for (const x of items.slice(0, 40)) {
      const title = tag(x, 'title');
      const url = link(x);
      const date = Date.parse(tag(x, 'pubDate') || tag(x, 'updated') || tag(x, 'published') || tag(x, 'dc:date'));
      if (!title || !url || !date || now - date > maxAgeMs || JUNK.test(title)) continue;
      out.push({ url, title: title.slice(0, 300), summary: (tag(x, 'description') || tag(x, 'summary')).slice(0, 600),
        source: f.source, sport: f.sport, published_at: new Date(date).toISOString() });
    }
  } catch (e) {
    errors.push(`${f.source} ${f.sport}: ${String(e.message).slice(0, 80)}`);
  }
}
if (!out.length) return [];
return [{ json: { channel_id: c.id, items: JSON.stringify(out), n: out.length, errors } }];
