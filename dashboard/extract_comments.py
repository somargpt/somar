#!/usr/bin/env python3
"""Extrai o catálogo de comentários das minutas para alimentar o banco
'Padrão de Revisão' (Notion). Para cada comentário único do conjunto produz:

  Comentario  - texto do comentário (verbatim)
  Trecho      - texto do documento ancorado ao comentário (commentRange...)
  Revisor     - autor do comentário (string bruta, como no banco existente)
  Arquivo     - nome do arquivo .docx onde o comentário aparece
  Data        - data/hora do comentário (ISO, até o minuto)
  Documento   - edital / chamamento publico (pela modalidade do arquivo)
  Tipo        - classificação heurística (portugues/formatacao/padronizacao/duvida/conteudo)
  Acionabilidade - heurística (erro/sugestao/escalonamento)

Deduplica contra as entradas já existentes no Notion (existing_keys.json:
lista de [revisor, data_ate_minuto, prefixo60_do_comentario]).

Uso: python3 dashboard/extract_comments.py
Saída: dashboard/comments_catalog.json
"""
import json
import os
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DOCS = os.path.join(REPO, "editais")
SCRATCH = os.environ.get("SCRATCH", HERE)
EXISTING = os.path.join(SCRATCH, "existing_keys.json")
OUT = os.path.join(HERE, "comments_catalog.json")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def q(tag):
    return f"{{{W}}}{tag}"


NAME_CANON = {"Paulo Eduardo Nobrega Rocha": "Paulo Rocha"}


def parse_filename_sei(name):
    m = re.search(r"SEI\s*([0-9X]{4,6}(?:-[0-9X]{2,4}){0,2})", name, re.IGNORECASE)
    sei = m.group(1) if m else None
    low = name.lower()
    if low.startswith("leil"):
        modality = "leilao"
    elif low.startswith("chamamento"):
        modality = "chamamento publico"
    else:
        modality = "pregao"
    return sei, modality


def norm(s):
    s = unicodedata.normalize("NFC", s or "")
    return re.sub(r"\s+", " ", s).strip()


def chain_len(name):
    base = name[:-5] if name.lower().endswith(".docx") else name
    base = re.sub(r"\s*\(\d+\)\s*$", "", base)
    m = re.search(r"[_\s]rev\b(.*)$", base, re.IGNORECASE)
    return len(re.split(r"\s+", m.group(1).strip())) if m and m.group(1).strip() else 0


def extract_comments(path):
    """Retorna {id: {author,date,text}} e {id: trecho} para um .docx."""
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if "word/comments.xml" not in names:
            return {}, {}
        croot = ET.parse(zf.open("word/comments.xml")).getroot()
        comments = {}
        for c in croot.findall(q("comment")):
            cid = c.get(q("id"))
            comments[cid] = {
                "author": c.get(q("author")),
                "date": c.get(q("date")),
                "text": norm("".join(t.text or "" for t in c.iter(q("t")))),
            }
        # trecho: texto entre commentRangeStart/End, em ordem de documento
        trechos = defaultdict(list)
        open_ids = set()
        droot = ET.parse(zf.open("word/document.xml")).getroot()
        for el in droot.iter():
            tag = el.tag
            if tag == q("commentRangeStart"):
                open_ids.add(el.get(q("id")))
            elif tag == q("commentRangeEnd"):
                open_ids.discard(el.get(q("id")))
            elif tag == q("t") and open_ids and el.text:
                for cid in open_ids:
                    trechos[cid].append(el.text)
        trechos = {cid: norm("".join(parts))[:1800] for cid, parts in trechos.items()}
        return comments, trechos


# --- classificação heurística ---
FORMAT_RE = re.compile(
    r"espa[çc]|alinh|centraliz|margem|negrito|it[áa]lico|fonte|"
    r"folha em branco|p[áa]gina|cabe[çc]alho|solto na|quebra|acento|"
    r"mai[úu]scul|min[úu]scul|realce|sublinhad|tabela|coluna|recuo|espaçamento",
    re.IGNORECASE)
QUESTION_RE = re.compile(
    r"\?|ser[áa] que|n[ãa]o seria|fiquei na d[úu]vida|n[ãa]o faço ideia|"
    r"o que acha|por que|porque ser|estranho|d[úu]vida|conferir se|verificar se",
    re.IGNORECASE)
ESCALON_RE = re.compile(
    r"[áa]rea t[ée]cnica|perguntar|consultar|passar para a? ?(dcp|dm|gdm|dt|gtp)|"
    r"encaminh|escalon|dilig" r"|verificar com|confirmar com|definir posi",
    re.IGNORECASE)
CONTENT_RE = re.compile(
    r"\bart\.?\b|\blei\b|\binciso\b|resolu[çc][ãa]o|decreto|"
    r"\b1[34]\.133\b|jurisprud|ac[óo]rd[ãa]o|s[úu]mula|cl[áa]usula|"
    r"exig[êe]nc|veda[çc]|habilita[çc]|qualifica[çc]|subcontrata",
    re.IGNORECASE)
STANDARD_RE = re.compile(
    r"^excluir|padroniz|nomenclatura|remiss|remissao|conforme (o )?item|"
    r"conforme (o )?modelo|numera[çc][ãa]o|minutas (mais )?recentes|"
    r"modelo institucional|geralmente|costumamos|usar a nomenclatura",
    re.IGNORECASE)
PT_RE = re.compile(r"^[\wÀ-ÿ]{1,20}$")  # palavra única curta


def classify(text, trecho):
    t = text or ""
    low = t.lower()
    # Tipo
    if FORMAT_RE.search(t) and not CONTENT_RE.search(t):
        tipo = "formatacao"
    elif re.fullmatch(r"[\d.\-/º°]+", t.strip()):
        tipo = "padronizacao"  # número de item / classificador contábil
    elif STANDARD_RE.search(t):
        tipo = "padronizacao"
    elif CONTENT_RE.search(t):
        tipo = "conteudo"
    elif QUESTION_RE.search(t):
        tipo = "duvida"
    elif PT_RE.match(t.strip()):
        tipo = "portugues"
    else:
        tipo = "conteudo"
    # Acionabilidade
    if ESCALON_RE.search(t) or (QUESTION_RE.search(t) and tipo == "duvida" and ESCALON_RE.search(t)):
        acion = "escalonamento"
    elif tipo == "duvida":
        acion = "escalonamento" if ESCALON_RE.search(t) else "sugestao"
    elif re.match(r"^\s*(excluir|incluir|sugiro|sugeriria|sugest|substituir|trocar|alterar|ajust|padroniz)", low) \
            or FORMAT_RE.search(t) or QUESTION_RE.search(t):
        acion = "sugestao"
    elif re.fullmatch(r"[\d.\-/º°]+", t.strip()) or STANDARD_RE.search(t):
        acion = "erro"
    else:
        acion = "sugestao"
    return tipo, acion


def main():
    def dnorm(d):
        return (d or "").replace("T", " ").strip()[:16]

    existing = set()
    existing_day = set()
    if os.path.exists(EXISTING):
        for rev, data, pref in json.load(open(EXISTING, encoding="utf-8")):
            r = norm(rev).lower()
            p = norm(pref).lower()
            existing.add((r, dnorm(data), p))
            existing_day.add((r, dnorm(data)[:10], p))

    files = sorted(f for f in os.listdir(DOCS)
                   if f.lower().endswith(".docx") and not f.startswith("~$"))

    # unique comment -> melhor registro (com trecho, arquivo mais recente)
    uniq = {}
    for name in files:
        sei, modality = parse_filename_sei(name)
        try:
            comments, trechos = extract_comments(os.path.join(DOCS, name))
        except (zipfile.BadZipFile, ET.ParseError, KeyError):
            continue
        cl = chain_len(name)
        for cid, c in comments.items():
            author = NAME_CANON.get(c["author"], c["author"])
            text = c["text"]
            if not text:
                continue
            date = c["date"] or ""
            key = (sei, norm(author).lower(), date[:16], norm(text).lower())
            trecho = trechos.get(cid, "")
            prev = uniq.get(key)
            # preferir ocorrência com trecho e do arquivo com cadeia mais longa
            score = (1 if trecho else 0, cl)
            if prev is None or score > prev["_score"]:
                doc = "chamamento publico" if modality == "chamamento publico" else "edital"
                tipo, acion = classify(text, trecho)
                uniq[key] = {
                    "Comentario": text,
                    "Trecho": trecho or None,
                    "Revisor": author,
                    "Arquivo": name,
                    "Data": date or None,
                    "Documento": doc,
                    "Tipo": tipo,
                    "Acionabilidade": acion,
                    "sei": sei,
                    "_score": score,
                }

    # dedup contra Notion existente
    new, dup = [], 0
    for rec in uniq.values():
        rev = norm(rec["Revisor"]).lower()
        data16 = dnorm(rec["Data"])
        pref = norm(rec["Comentario"]).lower()[:60]
        # também casar com data só-dia (entradas de impugnação sem hora)
        hit = ((rev, data16, pref) in existing or
               (rev, data16[:10], pref) in existing_day)
        if hit:
            dup += 1
            continue
        rec.pop("_score", None)
        new.append(rec)

    new.sort(key=lambda r: (r["Data"] or "", r["Revisor"]))
    for i, r in enumerate(new):
        r["idx"] = i
    json.dump(new, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # resumo
    from collections import Counter
    print(f"comentários únicos no conjunto: {len(uniq)}")
    print(f"duplicados (já no Notion): {dup}")
    print(f"novos a inserir: {len(new)}")
    print(f"  com trecho ancorado: {sum(1 for r in new if r['Trecho'])}")
    print("  por Tipo:", dict(Counter(r["Tipo"] for r in new)))
    print("  por Acionabilidade:", dict(Counter(r["Acionabilidade"] for r in new)))
    print("  por Revisor:", dict(Counter(r["Revisor"] for r in new)))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
