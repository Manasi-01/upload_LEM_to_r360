from loguru import logger
from dotenv import load_dotenv
import os
from azure.cosmos import CosmosClient, exceptions, PartitionKey

load_dotenv()

class CosmosService:
    def __init__(self):
        self.cosmos_client = None
        self.database = None
        partition_path = os.getenv("COSMOS_DB_LOG_PARTITION_KEY", "/dType")
        if not partition_path.startswith("/"):
            partition_path = f"/{partition_path}"
        self._log_partition_path = partition_path
        self._initialize_cosmos()
    
    def _initialize_cosmos(self):
        """Initialize Cosmos DB client and container"""
        try:
            # Get Cosmos DB credentials from environment variables
            cosmos_endpoint = os.getenv("COSMOS_DB_URL")
            cosmos_key = os.getenv("COSMOS_DB_KEY")
            database_name = os.getenv("COSMOS_DB_DATABASE")
            container_name = os.getenv("COSMOS_DB_CONTAINER")
            
            if not cosmos_endpoint or not cosmos_key:
                raise ValueError("Missing required environment variables: COSMOS_ENDPOINT and COSMOS_KEY must be set")
                
            self.cosmos_client = CosmosClient(
                url=cosmos_endpoint,
                credential=cosmos_key
            )
            self.database = self.cosmos_client.get_database_client(database_name)
            self.container = self.database.get_container_client(container_name)
            logger.info("Cosmos DB initialized successfully")

        except Exception as e:
            logger.error(f" Failed to initialize Cosmos DB: {str(e)}")
            raise
