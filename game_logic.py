# game_logic.py
import random

class Player:
    """Represents a player (human or bot) in the game."""
    def __init__(self, player_id, name, is_human=True):
        self.id = player_id
        self.name = name
        self.is_human = is_human
        self.total_score = 0
        # Store scores per round (key: round number, value: score)
        self.round_scores = {} 

    def reset_for_new_game(self):
        """Resets scores for a new game."""
        self.total_score = 0
        self.round_scores = {}

    def to_dict(self):
        """Converts player object to a dictionary for session storage."""
        return {
            'id': self.id,
            'name': self.name,
            'is_human': self.is_human,
            'total_score': self.total_score,
            'round_scores': self.round_scores
        }

    @classmethod
    def from_dict(cls, data):
        """Creates a Player instance from a dictionary."""
        if not all(k in data for k in ('id', 'name', 'is_human')):
             raise ValueError("Player data dictionary missing required keys (id, name, is_human)")
             
        player = cls(data['id'], data['name'], data['is_human'])
        player.total_score = data.get('total_score', 0) 
        player.round_scores = data.get('round_scores', {}) 
        # Convert keys back to int when loading from session/JSON
        player.round_scores = {int(k): int(v) for k, v in player.round_scores.items()}
        return player

class Game:
    """Manages the overall game state and logic."""
    DEFAULT_ROUNDS = 3
    BOT_STOP_SCORE = 15 

    # ** FIX: Changed __init__ signature to accept num_total_players and num_humans **
    def __init__(self, num_total_players=2, num_humans=1, total_rounds=DEFAULT_ROUNDS):
        
        # Validate inputs based on the arguments received
        if num_total_players < 2:
            raise ValueError("El juego requiere al menos 2 jugadores.")
        if num_humans < 1 or num_humans > num_total_players:
             raise ValueError("Número inválido de jugadores humanos para el total de jugadores.")
        
        num_bots = num_total_players - num_humans
        # num_bots check is implicitly covered by the check above

        self.players = []
        # Add human players
        for i in range(num_humans):
            player_id = i # Assign sequential IDs starting from 0
            player_name = "Tú" if i == 0 else f"Player {i + 1}" # Name them Player 1, Player 2...
            self.players.append(Player(player_id=player_id, name=player_name, is_human=True))
        
        # Add bots
        for i in range(num_bots):
            bot_id = num_humans + i # Continue numbering after humans
            self.players.append(Player(player_id=bot_id, name=f'Bot {i + 1}', is_human=False))

        self.total_rounds = total_rounds
        self.current_round = 1
        # Player order is now defined by the list creation order
        self.current_player_index = 0 
        self.current_round_score = 0 
        self.current_dice = [0, 0]
        initial_player_name = self.get_current_player().name if self.players else "N/A"
        self.message = f"Ronda {self.current_round}. Turno de {initial_player_name}."
        self.game_over = False
        self.turn_over = False 

    # --- Rest of the Game class methods (get_current_player, next_player, etc.) remain the same ---
    def get_current_player(self):
        """Returns the Player object whose turn it is."""
        if self.players and 0 <= self.current_player_index < len(self.players):
            return self.players[self.current_player_index]
        print(f"Warning: Attempted to get current player with index {self.current_player_index} or no players.")
        return None 

    def next_player(self):
        """Advances to the next player or next round. Returns True if state changed significantly (e.g., new round, game over)."""
        state_changed = False
        self.turn_over = False 
        
        if not self.players:
             self.end_game()
             return True 

        last_player_index = len(self.players) - 1
        
        if self.current_player_index == last_player_index:
            if self.current_round >= self.total_rounds:
                self.end_game()
                return True 
            else:
                self.current_round += 1
                self.current_player_index = 0
                state_changed = True 
                current_player = self.get_current_player()
                current_player_name = current_player.name if current_player else "N/A"
                self.message = f"Fin de Ronda {self.current_round - 1}. Empezando Ronda {self.current_round}. Turno de {current_player_name}."
        else:
            self.current_player_index += 1
            state_changed = True 
            current_player = self.get_current_player()
            current_player_name = current_player.name if current_player else "N/A"
            self.message = f"Ronda {self.current_round}. Turno de {current_player_name}."
        
        self.current_round_score = 0 
        self.current_dice = [0, 0]

        return state_changed


    def roll_dice(self):
        """Handles the 'Roll' action for the current player."""
        player = self.get_current_player()
        # Allow roll only if it's a human player's turn
        if self.game_over or not player or not player.is_human: 
             print("Roll attempt ignored: Game over, no current player, or not human's turn.")
             return 

        self.turn_over = False
        dice = [random.randint(1, 6), random.randint(1, 6)]
        self.current_dice = dice
        
        if dice[0] == dice[1]: 
            self.current_round_score = 0
            # Ensure round key exists before assigning
            player.round_scores[self.current_round] = 0 
            self.message = f"¡{player.name} sacó par {dice}! Pierde los puntos de la ronda."
            self.turn_over = True 
        else:
            roll_sum = sum(dice)
            self.current_round_score = int(self.current_round_score) + roll_sum 
            self.message = f"{player.name} tiró {dice} (Suma: {roll_sum}). Puntaje de turno actual: {self.current_round_score}. ¿Tirar de nuevo o parar?"

    def stop_turn(self):
        """Handles the 'Stop' action for the current player."""
        player = self.get_current_player()
         # Allow stop only if it's a human player's turn
        if self.game_over or not player or not player.is_human:
             print("Stop attempt ignored: Game over, no current player, or not human's turn.")
             return

        player.total_score = int(player.total_score) + int(self.current_round_score)
        player.round_scores[self.current_round] = int(self.current_round_score) 
        self.message = f"{player.name} decidió parar. Guardó {self.current_round_score} puntos."
        self.current_round_score = 0
        self.turn_over = True 

    def handle_bot_turn(self):
        """Simulates a single bot's turn. Returns True if the turn ended (bust or stop)."""
        player = self.get_current_player()
        if self.game_over or not player or player.is_human:
            print(f"handle_bot_turn called incorrectly for player {player.name if player else 'None'}")
            return False 

        initial_message = f"Ronda {self.current_round}. Turno del Bot: {player.name}."
        turn_messages = [] 
        
        # print(f"DEBUG: Bot {player.name} starting turn decision.") # Optional Debug
        
        try:
            current_score_int = int(self.current_round_score)
        except (ValueError, TypeError):
             print(f"Error: Could not convert current_round_score '{self.current_round_score}' to int for bot {player.name}. Ending turn.")
             self.current_round_score = 0 
             player.round_scores[self.current_round] = 0
             self.message = initial_message + f" Error interno procesando puntaje."
             self.turn_over = True
             return True 

        while current_score_int < self.BOT_STOP_SCORE:
            dice = [random.randint(1, 6), random.randint(1, 6)]
            self.current_dice = dice
            
            if dice[0] == dice[1]: 
                self.current_round_score = 0
                player.round_scores[self.current_round] = 0
                turn_messages.append(f" ¡{player.name} sacó par {dice}! Pierde los puntos.")
                self.turn_over = True
                self.message = initial_message + "".join(turn_messages) 
                return True 
            else:
                roll_sum = sum(dice)
                self.current_round_score = int(self.current_round_score) + roll_sum 
                current_score_int = self.current_round_score 
                turn_messages.append(f" {player.name} tiró {dice} (Suma: {roll_sum}). Puntaje de turno: {self.current_round_score}.")
                if current_score_int >= self.BOT_STOP_SCORE:
                    break 
        
        player.total_score = int(player.total_score) + int(self.current_round_score)
        player.round_scores[self.current_round] = int(self.current_round_score)
        turn_messages.append(f" {player.name} decidió parar y guardó {self.current_round_score} puntos.")
        self.current_round_score = 0 
        self.turn_over = True
        self.message = initial_message + "".join(turn_messages) 
        return True 

    def end_game(self):
        """Sets the game to finished and determines the winner."""
        if self.game_over: 
             return
        self.game_over = True
        if not self.players: 
             self.message = "¡Juego Terminado!"
             return
        
        for p in self.players:
             p.total_score = int(p.total_score)
             
        winner = max(self.players, key=lambda p: p.total_score)
        max_score = winner.total_score
        winners = [p for p in self.players if p.total_score == max_score]
        
        if len(winners) > 1:
             winner_names = ", ".join([w.name for w in winners])
             self.message = f"¡Juego Terminado después de {self.total_rounds} rondas! ¡Empate entre {winner_names} con {max_score} puntos!"
        else:
             self.message = f"¡Juego Terminado después de {self.total_rounds} rondas! Ganador: {winner.name} con {winner.total_score} puntos."

    def to_dict(self):
        """Converts game state to a dictionary for session storage."""
        return {
            'players_data': [p.to_dict() for p in self.players],
            'total_rounds': self.total_rounds,
            'current_round': self.current_round,
            'current_player_index': self.current_player_index,
            'current_round_score': self.current_round_score,
            'current_dice': self.current_dice,
            'message': self.message,
            'game_over': self.game_over,
        }

    @classmethod
    def from_dict(cls, data):
        """Creates a Game instance from a dictionary saved state."""
        if not data or 'players_data' not in data: 
            return None
        
        players = [Player.from_dict(p_data) for p_data in data['players_data']]
        num_players = len(players)
        num_humans = sum(1 for p in players if p.is_human) 
        
        total_rounds = int(data.get('total_rounds', cls.DEFAULT_ROUNDS)) 

        # Create instance using the correct constructor signature now
        game = cls(num_total_players=num_players, num_humans=num_humans, total_rounds=total_rounds) 
        
        # Overwrite state with loaded data 
        game.players = players 
        game.total_rounds = total_rounds 
        game.current_round = int(data.get('current_round', 1))
        game.current_player_index = int(data.get('current_player_index', 0))
        if not (0 <= game.current_player_index < len(game.players)):
             print(f"Warning: Loaded invalid player index {game.current_player_index}, resetting to 0.")
             game.current_player_index = 0
        game.current_round_score = int(data.get('current_round_score', 0))
        game.current_dice = data.get('current_dice', [0, 0])
        game.message = data.get('message', 'Estado de juego cargado.')
        game.game_over = data.get('game_over', False)
        return game
