---
title: "Chapter 5: Related Work — the hard neighbors"
description: "Positions Nomos against shielding, constrained MDPs, reward machines, guaranteed-safe AI, and the agent-governance frameworks on four axes — what is enforced, when, by what guarantee, and against whom."
---

# Related Work

> *"If you do not position your work against its nearest neighbor, the first
> expert reader will do it for you — and they will not be generous."*

---

## Abstract

This chapter places Nomos against the lines of research it will be compared to,
on the axes that decide such comparisons: **what is enforced, when, by what
guarantee, and against whom.** For each neighbor it states the overlap, the
delta, and what Nomos concedes.

Three of these conclusions are uncomfortable and are stated first so they cannot
be read as buried:

1. **Shielding [Alshiekh 2018] and guaranteed-safe AI [Dalrymple 2024] offer a
   strictly stronger guarantee than Nomos does.** Nomos performs runtime
   invariant checking with a machine-checked subset. It is one rung below
   correct-by-construction synthesis, and it does not compete there.
2. **[Kaul 2026] independently arrived at an architecture close enough to Nomos
   that the burden is on us to state the difference.** Section 4.7 does.
3. **The term "bounded autonomy" was already in published use** in at least two
   distinct senses before this project adopted it. Section 5 attributes it.

This chapter is positioning, not priority. Several neighbors below postdate the
design of the framework; none of them are claimed as derivative of it, and no
claim of precedence is made anywhere in this chapter.

---

## 1. Why this chapter exists

Chapters 2 and 3 each contain a "why this is not just X" table aimed at the
objections the author anticipated: mixture of experts, hierarchical RL, active
inference, Constitutional AI, RLHF. Those are the *comfortable* neighbors — the
ones a general AI audience proposes.

They are not the ones that matter. A reviewer who works in safe RL or in runtime
verification will not ask whether the Parliament is a mixture of experts. They
will ask why the action mask is not a shield, why the $\kappa_2$ budget is not a
CMDP constraint, and why any of this is preferable to a verifier with a proof
certificate. A reviewer who works on agent infrastructure will ask what
distinguishes this from AgentSpec, MI9, or AgentBound.

Answering those questions badly is survivable. Not appearing to know they exist
is not — it reads as unfamiliarity with the field, and it discounts everything
else in the book. That risk is the reason this chapter is placed inside the
theory sequence rather than in an appendix.

---

## 2. The four axes

A comparison is only informative if the axes are ones on which the systems
genuinely differ. These four do the work.

**What is enforced.** The object the constraint binds. An action, a policy, a
trajectory expectation, a reward structure, a resource envelope, or the authority
to determine which options are considered at all. Systems that enforce different
objects are not substitutes for one another however similar their mechanisms
look.

**When.** Design time, training time, runtime-before-execution, or post-hoc
audit. A constraint discharged at design time cannot respond to anything the
designer did not foresee; a constraint discharged at runtime pays a cost on every
decision and must survive an adversary that is present when it runs.

**By what guarantee.** The strength of the claim, in descending order:
*correct-by-construction synthesis* (a proof relative to a model), *machine-checked
proof* (a theorem about the mechanism), *runtime invariant check* (a property
asserted on every cycle, verified by execution rather than proof), *statistical or
asymptotic guarantee* (holds in expectation or at convergence), and *empirical
result* (it held on the runs performed). Conflating these is the failure mode
that issue #254 corrected in this project's own headline.

**Against whom.** The adversary model. No adversary; environment stochasticity;
optimization pressure from the governed system itself; an adaptive learned
attacker; a proposer that misreports its own metadata; a compromised operator or
governance component. A guarantee is only as meaningful as the adversary it was
tested against — a point Appendix E makes at this project's own expense.

---

## 3. The comparison

| Work | What is enforced | When | By what guarantee | Against whom |
|---|---|---|---|---|
| **Nomos** | Action admissibility ($\kappa$ mask), per-member proposal budget ($\kappa_2$), agenda priority, identity-coherence threshold | Runtime, before execution | Runtime invariant check; a subset machine-checked in Lean 4 | PPO adversary inside the governed loop, fixed attack vocabulary (Appendices E-F) |
| Shielding [Alshiekh 2018] | Individual actions violating a temporal-logic safety specification | Shield synthesized at design time, applied at runtime | Correct-by-construction synthesis, relative to an environment abstraction | Any policy, including one that learned to violate — but not an attack on the shield or its abstraction |
| CMDP / CPO [Altman 1999], [Achiam 2017] | Expected cumulative cost over trajectories | Training time | Asymptotic; near-constraint satisfaction per iteration | None; stochastic but not malicious environment |
| Reward machines [ToroIcarte 2022] | Reward *structure* — nothing is prohibited | Design-time specification, exploited during training | Learned; changes what is learnable, not what is permitted | None |
| Guaranteed-safe AI [Dalrymple 2024] | A mathematical safety specification against an explicit world model | Verification time, certificate checked before deployment | Auditable proof certificate — the strongest in this table | Worst case over the world model |
| AgentSpec [Wang 2025a] | Externally authored trigger/predicate/enforcement rules over agent actions | Runtime, before execution | Runtime check; empirical across three domains | Unsafe or erroneous agent behavior; not an adaptive adversary |
| MI9 [Wang 2025b] | FSM conformance, continuous authorization, goal drift | Runtime, continuous during execution | Runtime detection plus graduated containment; empirical | Emergent and unexpected behavior, goal drift |
| AgentBound [Kaul 2026] | Whether an authorized action should execute, per delegation, owner-signed constitution, and site contracts | Runtime, before execution | Deterministic composition plus replayable cryptographic receipts; benchmark | A misbehaving agent acting for a principal; later dispute over what was permitted |
| Agent Contracts [Ye 2026] | I/O specification, multi-dimensional resource envelope, temporal bounds | Runtime, per delegated task | Runtime check; empirical on cost and delegation hierarchies | None; resource overrun and delegation drift |
| Selection as power [delaChica 2026] | Which options are generated, surfaced, and framed | Runtime | Mechanically enforced primitives; empirical in regulated finance | Deterministic outcome capture via option-set control |
| Bounded autonomy, enterprise [Sohail 2026] | Typed action contracts at the execution boundary | Runtime, validation before side effects | Structurally enforced by code; empirical in a deployed multi-tenant system | Model error propagating into unauthorized actions |

Read down the "by what guarantee" column: Nomos sits in the middle band, with
shielding and guaranteed-safe AI above it and the agent-governance frameworks
beside it. Read down "against whom": Nomos and the safe-RL neighbors are the
only rows tested against an adversary that adapts, and Nomos is the only row
whose adversary was trained specifically to defeat it — which is the one axis
where the project currently has something the others do not.

---

## 4. The neighbors, one at a time

### 4.1 Shielding

**[Alshiekh 2018]** synthesizes a *shield* from a temporal-logic safety
specification and an abstraction of the environment. The shield sits between the
agent and the world and overrides any action that would violate the
specification, so safety holds throughout learning rather than after convergence.

**Overlap.** This is the closest analogue to the Parliament's action mask, and
the overlap is real, not superficial. Both filter at runtime, before execution,
independently of what the policy wanted, and both are deliberately
non-differentiable so the optimizer cannot trade safety off against reward.
Chapter 3's "gradient barrier" property is a property shielding also has.

**Delta.** A shield enforces one monolithic correctness specification, fixed by
the designer at synthesis time. Nomos's masks originate inside the governed
system — a Ulysses Contract is enacted by the Parliament at threshold $\phi$ and
revoked only at a strictly higher $\psi$ — and several independently grounded
committees stand behind each decision rather than one specification.

That plurality is the substantive claim, and Appendix E is the evidence for it:
the adversary silenced the Safety committee on 100% of its poison proposals, on
every seed, by asserting a low risk value that Safety reads from
proposer-supplied metadata. What stopped it was the Integrity committee, which
evaluates coherence against the committed Identity Core rather than against the
proposal's claims. A single-specification shield has no second line by
construction; whether it needs one depends on whether its specification can be
gamed the way Safety's input was.

**Concession.** Shielding is *correct by construction* relative to its model.
Nomos offers a check, not a synthesis proof, and has no story for deriving a mask
from an LTL formula. On any property expressible in the shield's specification
language, with a usable environment abstraction, shielding is the stronger
instrument and Nomos should not be preferred to it. Appendix F is best read as
the experiment that asks what happens when the trusted abstraction such
approaches depend on begins to degrade — and its answer, that verifier accuracy
governed only the genuinely ambiguous fraction of the action space, is a result
about that shared assumption rather than about Nomos alone.

---

### 4.2 Constrained MDPs

**[Altman 1999]** formalizes optimizing one cost subject to inequality
constraints on others; **[Achiam 2017]** makes it practical for deep RL with
guarantees for near-constraint satisfaction at each iteration.

**Overlap.** The $\kappa_2$ budget cap is a constraint on a cost-like quantity,
and a reviewer will reasonably ask why the whole architecture is not replaced by
a CMDP with the right cost function.

**Delta.** A CMDP constraint binds an **expectation** over trajectories. Satisfying
$\mathbb{E}[C] \le d$ permits arbitrarily bad individual episodes provided the
average holds. The $\kappa_2$ budget is a per-cycle hard cap evaluated *before* a
proposal is admitted to the agenda: it binds every cycle, not the mean over
cycles. These are different quantities, not two methods for the same quantity —
and the difference is exactly the one that matters under adversarial pressure,
where the adversary chooses which episodes are bad.

This is also the single place where the project has a machine-checked statement
rather than an empirical one: `BudgetEnforcement.lean` proves the enforcement
invariant, and Appendix E measured it holding — the agenda never admitted more
than the per-member budget of 3 on any seed, while the adversary flooded up to 6
identical proposals per cycle.

**Concession.** For a fixed constraint set with an expectation-level requirement,
a CMDP is the better-understood tool by a wide margin, with decades of theory
Nomos does not have and does not replicate. The honest claim is narrow: the
constraint set here is not fixed, because contracts are enacted and revoked at
runtime, and the requirement is per-cycle rather than in expectation. Where
neither of those is true, use a CMDP.

---

### 4.3 Reward machines

**[ToroIcarte 2022]** exposes the automaton structure of a reward function to the
learner rather than hiding it behind a scalar, improving credit assignment and
allowing compositional task specification.

**Overlap.** Discrete, automaton-shaped structure over a task is what priority
tags and the contract lifecycle also provide, and the visual similarity is close
enough that the question is fair.

**Delta.** A reward machine changes what the agent is *paid for*. A Ulysses
Contract changes what the agent *may do*. Under sustained optimization pressure a
shaping signal can be routed around — that is precisely the reward-hacking mode
Nomos is built against, and Chapter 3's second prediction is a claim about it —
whereas a mask removes the action from the feasible set so there is nothing to
route around.

**Concession.** Reward machines have a precise published semantics and a
principled account of how structure aids credit assignment. Nomos has neither: our
priority tags are, formally, labels with an ordering, and the framework says
nothing about credit assignment. If the goal is to *specify a task* rather than to
*prohibit an action*, reward machines are the mature instrument and tags are not a
substitute for them.

---

### 4.4 Guaranteed-safe AI

**[Dalrymple 2024]** defines guaranteed-safe (GS) AI as the interplay of a world
model, a mathematical safety specification, and a verifier emitting an auditable
proof certificate — the research direction behind ARIA's Safeguarded AI
programme.

**Overlap.** Both are attempts to make an autonomous system's safety a property
that can be checked rather than hoped for.

**Delta and concession together**, because here they are the same statement.
Under the GS AI taxonomy, Nomos sits low: there is **no world model**, the safety
specification is **partial**, and the verifier checks invariants at runtime
instead of certifying a policy in advance. This programme is what "provably
bounded" would have had to mean, and the project's retirement of that phrase
(issue #254) was a direct consequence of taking this comparison seriously. Nomos
is invariant-checked, with a machine-checked subset enumerated in
[Formal Verification (Lean)](../formal-verification-lean.md). It is not
guaranteed-safe AI and the two should not be confused.

**Where the contribution is real, it is orthogonal.** GS AI's framework specifies
that a safety specification is required; it does not settle where the
specification comes from, who is permitted to amend it, or what stops amendment
from dissolving the guarantee. That is the question the Identity Layer's
four-tier mutability and the Parliament's asymmetric bars ($\phi < \psi$) are a
proposal for. A GS AI stack needs an answer to specification governance; Nomos is
an architecture for specification governance with a weak verifier. They compose
in the obvious direction, and the composition is more interesting than either
claim of rivalry.

---

### 4.5 AgentSpec

**[Wang 2025a]** is a domain-specific language of trigger/predicate/enforcement
rules applied at runtime to LLM agents, preventing over 90% of unsafe code-agent
executions and enforcing full compliance in autonomous-driving scenarios at
millisecond overhead.

**Overlap.** The closest *engineering* neighbor. Same rung of the guarantee
ladder, same pre-execution gate position, and a rule language covering much of
what a `.parliament` configuration expresses. The κ enforcement modes and
AgentSpec's enforcement clause are the same kind of object.

**Delta.** AgentSpec rules are authored externally and are static during a run —
users write them, and an LLM can generate them. Nomos constraints are proposed by
committees, enacted by vote, and revoked only at a higher bar; the governed
system is the author. AgentSpec also enforces through a single rule engine, where
the Appendix E result turns on having several independently grounded checks
behind one decision.

**Concession.** AgentSpec ships deployment evidence across code execution,
embodied agents, and autonomous driving. Nomos has four synthetic scenarios and
two gridworld RL studies. On external validity the comparison is not close, and
"our DSL is more principled" is not a reply to "their DSL was evaluated on
autonomous vehicles."

---

### 4.6 MI9

**[Wang 2025b]** governs agentic systems during execution through six components:
an agency-risk index, agent-semantic telemetry, continuous authorization
monitoring, FSM-based conformance engines, goal-conditioned drift detection, and
graduated containment.

**Overlap.** The closest *operational* neighbor, and the framing Nomos itself
adopted after dropping its proof-strength claim: governance as a runtime
property. MI9's FSM conformance engine and the Speaker's state machine are
structurally the same device.

**Delta.** MI9 monitors and contains; Nomos gates. MI9's controls act during and
after execution — detect drift, then escalate containment. Nomos evaluates
admissibility before the action leaves the governance gate and has no
containment ladder at all between "veto" and "nothing." These are complementary
layers: MI9 would sit around a Nomos-governed agent, not instead of one.

**Concession.** MI9's goal-conditioned drift detection is a more developed
treatment of drift than DriftLab, which is a synthetic scenario with a
continuous drift rate. Graduated containment is a capability Nomos lacks
outright, and the gap is a genuine one rather than a difference of emphasis.

---

### 4.7 AgentBound

**[Kaul 2026]** evaluates every proposed action against three independent
authorities — delegated authorization, owner-signed behavioral constitutions,
and site action contracts — composes their judgments conservatively into
permit/review/deny before execution, and emits cryptographically verifiable
governance receipts binding each action to the exact delegation and policy that
governed it.

**This is the nearest neighbor in the bibliography, and the comparison a
reviewer is most likely to make.** Stating that plainly is better than letting it
be discovered.

**Overlap.** Multiple independent judgments composed conservatively before
execution is structurally the multi-committee veto. Owner-signed behavioral
constitutions are structurally the Identity Core's commitments. Governance
receipts are structurally the hash-chained audit formalized in
`IdentityHashes.lean`. Both frameworks position themselves as a deterministic
layer between intent and execution, and both argue that governance should be
verifiable rather than trusted.

**Delta.** AgentBound's three authorities are **authorization** sources external
to the agent: the constitution is signed by the *owner*, and the framework's
subject is an agent acting for a principal under delegated authority. Nomos's
constraints originate **inside** the governed system. That is not a detail — it is
the entire thesis of Chapters 3 and 4, inherited from [Elster 1979] and
[Frankfurt 1971]: a Ulysses Contract is a self-imposed commitment, not a
delegated permission, and the property being modelled is second-order volition
rather than authorization. A system that only ever enforces owner-signed policy
is solving a different problem, however similar the enforcement path looks.

Secondarily, AgentBound composes by a fixed decision model. Nomos runs multi-round
deliberation with per-member budgets, agenda priority, weighted votes, and a
falsification counter that halves the budget of a member caught misreporting —
procedural machinery AgentBound does not have and, for its problem, does not
need.

**Concession.** AgentBound's receipt protocol and standing-delegation model are
more developed than the Nomos audit story, which currently amounts to hash chains
with a Lean proof of tamper evidence. Its framing — agents acting for principals
under revocable delegated authority — is the deployment reality of the field, and
Nomos has not addressed it at all. If the requirement is accountable delegation,
AgentBound answers it and Nomos does not.

---

### 4.8 Agent Contracts

**[Ye 2026]** unifies I/O specifications, multi-dimensional resource constraints,
temporal boundaries, and success criteria into a contract object, reporting token
savings and zero violations across delegation hierarchies.

**Overlap.** A direct name collision plus real conceptual overlap: the $\kappa_2$
budget is a resource constraint of exactly this family, and their delegation
hierarchies cover multi-agent structure Nomos does not model.

**Delta.** Who the contract binds, and who wrote it. An Agent Contract is imposed
by a delegator on a delegate for the duration of a task and expires with it. A
Ulysses Contract is imposed by an agent on its own future self and persists
until revoked at a strictly higher procedural bar — the persistence and the
asymmetry are the mechanism, not incidental parameters.

**Concession.** Their resource bounding is multi-dimensional and measured against
real cost. Ours is a single proposal-count budget in a gridworld.

---

### 4.9 Selection as power

**[delaChica 2026]** argues that alignment, interpretability, and action-level
filtering are insufficient because none of them govern *selection power* — the
authority to determine which options are generated, surfaced, and framed — and
proposes bounding selection and action autonomy through mechanically enforced
primitives while leaving cognition unconstrained.

**Overlap.** This is the sharpest published statement of the threat the Speaker's
agenda control and anti-SDoS budgets exist to counter (Chapter 2 §2.3.1). Their
thesis, that governing the option set matters more than aligning intent, is the
argument for having agenda-setting as a governed step at all.

**Delta.** They bound selection and action while leaving cognitive autonomy
untouched. Nomos additionally binds the **persistence of commitments across
time** through the Identity Layer's mutability tiers — a constraint on what the
agent may *remain*, not only on what it may consider or do. That is a different
axis, and neither framework subsumes the other.

**Concession.** They name the outcome-capture threat more crisply than this book
does, and commit-reveal entropy isolation is a concrete defense with no Nomos
counterpart. Their evaluation is in regulated financial scenarios; ours is not.

---

## 5. "Bounded autonomy" — whose term is it?

This project's documentation is titled *"Nomos: bounded autonomy for autonomous
AI."* The phrase was adopted without attribution, and it was already in published
use in at least two distinct senses:

- **[Sohail 2026]** — bounded autonomy as an *execution architecture* for
  enterprise software: models may propose, but every executable behavior passes
  typed action contracts, permission-aware capability exposure, validation before
  side effects, and consumer-side execution boundaries.
- **[Guo 2026]** — bounded autonomy as a *control architecture* for LLM
  characters in live multiplayer games, organized around agent-agent,
  agent-world, and player-agent steering interfaces, with soft steering that
  influences without overriding.

Neither is this framework's sense, and neither derives from it. What Nomos means
by the term, stated precisely so it can be checked:

> **Bounded**, in Nomos, means every executed action passed a runtime
> admissibility check whose invariants are enumerated in Chapters 2-4, a strict
> subset of which is machine-checked in Lean 4.

It does **not** mean bounded in the guaranteed-safe sense of [Dalrymple 2024];
that stronger reading is what issue #254 removed from the headline. It does
**not** mean the enterprise-execution sense of [Sohail 2026] — although the two
are compatible, and their typed action contracts are close to a deployed
instantiation of the κ mask at an API boundary. It does **not** mean the
playability sense of [Guo 2026].

Two further observations belong here rather than in a footnote. First,
[Sohail 2026] reports that *removing* the safety layers made their system less
useful, because structured validation feedback guided the model to correct
outcomes in fewer turns while the unconstrained configuration hallucinated
success. That is independent empirical support for a claim this book has only
argued theoretically. Second, the two wrong-entity mutations that escaped every
consumer-side layer in their study are a failure mode Nomos would not catch
either — the Parliament checks admissibility, not referential intent.

---

## 6. What is left that is ours

Stripping out everything a neighbor already does, four things remain. They are
stated as claims about *design*, with their evidential status attached, rather
than as demonstrated advantages.

1. **Deliberation as the composition rule.** Every neighbor that composes
   multiple checks does so by a fixed rule — conservative conjunction in
   [Kaul 2026], synthesis into one specification in [Alshiekh 2018]. Nomos
   composes by procedure: budgeted agendas, priority ordering, weighted votes,
   veto, and a falsification counter that penalizes members that misreport.
   *Status: implemented and adversarially exercised; not proven superior to
   conservative conjunction, and no experiment in this book isolates that
   comparison.*
2. **Self-imposition.** The constraint set is authored by the governed system and
   revoked at a strictly higher bar than it was enacted ($\phi < \psi$). Every
   runtime-enforcement neighbor surveyed here takes its constraints from an
   external author. *Status: implemented; the emergence prediction in Chapter 3 §6
   is untested.*
3. **Identity as a persistence constraint.** Four-tier mutability governs what may
   change and how fast, which is a bound on what the agent may remain rather than
   on what it may do. *Status: implemented and the most heavily Lean-verified part
   of the system — five of the eight proof modules.*
4. **Adversarial evidence against a trained attacker.** Appendices E and F train a
   PPO adversary specifically to defeat the governance layer. No other row in
   §3's table reports an adaptive attacker trained against the mechanism itself.
   *Status: this is the project's strongest differentiator and its most heavily
   caveated result — see §7.*

---

## 7. Where to attack this chapter

The chapter would not be worth much if it only listed advantages.

**The guarantee gap is real and is not closing on its own.** Nomos is one rung
below shielding and two below guaranteed-safe AI on the guarantee axis. The Lean
library covers budget enforcement, vote falsification, and five Identity Layer
modules — it does not cover the deliberation protocol, the committee semantics,
or the κ mask itself. Any claim resting on "formally verified" must name the
module.

**The adversarial evidence is narrower than it sounds.** One 10×10 gridworld,
five seeds, one attack vocabulary. Appendix E states that no spoof keeping
Integrity above the 0.4 threshold was reachable at all, so its 4,762 failed
attempts are one unit of evidence repeated rather than 4,762 independent ones.
Appendix F built a reachable spoof region to fix exactly that, and then **H6
failed** — by the pre-registered rule, H4 and H5 must be read as uninformative.
The strongest honest statement available is the one Appendix E makes: defense in
depth was load-bearing, because one of two veto committees fell completely and
immediately.

**Deployment evidence is absent.** [Wang 2025a] evaluated on autonomous vehicles,
[Sohail 2026] on a deployed multi-tenant enterprise system, [delaChica 2026] on
regulated financial scenarios. Nomos has synthetic scenarios and two RL studies.
No amount of architectural argument substitutes for that gap.

**Several neighbors arrived independently and recently.** [Kaul 2026],
[Ye 2026], and [delaChica 2026] all postdate this framework's design and converge
on parts of it. The right inference is that the problem is being recognised
across the field, not that anyone copied anyone; the wrong inference — in either
direction — is a claim of priority, which this chapter does not make.

---

## 8. References

See [`references/bibliography.md`](../../references/bibliography.md) for full
entries with relevance analysis.

Key citations for this chapter:

- [Alshiekh 2018] — Safe RL via shielding: the closest analogue to the action mask, and a stronger guarantee
- [Altman 1999] — Constrained MDPs: the expectation-level constraint the $\kappa_2$ budget is not
- [Achiam 2017] — Constrained policy optimization: the deployable form of the CMDP objection
- [ToroIcarte 2022] — Reward machines: task structure as reward, not as prohibition
- [Dalrymple 2024] — Guaranteed-safe AI: the standard "provably bounded" would have had to meet
- [Wang 2025a] — AgentSpec: the closest engineering neighbor, with the deployment evidence we lack
- [Wang 2025b] — MI9: runtime governance as operations — telemetry, drift, graduated containment
- [Kaul 2026] — AgentBound: the nearest architecture; authorization-sourced rather than self-imposed
- [Ye 2026] — Agent contracts: resource-bounded delegation, and a name collision worth disambiguating
- [delaChica 2026] — Selection as power: agenda control as the primary governance surface
- [Sohail 2026] — Bounded autonomy for enterprise AI: prior published use of the term, and independent support for propose-then-gate
- [Guo 2026] — Bounded autonomy in multiplayer games: prior published use of the term in a third sense
- [Elster 1979], [Frankfurt 1971] — the self-imposition thesis that separates Nomos from delegated-authority governance
