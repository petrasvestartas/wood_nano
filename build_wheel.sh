#!/bin/bash

# Exporting environment variable
export BUILDING_DIST="1"

# Running Python build to create a wheel
python -m build --wheel
