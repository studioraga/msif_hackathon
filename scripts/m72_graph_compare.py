#!/usr/bin/env python3
"""Compare two independently exported OpenDB graphs for the same SHA-pinned mapped Verilog.
This is an initial-import structural check, not sequential or post-ECO equivalence.
"""
import argparse, collections, hashlib, json, sys
from pathlib import Path

SUPPLY = {'VPWR','VGND','VPB','VNB','VDD','VSS','VCCD1','VSSD1','VDDIO','VSSIO'}

def parse(path):
    cells = {}; pins = collections.defaultdict(dict); ports = {}; errors=[]
    for lineno, line in enumerate(path.read_text().splitlines(),1):
        a=line.split('\t')
        if len(a)==3 and a[0]=='CELL':
            if a[1] in cells: errors.append(f'duplicate CELL {a[1]}')
            cells[a[1]]=a[2]
        elif len(a)==4 and a[0]=='PIN':
            if a[2] in pins[a[1]]: errors.append(f'duplicate PIN {a[1]}/{a[2]}')
            pins[a[1]][a[2]]=a[3]
        elif len(a)==3 and a[0]=='PORT':
            if a[1] in ports: errors.append(f'duplicate PORT {a[1]}')
            ports[a[1]]=a[2]
        else: errors.append(f'invalid row {lineno}')
    for inst in pins:
        if inst not in cells: errors.append(f'PIN on unknown CELL {inst}')
    if errors or not cells or not ports: raise ValueError('; '.join(errors) or 'empty cells/ports')
    return cells,pins,ports

def canonical(path):
    cells,pins,ports=parse(path)
    nets=collections.defaultdict(list)
    disconnected=[]; supply=[]
    for inst, master in cells.items():
        if inst not in pins: raise ValueError(f'instance missing ITerms: {inst}')
        for pin,net in pins[inst].items():
            ep=('cell',inst,pin)
            if net=='__UNCONNECTED__':
                if pin in SUPPLY: supply.append(ep)
                else: disconnected.append(ep)
            else: nets[net].append(ep)
    for port,net in ports.items():
        ep=('port',port)
        if net=='__UNCONNECTED__': disconnected.append(ep)
        else: nets[net].append(ep)
    # Compare endpoint partitions, independent of net labels. Endpoint identities remain strict.
    partitions=collections.Counter(tuple(sorted(eps)) for eps in nets.values())
    return {
      'cells':cells, 'pins':{n:dict(p) for n,p in pins.items()}, 'ports':ports,
      'partitions':partitions, 'disconnected':sorted(disconnected),
      'unconnected_supply':sorted(supply),
    }

def compare(reference, candidate):
    a,b=canonical(reference),canonical(candidate)
    diffs=[]
    for field in ('cells','ports','disconnected','unconnected_supply'):
        if field=='ports':
            if set(a[field])!=set(b[field]):diffs.append('port names differ')
        elif a[field]!=b[field]:diffs.append(field+' differs')
    if {x:set(p) for x,p in a['pins'].items()} != {x:set(p) for x,p in b['pins'].items()}:
        diffs.append('pin inventory differs')
    if a['partitions']!=b['partitions']:diffs.append('net endpoint connectivity differs')
    return diffs, {'cells':len(a['cells']), 'ports':len(a['ports']), 'net_partitions':sum(a['partitions'].values()), 'unconnected_supply_pins':len(a['unconnected_supply'])}

def main():
    p=argparse.ArgumentParser()
    for arg in ('reference','candidate','out'):p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    try:
        diffs,stats=compare(a.reference,a.candidate)
        result={'schema':'msif-m72-p2b-odb-graph-v2','status':'INITIAL_IMPORTED_GRAPH_MATCH_NOT_FORMAL' if not diffs else 'BLOCKED_GRAPH_MISMATCH',
            'reference_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),
            'candidate_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
            'differences':diffs,'statistics':stats,'formal_sequential_equivalence':'NOT_VERIFIED','post_route_equivalence':'NOT_VERIFIED'}
        if a.out.exists():raise ValueError('refusing to overwrite existing receipt')
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'status':result['status'],'out':str(a.out)}))
        return 0 if not diffs else 2
    except (ValueError,OSError) as e:
        print(f'BLOCKED graph comparison: {e}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
