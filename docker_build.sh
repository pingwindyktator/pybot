#!/usr/bin/env bash
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) -f "${SCRIPT_DIR}/Dockerfile" -t pybot "${SCRIPT_DIR}"
