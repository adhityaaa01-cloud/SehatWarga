"""Local safety boundary: executed before any external provider sees a message."""
import re
import unicodedata

SAFETY_INTENTS = {"EMERGENCY", "MEDICAL_INQUIRY", "SECURITY_INQUIRY"}


def normalized_text(message):
    text = unicodedata.normalize("NFKC", message).lower()
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def deterministic_safety(message):
    text = normalized_text(message)
    # Safety always precedes generic greetings, facility search and model inference.
    if re.search(r"gawat darurat|kondisi darurat|serangan jantung|henti jantung|tidak sadar|pingsan|pendarahan hebat|perdarahan hebat|sesak napas parah|sulit bernapas|overdosis|sekarat|kritis|bunuh diri|mengakhiri hidup", text):
        return "EMERGENCY"
    if re.search(r"secret[_\s-]*key|database[_\s-]*url|api[_\s-]*key|\.env|\b(env|environ|kredensial|password|token|bearer)\b|kata sandi|system prompt|prompt sistem|ignore.{0,30}(previous|instruction)|abaikan.{0,40}(instruksi|aturan|sebelumnya)|bocorkan|jailbreak|developer mode|drop table|union select|shell command|curi|meretas|malware|bom|racun|senjata", text):
        return "SECURITY_INQUIRY"
    if re.search(r"diagnos|penyakit apa|sakit apa|kenapa saya sakit|gejala|resep|dosis|obat|apakah saya terkena|saya.{0,25}(demam|mual|nyeri|sakit|muntah)|cara.{0,15}(mengobati|menyembuhkan)", text):
        return "MEDICAL_INQUIRY"
    return None


def redact_sensitive(message):
    """Only a bounded, redacted current message may leave the backend.

    Never send application context, history, account records or user coordinates.
    Numeric identifiers, e-mails, URLs, bearer-like strings and membership codes
    are removed; explicit credential queries are already blocked by the guard.
    """
    text = normalized_text(message)[:2000]
    patterns = [r"https?://\S+", r"[\w.+-]+@[\w.-]+\.[a-z]{2,}",
                r"\bSW[A-Z]*-[A-Z0-9-]+\b", r"\b\d(?:[\s.-]?\d){5,}\b",
                r"\b[A-Za-z0-9_+/=-]{24,}\b"]
    for pattern in patterns:
        text = re.sub(pattern, "[data dihapus]", text, flags=re.I)
    return text
