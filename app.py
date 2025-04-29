
from flask import Flask, render_template, request, redirect, url_for, session
# Import the Game class from our new file
# Make sure game_logic.py is in the same directory or Python path
try:
    from game_logic import Game, Player 
except ImportError:
    print("Error: Could not import Game, Player from game_logic. Ensure game_logic.py exists.")
    Game = None # Define as None to prevent further errors if import fails
    Player = None

# This line MUST be here, before any @app.route decorators
app = Flask(__name__) 
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
    while current_player and not current_player.is_human and not game.game_over:
        print(f"Handling turn for Bot: {current_player.name}") # Debug print
        turn_ended = game.handle_bot_turn()
        updated = True # Mark that state was updated by the bot turn
        if game.game_over: # Check if bot's turn ended the game
             break
        if turn_ended:
             game.next_player() # Advance to the next player/round
             current_player = game.get_current_player() # Get the new current player
        else:
             # Should not happen with current bot logic, but break defensively
             print("Warning: Bot turn handler didn't report turn end.")
             break 
             
    return updated # Return True if any bot turn was processed

# --- Routes ---

@app.route('/')
def index():
    """Shows the main menu or the current game state, handling bot turns."""
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    
    if game and not game.game_over:
        # **FIX:** Check and handle bot turns before rendering
        if handle_pending_bot_turns(game):
            # If bot turns were handled, save the updated state back to session
            session['game_state'] = game.to_dict() 
            print("Processed bot turns, state saved.") # Debug print
            # Optionally, redirect back to index to ensure clean state load,
            # but rendering directly might be okay if template handles the final state.
            # return redirect(url_for('index')) 

    # Render the template with the potentially updated game state
    return render_template('index.html', game=game) 

@app.route('/start_quick_game', methods=['POST'])
def start_quick_game():
    """Starts a new quick game with default settings."""
    if not Game: # Check if import failed
         return "Error: Game logic not loaded.", 500
         
    players_data = QUICK_GAME_PLAYERS_DATA 
    try:
        game = Game(players_data, QUICK_GAME_ROUNDS)
        # Initial bot turn handling is now done in the index route after creation
        session['game_state'] = game.to_dict() 
    except Exception as e:
        print(f"Error starting game: {e}")
        session.pop('game_state', None) 
        return redirect(url_for('index'))

    # Redirect to index, which will handle any initial bot turn
    return redirect(url_for('index')) 

@app.route('/roll', methods=['POST'])
def roll_action():
    """Handles the 'Roll' action."""
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    current_player = game.get_current_player() if game else None

    if not game or game.game_over or not current_player or not current_player.is_human:
        print("Invalid roll action attempt.") 
        return redirect(url_for('index')) 

    try:
        game.roll_dice()
        # If the roll ended the player's turn (bust), advance state
        if game.turn_over:
            game.next_player() 
            # Bot turns will be handled by the redirect to index route

        session['game_state'] = game.to_dict()
    except Exception as e:
         print(f"Error during roll action: {e}")
         session.pop('game_state', None)
         return redirect(url_for('index')) 

    # Redirect to index, which will handle any subsequent bot turns
    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop_action():
    """Handles the 'Stop' action."""
    game_data = session.get('game_state')
    game = Game.from_dict(game_data) if game_data and Game else None
    current_player = game.get_current_player() if game else None

    if not game or game.game_over or not current_player or not current_player.is_human:
        print("Invalid stop action attempt.") 
        return redirect(url_for('index')) 
        
    try:
        game.stop_turn()
        # Turn always ends after stopping, advance state
        game.next_player() 
        # Bot turns will be handled by the redirect to index route

        session['game_state'] = game.to_dict()
    except Exception as e:
         print(f"Error during stop action: {e}")
         session.pop('game_state', None)
         return redirect(url_for('index')) 

    # Redirect to index, which will handle any subsequent bot turns
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 