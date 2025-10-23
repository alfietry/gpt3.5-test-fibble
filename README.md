# Fibble GPT-3.5 Testing

A modified version of the Fibble word game (Wordle variant with lies) that includes GPT-3.5 AI testing capabilities.

## Overview

Fibble is a Wordle-like game where players guess 5-letter words, but with a twist: **exactly one piece of feedback per guess is a lie**. This makes it significantly more challenging than standard Wordle.

## Features

- **Original Human Game**: Play Fibble interactively in the terminal
- **GPT-3.5 AI Testing**: Automated testing of GPT-3.5's performance on Fibble
- **WandB Integration**: Experiment tracking and performance logging
- **Performance Metrics**: Win rate, average guesses, latency tracking

## Installation

1. Clone this repository:
```bash
git clone https://github.com/alfietry/fibble-gpt-testing.git
cd fibble-gpt-testing
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install openai wandb
```

4. Set up your API keys:
   - Edit `config.py` and add your OpenAI API key
   - Run `wandb login` for experiment tracking

## Usage

### Play Human Game
```bash
python fibble.py
```

### Test GPT-3.5 AI
```bash
# Test on 10 games (default)
python fibble.py --test-ai

# Test on custom number of games
python fibble.py --test-ai 20
```

## Performance Results

**Fibble-1 Performance Table**
(Max 9 tries, one lie, average of 10 games)

| Model | Win Rate | No. of games | Avg Tries | Avg Latency | Bad Guesses | Link to WandB | By Whom |
|-------|----------|--------------|-----------|-------------|-------------|---------------|---------|
| gpt-3.5-turbo | 0% | 10 | 9.0 | 4.3s avg | 0 | [WandB Run](https://wandb.ai/bremen/fibble-gpt-testing/) | alfietry |

## Key Findings

- GPT-3.5 struggled significantly with Fibble's deceptive feedback mechanism
- 0% win rate across 10 games, using all 9 available guesses each time
- All guesses were valid 5-letter words (no invalid attempts)
- The "one lie per feedback" mechanic appears to break standard Wordle-solving strategies

## Files

- `fibble.py` - Main game implementation with GPT-3.5 integration
- `config.py` - Configuration file for API keys
- `5-letter-words.txt` - Dictionary of valid 5-letter words
- Requirements: `openai`, `wandb`, standard Python libraries

## Game Rules

1. Guess a 5-letter word
2. Get color-coded feedback:
   - **Green (G)**: Correct letter, correct position
   - **Yellow (Y)**: Correct letter, wrong position  
   - **Red (R)**: Letter not in the word
3. **Important**: Exactly ONE color in each feedback line is a lie!
4. You have 9 total attempts

## Contributing

Feel free to fork this repository and experiment with different AI models or improve the GPT-3.5 prompting strategy.

## License

Based on student projects from CS3560. Educational use.