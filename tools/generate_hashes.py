#!/usr/bin/env python3
"""Generate SHA-256 baseline JSON files for plugin releases listed in a manifest.

Each release is downloaded, checked against the MD5 published in the plugin
gallery feed, extracted, and hashed file by file. The resulting JSON maps a
relative file path to its SHA-256 digest, which is the format the File
Integrity Scanner plugin consumes.

A release may need more than one output file name: the scanner asks for a
baseline by name and derives that name from the installed plugin's version.xml,
which does not always match the version string the gallery publishes. The
manifest carries every candidate name, and each candidate is written out
pointing at the same hashes.

Usage:
    generate_hashes.py --manifest manifest.jsonl --output-dir ojs/plugins
    generate_hashes.py --manifest manifest.jsonl --output-dir ojs/plugins \
        --only gopher-1.0.0.1
"""

import argparse
import hashlib
import json
import os
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO


def download(url, timeout=120):
    request = urllib.request.Request(url, headers={'User-Agent': 'hash-repo-generator'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def extract_hashes(archive):
    """Hash every regular file in the archive, relative to its top directory.

    The repository layout strips the archive's single leading directory, so the
    hash keys are paths relative to that directory. Nothing is filtered out
    here: the existing baselines in this repository include dot-directories
    such as .git/, so dropping them would make the generated files differ from
    the ones the manual workflow produces.
    """
    hashes = {}
    with tarfile.open(fileobj=BytesIO(archive), mode='r:gz') as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            parts = member.name.split('/', 1)
            if len(parts) != 2:
                continue
            relative = parts[1]
            if not relative:
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            digest = hashlib.sha256()
            for chunk in iter(lambda: extracted.read(1024 * 1024), b''):
                digest.update(chunk)
            hashes[relative] = digest.hexdigest()
    return hashes


def write_json(path, hashes):
    """Write the baseline JSON.

    The formatting matches jq's default output (two space indent, ": "
    separator, trailing newline) so that files produced here are byte
    identical to the ones the manual workflow produces.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(hashes, handle, indent=2, ensure_ascii=False)
        handle.write('\n')


def process(row, output_dir, force, dry_run, existing_dir=None):
    """Generate every baseline file for one release.

    Only the files this release owns are written. A file name can be claimed by
    more than one release (two releases of the same plugin sometimes share a
    version.xml release string); the manifest resolves that and lists the owner
    in "owned_files".
    """
    product = row['product']
    version = row['gallery_version']
    label = '%s-%s' % (product, version)

    owned = row.get('owned_files')
    if owned:
        relative_paths = owned
    else:
        relative_paths = []
        for category in row['categories']:
            for name in row['file_names']:
                relative_paths.append('%s/%s-%s.json' % (category, product, name))

    if not relative_paths:
        return {'label': label, 'result': 'no-files', 'files': 0}

    targets = [os.path.join(output_dir, path) for path in relative_paths]
    if not force:
        if existing_dir:
            # Compare against the checked-out repository, not just the fresh
            # output directory, so the default run only emits genuinely new files.
            targets = [target for target, rel in zip(targets, relative_paths)
                       if not os.path.exists(os.path.join(existing_dir, rel))]
        else:
            targets = [path for path in targets if not os.path.exists(path)]
        if not targets:
            return {'label': label, 'result': 'skipped-existing'}

    if row.get('status') != 'ok':
        return {'label': label, 'result': 'unresolved', 'detail': row.get('status')}

    try:
        archive = download(row['package'])
    except Exception as exc:  # noqa: BLE001
        return {'label': label, 'result': 'download-failed', 'detail': str(exc)}

    expected_md5 = row.get('md5')
    if expected_md5:
        actual_md5 = hashlib.md5(archive).hexdigest()
        if actual_md5 != expected_md5:
            return {
                'label': label,
                'result': 'md5-mismatch',
                'detail': 'expected %s got %s' % (expected_md5, actual_md5),
            }

    try:
        hashes = extract_hashes(archive)
    except tarfile.TarError as exc:
        return {'label': label, 'result': 'extract-failed', 'detail': str(exc)}

    if not hashes:
        return {'label': label, 'result': 'empty-archive'}

    if dry_run:
        return {'label': label, 'result': 'dry-run', 'files': len(hashes)}

    written = []
    for path in targets:
        write_json(path, hashes)
        written.append(path)

    return {'label': label, 'result': 'written', 'files': len(hashes), 'paths': written}


def load_manifest(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, help='Manifest produced by build_manifest.py')
    parser.add_argument('--output-dir', required=True, help='Directory that receives <category>/<name>.json files')
    parser.add_argument('--existing-dir', help='Repository plugins directory; only write files that do not exist there')
    parser.add_argument('--only', action='append', default=[],
                        help='Only process these product-version labels (repeatable)')
    parser.add_argument('--force', action='store_true', help='Rewrite files that already exist')
    parser.add_argument('--dry-run', action='store_true', help='Download and hash, but do not write files')
    parser.add_argument('--jobs', type=int, default=8, help='Parallel downloads')
    parser.add_argument('--report', help='Write a JSON summary to this path')
    args = parser.parse_args()

    rows = load_manifest(args.manifest)
    if args.only:
        wanted = set(args.only)
        rows = [row for row in rows if '%s-%s' % (row['product'], row['gallery_version']) in wanted]

    if args.jobs > 1:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(
                lambda row: process(row, args.output_dir, args.force, args.dry_run, args.existing_dir), rows))
    else:
        results = [process(row, args.output_dir, args.force, args.dry_run, args.existing_dir) for row in rows]

    counts = {}
    for result in results:
        counts[result['result']] = counts.get(result['result'], 0) + 1

    sys.stderr.write('generate_hashes: %s\n' % json.dumps(counts, sort_keys=True))
    for result in results:
        if result['result'] not in ('written', 'skipped-existing', 'dry-run'):
            sys.stderr.write('  %s: %s %s\n' % (result['label'], result['result'], result.get('detail', '')))

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as handle:
            json.dump(results, handle, indent=2, sort_keys=True)
            handle.write('\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
