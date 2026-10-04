#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="${DUOOMARCHY_AQUAMARINE_BUILD_DIR:-$root/.build/aquamarine}"
prefix="${DUOOMARCHY_DATA:-$HOME/.local/share/duoomarchy}/runtime"
if [[ -e "$source_dir" ]]; then
  echo "Build directory already exists: $source_dir" >&2
  exit 1
fi
git clone --depth 1 --branch v0.14.0 https://github.com/hyprwm/aquamarine.git "$source_dir"
git -C "$source_dir" apply --check "$root/patches/aquamarine-nested-desktop.patch"
git -C "$source_dir" apply "$root/patches/aquamarine-nested-desktop.patch"
cmake -S "$source_dir" -B "$source_dir/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DBUILD_TESTING=OFF
cmake --build "$source_dir/build" -j "${BUILD_JOBS:-3}"
# Install the runtime library only. Keep system headers and pkg-config untouched.
mkdir -p "$prefix/lib"
cp -P "$source_dir"/build/libaquamarine.so* "$prefix/lib/"
printf 'Private work runtime installed at %s\n' "$prefix/lib"
