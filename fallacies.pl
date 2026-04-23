:- discontiguous claim/1.
:- discontiguous text/2.
:- discontiguous type/2.
:- discontiguous target/2.
:- discontiguous supports/3.

% =========================
% Fallacy rules
% =========================

% Ad hominem: personal attack used to dismiss the argument or speaker.
fallacy(ad_hominem, C1, C2) :-
    type(C1, attack_target),
    type(C2, broad_rejection),
    target(C1, Person),
    target(C2, Person),
    Person \= unknown,
    supports(C1, C2, _).

% Guilt by bad-act expansion: a single bad act is stretched into total unreliability.
fallacy(hasty_generalization, C1, C2) :-
    type(C1, single_bad_act),
    type(C2, universal_claim),
    supports(C1, C2, _).

fallacy(hasty_generalization, C1, C2) :-
    type(C1, single_bad_act),
    type(C2, broad_rejection),
    supports(C1, C2, _).

% False dilemma: presents only two options.
fallacy(false_dilemma, C1) :-
    type(C1, either_or).

% Slippery slope: if X then catastrophic end-state.
fallacy(slippery_slope, C1) :-
    type(C1, conditional_catastrophe).

% Appeal to authority: authority reference used as stand-alone reason.
fallacy(appeal_to_authority, C1, C2) :-
    type(C1, authority_claim),
    supports(C1, C2, _),
    type(C2, claim).

% Bandwagon / appeal to popularity.
fallacy(appeal_to_popularity, C1, C2) :-
    type(C1, popularity_claim),
    supports(C1, C2, _),
    memberchk(C2Type, [claim, universal_claim, broad_rejection]),
    type(C2, C2Type).

% =========================
% Explanations
% =========================

explanation(ad_hominem, 'The argument attacks the person instead of addressing the substance of the argument.').
explanation(hasty_generalization, 'A broad conclusion is drawn from one bad act or too little evidence.').
explanation(false_dilemma, 'The statement presents only two options when other possibilities may exist.').
explanation(slippery_slope, 'The argument predicts catastrophic consequences without enough support for that chain.').
explanation(appeal_to_authority, 'The claim leans on authority alone rather than presenting supporting reasons or evidence.').
explanation(appeal_to_popularity, 'The claim treats popularity as proof that something is true or right.').
