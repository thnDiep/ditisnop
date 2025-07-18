import os
from tqdm import tqdm
from openai import OpenAI
import concurrent


class VectorStoreUploader:
    """
    Helper class to create a Vector Store and upload multiple files to it.
    """

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def create_vector_store(self, store_name: str) -> dict:
        try:
            vector_store = self.client.vector_stores.create(name=store_name)
            details = {
                "id": vector_store.id,
                "name": vector_store.name,
                "created_at": vector_store.created_at,
                "file_count": vector_store.file_counts.completed,
            }
            print("[INFO] - Vector store created:", details)
            return details
        except Exception as e:
            print(f"[ERROR] - Error creating vector store: {e}")
            return {}

    def upload_file(self, file_path: str, vector_store_id: str) -> dict:
        """
        Upload a single file to Vector Store.
        """
        file_name = os.path.basename(file_path)

        try:
            file_response = self.client.files.create(
                file=open(file_path, "rb"), purpose="assistants"
            )
            self.client.vector_stores.files.create(
                vector_store_id=vector_store_id, file_id=file_response.id
            )
            return {"file": file_name, "status": "success"}
        except Exception as e:
            print(f"[ERROR] - Error with {file_name}: {str(e)}")
            return {"file": file_name, "status": "failed", "error": str(e)}

    def upload_files_to_vector_store(
        self, files: list[str], vector_store_id: str
    ) -> dict:
        """
        Upload all files in a directory to Vector Store in parallel.
        """
        stats = {
            "total_files": len(files),
            "successful_uploads": 0,
            "failed_uploads": 0,
            "errors": [],
        }

        print(f"[INFO] - Uploading {len(files)} delta files in parallel...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self.upload_file, file_path, vector_store_id): file_path
                for file_path in files
            }
            for future in tqdm(
                concurrent.futures.as_completed(futures), total=len(files)
            ):
                result = future.result()
                if result["status"] == "success":
                    stats["successful_uploads"] += 1
                else:
                    stats["failed_uploads"] += 1
                    stats["errors"].append(result)

        return stats

    def retrive_vector_store(self, vector_store_id: str) -> dict:
        """
        Retrieve details of a Vector Store.
        """
        try:
            vector_store = self.client.vector_stores.retrieve(vector_store_id)

            details = {
                "ID": vector_store.id,
                "Name": vector_store.name,
                "Created At": vector_store.created_at,
                "File Count": vector_store.file_counts.completed,
            }

            print(f"\n Vector Store Details:")
            for k, v in details.items():
                print(f"- {k}: {v}")
        except Exception as e:
            print(f"[ERROR] - Error retrieving vector store: {e}")
            return {}

    def list_vector_stores(self) -> list[dict]:
        """
        List all vector stores with basic metadata as list of dicts.
        """
        try:
            stores = self.client.vector_stores.list().data
            return [
                {
                    "id": vs.id,
                    "name": vs.name,
                    "created_at": vs.created_at,
                    "file_count": vs.file_counts.completed,
                }
                for vs in stores
            ]
        except Exception as e:
            print(f"[ERROR] - Failed to list vector stores: {e}")
            return []
