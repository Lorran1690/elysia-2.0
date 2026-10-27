"""Copy actual npm license texts into the native distribution."""
from pathlib import Path
import shutil,sys
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
modules=Path('desktop/node_modules')
for item in modules.rglob('*'):
 if item.is_file() and item.name.lower() in {'license','license.md','license.txt','licence','licence.md','licence.txt','copying'}:
  relative=item.relative_to(modules);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(item,target)
shutil.copyfile('desktop/public/music/LICENSE.txt',out/'ELYSIA-MUSIC-LICENSE.txt')
