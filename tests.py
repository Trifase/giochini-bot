from config import Punteggio
from utils import Giocata, Classifica

from collections import defaultdict

query1 = [
    Punteggio(day="200", name="NFLXdle", timestamp=10, tries="1", extra=1, user_id=111111111, user_name="Trifase"),
    Punteggio(day="200", name="NFLXdle", timestamp=8, tries="9999999", user_id=555555555, user_name="Eva"),       # lost play
    Punteggio(day="200", name="NFLXdle", timestamp=10, tries="1", extra=1, user_id=222222222, user_name="Sofia"),      # same score as Trifase
    Punteggio(day="200", name="NFLXdle", timestamp=12, tries="2", user_id=333333333, user_name="Charlie"),
    Punteggio(day="200", name="NFLXdle", timestamp=10, tries="1", extra=0, user_id=22223333, user_name="Jacopo"),      # same tries as trifase but less extra
    Punteggio(day="200", name="NFLXdle", timestamp=8, tries="4", user_id=555555555, user_name="Juan"),
    Punteggio(day="200", name="NFLXdle", timestamp=15, tries="3", user_id=444444444, user_name="Davide"),
]

query2 = [
    Punteggio(day="144", name="Gioco2", timestamp=8, tries="4", user_id=555555555, user_name="Juan"),       # lost play
    Punteggio(day="144", name="Gioco2", timestamp=15, tries="3", user_id=444444444, user_name="Davide"),
    Punteggio(day="144", name="Gioco2", timestamp=10, tries="1", user_id=111111111, user_name="Trifase"),
    Punteggio(day="144", name="Gioco2", timestamp=12, tries="2", user_id=333333333, user_name="Charlie"),
    Punteggio(day="144", name="Gioco2", timestamp=10, tries="1", user_id=222222222, user_name="Sofia"),      # same score as Trifase
    Punteggio(day="144", name="Gioco2", timestamp=10, tries="1", user_id=22223333, user_name="Jacopo"),      # same score as Trifase
    Punteggio(day="144", name="Gioco2", timestamp=8, tries="3", user_id=555555555, user_name="Eva"),
]

c1 = Classifica(game="NFLXdle", day="200", date=None, emoji="🏈", header="Classifica NFLXdle 200", last="", aggregate=False)
c2 = Classifica(game="Gioco2", day="144", date=None, emoji="🎲", header="Classifica Gioco2 144", last="", aggregate=False)
c1.giocate = [Giocata(user_id=g.user_id, user_name=g.user_name, tries=g.tries, game="NFLXdle", extra=g.extra if g.extra else 0) for g in query1]

c2.giocate = [Giocata(user_id=g.user_id, user_name=g.user_name, tries=g.tries, game="Gioco2", extra=g.extra if g.extra else 0) for g in query2]

print(c1.to_string())
c1.order_and_position()
print(c1.to_string())
c1.assign_stars('no_limit_with_lost')
print(c1.to_string())

# c1_stars = c1.get_stars()
# print(c1_stars.to_string())

# c2.order_and_position()
# print(c2.to_string())
# c2.assign_stars('no_limit_with_lost')
# c2_stars = c2.get_stars()
# print(c2_stars.to_string())

# print('TOTALE')
# c3 = c1_stars + c2_stars
# print(c3.to_string())


# import pprint
# # pprint.pp(points)