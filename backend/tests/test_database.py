"""Tests for database.py."""



class TestDatabaseEngine:
    """Tests for database engine setup."""

    def test_engine_exists(self):
        """Test that database engine is created."""
        from database import engine
        assert engine is not None

    def test_engine_has_database_url(self):
        """Test that engine is configured."""
        from database import engine
        assert engine.url is not None


class TestCreateDbAndTables:
    """Tests for create_db_and_tables function."""

    def test_function_exists(self):
        """Test that function exists."""
        from database import create_db_and_tables
        assert callable(create_db_and_tables)

    def test_creates_tables(self):
        """Test that tables are created."""
        from database import create_db_and_tables
        # Should run without error
        create_db_and_tables()


class TestGetSession:
    """Tests for get_session generator."""

    def test_function_exists(self):
        """Test that function exists."""
        from database import get_session
        assert callable(get_session)

    def test_yields_session(self):
        """Test that generator yields a session."""
        from database import get_session

        gen = get_session()
        session = next(gen)
        assert session is not None

        # Cleanup
        try:
            next(gen)
        except StopIteration:
            pass


class TestGetNewSession:
    """Tests for get_new_session function."""

    def test_function_exists(self):
        """Test that function exists."""
        from database import get_new_session
        assert callable(get_new_session)

    def test_returns_session(self):
        """Test that function returns a session."""
        from database import Session, get_new_session

        session = get_new_session()
        assert session is not None
        assert isinstance(session, Session)
        session.close()


class TestMigrationFunction:
    """Tests for _migrate_new_columns function."""

    def test_function_exists(self):
        """Test that migration function exists."""
        from database import _migrate_new_columns
        assert callable(_migrate_new_columns)

    def test_migration_runs(self):
        """Test that migration runs without error."""
        from database import _migrate_new_columns
        # Should run without error even if columns exist
        _migrate_new_columns()
