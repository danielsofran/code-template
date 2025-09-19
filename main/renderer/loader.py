import importlib.util
import os

from jinja2 import Environment, FileSystemLoader

from main.renderer.defaults import render_fragment


def __first_level_folders(path):
    items = os.listdir(path)
    return [item for item in items if os.path.isdir(os.path.join(path, item))]

def __only_callable_values(d):
    return {k: v for k, v in d.items() if callable(v)}

def __load_python_files_from_folder(folder_path):
    python_elements = {}
    if not os.path.exists(folder_path):
        return python_elements
    python_files = [f for f in os.listdir(folder_path) if f.endswith('.py')]
    for py_file in python_files:
        py_path = os.path.join(folder_path, py_file)
        py_name = os.path.splitext(py_file)[0]
        try:
            spec = importlib.util.spec_from_file_location(py_name, py_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr in dir(module):
                if not attr.startswith('_'):
                    elem = getattr(module, attr)
                    python_elements[attr] = elem
        except Exception as e:
            print(f"Error loading {py_name} from {py_path}: {e}")
    return python_elements

def create_jinja_env(template_folder):
    folders = __first_level_folders(template_folder)
    if not 'project' in folders:
        raise ValueError("No 'project' folder found in the template")
    project_folder = os.path.join(template_folder, 'project')
    folders.remove('project')
    filters = {}
    tests = {}
    other_python = {}
    for folder in folders:
        if folder == 'filters':
            filters_folder = os.path.join(template_folder, 'filters')
            python_elements = __load_python_files_from_folder(filters_folder)
            filters = __only_callable_values(python_elements)
        elif folder == 'tests':
            tests_folder = os.path.join(template_folder, 'tests')
            python_elements = __load_python_files_from_folder(tests_folder)
            tests = __only_callable_values(python_elements)
        else:
            other_folder = os.path.join(template_folder, folder)
            python_elements = __load_python_files_from_folder(other_folder)
            other_python.update(python_elements)
    env = Environment(loader=FileSystemLoader(template_folder))
    # add filters
    for name, func in filters.items():
        env.filters[name] = func
    # add tests
    for name, func in tests.items():
        env.tests[name] = func
    env.globals['render_fragment'] = render_fragment
    # add other python functions / data to globals
    for name, func in other_python.items():
        env.globals[name] = func
    return env
