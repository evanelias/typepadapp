from assets import *
from auth import *
from groups import *
from users import *
from profiles import *


APPLICATION, GROUP = None, None


import typepadapp.signals
import typepadapp.utils.loading

typepadapp.signals.post_start.send(None)
