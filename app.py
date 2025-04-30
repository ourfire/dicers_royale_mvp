# app.py
# Add send_from_directory to imports
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory 
import os # Import os to construct path

# Import the Game class from our new file
# Make sure game_logic.py is in the same directory or Python path
try:
    from game_logic import Game, Player 
except ImportError:
    print("Error: Could not import Game, Player from game_logic. Ensure game_logic.py exists.")
    Game = None # Define as None to prevent further errors if import fails
    Player = None

# This line MUST be here, before any @app.route decorators
# Explicitly tell Flask where the static folder is AND the URL path to use
# Define static folder relative to the app's root path
APP_ROOT = os.path.dirname(os.path.abspath(__file__)) # Get the absolute path of the directory app.py is in
STATIC_FOLDER = os.path.join(APP_ROOT, 'static') # Construct absolute path to static folder
print(f"DEBUG: Application Root Path: {APP_ROOT}") # Print app root path
print(f"DEBUG: Static Folder Path Set To: {STATIC_FOLDER}") # Print static folder path
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static') 
app.secret_key = 'tu_clave_secreta_aqui_cambiar_esto_de_nuevo' # Change this!

# --- Game Setup Options ---
QUICK_GAME_PLAYERS_DATA = [
    {'id': 0, 'name': 'Tú', 'is_human': True},
    {'id': 1, 'name': 'Bot 1', 'is_human': False},
    {'id': 2, 'name': 'Bot 2', 'is_human': False} 
]
QUICK_GAME_ROUNDS = 3

# --- Helper Function ---
def handle_pending_bot_turns(game):
    """Checks if current player is a bot and runs its turn(s) until human turn or game over."""
    if not game or game.game_over:
        return False # No game or game already over

    updated = False
    current_player = game.get_current_player()
    # Loop while the current player is a bot and the game is not over
    # Add safety limit to prevent infinite loops in case of logic errors
    max_bot_turns = len(game.players) * 2 if game.players else 0 # Limit bot turns per request cycle
    processed_turns = 0
    while current_player and not current_player.is_human and not game.game_over and processed_turns < max_bot_turns:
        # print(f"DEBUG (handle_pending_bot_turns): Handling turn for Bot: {current_player.name}") # Debug print (optional)
        turn_ended = game.handle_bot_turn()
        updated = True # Mark that state was updated by the bot turn
        processed_turns += 1
        if game.game_over: # Check if bot's turn ended the game
             break
        if turn_ended:
             game.next_player() # Advance to the next player/round
             current_player = game.get_current_player() # Get the new current player
        else:
             # Should not happen with current bot logic, but break defensively
             print("Warning: Bot turn handler didn't report turn end.")
             break 
    if processed_turns >= max_bot_turns:
         print("Warning: Exceeded max bot turns limit in single request cycle.")
             
    return updated # Return True if any bot turn was processed

# --- Routes ---

# ** Manual route to serve static files (FOR DEBUGGING) **
@app.route('/static/<path:filename>')
def serve_static(filename):
    # Use the explicitly defined STATIC_FOLDER path
    print(f"DEBUG (serve_static): Attempting to serve: {filename}")
    print(f"DEBUG (serve_static): Looking in directory: {app.static_folder}") 
    requested_path = os.path.join(app.static_folder, filename)
    print(f"DEBUG (serve_static): Full expected path: {requested_path}")
    print(f"DEBUG (serve_static): Does file exist? {os.path.isfile(requested_path)}") # Check if file actually exists at that path
    
    try:
        return send_from_directory(app.static_folder, filename)
    except FileNotFoundError:
        print(f"ERROR (serve_static): File not found via send_from_directory: {filename}")
        from werkzeug.exceptions import NotFound
        raise NotFound()
    except Exception as e:
         print(f"Error serving static file {filename}: {e}")
         from werkzeug.exceptions import InternalServerError
         raise InternalServerError()


@app.route('/')
def index():
    """Shows the main menu or the current game state, handling bot turns."""
    # print("DEBUG: Entering index route (GET request)") # Optional Debug
    game_data = session.get('game_state')
    # print(f"DEBUG (index): Loaded game_data from session: {game_data is not None}") # Optional Debug
    game = Game.from_dict(game_data) if game_data and Game else None
    
    if game and not game.game_over:
        # print("DEBUG (index): Game in progress, checking for bot turns...") # Optional Debug
        try: 
            if handle_pending_bot_turns(game):
                session['game_state'] = game.to_dict() 
                # print("DEBUG (index): Processed bot turns, state saved.") # Optional Debug
        except Exception as e:
             print(f"Error during bot turn handling in index route: {e}") 
             session.pop('game_state', None)
             game = None 
    # elif game and game.game_over:
         # print("DEBUG (index): Game is over.") # Optional Debug
    # else:
         # print("DEBUG (index): No active game found, showing initial menu.") # Optional Debug

    # print("DEBUG (index): Rendering index.html template...") # Optional Debug
    return render_template('index.html', game=game) 

@app.route('/start_quick_game', methods=['POST'])
def start_quick_game():
    """Starts a new quick game with default settings."""
    # print("DEBUG: Entering start_quick_game route (POST request)") # Optional Debug
    if not Game: 
         print("ERROR (start_quick_game): Game class not loaded!") 
         return "Error: Game logic not loaded.", 500
         
    players_data = QUICK_GAME_PLAYERS_DATA 
    try:
        # print("DEBUG (start_quick_game): Creating new Game instance...") # Optional Debug
        game = Game(players_data, QUICK_GAME_ROUNDS)
        # print("DEBUG (start_quick_game): Game instance created.") # Optional Debug
        session['game_state'] = game.to_dict() 
        # print("DEBUG (start_quick_game): Game state saved to session.") # Optional Debug
    except Exception as e:
        print(f"ERROR (start_quick_game): Error starting game: {e}") 
        session.pop('game_state', None) 
        return redirect(url_for('index'))

    # print("DEBUG (start_quick_game): Redirecting to index...") # Optional Debug
    return redirect(url_for('index')) 

@app.route('/roll', methods=['POST'])
def roll_action():
    """Handles the 'Roll' action."""
    # print("DEBUG: Entering roll_action route (POST request)") # Optional Debug
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    current_player = game.get_current_player() if game else None

    if not game or game.game_over or not current_player or not current_player.is_human:
        # print("DEBUG (roll_action): Invalid roll action attempt.") 
        return redirect(url_for('index')) 

    try:
        # print("DEBUG (roll_action): Calling game.roll_dice()") # Optional Debug
        game.roll_dice()
        # print(f"DEBUG (roll_action): Roll complete. Turn over? {game.turn_over}") # Optional Debug
        if game.turn_over:
            # print("DEBUG (roll_action): Advancing to next player...") # Optional Debug
            game.next_player() 
            
        session['game_state'] = game.to_dict()
        # print("DEBUG (roll_action): Game state saved.") # Optional Debug
    except Exception as e:
         print(f"ERROR (roll_action): Error during roll action: {e}") 
         session.pop('game_state', None)
         return redirect(url_for('index')) 

    # print("DEBUG (roll_action): Redirecting to index...") # Optional Debug
    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop_action():
    """Handles the 'Stop' action."""
    # print("DEBUG: Entering stop_action route (POST request)") # Optional Debug
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    current_player = game.get_current_player() if game else None

    if not game or game.game_over or not current_player or not current_player.is_human:
        # print("DEBUG (stop_action): Invalid stop action attempt.") 
        return redirect(url_for('index')) 
        
    try:
        # print("DEBUG (stop_action): Calling game.stop_turn()") # Optional Debug
        game.stop_turn()
        # print("DEBUG (stop_action): Stop complete. Advancing to next player...") # Optional Debug
        game.next_player() 
        
        session['game_state'] = game.to_dict()
        # print("DEBUG (stop_action): Game state saved.") # Optional Debug
    except Exception as e:
         print(f"ERROR (stop_action): Error during stop action: {e}") 
         session.pop('game_state', None)
         return redirect(url_for('index')) 

    # print("DEBUG (stop_action): Redirecting to index...") # Optional Debug
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
