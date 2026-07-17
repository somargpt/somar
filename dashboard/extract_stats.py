#!/usr/bin/env python3
"""Extrai metadados das minutas de edital (.docx) da pasta editais/ e gera dashboard/data.json.

Para cada arquivo .docx extrai:
  - Identificação do processo (número SEI) e objeto, a partir do nome do arquivo
  - Cadeia de revisão (tokens após "rev" no nome do arquivo)
  - docProps/core.xml: criador, último modificador, datas de criação/modificação, nº de revisões salvas
  - docProps/app.xml: páginas, palavras, tempo total de edição (minutos)
  - word/comments.xml: comentários (autor, iniciais, data, tamanho do texto)
  - word/commentsExtended.xml: comentários resolvidos (w15:done)
  - word/document.xml: alterações controladas (inserções/remoções) por autor

Uso: python3 dashboard/extract_stats.py
"""
import json
import os
import re
import sys
import zipfile
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "editais")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
}


def parse_filename(name):
    """Extrai nº SEI, objeto e cadeia de revisão do nome do arquivo."""
    base = name[:-5] if name.lower().endswith(".docx") else name
    # nº SEI: sequência após "SEI"
    m = re.search(r"SEI\s*([0-9X]{4,6}(?:-[0-9X]{2,4}){0,2})", base, re.IGNORECASE)
    sei = m.group(1) if m else None

    # marcador de duplicata "(2)" ao final
    dup = bool(re.search(r"\(\d+\)\s*$", base))
    clean = re.sub(r"\s*\(\d+\)\s*$", "", base)

    # cadeia de revisão: tudo após o último " rev " / "_rev "
    chain = []
    m = re.search(r"[_\s]rev\b(.*)$", clean, re.IGNORECASE)
    if m:
        chain = [t for t in re.split(r"\s+", m.group(1).strip()) if t]

    # objeto: trecho entre o nº SEI e "Minuta"/"rev"
    title = None
    if sei:
        after = clean.split(sei, 1)[1]
        after = after.lstrip("_- ")
        after = re.split(r"[_\s]*Minuta", after, 1, re.IGNORECASE)[0]
        after = re.split(r"[_\s]rev\b", after, 1, re.IGNORECASE)[0]
        title = after.strip(" _-") or None

    modality = "pregão eletrônico"
    low = base.lower()
    if low.startswith("leil"):
        modality = "leilão"
    elif low.startswith("chamamento"):
        modality = "chamamento público"
    return sei, title, chain, dup, modality


def norm_token(tok):
    """Normaliza token de revisor do nome do arquivo: lk2 -> lk, TR2 -> tr, DM1 -> dm."""
    t = tok.strip().lower()
    t = re.sub(r"\d+$", "", t)
    return t


def read_xml(zf, path):
    try:
        with zf.open(path) as f:
            return ET.parse(f).getroot()
    except KeyError:
        return None
    except ET.ParseError:
        return None


def extract(path):
    rec = {}
    with zipfile.ZipFile(path) as zf:
        core = read_xml(zf, "docProps/core.xml")
        if core is not None:
            def g(tag):
                el = core.find(tag, NS)
                return el.text if el is not None else None
            rec["creator"] = g("dc:creator")
            rec["lastModifiedBy"] = g("cp:lastModifiedBy")
            rec["created"] = g("dcterms:created")
            rec["modified"] = g("dcterms:modified")
            rev = g("cp:revision")
            rec["saveRevision"] = int(rev) if rev and rev.isdigit() else None

        app = read_xml(zf, "docProps/app.xml")
        if app is not None:
            def ga(tag):
                el = app.find(f"ep:{tag}", NS)
                return el.text if el is not None else None
            for k, tag in [("pages", "Pages"), ("words", "Words"),
                           ("editMinutes", "TotalTime")]:
                v = ga(tag)
                rec[k] = int(v) if v and v.lstrip("-").isdigit() else None

        # comentários
        comments = []
        croot = read_xml(zf, "word/comments.xml")
        if croot is not None:
            for c in croot.findall("w:comment", NS):
                author = c.get(f"{{{NS['w']}}}author")
                initials = c.get(f"{{{NS['w']}}}initials")
                date = c.get(f"{{{NS['w']}}}date")
                text = "".join(t.text or "" for t in c.iter(f"{{{NS['w']}}}t"))
                comments.append({
                    "author": author, "initials": initials, "date": date,
                    "chars": len(text), "words": len(text.split()),
                })
        rec["comments"] = comments

        # comentários resolvidos
        resolved = 0
        cext = read_xml(zf, "word/commentsExtended.xml")
        if cext is not None:
            for ce in cext.findall("w15:commentEx", NS):
                if ce.get(f"{{{NS['w15']}}}done") == "1":
                    resolved += 1
        rec["resolvedComments"] = resolved

        # alterações controladas (inserções/remoções) por autor
        ins_by, del_by = Counter(), Counter()
        tc_dates = []
        droot = read_xml(zf, "word/document.xml")
        if droot is not None:
            for tag, ctr in ((f"{{{NS['w']}}}ins", ins_by), (f"{{{NS['w']}}}del", del_by)):
                for el in droot.iter(tag):
                    a = el.get(f"{{{NS['w']}}}author")
                    if a:
                        ctr[a] += 1
                    d = el.get(f"{{{NS['w']}}}date")
                    if d:
                        tc_dates.append(d)
        rec["insertionsByAuthor"] = dict(ins_by)
        rec["deletionsByAuthor"] = dict(del_by)
        rec["trackedChangeDates"] = [min(tc_dates), max(tc_dates)] if tc_dates else None
    return rec


def main():
    files = sorted(
        f for f in os.listdir(DOCS)
        if f.lower().endswith(".docx") and not f.startswith("~$")
    )
    out = []
    for name in files:
        path = os.path.join(DOCS, name)
        sei, title, chain, dup, modality = parse_filename(name)
        try:
            rec = extract(path)
        except (zipfile.BadZipFile, OSError) as e:
            print(f"AVISO: falha ao ler {name}: {e}", file=sys.stderr)
            continue
        rec.update({
            "file": name,
            "sei": sei,
            "title": title,
            "revChain": chain,
            "revChainNorm": [norm_token(t) for t in chain],
            "isDup": dup,
            "modality": modality,
            "sizeBytes": os.path.getsize(path),
        })
        out.append(rec)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{len(out)} arquivos processados -> {OUT}")


if __name__ == "__main__":
    main()
