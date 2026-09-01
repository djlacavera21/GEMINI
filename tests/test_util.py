from gemini_cloner.git_clone import normalize_repo_url, repo_slug
from gemini_cloner.util import is_http_url, same_host, slugify


def test_slugify_strips_noise():
    assert slugify("Hello, World!!") == "hello-world"


def test_normalize_github_shorthand():
    assert normalize_repo_url("djlacavera21/GEMINI") == "https://github.com/djlacavera21/GEMINI.git"


def test_repo_slug():
    assert repo_slug("https://github.com/djlacavera21/GEMINI") == "djlacavera21-gemini"


def test_http_url_guard():
    assert is_http_url("https://example.com/x")
    assert not is_http_url("file:///etc/passwd")
    assert not is_http_url("javascript:alert(1)")


def test_same_host():
    assert same_host("https://a.example/x", "https://a.example/y")
    assert not same_host("https://a.example/x", "https://b.example/x")
