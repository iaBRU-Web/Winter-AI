% Winter AI -- Prolog Knowledge Engine (SWI-Prolog)
% Real facts + rules with unification and backtracking.
% Usage: swipl knowledge.pl <lang> <token1> <token2> ...
:- initialization(main, main).

keyword(greeting, en, hello). keyword(greeting, en, hi). keyword(greeting, en, hey).
keyword(greeting, fr, bonjour). keyword(greeting, fr, salut).
keyword(greeting, rw, muraho). keyword(greeting, rw, bite).
keyword(thanks, en, thanks). keyword(thanks, en, thank).
keyword(thanks, fr, merci). keyword(thanks, rw, murakoze).
keyword(identity, en, who). keyword(identity, en, name). keyword(identity, en, yourself).
keyword(identity, fr, qui). keyword(identity, rw, witwa).
keyword(wellbeing, en, how). keyword(wellbeing, en, doing).
keyword(wellbeing, fr, comment). keyword(wellbeing, rw, amakuru).
keyword(farewell, en, bye). keyword(farewell, en, goodbye).
keyword(farewell, rw, murabeho). keyword(farewell, fr, revoir).
keyword(help, en, help). keyword(help, en, assist).
keyword(help, fr, aide). keyword(help, rw, saidia).

translate(hello, en, bonjour, fr). translate(hello, en, muraho, rw).
translate(thanks, en, merci, fr). translate(thanks, en, murakoze, rw).
translate(good, en, bon, fr). translate(good, en, byiza, rw).
translate(friend, en, ami, fr). translate(friend, en, inshuti, rw).
translate(water, en, eau, fr). translate(water, en, amazi, rw).
translate(yes, en, oui, fr). translate(yes, en, yego, rw).
translate(no, en, non, fr). translate(no, en, oya, rw).
translate(bonjour, fr, muraho, rw). translate(merci, fr, murakoze, rw).

translate_chain(W, L1, T, L2) :- translate(W, L1, T, L2).
translate_chain(W, L1, T, L2) :- translate(W, L1, Mid, Lm), Lm \= L2, translate(Mid, Lm, T, L2).

matched_intents(Lang, Tokens, Intents) :-
    findall(I, (member(T, Tokens), keyword(I, Lang, T)), Raw),
    list_to_set(Raw, Intents).

main(Argv) :-
    (Argv = [LA|TA] -> true ; LA = en, TA = []),
    atom_string(Lang, LA),
    maplist(atom_string, TAtoms, TA),
    (matched_intents(Lang, TAtoms, Intents) -> true ; Intents = []),
    format("ENGINE: Prolog (SWI-Prolog)~n"),
    format("MATCHED_INTENTS: ~w~n", [Intents]),
    (TAtoms = [FT|_], translate_chain(FT, en, TR, rw), TR \= FT
     -> format("BACK_TRANSLATION: ~w -> rw:~w~n", [FT, TR])
     ;  format("BACK_TRANSLATION: none~n")),
    format("TRACE: findall(I,(member(T,Tokens),keyword(I,~w,T)),Raw),list_to_set(Raw,Intents)~n", [Lang]),
    halt.
main(_) :- halt.
