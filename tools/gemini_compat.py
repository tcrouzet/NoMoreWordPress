import re
import sys

from md2gemini import md2gemini
import mistune
from mistune import InlineParser
from mistune.scanner import Matcher


class InlineMatcher(Matcher):
    def __init__(self, lexicon):
        super().__init__([(re.compile(pattern), action) for pattern, action in lexicon])

    def search_pos(self, string, pos):
        matches = [rule.search(string, pos + 1) for rule, _ in self.lexicon]
        return min((match.start() for match in matches if match), default=None)


class GeminiInlineParser(InlineParser):
    scanner_cls = InlineMatcher
    # parse_ref_link expects a second group even for shortcut references.
    REF_LINK2 = InlineParser.REF_LINK2 + r'()'


# Python 3.15 rejects capturing groups used by Mistune 2's re.Scanner.
if sys.version_info >= (3, 15):
    mistune.InlineParser = GeminiInlineParser
