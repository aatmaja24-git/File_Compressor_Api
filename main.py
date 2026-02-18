from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path
import pikepdf
from docx import Document

app = FastAPI(title="File Size Reducer API")

UPLOAD_DIR = "uploads"
COMPRESSED_DIR = "compressed"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_TYPES = [".pdf", ".docx", ".txt"]

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(COMPRESSED_DIR, exist_ok=True)


def optimize_file(file_path: str):
    extension = Path(file_path).suffix.lower()
    filename = os.path.basename(file_path)
    output_path = os.path.join(COMPRESSED_DIR, filename)

    # Optimize PDF
    if extension == ".pdf":
        with pikepdf.open(file_path) as pdf:
            pdf.save(output_path, compress_streams=True)

    # Re-save DOCX (minor optimization)
    elif extension == ".docx":
        doc = Document(file_path)
        doc.save(output_path)

    # Trim TXT
    elif extension == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return output_path


@app.post("/compress/")
async def upload_and_reduce(file: UploadFile = File(...)):
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {ALLOWED_FILE_TYPES}"
            )

        contents = await file.read()

        # File size validation
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        # Save uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(contents)

        # Optimize file
        output_path = optimize_file(file_path)
        optimized_filename = os.path.basename(output_path)

        return {
            "message": "File optimized successfully",
            "original_file": file.filename,
            "download_url": f"/download/{optimized_filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(COMPRESSED_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=filename)