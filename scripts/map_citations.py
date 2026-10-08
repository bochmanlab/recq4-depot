"""Map review-draft citations to depot protein pages by section (and sentence-level organism mentions).
Usage: python3 scripts/map_citations.py draft.txt curation/citation_map.json
Output: {"proteins": {slug: {topic: [ref numbers]}}, "family": {topic: [ref numbers]}}"""
import re, sys, json
def cites(text):
    out=[]
    for g in re.findall(r'\(([\d,–—\-\s]+)\)',text):
        for part in g.split(','):
            part=part.strip()
            m=re.match(r'^(\d+)\s*[–—-]\s*(\d+)$',part)
            if m: out+=list(range(int(m.group(1)),int(m.group(2))+1))
            elif part.isdigit(): out.append(int(part))
    return [c for c in out if 1<=c<=400]
def main(path,outp):
    L=open(path).read().split('\n')
    s=next(i for i,l in enumerate(L) if l.startswith('1. '))
    toc_end=next(i for i,l in enumerate(L) if l.strip()=='SUMMARY' and i>100)
    body=L[toc_end:s]
    # headings (level by hand: ALLCAPS = section; others = subsection)
    head_idx=[]
    for i,l in enumerate(body):
        t=l.strip()
        if t and len(t)<110 and not t.endswith('.') and not re.search(r'\(\d',t) and (t.isupper() or i in ()):
            head_idx.append((i,t,'sec'))
    # subsections known from the TOC
    toc=[l.rsplit(' ',1)[0].strip() for l in L[:toc_end] if re.search(r' \d+$',l)]
    subs=set(toc)|{'Inter-strand crosslink repair','Hrq1 at RNA polymerase III-transcribed loci'}
    ALIAS={'Inter-strand crosslink repair':'Inter-strand crosslink (ICL) repair','Hrq1 at RNA polymerase III-transcribed loci':'RNA polymerase III-transcribed loci'}
    heads=[]; 
    for i,l in enumerate(body):
        t=l.strip()
        if t in subs and t!='TABLE OF CONTENTS': heads.append((i,t))
    result={'proteins':{}, 'family':{}}
    def add(dst,topic,nums):
        d=dst.setdefault(topic,[])
        for n in nums:
            if n not in d: d.append(n)
    def prot(slug,topic,nums): add(result['proteins'].setdefault(slug,{}),topic,nums)
    cur_sec=None; cur_sub=None
    for i,l in enumerate(body):
        t=l.strip()
        if t in subs:
            if t.isupper(): cur_sec=t; cur_sub=None
            else: cur_sub=ALIAS.get(t,t)
            continue
        if not t or cur_sec is None: continue
        sec=cur_sec
        if sec.startswith(('PROKARYOTIC','FUNGAL','PLANT')):
            # keep only citations from sentences that name the protein (or directly follow one that does)
            keep=[]; prev=False
            for sent in re.split(r'(?<=[.)])\s+(?=[A-Z])',t):
                hit=bool(re.search(r'Hrq1|HRQ1|SftH|MrfA',sent))
                if hit or prev: keep+=cites(sent)
                prev=hit
            nums=keep
        else:
            nums=cites(t)
        if not nums: continue
        sec=cur_sec; sub=cur_sub or ('Overview' if sec.startswith(('RECQ4-FAMILY HELICASES IN METAZOANS','FUNGAL','PLANT','PROKARYOTIC')) else sec.title())
        if sec.startswith('PROKARYOTIC'):
            if sub.startswith('Mycobacterium'): prot('sfth-msmegmatis',sub,nums)
            elif sub.startswith('Bacillus'): prot('mrfa-bsubtilis',sub,nums)
            else: add(result['family'],sub,nums)
        elif sec.startswith('FUNGAL'):
            if sub.startswith('Schizosaccharomyces'): prot('hrq1-spombe','Fission yeast Hrq1',nums)
            elif sub in ('Saccharomyces cerevisiae Hrq1','Fungal Recq4-family helicases'.upper(),'FUNGAL RECQ4-FAMILY HELICASES'): prot('hrq1-scerevisiae','Overview',nums)
            else: prot('hrq1-scerevisiae',sub,nums)
        elif sec.startswith('PLANT'):
            prot('hrq1-athaliana','Plant HRQ1',nums)
        elif sec.startswith('RECQ4-FAMILY HELICASES IN METAZOANS'):
            keep=[]; prev=False
            for sent in re.split(r'(?<=[.)])\s+(?=[A-Z])',t):
                hit=bool(re.search(r'RECQL4|RecQ4|Recql4|RECQ4|RecQL4',sent)) and not re.search(r'Hrq1|HRQ1|Pif1|cerevisiae|yeast|archae|bacteri|prokaryot|YprA|MrfA|SftH|E\. coli|Escherichia',sent)
                if hit: keep+=cites(sent)
            if keep: prot('recql4-human',sub,keep)
        else:  # intro, history, domains, biochemistry, synthesis
            add(result['family'],f"{sec.title()} — {sub}" if cur_sub else sec.title(),nums)
    # Organism-specific assignments checked by hand against the cited papers (sentence-level matching was too noisy).
    result['proteins'].pop('recq4-xenopus',None); result['proteins'].pop('recq4-drosophila',None)
    prot('recql4-mouse','Mouse models',[73,75])
    prot('recq4-xenopus','Egg-extract replication studies',[43,78,79,80])
    prot('recq4-drosophila','Drosophila RecQ4 genetics',[181,182,183])
    json.dump(result,open(outp,'w'),indent=1)
    for k,v in result['proteins'].items(): print(k,{t:len(n) for t,n in v.items()})
    print('family',{t:len(n) for t,n in result['family'].items()})
main(sys.argv[1],sys.argv[2])
