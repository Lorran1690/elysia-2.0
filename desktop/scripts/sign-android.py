"""Sign an already verified Android release using a private, external keystore.

The keystore/password must never be placed in the repository or CI artifacts.
Only the signed APK, public certificate hash and update descriptor are emitted.
"""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path

def digest(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--unsigned',type=Path,required=True)
 parser.add_argument('--metadata',type=Path,required=True)
 parser.add_argument('--tools',type=Path,required=True)
 parser.add_argument('--private-signing',type=Path,required=True)
 parser.add_argument('--source',required=True)
 parser.add_argument('--build',type=int,required=True)
 parser.add_argument('--output',type=Path,default=Path('artifacts/android'))
 args=parser.parse_args()
 if not re.fullmatch('[a-f0-9]{40}',args.source) or not 0<args.build<2147483647:raise ValueError('Invalid source commit or Android build.')
 if not 0<args.unsigned.stat().st_size<=100*1024*1024:raise ValueError('Unsigned APK outside supported size limits.')
 metadata=json.loads(args.metadata.read_text())
 elements=metadata.get('elements',[])
 if metadata.get('applicationId')!='org.elysia.mobile' or len(elements)!=1 or elements[0].get('versionCode')!=args.build or elements[0].get('versionName')!='2.2.0':raise ValueError('APK build identity does not match its verified workflow.')
 private_path=args.private_signing.resolve()
 repository=Path(__file__).resolve().parents[2]
 if private_path.is_relative_to(repository):raise ValueError('Private signing material must be outside the repository.')
 key=json.loads(private_path.read_text())
 if key.get('application_id')!='org.elysia.mobile' or Path(key['key_store']).name!=key['key_store']:raise ValueError('Private signing identity invalid.')
 key_path=private_path.parent/key['key_store']
 args.output.mkdir(parents=True,exist_ok=True)
 apk=args.output/'Elysia-Android.apk'
 env={**os.environ,'ELYSIA_ANDROID_STORE_PASS':key['store_password'],'ELYSIA_ANDROID_KEY_PASS':key['key_password'],'LD_LIBRARY_PATH':str(args.tools.resolve()/'lib64')+((':'+os.environ['LD_LIBRARY_PATH']) if os.environ.get('LD_LIBRARY_PATH') else '')}
 jar=args.tools/'apksigner.jar';align=args.tools/'zipalign';align.chmod(0o700)
 with tempfile.TemporaryDirectory(prefix='elysia-android-sign-') as temp:
  aligned=Path(temp)/'aligned.apk';signed=Path(temp)/'signed.apk'
  subprocess.run([str(align.resolve()),'-P','16','-f','4',str(args.unsigned.resolve()),str(aligned)],env=env,check=True,capture_output=True)
  subprocess.run(['java','-jar',str(jar.resolve()),'sign','--ks',str(key_path),'--ks-type','PKCS12','--ks-key-alias',key['alias'],'--ks-pass','env:ELYSIA_ANDROID_STORE_PASS','--key-pass','env:ELYSIA_ANDROID_KEY_PASS','--v4-signing-enabled','false','--out',str(signed),str(aligned)],env=env,check=True,capture_output=True)
  verification=subprocess.check_output(['java','-jar',str(jar.resolve()),'verify','--verbose','--print-certs',str(signed)],text=True)
  match=re.search(r'Signer #1 certificate SHA-256 digest: ([a-f0-9]{64})',verification)
  expected=(private_path.parent/'certificate.sha256').read_text().strip()
  if not match or match.group(1)!=expected:raise ValueError('The signed APK certificate does not match the private project key.')
  subprocess.run([str(align.resolve()),'-c','-P','16','4',str(signed)],env=env,check=True,capture_output=True)
  apk.write_bytes(signed.read_bytes())
 value={'format':'elysia-android-update-v1','version':'2.2.0','build':args.build,'source_sha':args.source,'apk':{'name':apk.name,'url':'https://raw.githubusercontent.com/Lorran1690/elysia-2.0/refs/heads/feature/media-creation/artifacts/android/Elysia-Android.apk','bytes':apk.stat().st_size,'sha256':digest(apk)},'certificate_sha256':expected}
 (args.output/'latest.json').write_text(json.dumps(value,indent=2)+'\n')
 (args.output/'Elysia-Android.sha256').write_text(value['apk']['sha256']+'  '+apk.name+'\n')
 report={'passed':True,'production_release_signed':True,'debug_keystore_used':False,'certificate_sha256':expected,'unsigned_apk_sha256':digest(args.unsigned),'apk_sha256':value['apk']['sha256'],'source_commit':args.source,'build':args.build,'signature_and_zip_alignment_verified':True,'private_signing_material_in_repository':False,'installer_executed_on_owner_phone':False}
 (args.output/'signing-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))

if __name__=='__main__':main()
