#!/usr/bin/env python3
"""Build a SKY130 functional model view from *actual* Yosys mapped cell inventory.

Uses upstream wrapper sources with Icarus preprocessor; never guesses from ABC logs.
This artifact is simulation-only and is not a PDK timing qualification.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path

CELL = re.compile(r'^sky130_fd_sc_hd__(.+)_([0-9]+)$')

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assemble(mapped: dict, top: str, source: Path, output: Path) -> dict:
    source = source.resolve(strict=True)
    if not (source / 'cells').is_dir() or not (source / 'models').is_dir():
        raise ValueError('SKY130 source tree must contain cells/ and models/')
    modules = mapped.get('modules', {})
    if top not in modules:
        raise ValueError('mapped top is missing')
    types = sorted({c['type'] for c in modules[top].get('cells', {}).values()})
    if not types:
        raise ValueError('mapped design contains no cells')
    wrappers = []
    for typ in types:
        match = CELL.fullmatch(typ)
        if not match:
            raise ValueError('not a SKY130 HD mapped cell: ' + typ)
        wrapper = source / 'cells' / match.group(1) / (typ + '.v')
        if not wrapper.is_file():
            raise FileNotFoundError('missing mapped cell wrapper: ' + str(wrapper))
        wrappers.append(wrapper)
    includes = sorted({p.parent for p in (source/'cells').rglob('*.v')} |
                      {p.parent for p in (source/'models').rglob('*.v')})
    output.parent.mkdir(parents=True, exist_ok=True)
    # Input file paths and macro selection are explicit. Never define NO_PRIMITIVES.
    cmd = ['iverilog','-g2012','-grelative-include','-E','-DFUNCTIONAL',
           '-DUNIT_DELAY=','-o',str(output)]
    for d in includes:
        cmd += ['-I',str(d)]
    cmd += [str(w) for w in wrappers]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('SKY130 preprocessor failed to launch') from exc
    (output.parent/(output.stem+'.preprocess.log')).write_text(cp.stdout+'\n'+cp.stderr)
    if cp.returncode or not output.is_file() or not output.stat().st_size:
        raise RuntimeError('SKY130 preprocessing failed; inspect preprocess log')
    text = output.read_text(errors='replace')
    definitions = set(re.findall(r'\bmodule\s+(sky130_fd_sc_hd__[\w$]+)',text))
    missing = sorted(set(types)-definitions)
    if missing:
        raise RuntimeError('cell wrappers not defined in functional model: '+', '.join(missing))
    if re.search(r'(?m)^\s*`include\s', text):
        raise RuntimeError('unresolved include in functional bundle')
    record = {'mode':'SKY130_HD_FUNCTIONAL_NO_POWER_PINS', 'source_root':str(source),
              'model_sha256':sha(output),'mapped_cell_types':types,
              'wrappers':[{ 'path':str(w.relative_to(source)), 'sha256':sha(w)} for w in wrappers]}
    (output.parent/(output.stem+'.provenance.json')).write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    return record
