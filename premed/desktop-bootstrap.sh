#!/bin/bash
set -euo pipefail

track="${1:-}"
case "$track" in collab|statsam) ;; *) echo "Usage: desktop-bootstrap.sh collab|statsam" >&2; exit 2 ;; esac
command -v plutil >/dev/null || { echo "This Mac is missing plutil; stopped before changing files." >&2; exit 1; }
command -v curl >/dev/null || { echo "curl is unavailable; ask the instructor for help." >&2; exit 1; }

base='https://sam-workshop-landing.vercel.app/premed/'
root="$(pwd -P)"
state="$root/.bootstrap"
manifest="$state/desktop-bootstrap.json"
mkdir -p "$state"
unexpected="$(find "$root" -mindepth 1 -maxdepth 1 ! -name .bootstrap -print -quit)"
[[ -z "$unexpected" ]] || { echo 'The selected folder is not empty. Choose a new dedicated folder; nothing was overwritten.' >&2; exit 1; }
while IFS= read -r item; do
  name="$(basename "$item")"
  case "$name" in desktop-bootstrap.json|desktop-bootstrap.ps1|desktop-bootstrap.sh) ;; *) echo 'The .bootstrap folder contains unexpected files; nothing was overwritten.' >&2; exit 1 ;; esac
done < <(find "$state" -mindepth 1 -maxdepth 1 -print)
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$base"'desktop-bootstrap.json' -o "$manifest"

field() { plutil -extract "$1" raw -o - "$manifest"; }
uv_bin=''
ensure_pinned_uv() {
  [[ -n "$uv_bin" ]] && return 0
  local machine uv_key uv_file uv_sha uv_expected_file uv_archive uv_actual uv_dir
  machine="$(uname -m)"
  case "$machine" in
    arm64|aarch64) uv_key=macos_arm64; uv_file=uv-aarch64-apple-darwin.tar.gz ;;
    x86_64) uv_key=macos_x64; uv_file=uv-x86_64-apple-darwin.tar.gz ;;
    *) echo "Unsupported Mac architecture: $machine" >&2; return 1 ;;
  esac
  uv_sha="$(field "runtime.uv_assets.$uv_key.sha256")"
  uv_expected_file="$(field "runtime.uv_assets.$uv_key.file")"
  [[ "$uv_expected_file" == "$uv_file" && "$uv_sha" =~ ^[0-9a-f]{64}$ ]] || { echo 'No pinned uv checksum exists for this Mac.' >&2; return 1; }
  uv_archive="$state/$uv_file"
  curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "${uv_base}${uv_file}" -o "$uv_archive"
  uv_actual="$(shasum -a 256 "$uv_archive" | awk '{print $1}')"
  [[ "$uv_actual" == "$uv_sha" ]] || { echo 'uv checksum mismatch; refusing to run the downloaded tool.' >&2; return 1; }
  uv_dir="$state/uv-unpacked"
  mkdir -p "$uv_dir"
  tar -tzf "$uv_archive" | awk -F/ 'BEGIN{bad=0} /^\//{bad=1} /(^|\/)\.\.?($|\/)/{bad=1} END{exit bad}' || { echo 'Unsafe uv archive path; refusing to extract.' >&2; return 1; }
  tar --no-same-owner -xzf "$uv_archive" -C "$uv_dir"
  uv_bin="$(find "$uv_dir" -type f -name uv -print -quit)"
  [[ -n "$uv_bin" ]] || { echo 'Verified uv archive did not contain the uv executable.' >&2; return 1; }
  chmod u+x "$uv_bin"
}
archive_name="$(field "tracks.$track.archive")"
archive_url="$(field "tracks.$track.url")"
expected_sha="$(field "tracks.$track.sha256")"
expected_bytes="$(field "tracks.$track.bytes")"
target_name="$(field "tracks.$track.target_directory")"
minimum_python="$(field runtime.minimum_python)"
python_minor="$(field runtime.managed_python_minor)"
uv_base="$(field runtime.uv_release_base)"

[[ "$expected_sha" =~ ^[0-9a-f]{64}$ && "$expected_bytes" =~ ^[0-9]+$ ]] || { echo "The $track package is not ready in the manifest. Ask the instructor for the current bundle." >&2; exit 1; }
[[ "$archive_name" =~ ^[A-Za-z0-9._-]+\.zip$ ]] || { echo 'Manifest archive filename is unsafe.' >&2; exit 1; }
case "$archive_url" in https://sam-workshop-landing.vercel.app/premed/*) ;; *) echo 'Package URL is outside the approved HTTPS host.' >&2; exit 1 ;; esac
case "$track:$target_name" in collab:student-collab|statsam:statsam-student) ;; *) echo 'Manifest target folder is not an approved track folder.' >&2; exit 1 ;; esac
target="$root/$target_name"
[[ ! -e "$target" ]] || { echo "Target already exists; nothing was overwritten: $target" >&2; exit 1; }

archive="$state/$archive_name"
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$archive_url" -o "$archive"
actual_bytes="$(wc -c < "$archive" | tr -d '[:space:]')"
[[ "$actual_bytes" == "$expected_bytes" ]] || { echo "Package size mismatch ($actual_bytes bytes); refusing to extract." >&2; exit 1; }
actual_sha="$(shasum -a 256 "$archive" | awk '{print $1}')"
[[ "$actual_sha" == "$expected_sha" ]] || { echo 'Package SHA-256 mismatch; refusing to extract.' >&2; exit 1; }

# Find an existing Python first; otherwise install a pinned uv-managed runtime under this new folder.
python_command=''
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    line="$("$candidate" --version 2>&1 || true)"
    if [[ "$line" =~ Python\ ([0-9]+\.[0-9]+) ]] && awk -v have="${BASH_REMATCH[1]}" -v need="$minimum_python" 'BEGIN{split(have,a,".");split(need,b,".");exit !((a[1]+0>b[1]+0)||((a[1]+0==b[1]+0)&&(a[2]+0>=b[2]+0)))}'; then
      if "$candidate" -c 'import venv, ensurepip' >/dev/null 2>&1; then
        python_command="$(command -v "$candidate")"
        break
      fi
    fi
  fi
done
managed=false
if [[ -z "$python_command" ]]; then
  ensure_pinned_uv || exit 1
  export UV_PYTHON_INSTALL_DIR="$root/.runtime/python"
  export UV_PYTHON_INSTALL_BIN=0
  export UV_PYTHON_INSTALL_REGISTRY=0
  export UV_CACHE_DIR="$root/.runtime/cache"
  mkdir -p "$UV_PYTHON_INSTALL_DIR" "$UV_CACHE_DIR"
  "$uv_bin" python install "$python_minor" --no-bin --no-registry
  python_command="$("$uv_bin" python find "$python_minor" --managed-python)"
  [[ -x "$python_command" ]] || { echo 'Could not locate the local Python runtime after installation.' >&2; exit 1; }
  managed=true
fi
if [[ "$track" == statsam ]]; then
  ensure_pinned_uv || exit 1
  export PATH="$(dirname "$uv_bin"):$PATH"
fi

# Validate every ZIP member, reject symlinks and traverse paths, then extract without following links.
mkdir "$target"
"$python_command" - "$archive" "$target" <<'PY'
import os, stat, sys, zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
archive, destination = sys.argv[1:]
root = Path(destination).resolve()
with zipfile.ZipFile(archive) as zf:
    items = zf.infolist()
    if len(items) > 2000 or sum(i.file_size for i in items) > 100_000_000:
        raise SystemExit('ZIP exceeds the workshop extraction limits; refusing to extract.')
    checked = []
    for info in items:
        name = info.filename
        parts = PurePosixPath(name).parts
        mode = (info.external_attr >> 16) & 0xFFFF
        if not name or name.startswith('/') or '\\' in name or PureWindowsPath(name).drive or any(p in ('', '.', '..') for p in parts):
            raise SystemExit(f'Unsafe ZIP member path: {name!r}')
        if stat.S_ISLNK(mode) or (mode and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))):
            raise SystemExit(f'ZIP links or special files are not allowed: {name!r}')
        target = root.joinpath(*parts)
        if os.path.commonpath([str(root), str(target.resolve())]) != str(root):
            raise SystemExit(f'ZIP member escapes the selected folder: {name!r}')
        checked.append((info, target))
    for info, target in checked:
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as source, open(target, 'xb') as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
PY

case "$track" in
  collab) required=(START_HERE.html pipeline.py AGENTS.md) ;;
  statsam) required=(README.md source_manifest.json bootstrap.py requirements.txt) ;;
esac
for name in "${required[@]}"; do [[ -f "$target/$name" ]] || { echo "Required package file is missing: $name" >&2; exit 1; }; done
printf 'BUNDLE_READY track=%s package_sha256=%s\n' "$track" "$actual_sha"

venv="$target/.venv"
"$python_command" -m venv "$venv"
venv_python="$venv/bin/python"
[[ -x "$venv_python" ]] || { echo 'The virtual environment interpreter was not created.' >&2; exit 1; }
version_line="$("$venv_python" --version 2>&1)"
if [[ ! "$version_line" =~ Python\ ([0-9]+\.[0-9]+) ]] || ! awk -v have="${BASH_REMATCH[1]:-0.0}" -v need="$minimum_python" 'BEGIN{split(have,a,".");split(need,b,".");exit !((a[1]+0>b[1]+0)||((a[1]+0==b[1]+0)&&(a[2]+0>=b[2]+0)))}'; then
  echo "Unsupported Python runtime: $version_line" >&2
  exit 1
fi

checks=()
if [[ "$track" == collab ]]; then
  doctor="$target/.doctor.json"
  "$venv_python" -X utf8 "$target/pipeline.py" doctor > "$doctor"
  "$venv_python" - "$doctor" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding='utf-8'))
required = ('python_supported','write_read_korean','core_hashes_match','path_ok','folder_ok')
failed = [key for key in required if data.get(key) is not True]
if failed:
    raise SystemExit('Collab doctor checks failed: ' + ', '.join(failed))
PY
  rm -f "$doctor"
  checks+=(pipeline_doctor=PASS)
else
  for step in setup doctor verify; do
    "$venv_python" -X utf8 "$target/bootstrap.py" "$step"
    printf 'STATSam_%s_PASS\n' "$(printf '%s' "$step" | tr '[:lower:]' '[:upper:]')"
    checks+=("statsam_${step}=PASS")
  done
fi

python_source='existing interpreter; venv workspace-local'
[[ "$managed" == true ]] && python_source='uv-managed interpreter; project-local'
{
  printf 'completed_utc=%s\ntrack=%s\npackage=%s\nsha256=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$track" "$archive_name" "$actual_sha"
  printf 'extracted_to=%s\npython=%s\npython_source=%s\ninterpreter=%s\n' "$target" "$version_line" "$python_source" "$venv_python"
  printf 'bundle_ready=true\nanalysis_ready=true\nanalysis_checks=%s\n' "$(IFS=,; echo "${checks[*]}")"
} > "$root/WORKSHOP_SETUP.txt"
printf 'SETUP_OK track=%s package_sha256=%s bundle_ready=true analysis_ready=true python=%s\n' "$track" "$actual_sha" "$version_line"
printf 'Track folder: %s\nUse this interpreter for the bootstrap host: %s\n' "$target" "$venv_python"
