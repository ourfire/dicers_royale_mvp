# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory # Added send_from_directory
import os 

try:
    from game_logic import Game, Player 
except ImportError:
    print("Error: Could not import Game, Player from game_logic. Ensure game_logic.py exists.")
    Game = None 
    Player = None

APP_ROOT = os.path.dirname(os.path.abspath(__file__)) 
STATIC_FOLDER = os.path.join(APP_ROOT, 'static') 
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static') 
app.secret_key = 'tu_clave_secreta_aqui_cambiar_esto_de_nuevo' 

# --- Game Setup Options ---
QUICK_GAME_NUM_PLAYERS = 3 
QUICK_GAME_NUM_HUMANS = 1
QUICK_GAME_ROUNDS = 3
MIN_PLAYERS = 2
MAX_PLAYERS = 5 
MIN_HUMANS = 1 
MIN_ROUNDS = 1
MAX_ROUNDS = 5

# --- Helper Function ---
def handle_pending_bot_turns(game):
    if not game or game.game_over: return False 
    updated = False
    current_player = game.get_current_player()
    max_bot_turns = len(game.players) * 2 if game.players else 0 
    processed_turns = 0
    while current_player and not current_player.is_human and not game.game_over and processed_turns < max_bot_turns:
        turn_ended = game.handle_bot_turn()
        updated = True 
        processed_turns += 1
        if game.game_over: break
        if turn_ended:
             game.next_player() 
             current_player = game.get_current_player() 
        else:
             print("Warning: Bot turn handler didn't report turn end.")
             break 
    if processed_turns >= max_bot_turns: print("Warning: Exceeded max bot turns limit.")
    return updated 

# --- Routes ---
@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except FileNotFoundError:
        from werkzeug.exceptions import NotFound
        raise NotFound()
    except Exception as e:
         print(f"Error serving static file {filename}: {e}")
         from werkzeug.exceptions import InternalServerError
         raise InternalServerError()

@app.route('/')
def index():
    """Shows the main game UI, handling bot turns if a game is active."""
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    
    # Handle bot turns ONLY if a game is active and not over
    if game and not game.game_over:
        try: 
            if handle_pending_bot_turns(game):
                session['game_state'] = game.to_dict() 
        except Exception as e:
             print(f"Error during bot turn handling in index route: {e}") 
             flash(f"Error procesando turno del bot: {e}", "error") 
             session.pop('game_state', None)
             game = None # Reset game object on error
             
    # Always render the main template, passing game (which might be None)
    # Also pass constants needed for the create form, even if hidden initially
    return render_template('index.html', game=game, 
                           min_players=MIN_PLAYERS, max_players=MAX_PLAYERS,
                           min_humans=MIN_HUMANS, 
                           min_rounds=MIN_ROUNDS, max_rounds=MAX_ROUNDS,
                           default_rounds=Game.DEFAULT_ROUNDS) 

@app.route('/start_quick_game', methods=['POST'])
def start_quick_game():
    """Starts a new quick game with default settings."""
    if not Game: 
         flash("Error: Lógica del juego no cargada.", "error")
         return redirect(url_for('index'))
         
    try:
        # Use constants for quick game setup
        game = Game(num_total_players=QUICK_GAME_NUM_PLAYERS, 
                    num_humans=QUICK_GAME_NUM_HUMANS, 
                    total_rounds=QUICK_GAME_ROUNDS)
        session['game_state'] = game.to_dict() 
    except Exception as e:
        print(f"ERROR (start_quick_game): Error starting game: {e}") 
        flash(f"Error al iniciar Quick Game: {e}", "error")
        session.pop('game_state', None) 
        return redirect(url_for('index'))

    return redirect(url_for('index')) 

@app.route('/create_game', methods=['POST'])
def create_game():
    """Handles the submission of the create game form."""
    if not Game:
        flash("Error: Lógica del juego no cargada.", "error")
        return redirect(url_for('index'))

    try:
        # Get data from form
        num_total_players_str = request.form.get('num_total_players')
        num_humans_str = request.form.get('num_humans')
        total_rounds_str = request.form.get('num_rounds')
        
        # Convert to int
        num_total_players = int(num_total_players_str if num_total_players_str else MIN_PLAYERS)
        num_humans = int(num_humans_str if num_humans_str else MIN_HUMANS)
        total_rounds = int(total_rounds_str if total_rounds_str else Game.DEFAULT_ROUNDS)
        
        # Validate inputs
        if not (MIN_PLAYERS <= num_total_players <= MAX_PLAYERS):
            flash(f"Número total de jugadores debe estar entre {MIN_PLAYERS} y {MAX_PLAYERS}.", "error")
            return redirect(url_for('index'))
        if not (MIN_HUMANS <= num_humans <= num_total_players): 
             flash(f"Número de jugadores humanos debe estar entre {MIN_HUMANS} y {num_total_players}.", "error")
             return redirect(url_for('index'))
        if not (MIN_ROUNDS <= total_rounds <= MAX_ROUNDS):
             flash(f"Número de rondas debe estar entre {MIN_ROUNDS} y {MAX_ROUNDS}.", "error")
             return redirect(url_for('index'))
        
        # Create the game instance using the updated __init__
        game = Game(num_total_players=num_total_players, num_humans=num_humans, total_rounds=total_rounds) 
        session['game_state'] = game.to_dict()

    except ValueError as e:
         print(f"ERROR (create_game): Invalid input value (not an integer): {e}") 
         flash("Entrada inválida. Por favor selecciona números válidos.", "error")
         return redirect(url_for('index'))
    except Exception as e:
        print(f"ERROR (create_game): Error creating game: {e}")
        flash(f"Error al crear la partida: {e}", "error")
        session.pop('game_state', None)
        return redirect(url_for('index'))

    return redirect(url_for('index'))

# --- Ruta para Salir/Resetear ---
@app.route('/reset_game', methods=['POST']) 
def reset_game():
    """Clears the game state from the session and redirects home."""
    session.pop('game_state', None) # Remove game state if it exists
    flash("Partida reiniciada.", "success") # Optional feedback
    return redirect(url_for('index'))


@app.route('/roll', methods=['POST'])
def roll_action():
    """Handles the 'Roll' action."""
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    current_player = game.get_current_player() if game else None

    if not game or game.game_over or not current_player or not current_player.is_human:
        return redirect(url_for('index')) 

    try:
        game.roll_dice()
        if game.turn_over:
            game.next_player() 
        session['game_state'] = game.to_dict()
    except Exception as e:
         print(f"ERROR (roll_action): Error during roll action: {e}") 
         flash(f"Error durante la tirada: {e}", "error")
         session.pop('game_state', None)
         return redirect(url_for('index')) 

    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop_action():
    """Handles the 'Stop' action."""
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    current_player = game.get_current_player() if game else None

    if not game or game.game_over or not current_player or not current_player.is_human:
        return redirect(url_for('index')) 
        
    try:
        game.stop_turn()
        game.next_player() 
        session['game_state'] = game.to_dict()
    except Exception as e:
         print(f"ERROR (stop_action): Error during stop action: {e}") 
         flash(f"Error al parar: {e}", "error")
         session.pop('game_state', None)
         return redirect(url_for('index')) 

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
