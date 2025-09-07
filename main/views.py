import datetime
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os, zipfile, tempfile, shutil

from .models import Template as TemplateModel
from .renderer.renderer import render


@csrf_exempt
def load_template(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({"error": "No file provided"}, status=400)

    uploaded_file = request.FILES['file']
    template_name = request.POST.get('name', 'default_template')
    if template_name.strip() == '':
        template_name = 'default_template'
    if not uploaded_file.name.endswith('.zip'):
        return JsonResponse({"error": "Only ZIP files are allowed"}, status=400)

    try:
        # Create a temporary directory to extract files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file to temporary location
            temp_zip_path = os.path.join(temp_dir, 'uploaded.zip')
            with open(temp_zip_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Extract ZIP file
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find the first directory in the extracted content
            extracted_items = os.listdir(temp_dir)
            first_level_dirs = [item for item in extracted_items if
                                os.path.isdir(os.path.join(temp_dir, item))]

            if not first_level_dirs:
                return JsonResponse({"error": "No directory found in ZIP file"}, status=400)

            # Get the first folder
            original_folder_name = first_level_dirs[0]
            original_folder_path = os.path.join(temp_dir, original_folder_name)

            # Define target directory (templates folder in project root)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            templates_dir = os.path.join(base_dir, 'templates')

            # Create templates directory if it doesn't exist
            os.makedirs(templates_dir, exist_ok=True)

            # Define new folder name (you can customize this)
            new_folder_path = os.path.join(templates_dir, template_name)

            # Create the template model
            existing_model = TemplateModel.objects.filter(name=template_name).first()
            if existing_model:
                existing_model.folder = new_folder_path
                existing_model.save()
            else:
                TemplateModel.objects.create(name=template_name, folder=new_folder_path)

            # Remove existing folder if it exists
            if os.path.exists(new_folder_path):
                shutil.rmtree(new_folder_path)

            # Move and rename the folder
            shutil.move(original_folder_path, new_folder_path)

        # return 200 ok and json response with message "Template loaded successfully"
        return JsonResponse({"message": "Template loaded successfully"}, status=200)

    except zipfile.BadZipFile:
        return JsonResponse({"error": "Invalid ZIP file"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Failed to process file: {str(e)}"}, status=500)

def render_template(request):
    # get the input of the template from the request body as json
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        input_str = request.body.decode('utf-8')
        input_data = json.loads(input_str)
    except Exception as e:
        return JsonResponse({"error": f"Invalid JSON input: {str(e)}"}, status=400)
    if not input_data:
        return JsonResponse({"error": "Input data is required"}, status=400)
    # get the template based on the query parameters 'template_name' or 'template_id'
    template_name = request.GET.get('template_name', None)
    template_id = request.GET.get('template_id', None)
    if not template_name and not template_id:
        return JsonResponse({"error": "template_name or template_id query parameter is required"}, status=400)
    if template_id:
        template = TemplateModel.objects.filter(id=template_id).first()
    else:
        template = TemplateModel.objects.filter(name=template_name).first()
    if not template:
        return JsonResponse({"error": "Template not found"}, status=404)

    template_folder = template.folder
    render(template_folder, input_data)
    return JsonResponse({"message": f"Rendering template from folder {template_folder} with input {input_data}"}, status=200)