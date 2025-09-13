from config import Punteggio
from utils import Giocata, Classifica, print_progressbar

# from collections import defaultdict

query1 = [
    Punteggio(day="200", name="Connections", timestamp=10, tries="1", extra=1, user_id=111111111, user_name="Davide"),
    Punteggio(day="200", name="Connections", timestamp=8, tries="1", extra=1, user_id=555555555, user_name="Francesco"),       # lost play
    Punteggio(day="200", name="Connections", timestamp=10, tries="1", extra=1, user_id=222222222, user_name="Sofia"),      # same score as Trifase
    Punteggio(day="200", name="Connections", timestamp=12, tries="1", extra=1, user_id=333333333, user_name="Lara"),
    Punteggio(day="200", name="Connections", timestamp=12, tries="2", extra=1, user_id=55443322, user_name="Lara2"),
]

c1 = Classifica(game="Connections", day="200", date=None, emoji="🏈", header="Classifica Connections 200", last="", aggregate=False)
c1.giocate = [Giocata(user_id=g.user_id, user_name=g.user_name, tries=g.tries, game="Connections", extra=g.extra if g.extra else 0) for g in query1]

print(c1.to_string())
c1.order_and_position()
print(c1.to_string())
c1.assign_stars('default')
print(c1.to_string())
c2 = Classifica(game="Connections", day="200", date=None, emoji="🏈", header="Classifica Connections 200", last="", aggregate=False)
c2.giocate = [Giocata(user_id=g.user_id, user_name=g.user_name, tries=g.tries, game="Connections", extra=g.extra if g.extra else 0) for g in query1]
print('=========================')
print(c2.to_string())
c2.order_and_position()
print(c2.to_string())
c2.assign_stars('default')
print(c2.to_string())

# # c1_stars = c1.get_stars_list()
# # print(c1_stars)

# giochini_curr = 35
# giochini_tot = 72

# perc = round((giochini_curr/giochini_tot) * 100)
# print(perc)
# print(print_progressbar(perc))
# print()


# # c1_stars = c1.get_stars()
# # print(c1_stars.to_string())

# # c2.order_and_position()
# # print(c2.to_string())
# # c2.assign_stars('no_limit_with_lost')
# # c2_stars = c2.get_stars()
# # print(c2_stars.to_string())

# # print('TOTALE')
# # c3 = c1_stars + c2_stars
# # print(c3.to_string())


# # import pprint
# # # pprint.pp(points)