import difflib
import re

import bleach

from base import constants
from style_guide import models


def get_styleguide_title(language: str):
    language_name = constants.LANGUAGES_DICT[language]
    return f'Style Guide for {language_name}'


def get_styleguide_content_from_template():
    template, _ = models.StyleGuide.objects.get_or_create(
        language='default',
        defaults={
            'title': 'Template for style guides',
            'content': 'Nobody started this Style Guide yet. Be the first!',
        },
    )
    return template.content


def normalize_string(text: str) -> str:
    if text and not text.endswith('\n'):
        return f'{text}\n'
    return text


def calculate_diff(source_text: str, changed_text: str):
    source_text = normalize_string(source_text)
    changed_text = normalize_string(changed_text)
    source_lines = source_text.splitlines(keepends=True)
    changed_lines = changed_text.splitlines(keepends=True)
    unified_diff = list(difflib.unified_diff(source_lines, changed_lines, n=0))
    return ''.join(unified_diff[2:])


class DiffConflictException(Exception):
    pass


class DiffFormatException(Exception):
    pass


class DiffParser:
    def __init__(self, diff_text):
        diff_lines = diff_text.splitlines(keepends=True)
        pattern = re.compile(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@')
        self.instructions = list()
        ll, ls, rl, rs, s, changes = None, None, None, None, None, []
        for line in diff_lines:
            if line.startswith('@@'):
                if ll is not None and rl is not None and changes:
                    self.instructions.append((ll, rl, s, changes))
                ll, ls, rl, rs = pattern.match(line).groups()
                ll = int(ll) - 1
                rl = int(rl) - 1
                rl = 0 if rl < 0 else rl
                s = int(rs or 1) - int(ls or 1)
                changes = []
            elif line.startswith('-') or line.startswith('+'):
                changes.append((line[0], line[1:]))
            else:
                raise DiffFormatException()
        if ll is not None and rl is not None and changes:
            self.instructions.append((ll, rl, s, changes))

    def has_conflict(self, source_text: str) -> bool:
        source_text = normalize_string(source_text)
        source_lines = source_text.splitlines(keepends=True)
        for ll, _, _, changes in self.instructions:
            for op, text in changes:
                if op == '-' and text != source_lines[ll]:
                    return True
                ll += 1
        return False

    def apply(self, source_text: str) -> str:
        source_text = normalize_string(source_text)
        source_lines = source_text.splitlines(keepends=True)
        result_lines = source_lines.copy()
        ds = 0
        for ll, rl, s, changes in self.instructions:
            for op, text in changes:
                if op == '-':
                    if source_lines[ll] != text:
                        raise DiffConflictException()
                    del result_lines[rl + ds]
                    ll += 1
                elif op == '+':
                    result_lines.insert(rl, text)
                    rl += 1
            ds += s
        return ''.join(result_lines)


def html_validation_check(value):
    if not value:
        return False

    clean = bleach.clean(value, tags=constants.ALLOWED_HTML_TAGS, strip=True)
    return clean == value


def process_diff(content, modified):
    if modified is None:
        return ''

    modified = normalize_string(modified)
    diff = calculate_diff(content, modified)

    return diff
