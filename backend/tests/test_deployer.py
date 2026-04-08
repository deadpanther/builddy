"""Tests for the services/deployer.py module."""

import zipfile


class TestEnsureDeployedDir:
    def test_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Test that ensure_deployed_dir creates the directory."""
        test_dir = tmp_path / "test_deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        # Re-import to get the patched value
        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        deployer.ensure_deployed_dir()
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_no_error_if_directory_exists(self, tmp_path, monkeypatch):
        """Test that calling ensure_deployed_dir on existing dir is safe."""
        test_dir = tmp_path / "existing_deployed"
        test_dir.mkdir()
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        # Should not raise
        deployer.ensure_deployed_dir()
        assert test_dir.exists()


class TestDeployHtml:
    def test_deploy_html_creates_file(self, tmp_path, monkeypatch):
        """Test that deploy_html creates the index.html file."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "test-build-123"
        html_code = "<html><body><h1>Hello World</h1></body></html>"

        url = deployer.deploy_html(build_id, html_code)

        assert url == f"/apps/{build_id}/"
        expected_file = test_dir / build_id / "index.html"
        assert expected_file.exists()
        assert expected_file.read_text(encoding="utf-8") == html_code

    def test_deploy_html_overwrites_existing(self, tmp_path, monkeypatch):
        """Test that deploy_html overwrites existing content."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "test-build-456"
        deployer.deploy_html(build_id, "<old>Old content</old>")

        new_html = "<new>New content</new>"
        url = deployer.deploy_html(build_id, new_html)

        expected_file = test_dir / build_id / "index.html"
        assert expected_file.read_text(encoding="utf-8") == new_html

    def test_deploy_html_handles_unicode(self, tmp_path, monkeypatch):
        """Test that deploy_html handles unicode content."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "unicode-test"
        html_code = "<html><body>Emoji: 😀 Chinese: 中文 Arabic: مرحبا</body></html>"

        url = deployer.deploy_html(build_id, html_code)
        expected_file = test_dir / build_id / "index.html"
        assert expected_file.read_text(encoding="utf-8") == html_code


class TestGetDeployedHtml:
    def test_get_deployed_html_returns_content(self, tmp_path, monkeypatch):
        """Test that get_deployed_html returns file content."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "read-test"
        html_code = "<html>Test</html>"
        deployer.deploy_html(build_id, html_code)

        result = deployer.get_deployed_html(build_id)
        assert result == html_code

    def test_get_deployed_html_returns_none_if_missing(self, tmp_path, monkeypatch):
        """Test that get_deployed_html returns None for non-existent build."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        result = deployer.get_deployed_html("nonexistent-build")
        assert result is None


class TestDeployProject:
    def test_deploy_project_creates_multiple_files(self, tmp_path, monkeypatch):
        """Test that deploy_project creates all project files."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "multi-file-project"
        files = {
            "index.html": "<html><body>Main</body></html>",
            "styles/main.css": "body { color: red; }",
            "scripts/app.js": "console.log('hello');",
            "data/config.json": '{"setting": true}',
        }

        url = deployer.deploy_project(build_id, files)

        assert url == f"/apps/{build_id}/"

        for filepath, content in files.items():
            expected_file = test_dir / build_id / filepath
            assert expected_file.exists(), f"Missing {filepath}"
            assert expected_file.read_text(encoding="utf-8") == content

    def test_deploy_project_with_frontend_dir(self, tmp_path, monkeypatch):
        """Test that frontend files are copied to root with path rewrites."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "frontend-app"
        files = {
            "frontend/index.html": '<a href="/page2">Link</a>',
            "frontend/page2.html": "<html>Page 2</html>",
            "frontend/js/app.js": "fetch('/api/data')",
            "backend/server.js": "const app = express();",
        }

        url = deployer.deploy_project(build_id, files)

        # Check frontend files are copied to root
        root_index = test_dir / build_id / "index.html"
        assert root_index.exists()
        # Should have rewritten /page2 to /apps/{build_id}/page2
        content = root_index.read_text(encoding="utf-8")
        assert f"/apps/{build_id}/page2" in content or 'href="/page2"' not in content

    def test_deploy_project_creates_nested_directories(self, tmp_path, monkeypatch):
        """Test that deploy_project creates nested directory structures."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "nested-dirs"
        files = {
            "a/b/c/d/file.txt": "deeply nested",
        }

        deployer.deploy_project(build_id, files)

        expected_file = test_dir / build_id / "a" / "b" / "c" / "d" / "file.txt"
        assert expected_file.exists()
        assert expected_file.read_text(encoding="utf-8") == "deeply nested"

    def test_deploy_project_overwrites_existing(self, tmp_path, monkeypatch):
        """Test that deploy_project overwrites existing files."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "overwrite-test"
        deployer.deploy_project(build_id, {"index.html": "old"})
        deployer.deploy_project(build_id, {"index.html": "new"})

        expected_file = test_dir / build_id / "index.html"
        assert expected_file.read_text(encoding="utf-8") == "new"


class TestCreateProjectZip:
    def test_create_project_zip_creates_archive(self, tmp_path, monkeypatch):
        """Test that create_project_zip creates a valid zip archive."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "zip-test-abc12345"
        files = {
            "index.html": "<html>Test</html>",
            "app.js": "console.log('test');",
        }

        url = deployer.create_project_zip(build_id, files)

        assert url == f"/apps/{build_id}/project.zip"

        zip_path = test_dir / build_id / "project.zip"
        assert zip_path.exists()

        # Verify zip contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # Should use first 8 chars of build_id as prefix ("zip-test")
            assert any("zip-test/" in n for n in names)
            assert any("index.html" in n for n in names)
            assert any("app.js" in n for n in names)

    def test_create_project_zip_preserves_directory_structure(self, tmp_path, monkeypatch):
        """Test that zip preserves nested directory structure."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "nested-zip-test"
        files = {
            "src/components/Button.tsx": "export const Button = () => {}",
            "src/utils/helpers.ts": "export const help = () => {}",
        }

        deployer.create_project_zip(build_id, files)

        zip_path = test_dir / build_id / "project.zip"
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert any("src/components/Button.tsx" in n for n in names)
            assert any("src/utils/helpers.ts" in n for n in names)


class TestGetProjectFiles:
    def test_get_project_files_returns_all_files(self, tmp_path, monkeypatch):
        """Test that get_project_files returns all deployed files."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "get-files-test"
        files = {
            "index.html": "<html>Main</html>",
            "styles.css": "body {}",
        }
        deployer.deploy_project(build_id, files)

        result = deployer.get_project_files(build_id)

        assert result is not None
        assert "index.html" in result
        assert "styles.css" in result
        assert result["index.html"] == "<html>Main</html>"

    def test_get_project_files_excludes_zip(self, tmp_path, monkeypatch):
        """Test that get_project_files excludes project.zip."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "exclude-zip-test"
        deployer.deploy_project(build_id, {"index.html": "content"})
        deployer.create_project_zip(build_id, {"index.html": "content"})

        result = deployer.get_project_files(build_id)

        assert result is not None
        assert "project.zip" not in result

    def test_get_project_files_returns_none_if_missing(self, tmp_path, monkeypatch):
        """Test that get_project_files returns None for non-existent build."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        result = deployer.get_project_files("nonexistent-build")
        assert result is None

    def test_get_project_files_excludes_pycache(self, tmp_path, monkeypatch):
        """Test that get_project_files excludes __pycache__ directories."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "pycache-test"
        # Create files including __pycache__
        app_dir = test_dir / build_id
        app_dir.mkdir(parents=True)

        (app_dir / "main.py").write_text("print('hi')")
        pycache_dir = app_dir / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "main.pyc").write_bytes(b"binary content")

        result = deployer.get_project_files(build_id)

        assert result is not None
        assert "main.py" in result
        assert not any("__pycache__" in k for k in result.keys())


class TestDeployProjectApiRewrites:
    def test_deploy_project_rewrites_api_paths_single_quotes(self, tmp_path, monkeypatch):
        """Test that /api/ paths are rewritten in JS files with single quotes."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "api-rewrite-1"
        files = {
            "frontend/app.js": "fetch('/api/users').then(r => r.json())",
        }

        deployer.deploy_project(build_id, files)

        # Check the rewritten file in root
        root_js = test_dir / build_id / "app.js"
        content = root_js.read_text(encoding="utf-8")
        assert f"/apps/{build_id}/api/users" in content

    def test_deploy_project_rewrites_api_paths_double_quotes(self, tmp_path, monkeypatch):
        """Test that /api/ paths are rewritten in JS files with double quotes."""
        test_dir = tmp_path / "deployed"
        monkeypatch.setattr("services.deployer.DEPLOYED_DIR", test_dir)

        from services import deployer
        deployer.DEPLOYED_DIR = test_dir

        build_id = "api-rewrite-2"
        files = {
            "frontend/app.js": 'fetch("/api/data")',
        }

        deployer.deploy_project(build_id, files)

        root_js = test_dir / build_id / "app.js"
        content = root_js.read_text(encoding="utf-8")
        assert f'/apps/{build_id}/api/data' in content
