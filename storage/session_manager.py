"""Session manager for handling session-specific Beancount ledger files.

This module provides the SessionManager class which manages the lifecycle
of session-specific Beancount ledger files and metadata. It ensures proper
directory structure and file initialization following the TravelCount
architecture patterns.
"""

import json
from datetime import datetime
from pathlib import Path


class SessionManager:
    """Manages session-specific Beancount ledger files and metadata.

    This class handles the creation and management of session directories,
    Beancount ledger files, and session metadata. Each session is isolated
    in its own directory structure under data/[session_id]/.

    Attributes:
        session_id: The unique identifier for the session
    """

    def __init__(self, session_id: str) -> None:
        """Initialize SessionManager with a session ID.

        Args:
            session_id: The unique identifier for the session

        Raises:
            ValueError: If session_id is empty or whitespace-only
        """
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty or whitespace-only")

        self.session_id = session_id
        self._base_data_dir = Path("data")

    def get_ledger_path(self) -> Path:
        """Get the path to the session's Beancount ledger file.

        Returns:
            Path to data/[session_id]/index.bean

        Example:
            >>> manager = SessionManager("session-123")
            >>> path = manager.get_ledger_path()
            >>> print(path)
            data/session-123/index.bean
        """
        return self._base_data_dir / self.session_id / "index.bean"

    def get_metadata_path(self) -> Path:
        """Get the path to the session's metadata file.

        Returns:
            Path to data/[session_id]/meta.json

        Example:
            >>> manager = SessionManager("session-123")
            >>> path = manager.get_metadata_path()
            >>> print(path)
            data/session-123/meta.json
        """
        return self._base_data_dir / self.session_id / "meta.json"

    def ensure_session_directory(self) -> None:
        """Create session directory if it does not exist.

        Creates the directory structure data/[session_id]/ with appropriate
        permissions. This must be called before accessing ledger or metadata files.

        Raises:
            OSError: If directory creation fails due to permission or other OS errors
        """
        session_dir = self._base_data_dir / self.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

    def initialize_ledger(self) -> None:
        """Create an empty Beancount ledger with proper header if not exists.

        Initializes a new Beancount ledger file with a standard header including
        the session ID and creation timestamp. If the ledger file already exists,
        this method does nothing to avoid overwriting existing data.

        The header format follows Beancount conventions:
        - Comment lines starting with semicolon (;)
        - TravelCount metadata
        - Operating currency declaration

        Raises:
            OSError: If file creation or writing fails
        """
        ledger_path = self.get_ledger_path()

        # Only initialize if file doesn't exist
        if ledger_path.exists():
            return

        # Ensure directory exists
        self.ensure_session_directory()

        # Create Beancount header
        current_date = datetime.now().strftime("%Y-%m-%d")
        header = f"""; TravelCount Session Ledger
; Session ID: {self.session_id}
; Created: {current_date}

option "operating_currency" "USD"
"""

        # Write header to file
        ledger_path.write_text(header, encoding="utf-8")

    def save_metadata(self, metadata: dict) -> None:
        """Save session metadata to JSON file.

        Persists session metadata (e.g., participant list, trip details) to
        data/[session_id]/meta.json. The directory must exist before calling
        this method. Call ensure_session_directory() first if needed.

        Args:
            metadata: Dictionary containing session metadata to persist

        Raises:
            OSError: If file writing fails
            TypeError: If metadata is not JSON serializable
        """
        metadata_path = self.get_metadata_path()

        # Ensure directory exists
        self.ensure_session_directory()

        # Write metadata as JSON
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def load_metadata(self) -> dict:
        """Load session metadata from JSON file.

        Retrieves previously saved session metadata from
        data/[session_id]/meta.json. Returns an empty dictionary if
        the metadata file does not exist.

        Returns:
            Dictionary containing session metadata. Returns empty dict
            if metadata file doesn't exist.

        Raises:
            json.JSONDecodeError: If metadata file contains invalid JSON
            OSError: If file reading fails
        """
        metadata_path = self.get_metadata_path()

        # Return empty dict if metadata doesn't exist
        if not metadata_path.exists():
            return {}

        # Load and parse JSON
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
