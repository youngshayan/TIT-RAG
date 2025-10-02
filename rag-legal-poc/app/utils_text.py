import re
import unicodedata

_arabic_to_persian = str.maketrans("كي", "کی")

def normalize_persian(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    text = text.translate(_arabic_to_persian)

    text = "".join(
        ch for ch in text
        if (ch in ("\n", "\r", "\t") or ch == "\u200C" or ord(ch) >= 32)
    )

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = re.sub(r"\s+([,،:؛\.\?!)])", r"\1", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


ARABIC_RANGES = (
    "\u0600-\u06FF"
    "\u0750-\u077F"
    "\u08A0-\u08FF"
    "\uFB50-\uFDFF"
    "\uFE70-\uFEFF"
)
LETTER_WITH_SPACES_PATTERN = re.compile(
    rf"(?:(?<=\s)|^)(?:[{ARABIC_RANGES}]\s+)(?:[{ARABIC_RANGES}]\s+)*(?:[{ARABIC_RANGES}])(?=(?:\s|$))",
    flags=re.UNICODE
)
SINGLE_ARABIC_CHAR = re.compile(rf"^[{ARABIC_RANGES}]$")

def repair_spaced_letters(text: str) -> str:
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        l = re.sub(r"[ \t]+", " ", line).strip()
        tokens = l.split(" ")
        out_tokens, buffer = [], []
        for tok in tokens:
            if SINGLE_ARABIC_CHAR.match(tok):
                buffer.append(tok)
            else:
                if len(buffer) >= 2:
                    out_tokens.append("".join(buffer))
                elif len(buffer) == 1:
                    out_tokens.append(buffer[0])
                buffer = []
                out_tokens.append(tok)
        if buffer:
            out_tokens.append("".join(buffer) if len(buffer) >= 2 else buffer[0])
        reconstructed = " ".join(t for t in out_tokens if t != "")
        new_lines.append(reconstructed)
    text = "\n".join(new_lines)

    def _collapse_match(m):
        s = m.group(0)
        return re.sub(r"\s+", "", s)
    text = LETTER_WITH_SPACES_PATTERN.sub(_collapse_match, text)

    text = re.sub(r"\s+([,،:؛\.\?!)])", r"\1", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text
