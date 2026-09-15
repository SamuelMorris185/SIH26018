import os
import uuid
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import anyio
from app.core.config import BACKEND_DIR, settings
from app.core.logging import logger
from app.core.exceptions import MissingFileError

class BaseStorageService(ABC):
    """
    Abstract interface for document file storage.
    Enables swapping between local filesystem and cloud object storage (S3/GCS) in future phases.
    """

    @abstractmethod
    async def save_file(self, file_bytes: bytes, original_filename: str, mime_type: str) -> Tuple[str, int]:
        """
        Persists raw file content to storage.
        Returns: (storage_path, file_size_bytes)
        """
        pass

    @abstractmethod
    async def read_file(self, storage_path: str) -> bytes:
        """
        Retrieves raw file content from storage.
        """
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """
        Removes file from storage if present.
        """
        pass

    @abstractmethod
    def file_exists(self, storage_path: str) -> bool:
        """
        Checks whether the file is available in storage.
        """
        pass

    @abstractmethod
    def get_storage_key(self, storage_path: str) -> str:
        """
        Returns a safe public identifier for the stored file without exposing absolute filesystem paths.
        """
        pass

class LocalStorageService(BaseStorageService):
    """
    Local filesystem storage provider for development and standard deployments.
    Enforces path traversal protection and secure filename handling.
    """

    def __init__(self, base_dir: Optional[str] = None):
        configured_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_dir = (configured_dir if configured_dir.is_absolute() else BACKEND_DIR / configured_dir).resolve()
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        # Strip all directory separators to prevent directory traversal
        clean_name = Path(filename).name
        # Remove null bytes and non-printable characters
        clean_name = re.sub(r"[\x00-\x1f\x7f]", "", clean_name).strip()
        return clean_name or "uploaded_document"

    def _verify_path_safety(self, target_path: Path):
        resolved = target_path.resolve()
        try:
            if not resolved.is_relative_to(self.base_dir):
                raise ValueError(f"Path traversal detected: {target_path} is outside {self.base_dir}")
        except AttributeError:
            # Fallback for older python or cross-drive edge cases
            if not str(resolved).startswith(str(self.base_dir)):
                raise ValueError(f"Path traversal detected: {target_path} is outside {self.base_dir}")

    def _sync_write(self, destination: Path, file_bytes: bytes):
        with open(destination, "wb") as f:
            f.write(file_bytes)

    def _sync_read(self, file_path: Path) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

    def _sync_delete(self, file_path: Path) -> bool:
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def file_exists(self, storage_path: str) -> bool:
        try:
            p = Path(storage_path).resolve()
            self._verify_path_safety(p)
            return p.is_file()
        except Exception:
            return False

    def get_storage_key(self, storage_path: str) -> str:
        try:
            p = Path(storage_path).resolve()
            return p.name
        except Exception:
            return Path(storage_path).name

    async def save_file(self, file_bytes: bytes, original_filename: str, mime_type: str) -> Tuple[str, int]:
        self._ensure_storage_dir()
        safe_name = self._sanitize_filename(original_filename)
        extension = Path(safe_name).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{extension}"
        destination = (self.base_dir / unique_name).resolve()

        self._verify_path_safety(destination)

        await anyio.to_thread.run_sync(self._sync_write, destination, file_bytes)
        file_size = len(file_bytes)
        logger.info(f"Stored document file '{safe_name}' as '{destination.name}' ({file_size} bytes)")
        return str(destination), file_size

    async def read_file(self, storage_path: str) -> bytes:
        file_path = Path(storage_path).resolve()
        self._verify_path_safety(file_path)

        if not file_path.is_file():
            raise MissingFileError(storage_path)
        return await anyio.to_thread.run_sync(self._sync_read, file_path)

    async def delete_file(self, storage_path: str) -> bool:
        file_path = Path(storage_path).resolve()
        self._verify_path_safety(file_path)
        return await anyio.to_thread.run_sync(self._sync_delete, file_path)

# Default singleton instance
storage_service = LocalStorageService()
