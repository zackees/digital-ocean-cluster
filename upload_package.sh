#!/bin/bash
set -e
rm -rf build dist
. ./activate
uv build
echo "Uploading the package to PyPI via Twine…"
twine upload dist/*tar.gz --verbose
# echo Pushing git tags…
