# Étape 0 — Notes

## Questions de compréhension

### 1. Que veut dire « 1.5b » ? Taille théorique en 4 bits vs taille réelle
- « 1.5b » = environ 1,5 milliard de paramètres (en réalité ~1,54 milliard).
- Théorie en 4 bits : 1,5 × 10⁹ × 0,5 octet = 0,75 Go.
- Mesuré : 986 Mo, soit environ 5,1 bits par paramètre.
- L'écart vient de la quantification : une échelle stockée par groupe de poids,
  et certaines couches sensibles (embeddings, couche de sortie) gardées en plus
  haute précision. Vérifiable avec `ollama show qwen2.5-coder:1.5b`.

### 2. Intérêt d'une API compatible OpenAI pour le projet
- Une seule fonction Python pour appeler le petit modèle local ET le grand modèle
  distant : on change seulement `base_url` et le nom du modèle.
- Comparaison équitable : même code, mêmes prompts, mêmes mesures.
- On peut changer de moteur (Ollama, llama.cpp, vLLM, fournisseurs cloud)
  sans réécrire le projet.

### 3. `prompt_tokens` vs `completion_tokens` : lequel coûte le plus de temps ?
- `prompt_tokens` = tokens lus (le message), `completion_tokens` = tokens générés.
- Les tokens générés coûtent plus de temps par token :
  - le prompt est traité en une seule passe parallèle (prefill) ;
  - la réponse est générée un token à la fois, et chaque token oblige à relire
    tous les poids en mémoire (décodage limité par la bande passante mémoire).
- Les API facturent aussi plus cher les tokens de sortie.

### 4. Pourquoi ne jamais committer une clé d'API, et comment l'éviter ?
- Des robots scannent GitHub en permanence pour voler les clés et les utiliser
  à nos frais.
- Une clé reste dans l'historique Git même si on la supprime ensuite.
- Bonne pratique : la clé dans un fichier `.env` (variable d'environnement),
  `.env` dans le `.gitignore`, le code la lit avec `os.environ`.
- Si une clé fuit : la révoquer immédiatement chez le fournisseur.

## Observations sur la réponse JSON du modèle
1. 38 tokens de prompt pour 8 mots : le serveur ajoute un gabarit de conversation
   (rôles, tokens spéciaux) qui compte dans le coût.
2. Le modèle n'a pas respecté la consigne (bloc « vide » demandé, 2 variables
   ajoutées) : premier exemple d'écart à la spécification d'un petit modèle.
3. Environ 2/3 des 126 tokens générés sont du texte d'explication : à éviter
   dans le prompt (« uniquement le code ») pour gagner du temps.
4. Le bloc de code est marqué ```structuredtext : l'extraction du code devra
   accepter toutes les variantes (st, iecst, aucune balise...).
5. `finish_reason: "stop"` = fin normale ; `"length"` = réponse coupée,
   code incomplet à gérer dans le vérificateur.
   