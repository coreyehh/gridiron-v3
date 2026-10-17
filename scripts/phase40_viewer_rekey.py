"""Re-wrap an existing Phase40 encrypted ledger with a NEW viewer key.

Both keys come exclusively from GitHub Actions Secrets. No raw records,
plaintext, secret values or filenames containing player details in logs.
"""
import argparse,hashlib,json,os
from pathlib import Path
from cryptography.fernet import Fernet,InvalidToken
from scripts.phase39_secure_quote_evidence import verify_cipher_key
from scripts.phase31_accountability import canonical

def rekey(ciphertext,old_key,new_key):
    old=Fernet(verify_cipher_key(old_key))
    new=Fernet(verify_cipher_key(new_key))
    if old_key==new_key:raise ValueError("New viewer key must differ from original key")
    try:plain=old.decrypt(ciphertext)
    except InvalidToken:raise ValueError("Original archive key could not decrypt the ledger") from None
    try:doc=json.loads(plain)
    except (ValueError,UnicodeDecodeError):raise ValueError("Invalid decrypted Phase40 ledger") from None
    if not isinstance(doc,dict) or doc.get("version")!="phase40-prospective-offer-forecast-outcome-ledger-v1":
        raise ValueError("Unexpected ledger type")
    lock=doc.get("lock_sha256")
    content={k:v for k,v in doc.items() if k!="lock_sha256"}
    if not lock or hashlib.sha256(canonical(content).encode()).hexdigest()!=lock:
        raise ValueError("Phase40 ledger integrity digest invalid")
    if not isinstance(doc.get("entries"),list):raise ValueError("Invalid ledger rows")
    rotated=new.encrypt(plain)
    return rotated,{"status":"ENCRYPTED_LEDGER_REKEYED",
       "source_sha256":hashlib.sha256(ciphertext).hexdigest(),
       "rotated_ciphertext_sha256":hashlib.sha256(rotated).hexdigest(),
       "entry_count":len(doc["entries"]),
       "plaintext_uploaded":False,"original_key_revealed":False,
       "new_key_revealed":False,"api_credits_used":0}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="private_data/phase40/locked_ledger.fernet")
    parser.add_argument("--output-dir",default="output/phase40-viewer")
    args=parser.parse_args()
    old=os.environ.get("QUOTE_ARCHIVE_KEY")
    new=os.environ.get("QUOTE_VIEWER_KEY")
    # Fail BEFORE reading or downloading anything from paid providers.
    verify_cipher_key(old);verify_cipher_key(new)
    rotated,manifest=rekey(Path(args.input).read_bytes(),old,new)
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    path=out/"locked_ledger_viewer.fernet"
    path.write_bytes(rotated);os.chmod(path,0o600)
    (out/"rekey_summary.json").write_text(json.dumps(manifest,indent=2))
    msg=(f"# GRIDIRON private viewer key rotation\n\n"
         f"**Re-encrypted market pairs:** {manifest['entry_count']}.\n\n"
         "Only authenticated ciphertext uploaded. Old and new keys remain secret. "
         "No sportsbook requests.\n")
    print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
