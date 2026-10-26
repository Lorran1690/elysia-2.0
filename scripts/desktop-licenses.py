"""Preserve runtime dependency notices alongside the distributed executable."""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys


def collect(destination):
    destination = Path(destination)
    for name in ('torch', 'psutil', 'PyYAML'):
        dist = distribution(name)
        files = [f for f in dist.files or [] if '.dist-info/' in str(f)
                 and any(word in str(f).lower() for word in ('license', 'copying', 'notice'))]
        if not files:
            raise RuntimeError(f'No distribution license found for {name}')
        for file in files:
            target = destination / name / str(file).split('.dist-info/', 1)[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(dist.locate_file(file), target)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        python_license = Path(sys.base_prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('CPython license was not found')
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(python_license, destination / 'CPython-LICENSE.txt')


if __name__ == '__main__':
    collect(sys.argv[1])
