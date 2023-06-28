
from utils import get_day_from_date
import datetime
import time

def wordle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Wordle'
    first_line = lines[0].split()
    result['day'] = first_line[1]
    result['tries'] = first_line[2].split('/')[0]
    result['timestamp'] = int(time.time())
    return result

def worldle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Worldle'
    first_line = lines[0].split()
    result['day'] = first_line[1][1:]
    result['tries'] = first_line[2].split('/')[0]
    result['timestamp'] = int(time.time())
    result['stars'] = text.count('⭐️') + text.count('🪙')
    return result

def parole(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Parole'
    first_line = lines[0].split()
    result['day'] = first_line[1][2:]
    result['tries'] = first_line[2].split('/')[0]
    result['timestamp'] = int(time.time())
    return result

def contexto(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Contexto'
    first_line = lines[0].split()
    result['day'] = first_line[3][1:]
    if first_line[4] == 'but':
        result['tries'] = 'X'
    elif first_line[-1] == 'tips.':
        tips = int(first_line[-2])
        index = first_line.index('guesses')
        result['tries'] = int(first_line[index - 1]) + (tips * 15)
    else:
        result['tries'] = first_line[-2]
    result['timestamp'] = int(time.time())
    return result

def tradle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Tradle'
    first_line = lines[0].split()
    result['day'] = first_line[1][1:]
    result['tries'] = first_line[2].split('/')[0]
    result['timestamp'] = int(time.time())
    return result

def guessthegame(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'GuessTheGame'
    result['timestamp'] = int(time.time())
    first_line = lines[0].split()
    result['day'] = first_line[1][1:]
    punteggio = lines[2].replace(' ', '')
    if '🟩' not in punteggio:
        result['tries'] = 'X'
    else:
        result['tries'] = str(punteggio.index('🟩'))
    return result

def globle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Globle'
    result['timestamp'] = int(time.time())
    # Globle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result['day'] = get_day_from_date('Globle', lines[0])
    for line in lines:
        if '=' in line:
            result['tries'] = line.split('=')[-1][1:]
    return result

def flagle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Flagle'
    first_line = lines[0].split()
    result['day'] = first_line[1][1:]
    result['tries'] = first_line[3].split('/')[0]
    result['timestamp'] = int(time.time())
    return result

def wheretaken(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'WhereTaken'
    first_line = lines[0].split()
    result['day'] = first_line[2][1:]
    result['tries'] = first_line[3].split('/')[0]
    result['timestamp'] = int(time.time())
    result['stars'] = text.count('⭐️')
    return result

def waffle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Waffle'
    first_line = lines[0].split()
    result['day'] = first_line[0].replace('#waffle', '')
    punti = first_line[1].split('/')[0]
    result['tries'] = 15 - int(punti) if punti != 'X' else 'X'
    result['timestamp'] = int(time.time())
    result['stars'] = text.count('⭐️')
    return result

def cloudle(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Cloudle'
    first_line = lines[0].split()
    # Cloudle doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result['day'] = get_day_from_date('Cloudle', datetime.date.today())
    result['tries'] = first_line[-1].split('/')[0]
    result['timestamp'] = int(time.time())
    return result

def highfive(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'HighFive'
    result['timestamp'] = int(time.time())
    # HighFive doesn't have a #day, so we parse the date and get our own numeration (Jun 23, 2023 -> 200)
    result['day'] = get_day_from_date('HighFive', lines[-1])
    result['tries'] = str(0-int(lines[0].split()[3]))
    return result

def plotwords(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Plotwords'
    result['timestamp'] = int(time.time())
    first_line = lines[0].split()
    result['day'] = first_line[1][1:]
    tries = lines[1].split()[-1].split('/')[0]
    result['tries'] = tries if tries != '13' else 'X'
    return result

def framed(text: str) -> dict:
    result = {}
    lines = text.splitlines()
    result['name'] = 'Framed'
    result['timestamp'] = int(time.time())
    first_line = lines[0].split()
    result['day'] = first_line[1][1:]
    punteggio = lines[1].replace(' ', '')
    if '🟩' not in punteggio:
        result['tries'] = 'X'
    else:
        result['tries'] = str(punteggio.index('🟩'))
    return result
