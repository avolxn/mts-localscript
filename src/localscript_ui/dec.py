from __future__ import annotations

# ============================================================================
# DEC SPECIAL GRAPHICS (Final character: '0')
# Used for: Box drawing, line graphics
# ============================================================================

DEC_GRAPHICS = {
    0x60: "◆",  # ` -> diamond
    0x61: "▒",  # a -> checkerboard
    0x62: "␉",  # b -> HT symbol
    0x63: "␌",  # c -> FF symbol
    0x64: "␍",  # d -> CR symbol
    0x65: "␊",  # e -> LF symbol
    0x66: "°",  # f -> degree symbol
    0x67: "±",  # g -> plus/minus
    0x68: "␤",  # h -> NL symbol
    0x69: "␋",  # i -> VT symbol
    0x6A: "┘",  # j -> lower right corner
    0x6B: "┐",  # k -> upper right corner
    0x6C: "┌",  # l -> upper left corner
    0x6D: "└",  # m -> lower left corner
    0x6E: "┼",  # n -> crossing lines
    0x6F: "⎺",  # o -> scan line 1
    0x70: "⎻",  # p -> scan line 3
    0x71: "─",  # q -> horizontal line
    0x72: "⎼",  # r -> scan line 7
    0x73: "⎽",  # s -> scan line 9
    0x74: "├",  # t -> left tee
    0x75: "┤",  # u -> right tee
    0x76: "┴",  # v -> bottom tee
    0x77: "┬",  # w -> top tee
    0x78: "│",  # x -> vertical bar
    0x79: "≤",  # y -> less than or equal
    0x7A: "≥",  # z -> greater than or equal
    0x7B: "π",  # { -> pi
    0x7C: "≠",  # | -> not equal
    0x7D: "£",  # } -> UK pound sign
    0x7E: "·",  # ~ -> centered dot
}

# ============================================================================
# US ASCII (Final character: 'B')
# Used for: Standard ASCII - default
# No mapping needed - just use chr(code) directly
# ============================================================================

US_ASCII = {}  # Identity mapping - no changes

# ============================================================================
# UK ASCII (Final character: 'A')
# Used for: British keyboard - pound sign
# ============================================================================

UK_ASCII = {
    0x23: "£",  # # -> £ (pound sign)
}

# ============================================================================
# DEC SUPPLEMENTAL GRAPHICS (Final character: '<')
# Used for: Western European accented characters (GR range 0xA0-0xFF)
# These would normally go in GR, not GL
# ============================================================================

DEC_SUPPLEMENTAL = {
    # Note: These are for the GR range (0xA0-0xFF), shown here with
    # their effective codes after subtracting 0x80 (so 0x20-0x7F range)
    0x21: "¡",  # A1 -> inverted exclamation
    0x22: "¢",  # A2 -> cent sign
    0x23: "£",  # A3 -> pound sign
    0x24: "¤",  # A4 -> currency sign (was blank in doc)
    0x25: "¥",  # A5 -> yen sign
    0x27: "§",  # A7 -> section sign
    0x28: "¤",  # A8 -> currency sign
    0x29: "©",  # A9 -> copyright
    0x2A: "ª",  # AA -> feminine ordinal
    0x2B: "«",  # AB -> left guillemet
    0x30: "°",  # B0 -> degree
    0x31: "±",  # B1 -> plus-minus
    0x32: "²",  # B2 -> superscript 2
    0x33: "³",  # B3 -> superscript 3
    0x35: "µ",  # B5 -> micro
    0x36: "¶",  # B6 -> pilcrow (paragraph)
    0x37: "·",  # B7 -> middle dot
    0x39: "¹",  # B9 -> superscript 1
    0x3A: "º",  # BA -> masculine ordinal
    0x3B: "»",  # BB -> right guillemet
    0x3C: "¼",  # BC -> one quarter
    0x3D: "½",  # BD -> one half
    0x3F: "¿",  # BF -> inverted question mark
    0x40: "À",  # C0 -> A grave
    0x41: "Á",  # C1 -> A acute
    0x42: "Â",  # C2 -> A circumflex
    0x43: "Ã",  # C3 -> A tilde
    0x44: "Ä",  # C4 -> A diaeresis
    0x45: "Å",  # C5 -> A ring
    0x46: "Æ",  # C6 -> AE ligature
    0x47: "Ç",  # C7 -> C cedilla
    0x48: "È",  # C8 -> E grave
    0x49: "É",  # C9 -> E acute
    0x4A: "Ê",  # CA -> E circumflex
    0x4B: "Ë",  # CB -> E diaeresis
    0x4C: "Ì",  # CC -> I grave
    0x4D: "Í",  # CD -> I acute
    0x4E: "Î",  # CE -> I circumflex
    0x4F: "Ï",  # CF -> I diaeresis
    0x51: "Ñ",  # D1 -> N tilde
    0x52: "Ò",  # D2 -> O grave
    0x53: "Ó",  # D3 -> O acute
    0x54: "Ô",  # D4 -> O circumflex
    0x55: "Õ",  # D5 -> O tilde
    0x56: "Ö",  # D6 -> O diaeresis
    0x57: "Œ",  # D7 -> OE ligature
    0x58: "Ø",  # D8 -> O slash
    0x59: "Ù",  # D9 -> U grave
    0x5A: "Ú",  # DA -> U acute
    0x5B: "Û",  # DB -> U circumflex
    0x5C: "Ü",  # DC -> U diaeresis
    0x5D: "Ÿ",  # DD -> Y diaeresis
    0x5F: "ß",  # DF -> sharp s (German)
    0x60: "à",  # E0 -> a grave
    0x61: "á",  # E1 -> a acute
    0x62: "â",  # E2 -> a circumflex
    0x63: "ã",  # E3 -> a tilde
    0x64: "ä",  # E4 -> a diaeresis
    0x65: "å",  # E5 -> a ring
    0x66: "æ",  # E6 -> ae ligature
    0x67: "ç",  # E7 -> c cedilla
    0x68: "è",  # E8 -> e grave
    0x69: "é",  # E9 -> e acute
    0x6A: "ê",  # EA -> e circumflex
    0x6B: "ë",  # EB -> e diaeresis
    0x6C: "ì",  # EC -> i grave
    0x6D: "í",  # ED -> i acute
    0x6E: "î",  # EE -> i circumflex
    0x6F: "ï",  # EF -> i diaeresis
    0x71: "ñ",  # F1 -> n tilde
    0x72: "ò",  # F2 -> o grave
    0x73: "ó",  # F3 -> o acute
    0x74: "ô",  # F4 -> o circumflex
    0x75: "õ",  # F5 -> o tilde
    0x76: "ö",  # F6 -> o diaeresis
    0x77: "œ",  # F7 -> oe ligature
    0x78: "ø",  # F8 -> o slash
    0x79: "ù",  # F9 -> u grave
    0x7A: "ú",  # FA -> u acute
    0x7B: "û",  # FB -> u circumflex
    0x7C: "ü",  # FC -> u diaeresis
    0x7D: "ÿ",  # FD -> y diaeresis
}

# ============================================================================
# NATIONAL REPLACEMENT CHARACTER SETS
# These replace specific ASCII positions with national characters
# ============================================================================

# Dutch NRC (Final character: '4')
DUTCH_NRC = {
    0x23: "£",  # # -> £
    0x40: "¾",  # @ -> ¾
    0x5B: "ĳ",  # [ -> ij ligature
    0x5C: "½",  # \ -> ½
    0x5D: "|",  # ] -> |
    0x7B: "¨",  # { -> diaeresis
    0x7C: "f",  # | -> f (florin)
    0x7D: "¼",  # } -> ¼
    0x7E: "´",  # ~ -> acute accent
}

# Finnish NRC (Final character: 'C' or '5')
FINNISH_NRC = {
    0x5B: "Ä",  # [ -> Ä
    0x5C: "Ö",  # \ -> Ö
    0x5D: "Å",  # ] -> Å
    0x5E: "Ü",  # ^ -> Ü
    0x60: "é",  # ` -> é
    0x7B: "ä",  # { -> ä
    0x7C: "ö",  # | -> ö
    0x7D: "å",  # } -> å
    0x7E: "ü",  # ~ -> ü
}

# French NRC (Final character: 'R')
FRENCH_NRC = {
    0x23: "£",  # # -> £
    0x40: "à",  # @ -> à
    0x5B: "°",  # [ -> °
    0x5C: "ç",  # \ -> ç
    0x5D: "§",  # ] -> §
    0x7B: "é",  # { -> é
    0x7C: "ù",  # | -> ù
    0x7D: "è",  # } -> è
    0x7E: "¨",  # ~ -> ¨
}

# French Canadian NRC (Final character: 'Q')
FRENCH_CANADIAN_NRC = {
    0x40: "à",  # @ -> à
    0x5B: "â",  # [ -> â
    0x5C: "ç",  # \ -> ç
    0x5D: "ê",  # ] -> ê
    0x5E: "î",  # ^ -> î
    0x60: "ô",  # ` -> ô
    0x7B: "é",  # { -> é
    0x7C: "ù",  # | -> ù
    0x7D: "è",  # } -> è
    0x7E: "û",  # ~ -> û
}

# German NRC (Final character: 'K')
GERMAN_NRC = {
    0x40: "§",  # @ -> §
    0x5B: "Ä",  # [ -> Ä
    0x5C: "Ö",  # \ -> Ö
    0x5D: "Ü",  # ] -> Ü
    0x7B: "ä",  # { -> ä
    0x7C: "ö",  # | -> ö
    0x7D: "ü",  # } -> ü
    0x7E: "ß",  # ~ -> ß
}

# Italian NRC (Final character: 'Y')
ITALIAN_NRC = {
    0x23: "£",  # # -> £
    0x40: "§",  # @ -> §
    0x5B: "°",  # [ -> °
    0x5C: "ç",  # \ -> ç
    0x5D: "é",  # ] -> é
    0x60: "ù",  # ` -> ù
    0x7B: "à",  # { -> à
    0x7C: "ò",  # | -> ò
    0x7D: "è",  # } -> è
    0x7E: "ì",  # ~ -> ì
}

# Norwegian/Danish NRC (Final character: 'E' or '6')
NORWEGIAN_DANISH_NRC = {
    0x40: "Ä",  # @ -> Ä
    0x5B: "Æ",  # [ -> Æ
    0x5C: "Ø",  # \ -> Ø
    0x5D: "Å",  # ] -> Å
    0x5E: "Ü",  # ^ -> Ü
    0x60: "ä",  # ` -> ä
    0x7B: "æ",  # { -> æ
    0x7C: "ø",  # | -> ø
    0x7D: "å",  # } -> å
    0x7E: "ü",  # ~ -> ü
}

# Spanish NRC (Final character: 'Z')
SPANISH_NRC = {
    0x23: "£",  # # -> £
    0x40: "§",  # @ -> §
    0x5B: "¡",  # [ -> ¡
    0x5C: "Ñ",  # \ -> Ñ
    0x5D: "¿",  # ] -> ¿
    0x7B: "°",  # { -> °
    0x7C: "ñ",  # | -> ñ
    0x7D: "ç",  # } -> ç
}

# Swedish NRC (Final character: 'H' or '7')
SWEDISH_NRC = {
    0x40: "É",  # @ -> É
    0x5B: "Ä",  # [ -> Ä
    0x5C: "Ö",  # \ -> Ö
    0x5D: "Å",  # ] -> Å
    0x5E: "Ü",  # ^ -> Ü
    0x60: "é",  # ` -> é
    0x7B: "ä",  # { -> ä
    0x7C: "ö",  # | -> ö
    0x7D: "å",  # } -> å
    0x7E: "ü",  # ~ -> ü
}

# Swiss NRC (Final character: '=')
SWISS_NRC = {
    0x23: "ù",  # # -> ù
    0x40: "à",  # @ -> à
    0x5B: "é",  # [ -> é
    0x5C: "ç",  # \ -> ç
    0x5D: "ê",  # ] -> ê
    0x5E: "î",  # ^ -> î
    0x5F: "è",  # _ -> è
    0x60: "ô",  # ` -> ô
    0x7B: "ä",  # { -> ä
    0x7C: "ö",  # | -> ö
    0x7D: "ü",  # } -> ü
    0x7E: "û",  # ~ -> û
}

# ============================================================================
# MASTER LOOKUP TABLE
# ============================================================================

CHARSET_MAP: dict[str, dict[int, str]] = {
    "B": US_ASCII,
    "A": UK_ASCII,
    "0": DEC_GRAPHICS,
    "<": DEC_SUPPLEMENTAL,
    "4": DUTCH_NRC,
    "5": FINNISH_NRC,
    "C": FINNISH_NRC,
    "R": FRENCH_NRC,
    "Q": FRENCH_CANADIAN_NRC,
    "K": GERMAN_NRC,
    "Y": ITALIAN_NRC,
    "E": NORWEGIAN_DANISH_NRC,
    "6": NORWEGIAN_DANISH_NRC,
    "Z": SPANISH_NRC,
    "H": SWEDISH_NRC,
    "7": SWEDISH_NRC,
    "=": SWISS_NRC,
}

CHARSET_NAMES = {
    "B": "US ASCII",
    "A": "UK ASCII",
    "0": "DEC Special Graphics",
    "<": "DEC Supplemental Graphics",
    "4": "Dutch NRC",
    "5": "Finnish NRC",
    "C": "Finnish NRC",
    "R": "French NRC",
    "Q": "French Canadian NRC",
    "K": "German NRC",
    "Y": "Italian NRC",
    "E": "Norwegian/Danish NRC",
    "6": "Norwegian/Danish NRC",
    "Z": "Spanish NRC",
    "H": "Swedish NRC",
    "7": "Swedish NRC",
    "=": "Swiss NRC",
}
