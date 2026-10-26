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
    parser.add_argument('--worktree', action='store_true',
                        help='Package current tracked changes and non-ignored untracked source files.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.worktree:
        names = subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root
        ).decode().split('\0')
        source_state = 'working-tree'
    else:
        names = subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', '-z', sha], cwd=root
        ).decode().split('\0')
        source_state = 'commit'
    tracked = sorted({name for name in names if name})
    output_path = args.output.resolve()
    root_path = root.resolve()
    manifest = {'commit': sha, 'sourceState': source_state, 'files': {}}
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in tracked:
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or path.suffix == '.class':
                raise ValueError(f'Invalid release path: {name}')
            source = root.joinpath(*path.parts)
            resolved = source.resolve(strict=True)
            if resolved != root_path and root_path not in resolved.parents:
                raise ValueError(f'Release path leaves source root: {name}')
            if source.is_symlink() or not source.is_file():
                raise ValueError(f'Release path is not a regular file: {name}')
            if args.worktree and (source.resolve() == output_path or output_path in source.resolve().parents):
                continue
            payload = source.read_bytes() if args.worktree else subprocess.check_output(
                ['git', 'show', f'{sha}:{name}'], cwd=root
            )
            manifest['files'][name] = hashlib.sha256(payload).hexdigest()
            archive.writestr(name, payload)
        archive.writestr('RELEASE_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f'Checksum mismatch: {name}')
        if set(archive.namelist()) != set(manifest['files']) | {'RELEASE_MANIFEST.json'}:
            raise ValueError('Unexpected or missing release files')
    print(json.dumps({'commit': sha, 'sourceState': source_state,
                      'verifiedFiles': len(manifest['files']),
                      'zip': str(args.output.resolve()),
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
