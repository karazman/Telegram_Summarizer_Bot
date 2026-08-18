"""
Azure Blob Storage integration for message persistence.
"""

import json
import datetime
from zoneinfo import ZoneInfo
from azure.storage.blob import BlobServiceClient, BlobClient
from typing import List, Dict, Optional


class BlobMessageStorage:
    """Handle message storage in Azure Blob Storage."""

    def __init__(self, connection_string: str, container_name: str = "telegram-messages"):
        """Initialize blob storage client."""
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        self.container_client = self.blob_service_client.get_container_client(container_name)
        
        # Ensure container exists
        try:
            self.container_client.get_container_properties()
        except:
            self.container_client.create_container()

    def save_message(self, message_data: Dict) -> None:
        """Save a message to blob storage."""
        try:
            # Create blob name based on chat_id and timestamp
            chat_id = message_data.get("chat_id")
            timestamp = message_data.get("date", datetime.datetime.now().isoformat())
            
            # Format: messages/{chat_id}/YYYY/MM/DD/{timestamp}_{user_id}.json
            blob_name = (
                f"messages/{chat_id}/"
                f"{timestamp[:10].replace('-', '/')}/{timestamp.replace(':', '-')}_"
                f"{message_data.get('user_id')}.json"
            )
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(json.dumps(message_data), overwrite=True)
            
        except Exception as e:
            print(f"Error saving message to blob storage: {e}")
            raise

    def load_messages_last_24_hours(
        self,
        chat_id: int,
        timezone: ZoneInfo = ZoneInfo("Europe/Vienna")
    ) -> List[Dict]:
        """Load all messages from the last 24 hours for a specific chat."""
        try:
            now = datetime.datetime.now(timezone)
            start = now - datetime.timedelta(hours=24)
            
            messages = []
            prefix = f"messages/{chat_id}/"
            
            # List all blobs in the chat folder
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            
            for blob in blobs:
                try:
                    blob_client = self.blob_service_client.get_blob_client(
                        container=self.container_name,
                        blob=blob.name
                    )
                    
                    data = blob_client.download_blob().readall()
                    message_data = json.loads(data)
                    
                    # Parse date and check if within 24 hours
                    message_date = datetime.datetime.fromisoformat(message_data.get("date", ""))
                    
                    if message_date.tzinfo is None:
                        message_date = message_date.replace(tzinfo=timezone)
                    
                    if message_date >= start:
                        messages.append({
                            "username": message_data.get("username", "").lower(),
                            "message": message_data.get("message", ""),
                            "date": message_date,
                            "user_id": message_data.get("user_id"),
                        })
                
                except json.JSONDecodeError:
                    continue
                except ValueError:
                    continue
            
            # Sort by date
            messages.sort(key=lambda x: x["date"])
            return messages
            
        except Exception as e:
            print(f"Error loading messages from blob storage: {e}")
            return []

    def cleanup_old_messages(self, days_to_keep: int = 30) -> None:
        """Delete messages older than specified days."""
        try:
            now = datetime.datetime.now()
            cutoff_date = now - datetime.timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()[:10]
            
            blobs = self.container_client.list_blobs()
            
            for blob in blobs:
                # Extract date from blob name (YYYY/MM/DD format)
                parts = blob.name.split("/")
                if len(parts) >= 3:
                    blob_date_str = f"{parts[1]}-{parts[2]}-{parts[3]}"
                    
                    if blob_date_str < cutoff_str:
                        blob_client = self.blob_service_client.get_blob_client(
                            container=self.container_name,
                            blob=blob.name
                        )
                        blob_client.delete_blob()
                        
        except Exception as e:
            print(f"Error cleaning up old messages: {e}")
