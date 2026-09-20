"""Explicit experimental launcher profile using the shared isolated HD pipeline."""
from functools import partial

import completehd

PROFILE = completehd.WIDGET_PROFILE
DIRECTORY = completehd.WIDGET_DIRECTORY
STAGE = completehd.WIDGET_STAGE
WARNING = completehd.WIDGET_WARNING
source_status = partial(completehd.source_status, profile=PROFILE)
plan_candidate = partial(completehd.plan_candidate, profile=PROFILE)
ensure_candidate = completehd.ensure_candidate
deploy_runtime_files = completehd.deploy_runtime_files
verify_launch = completehd.verify_launch
