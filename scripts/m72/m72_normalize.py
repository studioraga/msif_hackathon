#!/usr/bin/env python3
"""Fail-closed declaration-only normalization for fully mapped ORFS netlists."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DECL = re.compile(r'^(\s*)(input|output|inout|wire)(\s+)signed(\s+(?:\[[^\]\n]+\]\s*)?[a-zA-Z_$\\][^;\n]*;)(\r?\n?)$')
CELL = re.compile(r'^\s*(sky130_fd_sc_hd__[A-Za-z0-9_]+)\s+(\\\S+|[A-Za-z_$][\w$]*)\s*\(', re.M)

def sha(b): return hashlib.sha256(b).hexdigest()

def normalize(s):
    result=[]; modifications=[]
    for i, line in enumerate(s.splitlines(keepends=True),1):
        if re.search(r'\bsigned\b', line) and not line.lstrip().startswith(('//','/*','*')):
            m=DECL.fullmatch(line)
            if not m: raise ValueError(f'unexpected signed construct at line {i}: {line!r}')
            # Require only a single identifier after a supported optional bit range.
            statement=m.group(4).rstrip('; \t\r\n')
            if ',' in statement or '=' in statement: raise ValueError(f'complex declaration at line {i}')
            updated=m.group(1)+m.group(2)+m.group(3)+m.group(4)+m.group(5)
            result.append(updated); modifications.append(i)
        else: result.append(line)
    # A structural netlist without signed declarations needs no rewrite.
    # Preserve all bytes and issue an explicit no-op provenance receipt.
    return ''.join(result), modifications

def run(inp,out):
    if inp.resolve()==out.resolve(): raise ValueError('input and output must be different')
    raw=inp.read_bytes(); text=raw.decode('utf-8'); updated,lines=normalize(text)
    # Prove byte-for-byte restoration of the exact original when the removed keyword is put back.
    original_lines=text.splitlines(keepends=True); final_lines=updated.splitlines(keepends=True)
    assert len(original_lines)==len(final_lines)
    for i,(a,b) in enumerate(zip(original_lines,final_lines),1):
        if i not in lines and a!=b: raise ValueError(f'unexpected change at {i}')
        if i in lines and a.replace('signed','',1)!=b: raise ValueError(f'non-declaration change at {i}')
    # Sanity: cell instances unchanged (whole non-declaration lines are already byte identical).
    if CELL.findall(text)!=CELL.findall(updated): raise ValueError('cell inventory changed')
    if out.exists(): raise ValueError('output exists; refuse overwrite')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(updated.encode('utf-8'))
    receipt={'schema':'msif-m72-normalization-v1','source_sha256':sha(raw),'normalized_sha256':sha(out.read_bytes()),'changed_lines':lines,'normalization_action':'DECLARATION_REWRITE' if lines else 'NOOP_ALREADY_COMPATIBLE','cell_instance_count':len(CELL.findall(text)),'qualification':'SYNTAX_NORMALIZED_ONLY_NOT_PHYSICAL_SIGNOFF'}
    print(json.dumps(receipt,indent=2))
    return receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--receipt',type=Path);a=p.parse_args()
    try:
        result=run(a.input,a.output)
        if a.receipt:
            if a.receipt.exists(): raise ValueError('receipt exists')
            a.receipt.write_text(json.dumps(result,indent=2)+'\n')
    except (OSError,ValueError,AssertionError,UnicodeError) as e:
        print(f'BLOCKED M7.2: {e}',file=sys.stderr);return 1
    return 0
if __name__=='__main__':sys.exit(main())
