from __future__ import annotations

"""
One import for the whole app:

- Desktop: normal Kivy TextInput (with ScrollView-lock behavior)
- Android: AndroidNativeTextInput (native EditText overlay for Ink-to-Text)
"""

from kivy.utils import platform as kivy_platform

if kivy_platform == "android":
    from .android_native_textinput import AndroidNativeTextInput as VokabaTextInput
else:
    from .lock_textinput import LockScrollTextInput as VokabaTextInput

__all__ = ["VokabaTextInput"]
