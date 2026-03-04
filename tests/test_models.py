"""Tests for data models."""

from src.models import NewsItem


def test_newsitem_from_dict_basic():
    """Test NewsItem.from_dict with basic fields."""
    data = {
        "title": "Test Title",
        "link": "https://example.com",
        "summary": "Test summary",
        "published": "2024-01-01T00:00:00Z",
    }
    item = NewsItem.from_dict(data)
    assert item.title == "Test Title"
    assert item.link == "https://example.com"
    assert item.summary == "Test summary"
    assert item.published == "2024-01-01T00:00:00Z"
    assert item.key_points == []


def test_newsitem_from_dict_with_key_points_list():
    """Test NewsItem.from_dict with key_points as list."""
    data = {
        "title": "Test",
        "link": "https://example.com",
        "key_points": ["Point 1", "Point 2", "Point 3"],
    }
    item = NewsItem.from_dict(data)
    assert item.key_points == ["Point 1", "Point 2", "Point 3"]


def test_newsitem_from_dict_with_key_points_string():
    """Test NewsItem.from_dict with key_points as comma-separated string (old format)."""
    data = {
        "title": "Test",
        "link": "https://example.com",
        "key_points": "Point 1, Point 2, Point 3",
    }
    item = NewsItem.from_dict(data)
    assert item.key_points == ["Point 1", "Point 2", "Point 3"]


def test_newsitem_to_dict():
    """Test NewsItem.to_dict conversion."""
    item = NewsItem(
        title="Test Title",
        link="https://example.com",
        summary="Test summary",
        key_points=["Point 1", "Point 2"],
    )
    data = item.to_dict()
    assert data["title"] == "Test Title"
    assert data["link"] == "https://example.com"
    assert data["summary"] == "Test summary"
    assert data["key_points"] == ["Point 1", "Point 2"]


def test_newsitem_roundtrip():
    """Test NewsItem dict conversion roundtrip."""
    original = {
        "title": "Test",
        "link": "https://example.com",
        "summary": "Summary",
        "published": "2024-01-01",
        "dedupe_link": "https://example.com",
        "score": "8",
        "brief": "Brief",
        "details": "Details",
        "impact": "Impact",
        "key_points": ["P1", "P2"],
    }
    item = NewsItem.from_dict(original)
    result = item.to_dict()
    assert result == original


def test_newsitem_from_dict_list():
    """Test NewsItem.from_dict_list batch conversion."""
    data_list = [
        {"title": "Item 1", "link": "https://example.com/1"},
        {"title": "Item 2", "link": "https://example.com/2"},
    ]
    items = NewsItem.from_dict_list(data_list)
    assert len(items) == 2
    assert items[0].title == "Item 1"
    assert items[1].title == "Item 2"


def test_newsitem_to_dict_list():
    """Test NewsItem.to_dict_list batch conversion."""
    items = [
        NewsItem(title="Item 1", link="https://example.com/1"),
        NewsItem(title="Item 2", link="https://example.com/2"),
    ]
    data_list = NewsItem.to_dict_list(items)
    assert len(data_list) == 2
    assert data_list[0]["title"] == "Item 1"
    assert data_list[1]["title"] == "Item 2"


def test_newsitem_handles_missing_fields():
    """Test NewsItem.from_dict handles missing fields gracefully."""
    data = {"title": "Test"}
    item = NewsItem.from_dict(data)
    assert item.title == "Test"
    assert item.link == ""
    assert item.summary == ""
    assert item.key_points == []
