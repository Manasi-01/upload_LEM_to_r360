import os
import tempfile
import boto3
from config.s3_config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from loguru import logger

def download_psd_files_from_s3(psd_number: str):
    """
    Download all files for a given PSD number from S3 to temp files.
    Returns a list of (original_filename, temp_file_path).
    """
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    s3 = session.client('s3')
    prefix = f"{psd_number}/"
    downloaded = []
    
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        for obj in response.get('Contents', []):
            key = obj['Key']
            filename = os.path.basename(key)
            if not filename:  # Skip directory entries
                continue
            # Create temp file and close it immediately
            with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
                tmp_path = tmp.name
            try:
                # Download file
                s3.download_file(S3_BUCKET_NAME, key, tmp_path)
                downloaded.append((filename, tmp_path))
            except Exception as e:
                # Clean up if download fails
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                logger.error(f"Failed to download {key}: {e}")
        return downloaded
    except Exception as e:
        # Clean up any downloaded files if an error occurs
        for _, path in downloaded:
            try:
                os.unlink(path)
            except:
                pass
        logger.error(f"Failed to list/download files for {psd_number}: {e}")
        return []
