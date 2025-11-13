# Based on student projects from CS3560.

import random
import openai
import os
from config import *
# Prevent wandb from making network calls by default during local runs
os.environ.setdefault('WANDB_MODE', 'offline')
import wandb
import json
import time

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
        # Candidate pool filtered from available words
        self.candidate_words = []
        # Keep track of guesses we've already issued to avoid repeats
        self.guessed_words_set = set()

    def reset(self):
        """Reset transient state between games."""
        self.game_history = []
        self.candidate_words = []
        self.guessed_words_set = set()

    def filter_candidates(self, game_state, available_words):
        """Filter candidates by testing MULTIPLE hypotheses about which feedback was the lie.
        
        For each guess, assume each of the 5 colors is the lie, build a model, and keep words
        that are consistent with at least one hypothesis.
        """
        candidates = [w.strip().lower() for w in available_words if w.strip()]

        for fib in game_state.guessed_words:
            guess = fib.guessed_word.lower()
            colors = fib.colors

            # Try each position as the lie; keep words consistent with any hypothesis
            consistent_words = set()
            
            for lie_pos in range(5):
                # Assume position lie_pos is the lie
                green_pos = {}
                yellow_set = set()
                
                for i, (ch, col) in enumerate(zip(guess, colors)):
                    if i == lie_pos:
                        # This is the lie; invert its meaning
                        if col == "G":
                            # Lie: letter is NOT in this position
                            pass  # Don't enforce green
                        elif col == "Y":
                            # Lie: letter is NOT in word (but we'll be lenient)
                            pass
                        elif col == "R":
                            # Lie: letter IS in word somewhere
                            yellow_set.add(ch)
                    else:
                        # This is true
                        if col == "G":
                            green_pos[i] = ch
                        elif col == "Y":
                            yellow_set.add(ch)
                        # For "R", we don't enforce absence (could be the lie elsewhere)
                
                # Now find all candidates consistent with this hypothesis
                for cand in candidates:
                    ok = True
                    # All greens must match
                    for pos, ch in green_pos.items():
                        if cand[pos] != ch:
                            ok = False
                            break
                    if not ok:
                        continue
                    # All yellows must appear somewhere
                    for ch in yellow_set:
                        if ch not in cand:
                            ok = False
                            break
                    if ok:
                        consistent_words.add(cand)
            
            # Replace candidates with those consistent with at least one hypothesis
            candidates = list(consistent_words) if consistent_words else candidates

        # Remove words we've already guessed
        candidates = [w for w in candidates if w not in self.guessed_words_set]
        return candidates

    def make_guess(self, game_state, available_words):
        """Choose a guess: deterministic first, then candidate-driven selection."""
        try:
            # Deterministic first guess
            if len(game_state.guessed_words) == 0:
                recommended = ["stare", "roast", "arose", "store", "oater"]
                for w in recommended:
                    if w in available_words and w not in self.guessed_words_set:
                        self.guessed_words_set.add(w)
                        return w

            # Build candidate list and pick first one (best filtered candidate)
            self.candidate_words = self.filter_candidates(game_state, available_words)
            
            # Pick the first valid candidate (it's already filtered)
            for w in self.candidate_words:
                if w not in self.guessed_words_set:
                    self.guessed_words_set.add(w)
                    return w

            # Fallback: any unseen valid word
            for w in available_words:
                ww = w.strip().lower()
                if len(ww) == 5 and ww.isalpha() and ww not in self.guessed_words_set:
                    self.guessed_words_set.add(ww)
                    return ww

            w = random.choice(available_words).strip().lower()
            self.guessed_words_set.add(w)
            return w

        except Exception as e:
            print(f"Error: {e}")
            for w in available_words:
                ww = w.strip().lower()
                if len(ww) == 5 and ww.isalpha() and ww not in self.guessed_words_set:
                    self.guessed_words_set.add(ww)
                    return ww
            return random.choice(available_words).strip().lower()
    
    def _prepare_context(self, game_state, candidate_words):
        """Prepare context string for GPT-3.5 with strategic prompting"""
        context = ""
        
        if len(game_state.guessed_words) == 0:
            context += """FIRST GUESS STRATEGY:
Your goal: Maximize information to identify which feedback is the lie.

Strategy:
- Choose a word with 2+ common vowels
- Use letters: R, O, A, T, E, S (highest frequency in English)
- Examples: STARE, ROAST, AROSE, STORE

Why: These letters appear in ~50% of English words. If you see them marked R, Y, or G, you eliminate many possibilities.

RECOMMENDED: Pick one of these proven first words.
"""
        
        elif len(game_state.guessed_words) == 1:
            first_guess = game_state.guessed_words[0]
            context += f"""SECOND GUESS - CRITICAL LIE DETECTION PHASE:

Your first guess: {first_guess.guessed_word.upper()} -> {first_guess.colors}

ANALYZE THE FEEDBACK:
Remember: EXACTLY ONE of these 5 colors is a LIE.

Let me show you how to think about this:

Example: If you see STARE -> [G, R, Y, R, R]
- Hypothesis A: If the G is the lie → S is NOT in position 0 (but might be elsewhere)
- Hypothesis B: If position 1 R is the lie → T IS in the word somewhere
- Hypothesis C: If position 2 Y is the lie → A is NOT in the word at all
- Hypothesis D: If position 3 R is the lie → R IS in the word somewhere
- Hypothesis E: If position 4 R is the lie → E IS in the word somewhere

Your second guess should:
1. REUSE letters marked G or Y but in DIFFERENT positions (test if lie was there)
2. INTRODUCE NEW letters (test more of the alphabet)
3. Avoid RED letters (unless one of them might be the lie)

Goal: Create a guess that will help you narrow down which feedback was false.
"""
        
        else:
            context += """SUBSEQUENT GUESS - HYPOTHESIS REFINEMENT:

You've now seen multiple rounds of feedback. Each feedback had exactly ONE lie.

STRATEGY:
1. Look for CONTRADICTIONS between guesses
   - If guess 1 said letter A is in position 2 (G), but guess 2 says A is NOT in word (R)
   - One of these must be the lie!

2. Build competing hypotheses:
   - "What if the G in round 1 was the lie?"
   - "What if the R in round 2 was the lie?"
   - Keep track of which lies are consistent

3. Use process of elimination:
   - Test hypotheses by picking words that would contradict certain feedback
   - Gradually eliminate impossible lie scenarios

4. Narrow to the truth:
   - Eventually only one hypothesis remains: that's likely the secret word
"""
        
        context += f"\nGAME HISTORY:\n"
        for i, fib in enumerate(game_state.guessed_words):
            context += f"  Guess {i+1}: {fib.guessed_word.upper()} -> {fib.colors}\n"
        
        if candidate_words:
            context += f"\nCONDIDATE WORDS THAT FIT KNOWN CONSTRAINTS:\n"
            context += f"{', '.join(w.upper() for w in candidate_words[:15])}\n"
            context += f"(These words are consistent with at least one 'lie hypothesis' from the feedback above)\n"
        
        context += f"""
INSTRUCTIONS FOR YOUR NEXT GUESS:
1. Think step-by-step about which feedback might be the lie
2. Consider words from the candidate list - they're strategically filtered
3. Pick ONE 5-letter word that will help you test your hypothesis about which feedback is false
4. Respond with ONLY the word, nothing else.

Remaining guesses: {game_state.guesses_left}
"""
        
        return context

    def make_guess(self, game_state, available_words):
        """Choose a guess using LLM with strategic prompting"""
        try:
            # Deterministic first guess (proven best strategy)
            if len(game_state.guessed_words) == 0:
                recommended = ["stare", "roast", "arose", "store", "oater"]
                for w in recommended:
                    if w in available_words and w not in self.guessed_words_set:
                        self.guessed_words_set.add(w)
                        return w

            # Build candidate list using multi-hypothesis filtering
            self.candidate_words = self.filter_candidates(game_state, available_words)
            
            # Prepare strategic context for LLM
            context = self._prepare_context(game_state, self.candidate_words)
            
            # Call LLM with strong system prompt
            system_prompt = """You are an expert at playing Fibble, a Wordle variant where exactly ONE piece of feedback per guess is a lie.

Your task: Use logical reasoning to identify which feedback is the lie and guess a word that helps you narrow down the truth.

You are highly strategic, think step-by-step, and make calculated guesses that maximize information gain."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                max_tokens=100,
                temperature=0.7,
                top_p=0.9
            )
            
            # Extract the word from response
            guess_text = response.choices[0].message.content.strip().lower()
            
            # Try to extract a valid 5-letter word from response
            words = guess_text.split()
            for word in words:
                if len(word) == 5 and word.isalpha() and word not in self.guessed_words_set:
                    self.guessed_words_set.add(word)
                    return word
            
            # If LLM response is malformed, fallback to best candidate
            for w in self.candidate_words:
                if w not in self.guessed_words_set:
                    self.guessed_words_set.add(w)
                    print(f"  [LLM response invalid, using best candidate]")
                    return w
            
            # Last resort: random from candidates
            if self.candidate_words:
                w = random.choice(self.candidate_words)
                self.guessed_words_set.add(w)
                return w
            
            # Ultimate fallback
            for w in available_words:
                ww = w.strip().lower()
                if len(ww) == 5 and ww.isalpha() and ww not in self.guessed_words_set:
                    self.guessed_words_set.add(ww)
                    return ww

        except Exception as e:
            print(f"  [LLM Error: {e}, using fallback]")
            # Fallback to algorithm
            for w in self.candidate_words:
                if w not in self.guessed_words_set:
                    self.guessed_words_set.add(w)
                    return w
            
            for w in available_words:
                ww = w.strip().lower()
                if len(ww) == 5 and ww.isalpha() and ww not in self.guessed_words_set:
                    self.guessed_words_set.add(ww)
                    return ww
        
        return random.choice(available_words).strip().lower()
    
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
    
    results = []
    
    print(f"Testing GPT-3.5 on {num_games} Fibble games...")
    
    for game_num in range(num_games):
        # create a fresh AI player for each game so state doesn't leak
        ai_player = GPTPlayer(model="gpt-4")
        ai_player.reset()
        print(f"\nGame {game_num + 1}/{num_games}")
        game_state = Game(dict_size)
        # print(f"Secret word: {game_state.secret_word}")  # Hidden for blind testing
        
        start_time = time.time()
        guesses_made = 0
        won = False
        guess_latencies = []
        
        while game_state.guesses_left > 0 and not game_state.win_state:
            # AI makes a guess and measure latency
            guess_start = time.time()
            guess = ai_player.make_guess(game_state, game_state.WORDS)
            guess_latency = time.time() - guess_start
            guess_latencies.append(guess_latency)
            print(f"AI guesses: {guess.upper()} ({guess_latency:.3f}s)")
            
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
        avg_latency = sum(guess_latencies) / len(guess_latencies) if guess_latencies else 0
        
        result = {
            'game_number': game_num + 1,
            'won': won,
            'guesses_used': guesses_made,
            'secret_word': game_state.secret_word,
            'game_time': game_time,
            'avg_guess_latency': avg_latency,
            'total_guess_latency': sum(guess_latencies)
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
    total_latency = sum(r['total_guess_latency'] for r in results)
    avg_latency_all = sum(r['avg_guess_latency'] for r in results) / num_games
    total_game_time = sum(r['game_time'] for r in results)
    
    print(f"\n=== GPT-3.5 Performance Summary ===")
    print(f"Games played: {num_games}")
    print(f"Wins: {wins} ({win_rate:.1%})")
    print(f"Average guesses when winning: {avg_guesses:.1f}")
    print(f"\n=== Latency Metrics ===")
    print(f"Average latency per guess: {avg_latency_all:.3f}s")
    print(f"Total latency (all guesses): {total_latency:.2f}s")
    print(f"Total game time: {total_game_time:.2f}s")
    
    if log_to_wandb:
        wandb.log({
            "final_win_rate": win_rate,
            "total_games": num_games,
            "total_wins": wins,
            "avg_guesses_when_winning": avg_guesses,
            "avg_latency_per_guess": avg_latency_all,
            "total_latency": total_latency,
            "total_game_time": total_game_time
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

