#!/usr/bin/bash
# Usage: bash resample.sh /path/to/dir1 /path/to/dir2 ...
# Resamples all .wav files found recursively under the given directories
# to 24kHz mono, in-place (original filenames preserved).

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 /path/to/dir1 /path/to/dir2 ..."
    exit 1
fi

for dir in "$@"; do
    echo "Processing: $dir"
    find "$dir" -name "*.wav" | while IFS= read -r f; do
        tmp="${f%/*}/tmp_${f##*/}"
        sox -- "$f" -r 24000 -c 1 "$tmp" norm -3 && mv -- "$tmp" "$f"
        echo "  Resampled: $f"
    done
done

echo "Done."