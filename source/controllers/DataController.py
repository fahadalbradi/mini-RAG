from .BaseController import BaseController
from .ProjectController import ProjectController
from fastapi import UploadFile
from models import ResponseSignal
import re
import os

class DataController(BaseController):

    def __init__(self):
        super().__init__()
        self.size_scale = 1048576  # 1 MB in bytes

    def validate_uploaded_file(self, file: UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

        if file.size is not None and file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseSignal.FILE_SIZE_EXCEEDED.value

        return True, ResponseSignal.FILE_UPLOAD_SUCCESS.value

    def get_clean_file_name(self, orig_file_name: str):
        cleaned_file_name = orig_file_name.strip().replace(" ", "_")
        cleaned_file_name = re.sub(r'[^\w.]', '', cleaned_file_name)
        return cleaned_file_name

    def generate_unique_filepath(self, orig_file_name: str, project_id: str):
        project_path = ProjectController().get_project_path(project_id=project_id)
        cleaned_filename = self.get_clean_file_name(orig_file_name=orig_file_name)

        while True:
            file_id = self.generate_random_string() + "_" + cleaned_filename
            new_file_path = os.path.join(project_path, file_id)
            if not os.path.exists(new_file_path):
                return new_file_path, file_id
