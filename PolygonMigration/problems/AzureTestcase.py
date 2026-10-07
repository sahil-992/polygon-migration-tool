import os
from azure.identity import UsernamePasswordCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError
import logging

logger = logging.getLogger(__name__)


class AzureBlobManager:
    """
    Manager for Azure Blob Storage.

    Supports:
    1. Local Azurite development storage
    2. Real Azure Blob Storage
    """

    def __init__(self, account_url, tenant_id, client_id, username, password):
        """
        Initialize the Blob Service Client.
        """

        self.account_url = account_url
        self.blob_service_client = None

        logger.info("Attempting to connect to Azure Blob Storage...")

        try:
            # Local Azurite
            if self.account_url == "UseDevelopmentStorage=true":
                connection_string = (
                    "DefaultEndpointsProtocol=http;"
                    "AccountName=devstoreaccount1;"
                    "AccountKey="
                    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
                    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
                )

                self.blob_service_client = (
                    BlobServiceClient.from_connection_string(
                        connection_string
                    )
                )

            # Real Azure Blob Storage
            else:   
                credential = UsernamePasswordCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    username=username,
                    password=password
                )

                self.blob_service_client = BlobServiceClient(
                    account_url=self.account_url,
                    credential=credential
                )

            logger.info("BlobServiceClient created successfully.")

        except ClientAuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error during initialization: {e}"
            )
            raise

    def upload_test_case(
        self,
        container_name,
        db_problem_id,
        test_number,
        input_data,
        output_data
    ):
        """
        Upload a test case input and output to Blob Storage.

        Structure:

        test_cases/{problem_id}/{test_number}
        test_cases/{problem_id}/{test_number}.a
        """

        try:
            container_client = (
                self.blob_service_client.get_container_client(
                    container_name
                )
            )

            # Create container if it doesn't exist
            try:
                container_client.get_container_properties()
            except ResourceNotFoundError:
                logger.info(
                    f"Container '{container_name}' does not exist. "
                    "Creating it."
                )
                container_client.create_container()

            input_blob_name = (
                f"test_cases/{db_problem_id}/{test_number:02d}"
            )

            output_blob_name = (
                f"test_cases/{db_problem_id}/{test_number:02d}.a"
            )

            input_blob_client = container_client.get_blob_client(
                input_blob_name
            )

            output_blob_client = container_client.get_blob_client(
                output_blob_name
            )

            input_blob_client.upload_blob(
                input_data.encode("utf-8"),
                overwrite=True
            )

            output_blob_client.upload_blob(
                output_data.encode("utf-8"),
                overwrite=True
            )

            logger.info(
                f"Uploaded test case {test_number} for "
                f"problem {db_problem_id}"
            )

            return True

        except Exception as e:
            logger.error(
                f"Error uploading test case {test_number}: {e}"
            )
            raise

    def empty_blob(self, container_name, problem_id):
        """
        Delete all existing test-case blobs for a problem.
        """

        prefix = f"test_cases/{problem_id}/"

        try:
            container_client = (
                self.blob_service_client.get_container_client(
                    container_name
                )
            )

            blobs_to_delete = [
                blob.name
                for blob in container_client.list_blobs(
                    name_starts_with=prefix
                )
            ]

            for blob_name in blobs_to_delete:
                logger.info(f"Deleting blob: {blob_name}")
                container_client.delete_blob(blob_name)

            logger.info(
                f"Deleted {len(blobs_to_delete)} blobs "
                f"for problem {problem_id}"
            )

        except ResourceNotFoundError:
            logger.info(
                f"Container '{container_name}' does not exist yet."
            )

        except Exception as e:
            logger.error(
                f"Error deleting blobs for problem {problem_id}: {e}"
            )
            raise