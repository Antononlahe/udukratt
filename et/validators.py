import datetime

W1 = (1, 2, 3, 4, 5, 6, 7, 8, 9, 1)
W2 = (3, 4, 5, 6, 7, 8, 9, 1, 2, 3)
CENTURY = {1: 1800, 2: 1800, 3: 1900, 4: 1900, 5: 2000, 6: 2000, 7: 2100, 8: 2100}


def luhn(digits: str) -> bool:
    total, double = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        double = not double
    return total % 10 == 0


def isikukood_check_digit(first10: str) -> int:
    for weights in (W1, W2):
        r = sum(int(d) * w for d, w in zip(first10, weights)) % 11
        if r < 10:
            return r
    return 0


def isikukood_date(code: str):
    g = int(code[0])
    if g not in CENTURY:
        return None
    try:
        return datetime.date(CENTURY[g] + int(code[1:3]), int(code[3:5]), int(code[5:7]))
    except ValueError:
        return None


def is_valid_isikukood(code: str) -> bool:
    return (
        len(code) == 11
        and code.isdigit()
        and isikukood_date(code) is not None
        and isikukood_check_digit(code[:10]) == int(code[10])
    )


def is_valid_registrikood(code: str) -> bool:
    return len(code) == 8 and code.isdigit() and code[0] in "189" and isikukood_check_digit(code[:7]) == int(code[7])


def is_valid_iban(value: str) -> bool:
    s = value.replace(" ", "").upper()
    if len(s) < 15 or len(s) > 34 or not s[:2].isalpha() or not s[2:4].isdigit() or not s.isalnum():
        return False
    if s.startswith("EE") and len(s) != 20:
        return False
    moved = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in moved)) % 97 == 1
