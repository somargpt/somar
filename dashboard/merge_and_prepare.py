#!/usr/bin/env python3
"""Mescla as classificacoes dos agentes (dashboard/cls/cls_*.json) no catalogo e
gera dashboard/notion_pages.json: uma lista de objetos {idx, properties} prontos
para o tool notion-create-pages (parent = data source 'Padrao de Revisao').

Uso: python3 dashboard/merge_and_prepare.py
"""
import glob
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "comments_catalog.json")
CLSDIR = os.path.join(HERE, "cls")
OUT = os.path.join(HERE, "notion_pages.json")

TIPOS = {"portugues", "formatacao", "padronizacao", "duvida", "conteudo"}
ACION = {"erro", "sugestao", "escalonamento"}


def deaccent(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def main():
    catalog = json.load(open(CATALOG, encoding="utf-8"))
    by_idx = {c["idx"]: c for c in catalog}

    cls = {}
    for fn in sorted(glob.glob(os.path.join(CLSDIR, "cls_*.json"))):
        try:
            arr = json.load(open(fn, encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"AVISO: {fn}: {e}", file=sys.stderr)
            continue
        for r in arr:
            cls[r["idx"]] = r

    missing = sorted(set(by_idx) - set(cls))
    bad = []
    for idx, r in cls.items():
        if r.get("tipo") not in TIPOS or r.get("acionabilidade") not in ACION:
            bad.append((idx, r.get("tipo"), r.get("acionabilidade")))

    print(f"catalogo: {len(catalog)} | classificados: {len(cls)} | "
          f"faltando: {len(missing)} | invalidos: {len(bad)}")
    if missing:
        print("  idx faltando:", missing[:40], "..." if len(missing) > 40 else "")
    if bad:
        print("  invalidos (idx,tipo,acion):", bad[:20])
    if missing or bad:
        print("NAO gerando notion_pages.json ate resolver pendencias.", file=sys.stderr)
        sys.exit(1)

    pages = []
    for idx in sorted(by_idx):
        c = by_idx[idx]
        r = cls[idx]
        props = {
            "Comentario": c["Comentario"][:1900],
            "Revisor": c["Revisor"] or "",
            "Arquivo": c["Arquivo"],
            "Tipo": r["tipo"],
            "Acionabilidade": r["acionabilidade"],
            "Documento": c["Documento"],
            "Regra": deaccent(r["regra"] or "").lower().strip()[:400],
        }
        if c.get("Trecho"):
            props["Trecho"] = c["Trecho"][:1900]
        if c.get("Data"):
            props["date:Data:start"] = c["Data"]
            props["date:Data:is_datetime"] = 1
        pages.append({"idx": idx, "properties": props})

    json.dump(pages, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {OUT} ({len(pages)} paginas prontas)")


if __name__ == "__main__":
    main()
