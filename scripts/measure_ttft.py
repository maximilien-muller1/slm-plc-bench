import time                                            # chronomètre
from slm_plc_bench.llm import client                   # on réutilise le client créé dans llm.py

MODEL = "qwen2.5-coder:7b"                             # modèle testé
SHORT = "Write a Structured Text FUNCTION_BLOCK that counts parts."          # prompt court
LONG = "Context: the conveyor moves parts to a sensor. " * 300 + SHORT       # prompt long : une phrase répétée 300 fois

def ttft(prompt: str) -> float:
    start = time.perf_counter()                        # départ du chrono
    stream = client.chat.completions.create(           # même appel qu'avant...
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0, stream=True)                    # ...mais en streaming : la réponse arrive morceau par morceau
    for chunk in stream:                               # on parcourt les morceaux au fur et à mesure qu'ils arrivent
        if chunk.choices and chunk.choices[0].delta.content:   # le premier morceau qui contient du texte
            elapsed = time.perf_counter() - start               # temps jusqu'au premier token
            stream.close()                                      # coupe la connexion : le serveur arrête de générer
            return elapsed 

    return float("nan")                                # cas où aucun texte n'est arrivé ("nan" = pas un nombre)

if __name__ == "__main__":
    ttft(SHORT)                                        # préchauffage, résultat ignoré                                 
    for _ in range(3):                                 # 3 mesures alternées court / long
        print(f"court {ttft(SHORT):.2f} s, long {ttft(LONG):.2f} s")   # le long suit toujours un court : pas de cache
    first = ttft(LONG)                                 # bonus : un prompt long...
    second = ttft(LONG)                                # ...puis le MÊME juste après
    print(f"long puis long : {first:.2f} s puis {second:.2f} s")       # si le 2e est bien plus rapide : cache de préfixe`