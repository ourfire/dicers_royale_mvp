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
        # Ensure basic keys exist, though checks in Game.from_dict might be sufficient
        if not all(k in data for k in ('id', 'name', 'is_human')):
             raise ValueError("Player data dictionary missing required keys (id, name, is_human)")
             
        player = cls(data['id'], data['name'], data['is_human'])
        # **FIX:** Use .get() with default 0 for total_score to prevent KeyError
        player.total_score = data.get('total_score', 0) 
        player.round_scores = data.get('round_scores', {}) # Safely gets round_scores
        # Ensure scores are integers if they exist
        player.round_scores = {int(k): int(v) for k, v in player.round_scores.items()}
        return player

class Game:
    """Manages the overall game state and logic."""
    DEFAULT_ROUNDS = 3
    BOT_STOP_SCORE = 15 # Bot stops if round score reaches this

    def __init__(self, players_data, total_rounds=DEFAULT_ROUNDS):
        # Ensure players_data is a list before iterating
        if not isinstance(players_data, list):
             raise TypeError("players_data must be a list of player dictionaries")
        self.players = [Player.from_dict(p_data) for p_data in players_data]
        self.total_rounds = total_rounds
        self.current_round = 1
        self.current_player_index = 0
        self.current_round_score = 0 # Score accumulated in the current player's turn
        self.current_dice = [0, 0]
        # Ensure there are players before accessing index 0
        initial_player_name = self.get_current_player().name if self.players else "N/A"
        self.message = f"Ronda {self.current_round}. Turno de {initial_player_name}."
        self.game_over = False
        self.turn_over = False # Flag to indicate if the current player's turn just ended

    def get_current_player(self):
        """Returns the Player object whose turn it is."""
        # Add boundary check for safety
        if self.players and 0 <= self.current_player_index < len(self.players):
            return self.players[self.current_player_index]
        # Handle potential index out of bounds or no players
        print(f"Warning: Attempted to get current player with index {self.current_player_index} or no players.")
        return None # Return None if no valid player

    def next_player(self):
        """Advances to the next player or next round. Returns True if state changed significantly (e.g., new round, game over)."""
        state_changed = False
        self.turn_over = False # Reset flag
        
        # Ensure there are players
        if not self.players:
             self.end_game()
             return True # Game ended

        last_player_index = len(self.players) - 1
        
        if self.current_player_index == last_player_index:
            # Last player finished, advance round
            if self.current_round >= self.total_rounds:
                self.end_game()
                # Do not proceed further if game ended
                return True # Game ended
            else:
                self.current_round += 1
                self.current_player_index = 0
                state_changed = True # New round started
                current_player = self.get_current_player()
                current_player_name = current_player.name if current_player else "N/A"
                self.message = f"Fin de Ronda {self.current_round - 1}. Empezando Ronda {self.current_round}. Turno de {current_player_name}."
        else:
            # Simply advance to next player
            self.current_player_index += 1
            state_changed = True # Player changed
            current_player = self.get_current_player()
            current_player_name = current_player.name if current_player else "N/A"
            self.message = f"Ronda {self.current_round}. Turno de {current_player_name}."
        
        self.current_round_score = 0 # Reset round score for the new turn
        self.current_dice = [0, 0]

        return state_changed


    def roll_dice(self):
        """Handles the 'Roll' action for the current player."""
        player = self.get_current_player()
        if self.game_over or not player or not player.is_human:
             print("Roll attempt ignored: Game over, no current player, or not human's turn.")
             return 

        self.turn_over = False
        dice = [random.randint(1, 6), random.randint(1, 6)]
        self.current_dice = dice
        
        if dice[0] == dice[1]: # Pair rolled (Bust)
            self.current_round_score = 0
            # Record 0 for this round for the player if they bust
            player.round_scores[self.current_round] = 0 
            self.message = f"¡{player.name} sacó par {dice}! Pierde los puntos de la ronda."
            self.turn_over = True # Mark turn as over
        else:
            roll_sum = sum(dice)
            # Ensure score is treated as integer
            self.current_round_score = int(self.current_round_score) + roll_sum 
            self.message = f"{player.name} tiró {dice} (Suma: {roll_sum}). Puntaje de turno actual: {self.current_round_score}. ¿Tirar de nuevo o parar?"

    def stop_turn(self):
        """Handles the 'Stop' action for the current player."""
        player = self.get_current_player()
        if self.game_over or not player or not player.is_human:
             print("Stop attempt ignored: Game over, no current player, or not human's turn.")
             return

        # Ensure scores are integers before adding
        player.total_score = int(player.total_score) + int(self.current_round_score)
        # Record the banked score for this round
        player.round_scores[self.current_round] = int(self.current_round_score) 
        self.message = f"{player.name} decidió parar. Guardó {self.current_round_score} puntos."
        self.current_round_score = 0
        self.turn_over = True # Mark turn as over

    def handle_bot_turn(self):
        """Simulates a single bot's turn. Returns True if the turn ended (bust or stop)."""
        player = self.get_current_player()
        if self.game_over or not player or player.is_human:
            print(f"handle_bot_turn called incorrectly for player {player.name if player else 'None'}")
            return False # Should not happen

        initial_message = f"Ronda {self.current_round}. Turno del Bot: {player.name}."
        turn_messages = [] 
        
        # *** DEBUGGING PRINT STATEMENTS ADDED HERE ***
        print(f"DEBUG: Bot {player.name} starting turn decision.")
        print(f"DEBUG: Current Round Score = {self.current_round_score} (Type: {type(self.current_round_score)})")
        print(f"DEBUG: Bot Stop Score = {self.BOT_STOP_SCORE} (Type: {type(self.BOT_STOP_SCORE)})")
        # *** END DEBUGGING PRINT STATEMENTS ***

        # Ensure current_round_score is an integer before comparison
        try:
            current_score_int = int(self.current_round_score)
        except (ValueError, TypeError):
             print(f"Error: Could not convert current_round_score '{self.current_round_score}' to int for bot {player.name}. Ending turn.")
             self.current_round_score = 0 # Reset score
             player.round_scores[self.current_round] = 0
             self.message = initial_message + f" Error interno procesando puntaje."
             self.turn_over = True
             return True # End turn due to error

        while current_score_int < self.BOT_STOP_SCORE:
            dice = [random.randint(1, 6), random.randint(1, 6)]
            self.current_dice = dice
            
            if dice[0] == dice[1]: # Bot busts
                self.current_round_score = 0
                player.round_scores[self.current_round] = 0
                turn_messages.append(f" ¡{player.name} sacó par {dice}! Pierde los puntos.")
                self.turn_over = True
                self.message = initial_message + "".join(turn_messages) 
                return True # Bot's turn ends immediately
            else:
                roll_sum = sum(dice)
                # Ensure integer addition
                self.current_round_score = int(self.current_round_score) + roll_sum 
                current_score_int = self.current_round_score # Update integer version for loop check
                turn_messages.append(f" {player.name} tiró {dice} (Suma: {roll_sum}). Puntaje de turno: {self.current_round_score}.")
                if current_score_int >= self.BOT_STOP_SCORE:
                    break 
        
        # Bot decides to stop 
        # Ensure scores are integers before adding
        player.total_score = int(player.total_score) + int(self.current_round_score)
        player.round_scores[self.current_round] = int(self.current_round_score)
        turn_messages.append(f" {player.name} decidió parar y guardó {self.current_round_score} puntos.")
        self.current_round_score = 0 # Reset for next turn (done also in next_player)
        self.turn_over = True
        self.message = initial_message + "".join(turn_messages) 
        return True # Bot's turn ends

    def end_game(self):
        """Sets the game to finished and determines the winner."""
        if self.game_over: 
             return
        self.game_over = True
        if not self.players: 
             self.message = "¡Juego Terminado!"
             return
        
        # Ensure all total_scores are integers before finding max
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
        """Creates a Game instance from a dictionary."""
        if not data or 'players_data' not in data: 
            return None
        total_rounds = data.get('total_rounds', cls.DEFAULT_ROUNDS) 
        game = cls(data['players_data'], total_rounds)
        # Safely get other attributes with defaults and ensure types
        game.current_round = int(data.get('current_round', 1))
        game.current_player_index = int(data.get('current_player_index', 0))
        game.current_round_score = int(data.get('current_round_score', 0))
        game.current_dice = data.get('current_dice', [0, 0])
        game.message = data.get('message', 'Estado de juego cargado.')
        game.game_over = data.get('game_over', False)
        return game
