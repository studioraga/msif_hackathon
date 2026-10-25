"""Independent audit manifest with optional integration to actual PAG v0.21.1 functions."""
import hashlib, json, os, sys
from pathlib import Path

def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_manifest(folder):
    p=Path(folder); j=json.loads((p/'manifest.json').read_text()); model=json.loads((p/'model.json').read_text())
    from .core import sha, check
    check(model)
    if sha(model)!=j['model_sha256']:raise ValueError('model modified')
    for v,d in j['rtl_sha256'].items():
        if sha_file(p/f'msif_{v}.sv')!=d:raise ValueError('RTL modified: '+v)
    return True

def sign_via_pag(folder,private_key,public_key,signature_path=None):
    from portable_ai_governance.supply_chain.signing import sign_blob,verify_blob
    p=Path(folder)/'manifest.json'; sig=Path(signature_path) if signature_path else Path(folder)/'manifest.sig'
    validate_manifest(folder);sign_blob(p,private_key,sig)
    if not verify_blob(p,public_key,sig):raise RuntimeError('signature invalid')
    return str(sig)

def verify_via_pag(folder,public_key,signature_path=None):
    from portable_ai_governance.supply_chain.signing import verify_blob
    validate_manifest(folder)
    sig=Path(signature_path) if signature_path else Path(folder)/'manifest.sig'
    if not sig.is_file() or not verify_blob(Path(folder)/'manifest.json',public_key,sig):raise RuntimeError('signed build verification failed')
    return True
