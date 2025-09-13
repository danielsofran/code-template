import os, shutil, importlib.util
import re
from typing import List, Tuple, Any, Dict

from jinja2 import Environment, FileSystemLoader

from jinjaGenerator.settings import BASE_DIR


def __first_level_folders(path):
    items = os.listdir(path)
    return [item for item in items if os.path.isdir(os.path.join(path, item))]

def __create_output_folder(template_name):
    output_folder = os.path.join(BASE_DIR, 'toutput', template_name)
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    return output_folder

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

def __create_jinja_env(template_folder):
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
    env = Environment(loader=FileSystemLoader(project_folder))
    # add filters
    for name, func in filters.items():
        env.filters[name] = func
    # add tests
    for name, func in tests.items():
        env.tests[name] = func
    # add other python functions / data to globals
    for name, func in other_python.items():
        env.globals[name] = func
    return env

def __process_wildcard(wildcard: str, context: dict, env: Environment) -> Tuple[str, Dict[str, Any]]:
    """
    Process a wildcard and return the resolved string and additional context.
    """
    if not '.' in wildcard and not '(' in wildcard:
        # simple case. just context.wildcard
        if wildcard in context:
            return str(context[wildcard]), {wildcard: str(context[wildcard])}
        else:
            raise ValueError(f"Wildcard '{wildcard}' not found in context")
    # complex case 1. nested context like model.name
    elif '.' in wildcard and not '(' in wildcard:
        parts = wildcard.split('.')
        value = context.copy()
        for part in parts:
            if part in value:
                value = value[part]
            else:
                raise ValueError(f"Wildcard '{wildcard}' not found in context")
        return str(value), {wildcard: str(value)}
    else: raise ValueError(f"Invalid wildcard format: {wildcard}")

def __resolve_path(path: str, context: dict, env: Environment) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Resolve a path with possible wildcards using the context.
    Returns a list of tuples (resolved_path, additional_context)
    """
    if '%' not in path:
        return [(path, {})]
    final_additional_context = {}
    path = path[:]
    while path.find('%') != -1:
        start_index = path.find('%')
        end_index = path.find('%', start_index + 1)
        if end_index == -1:
            break
        wildcard = path[start_index + 1:end_index]
        resolved_str, additional_context = __process_wildcard(wildcard, context, env)
        final_additional_context.update(additional_context)
        path = path[:start_index] + resolved_str + path[end_index + 1:]
    return [(path, final_additional_context)]

def render(template_folder, context):
    project_folder = os.path.join(template_folder, 'project')
    env = __create_jinja_env(template_folder)
    template_name = os.path.basename(template_folder)
    output_folder = __create_output_folder(template_name)

    # render all files in the project folder
    for root, dirs, files in os.walk(project_folder):
        for file in files:
            template_path = os.path.relpath(os.path.join(root, file), project_folder)
            template_path = str(template_path).replace('\\', '/')
            resolved_paths = __resolve_path(file, context, env)
            for resolved_path, additional_context in resolved_paths:
                if resolved_path.endswith('.jinja') or resolved_path.endswith('.j2'):
                    template = env.get_template(template_path)
                    full_context = context.copy()
                    full_context.update(additional_context)
                    output = template.render(full_context)
                    # determine the output path
                    # TODO: this can be modified in the output. to think a solution
                    relative_path = os.path.relpath(os.path.join(root, resolved_path), project_folder)
                    relative_path = relative_path.replace('.jinja', '').replace('.j2', '')
                    output_path = os.path.join(output_folder, relative_path)
                    output_dir = os.path.dirname(output_path)
                    os.makedirs(output_dir, exist_ok=True)
                    with open(output_path, 'w') as f:
                        f.write(output)
                else: # copy the file as is
                    source_path = os.path.join(root, file)
                    # TODO; this won't work for folders with wildcards
                    relative_path = os.path.join(os.path.dirname(os.path.relpath(source_path, project_folder)), resolved_path)
                    output_path = os.path.join(output_folder, relative_path)
                    output_dir = os.path.dirname(output_path)
                    os.makedirs(output_dir, exist_ok=True)
                    shutil.copy(source_path, output_path)