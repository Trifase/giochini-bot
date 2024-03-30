import datetime
import time

from utils import get_day_from_date, is_connection_completed, time_from_emoji

# Every parser in this file will parse a text-result from a website and produce a dictionary with the following characteristics:
# dict = {
#     'name': 'Wordle'      -> a string for the game name
#     'day': '356'          -> a string with the game number, will be turned into a int when necessary
#     'tries': '3'          -> a string for the main 'points' of the game, usually the lesser the better. X for a fail.
#     'timestamp': 12345678 -> Unix timestamp. Int.
#     'stars': 3            -> some games have addictional stars or something if you do optional challenges. Int or None.
# }


def wordle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Wordle"
    first_line = lines[0].split()
    result["day"] = (
        first_line[1].replace(".", "").replace(",", "")
    )  # Wordle ti odio, chi cazzo scrive 1000 come "1.000" o "1,000"
    result["tries"] = first_line[-1].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def worldle(text: str, timestamp: int = None) -> dict:
    # https://emojiterra.com/speaking-head/
    # https://www.utf8-chartable.de/unicode-utf8-table.pl
    result = {}
    lines = text.splitlines()
    result["name"] = "Worldle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = first_line[3].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    bussola = text.count(b"\xf0\x9f\xa7\xad".decode("utf-8"))       # 🧭
    stars = text.count(b"\xe2\xad\x90".decode("utf-8"))             # ⭐️
    flag = text.count(b"\xf0\x9f\x9a\xa9".decode("utf-8"))          # 🚩
    abc = text.count(b"\xf0\x9f\x94\xa4".decode("utf-8"))           # 🔤
    language = text.count(b"\xf0\x9f\x97\xa3".decode("utf-8"))      # 🗣
    population = text.count(b"\xf0\x9f\x91\xab".decode("utf-8"))    # 👫
    coin = text.count(b"\xf0\x9f\xaa\x99".decode("utf-8"))          # 🪙
    cityscape = text.count(b"\xf0\x9f\x8f\x99".decode("utf-8"))     # 🏙
    area = text.count(b"\xf0\x9f\x93\x90".decode("utf-8"))          # 📐

    result["stars"] = bussola + stars + flag + abc + language + population + coin + cityscape + area
    return result


def parole(text: str, timestamp: int = None) -> dict:
    # This is for https://pietroppeter.github.io/wordle-it/
    result = {}
    lines = text.splitlines()
    result["name"] = "Parole"
    first_line = lines[0].split()
    result["day"] = first_line[1][2:]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def parole2(text: str, timestamp: int = None) -> dict:
    # This is for https://par-le.github.io/gioco/
    result = {}
    lines = text.splitlines()
    result["name"] = "Parole"
    first_line = lines[0].split()
    result["day"] = first_line[1]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def contexto(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Contexto"
    first_line = lines[0].split()
    result["day"] = first_line[3][1:]
    if first_line[4] == "but":
        result["tries"] = "X"
    elif first_line[-1] == "hints.":
        tips = int(first_line[-2])
        index = first_line.index("guesses")
        result["tries"] = int(first_line[index - 1]) + (tips * 15)
    else:
        result["tries"] = first_line[-2]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def tradle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Tradle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def guessthegame(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "GuessTheGame"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    punteggio = lines[2].replace(" ", "")
    if "🟩" not in punteggio:
        result["tries"] = "X"
    else:
        result["tries"] = str(punteggio.index("🟩"))
    return result


def globle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Globle"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    # Globle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("Globle", lines[0])
    for line in lines:
        if "=" in line:
            result["tries"] = line.split("=")[-1][1:]
    return result


def flagle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Flagle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = first_line[3].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def wheretaken(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "WhereTaken"
    first_line = lines[0].split()
    result["day"] = first_line[2][1:]
    result["tries"] = first_line[4].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    # This is because emojis have hidden personalities
    result["stars"] = text.count(b"\xe2\xad\x90".decode("utf-8"))
    return result


def waffle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Waffle"
    first_line = lines[0].split()
    result["day"] = first_line[0].replace("#waffle", "")
    punti = first_line[1].split("/")[0]
    result["tries"] = 15 - int(punti) if punti != "X" else "X"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    # This is because emojis have hidden personalities
    result["stars"] = text.count(b"\xe2\xad\x90".decode("utf-8"))
    return result


def cloudle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Cloudle"
    first_line = lines[0].split()
    # Cloudle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("Cloudle", datetime.date.today())
    result["tries"] = first_line[-1].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def highfive(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "HighFive"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    # HighFive doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("HighFive", lines[-1])
    result["tries"] = str(0 - int(lines[0].split()[3]))
    return result


def plotwords(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Plotwords"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    tries, clues = lines[1].split()[-1].split("/")
    result["tries"] = tries if tries != clues else "X"
    return result


def framed(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Framed"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    punteggio = lines[1].replace(" ", "")
    if "🟩" not in punteggio:
        result["tries"] = "X"
    else:
        result["tries"] = str(punteggio.index("🟩"))
    return result


def timeguesser(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "TimeGuesser"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = 50_000 - int(first_line[2].split("/")[0].replace(",", ""))
    return result


def moviedle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Moviedle"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    point_line = lines[2][3:]
    # Moviedle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("Moviedle", first_line[-1])
    punteggio = point_line.replace(" ", "")
    punteggio_bonificato = ""
    # Moviedle uses black-magic squares that inject empty invisible spaces fugging up the count. We remove them with a whitelisted chars list.
    for char in punteggio:
        if char in ["⬛", "🟥", "🟩", "⬜"]:
            punteggio_bonificato += char

    if "🟩" not in punteggio_bonificato:
        result["tries"] = "X"
    else:
        result["tries"] = str(punteggio_bonificato.index("🟩") + 1)
    return result


def murdle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Murdle"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    day = lines[1].split()[-1]
    # Murdle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("Murdle", day)
    points_line = lines[4]
    punteggio = points_line.split()[-1]
    if "❌" in points_line:
        result["tries"] = "X"
    else:
        result["tries"] = str(time_from_emoji(punteggio))
    return result


def connections(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()

    result["name"] = "Connections"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    result["day"] = lines[1].split()[-1][1:]

    points = lines[2:]
    if is_connection_completed(points):
        result["tries"] = len(points) - 3
    else:
        result["tries"] = "X"
    return result


def nerdle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Nerdle"
    first_line = lines[0].split()
    result["day"] = first_line[1]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def picsey(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    date = lines[0].split()[-1]
    result["name"] = "Picsey"
    result["day"] = get_day_from_date("Picsey", date)
    points = lines[2].split("p/")[0]
    # Picsey uses positive poits, from 0 to 100. We as usual save 100-n and then revert it when printing the results.
    result["tries"] = 100 - int(points)
    result["timestamp"] = timestamp if timestamp else int(time.time())
    if int(points) == 0:
        result["tries"] = "X"
    return result


def squareword(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    first_line = lines[0].split()
    result["name"] = "Squareword"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    result["day"] = first_line[1][:-1]
    result["tries"] = first_line[2]
    return result


def metazooa(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Metazooa"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    # metazoa doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = lines[0].split()[2][1:]
    if "stumped" in lines[1]:
        result["tries"] = "X"
    else:
        result["tries"] = lines[1].split()[-2]
    return result


def metaflora(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Metaflora"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    # metazoa doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = lines[0].split()[2][1:]
    if "stumped" in lines[1]:
        result["tries"] = "X"
    else:
        result["tries"] = lines[1].split()[-2]
    return result


def angle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Angle"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    result["day"] = lines[0].split()[1][1:]
    points = lines[0].split()[-1].split("/")[0]
    if points == "X":
        result["tries"] = "X"
    else:
        result["tries"] = points
    return result


def tempoindovinr(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "TempoIndovinr"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    result["day"] = lines[0].split()[-1]
    points = lines[1].split()[2].split("/")[0]
    result["tries"] = 1_000 - int(points)
    return result


def travle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Travle"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    tries = first_line[2].split("/")[0][1:]
    if tries == "?":
        result["tries"] = "X"
    else:
        hints = 0
        if len(first_line) > 3:
            hints = first_line[3][1:]
        result["tries"] = int(int(tries) + ((int(hints) * (int(hints) + 1)) / 2))  # +1, +2, +3 (triangulars)
    return result


def travle_ita(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "TravleITA"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    tries = first_line[2].split("/")[0][1:]
    if tries == "?":
        result["tries"] = "X"
    else:
        hints = 0
        if len(first_line) > 3:
            hints = first_line[3][1:]
        result["tries"] = int(int(tries) + ((int(hints) * (int(hints) + 1)) / 2))  # +1, +2, +3 (triangulars)
    return result


def nerdlecross(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "NerdleCross"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[-1][1:]
    points = lines[-1].split(":")[-1].split("/")[0].strip()

    # Nerdle Cross uses positive poits, from 0 to 6. We as usual save 6-n and then revert it when printing the results.
    result["tries"] = 6 - int(points)
    if result["tries"] == 6:
        result["tries"] = "X"
    return result


def dominofit(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "DominoFit"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[-2][1:]
    points = lines[-1]
    str_points = time_from_emoji(points.strip())
    result["tries"] = int(str_points.strip())
    return result


def bandle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Bandle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    punti = first_line[2].split("/")[0]
    if punti == "x":
        result["tries"] = "X"
    else:
        result["tries"] = punti
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def chrono(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Chrono"
    first_line = lines[0].split()
    result["day"] = first_line[2][1:]
    punti = first_line[0]

    if punti == "😬":
        result["tries"] = "X"
    elif punti == "🥉":
        result["tries"] = 3
    elif punti == "🥈":
        result["tries"] = 2
    elif punti == "🥇":
        result["tries"] = 1
    if result['tries'] in [1, 2, 3] and len(lines) >= 4:
        for line in lines:
            if line.startswith('⏱'):
                result["stars"] = 10_000 - float(line.split(':')[-1].strip())
                break
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def stepdle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Stepdle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    count = lines[-1].count("🟩")
    won = count == 7
    if won:
        punti = lines[1].split()[0].split("/")[0]
        result["tries"] = punti
    else:
        result["tries"] = "X"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def colorfle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Colorfle"
    first_line = lines[0].split()
    result["day"] = first_line[1]
    punti = first_line[2].split("/")[0]
    if punti == "X":
        result["tries"] = "X"
    else:
        result["tries"] = punti
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def rotaboxes(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Rotaboxes"
    result["day"] = lines[3].split("/")[-1]
    punti = lines[1]
    punti = punti.split("clicks: ")[-1]
    max_points = int(punti.split("/")[-1])
    clicks = int(punti.split("/")[0])
    result["tries"] = clicks - max_points
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def polygonle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Polygonle"
    first_line = lines[0].split()
    result["day"] = first_line[1]
    punti = first_line[2].split("/")[0]
    if punti == "X":
        result["tries"] = "X"

    elif punti == "🎯":
        result["tries"] = "1"

    else:
        result["tries"] = punti

    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def chronophoto(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Chronophoto"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = get_day_from_date("Chronophoto", first_line[-1])
    points = first_line[5]
    result["tries"] = 5_000 - int(points)
    if result["tries"] == 0:
        result["tries"] = "X"
    return result


def foodguessr(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "FoodGuessr"
    # Foodguessr doesn't have a #day, so we parse the date and get our own numeration (Mar 9, 2024 -> 200)
    result["day"] = get_day_from_date("FoodGuessr", datetime.date.today())
    points = lines[4].split()[2].replace(",", "").replace(".", "")
    result["tries"] = 15_000 - int(points)
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def spellcheck(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    first_line = lines[0].split()
    result["name"] = "Spellcheck"
    result["day"] = first_line[1][1:]
    result["tries"] = 15 - text.count("🟩")
    result["timestamp"] = timestamp if timestamp else int(time.time())
    return result


def spotle(text: str, timestamp: int = None) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Spotle"
    result["timestamp"] = timestamp if timestamp else int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:-1]
    punteggio = lines[2].replace(" ", "")
    punteggio_bonificato = ''
    for char in punteggio:
        if char in ["⬛", "🟥", "🟩", "⬜"]:
            punteggio_bonificato += char
    if "🟩" not in punteggio or "❌" in punteggio:
        result["tries"] = "X"
    else:
        result["tries"] = str(punteggio_bonificato.index("🟩") + 1)
    return result