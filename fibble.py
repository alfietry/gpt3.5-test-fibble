# Based on student projects from CS3560.

import random
import openai
import wandb
import json
import time
from config import *

def get_words(dict_size = 0):
    with open('5-letter-words.txt','r') as f:
        ALL_WORDS = f.read().split('\n')
        f.close()
    if dict_size == 0:
        return ALL_WORDS
    return ALL_WORDS[0:dict_size]
    
def choose_word(ALL_WORDS):
    return random.choice(ALL_WORDS).strip()

class Game:
    def __init__(self,dict_size=0):
        self.WORDS = get_words(dict_size)
        self.secret_word = choose_word(self.WORDS)
        self.guesses_left = 9
        # Array of Fib classes, i.e. guessed words, and their respective colors (w/ lie)
        self.guessed_words = [] 
        self.win_state=False
        self.current_word = "" 
    def make_guess(self, guess):
        # Return T/F based whether guess is valid
        guess = guess.lower() #For consistencies sake work with lower cases
        #Enter win state for correct guess
        if guess == self.secret_word: 
            self.win_state=True
            tmp = self.evaluate_word(guess)
            self.guessed_words.append(tmp)
            return True
        #Input validation
        if len(guess) != 5 or not guess in self.WORDS: 
            return False # Invalid guess
        self.guesses_left -= 1
        tmp = self.evaluate_word(guess) #Convert guess to Fib type
        tmp.make_lie() # generate lie
        self.guessed_words.append(tmp) # add to history
        return True # Valid guess
    def evaluate_word(self, guess, secret=""): # Return true state of word
        if secret == "":
            secret = self.secret_word
        return_fib = Fib(guess)
        for index, tmp in enumerate(zip(guess, secret)):
            guessed_letter, secret_letter = tmp
            # Iterate through each letter of secret word & guessed word
            if guessed_letter == secret_letter:
                return_fib.colors.append("G")
            elif guessed_letter in secret:

                count_letters_in_secret_word = secret.count(guessed_letter)
                count_letters_in_guess = guess[0:index].count(guessed_letter)
                
                for i, j in zip(guess, secret):
                    if i != guessed_letter: continue
                    if i == j:
                        count_letters_in_guess += 1 # discount greens from yellows

                if count_letters_in_guess < count_letters_in_secret_word:
                    return_fib.colors.append("Y")
                else:
                    return_fib.colors.append("R")
                # May need fixed later to adjust amount of yellows generated
                # e.g. how many yellows should "Month" show for guess "Mamma"?
            else:
                return_fib.colors.append("R")
        return return_fib
    def reset(self):
        self.secret_word = choose_word(self.WORDS)
        self.guesses_left = 9
        # Array of Fib classes, i.e. guessed words, and their respective colors (w/ lie)
        self.guessed_words = [] 
        self.win_state=False
        self.current_word = ""
    def __contains__(self, word):
        return any([i == word for i in self.guessed_words])

class Fib: # The Fibble Game
    #Class to track Guessed words, as well as colors at their respective position
    def __init__(self, guessed_word):
        self.colors = [] #["G","G","Y","Y","R"]
        self.guessed_word = guessed_word # ['s','t','r','a','p']
        #lie_position=0
        #lie_color=""
    def make_lie(self):
        #Randomly create lie at one position
        lie_position = random.randint(0,4)
        if self.colors[lie_position] == "G":
            self.colors[lie_position] = random.choice(["Y","R"])
        elif self.colors[lie_position] == "Y":
            self.colors[lie_position] = random.choice(["G","R"])
        elif self.colors[lie_position] == "R":
            self.colors[lie_position] = random.choice(["Y","G"])
    def __eq__(self, word: str) -> bool:
        return self.guessed_word.lower() == word.lower()
    def __repr__(self):
        return self.colors

class GPTPlayer:
    """AI Player that uses GPT-3.5 to play Fibble"""
    def __init__(self, model="gpt-3.5-turbo"):
        self.model = model
        self.client = openai.OpenAI()
        self.game_history = []
        
    def make_guess(self, game_state, available_words):
        """Use GPT-3.5 to make a guess based on game history"""
        try:
            # Prepare context for GPT-3.5
            context = self._prepare_context(game_state, available_words)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are playing Fibble, a Wordle-like game where there is exactly one lie in each feedback. Green (G) means correct letter and position, Yellow (Y) means correct letter but wrong position, Red (R) means letter not in word. However, ONE of these colors in each guess is a lie. Make your best guess for a 5-letter word."},
                    {"role": "user", "content": context}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            guess = response.choices[0].message.content.strip().lower()
            # Extract only the 5-letter word from response
            words = guess.split()
            for word in words:
                if len(word) == 5 and word.isalpha():
                    return word
            
            # Fallback to random word if GPT response is invalid
            return random.choice(available_words[:100]).lower().strip()
            
        except Exception as e:
            print(f"GPT Error: {e}")
            return random.choice(available_words[:100]).lower().strip()
    
    def _prepare_context(self, game_state, available_words):
        """Prepare context string for GPT-3.5"""
        context = "Game state:\n"
        
        if len(game_state.guessed_words) == 0:
            context += "This is your first guess. Choose a good starting 5-letter word.\n"
        else:
            context += "Previous guesses and feedback (remember, one color per line is a lie):\n"
            for fib in game_state.guessed_words:
                context += f"Word: {fib.guessed_word.upper()}, Colors: {fib.colors}\n"
        
        context += f"\nYou have {game_state.guesses_left} guesses remaining.\n"
        context += "Respond with only a single 5-letter word as your guess."
        
        return context

CLEAR="\033[0m"
RED="\033[91m"
GREEN="\033[92m"
YELLOW="\033[93m"

def ouput_fib(fib):
    '''
    Helper function to output a guessed word with colors
    '''
    print("Feedback  :", end= " ")
    for letter,letter_color in zip(fib.guessed_word, fib.colors):
        letter= letter.upper()
        if letter_color == "R":
            print(RED + letter + CLEAR, end= "")
        if letter_color == "G":
            print(GREEN + letter + CLEAR, end="")
        if letter_color == "Y":
            print(YELLOW + letter + CLEAR,end="")
    print()

# Main game loop"
def play_fibble():
    '''
    Plays fibble game interactively in the terminal
    Allows user to make guesses
    '''
    gamestate = Game()
    #print(gamestate.secret_word)
    print("Welcome to Fibble! (https://fibble.xyz/)")
    print("Try to guess a 5-letter word. You have 8 attempts after the first random guess.")
    print("There is exactly one lie in each line of feedback.")

    print(f"--DEBUG: Secret word: [{gamestate.secret_word}]")
    gamestate.make_guess(choose_word(gamestate.WORDS))
    last = gamestate.guessed_words[-1]
    ouput_fib(last)
    while gamestate.guesses_left > 0:
        while not gamestate.make_guess(input("Your guess: ").lower().replace(" ", "")):
            print("Invalid guess\n")
        if gamestate.win_state:
            ouput_fib(gamestate.guessed_words[-1])
            break
        last = gamestate.guessed_words[-1]
        ouput_fib(last)
        print(f"{gamestate.guesses_left} guesses remaining...\n")
    if gamestate.guesses_left == 0:
        print("You lose")
        print("The secret word was: ", gamestate.secret_word)
    else:
        print("You win!")

def test_gpt_player(num_games=10, dict_size=0, log_to_wandb=True):
    """Test GPT-3.5 player performance over multiple games"""
    
    if log_to_wandb:
        wandb.init(project="fibble-gpt-testing", 
                  config={"model": "gpt-3.5-turbo", "num_games": num_games, "dict_size": dict_size})
    
    ai_player = GPTPlayer()
    results = []
    
    print(f"Testing GPT-3.5 on {num_games} Fibble games...")
    
    for game_num in range(num_games):
        print(f"\nGame {game_num + 1}/{num_games}")
        game_state = Game(dict_size)
        print(f"Secret word: {game_state.secret_word}")
        
        start_time = time.time()
        guesses_made = 0
        won = False
        
        while game_state.guesses_left > 0 and not game_state.win_state:
            # AI makes a guess
            guess = ai_player.make_guess(game_state, game_state.WORDS)
            print(f"AI guesses: {guess.upper()}")
            
            if game_state.make_guess(guess):
                guesses_made += 1
                if game_state.win_state:
                    won = True
                    break
                # Show feedback
                last_fib = game_state.guessed_words[-1]
                print(f"Feedback: {last_fib.guessed_word.upper()} -> {last_fib.colors}")
            else:
                print("Invalid guess, trying another...")
        
        game_time = time.time() - start_time
        
        result = {
            'game_number': game_num + 1,
            'won': won,
            'guesses_used': guesses_made,
            'secret_word': game_state.secret_word,
            'game_time': game_time
        }
        results.append(result)
        
        if won:
            print(f"✓ Won in {guesses_made} guesses!")
        else:
            print(f"✗ Lost. Secret was: {game_state.secret_word}")
        
        if log_to_wandb:
            wandb.log(result)
    
    # Summary statistics
    wins = sum(1 for r in results if r['won'])
    win_rate = wins / num_games
    avg_guesses = sum(r['guesses_used'] for r in results if r['won']) / max(wins, 1)
    
    print(f"\n=== GPT-3.5 Performance Summary ===")
    print(f"Games played: {num_games}")
    print(f"Wins: {wins} ({win_rate:.1%})")
    print(f"Average guesses when winning: {avg_guesses:.1f}")
    
    if log_to_wandb:
        wandb.log({
            "final_win_rate": win_rate,
            "total_games": num_games,
            "total_wins": wins,
            "avg_guesses_when_winning": avg_guesses
        })
        wandb.finish()
    
    return results

#play fibble function
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test-ai":
        # Run AI testing
        num_games = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        test_gpt_player(num_games=num_games)
    else:
        # Run human game
        play_fibble()
    
