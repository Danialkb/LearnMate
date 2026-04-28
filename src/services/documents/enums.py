import enum


class DocumentFormat(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    WEB_PAGE = "web_page"


class DocumentLifecycleStatus(str, enum.Enum):
    NEW = "new"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class DocumentSourceType(str, enum.Enum):
    LOCAL_FILE = "local_file"
    URL = "url"
    TEXT_INPUT = "text_input"


class ProcessingJobType(str, enum.Enum):
    EXTRACT_TEXT = "extract_text"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"


class ProcessingJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
