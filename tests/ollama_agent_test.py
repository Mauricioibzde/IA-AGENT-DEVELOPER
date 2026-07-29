import json
import urllib.request


def test_ollama_api():
    req = urllib.request.Request('http://127.0.0.1:11434/api/tags')
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.load(r)
    assert 'models' in data

if __name__ == '__main__':
    test_ollama_api()
