"""Extended tests for services/process_manager.py."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path


class TestProcessManagerGetMethods:
    """Tests for ProcessManager get methods."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance."""
        from services.process_manager import ProcessManager
        return ProcessManager()

    def test_get_app_nonexistent(self, process_manager):
        """Test get_app for nonexistent build."""
        result = process_manager.get_app("nonexistent")
        assert result is None

    def test_get_port_nonexistent(self, process_manager):
        """Test get_port for nonexistent build."""
        result = process_manager.get_port("nonexistent")
        assert result is None

    def test_get_port_for_running_app(self, process_manager):
        """Test get_port for a running app."""
        from services.process_manager import AppProcess
        
        # Add a mock running app
        app = AppProcess(build_id="test-build", port=9100, status="running")
        process_manager._processes["test-build"] = app
        
        port = process_manager.get_port("test-build")
        assert port == 9100

    def test_get_app_updates_last_accessed(self, process_manager):
        """Test that get_app updates last_accessed."""
        import time
        from services.process_manager import AppProcess
        
        app = AppProcess(build_id="test-build", port=9100, status="running")
        old_time = app.last_accessed
        process_manager._processes["test-build"] = app
        
        time.sleep(0.01)  # Small delay
        result = process_manager.get_app("test-build")
        
        assert result.last_accessed > old_time


class TestProcessManagerStopApp:
    """Tests for stop_app method."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance."""
        from services.process_manager import ProcessManager
        return ProcessManager()

    @pytest.mark.asyncio
    async def test_stop_app_nonexistent(self, process_manager):
        """Test stopping nonexistent app."""
        # Should not raise
        await process_manager.stop_app("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_app_releases_port(self, process_manager):
        """Test that stop_app releases the port."""
        from services.process_manager import AppProcess
        
        app = AppProcess(build_id="test-build", port=9100, status="running")
        process_manager._processes["test-build"] = app
        
        await process_manager.stop_app("test-build")
        
        assert "test-build" not in process_manager._processes
        assert 9100 not in process_manager._ports_in_use


class TestProcessManagerEnsureRunning:
    """Tests for ensure_running method."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance."""
        from services.process_manager import ProcessManager
        pm = ProcessManager()
        return pm

    @pytest.mark.asyncio
    async def test_ensure_running_returns_port_for_running_app(self, process_manager):
        """Test ensure_running returns port for already running app."""
        from services.process_manager import AppProcess
        
        app = AppProcess(build_id="test-build", port=9100, status="running")
        process_manager._processes["test-build"] = app
        
        port = await process_manager.ensure_running("test-build")
        assert port == 9100

    @pytest.mark.asyncio
    async def test_ensure_running_raises_for_error(self, process_manager):
        """Test ensure_running raises RuntimeError for failed start."""
        # Mock start_app to return error status
        with patch.object(process_manager, 'start_app', new=AsyncMock()) as mock_start:
            from services.process_manager import AppProcess
            mock_start.return_value = AppProcess(
                build_id="test-build",
                port=0,
                status="error",
                error="Build directory does not exist"
            )
            
            with pytest.raises(RuntimeError) as exc_info:
                await process_manager.ensure_running("test-build")
            
            assert "Cannot start app" in str(exc_info.value)


class TestProcessManagerListRunning:
    """Tests for list_running method."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance."""
        from services.process_manager import ProcessManager
        return ProcessManager()

    def test_list_running_empty(self, process_manager):
        """Test list_running with no apps."""
        result = process_manager.list_running()
        assert result == []

    def test_list_running_with_apps(self, process_manager):
        """Test list_running with apps."""
        from services.process_manager import AppProcess
        
        app1 = AppProcess(build_id="app1", port=9100, status="running")
        app2 = AppProcess(build_id="app2", port=9101, status="running")
        app3 = AppProcess(build_id="app3", port=9102, status="stopped")
        
        process_manager._processes["app1"] = app1
        process_manager._processes["app2"] = app2
        process_manager._processes["app3"] = app3
        
        result = process_manager.list_running()
        
        # Should return all apps with their info
        assert len(result) == 3
        build_ids = [r["build_id"] for r in result]
        assert "app1" in build_ids
        assert "app2" in build_ids
        assert "app3" in build_ids


class TestProcessManagerStopAll:
    """Tests for stop_all method."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance."""
        from services.process_manager import ProcessManager
        return ProcessManager()

    @pytest.mark.asyncio
    async def test_stop_all_empty(self, process_manager):
        """Test stop_all with no apps."""
        # Should not raise
        await process_manager.stop_all()

    @pytest.mark.asyncio
    async def test_stop_all_with_apps(self, process_manager):
        """Test stop_all stops all running apps."""
        from services.process_manager import AppProcess
        
        app1 = AppProcess(build_id="app1", port=9100, status="running")
        app2 = AppProcess(build_id="app2", port=9101, status="running")
        
        process_manager._processes["app1"] = app1
        process_manager._processes["app2"] = app2
        
        await process_manager.stop_all()
        
        assert len(process_manager._processes) == 0
        assert len(process_manager._ports_in_use) == 0
