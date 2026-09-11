"""
Step 2: PDF Text Extraction
----------------------------
Ye module resume PDF ke andar se clean, plain text nikaalta hai.
pdfplumber isliye use kiya hai kyunki ye layout (columns, tables) ko
PyPDF se better handle karta hai — resumes mein aksar aise formatting hoti hai.
"""

import pdfplumber


def extract_text_from_pdf(pdf_path: str) -> str:
    """Given a path to a resume PDF, return clean extracted text."""
    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n".join(text_parts)

    # basic cleanup — remove null bytes / stray characters that sometimes
    # come from badly-encoded PDFs
    full_text = full_text.replace("\x00", "")

    return full_text.strip()


if __name__ == "__main__":
    # Quick manual test: python pdf_extractor.py sample_resume.pdf
    import sys
    if len(sys.argv) > 1:
        print(extract_text_from_pdf(sys.argv[1]))
    else:
        print("Usage: python pdf_extractor.py <path_to_resume.pdf>")
