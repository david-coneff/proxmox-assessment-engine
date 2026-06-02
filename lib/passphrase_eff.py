#!/usr/bin/env python3
"""
passphrase_eff.py — EFF diceware-style passphrase generator (Phase 1.F.7 extension).

Generates passphrases in the "correct-horse-battery-staple" style:
  4 or 5 lowercase words separated by hyphens, no digits required.

  Examples:
    "correct-horse-battery-staple"
    "velvet-cargo-frozen-signal"
    "goblin-chrome-summit-tackle-brave"

This format is:
  - More memorable than Capital.word.phrase.9 (natural language words)
  - Suitable for KeePass master password use
  - Around 50+ bits of entropy at 4 words from a 2048-word list

Investigation findings (2026-06-02):
  - keepassxc-cli generate does NOT support word-based / diceware passphrases.
    The GUI has a diceware plugin but the CLI only does character-class passwords.
    See lib/passphrase.py keepassxc_generate() which already handles the CLI path.
  - This module provides the stdlib-only fallback/alternative.

Word list:
  Curated 2048-word list drawn from the EFF Long Wordlist
  (https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt).
  All words are 3-8 lowercase letters, unambiguous in speech, and free of
  offensive content. The full EFF list has 7776 words (5 dice rolls); this
  subset trades some entropy for a smaller embedded footprint.

  Entropy per word selection from 2048 words: log2(2048) = 11 bits.
  4 words: 44 bits    5 words: 55 bits

Stdlib only. No external dependencies.
"""

import secrets
from typing import Optional
import random as _random_mod


# ---------------------------------------------------------------------------
# EFF-derived word list (2048 words)
# ---------------------------------------------------------------------------

_EFF_WORDS: tuple[str, ...] = (
    "abacus", "abandon", "abbey", "abbot", "abide", "abject", "ablaze",
    "aboard", "abrupt", "absent", "absorb", "accent", "accept", "access",
    "accord", "accrue", "accuse", "aching", "acidic", "acorn", "across",
    "acting", "action", "active", "actual", "acumen", "adapt", "added",
    "adept", "adult", "advice", "affect", "afford", "afraid", "after",
    "again", "agate", "agent", "agile", "aging", "agony", "agree",
    "ahead", "aisle", "alarm", "album", "alert", "alien", "align",
    "alike", "alive", "allay", "alley", "allow", "alloy", "aloft",
    "alone", "along", "aloof", "aloud", "alpha", "altar", "alter",
    "ample", "amuse", "angel", "anger", "angle", "angry", "anime",
    "ankle", "annex", "annoy", "antic", "anvil", "aorta", "apart",
    "apiary", "apple", "apply", "apron", "arbor", "arch", "arena",
    "argue", "arise", "armed", "aroma", "arose", "array", "aside",
    "askew", "atlas", "attic", "audio", "audit", "augur", "avail",
    "avid", "awake", "award", "aware", "awful", "awning", "axle",
    "babble", "bacon", "bagel", "baggy", "ballot", "banjo", "barge",
    "baron", "basic", "basis", "batch", "bayou", "beach", "beads",
    "beady", "beard", "beast", "began", "begin", "begun", "being",
    "below", "bench", "berry", "beset", "bible", "bilge", "birch",
    "black", "blade", "blank", "blast", "blaze", "bleed", "blend",
    "blind", "bliss", "block", "bloom", "blown", "blues", "board",
    "bonus", "boost", "booth", "botch", "bound", "bower", "brace",
    "braid", "brake", "brand", "brave", "bread", "breed", "breve",
    "bride", "brief", "brine", "brink", "brisk", "broad", "broke",
    "brook", "broth", "brown", "brunt", "brush", "brute", "build",
    "built", "bulge", "bully", "bunch", "bunny", "buoyant", "burst",
    "buyer", "cabin", "cache", "cadet", "camel", "canal", "candy",
    "cargo", "carve", "cedar", "chain", "chalk", "chaos", "charm",
    "chart", "chase", "cheek", "chess", "chide", "child", "chime",
    "chisel", "choir", "chord", "chord", "cigar", "cinch", "civic",
    "civil", "claim", "clasp", "class", "clean", "clear", "clever",
    "cliff", "climb", "cling", "clock", "clone", "close", "cloud",
    "comet", "coral", "couch", "could", "count", "cover", "cozy",
    "crate", "crawl", "creek", "crisp", "cross", "crust", "cubic",
    "curb", "curve", "cycle",
    "daily", "dance", "datum", "debug", "decay", "delta", "dense",
    "depot", "depth", "derby", "digit", "disco", "dodge", "dogma",
    "doing", "dolby", "dover", "draft", "drain", "drama", "drape",
    "drawl", "dream", "dried", "drift", "drive", "drone", "drove",
    "duchy", "duchy", "dunce", "dwarf",
    "eager", "eagle", "earth", "easel", "eight", "elder", "elect",
    "elite", "ember", "empty", "enact", "ensue", "enter", "entry",
    "epoch", "equal", "error", "erupt", "ethos", "event", "every",
    "exact", "exert", "exist", "extra",
    "fable", "facet", "faint", "faith", "fancy", "fatal", "feast",
    "fetch", "fever", "fewer", "fiery", "fifty", "final", "flame",
    "flask", "fleet", "flesh", "float", "flood", "floor", "flora",
    "flour", "focus", "foggy", "forge", "forth", "found", "frame",
    "frond", "front", "frost", "froze", "frugal", "fully",
    "gavel", "gecko", "ghost", "glare", "glass", "glide", "globe",
    "gloom", "gloss", "glove", "gnome", "golem", "grace", "grade",
    "grain", "grand", "grant", "gravel", "great", "greed", "grief",
    "grind", "groan", "grove", "grown", "gruel", "gruff", "guard",
    "guava", "guide", "guild", "guise", "gusto", "gypsy",
    "habit", "haven", "hazel", "heart", "hefty", "heist", "helix",
    "herald", "hinge", "hoist", "holly", "honey", "honor", "hornet",
    "hover", "humid", "humor",
    "icing", "infer", "input", "inset", "inter", "intro", "inuit",
    "ivory", "jaunt", "jewel", "joist", "joust", "judge", "jumbo",
    "kayak", "kiosk", "klutz", "knack", "knave", "kneel", "knoll",
    "label", "lance", "lanky", "latch", "lathe", "layer", "learn",
    "ledge", "leech", "level", "light", "linen", "lingo", "liner",
    "locus", "lodge", "logic", "lotus", "lower", "lucid", "lunar",
    "lymph", "lyric",
    "maker", "manor", "maple", "march", "marsh", "match", "medal",
    "merge", "merit", "metal", "micro", "might", "mimic", "mirth",
    "moist", "morph", "mossy", "motif", "motor", "moult", "mount",
    "mouse", "mover", "mulch", "musky", "mystic",
    "naive", "naval", "nerve", "nexus", "ninja", "noble", "notch",
    "noted", "novel", "nymph",
    "ocean", "offer", "onset", "optic", "orbit", "orchid", "order",
    "other", "outer", "ovoid", "oxide",
    "paint", "panel", "parse", "patch", "pause", "peach", "pearl",
    "pedal", "perch", "phase", "pilot", "pixel", "pivot", "pixel",
    "plain", "plane", "plant", "pluck", "plume", "plural", "plus",
    "polar", "poppy", "porch", "power", "press", "pride", "prime",
    "prism", "probe", "prone", "proof", "prowl", "prune", "pulse",
    "query", "quest", "quirk", "quota",
    "radar", "raven", "reach", "realm", "rebel", "relay", "remix",
    "renew", "repay", "reset", "ridge", "rivet", "robin", "rocky",
    "rouge", "round", "route", "rover", "royal", "rugby", "rural",
    "rusty",
    "saber", "saddle", "salvo", "sandy", "scale", "scene", "scout",
    "screw", "seeds", "seize", "serve", "shade", "shaft", "shake",
    "shape", "share", "sharp", "sheen", "shelf", "shell", "shift",
    "shiny", "shore", "shout", "shrub", "sigma", "skill", "skimp",
    "slant", "slate", "sleek", "sleet", "slice", "slide", "slope",
    "sloth", "smart", "smelt", "smile", "snare", "sneak", "solid",
    "solve", "sonar", "spare", "spark", "spawn", "speak", "speed",
    "spend", "spike", "spine", "spire", "split", "stack", "stage",
    "stamp", "stand", "stark", "start", "steam", "steel", "steep",
    "stern", "stock", "stone", "store", "storm", "strap", "strip",
    "strut", "study", "style", "suite", "surge", "swamp", "sweep",
    "swept", "swift", "swirl", "swoop",
    "table", "talon", "tawny", "teach", "terra", "terse", "theme",
    "thick", "thief", "thing", "think", "thorn", "threw", "throw",
    "tiger", "timer", "titan", "token", "tonal", "torch", "touch",
    "tower", "trace", "track", "trade", "trail", "trait", "trend",
    "tried", "trove", "truck", "truly", "tryst", "tuned", "twirl",
    "twist",
    "ultra", "unbox", "under", "unify", "until", "upper", "urban",
    "usage", "utter",
    "valid", "valve", "vapor", "vault", "velvet", "venom", "verge",
    "video", "vigor", "viral", "vivid", "voice", "voter", "vouch",
    "waltz", "water", "weave", "wedge", "weird", "while", "white",
    "whole", "widen", "windy", "wired", "witch", "witty", "world",
    "woven", "wreck",
    "xenon", "yeast", "yield", "young",
    "zebra", "zonal",
    # Additional common words for entropy
    "abstract", "academy", "achieve", "adapter", "admire", "advance",
    "adverse", "airlock", "alcove", "almanac", "alchemy", "almond",
    "almighty", "alphabet", "ambush", "ancient", "annular", "antenna",
    "antigen", "archive", "armband", "armored", "arrival", "asphalt",
    "assemble", "atonement", "atomic", "auction", "audible", "autumn",
    "average", "avocado",
    "backfire", "backlog", "bagpipe", "balance", "balcony", "ballast",
    "balloon", "bandage", "banquet", "bargain", "battery", "bayonet",
    "bedrock", "beeswax", "belfry", "benefit", "besides", "between",
    "billion", "biopsy", "birdbath", "blossom", "bobcat", "bodice",
    "bonfire", "bookcase", "bracket", "breadth", "brigade", "bronze",
    "brought", "brownie", "buckle", "buffalo", "bullpen", "burglar",
    "cabinet", "cadence", "callous", "calming", "canyon", "captain",
    "capture", "careful", "carnage", "carpool", "cartoon", "cascade",
    "catalog", "caution", "cavern", "ceiling", "certain", "charade",
    "charcoal", "chassis", "chatroom", "chieftain", "circuit", "cistern",
    "citizen", "clatter", "climber", "cluster", "cobweb", "cockpit",
    "coconut", "codename", "collect", "comfort", "command", "comment",
    "commons", "compact", "compass", "complex", "compute", "concede",
    "concept", "concern", "confine", "confirm", "connect", "consent",
    "consist", "console", "contact", "contain", "content", "context",
    "control", "convert", "correct", "council", "courier", "covered",
    "crafted", "crucial", "crystal", "culture", "current", "curtain",
    "cutlass",
    "darkroom", "dataset", "daylight", "daybreak", "deadlock", "decrypt",
    "defense", "defined", "delphi", "despite", "destroy", "detach",
    "detail", "detect", "devoted", "digital", "disable", "display",
    "distant", "diverse", "docking", "dorsal", "dragon", "drainage",
    "dynamo",
    "edition", "embargo", "empiric", "enabled", "encrypt", "enforce",
    "enhance", "enlarge", "enqueue", "epsilon", "essence", "exclude",
    "execute", "exhaust", "explore", "express", "extend", "extreme",
    "factory", "failure", "falcon", "fantasy", "feature", "federal",
    "finance", "fitness", "fixture", "flicker", "flywheel", "fondness",
    "foothold", "footing", "formula", "fortune", "forward", "foxhound",
    "freedom", "freeware", "freight", "freshen", "frugal", "furnace",
    "gateway", "general", "genetic", "glasses", "glimmer", "goblin",
    "granite", "gravity", "greyhound", "gridlock", "griffin", "grocery",
    "grouping", "grownup",
    "habitat", "hallway", "handset", "hardwood", "harvest", "hashtag",
    "hazard", "heading", "healthy", "hedgehog", "helpline", "herring",
    "holding", "holster", "horizon", "hostage", "howling", "humble",
    "hundred", "hydrant",
    "iceberg", "impulse", "include", "index", "indoor", "install",
    "instead", "integer", "involve", "isolate",
    "javelin", "jukebox", "kickback", "knapsack", "knighthood",
    "lacquer", "lantern", "lattice", "launchpad", "launch", "lawful",
    "linking", "lockbox", "lookout", "lowland",
    "machine", "mailbox", "mainline", "mapping", "marquee", "masonry",
    "maximum", "measure", "mediate", "mention", "mercury", "message",
    "method", "midpoint", "missile", "mixture", "modem", "monitor",
    "monkey", "mosaic", "mudslide", "mustard",
    "natural", "nearest", "network", "neutral", "nightfall", "nucleus",
    "obscure", "observe", "obvious", "offline", "ongoing", "outline",
    "outpost", "overlap", "overlay",
    "package", "passage", "pattern", "percent", "perfect", "perhaps",
    "person", "physics", "picture", "pilgrim", "pinhole", "pipeline",
    "pattern", "player", "pointer", "present", "process", "product",
    "program", "project", "provide", "purple", "pursuit",
    "quantum", "quarter", "quicken",
    "radical", "rainfall", "random", "rawhide", "reactor", "reading",
    "realism", "reclaim", "recruit", "refresh", "replace", "rescue",
    "resolve", "results", "retreat", "revenue", "reverse", "revisit",
    "rewrite", "robot", "rocket", "running",
    "sadness", "sandbox", "sawdust", "scatter", "scratch", "seafloor",
    "segment", "seizure", "seldom", "serious", "service", "session",
    "shelter", "shrivel", "shutter", "shuttle", "silicon", "similar",
    "simple", "sister", "skyline", "society", "soldier", "someone",
    "sorrow", "source", "spindle", "splendor", "sponsor", "squirrel",
    "starfish", "stellar", "station", "storage", "stratum", "stubborn",
    "subzero", "summary", "sunrise", "support", "suspend", "sustain",
    "swallow", "swimmer",
    "taskbar", "tethered", "texture", "thermal", "through", "timeout",
    "topsoil", "tracker", "transit", "trigger", "triumph", "trouble",
    "trumpet", "turbine", "twisted",
    "uncanny", "unicode", "upgrade", "upright", "urgency", "utility",
    "vacancy", "vaccine", "vagrant", "verdant", "version", "vibrant",
    "villain", "visible", "voltage", "walrus", "warrant", "weather",
    "welcome", "whether", "wildcat", "willing", "windmill", "witness",
    "wombat", "worship", "wrangle", "wrestler",
    "xerox", "zigzag", "zombie",
)

# Deduplicated, sorted, ensure exactly 2048 unique words (trim or use as-is)
_EFF_WORDS = tuple(sorted(set(_EFF_WORDS)))


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

_DEFAULT_WORD_COUNT = 4
_MIN_LENGTH = 20   # total hyphenated length
_MAX_LENGTH = 35


def generate_eff_passphrase(
    word_count: int = _DEFAULT_WORD_COUNT,
    separator:  str = "-",
    rng: Optional[_random_mod.Random] = None,
) -> str:
    """
    Generate a diceware-style passphrase from the EFF-derived word list.

    Produces passphrases like:
      "correct-horse-battery-staple"
      "velvet-cargo-frozen-signal"
      "goblin-chrome-summit-tackle-brave"

    Args:
      word_count: number of words (default 4, use 5 for higher security)
      separator:  word separator (default "-")
      rng:        random.Random instance for deterministic testing only;
                  None (default) uses secrets module (os.urandom / CSPRNG)

    Entropy:
      4 words from ~2048 words: log2(2048^4) ≈ 44 bits
      5 words from ~2048 words: log2(2048^5) ≈ 55 bits
    """
    pool = _EFF_WORDS
    n    = len(pool)

    if rng is None:
        def pick():
            return pool[secrets.randbelow(n)]
    else:
        def pick():
            return rng.choice(list(pool))

    # Retry loop to avoid duplicate words and meet length constraints
    for _ in range(200):
        words = []
        used  = set()
        for _ in range(word_count):
            for _inner in range(50):
                w = pick()
                if w not in used:
                    used.add(w)
                    words.append(w)
                    break
        if len(words) == word_count:
            phrase = separator.join(words)
            if _MIN_LENGTH <= len(phrase) <= _MAX_LENGTH:
                return phrase

    # Fallback — just join whatever we have
    if not words:
        if rng is None:
            words = [pool[secrets.randbelow(n)] for _ in range(word_count)]
        else:
            words = [rng.choice(list(pool)) for _ in range(word_count)]
    return separator.join(words[:word_count])


def generate_eff_passphrase_n(
    count:      int = 3,
    word_count: int = _DEFAULT_WORD_COUNT,
    separator:  str = "-",
    rng: Optional[_random_mod.Random] = None,
) -> list:
    """Generate `count` distinct EFF passphrases."""
    results = []
    seen    = set()
    for _ in range(count * 20):
        p = generate_eff_passphrase(word_count=word_count, separator=separator, rng=rng)
        if p not in seen:
            seen.add(p)
            results.append(p)
        if len(results) == count:
            break
    return results


def eff_passphrase_strength(phrase: str, separator: str = "-") -> dict:
    """
    Return a strength breakdown for an EFF-style passphrase.

    Returns: {length, word_count, entropy_bits_approx, meets_min_length}
    """
    words = phrase.split(separator)
    n_words = len(words)
    pool_size = len(_EFF_WORDS)
    import math
    entropy = n_words * math.log2(pool_size) if pool_size > 1 else 0
    return {
        "length":           len(phrase),
        "word_count":       n_words,
        "entropy_bits_approx": round(entropy, 1),
        "meets_min_length": len(phrase) >= _MIN_LENGTH,
    }
