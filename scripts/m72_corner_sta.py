#!/usr/bin/env python3
"""Fail-closed per-view OpenROAD STA of final routed ODB + SDC + SPEF.
Corner files must be independently validated; this tool never auto-declares signoff.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    try:
        m=json.loads(a.manifest.read_text());assert m.get('schema')=='msif-m72-corners-v1'
        assert set(m['corners'])=={'tt','ss','ff'}
        entries=[]
        for corner,cfg in m['corners'].items():
            assert cfg['role']=={'tt':'reference','ss':'setup','ff':'hold'}[corner]
            assert cfg.get('reviewed') is True,corner+' review missing'
            lib=Path(cfg['liberty']).resolve();assert lib.is_file() and sha(lib)==cfg['liberty_sha256']
            # Exact power/temperature metadata must be explicit and per-view.
            assert isinstance(cfg['voltage_v'],(float,int)) and 'temperature_c' in cfg
            for v,vfiles in cfg['designs'].items():
                assert v in ('programmable','fixed','rom')
                files={k:Path(vfiles[k]).resolve() for k in ('odb','sdc','spef')}
                for k,f in files.items():assert f.is_file() and sha(f)==vfiles[k+'_sha256']
                entries.append((corner,v,lib,files))
        assert len(entries)==9
        a.out.mkdir(parents=True,exist_ok=False)
        report={'schema':'msif-m72-sta-results-v1','results':{},'signoff':'NOT_VERIFIED'}
        for corner,v,lib,files in entries:
            name=f'{corner}_{v}';report['results'][name]={'status':'INPUTS_REVIEWED_NOT_EXECUTED','liberty_sha256':sha(lib),'spef_sha256':sha(files['spef'])}
            if not a.execute:continue
            tcl=a.out/f'{name}.tcl'
            tcl.write_text('read_liberty $::env(MSIF_LIB)\nread_db $::env(MSIF_ODB)\nread_sdc $::env(MSIF_SDC)\nread_spef $::env(MSIF_SPEF)\nreport_checks -path_delay max -group_path_count 5\nreport_checks -path_delay min -group_path_count 5\nreport_check_types -max_slew -max_cap -max_fanout -violators\ncheck_setup\nputs "M72_CORNER_STA_EXECUTED_NOT_SIGNOFF"\n')
            env=dict(os.environ,MSIF_LIB=str(lib),MSIF_ODB=str(files['odb']),MSIF_SDC=str(files['sdc']),MSIF_SPEF=str(files['spef']))
            q=subprocess.run(['openroad','-exit',str(tcl)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,text=True,timeout=300)
            (a.out/f'{name}.log').write_text(q.stdout)
            report['results'][name]['status']='STA_EXECUTED_REVIEW_REQUIRED' if q.returncode==0 and 'M72_CORNER_STA_EXECUTED_NOT_SIGNOFF' in q.stdout else 'BLOCKED'
        (a.out/'manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        return 2 if any(x['status']=='BLOCKED' for x in report['results'].values()) else 0
    except (AssertionError,KeyError,OSError,ValueError,subprocess.TimeoutExpired) as ex:
        print('BLOCKED corner STA:',ex,file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
