#!/bin/sh
set -eu
skill_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
        exec "$candidate" -B "$skill_dir/scripts/setup_wechat.py" "$@"
    fi
done
if command -v uv >/dev/null 2>&1; then
    exec uv run --no-project --python 3.12 python -B "$skill_dir/scripts/setup_wechat.py" "$@"
fi
case "$(uname -m)" in
    x86_64) cpu=x86_64 ;;
    arm64|aarch64) cpu=aarch64 ;;
    *) echo 'Unsupported architecture; use exported chat text.' >&2; exit 2 ;;
esac
case "$(uname -s)" in
    Darwin) target="$cpu-apple-darwin" ;;
    Linux) target="$cpu-unknown-linux-gnu" ;;
    *) echo 'Unsupported OS.' >&2; exit 2 ;;
esac
bootstrap="$HOME/.sales-dialogue-assistant/bootstrap/uv-0.7.22"
mkdir -p "$bootstrap"
asset="uv-$target.tar.gz"
base='https://github.com/astral-sh/uv/releases/download/0.7.22'
curl --fail --location --proto '=https' "$base/$asset" -o "$bootstrap/$asset"
curl --fail --location --proto '=https' "$base/$asset.sha256" -o "$bootstrap/$asset.sha256"
expected=$(awk '{print $1}' "$bootstrap/$asset.sha256")
if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$bootstrap/$asset" | awk '{print $1}')
else
    actual=$(shasum -a 256 "$bootstrap/$asset" | awk '{print $1}')
fi
[ "$expected" = "$actual" ] || { echo 'uv checksum mismatch; not executed.' >&2; exit 2; }
tar -xzf "$bootstrap/$asset" -C "$bootstrap"
exec "$bootstrap/uv-$target/uv" run --no-project --python 3.12 python -B "$skill_dir/scripts/setup_wechat.py" "$@"
