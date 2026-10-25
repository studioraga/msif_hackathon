'Independent cycle simulation of generated RTL using Icarus Verilog.'
import json
import random
import shutil
import subprocess
from pathlib import Path
from .core import inference, check
from .governance import validate_manifest

VARIANTS=('programmable','fixed','rom')

def test_vectors(model, n=24):
    _, k=check(model)
    rng=random.Random(781)
    v=[[0]*k, [127]*k, [-128]*k,
       [(-128 if i%2 else 127) for i in range(k)]]
    v.extend([[rng.randint(-128,127) for _ in range(k)] for __ in range(n)])
    return v

def create_testbench(model, vectors, variant):
    m,k=check(model)
    # Hex vectors represent two's-complement packed bytes and 32-bit words.
    def pack(values,bits):
        return ''.join(f'{v&((1<<bits)-1):0{bits//4}x}' for v in reversed(values))
    lines=[f'''module tb;
reg clk=0, rst_n=0, in_valid=0;
reg signed [{k*8-1}:0] activations=0;
wire out_valid;
wire signed [{m*32-1}:0] result;
msif_{variant} dut(.clk(clk),.rst_n(rst_n),.in_valid(in_valid),.activations(activations),.out_valid(out_valid),.result(result));
always #5 clk=~clk;
initial begin
  @(negedge clk);
  rst_n=1;
''']
    for idx,vec in enumerate(vectors):
        want=inference(model,vec)
        lines.extend([
            f'  activations = {k*8}\'h{pack(vec,8)};',
            '  in_valid=1;',
            '  @(posedge clk);',
            '  #1;',
            f'  if (out_valid !== 1\'b1 || result !== {m*32}\'h{pack(want,32)}) begin',
            f'    $display("FAIL {variant} vector {idx}: got %h",result); $fatal(1); end',
            '  @(negedge clk);',
        ])
    lines.extend(['  in_valid=0;', '  @(posedge clk); #1;',
                  '  if (out_valid !== 1\'b0) $fatal(1,"valid failed to deassert");',
                  f'  $display("PASS {variant} {len(vectors)} vectors");',
                  '  $finish;', 'end', 'endmodule'])
    return '\n'.join(lines)+'\n'

def simulate(folder, n=24):
    if n < 1 or n > 1024: raise ValueError('vectors must be 1..1024')
    if not shutil.which('iverilog') or not shutil.which('vvp'):
        raise RuntimeError('BLOCKED M2: iverilog and vvp are required')
    folder=Path(folder); validate_manifest(folder)
    model=json.loads((folder/'model.json').read_text())
    vectors=test_vectors(model,n)
    for variant in VARIANTS:
        tb=folder/f'tb_{variant}.sv'; executable=folder/f'sim_{variant}.vvp'
        tb.write_text(create_testbench(model,vectors,variant))
        compile_cmd=['iverilog','-g2012','-s','tb','-o',str(executable),str(folder/f'msif_{variant}.sv'),str(tb)]
        result=subprocess.run(compile_cmd,capture_output=True,text=True)
        if result.returncode:
            (folder/f'sim_{variant}.log').write_text(result.stdout+result.stderr)
            raise RuntimeError(f'FAILED RTL compile: {variant} (see sim_{variant}.log)')
        result=subprocess.run(['vvp',str(executable)],capture_output=True,text=True)
        (folder/f'sim_{variant}.log').write_text(result.stdout+result.stderr)
        if result.returncode or f'PASS {variant} {len(vectors)} vectors' not in result.stdout:
            raise RuntimeError(f'FAILED RTL simulation: {variant} (see sim_{variant}.log)')
    return {'variants':list(VARIANTS),'vectors_per_variant':len(vectors),'result':'PASS'}
