from __future__ import annotations

import html, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE='https://figure-online.net'
SALE=BASE+'/collections/sale'
OUT=Path('site')
TARGETS=['AURALEE','COMOLI','Graphpaper','A.PRESSE','marka','DAIWA PIER39','ATON','UNDERCOVER','FACETASM','White Mountaineering','beautiful people','JUNYA WATANABE MAN','Hender Scheme','visvim','WTAPS','nonnative']
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; DomesticSaleMVP/0.1; +https://github.com/musaonowaka/domestic-sale-site)'}
YEN=re.compile(r'¥\s*([0-9,]+)')

def clean(s): return ' '.join((s or '').split())
def esc(s): return html.escape(str(s or ''))
def money(n): return f'¥{n:,}'

def brand_for(text):
    low=text.casefold()
    for b in TARGETS:
        if b.casefold() in low: return b
    return None

def parse_card(card):
    text=clean(card.get_text(' ',strip=True))
    brand=brand_for(text)
    if not brand: return None
    prices=[int(x.replace(',','')) for x in YEN.findall(text)]
    if len(prices)<2: return None
    sale=min(prices[0],prices[1]); original=max(prices[0],prices[1])
    if not original or sale>=original: return None
    link=card.select_one('a[href*="/products/"]')
    if not link: return None
    href=urljoin(BASE,link.get('href',''))
    title=clean(link.get('title') or link.get_text(' ',strip=True))
    if not title or len(title)<4:
        title=text
    # Keep a compact useful title when the card text contains lots of UI labels.
    title=re.sub(r'\s*¥\s*[0-9,]+.*$','',title).strip()
    discount=round((1-sale/original)*100)
    sold=bool(re.search(r'\bSOLD\b|SOLD OUT|売り切れ|在庫なし',text,re.I))
    return {'brand':brand,'title':title,'sale':sale,'original':original,'discount':discount,'url':href,'sold':sold}

def fetch():
    session=requests.Session(); session.headers.update(HEADERS)
    found={}
    for page in range(1,31):
        r=session.get(SALE,params={'page':page},timeout=25); r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        cards=soup.select('.product-item,.product-card,.grid-product,.productgrid--item,li[class*="product"],div[class*="product-item"]')
        if not cards:
            links=soup.select('a[href*="/products/"]')
            cards=[]
            seen=set()
            for a in links:
                p=a
                for _ in range(5):
                    p=p.parent
                    if not p: break
                    if len(YEN.findall(clean(p.get_text(' ',strip=True))))>=2: break
                if p and id(p) not in seen:
                    seen.add(id(p)); cards.append(p)
        before=len(found)
        for c in cards:
            item=parse_card(c)
            if item: found[item['url']]=item
        if page>1 and len(found)==before: break
        time.sleep(1.2)
    return list(found.values())

def build(items):
    OUT.mkdir(exist_ok=True); (OUT/'.nojekyll').write_text('',encoding='utf-8')
    items=sorted(items,key=lambda x:(x['sold'], -x['discount'], x['sale']))
    brands=sorted({x['brand'] for x in items},key=str.casefold)
    chips=''.join(f'<button class="chip" data-brand="{esc(b)}">{esc(b)}</button>' for b in brands)
    cards=[]
    for x in items:
        state='<span class="sold">SOLD</span>' if x['sold'] else '<span class="stock">SALE</span>'
        cards.append(f'''<article class="card" data-search="{esc((x['brand']+' '+x['title']).casefold())}" data-brand="{esc(x['brand'])}"><div class="topline"><b>{esc(x['brand'])}</b>{state}</div><h2>{esc(x['title'])}</h2><div class="prices"><strong>{money(x['sale'])}</strong><del>{money(x['original'])}</del><em>{x['discount']}%OFF</em></div><a href="{esc(x['url'])}" target="_blank" rel="noopener sponsored">FIGURE ONLINEで見る →</a></article>''')
    now=datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M')
    doc=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DOMESTIC SALE</title><meta name="description" content="ドメスティックブランドのセール価格をまとめて検索"><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f5f3;color:#111;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}header{{background:#111;color:#fff;padding:18px 0}}.wrap{{width:min(1100px,calc(100% - 30px));margin:auto}}header b{{font-size:20px}}.hero{{padding:48px 0 22px}}h1{{font-size:clamp(36px,7vw,68px);letter-spacing:-.055em;line-height:1;margin:0 0 16px}}.lead{{color:#666;line-height:1.7}}input{{width:100%;padding:15px 16px;border:1px solid #ddd;border-radius:12px;font-size:16px;background:#fff;margin:18px 0 12px}}.chips{{display:flex;gap:7px;flex-wrap:wrap}}.chip{{border:1px solid #ddd;background:#fff;padding:8px 11px;border-radius:999px;cursor:pointer}}.chip.active{{background:#111;color:#fff}}.meta{{font-size:12px;color:#777;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:13px;padding-bottom:50px}}.card{{background:#fff;border:1px solid #e4e4e0;border-radius:15px;padding:18px}}.topline{{display:flex;justify-content:space-between;font-size:12px}}.card h2{{font-size:17px;line-height:1.45;min-height:49px}}.prices{{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin:15px 0}}.prices strong{{font-size:25px}}del{{color:#999}}em{{font-style:normal;color:#087747;font-weight:800}}.card a{{display:block;background:#111;color:#fff;text-decoration:none;text-align:center;padding:11px;border-radius:9px;font-weight:700;font-size:13px}}.stock{{color:#087747}}.sold{{color:#999}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><header><div class="wrap"><b>DOMESTIC SALE</b></div></header><main class="wrap"><section class="hero"><h1>ドメブラのセールを、<br>1か所で。</h1><p class="lead">国内ブランドのSALE商品をまとめて検索。まずはFIGURE ONLINEから自動更新する公開MVPです。</p><input id="q" placeholder="Graphpaper / marka / 商品名…"><div class="chips"><button class="chip active" data-brand="">すべて</button>{chips}</div><p class="meta">{len(items)}件 ・ {len(brands)}ブランド ・ 最終生成 {esc(now)}</p></section><section class="grid" id="grid">{''.join(cards)}</section></main><script>
let brand='';const q=document.getElementById('q');function filter(){{let s=q.value.trim().toLowerCase();document.querySelectorAll('.card').forEach(c=>c.style.display=(!s||c.dataset.search.includes(s))&&(!brand||c.dataset.brand===brand)?'block':'none')}}q.oninput=filter;document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));b.classList.add('active');brand=b.dataset.brand;filter()}});
</script></body></html>'''
    (OUT/'index.html').write_text(doc,encoding='utf-8')

if __name__=='__main__':
    items=fetch()
    if not items: raise SystemExit('No sale items parsed; keeping previous deployment is safer.')
    build(items)
    print(f'built {len(items)} live sale items')
