#!/usr/bin/env python3
"""Build a release manifest from the PKP plugin gallery's plugins.xml.

The gallery feed (https://raw.githubusercontent.com/pkp/plugin-gallery/main/plugins.xml)
lists every plugin release together with the tarball URL and the MD5 of that
tarball. This script turns that feed into a flat manifest that the hash
generator can consume without re-parsing XML 601 times.

Each release may produce more than one JSON file name. The scanner plugin
requests a baseline by file name, and it derives that name from the plugin's
version.xml (see PKPPluginInfo/Version::getVersionString), which is not always
the same string the gallery uses. We therefore emit every plausible name for a
release: the gallery version, the raw version.xml release, and the normalised
four-part version PKP computes at runtime.

Usage:
    build_manifest.py --plugins-xml plugins.xml --output manifest.jsonl
    build_manifest.py --plugins-xml plugins.xml --application ojs2 --output ...
"""

import argparse
import json
import re
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

PKP_NAMESPACE = 'http://pkp.sfu.ca'
NS = {'pkp': PKP_NAMESPACE}

# Application identifiers used inside the gallery feed.
APPLICATIONS = ('ojs2', 'omp', 'ops')

# Folder layout of this repository.
APPLICATION_FOLDER = {
    'ojs2': 'ojs',
    'omp': 'omp',
    'ops': 'ops',
}


def normalise_version(release):
    """Mirror PKP's Version::fromString() parsing.

    PKP explodes a version string on "." and casts each of the first four
    segments to an int, defaulting to 0. getVersionString() then formats those
    four numbers back as "%d.%d.%d.%d". A release such as "1.2.4" therefore
    becomes "1.2.4.0" at runtime, while "1.0.0-33" becomes "1.0.0.0".
    """
    parts = (release or '').split('.')
    numbers = []
    for index in range(4):
        try:
            numbers.append(int(parts[index]))
        except (IndexError, ValueError):
            numbers.append(0)
    return '%d.%d.%d.%d' % tuple(numbers)


def find_version_xml(archive):
    """Locate version.xml the way PKP does when installing a plugin.

    PKP extracts the archive and then looks for a version.xml either at the
    archive root or inside a direct sub-directory. We mimic that by stripping
    the single leading path component and looking for version.xml at the root.
    """
    try:
        with tarfile.open(fileobj=BytesIO(archive), mode='r:gz') as tar:
            members = [m for m in tar.getmembers() if m.isfile()]
            candidates = []
            for member in members:
                name = member.name
                if name == 'version.xml':
                    candidates.append((name, member))
                elif name.count('/') == 1 and name.endswith('/version.xml'):
                    candidates.append((name, member))
            if not candidates:
                return None
            candidates.sort()
            name, member = candidates[0]
            payload = tar.extractfile(member).read().decode('utf-8', 'replace')
    except (tarfile.TarError, OSError):
        return None

    def tag(name):
        match = re.search(r'<%s>([^<]*)</%s>' % (name, name), payload)
        return match.group(1).strip() if match else None

    return {
        'release': tag('release'),
        'type': tag('type'),
        'application': tag('application'),
    }


def candidate_names(product, gallery_version, version_info):
    """Every file name the scanner could legitimately ask for.

    The gallery version is what the feed publishes and what the repository
    already uses. The version.xml variants cover the name the scanner builds
    at runtime from the installed plugin.
    """
    names = {gallery_version}
    if version_info and version_info.get('release'):
        names.add(version_info['release'])
        names.add(normalise_version(version_info['release']))
    return sorted(names)


def version_sort_key(release):
    """Order two release strings by their numeric components.

    Version strings in the feed are mostly dotted numbers, but a few carry a
    dash suffix such as "1.0.0-33". Comparing them numerically keeps the
    ordering predictable: a dash suffix sorts before the next dotted bump.
    """
    numbers = []
    for part in re.split(r'[.-]', release or ''):
        try:
            numbers.append(int(part))
        except ValueError:
            numbers.append(-1)
    while len(numbers) < 4:
        numbers.append(0)
    return tuple(numbers[:4])


def resolve_ownership(rows):
    """Decide which release owns each baseline file name.

    A handful of releases declare a version.xml release that is identical to
    another release of the same plugin, so two releases can claim the same
    file name. Only one file can exist per name, so we pick a single owner:

    * A name that equals a gallery version always belongs to that release. The
      gallery version is the authoritative name for a release and the one the
      repository already uses.
    * Any remaining name is owned by the most recent release that claims it,
      because a site is far more likely to run the latest build of a plugin
      whose version.xml was never bumped.

    The names that stay ambiguous are reported so a maintainer can resolve
    them by hand.
    """
    gallery_owner = {}
    claims = {}
    for row in rows:
        for category in row['categories']:
            for name in row['file_names']:
                key = (category, '%s-%s' % (row['product'], name))
                claims.setdefault(key, []).append(row)
                if name == row['gallery_version']:
                    gallery_owner[key] = row
    ownership = {}
    ambiguous = []
    for key, claimants in claims.items():
        if key in gallery_owner:
            owner = gallery_owner[key]
        else:
            owner = sorted(
                claimants,
                key=lambda row: (version_sort_key(row['gallery_version']), row.get('date') or ''),
            )[-1]
            if len(claimants) > 1:
                ambiguous.append({
                    'file': '%s/%s' % key,
                    'claimants': ['%s-%s' % (row['product'], row['gallery_version']) for row in claimants],
                    'owner': '%s-%s' % (owner['product'], owner['gallery_version']),
                })
        ownership.setdefault(id(owner), set()).add(key)

    for row in rows:
        owned = ownership.get(id(row), set())
        row['owned_files'] = sorted('%s/%s.json' % (category, name) for category, name in owned)

    return ambiguous


def resolve_category(gallery_category, version_info):
    """Decide which plugin folder the baseline belongs in.

    The gallery category and the plugin's own version.xml type agree for every
    release except datacite 3.4.0.1, where the gallery still files it under
    importexport although the plugin declares itself plugins.generic. PKP
    installs a plugin into plugins/<type>/<application>, so the version.xml type
    is the authoritative folder. We keep the gallery category as well so a
    baseline is produced for both, and the existing repository layout stays
    intact.
    """
    categories = {gallery_category}
    if version_info and version_info.get('type'):
        categories.add(version_info['type'].split('.')[-1])
    return sorted(categories)


def download(url, timeout=60):
    request = urllib.request.Request(url, headers={'User-Agent': 'hash-repo-manifest'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def build_release(release_entry):
    """Resolve one release into its manifest row."""
    product = release_entry['product']
    gallery_version = release_entry['version']
    package = release_entry['package']

    archive = None
    status = 'ok'
    version_info = None
    try:
        archive = download(package)
    except Exception as exc:  # noqa: BLE001 - dead links and network errors are data, not crashes
        status = 'download-failed: %s' % type(exc).__name__

    if archive is not None:
        version_info = find_version_xml(archive)

    categories = resolve_category(release_entry['category'], version_info)
    names = candidate_names(product, gallery_version, version_info)

    return {
        'product': product,
        'gallery_version': gallery_version,
        'gallery_category': release_entry['category'],
        'package': package,
        'md5': release_entry['md5'],
        'date': release_entry['date'],
        'applications': release_entry['applications'],
        'categories': categories,
        'file_names': names,
        'version_xml_release': version_info['release'] if version_info else None,
        'version_xml_type': version_info['type'] if version_info else None,
        'status': status,
    }


def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    releases = []
    for plugin in root.findall('pkp:plugin', NS):
        product = plugin.get('product')
        category = plugin.get('category')
        for release in plugin.findall('pkp:release', NS):
            package_element = release.find('pkp:package', NS)
            package = (package_element.text or '').strip() if package_element is not None else ''
            if not package:
                continue
            applications = []
            for compatibility in release.findall('pkp:compatibility', NS):
                application = compatibility.get('application')
                if application and application not in applications:
                    applications.append(application)
            releases.append({
                'product': product,
                'version': release.get('version'),
                'category': category,
                'package': package,
                'md5': release.get('md5'),
                'date': release.get('date'),
                'applications': applications,
            })
    return releases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugins-xml', required=True, help='Path to plugins.xml')
    parser.add_argument('--output', required=True, help='Path to the manifest (JSON Lines)')
    parser.add_argument('--application', choices=APPLICATIONS, help='Only keep releases for this application')
    parser.add_argument('--skip-download', action='store_true',
                        help='Do not resolve version.xml; the gallery version is then the only candidate name')
    parser.add_argument('--jobs', type=int, default=16, help='Parallel downloads')
    args = parser.parse_args()

    with open(args.plugins_xml, 'rb') as handle:
        releases = parse_feed(handle.read())

    if args.application:
        releases = [r for r in releases if args.application in r['applications']]

    if args.skip_download:
        rows = []
        for release in releases:
            rows.append({
                'product': release['product'],
                'gallery_version': release['version'],
                'gallery_category': release['category'],
                'package': release['package'],
                'md5': release['md5'],
                'date': release['date'],
                'applications': release['applications'],
                'categories': [release['category']],
                'file_names': [release['version']],
                'version_xml_release': None,
                'version_xml_type': None,
                'status': 'skipped',
            })
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            rows = list(pool.map(build_release, releases))

    ambiguous = resolve_ownership(rows)

    with open(args.output, 'w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + '\n')

    failed = [row for row in rows if row['status'] != 'ok']
    sys.stderr.write('manifest: %d releases, %d unresolved\n' % (len(rows), len(failed)))
    for row in failed:
        sys.stderr.write('  %s %s: %s\n' % (row['product'], row['gallery_version'], row['status']))
    if ambiguous:
        sys.stderr.write('manifest: %d file names claimed by more than one release\n' % len(ambiguous))
        for entry in ambiguous:
            sys.stderr.write('  %s -> %s (claimed by %s)\n'
                             % (entry['file'], entry['owner'], ', '.join(entry['claimants'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
