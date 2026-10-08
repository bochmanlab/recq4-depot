#!/usr/bin/env python3
"""Fetch public data for the RecQ4-family depot prototype.

Sources (all public, no API keys):
  UniProt REST, AlphaFold DB, NCBI E-utilities (PubMed, ClinVar),
  IntAct, SGD (for S. cerevisiae only).

Writes data/<UNIPROT>.json (one compact record per protein) and data/_meta.json.
Re-run on a schedule (see .github/workflows/refresh-data.yml) to stay current.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

# One entry per protein. Add a row here (plus a PubMed query) to add a protein.
# Inclusion rule (see About page): a protein is listed here when UniProt cross-references it to one of
# the two PANTHER groups below. The "group" field is computed from the UniProt record, not typed by hand.
GROUPS = {
    "PTHR13710:SF108": "RECQL4 group",   # "ATP-dependent DNA helicase Q4"
    "PTHR47957": "HRQ1 group",           # "ATP-dependent helicase HRQ1"
}

PROTEINS = [
    {"uniprot": "O94761", "slug": "recql4-human", "gene": "RECQL4", "short": "RECQL4",
     "organism": "Homo sapiens", "kingdom": "Animals", "clinvar_gene": "RECQL4",
     "pubmed": 'RECQL4[tiab] OR RECQ4[tiab] OR "RecQ4"[tiab]'},
    {"uniprot": "Q75NR7", "slug": "recql4-mouse", "gene": "Recql4", "short": "Recql4",
     "organism": "Mus musculus", "kingdom": "Animals",
     "pubmed": 'Recql4[tiab] AND (mouse OR mice OR murine)'},
    {"uniprot": "E7F2M7", "slug": "recql4-zebrafish", "gene": "recql4", "short": "recql4",
     "organism": "Danio rerio", "kingdom": "Animals",
     "pubmed": 'recql4[tiab] AND (zebrafish OR Danio)'},
    {"uniprot": "Q33DM4", "slug": "recq4-xenopus", "gene": "XRecQ4", "short": "XRecQ4",
     "organism": "Xenopus laevis", "kingdom": "Animals",
     "pubmed": '(XRecQ4[tiab] OR RecQ4[tiab] OR RecQL4[tiab]) AND Xenopus'},
    {"uniprot": "Q9VSE6", "slug": "recq4-drosophila", "gene": "RecQ4", "short": "DmRECQ4",
     "organism": "Drosophila melanogaster", "kingdom": "Animals",
     "pubmed": '(RecQ4[tiab] OR DmRECQ4[tiab] OR CG7487[tiab]) AND Drosophila'},
    {"uniprot": "Q05549", "slug": "hrq1-scerevisiae", "gene": "HRQ1", "short": "Hrq1",
     "organism": "Saccharomyces cerevisiae", "kingdom": "Fungi", "sgd": "S000002699",
     "pubmed": 'HRQ1[tiab] AND (yeast OR cerevisiae OR helicase)'},
    {"uniprot": "O13983", "slug": "hrq1-spombe", "gene": "hrq1", "short": "Hrq1",
     "organism": "Schizosaccharomyces pombe", "kingdom": "Fungi",
     "pubmed": 'hrq1[tiab] AND (pombe OR "fission yeast")'},
    {"uniprot": "A0A1P8BBA5", "slug": "hrq1-athaliana", "gene": "HRQ1", "short": "HRQ1",
     "organism": "Arabidopsis thaliana", "kingdom": "Plants",
     "pubmed": '(HRQ1[tiab] OR At5g08110[tiab]) AND Arabidopsis'},
    {"uniprot": "P50830", "slug": "mrfa-bsubtilis", "gene": "mrfA", "short": "MrfA",
     "organism": "Bacillus subtilis", "kingdom": "Bacteria",
     "pubmed": 'MrfA[tiab] AND (Bacillus OR helicase)'},
    {"uniprot": "A0R5E2", "slug": "sfth-msmegmatis", "gene": "sftH", "short": "SftH",
     "organism": "Mycolicibacterium smegmatis", "kingdom": "Bacteria",
     "pubmed": 'SftH[tiab] AND (Mycobacterium OR Mycolicibacterium OR smegmatis)'},
    {"uniprot": "Q58969", "slug": "mj1574-mjannaschii", "gene": "MJ1574", "short": "MJ1574",
     "organism": "Methanocaldococcus jannaschii", "kingdom": "Archaea",
     "pubmed": '(MJ1574[tiab] OR MJ1572[tiab]) AND (Methanocaldococcus OR Methanococcus)'},
]

# Candidates found by the same rule but not included yet (documented on the About page):
#   E. coli DruE (P0DW38) -- 1,836 aa phage-defense protein; Gallus gallus A0A8V0XX13; many mammals/insects.
# Deliberately excluded by the rule: Arabidopsis RECQL4A/RECQL4B (PANTHER PTHR13710:SF148/SF156, not SF108)
# and C. elegans RecQ genes (other PTHR13710 subfamilies), despite "RecQ4" in some gene names.

UA = {"User-Agent": "bochmanlab-recq4-depot/0.1 (bochman@iu.edu)"}


def get(url, data=None, headers=None, retries=3):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            if i == retries - 1:
                print("  FAILED", url[:90], e, file=sys.stderr)
                return None
            time.sleep(2 * (i + 1))


def jget(url, **kw):
    b = get(url, **kw)
    return json.loads(b) if b else None


def uniprot(acc):
    return jget(f"https://rest.uniprot.org/uniprotkb/{acc}.json")


def alphafold(acc):
    j = jget(f"https://alphafold.ebi.ac.uk/api/prediction/{acc}")
    return j[0] if j else None


def pubmed(query, retmax=40):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    s = jget(f"{base}/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax, "sort": "pub date"}))
    if not s:
        return {"count": 0, "papers": []}
    ids = s["esearchresult"]["idlist"]
    count = int(s["esearchresult"]["count"])
    papers = []
    if ids:
        time.sleep(0.4)
        sm = jget(f"{base}/esummary.fcgi?" + urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}))
        for i in ids:
            r = (sm or {}).get("result", {}).get(i)
            if not r:
                continue
            authors = [a["name"] for a in r.get("authors", [])]
            papers.append({
                "pmid": i, "title": r.get("title", "").rstrip("."),
                "authors": authors[:3] + (["et al."] if len(authors) > 3 else []),
                "journal": r.get("source", ""), "year": (r.get("pubdate", "") or "")[:4],
                "date": r.get("pubdate", ""),
            })
    return {"count": count, "papers": papers, "query": query}


def clinvar(gene):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    out = {}
    for label, term in [
        ("total", f"{gene}[gene]"),
        ("pathogenic", f'{gene}[gene] AND "clinsig pathogenic"[Properties]'),
        ("likely_pathogenic", f'{gene}[gene] AND "clinsig likely pathogenic"[Properties]'),
        ("vus", f'{gene}[gene] AND "clinsig vus"[Properties]'),
        ("likely_benign", f'{gene}[gene] AND "clinsig likely benign"[Properties]'),
        ("benign", f'{gene}[gene] AND "clinsig benign"[Properties]'),
    ]:
        j = jget(f"{base}/esearch.fcgi?" + urllib.parse.urlencode(
            {"db": "clinvar", "term": term, "retmode": "json", "retmax": 0}))
        out[label] = int(j["esearchresult"]["count"]) if j else None
        time.sleep(0.4)
    return out


def intact(acc, self_id):
    b = get("https://www.ebi.ac.uk/intact/ws/interaction/findInteractionWithFacet",
            data=urllib.parse.urlencode({"query": acc, "pageSize": 500, "page": 0}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
    if not b:
        return {"total": 0, "partners": []}
    d = json.loads(b)["data"]
    partners = {}
    for r in d.get("content", []):
        if r.get("uniqueIdA") == acc:
            pid, name = r.get("uniqueIdB"), r.get("moleculeB")
        elif r.get("uniqueIdB") == acc:
            pid, name = r.get("uniqueIdA"), r.get("moleculeA")
        else:
            continue
        p = partners.setdefault(pid, {"uniprot": pid, "name": name, "methods": set(),
                                      "types": set(), "pmids": set(), "score": 0})
        if r.get("detectionMethod"): p["methods"].add(r["detectionMethod"])
        if r.get("type"): p["types"].add(r["type"])
        if r.get("publicationPubmedIdentifier"): p["pmids"].add(str(r["publicationPubmedIdentifier"]))
        p["score"] = max(p["score"], r.get("intactMiscore") or 0)
    plist = []
    for p in partners.values():
        plist.append({**p, "methods": sorted(p["methods"]), "types": sorted(p["types"]),
                      "pmids": sorted(p["pmids"])})
    plist.sort(key=lambda p: (-p["score"], p["name"] or ""))
    return {"total": d.get("totalElements", 0), "partners": plist}


def sgd(sgdid):
    out = {"sgdid": sgdid}
    inter = jget(f"https://www.yeastgenome.org/backend/locus/{sgdid}/interaction_details") or []
    phys, gen = {}, {}
    for r in inter:
        l1, l2 = r["locus1"], r["locus2"]
        other = l2 if l1["link"].endswith(sgdid) else l1
        bucket = phys if r.get("interaction_type") == "Physical" else gen
        p = bucket.setdefault(other["format_name"], {"name": other["display_name"],
                              "systematic": other["format_name"], "sgdid": other["link"].split("/")[-1],
                              "experiments": set()})
        p["experiments"].add(r["experiment"]["display_name"])
    fin = lambda d: sorted(({**p, "experiments": sorted(p["experiments"])} for p in d.values()),
                           key=lambda p: p["name"])
    out["physical"] = fin(phys)
    out["genetic_partners"] = sorted(p["name"] for p in gen.values())
    out["genetic_count"] = len(gen)
    out["interaction_rows"] = len(inter)
    ph = jget(f"https://www.yeastgenome.org/backend/locus/{sgdid}/phenotype_details") or []
    rows = []
    for r in ph:
        alleles = [x["bioitem"]["display_name"] for x in r.get("properties", [])
                   if x.get("role") == "Allele" and x.get("bioitem")]
        chem = [x["bioitem"]["display_name"] for x in r.get("properties", [])
                if x.get("role") == "Chemical" and x.get("bioitem")]
        rows.append({
            "phenotype": r["phenotype"]["display_name"],
            "mutant_type": r.get("mutant_type"),
            "alleles": alleles, "chemicals": chem,
            "strain": (r.get("strain") or {}).get("display_name"),
            "reference": (r.get("reference") or {}).get("display_name"),
            "pmid": (r.get("reference") or {}).get("pubmed_id"),
            "experiment": (r.get("experiment") or {}).get("display_name"),
        })
    out["phenotypes"] = rows
    return out


def slim_uniprot(u):
    """Keep only what the pages render."""
    def text(c):
        return " ".join(t["value"] for t in c.get("texts", []))
    comments = {}
    for c in u.get("comments", []):
        t = c["commentType"]
        if t in ("FUNCTION", "SUBUNIT", "SUBCELLULAR LOCATION", "TISSUE SPECIFICITY", "INDUCTION",
                 "DISRUPTION PHENOTYPE", "DOMAIN", "SIMILARITY", "MISCELLANEOUS"):
            if t == "SUBCELLULAR LOCATION":
                v = "; ".join(l["location"]["value"] for l in c.get("subcellularLocations", []))
            else:
                v = text(c)
            if v:
                comments.setdefault(t, []).append(v)
        elif t == "COFACTOR":
            comments.setdefault("COFACTOR", []).extend(x["name"] for x in c.get("cofactors", []))
        elif t == "CATALYTIC ACTIVITY":
            r = c.get("reaction", {})
            comments.setdefault("CATALYTIC ACTIVITY", []).append(r.get("name", ""))
        elif t == "DISEASE":
            d = c.get("disease", {})
            comments.setdefault("DISEASE", []).append({
                "name": d.get("diseaseId"), "acronym": d.get("acronym"),
                "desc": d.get("description"), "mim": (d.get("diseaseCrossReference") or {}).get("id"),
                "note": text(c.get("note", {})) if c.get("note") else ""})
    feats = {"domains": [], "regions": [], "motifs": [], "binding": [], "mutagenesis": [], "variants": []}
    for f in u.get("features", []):
        loc = f["location"]; s, e = loc["start"]["value"], loc["end"]["value"]
        d = f.get("description", "")
        if f["type"] == "Domain": feats["domains"].append({"name": d, "start": s, "end": e})
        elif f["type"] == "Region": feats["regions"].append({"name": d, "start": s, "end": e})
        elif f["type"] == "Motif": feats["motifs"].append({"name": d, "start": s, "end": e})
        elif f["type"] == "Binding site":
            feats["binding"].append({"start": s, "end": e, "ligand": (f.get("ligand") or {}).get("name", d)})
        elif f["type"] == "Mutagenesis":
            feats["mutagenesis"].append({"pos": s, "change": f.get("alternativeSequence", {}).get("originalSequence", "") +
                                         ">" + ",".join(f.get("alternativeSequence", {}).get("alternativeSequences", [])),
                                         "desc": d})
        elif f["type"] == "Natural variant":
            alt = f.get("alternativeSequence", {})
            feats["variants"].append({"pos": s, "orig": alt.get("originalSequence", ""),
                                      "alt": ",".join(alt.get("alternativeSequences", [])), "desc": d})
    xr = {}
    for x in u.get("uniProtKBCrossReferences", []):
        xr.setdefault(x["database"], []).append({"id": x["id"], "props": {p["key"]: p["value"] for p in x.get("properties", [])}})
    go = [{"id": x["id"], "term": x["props"].get("GoTerm", "")} for x in xr.get("GO", [])]
    return {
        "accession": u["primaryAccession"], "entry": u["uniProtkbId"],
        "reviewed": u.get("entryType", "").startswith("UniProtKB reviewed"),
        "name": u["proteinDescription"].get("recommendedName", {}).get("fullName", {}).get("value", ""),
        "alt_names": [n["fullName"]["value"] for n in u["proteinDescription"].get("alternativeNames", [])],
        "ec": [e["value"] for e in u["proteinDescription"].get("recommendedName", {}).get("ecNumbers", [])],
        "genes": [g.get("geneName", {}).get("value") for g in u.get("genes", [])] +
                 [s["value"] for g in u.get("genes", []) for s in g.get("synonyms", [])] +
                 [s["value"] for g in u.get("genes", []) for s in g.get("orderedLocusNames", [])],
        "organism": u["organism"]["scientificName"], "taxid": u["organism"]["taxonId"],
        "length": u["sequence"]["length"], "mass": u["sequence"]["molWeight"],
        "sequence": u["sequence"]["value"], "existence": u.get("proteinExistence"),
        "annotation_score": u.get("annotationScore"),
        "last_modified": u["entryAudit"]["lastAnnotationUpdateDate"],
        "comments": comments, "features": feats,
        "go": go,
        "pdb": [{"id": x["id"], "method": x["props"].get("Method"), "res": x["props"].get("Resolution"),
                 "chains": x["props"].get("Chains")} for x in xr.get("PDB", [])],
        "interpro": [{"id": x["id"], "name": x["props"].get("EntryName")} for x in xr.get("InterPro", [])],
        "pfam": [{"id": x["id"], "name": x["props"].get("EntryName")} for x in xr.get("Pfam", [])],
        "omim": [x["id"] for x in xr.get("MIM", [])],
        "orphanet": [{"id": x["id"], "name": x["props"].get("DiseaseName")} for x in xr.get("Orphanet", [])],
        "refseq": [x["id"] for x in xr.get("RefSeq", [])],
        "panther": [{"id": x["id"], "name": x["props"].get("EntryName")} for x in xr.get("PANTHER", [])],
    }


def main():
    meta = {"fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"), "proteins": []}
    for p in PROTEINS:
        acc = p["uniprot"]
        print("==", p["short"], acc)
        rec = {**p}
        u = uniprot(acc)
        if not u:
            print("  UniProt failed; keeping previous file if present"); continue
        rec["uniprot_data"] = slim_uniprot(u)
        fam = [x["id"] for x in rec["uniprot_data"]["panther"]]
        rec["group_ids"] = [g for g in GROUPS if g in fam]
        rec["group"] = " + ".join(GROUPS[g] for g in rec["group_ids"]) or "unassigned"
        af = alphafold(acc)
        if af:
            rec["alphafold"] = {k: af.get(k) for k in (
                "entryId", "globalMetricValue", "fractionPlddtVeryHigh", "fractionPlddtConfident",
                "fractionPlddtLow", "fractionPlddtVeryLow", "cifUrl", "pdbUrl", "paeImageUrl",
                "latestVersion", "modelCreatedDate")}
        if af and af.get("pdbUrl"):
            b = get(af["pdbUrl"])  # keep a same-origin copy so the 3D viewer needs no cross-site fetch
            if b:
                os.makedirs(os.path.join(DATA, "models"), exist_ok=True)
                with open(os.path.join(DATA, "models", f"{acc}.pdb"), "wb") as fh:
                    fh.write(b)
        rec["literature"] = pubmed(p["pubmed"])
        rec["interactions_intact"] = intact(acc, acc)
        if p.get("sgd"):
            rec["sgd_data"] = sgd(p["sgd"])
        if p.get("clinvar_gene"):
            rec["clinvar"] = clinvar(p["clinvar_gene"])
        with open(os.path.join(DATA, f"{acc}.json"), "w") as fh:
            json.dump(rec, fh, indent=1)
        meta["proteins"].append(acc)
        time.sleep(0.5)
    with open(os.path.join(DATA, "_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    print("done", meta["fetched"])


if __name__ == "__main__":
    main()
