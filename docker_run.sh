#!/usr/bin/env bash

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run -it --rm -v /etc/localtime:/etc/localtime:ro -v $SCRIPT_DIR:/pybot:z pybot