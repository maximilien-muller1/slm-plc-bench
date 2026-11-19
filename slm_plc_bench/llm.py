import time                                       # pour mesurer les durées
from dataclasses import dataclass                 # pour renvoyer un résultat structuré
from openai import OpenAI                         # client compatible OpenAI, marche aussi avec Ollama

@dataclass
class Completion:                                 # ce que renvoie un appel au modèle
    text: str                                     # texte généré
    prompt_tokens: int                            # nombre de tokens lus (le prompt)
    completion_tokens: int                        # nombre de tokens générés
    latency_s: float                              # durée totale de l'appel, en secondes

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")  # Ollama ignore la clé, mais le client en exige une

def complete(model: str, messages: list[dict], temperature: float = 0.0) -> Completion:
    start = time.perf_counter()                          # chronomètre lancé juste avant l'appel
    response = client.chat.completions.create(           # envoie la requête HTTP au serveur Ollama
        model=model, messages=messages, temperature=temperature)
    latency = time.perf_counter() - start                # durée totale de l'appel, en secondes
    text = response.choices[0].message.content or ""     # texte généré ("" si le modèle n'a rien renvoyé)
    usage = response.usage                               # bloc des compteurs de tokens
    return Completion(                                   # on regroupe tout dans l'objet résultat
        text=text,                                       # le texte
        prompt_tokens=usage.prompt_tokens,               # tokens lus
        completion_tokens=usage.completion_tokens,       # tokens générés
        latency_s=latency,                               # la durée mesurée
    )

def throughput(completion_tokens: int, latency_s: float) -> float:
    """Débit en tokens par seconde."""                  
    if latency_s <= 0:                                     # cas impossible en pratique, mais on se protège
        raise ValueError("latency must be positive")      # erreur explicite plutôt qu'une division par zéro
    return completion_tokens / latency_s                   # le calcul lui-même