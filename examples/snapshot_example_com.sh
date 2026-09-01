#!/usr/bin/env bash
set -euo pipefail
# example.com is the IANA reserved documentation host.
gemini-cloner web https://example.com
gemini-cloner report clones/example.com
