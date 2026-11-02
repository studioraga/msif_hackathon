#!/usr/bin/env python3
"""Compare accepted Yosys JSON mapped graph against OpenDB export with renaming-invariant net partitions."""
import argparse,collections,json,sys
from pathlib import Path
def signatures(cells,ports):
    nets=collections.defaultdict(list)
    for name,c in cells.items():
        for pin,bits in c['connections'].items():
            for ix,net in enumerate(bits):nets[str(net)].append(('cell',name,pin,ix))
    for name,p in ports.items():
        for ix,net in enumerate(p['bits']):nets[str(net)].append(('port',name,ix))
    return sorted(tuple(sorted(v)) for v in nets.values())
def compare(yosys,odb):
    top=next(n for n in yosys['modules'] if n.startswith('msif_') and n in ('msif_programmable','msif_fixed','msif_rom'))
    m=yosys['modules'][top]
    expected=collections.Counter((n,c['type']) for n,c in m['cells'].items())
    got={};pinrows=collections.defaultdict(dict);portrows={}
    for line in odb.splitlines():
        p=line.split('\t')
        if p[0]=='CELL' and len(p)==3:got[p[1]]=p[2]
        elif p[0]=='PIN' and len(p)==4:pinrows[p[1]][p[2]]=p[3]
        elif p[0]=='PORT' and len(p)==3:portrows[p[1]]=p[2]
        else:raise ValueError('invalid graph export row '+line)
    if expected!=collections.Counter(got.items()):raise ValueError('cell name/master inventory differs')
    if len(portrows)!=sum(len(p['bits']) for p in m['ports'].values()):
        raise ValueError('port bit count differs')
    # Obtain source graph connectivity indexed by unique bit-level endpoint labels.
    source=collections.defaultdict(set)
    for n,c in m['cells'].items():
        for pin,bits in c['connections'].items():
            for i,bit in enumerate(bits):source[str(bit)].add(('C',n,pin,i))
    for n,p in m['ports'].items():
        for i,bit in enumerate(p['bits']):source[str(bit)].add(('P',n,i))
    actual=collections.defaultdict(set)
    for n,pm in pinrows.items():
        for pin,net in pm.items():actual[net].add(('C',n,pin,0))
    for n,net in portrows.items():actual[net].add(('P',n,0))
    # Bus-bit normalization and const nets vary across OpenDB builds; report unsupported, not PASS.
    if any(len(bits)!=1 for c in m['cells'].values() for bits in c['connections'].values()):
        raise ValueError('multi-bit cell pins require pinned OpenDB bit mapping')
    if source.values() and actual.values():
        src=collections.Counter(frozenset(v) for v in source.values())
        dst=collections.Counter(frozenset(v) for v in actual.values())
        if src!=dst:raise ValueError('connectivity partitions differ; inspect constant and port naming')
    return len(got)
def main():
    p=argparse.ArgumentParser();p.add_argument('--json',type=Path,required=True);p.add_argument('--graph',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:
        count=compare(json.loads(a.json.read_text()),a.graph.read_text())
        obj={'status':'EXACT_IMPORTED_GRAPH_MATCH_NOT_SEQUENTIAL_PROOF','cells':count}
        a.out.write_text(json.dumps(obj,indent=2)+'\n');print(obj);return 0
    except (ValueError,KeyError,StopIteration) as e:
        print('BLOCKED P2b graph:',e,file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
