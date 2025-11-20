"""Tests for SessionManager."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from agents.travelcount.storage.session_manager import SessionManager


class TestSessionManagerConstruction:
    """Test SessionManager initialization and validation."""

    def test_create_session_manager_with_valid_id(self) -> None:
        """Test creating SessionManager with a valid session ID."""
        manager = SessionManager("session-123")
        assert manager.session_id == "session-123"

    def test_create_session_manager_with_alphanumeric_id(self) -> None:
        """Test creating SessionManager with alphanumeric session ID."""
        manager = SessionManager("session123abc")
        assert manager.session_id == "session123abc"

    def test_create_session_manager_with_uuid_id(self) -> None:
        """Test creating SessionManager with UUID-style session ID."""
        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        manager = SessionManager(uuid_id)
        assert manager.session_id == uuid_id

    def test_empty_session_id_raises_error(self) -> None:
        """Test that empty session ID raises ValueError."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            SessionManager("")

    def test_whitespace_only_session_id_raises_error(self) -> None:
        """Test that whitespace-only session ID raises ValueError."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            SessionManager("   ")


class TestSessionManagerPaths:
    """Test SessionManager path generation."""

    def test_get_ledger_path_returns_correct_path(self) -> None:
        """Test that get_ledger_path returns correct path."""
        manager = SessionManager("session-123")
        path = manager.get_ledger_path()
        assert path == Path("data/session-123/index.bean")

    def test_get_ledger_path_with_different_session_ids(self) -> None:
        """Test get_ledger_path with various session IDs."""
        test_ids = ["session-1", "abc-def-ghi", "uuid-12345"]
        for session_id in test_ids:
            manager = SessionManager(session_id)
            path = manager.get_ledger_path()
            assert str(path) == f"data/{session_id}/index.bean"

    def test_get_metadata_path_returns_correct_path(self) -> None:
        """Test that get_metadata_path returns correct path."""
        manager = SessionManager("session-123")
        path = manager.get_metadata_path()
        assert path == Path("data/session-123/meta.json")

    def test_get_metadata_path_with_different_session_ids(self) -> None:
        """Test get_metadata_path with various session IDs."""
        test_ids = ["session-1", "abc-def-ghi", "uuid-12345"]
        for session_id in test_ids:
            manager = SessionManager(session_id)
            path = manager.get_metadata_path()
            assert str(path) == f"data/{session_id}/meta.json"

    def test_ledger_and_metadata_paths_in_same_directory(self) -> None:
        """Test that ledger and metadata paths are in the same directory."""
        manager = SessionManager("session-123")
        ledger_path = manager.get_ledger_path()
        metadata_path = manager.get_metadata_path()
        assert ledger_path.parent == metadata_path.parent


class TestSessionManagerDirectoryCreation:
    """Test SessionManager directory creation."""

    def test_ensure_session_directory_creates_directory(self) -> None:
        """Test that ensure_session_directory creates session directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            session_dir = manager._base_data_dir / "test-session"
            assert not session_dir.exists()

            manager.ensure_session_directory()

            assert session_dir.exists()
            assert session_dir.is_dir()

    def test_ensure_session_directory_is_idempotent(self) -> None:
        """Test that calling ensure_session_directory multiple times is safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            # Call multiple times - should not raise error
            manager.ensure_session_directory()
            manager.ensure_session_directory()
            manager.ensure_session_directory()

            assert (manager._base_data_dir / "test-session").exists()

    def test_ensure_session_directory_creates_parent_directories(self) -> None:
        """Test that ensure_session_directory creates all parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("nested-session-id")
            manager._base_data_dir = Path(tmpdir)

            manager.ensure_session_directory()

            assert (manager._base_data_dir / "nested-session-id").exists()


class TestSessionManagerLedgerInitialization:
    """Test SessionManager ledger file creation."""

    def test_initialize_ledger_creates_file(self) -> None:
        """Test that initialize_ledger creates ledger file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            ledger_path = manager.get_ledger_path()
            assert not ledger_path.exists()

            manager.initialize_ledger()

            assert ledger_path.exists()
            assert ledger_path.is_file()

    def test_initialize_ledger_creates_parent_directory(self) -> None:
        """Test that initialize_ledger creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            session_dir = manager._base_data_dir / "test-session"
            assert not session_dir.exists()

            manager.initialize_ledger()

            assert session_dir.exists()

    def test_initialize_ledger_contains_header(self) -> None:
        """Test that initialized ledger contains proper Beancount header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            manager.initialize_ledger()

            content = manager.get_ledger_path().read_text()
            assert "; TravelCount Session Ledger" in content
            assert "; Session ID: test-session" in content
            assert "; Created:" in content
            assert 'option "operating_currency" "USD"' in content

    def test_initialize_ledger_contains_valid_date(self) -> None:
        """Test that ledger header contains valid creation date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            manager.initialize_ledger()

            content = manager.get_ledger_path().read_text()
            # Check that date is in YYYY-MM-DD format
            lines = content.split("\n")
            date_line = [line for line in lines if "; Created:" in line][0]
            date_str = date_line.split("; Created: ")[1]
            # Should not raise if date is valid
            datetime.strptime(date_str, "%Y-%m-%d")

    def test_initialize_ledger_is_idempotent(self) -> None:
        """Test that initialize_ledger doesn't overwrite existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            manager.initialize_ledger()

            # Modify the file
            ledger_path = manager.get_ledger_path()
            ledger_path.write_text("modified content")

            # Call initialize again
            manager.initialize_ledger()

            # Content should not be overwritten
            final_content = manager.get_ledger_path().read_text()
            assert final_content == "modified content"

    def test_initialize_ledger_header_format(self) -> None:
        """Test that ledger header follows Beancount conventions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            manager.initialize_ledger()

            content = manager.get_ledger_path().read_text()
            lines = content.split("\n")

            # First three lines should be comments
            assert lines[0].startswith(";")
            assert lines[1].startswith(";")
            assert lines[2].startswith(";")

            # Should have option declaration
            assert any('option "operating_currency"' in line for line in lines)


class TestSessionManagerMetadata:
    """Test SessionManager metadata operations."""

    def test_save_metadata_creates_file(self) -> None:
        """Test that save_metadata creates metadata file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            metadata = {"trip": "Paris", "participants": ["Alice", "Bob"]}
            manager.save_metadata(metadata)

            assert manager.get_metadata_path().exists()

    def test_save_metadata_creates_parent_directory(self) -> None:
        """Test that save_metadata creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            metadata = {"trip": "Paris"}
            manager.save_metadata(metadata)

            assert (manager._base_data_dir / "test-session").exists()

    def test_save_metadata_with_simple_dict(self) -> None:
        """Test saving simple metadata dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            metadata = {"trip": "Paris", "currency": "EUR"}
            manager.save_metadata(metadata)

            content = manager.get_metadata_path().read_text()
            saved = json.loads(content)
            assert saved == metadata

    def test_save_metadata_with_complex_dict(self) -> None:
        """Test saving complex nested metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            metadata = {
                "trip": "Paris",
                "participants": [
                    {"name": "Alice", "role": "organizer"},
                    {"name": "Bob", "role": "participant"},
                ],
                "budget": {"total": 1000, "per_person": 500},
            }
            manager.save_metadata(metadata)

            content = manager.get_metadata_path().read_text()
            saved = json.loads(content)
            assert saved == metadata

    def test_save_metadata_overwrites_existing(self) -> None:
        """Test that save_metadata overwrites existing metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            metadata1 = {"version": 1}
            manager.save_metadata(metadata1)

            metadata2 = {"version": 2, "name": "Updated"}
            manager.save_metadata(metadata2)

            saved = json.loads(manager.get_metadata_path().read_text())
            assert saved == metadata2

    def test_save_metadata_with_unicode_characters(self) -> None:
        """Test saving metadata with unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            metadata = {
                "location": "巴黎",  # Paris in Chinese
                "participants": ["张三", "李四"],  # Chinese names
            }
            manager.save_metadata(metadata)

            saved = json.loads(manager.get_metadata_path().read_text())
            assert saved == metadata

    def test_load_metadata_returns_empty_dict_if_not_exists(self) -> None:
        """Test that load_metadata returns empty dict if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            result = manager.load_metadata()
            assert result == {}
            assert isinstance(result, dict)

    def test_load_metadata_returns_saved_metadata(self) -> None:
        """Test that load_metadata returns previously saved metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            original_metadata = {"trip": "Paris", "currency": "EUR"}
            manager.save_metadata(original_metadata)

            loaded_metadata = manager.load_metadata()
            assert loaded_metadata == original_metadata

    def test_load_metadata_with_complex_structure(self) -> None:
        """Test loading complex nested metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            original_metadata = {
                "trip": "Paris",
                "participants": ["Alice", "Bob", "Charlie"],
                "expenses": {
                    "accommodation": 150.50,
                    "food": 75.25,
                    "transport": 45.00,
                },
                "dates": {"start": "2024-06-01", "end": "2024-06-10"},
            }
            manager.save_metadata(original_metadata)

            loaded_metadata = manager.load_metadata()
            assert loaded_metadata == original_metadata

    def test_load_metadata_with_unicode_characters(self) -> None:
        """Test loading metadata with unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)

            original_metadata = {
                "location": "東京",  # Tokyo in Japanese
                "participants": ["太郎", "花子"],  # Japanese names
            }
            manager.save_metadata(original_metadata)

            loaded_metadata = manager.load_metadata()
            assert loaded_metadata == original_metadata


class TestSessionManagerIntegration:
    """Integration tests for SessionManager operations."""

    def test_full_session_workflow(self) -> None:
        """Test complete session creation and metadata workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("trip-paris-2024")
            manager._base_data_dir = Path(tmpdir)

            # Initialize session
            manager.ensure_session_directory()
            manager.initialize_ledger()

            # Save metadata
            metadata = {
                "trip": "Paris",
                "start_date": "2024-06-01",
                "participants": ["Alice", "Bob"],
            }
            manager.save_metadata(metadata)

            # Verify all files exist
            assert manager.get_ledger_path().exists()
            assert manager.get_metadata_path().exists()

            # Verify ledger content
            ledger_content = manager.get_ledger_path().read_text()
            assert "TravelCount Session Ledger" in ledger_content

            # Verify metadata content
            loaded = manager.load_metadata()
            assert loaded == metadata

    def test_multiple_sessions_isolation(self) -> None:
        """Test that different sessions maintain isolated data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager1 = SessionManager("session-1")
            manager1._base_data_dir = Path(tmpdir)

            manager2 = SessionManager("session-2")
            manager2._base_data_dir = Path(tmpdir)

            # Save different metadata for each session
            meta1 = {"trip": "Paris"}
            meta2 = {"trip": "Tokyo"}

            manager1.save_metadata(meta1)
            manager2.save_metadata(meta2)

            # Verify isolation
            assert manager1.load_metadata() == meta1
            assert manager2.load_metadata() == meta2

    def test_session_state_persistence(self) -> None:
        """Test that session state persists across manager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and save with first manager instance
            manager1 = SessionManager("persistent-session")
            manager1._base_data_dir = Path(tmpdir)

            metadata1 = {
                "trip": "Barcelona",
                "participants": ["Alice", "Bob", "Charlie"],
            }
            manager1.save_metadata(metadata1)
            manager1.initialize_ledger()

            # Load with different manager instance
            manager2 = SessionManager("persistent-session")
            manager2._base_data_dir = Path(tmpdir)

            # Verify data is accessible
            assert manager2.get_ledger_path().exists()
            assert manager2.load_metadata() == metadata1
