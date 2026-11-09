"""Liste les modèles Groq disponibles pour votre clé."""
import os
from dotenv import load_dotenv
load_dotenv()

from groq import Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
models = client.models.list()
for m in models.data:
    print(f"- {m.id} (owned_by: {m.owned_by})")
