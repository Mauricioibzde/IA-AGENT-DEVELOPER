import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama_agent import parse_tool_call, execute_tool


def test_parse_tool_call_with_json_payload():
    payload = '{"tool":"write_file","args":{"path":"notes.txt","content":"hello"}}'
    tool_name, args = parse_tool_call(payload)
    assert tool_name == 'write_file'
    assert args['path'] == 'notes.txt'
    assert args['content'] == 'hello'


def test_execute_tool_writes_file(tmp_path):
    target = tmp_path / 'demo.txt'
    result = execute_tool('write_file', {'path': str(target), 'content': 'ok'}, workspace=str(tmp_path))
    assert result['ok'] is True
    assert target.read_text(encoding='utf-8') == 'ok'
