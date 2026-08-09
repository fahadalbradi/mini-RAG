from enum import Enum

class ResponseSignal(Enum):
    FILE_TYPE_NOT_SUPPORTED = "file type is not supported"
    FILE_SIZE_EXCEEDED = "file size exceeds the maximum limit"
    FILE_UPLOAD_SUCCESS = "successfully validated the uploaded file"
    FILE_UPLOAD_FAILED = "file upload failed"
    FILE_VALIDATION_FAILED = "file validation failed"
    FILE_PROCESSING_FAILED = "file processing failed"