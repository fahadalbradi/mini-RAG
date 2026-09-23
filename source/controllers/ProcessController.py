from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import ProcessingEnum

class ProcessController(BaseController):

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1].lower().replace(".", "")

    def get_file_loader(self, file_id: str):
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(
            self.project_path,
            file_id
        )

        if not os.path.exists(file_path):
            return None

        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        if file_ext == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)

        return None

    def get_file_content(self, file_id: str):
        loader = self.get_file_loader(file_id=file_id)
        if loader is None:
            return None
        return loader.load()

    def process_file_content(self, file_content: list, file_id: str, chunk_size: int = 800, overlap: int = 100):
        if not file_content:
            return None

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=min(overlap, chunk_size - 1),
            length_function=len
        )

        chunks = text_splitter.split_documents(file_content)

        # keep only useful, JSON-friendly metadata and hide the absolute server path
        for chunk in chunks:
            metadata = {"source": file_id}
            if "page" in chunk.metadata:
                metadata["page"] = int(chunk.metadata["page"]) + 1
            chunk.metadata = metadata

        return [chunk for chunk in chunks if chunk.page_content.strip()]
