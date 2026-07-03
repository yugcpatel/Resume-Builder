"""
Helper script to query and display all available Google GenAI models accessible by the current API key.
"""
from google import genai
import os
from utils import load_env

def list_available_models():
    """
    Connects to the Google GenAI SDK and prints the names of all models available for inference and embedding.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, '.env')
    load_env(env_path)
    
    client = genai.Client()
    print("Available Models:")
    try:
        for model in client.models.list_models():
            print(model.name)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_available_models()
