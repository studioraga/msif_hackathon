import argparse,json,random,subprocess,shutil
from pathlib import Path
from .core import fixture,write_build,inference
from .governance import validate_manifest,sign_via_pag,verify_via_pag
from .simulation import simulate
from .tensor_import import build_from_tensor

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
 b=sub.add_parser('build');b.add_argument('--out',default='build/demo');b.add_argument('--m',type=int,default=16);b.add_argument('--k',type=int,default=64);b.add_argument('--seed',type=int,default=2026)
 v=sub.add_parser('verify');v.add_argument('--out',default='build/demo');v.add_argument('--pubkey');v.add_argument('--signature')
 s=sub.add_parser('sign');s.add_argument('--out',default='build/demo');s.add_argument('--private-key',required=True);s.add_argument('--public-key',required=True)
 y=sub.add_parser('synthesize');y.add_argument('--out',default='build/demo')
 imp=sub.add_parser('import-tensor');imp.add_argument('--checkpoint',required=True);imp.add_argument('--tensor-key');imp.add_argument('--scale',type=float,required=True);imp.add_argument('--out',default='build/m51');imp.add_argument('--bias-json')
 t=sub.add_parser('sim');t.add_argument('--out',default='build/demo');t.add_argument('--vectors',type=int,default=24)
 args=p.parse_args()
 if args.action=='build':print(json.dumps(write_build(fixture(args.m,args.k,args.seed),args.out),indent=2))
 elif args.action=='import-tensor':
  bias=json.loads(Path(args.bias_json).read_text()) if args.bias_json else None
  print(json.dumps(build_from_tensor(args.checkpoint,args.scale,args.out,args.tensor_key,bias),indent=2))
 elif args.action=='sign':print(sign_via_pag(args.out,args.private_key,args.public_key))
 elif args.action=='verify':
  validate_manifest(args.out)
  if args.pubkey:verify_via_pag(args.out,args.pubkey,args.signature)
  print('PASS: integrity'+(' + PAG Ed25519 signature' if args.pubkey else ' (UNSIGNED; not approved)'))
 elif args.action=='sim':print(json.dumps(simulate(args.out,args.vectors),indent=2))
 elif args.action=='synthesize':
  validate_manifest(args.out)
  if not shutil.which('yosys'):raise SystemExit('BLOCKED: yosys not installed')
  out=Path(args.out)
  for typ in ('programmable','fixed','rom'):
   cmd=['yosys','-Q','-T','-p',f'read_verilog -sv {out/f"msif_{typ}.sv"}; hierarchy -top msif_{typ}; proc; opt; synth -top msif_{typ}; stat']
   log=subprocess.run(cmd,text=True,capture_output=True)
   (out/f'yosys_{typ}.log').write_text(log.stdout+log.stderr)
   if log.returncode:raise SystemExit('FAILED: '+typ+' (see synthesis log)')
  print('PASS: synthesis logs produced; NOT PDK area or timing')
if __name__=='__main__':main()
