import os, shutil

from jinjaGenerator.settings import BASE_DIR
from .loader import create_jinja_env
from .wildcard_resolver import resolve_path


def __create_output_folder(template_name):
    output_folder = os.path.join(BASE_DIR, 'toutput', template_name)
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    return output_folder

def render(template_folder, context):
    project_folder = os.path.join(template_folder, 'project')
    env = create_jinja_env(template_folder)
    template_name = os.path.basename(template_folder)
    output_folder = __create_output_folder(template_name)

    # render all files in the project folder
    for root, dirs, files in os.walk(project_folder):
        for file in files:
            template_path = os.path.relpath(os.path.join(root, file), project_folder)
            template_path = str(template_path).replace('\\', '/')
            resolved_paths = resolve_path(template_path, context, env)
            for resolved_path, additional_context in resolved_paths:
                print("Processing file:", template_path, "->", resolved_path, "with context:", additional_context)
                if resolved_path.endswith('.jinja') or resolved_path.endswith('.j2'):
                    template = env.get_template(template_path)
                    full_context = context.copy()
                    full_context.update({"_path": additional_context})
                    output = template.render(full_context)
                    # determine the output path
                    relative_path = resolved_path
                    relative_path = relative_path.replace('.jinja', '').replace('.j2', '')
                    output_path = os.path.join(output_folder, relative_path)
                    output_dir = os.path.dirname(output_path)
                    os.makedirs(output_dir, exist_ok=True)
                    with open(output_path, 'w') as f:
                        f.write(output)
                else: # copy the file as is
                    source_path = os.path.join(root, file)
                    relative_path = resolved_path
                    output_path = os.path.join(output_folder, relative_path)
                    output_dir = os.path.dirname(output_path)
                    os.makedirs(output_dir, exist_ok=True)
                    shutil.copy(source_path, output_path)