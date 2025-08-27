# 1. Create a new file: force_imports.py (place in your project root)
"""
Force imports for buildozer to ensure all necessary modules are included
"""

# Force import all KivyMD picker components
try:
    from kivymd.uix.pickers.datepicker.datepicker import MDDatePicker
    from kivymd.uix.pickers.datepicker import *
except:
    pass

try:
    from kivymd.uix.pickers import MDDatePicker
    from kivymd.uix.pickers import *
except:
    pass

try:
    from kivymd.uix.picker import MDDatePicker
    from kivymd.uix.picker import *
except:
    pass

# Force import date/time related modules
import datetime
import calendar
import time
try:
    import dateutil
    import dateutil.parser
    import dateutil.tz
except:
    pass

try:
    import babel
    import babel.dates
except:
    pass

# Force import KivyMD core components that picker depends on
try:
    from kivymd.uix.behaviors import *
    from kivymd.uix.selectioncontrol import *
    from kivymd.theming import *
    from kivymd.material_resources import *
except:
    pass

print("Force imports loaded")