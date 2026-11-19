import time                                            # chronomètre
import uuid                                            # NOUVEAU : génère des identifiants aléatoires uniques
from slm_plc_bench.llm import client, complete         # NOUVEAU : on importe aussi complete (pour compter les tokens)

MODEL = "qwen2.5-coder:7b"                             # modèle testé
SHORT = "Write a Structured Text FUNCTION_BLOCK that counts parts."          # prompt court
LONG = "Context: the conveyor moves parts to a sensor. " * 300 + SHORT       # prompt long : une phrase répétée 300 fois

def unique(prompt: str) -> str:                        # NOUVEAU : rend un prompt unique
    return f"Request {uuid.uuid4()}.\n" + prompt       # identifiant différent AU DÉBUT : aucun préfixe commun avec le cache

def ttft(prompt: str) -> float:
    start = time.perf_counter()                        # départ du chrono
    stream = client.chat.completions.create(           # même appel qu'avant...
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0, stream=True)                    # ...mais en streaming : la réponse arrive morceau par morceau
    for chunk in stream:                               # on parcourt les morceaux au fur et à mesure qu'ils arrivent
        if chunk.choices and chunk.choices[0].delta.content:   # le premier morceau qui contient du texte
            elapsed = time.perf_counter() - start               # temps jusqu'au premier token
            stream.close()                                      # coupe la connexion : le serveur arrête de générer
            return elapsed                                      # renvoie la mesure
    return float("nan")                                # cas où aucun texte n'est arrivé ("nan" = pas un nombre)

if __name__ == "__main__":
    ttft(unique(SHORT))                                # préchauffage, résultat ignoré
    tokens = complete(MODEL, [{"role": "user", "content": unique(LONG)}]).prompt_tokens   # NOUVEAU : taille réelle du prompt long
    print(f"prompt long : {tokens} tokens")            # NOUVEAU : affichage de cette taille
    for _ in range(3):                                 # 3 mesures sans cache
        print(f"court {ttft(unique(SHORT)):.2f} s, long {ttft(unique(LONG)):.2f} s")   # MODIFIÉ : chaque prompt est unique
    first = ttft(LONG)                                 # bonus, SANS unique : un prompt long...
    second = ttft(LONG)                                # ...puis exactement le même juste après
    print(f"long puis long : {first:.2f} s puis {second:.2f} s")   # si le 2e est bien plus rapide : cache de préfixe