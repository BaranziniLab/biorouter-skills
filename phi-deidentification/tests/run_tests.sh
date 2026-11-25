#!/usr/bin/env bash
# Copyright 2026 Baranzini Lab, University of California, San Francisco
# SPDX-License-Identifier: Apache-2.0
#
# Runs the upstream scanner tests (tests/upstream, from medsci-skills) and the
# Safe Harbor tests (tests/test_safe_harbor.py). Both use synthetic data only
# and need no network. To prove that, run them with networking denied, e.g. on
# macOS:
#
#   sandbox-exec -p '(version 1)(allow default)(deny network*)' bash tests/run_tests.sh
#
# or on Linux: unshare -rn bash tests/run_tests.sh
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
status=0

echo "== upstream scanner tests (tests/upstream/test_deidentify_scan.sh)"
bash "$HERE/upstream/test_deidentify_scan.sh" || status=1

echo "== Safe Harbor tests (tests/test_safe_harbor.py)"
python3 "$HERE/test_safe_harbor.py" || status=1

if [ "$status" -eq 0 ]; then echo "ALL TESTS PASSED"; else echo "SOME TESTS FAILED"; fi
exit "$status"
