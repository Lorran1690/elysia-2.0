"""Bundle the actual npm license/notice texts used by the Android frontend."""
import json,re,shutil
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root/'android/app/src/main/assets/public/licenses'
out.mkdir(parents=True,exist_ok=True)
index=[]
for entry,data in json.loads((root/'package-lock.json').read_text())['packages'].items():
 if not entry or data.get('dev'):continue
 package=root/entry
 if not (package/'package.json').is_file():continue
 metadata=json.loads((package/'package.json').read_text())
 target=out/re.sub(r'[^a-zA-Z0-9_.-]+','_',metadata['name'])
 copied=[]
 for file in package.iterdir():
  if file.is_file() and re.match(r'^(license|licence|notice|copying)(\.|$|-)',file.name,re.I):
   target.mkdir(exist_ok=True);shutil.copyfile(file,target/file.name);copied.append(file.name)
 index.append({'name':metadata['name'],'version':metadata['version'],'license':metadata.get('license'),'files':copied})
(out/'npm-components.json').write_text(json.dumps(index,indent=2)+'\n')
shutil.copyfile(root/'android/NOTICE.md',out/'NOTICE.md')
print(f'Bundled license metadata for {len(index)} Android frontend packages.')
