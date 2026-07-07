import json, urllib.request, io, os
from PIL import Image, ImageFilter
from collections import deque

cat = json.load(open('catalog_full.json'))
by_handle = {c['handle']: c for c in cat}
OUT = '/Users/gimmymusone/SETUP/💼 Lavoro/.tmp/scroll-journey/caveau/bottles'
os.makedirs(OUT, exist_ok=True)

FEATURED = ['absolu-aventus-millesime-50-ml-spray','kirke-extrait-de-parfum-100-ml','black-phantom-50-ml',
  'hacivat-extrait-de-parfum-100-ml','layton-edp-125-ml','oud-for-greatness-eau-deparfum-90-ml',
  'cap-camarat-eau-de-parfum','molecule-01-mandarin-eau-de-toilette-100-ml']
SHELF = ['bois-1920-durocaffe-extrait-50-ml','bleu-infini-eau-de-toilette-50-ml',
  'exotic-chocolate-extrait-de-parfum','exclusive-eternal-sunrise-edpc',
  'botanicae-expression-en-route-eau-de-parfum-100-ml','saffron-mandarin-100-ml',
  'iperborea-eau-de-toilette-50-ml-spray','n-89-e-d-t-100-ml-spray',
  'absolute-shadow-extrait-de-parfum','the-chronic-extrait-rouge-extreme',
  'royal-sapphire-extrait','lineam','venom-incarnat-eau-de-parfum','faisa-eau-de-parfum',
  'nicocello-extrait','verde-respiro-100-ml','unique-blue-extrait-de-parfum','pure-diamond-eau-de-parfum',
  'saaqi-eau-de-parfum','moroccan-medjool-pure-parfum','5-elixir-eau-de-parfum','mada-extrait-de-parfum',
  'sweet-pulp-extrait-de-parfum','kite-in-crystal-reef-parfum-nectar','wave-of-freedom-eau-de-parfum',
  'delox-extrait-de-parfum-100-ml','maremosso-eau-de-parfum-100-ml','golden-oud-eau-de-parfum-100-ml-1',
  'onyx-100-ml','plumbeo-extrait-de-parfum','dominus-extrait-de-parfum','familiar-strangers-parfum-75-ml']

def fetch(url, width=460):
    u = url.split('&width=')[0] + ('&' if '?' in url.split('&width=')[0] else '?') + f'width={width}'
    d = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0'}), timeout=20).read()
    return Image.open(io.BytesIO(d)).convert('RGB')

def key(img, aggressive):
    w, h = img.size
    px = img.load()
    bs = [px[x,0] for x in range(w)]+[px[x,h-1] for x in range(w)]+[px[0,y] for y in range(h)]+[px[w-1,y] for y in range(h)]
    lows = [p for p in bs if max(p)-min(p) < 30] or bs
    bg = tuple(sum(c[i] for c in lows)//len(lows) for i in range(3))
    def floodable(p):
        r,g,b = p
        sat = max(r,g,b)-min(r,g,b); lum = (r+g+b)/3
        dist = max(abs(r-bg[0]),abs(g-bg[1]),abs(b-bg[2]))
        if aggressive: return (dist < 26) or (sat < 46 and lum > 128 and dist < 95)
        return dist < 22 and sat < 24
    mark = bytearray(w*h); dq = deque()
    def seed(x,y):
        i = y*w+x
        if not mark[i] and floodable(px[x,y]): mark[i]=1; dq.append(i)
    for x in range(w): seed(x,0); seed(x,h-1)
    for y in range(h): seed(0,y); seed(w-1,y)
    while dq:
        i = dq.popleft(); x,y = i%w, i//w
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=nx<w and 0<=ny<h:
                j = ny*w+nx
                if not mark[j] and floodable(px[nx,ny]): mark[j]=1; dq.append(j)
    # components, keep >=10% of largest
    comp = [0]*(w*h); n = 0; sizes = {}
    for i in range(w*h):
        if mark[i] or comp[i]: continue
        n += 1; q = deque([i]); comp[i] = n; s = 0
        while q:
            k = q.popleft(); s += 1; x,y = k%w, k//w
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<w and 0<=ny<h:
                    j = ny*w+nx
                    if not mark[j] and not comp[j]: comp[j]=n; q.append(j)
        sizes[n] = s
    if not sizes: return None, 0
    big = max(sizes.values()); keepset = {c for c,s in sizes.items() if s >= big*0.10}
    alpha = bytearray(255 if (not mark[i] and comp[i] in keepset) else 0 for i in range(w*h))
    # defringe
    thr = (222,32) if aggressive else (235,22)
    for _ in range(2):
        cut = []
        for i in range(w*h):
            if not alpha[i]: continue
            x,y = i%w, i//w
            if any(not(0<=nx<w and 0<=ny<h) or not alpha[ny*w+nx] for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))):
                r,g,b = px[x,y]
                if (r+g+b)/3 > thr[0] and max(r,g,b)-min(r,g,b) < thr[1]: cut.append(i)
        for i in cut: alpha[i] = 0
    kept = sum(1 for a in alpha if a)/(w*h)
    out = Image.new('RGBA',(w,h),(0,0,0,0)); op = out.load()
    for i in range(w*h):
        if alpha[i]: x,y = i%w,i//w; op[x,y] = px[x,y]+(255,)
    return out, kept

def best_cutout(img):
    ag, ka = key(img, True)
    co, kc = key(img, False)
    # aggressive wins unless it destroyed the bottle vs conservative
    if ag is not None and ka >= 0.06 and ka >= 0.55*kc: return ag, 'aggr', ka
    return co, 'cons', kc

def bake_shadow(cut):
    # crop to content, pad, soft drop shadow
    bbox = cut.getbbox()
    cut = cut.crop(bbox)
    pad = 30
    W, H = cut.size[0]+pad*2, cut.size[1]+pad*2
    base = Image.new('RGBA',(W,H),(0,0,0,0))
    sh = Image.new('RGBA',(W,H),(0,0,0,0))
    mask = cut.split()[3].point(lambda a: int(a*0.55))
    black = Image.new('RGBA',cut.size,(12,9,4,255))
    sh.paste(black,(pad,pad+10),mask)
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    base = Image.alpha_composite(base, sh)
    img2 = Image.new('RGBA',(W,H),(0,0,0,0)); img2.paste(cut,(pad,pad),cut)
    return Image.alpha_composite(base, img2)

if __name__ == '__main__':
    report = []
    for hnd in FEATURED + SHELF:
        img = fetch(by_handle[hnd]['img'])
        cut, mode, kept = best_cutout(img)
        if cut is None or kept < 0.03:
            report.append((hnd, mode, kept, 'FAILED')); continue
        final = bake_shadow(cut)
        final.save(f'{OUT}/{hnd}.png')
        report.append((hnd, mode, kept, 'ok'))
        print(f"{'FEAT' if hnd in FEATURED else 'shelf'} {hnd[:44]:46} {mode} kept={kept:.2f}", flush=True)
    fails = [r for r in report if r[3]=='FAILED']
    print('FAILED:', fails if fails else 'none')
