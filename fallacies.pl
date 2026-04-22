% ============================================================
%  FALLACY DETECTION KNOWLEDGE BASE
%  Logic Checker for Political Speeches
%  Uses SWI-Prolog with dynamic facts asserted per analysis run
% ============================================================

:- discontiguous fallacy/3.
:- discontiguous claim/2.
:- discontiguous has_feature/2.
:- dynamic claim/2.
:- dynamic has_feature/2.

% ============================================================
%  FEATURE PREDICATES
%  Features are asserted dynamically by Python based on
%  Claude's NLP analysis of each atomic sentence.
%  has_feature(ClaimId, Feature)
% ============================================================

% ============================================================
%  FALLACY RULES
%  fallacy(ClaimId, FallacyType, Explanation)
% ============================================================

% --- AD HOMINEM ---
% Attacking the person rather than their argument
fallacy(Id, ad_hominem, 'Attacks the character or personal traits of an opponent rather than addressing their actual argument.') :-
    claim(Id, _),
    has_feature(Id, attacks_person),
    has_feature(Id, ignores_argument).

% --- FALSE DILEMMA ---
% Presenting only two options when more exist
fallacy(Id, false_dilemma, 'Presents only two possible options, ignoring other valid alternatives.') :-
    claim(Id, _),
    has_feature(Id, binary_choice),
    \+ has_feature(Id, acknowledges_alternatives).

% --- SLIPPERY SLOPE ---
% Assuming one event will lead to extreme consequences without justification
fallacy(Id, slippery_slope, 'Assumes that one event will inevitably lead to extreme negative consequences without sufficient justification.') :-
    claim(Id, _),
    has_feature(Id, chain_of_consequences),
    has_feature(Id, extreme_endpoint),
    \+ has_feature(Id, causal_evidence).

% --- HASTY GENERALIZATION ---
% Drawing broad conclusions from limited examples
fallacy(Id, hasty_generalization, 'Draws a broad general conclusion from a limited or unrepresentative sample of evidence.') :-
    claim(Id, _),
    has_feature(Id, broad_generalization),
    has_feature(Id, limited_sample).

% --- STRAW MAN ---
% Misrepresenting an opponent's position to make it easier to attack
fallacy(Id, straw_man, 'Misrepresents or exaggerates an opponent\'s position, then attacks that distorted version.') :-
    claim(Id, _),
    has_feature(Id, misrepresents_opponent),
    has_feature(Id, attacks_misrepresentation).

% --- APPEAL TO AUTHORITY ---
% Using an authority figure as evidence without proper justification
fallacy(Id, appeal_to_authority, 'Cites an authority figure as definitive proof without sufficient supporting evidence or relevant expertise.') :-
    claim(Id, _),
    has_feature(Id, cites_authority),
    ( has_feature(Id, irrelevant_authority)
    ; has_feature(Id, no_supporting_evidence)
    ).

% --- RED HERRING ---
% Introducing irrelevant information to distract from the main issue
fallacy(Id, red_herring, 'Introduces irrelevant information or arguments to distract from the actual issue being discussed.') :-
    claim(Id, _),
    has_feature(Id, topic_diversion),
    has_feature(Id, ignores_main_issue).

% ============================================================
%  QUERY HELPERS
% ============================================================

% Find all fallacies for a given claim
fallacies_for_claim(Id, FallacyList) :-
    findall(F-E, fallacy(Id, F, E), FallacyList).

% Find all claims that have at least one fallacy
all_fallacious_claims(Pairs) :-
    findall(Id-FList, (
        claim(Id, _),
        fallacies_for_claim(Id, FList),
        FList \= []
    ), Pairs).

% Count total fallacies detected
total_fallacies(Count) :-
    findall(_, fallacy(_, _, _), L),
    length(L, Count).
