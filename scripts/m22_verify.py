#!/usr/bin/env python3
"""M2.2: independently check small-shape GEMV combinational arithmetic and sequential behavior."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from msif.core import fixture, generate, inference, signed_literal, check
from msif.simulation import test_vectors

VARIANTS = ('programmable', 'fixed', 'rom')
MARKER = 'PASS M2.2 sequential 2x4 36 vectors'

def pack(values, bits):
    return ''.join(f'{v & ((1 << bits)-1):0{bits//4}x}' for v in reversed(values))

def formal_rtl(model):
    m,k=check(model)
    if (m,k)!=(2,4):
        raise ValueError('M2.2 bounded formal shape must be 2x4')
    # Independent expressions: ordinary multiplication vs constant shift/add.
    lines=['module msif_m22_comb(input wire signed [31:0] activations);']
    for i,row in enumerate(model['weights']):
        reference=[signed_literal(model['bias'][i],32)]
        optimized=[signed_literal(model['bias'][i],32)]
        for j,w in enumerate(row):
            byte=f'activations[{j*8} +: 8]'
            sx=f'$signed({{{{24{{activations[{j*8+7}]}}}}, {byte}}})'
            reference.append(f'({sx} * {signed_literal(w,32)})')
            # Avoid multiplying in the optimized path; each coefficient is decomposed into signed bits.
            bits=w & 0xf
            terms=[]
            for bit in range(4):
                if bits & (1<<bit):
                    term=sx if bit==0 else f'({sx} <<< {bit})'
                    terms.append(f'(-{term})' if bit==3 else term)
            optimized.append('('+' + '.join(terms)+')' if terms else "32'sd0")
        lines.extend([f'  wire signed [31:0] ref_{i} = '+' + '.join(reference)+';',
                      f'  wire signed [31:0] opt_{i} = '+' + '.join(optimized)+';',
                      f'  always @* assert (ref_{i} == opt_{i});'])
    lines.extend(['endmodule',''])
    return '\n'.join(lines)

def sequential_tb(model,variant,vectors):
    m,k=check(model)
    if (m,k)!=(2,4): raise ValueError('shape')
    lines=[f'''module tb;
 reg clk=0, rst_n=1, in_valid=0;
 reg signed [31:0] activations=0;
 wire out_valid;
 wire signed [63:0] result;
 msif_{variant} dut(.clk(clk),.rst_n(rst_n),.in_valid(in_valid),.activations(activations),.out_valid(out_valid),.result(result));
 always #5 clk=~clk;
 initial begin
  #1; rst_n=0; #1; // explicit negedge guarantees asynchronous reset event
  if (out_valid !== 1'b0 || result !== 64'b0) $fatal(1,"async reset failed");
  @(negedge clk); rst_n=1;
''']
    for idx,vec in enumerate(vectors):
        expected=pack(inference(model,vec),32)
        lines += [f"  activations=32'h{pack(vec,8)}; in_valid=1'b1;",
                  '  @(posedge clk); #1;',
                  f"  if (out_valid !== 1'b1 || result !== 64'h{expected}) $fatal(1,\"vector {idx}\");",
                  '  @(negedge clk);']
        # Check invalid-cycle output hold every ninth vector.
        if idx%9==0:
            lines += ["  in_valid=1'b0; activations=32'hffffffff;",
                      '  @(posedge clk); #1;',
                      f"  if (out_valid !== 1'b0 || result !== 64'h{expected}) $fatal(1,\"invalid hold {idx}\");",
                      '  @(negedge clk);']
    lines += ["  rst_n=1'b0; #1;",
              "  if (out_valid !== 1'b0 || result !== 64'b0) $fatal(1,\"mid-stream async reset\");",
              '  @(negedge clk);',
              f'  $display("PASS M2.2 {variant} sequential 2x4 {len(vectors)} vectors");',
              '  $finish;', ' end', 'endmodule', '']
    return '\n'.join(lines)

def require_clean(output, marker):
    if re.search(r'(?im)^\s*(?:ERROR:|FATAL:|FAIL(?:\s|:)|WARNING:|%Error|%Warning)', output):
        raise RuntimeError('ERROR or warning diagnostics in run')
    if sum(line.strip()==marker for line in output.splitlines())!=1:
        raise RuntimeError(f'expected exactly one marker: {marker}')

def run(args, log):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
    log.write_text('$ '+' '.join(map(str,args))+'\n'+p.stdout)
    if p.returncode: raise RuntimeError(f'{args[0]} exited {p.returncode}; see {log}')
    return p.stdout

def execute(out, seed):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'evidence.json').unlink(missing_ok=True)
    for exe in ('iverilog','vvp','yosys','verilator'):
        if not shutil.which(exe): raise RuntimeError(f'missing {exe}')
    model=fixture(2,4,seed)
    (out/'model.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
    formal=out/'small_gemv_equiv.sv';formal.write_text(formal_rtl(model))
    formal_log=out/'formal.log'
    proof=run(['yosys','-Q','-T','-p',f'read_verilog -formal -sv {formal}; hierarchy -check -top msif_m22_comb; proc; flatten; opt; sat -verify -prove-asserts -show activations'],formal_log)
    if 'SAT proof finished - no model found: SUCCESS!' not in proof or 'ERROR:' in proof or 'FAIL' in proof:
        raise RuntimeError('Yosys formal proof not successful')
    lint=run(['verilator','--lint-only','--sv','--top-module','msif_m22_comb',formal],out/'formal_lint.log')
    if re.search(r'%Warning|%Error',lint): raise RuntimeError('Verilator lint diagnostic')
    vectors=test_vectors(model,32)
    for variant in VARIANTS:
        rtl=out/f'msif_{variant}.sv';rtl.write_text(generate(model,variant))
        tb=out/f'tb_{variant}.sv';tb.write_text(sequential_tb(model,variant,vectors))
        sim=out/f'{variant}.vvp'
        compile_log=out/f'compile_{variant}.log'
        run(['iverilog','-g2012','-s','tb','-o',sim,rtl,tb],compile_log)
        output=run(['vvp',sim],out/f'sim_{variant}.log')
        require_clean(output,f'PASS M2.2 {variant} sequential 2x4 {len(vectors)} vectors')
        lint_output=run(['verilator','--lint-only','--sv','--top-module',f'msif_{variant}',rtl],out/f'lint_{variant}.log')
        if re.search(r'%Warning|%Error',lint_output): raise RuntimeError(f'lint failed {variant}')
    logs=sorted(out.glob('*.log'))
    sources=[formal,out/'model.json',*sorted(out.glob('*.sv'))]
    evidence={'schema':'msif-m22-evidence-v1','qualification':'bounded-2x4-combinational-proof-and-sequential-simulation','seed':seed,
              'formal_proof':'PASS','simulation':'PASS','vectors_per_variant':len(vectors),
              'variants':list(VARIANTS),
              'limitations':['Full 16x64 formal proof unverified','No physical PPA','No governed release'],
              'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sources+logs}}
    (out/'evidence.json').write_text(json.dumps(evidence,sort_keys=True,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='build/m22');p.add_argument('--seed',type=int,default=2026)
    a=p.parse_args();execute(a.out,a.seed)
if __name__=='__main__': main()
