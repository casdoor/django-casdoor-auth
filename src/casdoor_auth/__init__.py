try:
    from apps import *
    from urls import *
    from user import *
    from views import *
except ModuleNotFoundError or ImportError:
    from .apps import *
    from .urls import *
    from .user import *
    from .views import *

