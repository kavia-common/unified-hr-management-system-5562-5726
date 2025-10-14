#!/bin/bash
cd /home/kavia/workspace/code-generation/unified-hr-management-system-5562-5726/hrms_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

