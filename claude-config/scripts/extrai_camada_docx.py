#!/usr/bin/env python3
"""Extrai a camada Word que a conversão pandoc→markdown destrói.

Uso: python3 extrai_camada_docx.py <arquivo.docx> <saida.md>

Gera um extrato estruturado com:
- comentários embutidos (word/comments.xml): autor, data, texto e trecho ancorado;
- runs realçados (w:highlight) por cor, com o texto do run — FT-01 (amarelo) / FT-02 (vermelho);
- track changes não aceitos (w:ins / w:del): contagem;
- runs com fonte diferente de Arial ou tamanho diferente de 12 — FT-07 (contagem + amostra);
- células mescladas em tabelas (vMerge / gridSpan) — FT-04 (contagem);
- hiperlinks e seus alvos (word/_rels/document.xml.rels) — FT-08.

Somente leitura sobre o .docx; escreve apenas o arquivo de saída indicado.
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}
W = NS['w']


def qn(tag):
    return f'{{{W}}}{tag}'


def run_text(run):
    return ''.join(t.text or '' for t in run.iter(qn('t')))


def main(docx_path, out_path):
    z = zipfile.ZipFile(docx_path)
    doc = ET.fromstring(z.read('word/document.xml'))

    linhas = [f'# Camada Word extraída de {docx_path}', '']

    # --- comentários -------------------------------------------------------
    linhas.append('## Comentários embutidos (word/comments.xml)')
    if 'word/comments.xml' in z.namelist():
        com = ET.fromstring(z.read('word/comments.xml'))
        comentarios = com.findall(qn('comment'))
        linhas.append(f'Total: {len(comentarios)}')
        # âncoras: texto entre commentRangeStart/End no document.xml
        ancoras = {}
        atual, buf = None, []
        for el in doc.iter():
            if el.tag == qn('commentRangeStart'):
                atual, buf = el.get(qn('id')), []
            elif el.tag == qn('commentRangeEnd'):
                if atual is not None:
                    ancoras[atual] = ' '.join(''.join(buf).split())[:200]
                atual, buf = None, []
            elif atual is not None and el.tag == qn('t'):
                buf.append(el.text or '')
        for c in comentarios:
            cid = c.get(qn('id'))
            autor = c.get(qn('author'), '?')
            data = c.get(qn('date'), '?')
            texto = ' '.join(''.join(t.text or '' for t in c.iter(qn('t'))).split())
            anc = ancoras.get(cid, '(âncora não localizada)')
            linhas.append(f'- [{cid}] {autor} ({data}): "{texto}" — ancorado em: "{anc}"')
    else:
        linhas.append('Nenhum (word/comments.xml ausente).')
    linhas.append('')

    # --- realces -----------------------------------------------------------
    linhas.append('## Realces (w:highlight) — FT-01 amarelo / FT-02 vermelho')
    por_cor = {}
    for run in doc.iter(qn('r')):
        rpr = run.find(qn('rPr'))
        if rpr is None:
            continue
        hl = rpr.find(qn('highlight'))
        if hl is None:
            continue
        cor = hl.get(qn('val'), '?')
        txt = ' '.join(run_text(run).split())
        if txt:
            por_cor.setdefault(cor, []).append(txt)
    if por_cor:
        for cor, textos in sorted(por_cor.items()):
            linhas.append(f'### cor: {cor} — {len(textos)} run(s)')
            for t in textos:
                linhas.append(f'- "{t[:160]}"')
    else:
        linhas.append('Nenhum realce encontrado.')
    linhas.append('')

    # --- track changes -----------------------------------------------------
    ins = len(list(doc.iter(qn('ins'))))
    dele = len(list(doc.iter(qn('del'))))
    linhas.append('## Track changes não aceitos')
    linhas.append(f'w:ins = {ins} · w:del = {dele}')
    linhas.append('')

    # --- fontes fora de Arial 12 (FT-07) -----------------------------------
    fora = []
    for run in doc.iter(qn('r')):
        rpr = run.find(qn('rPr'))
        if rpr is None:
            continue
        motivo = []
        rf = rpr.find(qn('rFonts'))
        if rf is not None:
            fonte = rf.get(qn('ascii')) or rf.get(qn('hAnsi'))
            if fonte and fonte.lower() != 'arial':
                motivo.append(f'fonte={fonte}')
        sz = rpr.find(qn('sz'))
        if sz is not None and sz.get(qn('val')) not in (None, '24'):  # 24 half-points = 12pt
            motivo.append(f'tamanho={int(sz.get(qn("val"))) / 2:g}pt')
        if motivo:
            txt = ' '.join(run_text(run).split())
            if txt:
                fora.append((', '.join(motivo), txt[:80]))
    linhas.append('## Fonte fora de Arial 12 (FT-07)')
    linhas.append(f'Total de runs: {len(fora)}')
    for m, t in fora[:40]:
        linhas.append(f'- ({m}) "{t}"')
    if len(fora) > 40:
        linhas.append(f'... e mais {len(fora) - 40} runs (amostra truncada).')
    linhas.append('')

    # --- células mescladas (FT-04) -----------------------------------------
    vmerge = len(list(doc.iter(qn('vMerge'))))
    gridspan = len(list(doc.iter(qn('gridSpan'))))
    linhas.append('## Células mescladas em tabelas (FT-04)')
    linhas.append(f'vMerge = {vmerge} · gridSpan = {gridspan}')
    linhas.append('')

    # --- hiperlinks (FT-08) ------------------------------------------------
    linhas.append('## Hiperlinks (FT-08)')
    rels_path = 'word/_rels/document.xml.rels'
    if rels_path in z.namelist():
        rels = z.read(rels_path).decode('utf-8', errors='replace')
        alvos = re.findall(r'Target="([^"]+)"[^>]*TargetMode="External"', rels)
        alvos += re.findall(r'TargetMode="External"[^>]*Target="([^"]+)"', rels)
        alvos = sorted(set(alvos))
        linhas.append(f'Total de alvos externos: {len(alvos)}')
        for a in alvos:
            linhas.append(f'- {a}')
    else:
        linhas.append('Sem relacionamentos externos.')
    linhas.append('')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')
    print(f'Extrato gravado em {out_path}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
