"""Tests for GitHub CHANGELOG parsing functionality."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from src.feed import (
    parse_changelog_versions,
    fetch_github_changelog_content,
    fetch_github_changelog_items,
    parse_github_changelog_feed,
)


# Sample CHANGELOG content for testing
SAMPLE_CHANGELOG = """# Changelog

All notable changes to this project will be documented in this file.

## 2.1.81

### Bug Fixes
- Fixed API 400 errors when using custom gateways
- Fixed memory leak in long sessions
- Fixed clipboard issues on Windows

## 2.1.80

### Features
- Added new voice mode support
- Improved performance by 74%

## 2.1.79

### Bug Fixes
- Fixed startup crash on macOS
- Fixed permission prompts

## [2.1.78] - 2024-01-15

### Added
- New slash commands

## v2.1.77

Minor updates and fixes.
"""

SAMPLE_CHANGELOG_KEEP_A_CHANGELOG = """# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [2.0.0] - 2024-03-20

### Added
- New feature A
- New feature B

### Changed
- Improved performance

### Fixed
- Bug fix 1

## [1.9.0] - 2024-03-01

### Added
- Initial release features
"""


class TestParseChangelogVersions:
    """Tests for parse_changelog_versions function."""

    def test_extract_versions_with_hash_prefix(self):
        """Test extracting versions with ## prefix format."""
        versions = parse_changelog_versions(SAMPLE_CHANGELOG, max_versions=5)

        assert len(versions) >= 3
        assert versions[0]["version"] == "2.1.81"
        assert "API 400" in versions[0]["changes"] or "Fixed API" in versions[0]["changes"]
        assert versions[1]["version"] == "2.1.80"

    def test_extract_versions_with_brackets(self):
        """Test extracting versions with [version] format."""
        versions = parse_changelog_versions(SAMPLE_CHANGELOG_KEEP_A_CHANGELOG, max_versions=5)

        assert len(versions) >= 2
        assert versions[0]["version"] == "2.0.0"
        assert versions[0]["date"] == "2024-03-20"

    def test_extract_versions_with_v_prefix(self):
        """Test extracting versions with v prefix like v2.1.77."""
        versions = parse_changelog_versions(SAMPLE_CHANGELOG, max_versions=5)

        # v2.1.77 should be extracted
        version_numbers = [v["version"] for v in versions]
        assert any("2.1.77" in v for v in version_numbers)

    def test_max_versions_limit(self):
        """Test that max_versions limits the number of versions returned."""
        versions = parse_changelog_versions(SAMPLE_CHANGELOG, max_versions=2)
        assert len(versions) == 2

    def test_empty_content(self):
        """Test handling of empty content."""
        versions = parse_changelog_versions("")
        assert versions == []

    def test_no_versions_found(self):
        """Test handling of content without version patterns."""
        content = "# Some random document\n\nNo version numbers here."
        versions = parse_changelog_versions(content)
        assert versions == []

    def test_date_extraction(self):
        """Test that dates are extracted from changelog entries."""
        versions = parse_changelog_versions(SAMPLE_CHANGELOG_KEEP_A_CHANGELOG, max_versions=5)

        # First version should have date extracted
        assert versions[0]["date"] == "2024-03-20"


class TestParseGithubChangelogFeed:
    """Tests for parse_github_changelog_feed function."""

    def test_parse_valid_atom_url(self):
        """Test parsing a valid GitHub commits atom URL."""
        url = "https://github.com/anthropics/claude-code/commits/main/CHANGELOG.md.atom"
        result = parse_github_changelog_feed(url)

        assert result is not None
        owner, repo, branch, tracked_file = result
        assert owner == "anthropics"
        assert repo == "claude-code"
        assert branch == "main"
        assert tracked_file == "CHANGELOG.md"

    def test_parse_blob_url_returns_none(self):
        """Test that blob URLs are not parsed by this function."""
        url = "https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md"
        result = parse_github_changelog_feed(url)
        assert result is None

    def test_parse_non_github_url(self):
        """Test that non-GitHub URLs return None."""
        url = "https://example.com/some/feed.atom"
        result = parse_github_changelog_feed(url)
        assert result is None


class TestFetchGithubChangelogContent:
    """Tests for fetch_github_changelog_content function."""

    def test_fetch_content_success(self):
        """Test successful content fetch from GitHub API."""
        import base64

        mock_content = "# Changelog\n\n## 1.0.0\n- Initial release"
        encoded_content = base64.b64encode(mock_content.encode()).decode()

        mock_response = MagicMock()
        mock_response.json.return_value = {"content": encoded_content}
        mock_response.raise_for_status = MagicMock()

        with patch("src.feed.requests.get", return_value=mock_response):
            content, error = fetch_github_changelog_content(
                owner="test-owner",
                repo="test-repo",
                branch="main",
                file_path="CHANGELOG.md",
            )

        assert error is None
        assert content == mock_content

    def test_fetch_content_api_error(self):
        """Test handling of API errors."""
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.RequestException("API Error")

        with patch("src.feed.requests.get", return_value=mock_response):
            content, error = fetch_github_changelog_content(
                owner="test-owner",
                repo="test-repo",
                branch="main",
                file_path="CHANGELOG.md",
            )

        assert content is None
        assert error is not None
        assert "failed" in error.lower()

    def test_fetch_content_with_github_token(self):
        """Test that GITHUB_TOKEN is included in headers."""
        import base64

        mock_content = "# Test"
        encoded_content = base64.b64encode(mock_content.encode()).decode()

        mock_response = MagicMock()
        mock_response.json.return_value = {"content": encoded_content}
        mock_response.raise_for_status = MagicMock()

        with patch("src.feed.requests.get") as mock_get:
            mock_get.return_value = mock_response

            with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token-123"}):
                content, error = fetch_github_changelog_content(
                    owner="test-owner",
                    repo="test-repo",
                    branch="main",
                    file_path="CHANGELOG.md",
                )

            # Verify Authorization header was set
            call_kwargs = mock_get.call_args
            headers = call_kwargs[1]["headers"]
            assert headers["Authorization"] == "token test-token-123"


class TestFetchGithubChangelogItems:
    """Tests for fetch_github_changelog_items function."""

    def test_fetch_items_success(self):
        """Test successful fetching and parsing of changelog items."""
        import base64

        mock_content = """# Changelog

## 2.1.81

- Fixed API errors
- Improved performance

## 2.1.80

- Added new features
"""
        encoded_content = base64.b64encode(mock_content.encode()).decode()

        mock_response = MagicMock()
        mock_response.json.return_value = {"content": encoded_content}
        mock_response.raise_for_status = MagicMock()

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        with patch("src.feed.requests.get", return_value=mock_response):
            items, error = fetch_github_changelog_items(
                owner="test-owner",
                repo="test-repo",
                branch="main",
                file_path="CHANGELOG.md",
                cutoff=cutoff,
                per_source=10,
            )

        assert error is None
        assert len(items) >= 1
        assert items[0].title == "test-owner/test-repo v2.1.81"
        assert "2.1.81" in items[0].dedupe_link

    def test_fetch_items_cutoff_filter(self):
        """Test that items older than cutoff are filtered."""
        import base64

        # Create content with old dates
        mock_content = """# Changelog

## 2.1.81

2024-01-01

- Old release

## 2.1.80

2023-12-01

- Even older release
"""
        encoded_content = base64.b64encode(mock_content.encode()).decode()

        mock_response = MagicMock()
        mock_response.json.return_value = {"content": encoded_content}
        mock_response.raise_for_status = MagicMock()

        # Very recent cutoff - should filter out all items with dates
        cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)

        with patch("src.feed.requests.get", return_value=mock_response):
            items, error = fetch_github_changelog_items(
                owner="test-owner",
                repo="test-repo",
                branch="main",
                file_path="CHANGELOG.md",
                cutoff=cutoff,
                per_source=10,
            )

        # Items without dates should still be included
        # Items with dates older than cutoff should be filtered
        assert error is None

    def test_fetch_items_api_failure(self):
        """Test handling of API failure."""
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.RequestException("API Error")

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        with patch("src.feed.requests.get", return_value=mock_response):
            items, error = fetch_github_changelog_items(
                owner="test-owner",
                repo="test-repo",
                branch="main",
                file_path="CHANGELOG.md",
                cutoff=cutoff,
                per_source=10,
            )

        assert items == []
        assert error is not None
