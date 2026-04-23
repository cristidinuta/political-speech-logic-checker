% ============================================================
%  LOGICWATCH — FALLACY DETECTION KNOWLEDGE BASE
%  Uses SWI-Prolog with DCGs for linguistic feature extraction
%  and rule-based fallacy detection
% ============================================================

:- discontiguous fallacy/3.
:- discontiguous claim/2.
:- discontiguous has_feature/2.
:- dynamic claim/2.
:- dynamic has_feature/2.

% ============================================================
%  DCG — Definite Clause Grammars for sentence tokenization
%  and linguistic pattern recognition
% ============================================================

% Tokenize a sentence string into a list of lowercase word atoms
tokenize(Sentence, Tokens) :-
    string_lower(Sentence, Lower),
    split_string(Lower, " \t\n,.:;!?\"'()-", " \t\n,.:;!?\"'()-", Parts),
    include([P]>>(P \= ""), Parts, NonEmpty),
    maplist(atom_string, Tokens, NonEmpty).

% DCG: detect "either ... or ..." binary choice pattern
binary_choice_phrase --> [either], any_words, [or], any_words.
binary_choice_phrase --> [if], any_words, [then], any_words.

% DCG: detect consequence chain markers
consequence_marker --> [leads], [to].
consequence_marker --> [will], [lead], [to].
consequence_marker --> [will], [result], [in].
consequence_marker --> [soon], any_words, [will].
consequence_marker --> [eventually].

% DCG: detect authority citation patterns  
authority_phrase --> [according], [to], any_words.
authority_phrase --> [endorsed], [by].
authority_phrase --> [supported], [by].

% DCG: detect attack on person patterns
attack_phrase --> [my], [opponent], any_words.
attack_phrase --> any_words, [arrested], any_words.
attack_phrase --> any_words, [embezzl], any_words.
attack_phrase --> any_words, [corrupt], any_words.
attack_phrase --> any_words, [liar], any_words.
attack_phrase --> any_words, [criminal], any_words.

% DCG: detect generalization markers
generalization_marker --> [everyone].
generalization_marker --> [nobody].
generalization_marker --> [always].
generalization_marker --> [never].
generalization_marker --> [every], [single].
generalization_marker --> [all], [of], [them].

% Helper: match any sequence of words (0 or more)
any_words --> [].
any_words --> [_], any_words.

% DCG-based feature check: succeeds if DCG rule matches token list
dcg_matches(Rule, Tokens) :-
    phrase(Rule, Tokens, _).
dcg_matches(Rule, Tokens) :-
    append(_, Rest, Tokens),
    Rest \= [],
    phrase(Rule, Rest, _).

% ============================================================
%  FALLACY RULES
%  Combine Python-detected features AND DCG verification
% ============================================================

% AD HOMINEM: attack on person + ignores their argument
fallacy(Id, ad_hominem,
    'Attacks the character or personal traits of an opponent rather than addressing their actual argument.') :-
    claim(Id, _),
    has_feature(Id, attacks_person),
    has_feature(Id, ignores_argument).

% FALSE DILEMMA: binary choice with no alternatives acknowledged
fallacy(Id, false_dilemma,
    'Presents only two possible options, ignoring other valid alternatives.') :-
    claim(Id, _),
    has_feature(Id, binary_choice),
    \+ has_feature(Id, acknowledges_alternatives).

% SLIPPERY SLOPE: chain of consequences ending in extreme outcome, no evidence
fallacy(Id, slippery_slope,
    'Assumes that one event will inevitably lead to extreme negative consequences without sufficient justification.') :-
    claim(Id, _),
    has_feature(Id, chain_of_consequences),
    has_feature(Id, extreme_endpoint),
    \+ has_feature(Id, causal_evidence).

% HASTY GENERALIZATION: sweeping claim from limited sample
fallacy(Id, hasty_generalization,
    'Draws a broad general conclusion from a limited or unrepresentative sample of evidence.') :-
    claim(Id, _),
    has_feature(Id, broad_generalization),
    has_feature(Id, limited_sample).

% STRAW MAN: misrepresent then attack the misrepresentation
fallacy(Id, straw_man,
    'Misrepresents or exaggerates an opponent\'s position, then attacks that distorted version.') :-
    claim(Id, _),
    has_feature(Id, misrepresents_opponent),
    has_feature(Id, attacks_misrepresentation).

% APPEAL TO AUTHORITY: cite authority without relevant evidence
fallacy(Id, appeal_to_authority,
    'Cites an authority figure as definitive proof without sufficient supporting evidence or relevant expertise.') :-
    claim(Id, _),
    has_feature(Id, cites_authority),
    ( has_feature(Id, irrelevant_authority)
    ; has_feature(Id, no_supporting_evidence)
    ).

% RED HERRING: divert topic, ignore main issue
fallacy(Id, red_herring,
    'Introduces irrelevant information or arguments to distract from the actual issue being discussed.') :-
    claim(Id, _),
    has_feature(Id, topic_diversion),
    has_feature(Id, ignores_main_issue).

% ============================================================
%  DCG-ENHANCED VERIFICATION
%  These rules use DCG to double-check Python features
%  by re-parsing the claim text at the Prolog level
% ============================================================

% Verify binary_choice using DCG on actual token stream
dcg_verify_binary(Id) :-
    claim(Id, Text),
    tokenize(Text, Tokens),
    dcg_matches(binary_choice_phrase, Tokens).

% Verify slippery slope chain using DCG
dcg_verify_chain(Id) :-
    claim(Id, Text),
    tokenize(Text, Tokens),
    dcg_matches(consequence_marker, Tokens).

% Extended false dilemma: also fires if DCG detects binary pattern
% even if Python missed it
fallacy(Id, false_dilemma,
    'Presents only two possible options, ignoring other valid alternatives. (DCG-detected)') :-
    claim(Id, _),
    dcg_verify_binary(Id),
    \+ has_feature(Id, acknowledges_alternatives),
    \+ has_feature(Id, binary_choice). % avoid duplicate

% Extended slippery slope: DCG verifies chain marker
fallacy(Id, slippery_slope,
    'Assumes that one event will lead to extreme consequences without justification. (DCG-verified)') :-
    claim(Id, _),
    dcg_verify_chain(Id),
    has_feature(Id, extreme_endpoint),
    \+ has_feature(Id, causal_evidence),
    \+ has_feature(Id, chain_of_consequences). % avoid duplicate

% ============================================================
%  QUERY HELPERS
% ============================================================

fallacies_for_claim(Id, FallacyList) :-
    findall(F-E, fallacy(Id, F, E), FallacyList).

all_fallacious_claims(Pairs) :-
    findall(Id-FList, (
        claim(Id, _),
        fallacies_for_claim(Id, FList),
        FList \= []
    ), Pairs).
