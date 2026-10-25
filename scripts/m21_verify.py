#!/usr/bin/env python3
"""M2.1 exhaustive RTL scalar test and Yosys SAT proof; strict fail-closed evidence."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

RTL = r'''module msif_int4_int8_equiv(input signed [3:0] w, input signed [7:0] x, output signed [15:0] product);
  wire signed [15:0] sx = {{8{x[7]}}, x};
  wire signed [15:0] shift_add =
      (w[0] ? sx : 16'sd0)
    + (w[1] ? (sx <<< 1) : 16'sd0)
    + (w[2] ? (sx <<< 2) : 16'sd0)
    - (w[3] ? (sx <<< 3) : 16'sd0);
  wire signed [15:0] mul_ref = $signed(w) * $signed(x);
  assign product = shift_add;
`ifdef FORMAL
  always @* assert(shift_add == mul_ref);
`endif
endmodule
'''
TB = r'''module tb;
 reg signed [3:0] w;
 reg signed [7:0] x;
 wire signed [15:0] product;
 integer wi, xi, count;
 msif_int4_int8_equiv dut (.w(w), .x(x), .product(product));
 initial begin
  count=0;
  for (wi=-8; wi<=7; wi=wi+1) begin
   for (xi=-128; xi<=127; xi=xi+1) begin
    w=wi; x=xi; #1;
    if (product !== (wi*xi)) begin
     $display("FAIL w=%0d x=%0d got=%0d expected=%0d",wi,xi,product,wi*xi);
     $fatal(1);
    end
    count=count+1;
   end
  end
  if (count != 4096) $fatal(1,"Wrong vector count");
  $display("PASS M2.1 exhaustive RTL 4096 vectors");
  $finish;
 end
endmodule
'''

def run(cmd, logfile, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    logfile.write_text('$ ' + ' '.join(map(str,cmd)) + '\n' + result.stdout)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {cmd[0]}; see {logfile}')
    return result.stdout

def validate_simulation_output(output: str) -> None:
    """Reject simulator errors even if a testbench later prints PASS."""
    import re
    if re.search(r'(?m)^\s*(?:ERROR:|FATAL:|FAIL(?:\s|:)|WARNING:)', output):
        raise RuntimeError('Simulator emitted error/failure/warning diagnostics; cannot approve')
    markers = [line.strip() for line in output.splitlines()
               if line.strip() == 'PASS M2.1 exhaustive RTL 4096 vectors']
    if len(markers) != 1:
        raise RuntimeError('Expected exactly one 4096-vector PASS marker')


def validate_formal_output(output: str) -> None:
    if 'SAT proof finished - no model found: SUCCESS!' not in output:
        raise RuntimeError('Formal proof success marker missing')
    if 'FAIL' in output or 'ERROR:' in output:
        raise RuntimeError('Formal proof includes error/failure output')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out', default='build/m21')
    args=p.parse_args()
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    for command in ('iverilog','vvp','yosys'):
        if not shutil.which(command):
            raise SystemExit(f'BLOCKED: missing required tool {command}')
    (out/'evidence.json').unlink(missing_ok=True)  # never reuse stale PASS evidence
    rtl=out/'msif_int4_int8_equiv.sv'; tb=out/'tb_exhaustive.sv'
    rtl.write_text(RTL); tb.write_text(TB)
    sim=out/'m21_exhaustive.vvp'
    run(['iverilog','-g2012','-s','tb','-o',str(sim),str(rtl),str(tb)],out/'compile.log')
    output=run(['vvp',str(sim)],out/'exhaustive.log')
    validate_simulation_output(output)
    # SAT proof covers all 4096 inputs symbolically, independent from simulation.
    yosys_cmd='read_verilog -D FORMAL -formal -sv '+str(rtl)+'; hierarchy -check -top msif_int4_int8_equiv; proc; flatten; opt; sat -verify -prove-asserts -show w,x'
    proof=run(['yosys','-Q','-T','-p',yosys_cmd],out/'formal.log')
    validate_formal_output(proof)
    evidence={'schema':'msif-m21-evidence-v1','qualification':'scalar-int4-int8-only','rtl_vectors':4096,'formal_proof':'PASS','rtl_simulation':'PASS','limitations':['No full GEMV formal equivalence','No technology-mapped PPA','No governance approval'],'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [rtl,tb,out/'compile.log',out/'exhaustive.log',out/'formal.log']}}
    (out/'evidence.json').write_text(json.dumps(evidence,sort_keys=True,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':
    main()
