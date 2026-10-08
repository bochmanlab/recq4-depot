"""Merge resolved references and the citation map into data/curated_refs.json (used by build_site.py).
Usage: python3 scripts/curate_merge.py curation/refs_resolved.json curation/citation_map.json data/curated_refs.json"""
import json, sys, re
def short_auth(a):
    names=[x.strip() for x in re.split(r',\s*(?=[A-Z][A-Za-z\-\']+ [A-Z]{1,3}\b)',a) if x.strip()]
    if len(names)>3: return names[0]+" et al."
    return ", ".join(names)
def entry(n,refs):
    r=refs.get(str(n))
    if not r: return None
    m=r.get('match')
    e={'n':n,'authors':short_auth(r.get('authors','')) if r.get('authors') else '','year':r.get('year'),
       'title':(m or {}).get('pm_title') or r.get('title') or r['raw'],'journal':(m or {}).get('journal'),
       'pmid':(m or {}).get('pmid'),'doi':r.get('doi')}
    if not m: e['raw']=r['raw']
    return e
# The review draft's citation numbers do not always line up with its reference list, so a paper is kept for a protein only if
# its title names the protein/family or it is in the hand-checked ALLOW list (reference numbers verified against the paper).
RELEVANT={
 'recql4-human':r'RECQL4|RecQ4|RECQ4|RecQL4|Rothmund|RAPADILINO|Baller|DONSON|osteosarcoma|RecQ protein-like 4|RecQ-like helicase 4',
 'hrq1-scerevisiae':r'Hrq1|HRQ1|RecQ4|RECQL4','hrq1-spombe':r'Hrq1|HRQ1|RecQ4','hrq1-athaliana':r'Hrq1|HRQ1|Arabidopsis|RecQ4-homologous',
 'mrfa-bsubtilis':r'MrfA','sfth-msmegmatis':r'SftH','recql4-mouse':r'.','recq4-xenopus':r'.','recq4-drosophila':r'.'}
EXCLUDE={'recql4-human':r'Drosophila|dRecQ4|Hrq1|yeast|cerevisiae'}
ALLOW={'hrq1-scerevisiae':{49},'mrfa-bsubtilis':{26,29},'sfth-msmegmatis':{25}}
def keep(slug,e):
    import re
    if e['n'] in ALLOW.get(slug,()): return True
    if re.search(EXCLUDE.get(slug,r'(?!x)x'),e['title'],re.I): return False
    return bool(re.search(RELEVANT.get(slug,'.'),e['title'],re.I))
def main(rp,cp,op):
    refs=json.load(open(rp)); cm=json.load(open(cp)); out={'proteins':{},'family':[]}
    for slug,topics in cm['proteins'].items():
        out['proteins'][slug]=[g for g in ({'topic':t,'items':[e for e in (entry(n,refs) for n in nums) if e and keep(slug,e)]} for t,nums in topics.items()) if g['items']]
    seen=set()
    for t,nums in cm['family'].items():
        items=[e for e in (entry(n,refs) for n in nums) if e]
        out['family'].append({'topic':t,'items':items})
    json.dump(out,open(op,'w'),indent=1)
    tot=sum(len(g['items']) for v in out['proteins'].values() for g in v)
    unres=sum(1 for v in out['proteins'].values() for g in v for e in g['items'] if not e['pmid'])
    print('protein entries',tot,'unresolved',unres)
main(*sys.argv[1:4])
