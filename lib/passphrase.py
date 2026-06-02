#!/usr/bin/env python3
"""
passphrase.py — Readable passphrase generator (Phase 1.F.7).

Generates passwords in Capital.word.phrase.9 format from a curated word list.
Format: one leading-capital word, two-to-three lowercase words, period separators,
trailing digit. Total length 20-30 characters.

Used for:
  - KeePass master password suggestion at forge time
  - Initial service credential generation
  - Temporary root password for broodling spawn (via spawn_planner.py)

Character set: A-Z (leading only), a-z, 0-9, period.
No shell-special characters — passphrases are safe to embed in scripts.

Entropy source
--------------
The production path (rng=None) uses Python's `secrets` module exclusively:
  - `secrets.choice()` and `secrets.randbelow()` are backed by `os.urandom()`
    which is a CSPRNG (ChaCha20 on Linux ≥5.6, Fortuna on macOS, BCryptGenRandom
    on Windows). This is the same OS-level source that KeePass uses internally.

The `rng` parameter accepts a `random.Random` instance ONLY for deterministic
testing (test_seeded_reproducible). It MUST NOT be used in production paths.

KeePass master password
-----------------------
For the KeePass master password specifically, `generate_master_password_suggestion()`
first attempts `keepassxc-cli generate` when KeePass is already installed,
falling back to the secrets-based generator otherwise. This means the operator
sees a KeePass-native suggestion whenever possible.

Stdlib only.
"""

import random  # used ONLY for the deterministic test path (rng parameter)
import secrets
import string
import subprocess
from typing import Optional


# ---------------------------------------------------------------------------
# Word list — common 4-8 letter English words suitable for passphrases
# Chosen for: memorability, unambiguous spelling, no offensive content
# ---------------------------------------------------------------------------

_WORDS: tuple[str, ...] = (
    "able", "above", "across", "after", "again", "agent", "agree",
    "ahead", "allow", "alone", "along", "alter", "angle", "ankle",
    "antler", "apply", "apron", "arbor", "arise", "arrow", "atlas",
    "audio", "audit", "avid", "awake", "axle",
    "badge", "baker", "barge", "batch", "beacon", "beach", "bench",
    "berry", "blade", "blank", "blast", "blend", "block", "bloom",
    "blown", "board", "bonus", "boost", "booth", "botch", "bound",
    "brace", "brake", "brand", "brave", "break", "breed", "bride",
    "brief", "brine", "bring", "brisk", "broad", "brook", "brown",
    "brush", "build", "built", "burst", "buyer",
    "cable", "cameo", "canoe", "cargo", "carry", "cedar", "chain",
    "chalk", "chart", "chase", "check", "chief", "child", "chisel",
    "chord", "civic", "civil", "claim", "clamp", "clash", "class",
    "clean", "clear", "clerk", "click", "cliff", "climb", "clock",
    "clone", "close", "cloud", "coach", "coast", "comet", "coral",
    "could", "count", "cover", "craft", "crane", "creek", "crisp",
    "cross", "crust", "cubic", "curve",
    "daily", "dance", "datum", "debug", "delta", "dense", "depot",
    "depth", "derby", "drift", "drive", "drone", "drove", "dryly",
    "dusky", "dwarf",
    "eager", "eagle", "early", "earth", "eight", "elder", "elect",
    "ember", "emote", "empty", "enact", "enter", "equal", "error",
    "event", "every", "exact", "exist", "extra",
    "fable", "facet", "faint", "faith", "false", "fancy", "feast",
    "fetch", "fever", "field", "fifth", "fifty", "final", "first",
    "fixed", "fjord", "flame", "flask", "fleet", "flesh", "float",
    "flood", "floor", "flora", "flour", "flown", "focus", "forge",
    "forth", "found", "frame", "freed", "fresh", "front", "frost",
    "froze", "fully", "funky", "fuzzy",
    "gable", "gecko", "ghost", "given", "glare", "glass", "glide",
    "globe", "gloom", "gloss", "glove", "glyph", "gnome", "grace",
    "grade", "grain", "grand", "grant", "gravel", "great", "green",
    "greet", "grift", "grind", "groan", "grove", "grown", "guard",
    "guide", "guild", "guise", "gusto",
    "haven", "hazel", "heavy", "helix", "herald", "hinge", "hivemind",
    "hoist", "holly", "honey", "honor", "hover", "humid",
    "infer", "input", "inset", "inter",
    "jewel", "jumbo", "juror",
    "kayak", "ketch", "knack", "knave", "kneel", "knoll", "knot",
    "label", "lance", "latch", "layer", "learn", "ledge", "light",
    "limit", "linen", "liner", "lingo", "locus", "lodge", "logic",
    "lower", "lucid", "lunar",
    "maker", "maple", "march", "match", "medal", "merge", "merit",
    "micro", "mixer", "model", "module", "mondo", "moose", "morph",
    "mossy", "motif", "mount", "mouse", "mover", "muddy", "multi",
    "natal", "nerve", "nexus", "noble", "notch", "noted", "novel",
    "offer", "often", "onion", "onset", "optic", "orbit", "orchid",
    "order", "organ", "other", "outer", "outwit", "ovoid",
    "panel", "paper", "parse", "patch", "pause", "payoff", "pearl",
    "pedal", "penny", "perch", "pilot", "pinch", "pixel", "pivot",
    "place", "plain", "plane", "plant", "plate", "plaza", "plead",
    "plume", "plunk", "plush", "polar", "poppy", "poser", "power",
    "press", "pride", "prime", "prism", "probe", "prone", "proof",
    "proto", "prowl", "proxy", "prune", "pulse",
    "query", "quest", "quick", "quirk", "quota",
    "radar", "radio", "raise", "rally", "ramen", "ranch", "range",
    "rapid", "ratio", "reach", "ready", "realm", "rebel", "relay",
    "remix", "renew", "repay", "reset", "reuse", "ridge", "rivet",
    "robin", "rocky", "rough", "round", "route", "rover", "royal",
    "rugby", "ruler", "rural", "rusty",
    "sabre", "saddle", "salvo", "sandy", "scala", "scale", "scene",
    "scout", "screw", "scrub", "seeds", "seize", "serve", "seven",
    "shade", "shaft", "shake", "shape", "share", "sharp", "sheen",
    "shelf", "shell", "shift", "shiny", "shore", "short", "shout",
    "shrub", "sight", "sigma", "sixty", "sized", "skiff", "skill",
    "skimp", "slant", "slate", "sleek", "sleet", "slice", "slide",
    "slope", "sloth", "smart", "smelt", "smile", "smolt", "snare",
    "sneak", "solid", "solve", "sonar", "south", "space", "spare",
    "spark", "spawn", "speak", "speed", "spend", "spike", "spine",
    "spire", "split", "spree", "squad", "squib", "stack", "stage",
    "stale", "stall", "stamp", "stand", "stark", "start", "state",
    "steam", "steel", "steep", "steer", "stein", "stern", "stint",
    "stock", "stoic", "stone", "store", "storm", "story", "stove",
    "strap", "straw", "strip", "strut", "stuck", "study", "style",
    "suite", "super", "surge", "swamp", "sweep", "swept", "swift",
    "swirl", "swoop", "synth",
    "table", "talon", "tawny", "teach", "tenth", "terra", "terse",
    "theme", "thick", "thief", "thing", "think", "third", "thorn",
    "three", "threw", "throw", "thumb", "tiger", "tiled", "timer",
    "titan", "token", "tonal", "touch", "tough", "tower", "trace",
    "track", "trade", "trail", "train", "trait", "trawl", "trend",
    "tried", "trove", "truck", "truly", "tryst", "tuned", "tural",
    "twirl", "twist",
    "ultra", "unbox", "under", "unify", "until", "upper", "urban",
    "usage", "usual", "utter",
    "valid", "valve", "vapor", "vault", "venom", "verge", "verso",
    "video", "vigor", "viral", "vivid", "voice", "volta", "voter",
    "voted", "vouch",
    "water", "weave", "wedge", "weird", "while", "white", "whole",
    "wider", "windy", "wired", "witch", "witty", "woken", "world",
    "worth", "would", "woven",
    "xenon", "xeric",
    "yeast", "yield", "young", "yours",
    "zebra", "zoned", "zonal",
)

# Minimum and maximum total passphrase length (including periods and digit)
_MIN_LEN = 20
_MAX_LEN = 30


# ---------------------------------------------------------------------------
# Secure sampling (production path)
# ---------------------------------------------------------------------------

def _secure_sample(population: tuple | list, k: int) -> list:
    """
    Draw k distinct items from population using secrets.randbelow().

    Each draw uses a fresh os.urandom()-backed call — no shared state
    carries entropy information between draws.
    """
    pool   = list(population)
    result = []
    for _ in range(k):
        idx = secrets.randbelow(len(pool))
        result.append(pool.pop(idx))
    return result


# ---------------------------------------------------------------------------
# Passphrase generator
# ---------------------------------------------------------------------------

def generate_passphrase(rng: Optional[random.Random] = None) -> str:
    """
    Generate a readable passphrase in Capital.word.phrase.9 format.

    Format:
      Capital.word1.word2[.word3].digit
      - First word: leading capital, rest lowercase
      - Subsequent words: all lowercase
      - Separated by periods
      - Final trailing digit (0-9)
      - Total length 20-30 characters

    Returns a string such as "Forest.amber.glide.8" or "Brave.sonic.relay.stone.3".

    rng: pass a random.Random instance ONLY for deterministic testing.
         Leave as None (default) in all production paths — the function
         then uses secrets.choice() / secrets.randbelow() which are
         backed by os.urandom() (the same CSPRNG KeePass uses internally).
    """
    for _attempt in range(200):
        if rng is None:
            n_words = secrets.choice([2, 3])
            chosen  = _secure_sample(_WORDS, n_words)
            digit   = str(secrets.randbelow(10))
        else:
            n_words = rng.choice([2, 3])
            chosen  = rng.sample(list(_WORDS), n_words)
            digit   = str(rng.randint(0, 9))

        first  = chosen[0].capitalize()
        rest   = chosen[1:]
        phrase = ".".join([first] + rest) + "." + digit
        if _MIN_LEN <= len(phrase) <= _MAX_LEN:
            return phrase

    # Fallback: 3 words — should never be reached with this word list.
    if rng is None:
        chosen = _secure_sample(_WORDS, 3)
        digit  = str(secrets.randbelow(10))
    else:
        chosen = rng.sample(list(_WORDS), 3)
        digit  = str(rng.randint(0, 9))
    return chosen[0].capitalize() + "." + chosen[1] + "." + chosen[2] + "." + digit


def generate_passphrase_n(count: int, rng: Optional[random.Random] = None) -> list[str]:
    """Generate `count` distinct passphrases."""
    results: list[str] = []
    seen:    set[str]  = set()
    for _ in range(count * 10):
        p = generate_passphrase(rng)
        if p not in seen:
            seen.add(p)
            results.append(p)
        if len(results) == count:
            break
    return results


# ---------------------------------------------------------------------------
# Alphanumeric generator
# ---------------------------------------------------------------------------

def generate_alphanumeric(
    length: int = 24,
    rng:    Optional[random.Random] = None,
) -> str:
    """
    Generate an alphanumeric-only password (letters + digits, no special chars).

    Uses secrets.choice() (os.urandom) on the production path.
    rng parameter is for deterministic testing only.

    Guarantees at least one uppercase letter, one lowercase letter, one digit.
    Length default matches 24-char typical service credential length.
    """
    alphabet = string.ascii_letters + string.digits

    if rng is None:
        chars = [secrets.choice(alphabet) for _ in range(length)]
        # Guarantee character-class diversity by replacing three positions
        pos = _secure_sample(range(length), 3)
        chars[pos[0]] = secrets.choice(string.ascii_uppercase)
        chars[pos[1]] = secrets.choice(string.ascii_lowercase)
        chars[pos[2]] = secrets.choice(string.digits)
    else:
        chars = [rng.choice(alphabet) for _ in range(length)]
        rng.shuffle(chars)
        pos = rng.sample(range(length), 3)
        chars[pos[0]] = rng.choice(string.ascii_uppercase)
        chars[pos[1]] = rng.choice(string.ascii_lowercase)
        chars[pos[2]] = rng.choice(string.digits)

    return "".join(chars)


# ---------------------------------------------------------------------------
# KeePass-native generation (preferred for master password)
# ---------------------------------------------------------------------------

def keepassxc_generate(
    length:    int  = 32,
    uppercase: bool = True,
    lowercase: bool = True,
    digits:    bool = True,
    special:   bool = False,
) -> Optional[str]:
    """
    Generate a password using keepassxc-cli's own CSPRNG.

    Returns the generated password string, or None if keepassxc-cli is not
    installed or the command fails.

    keepassxc-cli generates passwords using KeePass's own secure random engine
    (the same engine used for database key generation). This is the most
    trustworthy source for the KeePass master password itself — generated
    by the same application that will guard it.

    Note: keepassxc-cli's `generate` command does not support the
    Capital.word.phrase.N format; it generates character-class passwords.
    For that reason this function is offered as an alternative for the master
    password but the Python-backed generator (using secrets) is used for
    service credentials where the period-separated format is expected.
    """
    try:
        cmd = ["keepassxc-cli", "generate", f"-L{length}"]
        if uppercase: cmd.append("-u")
        if lowercase: cmd.append("-l")
        if digits:    cmd.append("-n")
        if special:   cmd.append("-s")
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            generated = result.stdout.strip()
            if generated:
                return generated
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def generate_master_password_suggestion() -> tuple[str, str]:
    """
    Generate a master password suggestion for display at forge time.

    Returns (password, source) where source is either:
      "keepassxc-cli"  — generated by KeePass's own CSPRNG (preferred)
      "secrets"        — generated by Python's secrets module (os.urandom)

    Tries keepassxc-cli first. Falls back to the secrets-based generator
    when KeePass is not yet installed (e.g. before forge phase-03).

    Both sources use a CSPRNG (os.urandom or equivalent). The keepassxc-cli
    path is preferred so operators can see that the suggestion comes from the
    same tool they are about to use as their password manager.
    """
    kp = keepassxc_generate(length=28, uppercase=True, lowercase=True,
                             digits=True, special=False)
    if kp:
        return kp, "keepassxc-cli"

    passphrase = generate_passphrase()
    return passphrase, "secrets"


# ---------------------------------------------------------------------------
# Strength report
# ---------------------------------------------------------------------------

def passphrase_strength(phrase: str) -> dict:
    """
    Return a simple strength breakdown for a passphrase.

    Returns: {length, word_count, has_digit, format_valid, meets_min_length}
    """
    parts = phrase.split(".")
    has_digit  = parts[-1].isdigit() if parts else False
    word_parts = parts[:-1] if has_digit else parts
    return {
        "length":           len(phrase),
        "word_count":       len(word_parts),
        "has_digit":        has_digit,
        "format_valid":     (
            len(word_parts) >= 2
            and word_parts[0][:1].isupper()
            and all(w[:1].islower() or w == "" for w in word_parts[1:])
            and has_digit
        ),
        "meets_min_length": len(phrase) >= _MIN_LEN,
    }
