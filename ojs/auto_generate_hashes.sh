#!/bin/bash
VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: ./auto_generate_hashes.sh <ojs-version>"
  exit 1
fi

# Unduh versi OJS resmi
wget "https://pkp.sfu.ca/ojs/download/ojs-$VERSION.tar.gz"

# Ekstrak
tar -xzf "ojs-$VERSION.tar.gz"

# Pindah ke direktori dan hasilkan hash
cd "ojs-$VERSION"
# Gunakan sha256sum dan format ke JSON (memerlukan 'jq')
find . -type f ! -name 'config.TEMPLATE.inc.php' -print0 | xargs -0 sha256sum | \
awk '{print "\"" $2 "\": \"" $1 "\""}' | sed 's|^\."/||' | \
jq -s -c 'reduce .[] as $item ({}; . + ($item | split(":") | {(.[0]): .[1]}))' > "../hashes-$VERSION.json"

# Bersihkan
cd ..
rm -rf "ojs-$VERSION" "ojs-$VERSION.tar.gz"

echo "File hashes-$VERSION.json created successfully."
