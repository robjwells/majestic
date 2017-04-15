import importlib
import sys


def load_extensions(directory):
    """Import all modules in directory and return a list of them"""
    # Add extensions directory to path
    sys.path.insert(0, str(directory))

    module_names = [file.stem for file in directory.iterdir()
                    if file.suffix == '.py']
    imported_modules = [importlib.import_module(name) for name in module_names]

    # Remove extensions directory from path
    sys.path = sys.path[1:]
    return imported_modules
