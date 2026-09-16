#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="${DUOOMARCHY_BUILD_DIR:-$root/.build/gamescope}"
prefix="${DUOOMARCHY_DATA:-$HOME/.local/share/duoomarchy}/runtime"
revision=17baf4abd1ab3353fb705e4d0d023f84e870f7e8
if [[ -e "$source_dir" ]]; then
  echo "Build directory already exists: $source_dir. Use another DUOOMARCHY_BUILD_DIR for a clean build." >&2
  exit 1
fi
git clone --no-checkout https://github.com/ValveSoftware/gamescope.git "$source_dir"
git -C "$source_dir" checkout --detach "$revision"
git -C "$source_dir" submodule update --init --recursive
git -C "$source_dir" apply --check "$root/patches/gamescope-selective-input.patch"
git -C "$source_dir" apply "$root/patches/gamescope-selective-input.patch"
meson setup "$source_dir/build" "$source_dir" --prefix="$prefix" \
  -Denable_openvr_support=false -Denable_gamescope_wsi_layer=false \
  -Denable_tests=false -Dbenchmark=disabled -Dbuildtype=release
ninja -C "$source_dir/build" -j "${BUILD_JOBS:-4}"
meson install -C "$source_dir/build"
printf 'Private Gamescope installed at %s\n' "$prefix/bin/gamescope"
