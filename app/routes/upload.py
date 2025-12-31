from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from app.services.upload_sheet_r360 import upload_sheets_to_s3
from app.services.download_sheet_r360 import download_psd_files_from_s3
from app.services.upload_sheet_r360 import get_psd_by_sheet, get_parent_id_by_psd
from typing import Optional
import zipfile
import io
import logging

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/get-psd", response_model=dict, summary="Extract PSD from filename")
async def get_psd(
    filename: str = Query(
        ...,
        description="Filename in format 'LegalEntityMapping_SFDC-PSD-{number}_{timestamp}'",
        examples={"example1": {"value": "LegalEntityMapping_SFDC-PSD-076858_1767096012389"}}
    )
):
    """
    Extract PSD number from a properly formatted filename.
    
    The filename should be in the format: LegalEntityMapping_SFDC-PSD-{number}_{timestamp}
    """
    try:
        psd_number = get_psd_by_sheet(filename)
        return {
            "status": "success",
            "data": {
                "filename": filename,
                "psd_number": psd_number
            }
        }
    except ValueError as e:
        logger.error(f"Error extracting PSD from {filename}: {str(e)}")
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "message": str(e)
        })
    except Exception as e:
        logger.error(f"Unexpected error processing {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "message": "An unexpected error occurred"
        })

@router.get("/get-id", response_model=dict, summary="Get parent ID by PSD number")
async def get_id(
    psd_number: str = Query(
        ...,
        description="PSD number in format 'SFDC-PSD-{number}'",
        examples={"example1": {"value": "SFDC-PSD-076858"}}
    )
):
    """
    Fetch the parent ID associated with a given PSD number.
    
    The PSD number should be in the format: SFDC-PSD-{number}
    """
    try:
        parent_id = get_parent_id_by_psd(psd_number)
        if not parent_id:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "not_found",
                    "message": f"No parent ID found for PSD: {psd_number}"
                }
            )
            
        return {
            "status": "success",
            "data": {
                "psd_number": psd_number,
                "parent_id": parent_id
            }
        }
    except Exception as e:
        logger.error(f"Error fetching parent ID for PSD {psd_number}: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "message": f"Failed to fetch parent ID: {str(e)}"
        })


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
