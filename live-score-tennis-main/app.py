import tornado.web
import tornado.websocket
import json
import random
import time
import asyncio

POOL_GIOCATORI = [
    "Jannik Sinner", "Carlos Alcaraz", "Novak Djokovic", "Daniil Medvedev",
    "Alexander Zverev", "Andrey Rublev", "Casper Ruud", "Holger Rune",
    "Taylor Fritz", "Alex De Minaur", "Grigor Dimitrov", "Tommy Paul",
    "Lorenzo Musetti", "Ben Shelton", "Félix Auger-Aliassime", "Jack Draper",
    "Sebastian Korda", "Hubert Hurkacz", "Karen Khachanov", "Frances Tiafoe",
    "Alexander Bublik", "Sebastian Ofner", "Jaume Munar", "Brandon Nakashima"
]


def genera_accoppiamenti():

    giocatori_casuali = random.sample(POOL_GIOCATORI, 16)

    return giocatori_casuali


EVENTI_TENNIS = [
    {"text": "Ace!", "icon": "⚡", "prob": 0.3},
    {"text": "Doppio fallo", "icon": "❌", "prob": 0.15},
    {"text": "Vincente di dritto", "icon": "💥", "prob": 0.25},
    {"text": "Passante spettacolare", "icon": "🔥", "prob": 0.2},
    {"text": "Smash vincente", "icon": "⭐", "prob": 0.2},
    {"text": "Palla break salvata", "icon": "🛡️", "prob": 0.15},
    {"text": "Break point!", "icon": "🎯", "prob": 0.15},
]


class TennisMatch:


    def __init__(self, id, p1, p2):
        self.id = id
        self.p1 = p1
        self.p2 = p2
        self.sets = [0, 0]
        self.games = [0, 0]
        self.status = "LIVE"
        self.start_time = time.time()
        self.events = []
        self.game_counter = 0
        self.set_history = []
        self.p1_strength = random.uniform(0.4, 0.6)

    def update(self):

        if self.status == "TERMINATO":
            return

        self.game_counter += 1

        if random.random() < 0.4:
            self._aggiungi_evento()

        if self.game_counter % random.randint(1, 2) == 0:
            self._vinci_game()

    def _aggiungi_evento(self):

        eventi_disponibili = [e for e in EVENTI_TENNIS if random.random() < e["prob"]]

        if eventi_disponibili:
            evento = random.choice(eventi_disponibili)
            giocatore = random.choice([self.p1, self.p2])

            # Aggiungi evento in cima alla lista
            self.events.insert(0, {
                "time": self._tempo(),
                "text": f"{giocatore}: {evento['text']}",
                "icon": evento["icon"]
            })

    def _vinci_game(self):

        # Determina vincitore in base alla forza
        vincitore = 0 if random.random() < self.p1_strength else 1
        self.games[vincitore] += 1
        nome_vincitore = self.p1 if vincitore == 0 else self.p2

        # Controlla se il set è vinto
        if self.games[vincitore] >= 6 and self.games[vincitore] - self.games[1 - vincitore] >= 2:
            self._vinci_set(vincitore)
        else:
            self.events.insert(0, {
                "time": self._tempo(),
                "text": f"Game vinto da {nome_vincitore}",
                "icon": "🎾"
            })

    def _vinci_set(self, vincitore):

        nome = self.p1 if vincitore == 0 else self.p2

        # Salva punteggio del set nello storico
        self.set_history.append(f"{self.games[0]}-{self.games[1]}")

        # Incrementa i set vinti
        self.sets[vincitore] += 1

        # Registra evento set vinto
        self.events.insert(0, {
            "time": self._tempo(),
            "text": f"SET vinto da {nome} ({self.games[0]}-{self.games[1]})",
            "icon": "⭐"
        })

        self.games = [0, 0]

        if self.sets[vincitore] == 3:
            self.status = "TERMINATO"
            self.events.insert(0, {
                "time": self._tempo(),
                "text": f"MATCH vinto da {nome}!",
                "icon": "🏆"
            })

    def _tempo(self):

        if self.status == "TERMINATO":
            return "Fine"

        secondi = int(time.time() - self.start_time)
        return f"{secondi // 60}:{secondi % 60:02d}"

    def to_dict(self):

        return {
            "id": self.id,
            "p1": self.p1,
            "p2": self.p2,
            "sets1": self.sets[0],
            "sets2": self.sets[1],
            "games1": self.games[0],
            "games2": self.games[1],
            "status": self.status,
            "time": self._tempo(),
            "events": self.events[:15],
            "set_history": self.set_history
        }



PLAYERS = genera_accoppiamenti()

matches = [TennisMatch(i, PLAYERS[i * 2], PLAYERS[i * 2 + 1]) for i in range(8)]

print("\n🎾 OTTAVI DI FINALE - ACCOPPIAMENTI:")
print("=" * 50)
for i in range(8):
    print(f"Court {i + 1}: {PLAYERS[i * 2]} vs {PLAYERS[i * 2 + 1]}")
print("=" * 50 + "\n")



class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("index.html")


class WSHandler(tornado.websocket.WebSocketHandler):
    clients = set()

    def open(self):
        WSHandler.clients.add(self)

    def on_close(self):
        WSHandler.clients.remove(self)

    def check_origin(self, origin):
        return True


async def broadcast_updates():
    """
    Loop infinito che aggiorna i match ogni secondo
    e invia i dati a tutti i client
    """
    while True:
        for m in matches:
            m.update()

        data = json.dumps([m.to_dict() for m in matches])

        for client in WSHandler.clients:
            client.write_message(data)

        await asyncio.sleep(1)


def make_app():
    import os
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/ws", WSHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {
            "path": os.path.join(os.path.dirname(__file__), "static")
        }),
    ], debug=True)



async def main():

    app = make_app()
    app.listen(8888)
    print("server avviato su http://localhost:8888")
    await broadcast_updates()


if __name__ == "__main__":
    asyncio.run(main())
