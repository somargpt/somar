#!/usr/bin/env python3
"""Agrega os metadados extraídos (data.json) e injeta o dataset no dashboard (index.html).

Modelo:
  - Versão  = um arquivo .docx salvo (snapshot da minuta)
  - Rodada  = transição entre duas versões consecutivas do mesmo processo;
              atribuída a quem salvou a versão resultante (lastModifiedBy)
  - Comentário único = (processo, autor, data, tamanho) — o mesmo comentário
              persiste em várias versões do arquivo e é contado uma única vez
  - Etapas nominais = tokens da cadeia de revisão no nome do arquivo da
              versão mais recente (inclui marcos institucionais: GDM, TR, ...)

Uso: python3 dashboard/extract_stats.py && python3 dashboard/build_dashboard.py
"""
import json
import os
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data.json")
HTML = os.path.join(HERE, "index.html")

# iniciais (tokens do nome do arquivo) -> nome canônico do revisor
INITIALS = {
    "oc": "Olívia Carvalho",
    "lk": "Leonardo Kim",
    "cz": "Caroline Zentner",
    "rpf": "Renan Peron Fineto",
    "lrs": "Lucas Ramos da Silva",
    "lr": "Lucas Ramos da Silva",
    "pr": "Paulo Rocha",
}
# variações de nome nos metadados -> nome canônico
NAME_MAP = {
    "Paulo Eduardo Nobrega Rocha": "Paulo Rocha",
    "Lucas Ramos Da Silva": "Lucas Ramos da Silva",
}
# tokens de marcos institucionais na cadeia de revisão
MILESTONES = {
    "gdm": "GDM", "dm": "DM", "tr": "TR (Termo de Referência)",
    "dt": "DT", "dcp": "DCP", "gtp": "GTP", "res": "Resolução 11",
}
NOISE_TOKENS = {"sem", "anexo"}  # anotações no nome do arquivo, não são etapas


def canon(name):
    return NAME_MAP.get(name, name) if name else name


def parse_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def days_between(a, b):
    return round((parse_dt(b) - parse_dt(a)).total_seconds() / 86400, 2)


def chain_tokens(rec):
    return [t for t in rec["revChainNorm"] if t not in NOISE_TOKENS]


def comment_key(sei, c):
    return (sei, canon(c["author"]), c["date"], c["chars"])


def mean(xs):
    return round(statistics.mean(xs), 1) if xs else None


def median(xs):
    return round(statistics.median(xs), 1) if xs else None


def main():
    with open(DATA, encoding="utf-8") as f:
        raw = json.load(f)

    by_sei = defaultdict(list)
    for r in raw:
        by_sei[r["sei"]].append(r)

    processes = []
    all_rounds = []                       # durações e metadados de todas as rodadas
    reviewer_comments = defaultdict(set)  # revisor -> chaves de comentários únicos
    reviewer_words = defaultdict(list)    # revisor -> tamanho (palavras) por comentário
    reviewer_rounds = defaultdict(list)   # revisor -> durações de rodadas executadas
    reviewer_procs = defaultdict(set)
    monthly = defaultdict(Counter)        # mês -> revisor -> comentários únicos
    monthly_versions = Counter()          # mês -> versões salvas
    heat = Counter()                      # (dia-da-semana, hora) -> comentários únicos

    for sei, recs in by_sei.items():
        recs.sort(key=lambda r: (len(chain_tokens(r)), r["modified"] or ""))
        title = next((r["title"] for r in recs if r["title"]), None) or "(sem objeto)"
        modality = recs[0]["modality"]

        versions = []
        seen_keys = set()
        proc_comments = set()
        proc_by_reviewer = Counter()
        for i, r in enumerate(recs):
            keys = {comment_key(sei, c) for c in r["comments"]}
            new_keys = keys - seen_keys
            seen_keys |= keys
            for c in r["comments"]:
                k = comment_key(sei, c)
                if k in proc_comments:
                    continue
                proc_comments.add(k)
                author = canon(c["author"])
                proc_by_reviewer[author] += 1
                reviewer_comments[author].add(k)
                reviewer_words[author].append(c["words"])
                reviewer_procs[author].add(sei)
                d = parse_dt(c["date"])
                if d:
                    monthly[d.strftime("%Y-%m")][author] += 1
                    heat[(d.weekday(), d.hour)] += 1
            if r["modified"]:
                monthly_versions[parse_dt(r["modified"]).strftime("%Y-%m")] += 1
            versions.append({
                "file": r["file"],
                "chain": " ".join(r["revChain"]) or "(base)",
                "chainLen": len(chain_tokens(r)),
                "modified": r["modified"],
                "savedBy": canon(r["lastModifiedBy"]),
                "creator": canon(r["creator"]),
                "activeComments": len(r["comments"]),
                "newComments": len(new_keys),
                "pages": r.get("pages"),
                "words": r.get("words"),
                "editMinutes": r.get("editMinutes"),
                "isDup": r["isDup"],
            })

        rounds = []
        for i in range(1, len(versions)):
            a, b = versions[i - 1], versions[i]
            if not (a["modified"] and b["modified"]):
                continue
            dur = max(days_between(a["modified"], b["modified"]), 0)
            added = [t for t in chain_tokens(recs[i])
                     if t not in chain_tokens(recs[i - 1])] or None
            rnd = {
                "idx": i,
                "start": a["modified"],
                "end": b["modified"],
                "days": dur,
                "by": b["savedBy"],
                "tokenAdded": recs[i]["revChain"][len(recs[i - 1]["revChain"]):] or None,
                "newComments": b["newComments"],
            }
            rounds.append(rnd)
            all_rounds.append(dur)
            if b["savedBy"]:
                reviewer_rounds[b["savedBy"]].append(dur)

        final = versions[-1]
        final_tokens = chain_tokens(recs[-1])
        milestones = [MILESTONES[t] for t in final_tokens if t in MILESTONES]
        lead = (days_between(versions[0]["modified"], final["modified"])
                if len(versions) > 1 and versions[0]["modified"] and final["modified"]
                else None)
        round_durs = [r["days"] for r in rounds]
        processes.append({
            "sei": sei,
            "title": title,
            "modality": modality,
            "placeholder": bool(re.fullmatch(r"[0X]+(-.*)?", sei or "")
                                or "X" in (sei or "")),
            "nVersions": len(versions),
            "nStages": len(final_tokens),
            "nRoundsObserved": len(rounds),
            "leadDays": lead,
            "avgRoundDays": mean(round_durs),
            "medianRoundDays": median(round_durs),
            "totalComments": len(proc_comments),
            "commentsByReviewer": dict(proc_by_reviewer),
            "reviewers": sorted(set(list(proc_by_reviewer) +
                                    [v["savedBy"] for v in versions if v["savedBy"]])),
            "firstDate": versions[0]["modified"],
            "lastDate": final["modified"],
            "finalPages": final["pages"],
            "finalWords": final["words"],
            "editHours": round(final["editMinutes"] / 60, 1) if final["editMinutes"] else None,
            "milestones": milestones,
            "versions": versions,
            "rounds": rounds,
        })

    processes.sort(key=lambda p: (p["lastDate"] or ""), reverse=True)

    # ranking fixo de revisores (ordem de slot de cor: por comentários únicos, desc)
    reviewers = []
    order = sorted(reviewer_comments, key=lambda a: -len(reviewer_comments[a]))
    for slot, name in enumerate(order, start=1):
        durs = reviewer_rounds.get(name, [])
        reviewers.append({
            "name": name,
            "slot": slot,
            "uniqueComments": len(reviewer_comments[name]),
            "avgCommentWords": mean(reviewer_words[name]),
            "roundsExecuted": len(durs),
            "avgRoundDays": mean(durs),
            "medianRoundDays": median(durs),
            "nProcesses": len(reviewer_procs[name]),
        })

    multi = [p for p in processes if p["leadDays"] is not None]
    total_new_comments = sum(r["newComments"] for p in processes for r in p["rounds"])
    months = sorted(set(list(monthly) + list(monthly_versions)))
    glob = {
        "nProcesses": len(processes),
        "nFiles": len(raw),
        "nRoundsObserved": len(all_rounds),
        "nStagesTotal": sum(p["nStages"] for p in processes),
        "nUniqueComments": sum(len(v) for v in reviewer_comments.values()),
        "nReviewers": len(reviewers),
        "avgLeadDays": mean([p["leadDays"] for p in multi]),
        "medianLeadDays": median([p["leadDays"] for p in multi]),
        "avgRoundDays": mean(all_rounds),
        "medianRoundDays": median(all_rounds),
        "avgRoundsPerProcess": mean([p["nStages"] for p in processes if p["nStages"]]),
        "avgCommentsPerRound": (round(total_new_comments / len(all_rounds), 1)
                                if all_rounds else None),
        "modalities": dict(Counter(p["modality"] for p in processes)),
        "months": months,
        "monthlyComments": {m: dict(monthly[m]) for m in months},
        "monthlyVersions": {m: monthly_versions.get(m, 0) for m in months},
        "heatmap": [[heat.get((wd, h), 0) for h in range(24)] for wd in range(7)],
        "dateRange": [min(p["firstDate"] for p in processes if p["firstDate"]),
                      max(p["lastDate"] for p in processes if p["lastDate"])],
    }

    payload = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "global": glob,
        "reviewers": reviewers,
        "processes": processes,
    }

    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = re.sub(
        r'(<script id="data" type="application/json">).*?(</script>)',
        lambda m: m.group(1) + blob + m.group(2),
        html, count=1, flags=re.DOTALL)
    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"dataset injetado em {HTML}: {len(processes)} processos, "
          f"{glob['nUniqueComments']} comentários únicos, "
          f"{glob['nRoundsObserved']} rodadas observadas")


if __name__ == "__main__":
    main()
