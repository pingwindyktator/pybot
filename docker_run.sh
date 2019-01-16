#!/usr/bin/env bash

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run --user appuser -it --rm -v /etc/localtime:/etc/localtime:ro -v $SCRIPT_DIR:/pybot:z pybot
