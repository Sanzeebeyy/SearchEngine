import unicodedata
from functools import lru_cache

QUOTE_MAP = str.maketrans({ # using str.maketrans() with .translate() later to replace string characters efficiently
    "\u2018" : "'",
    "\u2019" : "'",
    "\u201b" : "'",
    "\u02bc" : "'" # fancy apostrophes into simple one   
})

SPECIAL_LATIN = str.maketrans({ # same as apostrophes
    "ø": "o",    # Endsjø
    "ł": "l",    # Wałęsa
    "đ": "d",
    "æ": "ae",
    "œ": "oe",
    "ð": "d",
    "þ": "th",
    "ı": "i",    # dotless i
})

@lru_cache(maxsize= None) 

# lru_cache is being used since this is a expensive operation to perform so the result of previous operation can be stored in cache and used whenever necessary, max_sixe of cache is None (if it was something like 32, then 32 bit cache, replacement with LRU strategy) 

# identifying latin
def is_latin(ch):
    return ("LATIN" in unicodedata.name(ch, "")) # return "" if ch is unidentified

def strip_latin_accents(text): # we only strip latin's accent since in other language, the meaning changes with accent
    
    decomposed = unicodedata.normalize("NFD", text) # NFD decomposes text to letter and accent, (NFC le chai compose pani garxa after decompose)
    
    last_was_latin = False
    out = []
    
    for ch in decomposed:
        if unicodedata.combining(ch):
            if last_was_latin:
                continue
            out.append(ch)
        else:
            last_was_latin = is_latin(ch)
            out.append(ch)
    
    return "".join(out)

def normalize_text(text, fold_accents = True):
    
    if not text:
        return ""
    
    text = unicodedata.normalize("NFKC", text) # NFKC le chai lookalikes lai base form ma lera janxa
    text = text.casefold() # better lowercasing
    text = unicodedata.normalize("NFKC", text) # casefold can sometimes yk
    text = text.translate(QUOTE_MAP)
    
    if fold_accents:
        text = strip_latin_accents(text)
        text = text.translate(SPECIAL_LATIN)
        
    text = unicodedata.normalize("NFC", text) # to recompose the broken down letters
    
    
    return " ".join(text.split())


# test cases before trying normalization on real extracted jsonl

if __name__ == "__main__":
    tests = {
        "Dag Øistein Endsjø": "dag oistein endsjo",
        "Wałęsa": "walesa",
        "Ján Figeľ": "jan figel",
        "Python’s": "python's",
        "Chambers’s Twentieth": "chambers's twentieth",
        "Российские": "российские",
        "Straße": "strasse",
        "\ufb01nal": "final",
        "  too   many \n spaces ": "too many spaces",
    }
 
    all_ok = True
    for raw, expected in tests.items():
        got = normalize_text(raw)
        ok = got == expected
        all_ok = all_ok and ok
        print("OK  " if ok else "FAIL", repr(raw), "->", repr(got))
 
    print("\nAll tests passed." if all_ok else "\nSome tests FAILED.")