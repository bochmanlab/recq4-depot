#!/usr/bin/env python3
"""Build the static RecQ4 depot site from data/*.json (produced by fetch_data.py).

    python3 scripts/fetch_data.py   # refresh data from public sources
    python3 scripts/build_site.py   # regenerate HTML

No dependencies beyond the Python standard library.
"""
import html, json, os, re, urllib.parse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
_cp = os.path.join(DATA, "curated_refs.json")
CURATED = json.load(open(_cp)) if os.path.exists(_cp) else {}
LAB_URL = "https://bochmanlab.github.io"
GROUP_LABEL = {"PTHR13710:SF108": "ATP-dependent DNA helicase Q4", "PTHR47957": "ATP-dependent helicase HRQ1"}
E = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def load():
    meta = json.load(open(os.path.join(DATA, "_meta.json")))
    recs = [json.load(open(os.path.join(DATA, f"{a}.json"))) for a in meta["proteins"]]
    return meta, recs


def fmt_date(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%B %-d, %Y")
    except Exception:
        return iso


def org_html(name):
    m = re.match(r"^(.*?)\s*(\(strain.*\))?$", name)
    return f"<i>{E(m.group(1))}</i>" + (f" {E(m.group(2))}" if m.group(2) else "")


def pm_links(text):
    t = E(text)
    return re.sub(r"PubMed:(\d+)", r'<a href="https://pubmed.ncbi.nlm.nih.gov/\1/">PubMed:\1</a>', t)


def shell(title, body, active, depth=0, extra_head="", extra_foot="", meta=None):
    p = "../" * depth
    nav = [("index.html", "Proteins", "home"), ("family.html", "Family overview", "family"), ("about.html", "About &amp; sources", "about")]
    items = "".join(f'<li><a href="{p}{h}"{" aria-current=page" if k == active else ""}>{l}</a></li>' for h, l, k in nav)
    stamp = f"Data last refreshed {fmt_date(meta['fetched'])}. " if meta else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<link rel="stylesheet" href="{p}assets/style.css">
<link rel="icon" href="{p}assets/favicon.ico">{extra_head}
</head><body>
<div class="proto">Prototype &mdash; {len(meta["proteins"]) if meta else ""} proteins so far. Content is assembled automatically from public databases and has not been fully curated.</div>
<header class="site"><div class="wrap row">
<a class="brand" href="{p}index.html">RecQ4 <span>Family Depot</span></a>
<nav aria-label="Primary"><ul>{items}<li><a href="{LAB_URL}">Bochman Lab &nearr;</a></li></ul></nav>
</div></header>
{body}
<footer><div class="wrap">{stamp}Sources: UniProt, AlphaFold DB, PDB, IntAct, SGD, ClinVar, PubMed &mdash; see <a href="{p}about.html">About &amp; sources</a>. A project of the <a href="{LAB_URL}">Bochman Lab</a>, Indiana University Bloomington.</div></footer>
{extra_foot}
</body></html>"""


# ---------- domain map (SVG) ----------
def short(n):
    m = re.search(r"\(([A-Za-z0-9]{2,5})\)\s*$", n)
    if m and not n.startswith("Helicase"):
        return m.group(1)
    return (n.replace("Helicase ATP-binding", "ATP-binding").replace("Helicase C-terminal", "C-terminal helicase")
             .replace("Oligonucleotide/oligosaccharide-binding", "OB").replace("MrfA Zn(2+)-binding", "Zn-binding")
             .replace("N-terminal region", "N-term").replace("Winged-helix", "WH"))


def domain_map(u, ref_len=None, width=1000):
    L = u["length"]; R = ref_len or L
    sx = lambda pos: 10 + (pos / R) * (width - 20)
    f = u["features"]; h = 100
    out = [f'<svg class="map" viewBox="0 0 {width} {h}" role="img" aria-label="Domain map of {E(u["entry"])}">']
    out.append(f'<rect x="10" y="40" width="{sx(L)-10:.1f}" height="8" rx="4" fill="var(--line)"/>')
    for r in f["regions"]:
        if r["name"] == "Disordered":
            out.append(f'<rect x="{sx(r["start"]):.1f}" y="38" width="{sx(r["end"])-sx(r["start"]):.1f}" height="12" rx="3" fill="var(--dom-other)" opacity=".35"/>')
    seg_y = 56
    for r in f["regions"]:
        if r["name"] != "Disordered" and len(r["name"]) <= 42:
            x, w = sx(r["start"]), sx(r["end"]) - sx(r["start"])
            out.append(f'<rect x="{x:.1f}" y="{seg_y}" width="{w:.1f}" height="14" rx="3" fill="var(--dom-other)" opacity=".55"><title>{E(r["name"])} ({r["start"]}–{r["end"]})</title></rect>')
            if w > 22:
                out.append(f'<text x="{x+w/2:.1f}" y="{seg_y+25}" text-anchor="middle">{E(short(r["name"]))}</text>')
    for d in f["domains"]:
        x, w = sx(d["start"]), sx(d["end"]) - sx(d["start"])
        col = "var(--dom-atp)" if "ATP" in d["name"] else "var(--dom-ct)" if "C-terminal" in d["name"] else "var(--dom-extra)"
        out.append(f'<rect x="{x:.1f}" y="26" width="{w:.1f}" height="36" rx="5" fill="{col}"><title>{E(d["name"])} ({d["start"]}–{d["end"]})</title></rect>')
        base = short(d["name"])
        for lab in (base, base.replace("C-terminal helicase", "C-term"), base.replace("C-terminal helicase", "CT"), ""):
            if lab and w >= len(lab) * 6.6 + 10:
                out.append(f'<text x="{x+w/2:.1f}" y="48" text-anchor="middle" style="fill:#fff;font-weight:600">{E(lab)}</text>')
                break
    for m in f["motifs"]:
        x = sx((m["start"] + m["end"]) / 2)
        out.append(f'<line x1="{x:.1f}" y1="14" x2="{x:.1f}" y2="26" stroke="var(--dom-motif)" stroke-width="2"/><text x="{x:.1f}" y="10" text-anchor="middle" style="fill:var(--dom-motif);font-weight:700">{E(m["name"].replace(" box",""))}</text>')
    for tick in (1, L):
        out.append(f'<text x="{sx(tick):.1f}" y="{h-2}" text-anchor="{"start" if tick==1 else "end"}">{tick}</text>')
    out.append("</svg>")
    return "".join(out)


LEGEND = ('<div class="legend"><span><i style="background:var(--dom-atp)"></i>ATP-binding helicase domain</span>'
          '<span><i style="background:var(--dom-ct)"></i>C-terminal helicase domain</span>'
          '<span><i style="background:var(--dom-extra)"></i>other domains</span>'
          '<span><i style="background:var(--dom-other);opacity:.6"></i>other annotated regions</span>'
          '<span><i style="background:var(--dom-other);opacity:.3"></i>predicted disordered</span>'
          '<span><i style="background:var(--dom-motif)"></i>DEAH motif</span></div>')


# ---------- protein page ----------
def tbl(head, rows, cls="scroll"):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="{cls}"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def fasta(u):
    seq = u["sequence"]
    head = f">sp|{u['accession']}|{u['entry']} {u['name']} OS={u['organism']} OX={u['taxid']}"
    return head + "\n" + "\n".join(seq[i:i + 60] for i in range(0, len(seq), 60))


def curated_html(groups):
    """Render curated reference groups (topic -> items). Items without a PMID link out via DOI or show plain text."""
    h = ""
    seen = set()
    for g in groups:
        items = [e for e in g["items"] if e["n"] not in seen]
        if not items: continue
        h += f'<h3>{E(g["topic"])}</h3><ul class="lit">'
        for e in items:
            seen.add(e["n"])
            if e.get("pmid"):
                t = f'<a href="https://pubmed.ncbi.nlm.nih.gov/{e["pmid"]}/">{E(e["title"])}</a>'
                m = f'{E(e["authors"])} &middot; <i>{E(e["journal"] or "")}</i> {E(e["year"] or "")} &middot; PMID {e["pmid"]}'
            elif e.get("doi"):
                t = f'<a href="https://doi.org/{E(e["doi"])}">{E(e["title"])}</a>'; m = f'{E(e["authors"])} &middot; {E(e["year"] or "")} &middot; DOI {E(e["doi"])}'
            else:
                t = E(e["title"]); m = f'{E(e["authors"])} &middot; {E(e["year"] or "")} &middot; not indexed in PubMed or not matched'
            h += f'<li><div class="t">{t}</div><div class="m">{m}</div></li>'
        h += "</ul>"
    return h


def protein_page(r, meta):
    u = r["uniprot_data"]; c = u["comments"]; f = u["features"]; af = r.get("alphafold") or {}
    acc = u["accession"]; secs = []; toc = []

    def sec(id_, title, content):
        toc.append(f'<a href="#{id_}">{title}</a>')
        secs.append(f'<section id="{id_}"><h2>{title}</h2>{content}</section>')

    # facts
    cof = ", ".join(c.get("COFACTOR", [])) or "—"
    facts = [(f"{u['length']:,} aa", "Length"), (f"{u['mass']/1000:.1f} kDa", "Mass"),
             (", ".join(u["ec"]) or "—", "EC number"),
             (f"{af.get('globalMetricValue', 0):.0f}" if af else "—", "AlphaFold mean pLDDT"),
             (cof, "Cofactors"), ("; ".join(c.get("SUBCELLULAR LOCATION", [])) or "—", "Location")]
    fx = "".join(f'<div class="fact"><b>{E(a)}</b><span>{E(b)}</span></div>' for a, b in facts)

    # summary / function
    fn = "".join(f"<p>{pm_links(t)}.</p>" if not t.endswith(".") else f"<p>{pm_links(t)}</p>" for t in c.get("FUNCTION", [])) \
        or '<p class="empty">No function annotation yet in UniProt.</p>'
    extra = ""
    for k, lab in (("CATALYTIC ACTIVITY", "Catalytic activity"), ("SUBUNIT", "Subunit / complex"), ("DOMAIN", "Domain notes"),
                   ("INDUCTION", "Induction"), ("TISSUE SPECIFICITY", "Tissue specificity"),
                   ("DISRUPTION PHENOTYPE", "Disruption phenotype"), ("SIMILARITY", "Family"), ("MISCELLANEOUS", "Miscellaneous")):
        if c.get(k):
            extra += f"<tr><th style='position:static;width:190px'>{lab}</th><td>{'<br>'.join(pm_links(x) for x in c[k])}</td></tr>"
    sec("function", "Function", fn + f'<div class="scroll" style="max-height:none"><table>{extra}</table></div>'
        + '<p class="mono-label" style="font-size:.8rem;color:var(--ink-soft)">'
        + ("Text from UniProt/Swiss-Prot curation." if u["reviewed"] else "Automatic annotation from UniProt (TrEMBL), not manually reviewed.") + "</p>")

    # features
    sec("domains", "Domains &amp; features", domain_map(u) + LEGEND + (
        "" if not f["binding"] else "<p>" + f"{len(f['binding'])} annotated ligand-binding sites: " +
        "; ".join(f"{E(b['ligand'])} ({b['start']}{'–'+str(b['end']) if b['end']!=b['start'] else ''})" for b in f["binding"][:10]) + ".</p>")
        + ("<p>InterPro: " + ", ".join(f'<a href="https://www.ebi.ac.uk/interpro/entry/InterPro/{i["id"]}/">{E(i["name"] or i["id"])}</a>' for i in u["interpro"]) + "</p>" if u["interpro"] else ""))

    # sequence
    fa = fasta(u)
    sec("sequence", "Sequence",
        f'<pre class="fasta" id="fasta">{E(fa)}</pre><button onclick="cp()">Copy FASTA</button> '
        f'<button class="ghost" onclick="dl()">Download .fasta</button>'
        f'<script>function cp(){{var e=document.getElementById("fasta");function sel(){{var r=document.createRange();r.selectNodeContents(e);var g=getSelection();g.removeAllRanges();g.addRange(r);}}try{{navigator.clipboard.writeText(e.textContent).catch(sel)}}catch(x){{sel()}}}}function dl(){{var b=new Blob([document.getElementById("fasta").textContent+"\\n"],{{type:"text/plain"}});var a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="{acc}.fasta";a.click();}}</script>'
        f'<p>UniProt <a href="https://www.uniprot.org/uniprotkb/{acc}">{acc}</a> &middot; entry {E(u["entry"])} &middot; protein evidence: {E(u["existence"])}'
        + (f' &middot; RefSeq: {", ".join(E(x) for x in u["refseq"][:3])}' if u["refseq"] else "") + "</p>")

    # structure
    st = ""
    if af:
        fr = [(af["fractionPlddtVeryHigh"], "#0053d6", "very high (&gt;90)"), (af["fractionPlddtConfident"], "#65cbf3", "confident (70–90)"),
              (af["fractionPlddtLow"], "#ffdb13", "low (50–70)"), (af["fractionPlddtVeryLow"], "#ff7d45", "very low (&lt;50)")]
        bar = "".join(f'<div style="width:{v*100:.1f}%;background:{col}" title="{lab}: {v*100:.0f}%"></div>' for v, col, lab in fr)
        lg = '<div class="legend">' + "".join(f'<span><i style="background:{col}"></i>{lab}: {v*100:.0f}%</span>' for v, col, lab in fr) + "</div>"
        st += (f'<div id="viewer"><p class="empty" style="padding:1rem" id="vmsg">Loading 3D model…</p></div>'
               f'<p style="font-size:.88rem;color:var(--ink-soft)">AlphaFold prediction ({E(af["entryId"])}), colored by per-residue confidence (pLDDT). Drag to rotate, scroll to zoom.</p>'
               f'<div class="plddt">{bar}</div>{lg}'
               f'<p><a class="btn ghost" href="https://alphafold.ebi.ac.uk/entry/{acc}">Open in AlphaFold DB</a> '
               f'<a class="btn ghost" href="../data/models/{acc}.pdb" download>Download model (PDB)</a></p>')
    if not af:
        st += '<p class="empty">AlphaFold DB has no predicted model for this entry.</p>'
    if u["pdb"]:
        st += "<h3>Experimental structures</h3>" + tbl(["PDB", "Method", "Resolution", "Chains"], [
            [f'<a href="https://www.rcsb.org/structure/{p["id"]}">{p["id"]}</a>', E(p["method"]), E(p["res"]), E(p["chains"])] for p in u["pdb"]], "scroll")
    else:
        st += '<p class="empty">No experimental structures deposited in the PDB for this protein.</p>'
    sec("structure", "Structure", st)

    # alleles / variants
    av = ""
    sd = r.get("sgd_data")
    if sd:
        al = {}
        for ph in sd["phenotypes"]:
            for a in ph["alleles"]:
                x = al.setdefault(a, {"phen": [], "pm": set(), "n": 0}); x["n"] += 1
                x["phen"].append(ph["phenotype"]);
                if ph["pmid"]: x["pm"].add(ph["pmid"])
        rows = []
        for a, x in sorted(al.items(), key=lambda kv: -kv[1]["n"]):
            uniq = sorted(set(x["phen"]))
            rows.append([f"<b>{E(a)}</b>", str(x["n"]), E("; ".join(uniq[:6]) + (f"; +{len(uniq)-6} more" if len(uniq) > 6 else "")),
                         ", ".join(f'<a href="https://pubmed.ncbi.nlm.nih.gov/{p}/">{p}</a>' for p in sorted(x["pm"])[:5])])
        av += "<h3>Alleles with annotated phenotypes (SGD)</h3>" + (tbl(["Allele", "Phenotype annotations", "Phenotypes observed", "References (PMID)"], rows) if rows else '<p class="empty">None.</p>')
    if f["variants"]:
        av += "<h3>Natural variants (UniProt)</h3>" + tbl(["Position", "Change", "Annotation"], [
            [str(v["pos"]), E(f'{v["orig"]}→{v["alt"]}'), pm_links(v["desc"])] for v in f["variants"]])
    if f["mutagenesis"]:
        av += "<h3>Engineered mutations (UniProt mutagenesis)</h3>" + tbl(["Position", "Change", "Effect"], [
            [str(m["pos"]), E(m["change"].replace(">", "→")) if m["change"].strip(">") else "deletion / truncation", pm_links(m["desc"])] for m in f["mutagenesis"]])
    cv = r.get("clinvar")
    if cv:
        tot = cv["total"] or 1
        segs = [("pathogenic", "#b3261e", "Pathogenic"), ("likely_pathogenic", "#e46962", "Likely pathogenic"), ("vus", "#9aa8b4", "Uncertain significance"),
                ("likely_benign", "#7fb77e", "Likely benign"), ("benign", "#2e7d32", "Benign")]
        bar = "".join(f'<div style="width:{cv[k]/tot*100:.2f}%;background:{col}" title="{lab}: {cv[k]:,}"></div>' for k, col, lab in segs)
        lg = '<div class="legend">' + "".join(f'<span><i style="background:{col}"></i>{lab}: {cv[k]:,}</span>' for k, col, lab in segs) + "</div>"
        av += (f'<h3>ClinVar submissions for {E(r["gene"])}</h3><div class="bar">{bar}</div>{lg}'
               f'<p>{cv["total"]:,} ClinVar records in total (other classifications not shown). '
               f'<a href="https://www.ncbi.nlm.nih.gov/clinvar/?term={urllib.parse.quote(r["gene"])}%5Bgene%5D">Browse in ClinVar</a>.</p>')
    if not av:
        av = '<p class="empty">No allele or variant data available yet.</p>'
    sec("alleles", "Alleles &amp; variants", av)

    # disease
    if c.get("DISEASE"):
        dh = "".join(f'<div class="note"><b>{E(d["name"])}</b>{" ("+E(d["acronym"])+")" if d.get("acronym") else ""}'
                     f'{" &middot; <a href=https://www.omim.org/entry/"+E(d["mim"])+">OMIM "+E(d["mim"])+"</a>" if d.get("mim") else ""}<br>{pm_links(d.get("desc"))}</div>' for d in c["DISEASE"])
        sec("disease", "Disease associations", dh + '<p style="font-size:.88rem;color:var(--ink-soft)">From UniProt; see ClinVar above for variant-level data.</p>')

    # interactions
    ih = ""
    if sd:
        ph_ = sd["physical"]
        ih += (f'<p><b>{len(ph_)}</b> physical interactors and <b>{sd["genetic_count"]:,}</b> genetic interactors are annotated in SGD '
               f'(many from high-throughput screens). <a href="https://www.yeastgenome.org/locus/{sd["sgdid"]}/interaction">View all at SGD</a>.</p>')
        ih += "<h3>Physical interactions (SGD)</h3>" + tbl(["Partner", "Systematic name", "Evidence"], [
            [f'<a href="https://www.yeastgenome.org/locus/{p["sgdid"]}">{E(p["name"])}</a>', E(p["systematic"]), E(", ".join(p["experiments"]))] for p in ph_])
    ia = r["interactions_intact"]
    if ia["partners"]:
        ih += (f"<h3>Interactions in IntAct</h3><p>{ia['total']} binary interaction records involving {len(ia['partners'])} distinct partners "
               f'(top {min(60,len(ia["partners"]))} by confidence score shown). <a href="https://www.ebi.ac.uk/intact/search?query={acc}">View all at IntAct</a>. Records can include isoforms and partners from other species.</p>'
               + tbl(["Partner", "UniProt", "Detection methods", "MI score"], [
                   [E(p["name"]), f'<a href="https://www.uniprot.org/uniprotkb/{p["uniprot"]}">{E(p["uniprot"])}</a>', E("; ".join(p["methods"][:3])), f'{p["score"]:.2f}'] for p in ia["partners"][:60]]))
    elif not sd:
        ih += '<p class="empty">No curated interactions found in IntAct for this protein.</p>'
    if c.get("SUBUNIT"):
        ih += "<h3>Described in UniProt</h3><p>" + "<br>".join(pm_links(x) for x in c["SUBUNIT"]) + "</p>"
    sec("interactions", "Interactions", ih)

    # phenotypes
    if sd and sd["phenotypes"]:
        sec("phenotypes", "Phenotypes (yeast)", tbl(["Phenotype", "Allele / mutant", "Condition", "Reference"], [
            [E(p["phenotype"]), E(", ".join(p["alleles"]) or p["mutant_type"] or "—"), E(", ".join(p["chemicals"]) or "—"),
             f'<a href="https://pubmed.ncbi.nlm.nih.gov/{p["pmid"]}/">{E(p["reference"])}</a>' if p["pmid"] else E(p["reference"])]
            for p in sd["phenotypes"]]) + f'<p style="font-size:.88rem;color:var(--ink-soft)">From SGD phenotype annotations. <a href="https://www.yeastgenome.org/locus/{sd["sgdid"]}/phenotype">See SGD</a>.</p>')

    # GO
    if u["go"]:
        groups = {"F": "Molecular function", "P": "Biological process", "C": "Cellular component"}
        gh = '<div class="cols">'
        for k, lab in groups.items():
            ts = sorted({g["term"][2:] for g in u["go"] if g["term"].startswith(k + ":")})
            if ts: gh += f"<div><h3>{lab}</h3><ul>" + "".join(f"<li>{E(t)}</li>" for t in ts) + "</ul></div>"
        sec("go", "Gene Ontology", gh + "</div>")

    # curated key papers
    cur = CURATED.get("proteins", {}).get(r["slug"])
    if cur:
        n_cur = len({e["n"] for g in cur for e in g["items"]})
        sec("keypapers", "Key papers", f'<p>{n_cur} papers curated by the lab, grouped by the topic under which each is discussed. A paper can be relevant beyond its group. The automatic PubMed search under Literature is separate.</p>' + curated_html(cur))

    # literature
    lit = r["literature"]
    pq = urllib.parse.quote(lit["query"])
    lh = (f'<p><b>{lit["count"]}</b> PubMed records match the saved search <code>{E(lit["query"])}</code>; the {len(lit["papers"])} most recent are shown. '
          f'<a href="https://pubmed.ncbi.nlm.nih.gov/?term={pq}">Open in PubMed</a>.</p>'
          '<div class="note warn">Prototype caveat: this list comes from an automatic keyword search and can include off-topic papers or miss relevant ones.</div><ul class="lit">')
    for p in lit["papers"]:
        lh += (f'<li><div class="t"><a href="https://pubmed.ncbi.nlm.nih.gov/{p["pmid"]}/">{E(p["title"])}</a></div>'
               f'<div class="m">{E(", ".join(p["authors"]))} &middot; <i>{E(p["journal"])}</i> {E(p["year"])} &middot; PMID {p["pmid"]}</div></li>')
    sec("literature", "Literature", lh + "</ul>")

    # links
    links = [("UniProt", f"https://www.uniprot.org/uniprotkb/{acc}"), ("AlphaFold DB", f"https://alphafold.ebi.ac.uk/entry/{acc}"),
             ("InterPro", f"https://www.ebi.ac.uk/interpro/protein/UniProt/{acc}/"), ("IntAct", f"https://www.ebi.ac.uk/intact/search?query={acc}")]
    if sd: links.insert(1, ("SGD", f"https://www.yeastgenome.org/locus/{sd['sgdid']}"))
    if cv: links.append(("ClinVar", f"https://www.ncbi.nlm.nih.gov/clinvar/?term={r['gene']}%5Bgene%5D"))
    for o in u["omim"]: links.append((f"OMIM {o}", f"https://www.omim.org/entry/{o}"))
    for o in u["orphanet"]: links.append((f"Orphanet: {o['name']}", f"https://www.orpha.net/en/disease/detail/{o['id']}"))
    for p in u["panther"][:1]: links.append((f"PANTHER {p['id']}", f"https://www.pantherdb.org/panther/family.do?clsAccession={p['id'].split(':')[0]}"))
    sec("links", "External links", '<div class="chips">' + "".join(f'<a class="chip" href="{E(h)}">{E(l)}</a>' for l, h in links) + "</div>")

    viewer_js = ""
    if af:
        viewer_js = f"""<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.5.5/3Dmol-min.js"></script>
<script>(function(){{var m=document.getElementById('vmsg');
if(!window.$3Dmol){{m.textContent='3D viewer could not be loaded (offline?). Use the AlphaFold DB link below.';return;}}
fetch('../data/models/{acc}.pdb').then(function(r){{return r.text()}}).then(function(t){{
 var v=$3Dmol.createViewer('viewer',{{backgroundColor:'white'}});v.addModel(t,'pdb');
 v.setStyle({{}},{{cartoon:{{colorfunc:function(a){{var b=a.b;return b>90?'#0053d6':b>70?'#65cbf3':b>50?'#ffdb13':'#ff7d45'}}}}}});
 v.zoomTo();v.render();if(m)m.remove();
}}).catch(function(){{m.textContent='Model failed to load.'}});}})();</script>"""

    gl = "; ".join(f'<a href="https://www.pantherdb.org/panther/family.do?clsAccession={g.split(":")[0]}">{E(g)}</a> ({E(GROUP_LABEL[g])})' for g in r["group_ids"])
    basis = (f'<div class="note"><b>Why it is here:</b> UniProt assigns this protein to PANTHER {gl}. '
             + ("This is a manually reviewed Swiss-Prot entry." if u["reviewed"] else
                "This is an <b>unreviewed (TrEMBL)</b> entry: its function text and features are inferred automatically from sequence similarity rather than curated by hand.") + "</div>")
    header = f"""<section class="hero"><div class="wrap">
<span class="tag {E(r['kingdom'])}">{E(r['kingdom'])}</span> <span class="tag">{E(r['group'])}</span>
<h1>{E(r['short'])} <span style="font-weight:400;color:var(--ink-soft);font-size:.6em">{E(u['name'])}</span></h1>
<div class="lede" style="margin:.2em 0">{org_html(u['organism'])} &middot; {E(', '.join(g for g in u['genes'] if g))}</div>
<div class="chips"><a class="chip" href="https://www.uniprot.org/uniprotkb/{acc}">UniProt {acc}</a>{"".join(f'<a class="chip" href="https://www.yeastgenome.org/locus/{sd["sgdid"]}">SGD {sd["sgdid"]}</a>' for _ in [0] if sd)}<a class="chip" href="https://alphafold.ebi.ac.uk/entry/{acc}">AlphaFold</a></div>
{basis}
<div class="facts">{fx}</div>
<div class="toc">{" ".join(toc)}</div></div></section>"""
    body = header + '<main class="wrap">' + "".join(secs) + "</main>"
    return shell(f"{r['short']} ({u['organism']}) — RecQ4 Family Depot", body, "home", 1, meta=meta, extra_foot=viewer_js)


# ---------- home, family, about ----------
def home(recs, meta):
    cards = "".join(f"""<div class="card" data-acc="{r['uniprot']}"><div><span class="tag {E(r['kingdom'])}">{E(r['kingdom'])}</span> <span class="tag">{E(r['group'])}</span></div>
<h3><a href="proteins/{r['slug']}.html">{E(r['short'])}</a></h3><div class="org">{org_html(r['uniprot_data']['organism'])}</div>
<p>{E(r['uniprot_data']['name'])} &middot; {r['uniprot_data']['length']:,} aa</p>
<p>{r['literature']['count']} PubMed records &middot; {"AlphaFold model" if r.get('alphafold') else "no AlphaFold model"}{" &middot; "+str(len(r['uniprot_data']['pdb']))+" PDB" if r['uniprot_data']['pdb'] else ""}{"" if r['uniprot_data']['reviewed'] else " &middot; unreviewed"}</p>
<div class="legend" style="margin-top:auto">{"" }</div></div>""" for r in recs)
    body = f"""<section class="hero"><div class="wrap"><span class="tag">Prototype</span>
<h1>RecQ4 Family Depot</h1>
<p class="lede">A single place for sequence, structure, alleles, interactions, and literature on RecQ4-family helicases, collected across organisms &mdash; modeled on what the <a href="https://www.yeastgenome.org/">Saccharomyces Genome Database</a> does for yeast genes.</p>
<form class="search" onsubmit="return false"><input id="q" type="search" placeholder="Search proteins, organisms, partners, diseases…" autocomplete="off" aria-label="Search"><button class="ghost" type="button" onclick="document.getElementById('q').value='';document.getElementById('q').dispatchEvent(new Event('input'))">Clear</button></form>
<div id="hint" style="font-size:.9rem;color:var(--ink-soft)"></div></div></section>
<main class="wrap"><div class="cards" id="cards">{cards}</div>
<h2>What each protein page includes</h2>
<div class="cols"><ul><li>Function and catalytic activity (UniProt)</li><li>Domain map and annotated sites</li><li>FASTA sequence, one click to copy or download</li><li>AlphaFold model in an interactive 3D viewer, plus PDB entries</li></ul>
<ul><li>Alleles, engineered mutations, and clinical variants</li><li>Physical and genetic interactions</li><li>Phenotypes and Gene Ontology terms</li><li>Recent literature</li></ul></div>
<p>The <a href="family.html">family overview</a> compares all entries side by side on one scale. Everything is refreshed from public databases by a script, so entries stay current without manual editing; see <a href="about.html">About &amp; sources</a> for what is and is not covered.</p></main>
<script src="assets/search-index.js"></script><script src="assets/search.js"></script>"""
    return shell("RecQ4 Family Depot (prototype)", body, "home", 0, meta=meta)


def family(recs, meta):
    mx = max(r["uniprot_data"]["length"] for r in recs)
    order = ["RECQL4 group", "HRQ1 group"]
    def grp(r): return r["group"] if r["group"] in order else "other"
    sections = ""
    for g in order:
        members = sorted([r for r in recs if grp(r) == g], key=lambda r: (["Animals", "Fungi", "Plants", "Bacteria", "Archaea"].index(r["kingdom"]), r["uniprot_data"]["organism"]))
        if not members: continue
        ids = ", ".join(sorted({i for r in members for i in r["group_ids"]}))
        maps = "".join(f'<h3><a href="proteins/{r["slug"]}.html">{E(r["short"])}</a> <span style="font-weight:400;color:var(--ink-soft)">&mdash; {org_html(r["uniprot_data"]["organism"])}, {r["uniprot_data"]["length"]:,} aa</span></h3>'
                       + domain_map(r["uniprot_data"], ref_len=mx) for r in members)
        sections += f'<h2>{E(g)} <span style="font-weight:400;font-size:.8em;color:var(--ink-soft)">(PANTHER {E(ids)})</span></h2>{maps}'
    rows = []
    for r in sorted(recs, key=lambda r: (order.index(grp(r)) if grp(r) in order else 9, r["uniprot_data"]["organism"])):
        u = r["uniprot_data"]; af = r.get("alphafold") or {}
        atp = next((d for d in u["features"]["domains"] if "ATP" in d["name"]), None)
        ct = next((d for d in u["features"]["domains"] if "C-terminal" in d["name"]), None)
        n_int = (len(r["sgd_data"]["physical"]) if r.get("sgd_data") else len(r["interactions_intact"]["partners"]))
        rows.append([f'<a href="proteins/{r["slug"]}.html"><b>{E(r["short"])}</b></a>', org_html(u["organism"]), E(r["kingdom"]), E(r["group"].replace(" group", "")),
                     "reviewed" if u["reviewed"] else "unreviewed", f"{u['length']:,}", f"{atp['start']}&ndash;{atp['end']}" if atp else "&mdash;",
                     f"{ct['start']}&ndash;{ct['end']}" if ct else "&mdash;", f"{af.get('globalMetricValue',0):.0f}" if af else "&mdash;", str(n_int), str(r["literature"]["count"])])
    body = f"""<section class="hero"><div class="wrap"><h1>Family overview</h1>
<p class="lede">All entries on one scale, split into the two PANTHER groups that define membership. The helicase domains are shared across members; their position and the regions flanking them differ.</p></div></section>
<main class="wrap"><div class="note"><b>Inclusion rule.</b> A protein is listed when UniProt cross-references it to PANTHER family PTHR13710:SF108 (ATP-dependent DNA helicase Q4, the RECQL4 group) or PTHR47957 (ATP-dependent helicase HRQ1, the HRQ1 group). The rule is applied by a script, so every entry shows which family it matched. See <a href="about.html#inclusion">About</a> for what the rule misses.</div>
{sections}{LEGEND}
<h2>Side-by-side</h2>{tbl(["Protein","Organism","Kingdom","Group","UniProt status","Length (aa)","ATP-binding domain","C-terminal domain","AlphaFold pLDDT","Physical / curated interactors","PubMed records"], rows, "scroll")}
<p style="font-size:.85rem;color:var(--ink-soft)">Interactor counts come from different sources (SGD for yeast, IntAct for the others) and include high-throughput data, so they are not directly comparable. Unreviewed entries are annotated automatically. Planned next: a sequence alignment and tree across all members.</p></main>"""
    return shell("Family overview — RecQ4 Family Depot", body, "family", 0, meta=meta)


def about(meta, recs):
    names = ", ".join(f"{r['short']} (<i>{E(r['uniprot_data']['organism'].split(' (')[0])}</i>)" for r in recs)
    body = f"""<section class="hero"><div class="wrap"><h1>About &amp; sources</h1>
<p class="lede">What this site is, where its data come from, and what it does not do yet.</p></div></section>
<main class="wrap prose" style="max-width:780px">
<h2 style="margin-top:.5em">Scope</h2>
<p>A prototype resource for RecQ4-family helicases from all organisms, started by the <a href="{LAB_URL}">Bochman Lab</a>. It currently lists {len(recs)} proteins: {names}.</p>
<h2 id="inclusion">What counts as RecQ4-family</h2>
<p>Gene names are inconsistent across species, so the site uses a database-defined rule instead of names:</p>
<ul><li><b>RECQL4 group:</b> UniProt cross-references the protein to PANTHER subfamily PTHR13710:SF108 (ATP-dependent DNA helicase Q4).</li>
<li><b>HRQ1 group:</b> UniProt cross-references the protein to PANTHER family PTHR47957 (ATP-dependent helicase HRQ1). This group includes yeast Hrq1, <i>Arabidopsis</i> HRQ1, and bacterial MrfA.</li></ul>
<p>The rule is already doing useful work. <i>Arabidopsis</i> genes named <i>RECQL4A</i> and <i>RECQL4B</i> sit in the broader RecQ family (PTHR13710) but in different subfamilies (SF148 and SF156), so they are left out, and none of the <i>C. elegans</i> RecQ genes I checked (wrn-1, him-6, rcq-5 and one other) are in the RECQL4 subfamily either.</p>
<p>Limits: the rule inherits PANTHER's classification, including its mistakes. It only sees proteins PANTHER has already assigned. The two groups are shown separately because this site makes no claim about how they relate to each other. Hits not yet added include <i>E. coli</i> DruE (a 1,836-aa phage-defense protein), chicken and other vertebrate Q4 proteins, and many insects. A phylogeny-based definition would still be a better long-term answer.</p>
<h2>Where the data come from</h2>
{tbl(["Data","Source","Notes"],[
 ["Sequence, domains, function, variants, mutagenesis","<a href='https://www.uniprot.org/'>UniProt</a>","Swiss-Prot entries are curated; TrEMBL entries are automatic and marked &ldquo;unreviewed&rdquo;"],
 ["Family membership","<a href='https://www.pantherdb.org/'>PANTHER</a> via UniProt","See rule above"],
 ["Predicted structure","<a href='https://alphafold.ebi.ac.uk/'>AlphaFold DB</a>","Model files copied into this site; some entries have none"],
 ["Experimental structures","PDB via UniProt cross-references",""],
 ["Interactions","<a href='https://www.ebi.ac.uk/intact/'>IntAct</a>; <a href='https://www.yeastgenome.org/'>SGD</a> for <i>S. cerevisiae</i>","Counts include high-throughput screens"],
 ["Yeast alleles and phenotypes","SGD","<i>S. cerevisiae</i> only"],
 ["Clinical variants","<a href='https://www.ncbi.nlm.nih.gov/clinvar/'>ClinVar</a>","Human only; counts by classification, no individual variant tables yet"],
 ["Literature","<a href='https://pubmed.ncbi.nlm.nih.gov/'>PubMed</a>","Automatic keyword search per protein"]],"")}
<h2>How it stays current</h2>
<p>A script (<code>scripts/fetch_data.py</code>) re-downloads everything from the sources above and a second script (<code>scripts/build_site.py</code>) regenerates the pages. A scheduled GitHub Action runs both weekly. Data were last refreshed {fmt_date(meta['fetched'])}.</p>
<h2>Limitations</h2>
<ul><li>This is aggregation, not expert curation. Annotations are only as good as the upstream databases, and unreviewed entries are the weakest.</li>
<li>The automatic literature searches are imprecise; some off-topic papers appear and relevant ones can be missed.</li>
<li>Only yeast has allele/phenotype detail so far, and only human has clinical variants.</li>
<li>There is no alignment, tree, or ortholog table yet.</li></ul>
<h2>Contact</h2><p>Corrections and suggestions: <a href="mailto:bochman@iu.edu">bochman@iu.edu</a>.</p></main>"""
    return shell("About & sources — RecQ4 Family Depot", body, "about", 0, meta=meta)


def search_index(recs):
    idx = []
    for r in recs:
        u = r["uniprot_data"]
        partners = [p["name"] for p in r["interactions_intact"]["partners"]] + [p["name"] for p in (r.get("sgd_data") or {}).get("physical", [])]
        fields = {
            "names": " ".join([r["short"], u["name"], *u["alt_names"], *[g for g in u["genes"] if g]]),
            "organism": u["organism"] + " " + r["kingdom"],
            "function": " ".join(u["comments"].get("FUNCTION", [])),
            "partners": " ".join(partners),
            "disease": " ".join((d.get("name") or "") + " " + (d.get("acronym") or "") for d in u["comments"].get("DISEASE", [])),
            "terms": " ".join(g["term"][2:] for g in u["go"]),
            "alleles": " ".join(sorted({a for p in (r.get("sgd_data") or {}).get("phenotypes", []) for a in p["alleles"]})),
        }
        idx.append({"acc": r["uniprot"], "url": f"proteins/{r['slug']}.html", "fields": fields})
    return "window.SEARCH_INDEX=" + json.dumps(idx) + ";"


SEARCH_JS = """(function(){var q=document.getElementById('q'),hint=document.getElementById('hint');
var cards=[].slice.call(document.querySelectorAll('.card'));
q.addEventListener('input',function(){var t=q.value.trim().toLowerCase();var n=0;hint.innerHTML='';
cards.forEach(function(c){var e=window.SEARCH_INDEX.find(function(x){return x.acc===c.dataset.acc});var hits=[];
if(t){Object.keys(e.fields).forEach(function(k){if(e.fields[k].toLowerCase().indexOf(t)>-1)hits.push(k)});}
var show=!t||hits.length>0;c.style.display=show?'':'none';c.classList.toggle('hit',!!t&&show);if(show)n++;
var old=c.querySelector('.why');if(old)old.remove();
if(t&&show){var d=document.createElement('p');d.className='why';d.style.fontSize='.85rem';d.textContent='Matches: '+hits.join(', ');c.appendChild(d);}});
if(t)hint.textContent=n+' of '+cards.length+' proteins match.';});})();"""


def main():
    meta, recs = load()
    os.makedirs(os.path.join(ROOT, "proteins"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    w = lambda path, s: open(os.path.join(ROOT, path), "w", encoding="utf-8").write(s)
    w("index.html", home(recs, meta)); w("family.html", family(recs, meta)); w("about.html", about(meta, recs))
    for r in recs:
        w(f"proteins/{r['slug']}.html", protein_page(r, meta))
    w("assets/search-index.js", search_index(recs)); w("assets/search.js", SEARCH_JS)
    print("built", len(recs), "protein pages")


if __name__ == "__main__":
    main()
