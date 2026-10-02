# 🎮 Giochini Bot

**Giochini Bot** è un bot Telegram pensato per gruppi di amici appassionati di puzzle game giornalieri (Wordle, Connections, Travle, Framed, e decine di altri).

Il bot analizza automaticamente i messaggi contenenti i risultati condivisi dai vari giochi, compila classifiche in tempo reale, tiene traccia dei punteggi personali e di gruppo, assegna medaglie quotidiane e aggiorna un medagliere mensile e all-time!

---

## 🕹️ Come Funziona

1. **Gioca**: completa il tuo puzzle giornaliero sul sito web del gioco.
2. **Condividi**: premi il tasto *Share* / *Condividi* sul sito del gioco per copiare il testo del risultato negli appunti.
3. **Incolla nel gruppo**: invia il messaggio nella chat Telegram.
4. **Riconoscimento automatico**:
   - Il bot riconosce istantaneamente il gioco, il giorno e il tuo punteggio.
   - Aggiunge una reaction al messaggio e aggiorna la barra di progresso giornaliera (es. `⭐️ ███████░░░░ 7/20`).
   - Se completi tutti i tuoi giochi preferiti della giornata, riceverai una celebrazione speciale! 🎉

> 💡 **Scorciatoie veloci**: vuoi giocare al volo? Scrivi in chat `/<nomegioco>` (ad esempio `/wordle`, `/travle`, `/connections`, `/framed`) e il bot invierà il link diretto alla partita odierna!

---

## 🏆 Punteggi e Medaglie

- **Classifica di gioco**: ogni gioco ha la sua classifica giornaliera basata sul numero di tentativi (o tempo/punti a seconda della tipologia).
- **Riassunto serale (ore 00:10)**: ogni notte il bot calcola i punteggi complessivi della giornata assegnando stelle ⭐ in base alle posizioni conquistate in ciascun gioco.
- **Medagliere (🥇 🥈 🥉)**: i primi tre classificati del giorno vincono rispettivamente medaglia d'oro, argento e bronzo, che confluiscono nei medaglieri mensili e all-time.
- **Risveglio giochi inattivi**: se un gioco non viene giocato per oltre 30 giorni entra in standby per mantenere pulita la lista dei suggerimenti. Non appena qualcuno invia un nuovo risultato, il gioco si risveglia automaticamente tornando attivo per tutti! ✨

---

## 📋 Comandi Disponibili

### 📊 Giornata & Personale
| Comando | Alias | Descrizione |
|---|---|---|
| `/myday` | `/mytoday`, `/my`, `/today`, `/daily` | Mostra quali giochi ti mancano ancora da completare oggi |
| `/myscore` | `/score` | Mostra i tuoi punteggi e le tue posizioni nella giornata odierna |
| `/favs` | `/fav` | Gestione interattiva dei tuoi giochi preferiti (per personalizzare `/myday` e la barra di avanzamento) |
| `/mystats` | `/mystat`, `/statistiche` | Mostra le tue statistiche complete (partite giocate, vittorie, streak) |

### 🏅 Classifiche & Medagliere
| Comando | Alias | Descrizione |
|---|---|---|
| `/classifica` | `/c` | Mostra la panoramica completa con le classifiche di tutti i giochi di oggi |
| `/c [gioco]` | — | Mostra la classifica odierna di un singolo gioco (es. `/c wordle`) |
| `/dailyranking` | `/simuladaily` | Simula la classifica provvisoria a punti (stelle ⭐) della giornata in corso |
| `/medaglie` | — | Mostra il medagliere del mese corrente |
| `/top` | — | Classifica generale all-time per punti totali accumulati |
| `/top_medaglie` | — | Medagliere olimpico all-time (oro, argento, bronzo) |

### 📈 Gruppo & Informazioni
| Comando | Alias | Descrizione |
|---|---|---|
| `/groupstats` | `/gstats`, `/statsgroup` | Statistiche aggregate di tutto il gruppo |
| `/weekstat` | `/weekstats`, `/wstat`, `/week` | Report dettagliato dell'attività degli ultimi 7 giorni |
| `/topgames` | — | Classifica dei giochi più popolari e giocati nel gruppo |
| `/list` | `/lista` | Elenco di tutti i giochi supportati con link e categorie |
| `/help` | — | Mostra la guida sintetica ai comandi |

---

## 🎲 Elenco dei Giochi Supportati

Il bot supporta **99 giochi**, suddivisi in 8 categorie:

### 🌍 Bandiere e geografia (13)
- 🌍 [Borderline](https://borderline.world)
- 🌐 [Countryle](https://countryle.com)
- 🏁 [Flagle](https://www.flagle.io)
- 🏳️‍🌈 [Flags](https://flagsgame.net)
- 🌎 [Geogrid](https://geogridgame.com)
- 🌍 [Geozee](https://geozee.earth)
- 🌍 [Globle](https://globle-game.com)
- 🚢 [Tradle](https://games.oec.world/en/tradle)
- 🧭 [Travle](https://travle.earth)
- 👢 [TravleITA](https://travle.earth/ita)
- 🔎 [Unzoomed](https://unzoomed.com)
- 📸 [WhereTaken](http://wheretaken.teuteuf.fr)
- 🗺️ [Worldle](https://worldle.teuteuf.fr)

### 🎬 Cinema (8)
- 🎬 [Flickle](https://flickle.app)
- 🎞 [Framed](https://framed.wtf)
- 🎞 [Framed One Frame](https://framed.wtf/one-frame)
- 📽 [GuessTheMovie](https://GuessTheMovie.Name)
- 🎥 [Moviedle](https://likewise.com/games/moviedle)
- 📺 [NFLXdle](https://likewise.com/games/nflxdle)
- 🍿 [Posterdle](https://likewise.com/games/posterdle)
- 🎦 [Titleshot](https://framed.wtf/titleshot)

### 🔤 Giochi di parole (27)
- 🈁 [BracketCity](https://www.theatlantic.com/games/bracket-city/)
- 🔀 [Connections](https://www.nytimes.com/games/connections)
- 🔄 [Contexto](https://contexto.me)
- 🪜 [Crossclimb](https://lnkd.in/crossclimb)
- 🔎 [Decipher](https://decipher.wtf)
- 🛑 [DontWordle](https://dontwordle.com)
- 🔃 [Flipple](https://flipple.clevergoat.com)
- 🦊 [FoxiMax](https://foximax.com)
- 🧩 [Gisnep](https://gisnep.com)
- 🔡 [GuessThePhrase](https://GuessThePhrase.xyz)
- 🔗 [Linxicon](https://linxicon.com)
- 🧩 [MinuteCryptic](https://www.minutecryptic.com/)
- 🇮🇹 [Parole](https://par-le.github.io/gioco/)
- 🌥️ [Pedantle](https://pedantle.certitudes.org)
- 🔷 [Polygonle](https://www.polygonle.com)
- 📝 [Redattolo](https://redattolo.vercel.app)
- ⤴️ [Reversle](https://reversle.net/)
- 👂 [Spellcheck](https://spellcheck.xyz)
- 🔠 [Squareword](https://squareword.org)
- 🗼 [Stepdle](https://www.stepdle.com)
- 💡 [Strands](https://www.nytimes.com/games/strands)
- #️⃣ [Thirdle](https://thirdle.org/)
- 🧇 [Waffle](https://wafflegame.net/daily)
- 🌀 [Wend](https://lnkd.in/wend)
- 🦄 [WordGrid](https://wordgrid.clevergoat.com/)
- 🔤 [WordPeaks](https://wordpeaks.com)
- 🆒 [Wordle](https://www.nytimes.com/games/wordle/index.html)

### 🧩 Logica e matematica (15)
- 🔎 [CluesBySam](https://cluesbysam.com)
- 🃏 [DominoFit](https://dominofit.isotropic.us)
- 🐴 [EncloseHorse](https://enclose.horse)
- 🔪 [Murdle](https://murdle.com)
- 🤓 [Nerdle](https://nerdlegame.com)
- 🧮 [NerdleCross](https://nerdlegame.com/crossnerdle)
- ➗ [Numble](https://numble.wtf)
- 🧶 [Patches](https://lnkd.in/patches)
- 👑 [Queens](https://lnkd.in/queens)
- 👑 [QueensUltimateMax](https://queensultimate.com/max)
- 👑 [QueensUltimateMini](https://queensultimate.com)
- 🟡 [Spots](https://spots.wtf)
- 🧩 [Sumplete](https://sumplete.com/)
- 🌗 [Tango](https://lnkd.in/tango)
- ⚡ [Zip](https://lnkd.in/zip)

### 🎲 Miscellanea (14)
- 🐟 [Catfishing](https://catfishing.net)
- 📄 [Disorderly](https://playdisorderly.com/)
- 🍝 [FoodGuessr](https://foodguessr.com)
- 🛡️ [GuessTheFootballClub](https://playfootball.games/guess-the-football-club/)
- 🎮 [GuessTheGame](https://guessthe.game)
- 🏠 [GuessTheHouse](https://guessthe.house)
- ® [GuessTheLogo](https://guessthelogo.wtf)
- 💯 [Hundo](https://hundo.today)
- 🦐 [Krillion](https://krillion.io/)
- 🌿 [Metaflora](https://flora.metazooa.com/game)
- 🐢 [Metazooa](https://metazooa.com/game)
- 📊 [MoreLess](https://less.gg/moreless)
- 📌 [Pinpoint](https://lnkd.in/pinpoint)
- ⛳ [Putt](https://putt.day)

### 🎵 Musica (6)
- 🎸 [Bandle](https://bandle.app/)
- 🔊 [Heardle](https://heardle.it)
- 📜 [Lyricle](https://lyricle.app)
- 🎶 [Songless](https://less.gg/songless)
- 🎧 [Spotle](https://spotle.io/)
- ⏳ [Timdle Music](https://www.timdle.com/music)

### 👁️ Osservazione e percezione (11)
- 📐 [Angle](https://angle.wtf)
- 🎨 [Color](https://dialed.gg)
- 🎨 [Color2](https://dialed.gg/color2)
- 🎨 [Colorfle](https://colorfle.com)
- 📐 [GuessTheAngle](https://guesstheangle.wtf)
- 🎨 [Hexcodle](https://hexcodle.com)
- 🪟 [Picsey](https://picsey.io)
- 🧩 [Rotaboxes](https://rotaboxes.com)
- 📏 [Size It Up](https://magnitudle.com/size-it-up)
- 🔍 [Snoop](https://www.shockwave.com/gamelanding/the-daily-snoop-a-hidden-object-game)
- ⏰ [Time](https://dialed.gg/time)

### 📜 Storia (5)
- ⏱️ [Chrono](https://chrono.quest)
- ⏳ [Chronophoto](https://www.chronophoto.app/daily.html)
- ⏳ [Timdle](https://www.timdle.com/)
- 📅 [TimeGuessr](https://timeguessr.com)
- 📍 [WhenTaken](https://whentaken.com)
