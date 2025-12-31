import os
import boto3
from app.services.cosmos import CosmosService
from dotenv import load_dotenv
from loguru import logger
from config.s3_config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME

load_dotenv()

def get_parent_id_by_psd(psd_number: str) -> str:
    """
    Fetch the main parent ID from Cosmos DB using a PSD number.
    
    Args:
        psd_number (str): The PSD number to search for
        
    Returns:
        str: The main parent ID if found, None otherwise
    """
    try:
        # Initialize Cosmos service
        cosmos_service = CosmosService()
        
        # Query to find document with the given PSD number
        query = """
        SELECT c.main_parent_id 
        FROM c 
        WHERE c.dType = @d_type 
        AND c.psd_number = @psd_number 
        AND c.active = @is_active
        """
        
        parameters = [
            {"name": "@d_type", "value": "main_parent"},
            {"name": "@psd_number", "value": psd_number},
            {"name": "@is_active", "value": True}
        ]
        
        # Execute the query
        items = list(cosmos_service.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        if not items:
            logger.warning(f"No document found with PSD number: {psd_number}")
            return None
            
        # Assuming the first match is what we want
        parent_id = items[0].get('main_parent_id')
        
        if not parent_id:
            logger.warning(f"Document found but no parentId for PSD: {psd_number}")
            return None
            
        logger.info(f"Found parent ID {parent_id} for PSD: {psd_number}")
        return parent_id
        
    except Exception as e:
        logger.error(f"Error fetching parent ID for PSD {psd_number}: {str(e)}")
        raise

def upload_sheets_to_s3(file_path: str, original_filename: str):
    """
    Upload an Excel sheet to S3 inside a folder named after the PSD number extracted from the original filename.
    Args:
        file_path (str): Path to the temp file.
        original_filename (str): The original filename uploaded by the user.
    Returns:
        str: S3 object key if upload is successful, None otherwise.
    """
    import re
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    s3 = session.client('s3')
    # Extract PSD number (e.g., SFDC-PSD-078063) from the original filename
    match = re.search(r'(SFDC-PSD-\d+)', original_filename)
    if not match:
        logger.error(f"Could not extract PSD number from filename: {original_filename}")
        return None
    psd_number = match.group(1)
    s3_key = f"{psd_number}/{original_filename}"
    try:
        s3.upload_file(file_path, S3_BUCKET_NAME, s3_key)
        logger.info(f"Uploaded {original_filename} to S3 bucket {S3_BUCKET_NAME} at {s3_key}")
        return s3_key
    except Exception as e:
        logger.error(f"Failed to upload {original_filename} to S3: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    psd = input("Enter PSD number: ").strip()
    if psd:
        parent_id = get_parent_id_by_psd(psd)
        if parent_id:
            print(f"Main Parent ID: {parent_id}")
        else:
            print("No matching record found for the given PSD number.")
    else:
        print("No PSD number provided.")
