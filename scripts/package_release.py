"""Create and independently verify a source ZIP from a committed Git tree."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('output/local/face-liveness-source.zip'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', '-z', sha], cwd=root).decode().split('\0')
    tracked = [name for name in tracked if name]
    manifest = {'commit': sha, 'files': {}}
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in tracked:
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or path.suffix == '.class':
                raise ValueError(f'Invalid release path: {name}')
            payload = subprocess.check_output(['git', 'show', f'{sha}:{name}'], cwd=root)
            manifest['files'][name] = hashlib.sha256(payload).hexdigest()
            archive.writestr(name, payload)
        archive.writestr('RELEASE_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f'Checksum mismatch: {name}')
        if set(archive.namelist()) != set(tracked) | {'RELEASE_MANIFEST.json'}:
            raise ValueError('Unexpected or missing release files')
    print(json.dumps({'commit': sha, 'verifiedFiles': len(tracked),
                      'zip': str(args.output.resolve()),
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
