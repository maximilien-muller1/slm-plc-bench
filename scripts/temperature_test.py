from slm_plc_bench.llm import complete                 # ton client

MODEL = "qwen2.5-coder:1.5b"                           # petit modèle : le test est plus rapide
PROMPT = "Write a Structured Text FUNCTION_BLOCK that counts parts passing in front of a sensor."
RUNS = 5                                               # nombre de réponses par température

def distinct_answers(temperature: float) -> int:
    answers = []                                       # liste des textes obtenus
    for _ in range(RUNS):                              # RUNS appels identiques
        result = complete(MODEL, [{"role": "user", "content": PROMPT}], temperature=temperature)  # même prompt, température choisie
        answers.append(result.text)                    # on garde le texte de la réponse
    return len(set(answers))   
    

if __name__ == "__main__":
    complete(MODEL, [{"role": "user", "content": "Say hello"}])   # préchauffage
    for temp in [0 , 0.8]: 
        n = distinct_answers(temp)
        print(f"température {temp} : {n} réponse(s) différente(s) sur {RUNS}")  
    
        