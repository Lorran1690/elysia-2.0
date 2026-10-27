"""Copy actual npm license texts into the native distribution."""
from pathlib import Path
import shutil,sys
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
modules=Path('desktop/node_modules')
for item in modules.rglob('*'):
 if item.is_file() and item.name.lower() in {'license','license.md','license.txt','licence','licence.md','licence.txt','copying'}:
  relative=item.relative_to(modules);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(item,target)
shutil.copyfile('desktop/public/music/LICENSE.txt',out/'ELYSIA-MUSIC-LICENSE.txt')
# Rust dependencies are statically linked into the native executable. Include
# their original license notices as well as the frontend package licenses.
import os
cargo_home=Path(os.environ.get('CARGO_HOME',str(Path.home()/'.cargo')))
registry=cargo_home/'registry/src'
rust_count=0
if registry.is_dir():
 for item in registry.rglob('*'):
  if item.is_file() and (item.name.lower().startswith(('license','licence')) or item.name.lower() in {'copying','notice','notice.txt','copyright'}):
   relative=item.relative_to(registry);target=out/'rust'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(item,target);rust_count+=1
if os.environ.get('GITHUB_ACTIONS')=='true' and not rust_count:
 raise RuntimeError('Rust dependency license texts were not found; distribution refused.')
print(f'Included {rust_count} Rust license and attribution files.')
