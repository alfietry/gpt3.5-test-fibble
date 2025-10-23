import os

# Set your OpenAI API key here or as environment variable
if 'OPENAI_API_KEY' not in os.environ:
    os.environ['OPENAI_API_KEY'] = 'your_openai_api_key_here'  # Replace with your actual API key

# Wandb configuration
WANDB_PROJECT = 'fibble-gpt-testing'