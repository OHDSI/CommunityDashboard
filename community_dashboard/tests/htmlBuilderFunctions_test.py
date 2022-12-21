# This function are used in pubmed_routes and youtube_routes handlers.
import pytest
from community_dashboard import app
from community_dashboard.handlers.htmlBuilderFunctions import addTagWrapper

def test_addTagWrapper():
    # Test that the function wraps the string in the specified tag
    assert addTagWrapper("Hello, world!", "p") == "<p>Hello, world!</p>"
    
    # Test function adds custom opening tag
    assert addTagWrapper("Hello, world!", "p", " class='testtest'") == "<p class='testtest'>Hello, world!</p>"
    
    # Test function with different tags
    assert addTagWrapper("Hello, world!", "div") == "<div>Hello, world!</div>"
    assert addTagWrapper("Hello, world!", "h1") == "<h1>Hello, world!</h1>"

    # Test with empty strings
    assert addTagWrapper("", "p") == "<p></p>"
