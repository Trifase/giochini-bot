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


def wordle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Wordle"
    first_line = lines[0].split()
    result["day"] = first_line[1]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = int(time.time())
    return result


def worldle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Worldle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = int(time.time())
    stars = text.count(b"\xe2\xad\x90".decode("utf-8"))
    cityscape = text.count(b"\xf0\x9f\x8f\x99".decode("utf-8"))
    coin = text.count(b"\xf0\x9f\xaa\x99".decode("utf-8"))
    result["stars"] = stars + cityscape + coin
    return result


def parole(text: str) -> dict:
    # This is for https://pietroppeter.github.io/wordle-it/
    result = {}
    lines = text.splitlines()
    result["name"] = "Parole"
    first_line = lines[0].split()
    result["day"] = first_line[1][2:]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = int(time.time())
    return result


def parole2(text: str) -> dict:
    # This is for https://par-le.github.io/gioco/
    result = {}
    lines = text.splitlines()
    result["name"] = "Parole"
    first_line = lines[0].split()
    result["day"] = first_line[1]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = int(time.time())
    return result


def contexto(text: str) -> dict:
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
    result["timestamp"] = int(time.time())
    return result


def tradle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Tradle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = int(time.time())
    return result


def guessthegame(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "GuessTheGame"
    result["timestamp"] = int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    punteggio = lines[2].replace(" ", "")
    if "🟩" not in punteggio:
        result["tries"] = "X"
    else:
        result["tries"] = str(punteggio.index("🟩"))
    return result


def globle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Globle"
    result["timestamp"] = int(time.time())
    # Globle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("Globle", lines[0])
    for line in lines:
        if "=" in line:
            result["tries"] = line.split("=")[-1][1:]
    return result


def flagle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Flagle"
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = int(time.time())
    return result


def wheretaken(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "WhereTaken"
    first_line = lines[0].split()
    result["day"] = first_line[2][1:]
    result["tries"] = first_line[3].split("/")[0]
    result["timestamp"] = int(time.time())
    # This is because emojis have hidden personalities
    result["stars"] = text.count(b"\xe2\xad\x90".decode("utf-8"))
    return result


def waffle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Waffle"
    first_line = lines[0].split()
    result["day"] = first_line[0].replace("#waffle", "")
    punti = first_line[1].split("/")[0]
    result["tries"] = 15 - int(punti) if punti != "X" else "X"
    result["timestamp"] = int(time.time())
    # This is because emojis have hidden personalities
    result["stars"] = text.count(b"\xe2\xad\x90".decode("utf-8"))
    return result


def cloudle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Cloudle"
    first_line = lines[0].split()
    # Cloudle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("Cloudle", datetime.date.today())
    result["tries"] = first_line[-1].split("/")[0]
    result["timestamp"] = int(time.time())
    return result


def highfive(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "HighFive"
    result["timestamp"] = int(time.time())
    # HighFive doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = get_day_from_date("HighFive", lines[-1])
    result["tries"] = str(0 - int(lines[0].split()[3]))
    return result


def plotwords(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Plotwords"
    result["timestamp"] = int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    tries, clues = lines[1].split()[-1].split("/")
    result["tries"] = tries if tries != clues else "X"
    return result


def framed(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Framed"
    result["timestamp"] = int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    punteggio = lines[1].replace(" ", "")
    if "🟩" not in punteggio:
        result["tries"] = "X"
    else:
        result["tries"] = str(punteggio.index("🟩"))
    return result


def timeguesser(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "TimeGuesser"
    result["timestamp"] = int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    result["tries"] = 50_000 - int(first_line[2].split("/")[0].replace(",", ""))
    return result


def moviedle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Moviedle"
    result["timestamp"] = int(time.time())
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


def murdle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Murdle"
    result["timestamp"] = int(time.time())
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


def connections(text: str) -> dict:
    result = {}
    lines = text.splitlines()

    result["name"] = "Connections"
    result["timestamp"] = int(time.time())
    result["day"] = lines[1].split()[-1][1:]

    points = lines[2:]
    if is_connection_completed(points):
        result["tries"] = len(points) - 3
    else:
        result["tries"] = "X"
    return result


def nerdle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Nerdle"
    first_line = lines[0].split()
    result["day"] = first_line[1]
    result["tries"] = first_line[2].split("/")[0]
    result["timestamp"] = int(time.time())
    return result


def picsey(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    date = lines[0].split()[-1]
    result["name"] = "Picsey"
    result["day"] = get_day_from_date("Picsey", date)
    points = lines[2].split("p/")[0]
    # Picsey uses positive poits, from 0 to 100. We as usual save 100-n and then revert it when printing the results.
    result["tries"] = 100 - int(points)
    result["timestamp"] = int(time.time())
    if int(points) == 0:
        result["tries"] = "X"
    return result


def squareword(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    first_line = lines[0].split()
    result["name"] = "Squareword"
    result["timestamp"] = int(time.time())
    result["day"] = first_line[1][:-1]
    result["tries"] = first_line[2]
    return result


def metazooa(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Metazooa"
    result["timestamp"] = int(time.time())
    # metazoa doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = lines[0].split()[2][1:]
    if "stumped" in lines[1]:
        result["tries"] = "X"
    else:
        result["tries"] = lines[1].split()[-2]
    return result

def metaflora(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Metaflora"
    result["timestamp"] = int(time.time())
    # metazoa doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result["day"] = lines[0].split()[2][1:]
    if "stumped" in lines[1]:
        result["tries"] = "X"
    else:
        result["tries"] = lines[1].split()[-2]
    return result

def angle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Angle"
    result["timestamp"] = int(time.time())
    result["day"] = lines[0].split()[1][1:]
    points = lines[0].split()[-1].split("/")[0]
    if points == 'X':
        result["tries"] = 'X'
    else:
        result["tries"] = points
    return result

def tempoindovinr(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "TempoIndovinr"
    result["timestamp"] = int(time.time())
    result["day"] = lines[0].split()[-1]
    points = lines[1].split()[2].split('/')[0]
    result["tries"] = 1_000 - int(points)
    return result

def travle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result["name"] = "Travle"
    result["timestamp"] = int(time.time())
    first_line = lines[0].split()
    result["day"] = first_line[1][1:]
    tries = first_line[2].split("/")[0][1:]
    if tries == '?':
        result["tries"] = 'X'
    else:
        hints = 0
        if len(first_line) > 3:
            hints = first_line[3][1:]
        result["tries"] = int(int(tries) + ((int(hints) * (int(hints) + 1)) / 2)) # +1, +2, +3 (triangulars)
    return result

