from services.documents.enums import DocumentSummaryStyle


def parse_summary_style(style: str) -> DocumentSummaryStyle:
    normalized = style.strip().lower()
    for summary_style in DocumentSummaryStyle:
        if normalized in {summary_style.value, summary_style.name.lower()}:
            return summary_style
    return DocumentSummaryStyle.BRIEF
