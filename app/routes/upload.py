from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.services.upload_sheet_r360 import upload_sheets_to_s3
from app.services.download_sheet_r360 import download_psd_files_from_s3
import zipfile
import io

router = APIRouter()

@router.get("/download-sheet/{psd_number}")
def download_sheet(psd_number: str):
    files = download_psd_files_from_s3(psd_number)
    if not files:
        raise HTTPException(status_code=404, detail="No files found for this PSD number.")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for filename, path in files:
            zipf.write(path, arcname=filename)
    zip_buffer.seek(0)
    # Cleanup temp files
    for _, path in files:
        try:
            import os
            os.remove(path)
        except Exception:
            pass
    return StreamingResponse(zip_buffer, media_type="application/x-zip-compressed", headers={"Content-Disposition": f"attachment; filename={psd_number}_files.zip"})

@router.post("/upload-sheet/")
def upload_sheet(file: UploadFile = File(...)):
    import tempfile
    import shutil
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        s3_key = upload_sheets_to_s3(tmp_path, file.filename)
        if not s3_key:
            raise HTTPException(status_code=500, detail="Failed to upload file to S3.")
        return {"s3_key": s3_key}
    finally:
        file.file.close()
        try:
            import os
            os.remove(tmp_path)
        except Exception:
            pass
