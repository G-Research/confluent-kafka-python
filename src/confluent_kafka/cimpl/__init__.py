import importlib

variant = None

for module_name in ("sasl2_3", "sasl2_2", "nodeps"):
    try:
        module = importlib.import_module(f".{module_name}.cimpl", __package__)
        variant = module_name
        for name in dir(module):
            if not name.startswith("__"):
                globals()[name] = getattr(module, name)
        break
    except ImportError:
        pass

if variant is None:
    msg = "No valid native Python extension found"
    raise ImportError(msg)
