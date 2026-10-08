"""Parse the numbered reference list from a review draft and resolve each entry to a PubMed ID.
Usage: python3 scripts/resolve_refs.py draft.txt curation/refs_resolved.json
Matching: first-author surname + year + title words via PubMed ESearch, then a fuzzy title check on ESummary.
Unresolved entries are kept (with DOI if present) for manual review."""
import re, sys, json, time, difflib, urllib.request, urllib.parse
EU="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
def get(url):
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(url,timeout=40))
        except Exception as e:
            time.sleep(1.5*(i+1))
    return None
def parse(path):
    L=open(path).read().split('\n')
    s=next(i for i,l in enumerate(L) if l.startswith('1. '))
    out={}
    for l in L[s:]:
        m=re.match(r'^(\d+)\. (.*)$',l)
        if not m: continue
        n=int(m.group(1)); t=m.group(2)
        y=re.search(r'\b((?:19|20)\d\d)\. ',t)
        if not y: out[n]={'raw':t}; continue
        authors=t[:y.start()].strip(' .')
        rest=t[y.end():]
        title=re.split(r'\. (?=[A-Z])',rest,1)[0]
        doi=re.search(r'doi:?\s*(10\.\S+)',t)
        out[n]={'raw':t,'authors':authors,'year':y.group(1),'title':title,'first':re.split(r'[ ,]',authors)[0],
                'doi':doi.group(1).rstrip('.') if doi else None}
    return out
def norm(s): return re.sub(r'[^a-z0-9 ]','',s.lower())
def resolve(r):
    if 'title' not in r: return None
    words=[w for w in norm(r['title']).split() if len(w)>3][:8]
    q=f"{r['first']}[1au] AND {r['year']}[dp] AND ("+" AND ".join(w+"[tiab]" for w in words[:5])+")"
    for attempt in (q, f"{r['first']}[1au] AND {r['year']}[dp] AND ("+" AND ".join(w+"[tiab]" for w in words[:2])+")"):
        j=get(EU+"esearch.fcgi?db=pubmed&retmode=json&retmax=5&term="+urllib.parse.quote(attempt)); time.sleep(0.4)
        ids=(j or {}).get('esearchresult',{}).get('idlist',[])
        if not ids: continue
        s=get(EU+"esummary.fcgi?db=pubmed&retmode=json&id="+",".join(ids)); time.sleep(0.4)
        best=None
        for i in ids:
            d=(s or {}).get('result',{}).get(i)
            if not d: continue
            sc=difflib.SequenceMatcher(None,norm(d['title']),norm(r['title'])).ratio()
            if best is None or sc>best[0]: best=(sc,i,d)
        if best and best[0]>=0.8:
            return {'pmid':best[1],'score':round(best[0],2),'pm_title':best[2]['title'],'journal':best[2].get('source'),'year':(best[2].get('pubdate') or '')[:4]}
    return None
if __name__=="__main__":
    refs=parse(sys.argv[1]); res={}
    for n,r in sorted(refs.items()):
        m=resolve(r); res[n]={**{k:v for k,v in r.items() if k!='raw'},'raw':r['raw'],'match':m}
        print(n,'OK' if m else 'MISS',flush=True)
    json.dump(res,open(sys.argv[2],'w'),indent=1)
