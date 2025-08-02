try:
    from .sasl2_3.cimpl import *
    variant = "sasl2_3"
except ImportError:
    try:
        from .sasl2_2.cimpl import *
        variant = "sasl2_2"
    except ImportError:
        from .nodeps.cimpl import *
        variant = "nodeps"
