import zipfile
import xml.etree.ElementTree as ET
import os

docx_path = r"c:\Users\shrut\OneDrive\Desktop\team_3\bootcamp-ace-26-team-3\MVP_plan.docx"

def get_docx_text(path):
    if not os.path.exists(path):
        return f"File not found: {path}"
    try:
        # Try to read standard word/document.xml inside docx
        with zipfile.ZipFile(path) as z:
            doc_xml = z.read("word/document.xml")
            root = ET.fromstring(doc_xml)
            
            # XML namespace for word processingML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            paragraphs = []
            for para in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                texts = []
                for run in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if run.text:
                        texts.append(run.text)
                paragraphs.append("".join(texts))
            
            return "\n".join(paragraphs)
    except Exception as e:
        return f"Error reading docx: {e}"

print(get_docx_text(docx_path))
