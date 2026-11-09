#!/bin/sh
set -eu
LDM_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$LDM_ROOT"
LDM_RUN="workspace/demo-$(date +%Y%m%d-%H%M%S)-$$"
python3 -m ldm demo --workspace "$LDM_RUN"
if [ "$(uname)" = "Darwin" ]; then
  open "$LDM_RUN/report.html"
fi
