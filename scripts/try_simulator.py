from slm_plc_bench.st import compile_st, Simulator, STError   # le compilateur et le simulateur de Structured Text, le type d'erreur levé par le simulateur


CODE = """
FUNCTION_BLOCK FB_Moteur                         (* bloc fonction réutilisable de commande moteur *)
VAR_INPUT                                        (* entrées fournies par l'appelant *)
    Marche : BOOL;                               (* bouton marche, impulsion *)
    Arret : BOOL;                                (* bouton arrêt câblé en contact fermé : FALSE = appuyé *)
    ArretUrgence : BOOL;                         (* TRUE = arrêt d'urgence actif *)
    RetourMarche : BOOL;                         (* capteur confirmant que le moteur tourne *)
END_VAR
VAR_OUTPUT                                       (* sorties lues par l'appelant *)
    Moteur : BOOL;                               (* commande du contacteur moteur *)
    Defaut : BOOL;                               (* TRUE si le moteur ne démarre pas *)
END_VAR
VAR                                              (* variables internes, gardées d'un cycle à l'autre *)
    Tempo : TON;                                 (* temporisation au travail standard *)
END_VAR

IF ArretUrgence OR NOT Arret OR Defaut THEN      (* les conditions d'arrêt sont prioritaires *)
    Moteur := FALSE;                             (* on coupe le moteur *)
ELSIF Marche THEN                                (* sinon, un appui sur marche... *)
    Moteur := TRUE;                              (* ...démarre le moteur (auto-maintien) *)
END_IF;

Tempo(IN := Moteur AND NOT RetourMarche, PT := T#5S);  (* compte tant que commandé mais sans retour *)
Defaut := Tempo.Q;                               (* au bout de 5 s sans retour : défaut *)
END_FUNCTION_BLOCK                               (* fin du bloc *)
"""
# Trois copies du code correct, chacune avec UNE erreur volontaire
BAD_SEMICOLON = CODE.replace("Moteur := FALSE;", "Moteur := FALSE", 1)    # point-virgule oublié (1 = seulement la 1re occurrence)
BAD_UNDECLARED = CODE.replace("Moteur := TRUE;", "Moteur := Demarrage;", 1)   # variable jamais déclarée
BAD_LOOP = CODE.replace(                               # boucle bloquante insérée juste avant la fin du bloc
    "END_FUNCTION_BLOCK",
    "WHILE NOT RetourMarche DO\n    Moteur := TRUE;\nEND_WHILE;\nEND_FUNCTION_BLOCK",   # \n = retour à la ligne dans le texte
    1)

ERRORS = {                                             # dictionnaire : description -> code faux
    "point-virgule oublié": BAD_SEMICOLON,
    "variable non déclarée": BAD_UNDECLARED,
    "boucle WHILE": BAD_LOOP,
}

print()                                                # ligne vide pour séparer de la séquence précédente
for description, bad_code in ERRORS.items():           # .items() donne les paires (clé, valeur) du dictionnaire
    try:                                               # on essaie de compiler...
        compile_st(bad_code)                           # ...le code faux
        print(description, "-> AUCUNE ERREUR détectée (problème !)")   # ne devrait jamais s'afficher
    except STError as error:                           # le simulateur a détecté l'erreur
        print(description, "->", error)                # affiche le message au lieu de planter.

fb = compile_st(CODE)                                  # lexer + parser + vérifications : renvoie le bloc vérifié
sim = Simulator(fb)                                    # crée une instance du bloc, prête à être exécutée

# Moment 1 : appui sur Marche
sim.set_inputs({"Marche": True, "Arret": True, "ArretUrgence": False, "RetourMarche": False})  # Arrêt non appuyé (contact fermé = True)
sim.scan()                                             # exécute UN cycle automate : c'est ici que les sorties sont calculées
print("1. appui Marche    ->", sim.read("Moteur"))     # attendu : True

# Moment 2 : on relâche Marche
sim.set_inputs({"Marche": False})                      # seule l'entrée qui change ; les autres gardent leur valeur
sim.scan()                                             # un nouveau cycle
print("2. relâche Marche  ->", sim.read("Moteur"))     # attendu : True (auto-maintien)

# Moment 3 : appui sur Arrêt
sim.set_inputs({"Arret": False})                       # contact fermé : appuyer = False
sim.scan()                                             # un nouveau cycle
print("3. appui Arrêt     ->", sim.read("Moteur"))     # attendu : False (l'arrêt est prioritaire)