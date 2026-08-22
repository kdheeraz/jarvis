"""Text preparation for speech synthesis.

The agent is shared between text chat (where markdown is rendered) and voice
(where it is read out literally), so replies arrive with `**bold**`, bullets and
headings in them. Piper pronounces those markers — "asterisk asterisk" — so the
markup has to come off before synthesis rather than by asking the LLM not to use
it, which is unreliable and would degrade the text UI.
"""

import re

# Fenced code: drop the fence line (and its language tag) but keep the body,
# so a code-heavy reply degrades to reading the code rather than to silence.
_CODE_FENCE_LINE = re.compile(r"^\s*```[^\n]*$", re.M)
_INLINE_CODE = re.compile(r"`([^`]*)`")

_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.M)
_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", re.M)
_HORIZONTAL_RULE = re.compile(r"^\s*(?:[-*_]\s*){3,}$", re.M)
_BULLET = re.compile(r"^\s*[-*+]\s+", re.M)

_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]*\|[\s:|-]*\|?\s*$", re.M)
_TABLE_PIPE = re.compile(r"[ \t]*\|[ \t]*")

_STRIKETHROUGH = re.compile(r"~~([^~]*)~~")
# Any run of asterisks is emphasis markup — a lone `*` is never spoken text.
_ASTERISKS = re.compile(r"\*+")
# Underscores only when they wrap a word, so snake_case identifiers survive.
_UNDERSCORE_EMPHASIS = re.compile(r"(?<![A-Za-z0-9_])_{1,3}([^_\n]+?)_{1,3}(?![A-Za-z0-9_])")

_BLANK_LINES = re.compile(r"\n{2,}")
_SPACES = re.compile(r"[ \t]{2,}")


def strip_markdown_for_speech(text: str) -> str:
    """Return `text` with markdown markup removed, ready to hand to a TTS engine.

    Structure is flattened to plain sentences: markers are dropped, link labels
    and table cells are kept as words. The result is only meant to be spoken —
    never store it as the assistant's message, which should stay markdown.
    """
    if not text:
        return ""

    out = _CODE_FENCE_LINE.sub("", text)
    out = _INLINE_CODE.sub(r"\1", out)

    # Links before asterisks: the label may itself be emphasised.
    out = _IMAGE.sub(r"\1", out)
    out = _LINK.sub(r"\1", out)

    # Horizontal rules before bullets, so a `* * *` rule isn't read as a bullet.
    out = _HORIZONTAL_RULE.sub("", out)
    out = _HEADING.sub("", out)
    out = _BLOCKQUOTE.sub("", out)
    out = _BULLET.sub("", out)

    # Table separator rows carry no words; remaining pipes become pauses.
    out = _TABLE_SEPARATOR.sub("", out)
    out = _TABLE_PIPE.sub(", ", out)

    out = _STRIKETHROUGH.sub(r"\1", out)
    out = _UNDERSCORE_EMPHASIS.sub(r"\1", out)
    out = _ASTERISKS.sub("", out)

    out = _BLANK_LINES.sub("\n", out)
    out = _SPACES.sub(" ", out)
    # Leading ", " can survive a table row that started with a pipe.
    return "\n".join(line.strip().lstrip(",").strip() for line in out.splitlines()).strip()
