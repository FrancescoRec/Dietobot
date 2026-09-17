"""
Django settings loader.

This module selects the appropriate settings based on the DJANGO_SETTINGS_MODULE
environment variable. If not set, defaults to local settings.
"""

import os
import sys

# Determine which settings module to use
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.local')

if 'config.settings.local' in settings_module:
    from .local import *
elif 'config.settings.prod' in settings_module:
    from .prod import *
else:
    # Default to local if nothing else matches
    from .local import *
