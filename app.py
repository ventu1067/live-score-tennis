import tornado.web
import tornado.websocket
import json
import random
import time
import asyncio

PLAYERS = [
    "Carlos Alcaraz", "Jannik Sinner", "Alexander Zverev", "Novak Djokovic",
    "Daniil Medvedev", "Casper Ruud", "Andrey Rublev", "Hubert Hurkacz",
    "Alex de Minaur", "Grigor Dimitrov"
]

EVENTI_TENNIS = [
    {"text": "Ace!", "icon": "⚡", "probability": 0.3},
    {"text": "Doppio fallo", "icon": "❌", "probability": 0.15},
    {"text": "Vincente di dritto", "icon": "💥", "probability": 0.25},
    {"text": "Passante spettacolare", "icon": "🔥", "probability": 0.2},
    {"text": "Smash vincente", "icon": "⭐", "probability": 0.2},
    {"text": "Palla break salvata", "icon": "🛡️", "probability": 0.15},
    {"text": "Break point!", "icon": "🎯", "probability": 0.15},
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
        self.tiebreak_mode = False
        # Probabilità di vincita per rendere i match più equilibrati
        self.p1_strength = random.uniform(0.4, 0.6)  # Forza giocatore 1 (40-60%)
        # Storico dei set (es: ["6-4", "7-6", "6-3"])
        self.set_history = []

    def update(self):
        if self.status == "TERMINATO":
            return

        self.game_counter += 1

        if random.random() < 0.4:
            self._add_random_event()

        # Cambia questi numeri per velocizzare: (1, 2) = veloce, (2, 3) = medio, (3, 5) = lento
        if self.game_counter % random.randint(1, 2) == 0:
            self._win_game()

    def _add_random_event(self):
        available_events = [e for e in EVENTI_TENNIS if random.random() < e["probability"]]
        if available_events:
            event = random.choice(available_events)
            player = random.choice([self.p1, self.p2])
            self.events.insert(0, {
                "time": self.get_elapsed_time(),
                "text": f"{player}: {event['text']}",
                "icon": event["icon"]
            })

    def _win_game(self):
        # Usa la forza dei giocatori per decidere il vincitore (più realistico)
        winner_idx = 0 if random.random() < self.p1_strength else 1
        self.games[winner_idx] += 1

        winner_name = self.p1 if winner_idx == 0 else self.p2

        if self.games[0] == 6 and self.games[1] == 6:
            self.tiebreak_mode = True
            self.events.insert(0, {
                "time": self.get_elapsed_time(),
                "text": f"Tiebreak in corso!",
                "icon": "🎾"
            })
            self._win_tiebreak(winner_idx)
            return

        if self.games[winner_idx] >= 6 and self.games[winner_idx] - self.games[1 - winner_idx] >= 2:
            self._win_set(winner_idx)
        else:
            self.events.insert(0, {
                "time": self.get_elapsed_time(),
                "text": f"Game vinto da {winner_name}",
                "icon": "🎾"
            })

    def _win_tiebreak(self, winner_idx):
        winner_name = self.p1 if winner_idx == 0 else self.p2
        score_tb = f"7-{random.randint(0, 6)}"

        self.events.insert(0, {
            "time": self.get_elapsed_time(),
            "text": f"Tiebreak vinto da {winner_name} ({score_tb})",
            "icon": "🏆"
        })

        self.tiebreak_mode = False
        self._win_set(winner_idx)

    def _win_set(self, winner_idx):
        winner_name = self.p1 if winner_idx == 0 else self.p2

        # Salva il punteggio del set SEMPRE dal punto di vista del giocatore 1
        set_score_p1 = self.games[0]
        set_score_p2 = self.games[1]
        self.set_history.append(f"{set_score_p1}-{set_score_p2}")

        self.sets[winner_idx] += 1

        self.events.insert(0, {
            "time": self.get_elapsed_time(),
            "text": f"SET vinto da {winner_name} ({set_score_p1}-{set_score_p2})",
            "icon": "⭐"
        })

        self.games = [0, 0]

        # SLAM: Best of 5 sets (si vince con 3 set)
        if self.sets[winner_idx] == 3:
            self.status = "TERMINATO"
            self.events.insert(0, {
                "time": self.get_elapsed_time(),
                "text": f"MATCH vinto da {winner_name}!",
                "icon": "🏆"
            })

    def get_elapsed_time(self):
        if self.status == "TERMINATO":
            return "Fine"
        elapsed = int(time.time() - self.start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        return f"{minutes}:{seconds:02d}"

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
            "time": self.get_elapsed_time(),
            "events": self.events[:15],
            "set_history": self.set_history  # Storico dei set
        }


matches = [TennisMatch(i, PLAYERS[i * 2], PLAYERS[i * 2 + 1]) for i in range(5)]


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
    """Aggiorna i match e invia ai client ogni 1 secondo (veloce)"""
    while True:
        for m in matches:
            m.update()
        data = json.dumps([m.to_dict() for m in matches])
        for client in WSHandler.clients:
            client.write_message(data)
        await asyncio.sleep(1)  # Cambia a 0.5 per andare ancora più veloce, o 2 per rallentare


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
    print("🎾 Server avviato su http://localhost:8888")

    # Avvia il task di aggiornamento
    await broadcast_updates()


if __name__ == "__main__":
    asyncio.run(main())