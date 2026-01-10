import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing models...")
# Note: google-genai SDK listing might differ.
# Trying to just list models from V1Beta or V1
for m in client.models.list(config={"query_base": True}): # hypothetical
    print(m.name)

