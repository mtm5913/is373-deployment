import unittest
from html.parser import HTMLParser
from pathlib import Path

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.release_found = False

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "p" and dict(attrs).get("id") == "release":
            self.release_found = True

class WebsiteTest(unittest.TestCase):
    def test_homepage(self):
        html = Path("index.html").read_text()
        page = PageParser()
        page.feed(html)
        for tag in ("html", "head", "title", "body", "h1"):
            self.assertIn(tag, page.tags, f"Missing {tag}")
        self.assertTrue(page.release_found, "Missing release paragraph")
        self.assertIn("Release 1", html)
        self.assertIn("</html>", html.lower())

if __name__ == "__main__":
    unittest.main()
