#! python3
# venv: wood_env
# r: wood-nano==1.0.8
# r: session-py==0.84.0
# r: session-rhino==0.37.0

import wood_nano
import session_rhino
from importlib.metadata import version

print(f"Successfully installed wood-nano=={version('wood-nano')} and session-rhino=={version('session-rhino')}!")