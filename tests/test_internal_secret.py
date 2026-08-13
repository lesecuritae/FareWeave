from pathlib import Path
import os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
 target=Path(directory)/"token"; env={**os.environ,"DB_CFFI_TOKEN":"","DB_CFFI_TOKEN_FILE":str(target)}
 subprocess.run([sys.executable,str(ROOT/"tool/init_db_cffi_token.py")],env=env,check=True)
 token=target.read_text().strip(); assert len(token)==64 and all(c in "0123456789abcdef" for c in token)
 first=target.read_bytes(); subprocess.run([sys.executable,str(ROOT/"tool/init_db_cffi_token.py")],env=env,check=True); assert target.read_bytes()==first
 spec=__import__("importlib.util").util.spec_from_file_location("internal_secret",ROOT/"tool/reisevergleich/internal_secret.py"); module=__import__("importlib.util").util.module_from_spec(spec); spec.loader.exec_module(module); read_internal_token=module.read_internal_token
 old=os.environ.copy()
 try:
  os.environ.update(env); assert read_internal_token()==token
  os.environ["DB_CFFI_TOKEN"]="explicit-token"; assert read_internal_token()=="explicit-token"
 finally: os.environ.clear(); os.environ.update(old)
print("Persistent internal secret generation and precedence: OK")
