"""Record reviewed Python/Windows mappings and check the built release set."""
import json
from pathlib import Path
import sys
from release_preflight import init, check


def main():
    root = Path(__file__).resolve().parents[1]
    release = Path(sys.argv[1]).resolve()
    built = json.loads((release / 'release-manifest.json').read_text())
    artifacts = list(built['artifacts'])
    wheel = next(p for p in artifacts if p.endswith('.whl'))
    portable = next(p for p in artifacts if p.endswith('-Windows.zip'))
    installer = next(p for p in artifacts if p.endswith('-Setup.exe'))
    manifest = release / 'DEPLOY_MANIFEST.json'
    data = init(root, manifest, built['version'], artifacts,
                ['python-api', 'command-line', 'portable-desktop', 'installed-desktop'],
                ['pypi', 'github-windows'], artifact_root=release)
    for surface in data['surfaces']:
        surface['artifact'] = {'portable-desktop': portable,
                               'installed-desktop': installer}.get(surface['name'], wheel)
    for channel in data['channels']:
        channel['artifact'] = wheel if channel['name'] == 'pypi' else installer
    manifest.write_text(json.dumps(data, indent=2) + '\n')
    result = check(root, manifest, 'candidate')
    (release / 'candidate-preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'ready':
        raise RuntimeError(result)
    print('Candidate preflight passed for Python and Windows release surfaces')


if __name__ == '__main__':
    main()
