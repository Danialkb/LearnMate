import enum


class DocumentFormat(str, enum.Enum):
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    MARKDOWN = "MARKDOWN"
    WEB_PAGE = "WEB_PAGE"


class DocumentLifecycleStatus(str, enum.Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class DocumentSourceType(str, enum.Enum):
    LOCAL_FILE = "LOCAL_FILE"
    URL = "URL"
    TEXT_INPUT = "TEXT_INPUT"


class DocumentSummaryStyle(str, enum.Enum):
    BRIEF = "brief"
    DETAILED = "detailed"
    BULLETS = "bullets"


class QuizGenerationMode(str, enum.Enum):
    DOCUMENT = "document"
    QUERY = "query"


class ProcessingJobType(str, enum.Enum):
    EXTRACT_TEXT = "EXTRACT_TEXT"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"


class ProcessingJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
