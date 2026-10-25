"""Deterministic signed INT4 x INT8 kernel and synthesizable RTL generator.
For the hackathon: integer accumulator only, not the final requantized INT8 interface.
"""
import hashlib, json, random, re
from pathlib import Path

def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x): return hashlib.sha256(canonical(x)).hexdigest()
def fixture(m=16,k=64,seed=2026):
    if not (1<=m<=256 and 1<=k<=4096): raise ValueError('invalid dimensions')
    r=random.Random(seed)
    w=[[r.randint(-8,7) for _ in range(k)] for _ in range(m)]
    b=[r.randint(-1024,1024) for _ in range(m)]
    return {'format':'msif-int4-v1','shape':[m,k],'weights':w,'bias':b,'seed':seed,
            'numeric':{'weight':'int4-twos-complement','activation':'int8-twos-complement','accumulator':'int32','overflow':'reject'}}
def check(model):
    if model.get('format')!='msif-int4-v1': raise ValueError('format')
    m,k=model['shape']; w=model['weights']; b=model['bias']
    if not (1<=m<=256 and 1<=k<=4096 and len(w)==m and len(b)==m): raise ValueError('shape')
    if any(len(row)!=k or any(type(x)!=int or not -8<=x<=7 for x in row) for row in w): raise ValueError('weights')
    if any(type(x)!=int or not -(2**31)<=x<2**31 for x in b): raise ValueError('bias')
    if model['numeric'] != {'weight':'int4-twos-complement','activation':'int8-twos-complement','accumulator':'int32','overflow':'reject'}: raise ValueError('numeric')
    if any(abs(v)+1024*k>=2**31 for v in b): raise ValueError('overflow risk')
    return m,k

def inference(model,x):
    m,k=check(model)
    if len(x)!=k or any(type(a)!=int or not -128<=a<=127 for a in x):raise ValueError('activations')
    return [model['bias'][i]+sum(w*a for w,a in zip(model['weights'][i],x)) for i in range(m)]

def signed_literal(val,width):
    return f"{width}'sd{val}" if val>=0 else f"(-{width}'sd{-val})"

def generate(model,variant='fixed'):
    m,k=check(model)
    if variant not in ('programmable','fixed','rom'):raise ValueError('variant')
    # Common input and output contract, and a one-cycle valid register.
    lines=[f'module msif_{variant} (', 'input wire clk, input wire rst_n, input wire in_valid,',
           f'input wire signed [{8*k-1}:0] activations,',
           f'output reg out_valid, output reg signed [{32*m-1}:0] result);',
           f'wire signed [31:0] sums [0:{m-1}];']
    if variant=='programmable':
        lines.append(f'reg signed [3:0] weights [0:{m*k-1}];')
        lines.append('initial begin')
        for i,row in enumerate(model['weights']):
            for j,v in enumerate(row): lines.append(f'weights[{i*k+j}] = {signed_literal(v,4)};')
        lines.append('end')
    if variant=='rom':
        lines.append(f'reg signed [3:0] rom [0:{m*k-1}];')
        lines.append('initial begin')
        for i,row in enumerate(model['weights']):
            for j,v in enumerate(row): lines.append(f'rom[{i*k+j}] = {signed_literal(v,4)};')
        lines.append('end')
    for i,row in enumerate(model['weights']):
        expr=[signed_literal(model['bias'][i],32)]
        for j,w in enumerate(row):
            x=f'$signed(activations[{8*j} +: 8])'
            if variant=='fixed':
                if w==0: continue
                # Sign extended operand, avoid Verilog's self-determined signed width traps.
                a=f'$signed({{ {{24{{activations[{8*j+7}]}}}}, activations[{8*j} +: 8] }})'
                term= a if w==1 else f'(-{a})' if w==-1 else f'({a} * {signed_literal(w,32)})'
            else:
                name='weights' if variant=='programmable' else 'rom'
                term=f'($signed({name}[{i*k+j}]) * {x})'
            expr.append(term)
        lines.append(f'assign sums[{i}] = '+ ' + '.join(expr)+';')
    lines += ['always @(posedge clk or negedge rst_n) begin',
              "if (!rst_n) begin out_valid <= 1'b0; result <= '0; end",
              'else begin out_valid <= in_valid; if(in_valid) begin']
    for i in range(m):lines.append(f'result[{32*i} +: 32] <= sums[{i}];')
    lines+=['end end end','endmodule']
    return '\n'.join(lines)+'\n'

def write_build(model,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'model.json').write_bytes(canonical(model)+b'\n')
    for v in ('programmable','fixed','rom'): (out/f'msif_{v}.sv').write_text(generate(model,v))
    manifest={'schema':'msif-build-v1','model_sha256':sha(model),'rtl_sha256':{v:hashlib.sha256((out/f'msif_{v}.sv').read_bytes()).hexdigest() for v in ('programmable','fixed','rom')},'contract':'signed-int4-int8-int32-one-cycle-valid'}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return manifest
