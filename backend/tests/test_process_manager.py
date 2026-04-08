"""Tests for services/process_manager.py."""

from pathlib import Path

import pytest


class TestAppProcess:
    """Tests for the AppProcess dataclass."""

    def test_app_process_creation(self):
        """Test creating an AppProcess instance."""
        from services.process_manager import AppProcess

        app = AppProcess(build_id="test-build", port=9100)
        assert app.build_id == "test-build"
        assert app.port == 9100
        assert app.status == "starting"
        assert app.process is None
        assert app.error is None

    def test_app_process_default_values(self):
        """Test AppProcess default values."""
        import time

        from services.process_manager import AppProcess

        before = time.time()
        app = AppProcess(build_id="test", port=9100)
        after = time.time()

        assert before <= app.started_at <= after
        assert before <= app.last_accessed <= after


class TestProcessManagerInit:
    """Tests for ProcessManager initialization."""

    def test_init(self):
        """Test ProcessManager initialization."""
        from services.process_manager import BASE_PORT, ProcessManager

        pm = ProcessManager()
        assert pm._processes == {}
        assert pm._next_port == BASE_PORT
        assert pm._ports_in_use == set()
        assert pm._cleanup_task is None


class TestPortAllocation:
    """Tests for port allocation."""

    def test_allocate_first_port(self):
        """Test allocating the first port."""
        from services.process_manager import BASE_PORT, ProcessManager

        pm = ProcessManager()
        port = pm._allocate_port()

        assert port == BASE_PORT
        assert port in pm._ports_in_use

    def test_allocate_sequential_ports(self):
        """Test allocating multiple ports sequentially."""
        from services.process_manager import BASE_PORT, ProcessManager

        pm = ProcessManager()
        ports = [pm._allocate_port() for _ in range(5)]

        assert ports == [BASE_PORT, BASE_PORT + 1, BASE_PORT + 2, BASE_PORT + 3, BASE_PORT + 4]

    def test_release_port(self):
        """Test releasing a port."""
        from services.process_manager import ProcessManager

        pm = ProcessManager()
        port = pm._allocate_port()
        assert port in pm._ports_in_use

        pm._release_port(port)
        assert port not in pm._ports_in_use

    def test_reuse_released_port(self):
        """Test that released ports are reused."""
        from services.process_manager import ProcessManager

        pm = ProcessManager()
        port1 = pm._allocate_port()
        port2 = pm._allocate_port()

        pm._release_port(port1)
        port3 = pm._allocate_port()

        assert port3 == port1  # Should reuse the released port


class TestProcessManagerMethods:
    """Tests for ProcessManager methods."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance."""
        from services.process_manager import ProcessManager
        return ProcessManager()

    def test_processes_dict(self, process_manager):
        """Test that processes are tracked in a dict."""
        assert isinstance(process_manager._processes, dict)

    def test_ports_in_use_set(self, process_manager):
        """Test that ports in use is a set."""
        assert isinstance(process_manager._ports_in_use, set)

    def test_get_process_nonexistent(self, process_manager):
        """Test getting a nonexistent process."""
        result = process_manager._processes.get("nonexistent")
        assert result is None


class TestConstants:
    """Tests for module constants."""

    def test_base_port(self):
        """Test BASE_PORT constant."""
        from services.process_manager import BASE_PORT
        assert BASE_PORT == 9100

    def test_max_concurrent(self):
        """Test MAX_CONCURRENT constant."""
        from services.process_manager import MAX_CONCURRENT
        assert MAX_CONCURRENT == 20

    def test_idle_timeout(self):
        """Test IDLE_TIMEOUT_SECONDS constant."""
        from services.process_manager import IDLE_TIMEOUT_SECONDS
        assert IDLE_TIMEOUT_SECONDS == 1800  # 30 minutes

    def test_deployed_dir(self):
        """Test DEPLOYED_DIR constant."""
        from services.process_manager import DEPLOYED_DIR
        assert isinstance(DEPLOYED_DIR, Path)
