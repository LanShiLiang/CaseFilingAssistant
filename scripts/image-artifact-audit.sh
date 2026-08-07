#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "usage: $0 IMAGE [IMAGE...]" >&2
  exit 2
fi

audit_root="$(mktemp -d)"
container_ids=()
cleanup() {
  for container_id in "${container_ids[@]}"; do
    docker rm --force "$container_id" >/dev/null 2>&1 || true
  done
  rm -rf "$audit_root"
}
trap cleanup EXIT

for image in "$@"; do
  safe_name="${image//[^a-zA-Z0-9_.-]/_}"
  container_id="$(docker create "$image")"
  container_ids+=("$container_id")
  docker export "$container_id" > "$audit_root/$safe_name.tar"
  docker rm "$container_id" >/dev/null
  tar -tf "$audit_root/$safe_name.tar" > "$audit_root/$safe_name.files"

  # 只检查工作目录和秘密扩展名，避免把基础镜像自带文档误判为仓库制品。
  if grep -E '(^|/)app/(outputs|e2e|tests?|test-results|playwright-report|\.git|\.local|\.artifacts)(/|$)|(^|/)app/app/tests?(/|$)|(^|/)app/apps/web/.*\.(test|spec)\.[cm]?[jt]sx?$|\.(pem|p12|pfx|key)$|(^|/)app/\.env($|\.)' "$audit_root/$safe_name.files"; then
    echo "forbidden runtime artifact found in $image" >&2
    exit 1
  fi

  image_size="$(docker image inspect "$image" --format '{{.Size}}')"
  case "$image" in
    *api*) max_size=1200000000 ;;
    *web*) max_size=500000000 ;;
    *) max_size=1200000000 ;;
  esac
  if (( image_size > max_size )); then
    echo "$image exceeds size budget: $image_size > $max_size bytes" >&2
    exit 1
  fi
  echo "audited $image ($image_size bytes; budget $max_size)"
done
