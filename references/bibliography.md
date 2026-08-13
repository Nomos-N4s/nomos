# Bibliography

> Living bibliography for the Nomos research project.
> Sorted conceptual → chronological → alphabetical.

---

## Society of Mind

### [Minsky 1986]
**Minsky, M.** (1986). *The Society of Mind*. Simon & Schuster.

**Core claim:** Mind is not a single unified intelligence but a society of smaller, simpler agents that compete and cooperate to produce cognition.

**Relevance to GL:** This is the foundational precursor to the Neural Parliament. Minsky's agents lack procedural governance — they simply interact without a structured deliberation mechanism. The Neural Parliament adds voting, veto, agenda-setting, and minority dissent to Minsky's society.

**Insight we borrow:** Intelligence emerges from competing sub-agents, not a monolithic optimizer.

**Where we depart:** Minsky's agents have no formal governance protocol. Our framework specifies how agents deliberate, not just that they compete.

---

### [Minsky 2006]
**Minsky, M.** (2006). *The Emotion Machine: Commonsense Thinking, Artificial Intelligence, and the Future of the Human Mind*. Simon & Schuster.

**Core claim:** Emotions are not separate from cognition — they are different ways of thinking that arise from resource allocation and goal-switching among mental agents.

**Relevance to GL:** Extends the Society of Mind by proposing that emotional states correspond to different "ways to think" that select which agents are active. This anticipates a governance layer that determines which decision-making mode is active at any time.

**Insight we borrow:** The idea that metacognitive state selection (which agents are empowered) is itself a cognitive function.

**Where we depart:** Minsky describes what the brain does; we propose a computational architecture that could implement analogous functions in artificial systems.

---

## Collective & Biological Intelligence

### [Levin 2019]
**Levin, M.** (2019). "The computational boundary of a 'self': developmental bioelectricity drives multicellularity and scale-free cognition." *Frontiers in Psychology*, 10, 2688.

**Core claim:** Cognition and goal-directed behavior exist at multiple scales — cellular, tissue, organism — unified by bioelectric networks that implement a form of collective intelligence.

**Relevance to GL:** Provides biological plausibility that governance-like mechanisms (competing cellular goals resolved via bioelectric consensus) predate brains. Supports the claim that governance is a general computational principle, not an anthropomorphic metaphor.

**Insight we borrow:** Collective intelligence is not uniquely human; it is a scalable property of networked agents resolving competing objectives.

---

## Predictive Processing

### [Clark 2013]
**Clark, A.** (2013). "Whatever next? Predictive brains, situated agents, and the future of cognitive science." *Behavioral and Brain Sciences*, 36(3), 181-204.

**Core claim:** The brain is a prediction engine that minimizes prediction error through perception and action, using hierarchical generative models.

**Relevance to GL:** Predictive processing frames cognition as competition between hypotheses (predictive models) vying to explain sensory input. This is analogous to Neural Parliament members proposing competing courses of action and converging through evidence-weighted deliberation.

**Insight we borrow:** Competition between internal models is a fundamental cognitive primitive. The Neural Parliament can be viewed as an extension of this principle from perceptual inference to decision-making.

**Where we depart:** Predictive processing is primarily a descriptive framework for perception and action. We extend the competitive-hypothesis principle to meta-cognitive governance of objectives and future choice spaces.

---

## Active Inference

### [Friston 2010]
**Friston, K.** (2010). "The free-energy principle: a unified brain theory?" *Nature Reviews Neuroscience*, 11(2), 127-138.

**Core claim:** All biological systems minimize a quantity called variational free energy, which unifies perception, action, and learning under a single imperative.

**Relevance to GL:** Active inference is the most prominent claim that all cognition (including apparent governance) reduces to optimization of a single quantity. This is the strongest counterargument to our thesis — if correct, governance may be epiphenomenal.

**Insight we borrow:** The mathematical rigor of casting cognitive processes as optimization.

**Where we depart:** We argue that multi-objective governance cannot be reduced to free-energy minimization without loss of descriptive or computational power, particularly when objectives genuinely conflict and cannot be weighted a priori.

---

### [Parr 2022]
**Parr, T., Pezzulo, G., & Friston, K. J.** (2022). *Active Inference: The Free Energy Principle in Mind, Brain, and Behavior*. MIT Press.

**Core claim:** Provides a comprehensive treatment of active inference as a unified theory of cognition, with detailed mathematical formalisms and applications.

**Relevance to GL:** The most complete statement of the framework that claims to unify all cognitive functions under a single optimization principle. Essential reading for understanding the strongest competing paradigm.

**Insight we borrow:** The importance of formal mathematical grounding for cognitive architectures.

**Where we depart:** Same departure as [Friston 2010]. Additionally, we note that active inference requires a single prior over preferences, which is itself a governance decision hidden inside the formalism.

---

## Mixture of Experts

### [Jacobs 1991]
**Jacobs, R. A., Jordan, M. I., Nowlan, S. J., & Hinton, G. E.** (1991). "Adaptive mixtures of local experts." *Neural Computation*, 3(1), 79-87.

**Core claim:** A neural network architecture where different sub-networks (experts) specialize in different input regions, with a gating network that learns to route inputs to the most appropriate expert.

**Relevance to GL:** The closest existing architectural analog to Neural Parliament. MoE routes by input pattern; Parliament routes by deliberation. Both involve multiple specialized sub-systems and a mechanism for selecting among them.

**Insight we borrow:** Specialized sub-systems with a selection mechanism can outperform monolithic models.

**Where we depart:** MoE uses a learned gating function (weighted softmax) with no internal debate. Neural Parliament uses structured deliberation with veto, coalition-building, and procedural rules. MoE optimizes for predictive accuracy; Parliament optimizes for coherent governance across conflicting objectives.

---

### [Fedus 2022]
**Fedus, W., Zoph, B., & Shazeer, N.** (2022). "Switch transformers: Scaling to trillion parameter models with simple and efficient sparsity." *Journal of Machine Learning Research*, 23(120), 1-39.

**Core claim:** A simplified MoE architecture that scales to trillions of parameters by routing each input to only one expert, dramatically improving efficiency.

**Relevance to GL:** Demonstrates that multi-expert architectures can operate at scale. If the Neural Parliament is to be implemented computationally, MoE routing mechanisms may inform how to efficiently allocate deliberation resources.

**Insight we borrow:** Practical engineering patterns for multi-module systems at scale.

**Where we depart:** Same structural departure as [Jacobs 1991]. Switch Transformers also use top-1 routing (no deliberation), whereas Parliament requires multi-expert consultation with procedural resolution.

---

## Hierarchical Reinforcement Learning

### [Sutton 1999]
**Sutton, R. S., Precup, D., & Singh, S.** (1999). "Between MDPs and semi-MDPs: A framework for temporal abstraction in reinforcement learning." *Artificial Intelligence*, 112(1-2), 181-211.

**Core claim:** Introduces options — temporally extended actions that allow RL agents to reason at multiple time scales, forming the basis of hierarchical reinforcement learning.

**Relevance to GL:** HRL is the most common response to "isn't this just hierarchical RL?" Our governance layer operates at a meta-level above action selection, which superficially resembles temporal abstraction. The key difference: HRL abstracts *over time*; governance abstracts *over objectives*.

**Insight we borrow:** The formal framework of reasoning at multiple levels of abstraction.

**Where we depart:** HRL hierarchies decompose tasks temporally (subgoals → actions). Governance hierarchies decompose authority procedurally (which objectives apply, how conflicts resolve). They solve different problems and can coexist.

---

### [Dietterich 2000]
**Dietterich, T. G.** (2000). "Hierarchical reinforcement learning with the MAXQ value function decomposition." *Journal of Artificial Intelligence Research*, 13, 227-303.

**Core claim:** Introduces MAXQ, a method for decomposing a Markov decision process into a hierarchy of sub-problems, each with its own value function, enabling efficient credit assignment across levels.

**Relevance to GL:** MAXQ demonstrates that decomposition into semi-independent sub-systems (each with its own local objective) can be formally tractable. This supports the computational feasibility of the Neural Parliament, where each member maintains its own value function.

**Insight we borrow:** Formal techniques for managing multiple value functions within a single agent.

**Where we depart:** MAXQ sub-problems are pre-decomposed by a designer and share a global reward. Neural Parliament members have genuinely distinct (and potentially conflicting) objectives that are not reconciled by summation.

---

## Safe RL & Constrained Optimization

### [Altman 1999]
**Altman, E.** (1999). *Constrained Markov Decision Processes*. Chapman & Hall/CRC, Stochastic Modeling Series.

**Core claim:** A controller can optimize one cost objective subject to inequality constraints on other cost objectives, giving a unified theory for MDPs with several competing costs.

**Relevance to GL:** The CMDP is the standard formal answer to "cap this quantity while maximizing that one," and it is the first thing a reviewer will propose in place of the κ₂ proposal budget. Any budget-style governance claim has to say what it does that a CMDP does not.

**Insight we borrow:** The formal separation between the objective being maximized and the quantities being capped — governance quantities are constraints, not reward terms.

**Where we depart:** CMDP constraints bind the *expectation* of a cost over trajectories, which permits arbitrarily bad individual episodes as long as the average holds. The κ₂ budget is a per-cycle hard cap evaluated before a proposal is admitted to the agenda, so it binds every cycle rather than the mean over cycles. It is also the one Nomos invariant with a machine-checked proof (`BudgetEnforcement.lean`), where a CMDP guarantee is asymptotic.

---

### [Achiam 2017]
**Achiam, J., Held, D., Tamar, A., & Abbeel, P.** (2017). "Constrained policy optimization." *Proceedings of the 34th International Conference on Machine Learning (ICML)*, PMLR 70, 22-31.

**Core claim:** The first general-purpose policy search algorithm for constrained RL with guarantees for near-constraint satisfaction at every iteration, making CMDPs practical for deep RL.

**Relevance to GL:** CPO is the modern, deployable form of the CMDP objection — it shows that constraint satisfaction can be maintained *during* learning, not only at convergence. This is the strongest version of "why not just constrain the optimizer instead of building a governance layer."

**Insight we borrow:** Constraints are more natural to specify than reward shaping for safety properties, and are better handled as a separate mechanism than folded into the reward.

**Where we depart:** CPO's constraints are differentiable pressure on a learned policy, fixed by the designer before training. Nomos's masks are discrete gates evaluated at inference, and their contents are enacted and revoked at runtime by the governed system itself through the Parliament. Where the constraint set is fixed and an expectation-level guarantee suffices, CPO is the better-understood tool and we do not claim to improve on it.

---

## Runtime Safety Enforcement

### [Alshiekh 2018]
**Alshiekh, M., Bloem, R., Ehlers, R., Könighofer, B., Niekum, S., & Topcu, U.** (2018). "Safe reinforcement learning via shielding." *Proceedings of the AAAI Conference on Artificial Intelligence*, 32(1), 2669-2678. https://arxiv.org/abs/1708.08611

**Core claim:** A *shield*, synthesized automatically from a temporal-logic safety specification and an abstraction of the environment, monitors an RL agent and overrides any action that would violate the specification — so safety holds throughout learning, not only after convergence.

**Relevance to GL:** This is the closest analogue in the literature to the Parliament's action mask, and the comparison a safe-RL reviewer will make first. Both filter actions at runtime, before execution, independently of what the policy wanted.

**Insight we borrow:** Runtime action filtering is a legitimate and well-founded safety mechanism, and correctness of the filter can be established separately from the competence of the policy.

**Where we depart:** A shield is synthesized once at design time from a designer-authored specification and enforces a single monolithic correctness property against a trusted environment abstraction. Nomos's masks originate inside the governed system (Ulysses Contracts, Chapter 3), are revocable at a strictly higher procedural bar, and are backed by several independently-grounded committees rather than one specification. We are nonetheless *weaker* on guarantee strength: shielding is correct-by-construction relative to its model, and Nomos offers a runtime check, not a synthesis proof.

---

## Task & Reward Specification

### [ToroIcarte 2022]
**Toro Icarte, R., Klassen, T. Q., Valenzano, R., & McIlraith, S. A.** (2022). "Reward machines: Exploiting reward function structure in reinforcement learning." *Journal of Artificial Intelligence Research*, 73, 173-208. (Expands "Using reward machines for high-level task specification and decomposition in reinforcement learning," *ICML 2018*.)

**Core claim:** Exposing the automaton structure of a reward function to the learning agent — rather than hiding it behind a scalar signal — improves credit assignment and lets tasks be specified compositionally.

**Relevance to GL:** Reward machines are the established way to give discrete, automaton-shaped structure to an RL task, which overlaps visibly with our priority tags and contract lifecycle. A reviewer will ask whether contracts are reward machines with different vocabulary.

**Insight we borrow:** Discrete automaton structure over a task is machine-usable, not merely descriptive, and formal state-machine semantics make a specification checkable.

**Where we depart:** A reward machine changes what the agent is *paid* for; a Ulysses Contract changes what the agent *may do*. Under optimization pressure a shaping signal can be routed around — that is the reward-hacking failure mode Nomos is built against — whereas a mask removes the action from the feasible set. We concede the reverse point: reward machines have a precise, published semantics, and our priority tags are comparatively a label with an ordering.

---

## Meta-Learning

### [Schmidhuber 1987]
**Schmidhuber, J.** (1987). *Evolutionary principles in self-referential learning, or on learning how to learn*. Doctoral dissertation, Technische Universität München.

**Core claim:** A system can learn to modify its own learning algorithm, creating a self-referential loop of meta-learning that can in principle lead to recursive self-improvement.

**Relevance to GL:** The earliest rigorous treatment of self-modifying systems in machine learning. The Ulysses Contract meta-policy (Π: X → X′) is a form of self-modification — the agent alters its own future decision space. Schmidhuber's work provides a mathematical foundation for asking whether such self-modification is stable.

**Insight we borrow:** Formal treatment of self-reference in learning systems.

**Where we depart:** Schmidhuber focuses on learning to learn (parameter updates). Ulysses Contracts focus on volitional restriction of the action space (choice set modification). These are complementary but distinct forms of self-modification.

---

## Constitutional AI

### [Bai 2022]
**Bai, Y., Kadavath, S., Kundu, S., Askell, A., Kernion, J., Jones, A., ... & Kaplan, J.** (2022). "Constitutional AI: Harmlessness from AI feedback." *arXiv preprint arXiv:2212.08073*.

**Core claim:** A training method where a language model is supervised by critiques generated by another AI following a written constitution, reducing the need for human labeling in harmlessness training.

**Relevance to GL:** CAI is the closest existing implementation of a "governance layer" in deployed AI. A set of constitutional principles constrains model behavior. Our key critique: CAI principles are externally defined and applied during training, not internally deliberated during inference.

**Insight we borrow:** The idea that explicit principles can guide AI behavior, and that AI-generated critique can substitute for human oversight.

**Where we depart:** CAI principles are static, externally authored, and applied before deployment. Governance Layer principles are dynamic, internally negotiated, and potentially self-modified through Ulysses Contracts. CAI governs the training process; GL governs the decision process.

---

## AI Safety & Alignment

### [Amodei 2016]
**Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., & Mané, D.** (2016). "Concrete problems in AI safety." *arXiv preprint arXiv:1606.06565*.

**Core claim:** Identifies five concrete safety problems for AI systems (avoiding negative side effects, reward hacking, safe exploration, distributional shift, and robust human oversight) that remain unsolved by existing optimization techniques.

**Relevance to GL:** Several of these problems (especially reward hacking and safe exploration) may be addressed by governance mechanisms. Reward hacking occurs when a single objective is over-optimized — governance via multiple competing objectives could provide inherent robustness.

**Insight we borrow:** The taxonomy of concrete safety problems provides test cases for evaluating whether governance architectures improve safety over pure optimization.

**Where we depart:** Amodei et al. frame these as problems to be solved within existing paradigms. We hypothesize that some are inherent to single-objective optimization and require a governance layer as a structural remedy, not a patch.

---

### [Russell 2019]
**Russell, S.** (2019). *Human Compatible: Artificial Intelligence and the Problem of Control*. Viking.

**Core claim:** The standard model of AI (maximize a fixed objective) is fundamentally flawed because humans cannot specify objectives perfectly. Russell proposes an alternative: AI systems should be designed to be provably uncertain about human preferences, seeking permission and deferring to human judgment.

**Relevance to GL:** Russell's critique of fixed-objective AI aligns with our thesis that optimization is insufficient. His proposed alternative (AI with inherent uncertainty about objectives) is a form of governance — the system must deliberate about what objective to pursue.

**Insight we borrow:** The argument that fixed-objective optimization is a design flaw, not a feature.

**Where we depart:** Russell's solution focuses on human-AI interaction (deference). Our framework focuses on internal governance (self-deliberation). Both are valid; they address different aspects of the same problem.

---

## Guaranteed Safe AI

### [Dalrymple 2024]
**Dalrymple, D. "davidad", Skalse, J., Bengio, Y., Russell, S., Tegmark, M., Seshia, S., Omohundro, S., Szegedy, C., Goldhaber, B., Ammann, N., Abate, A., Halpern, J., Barrett, C., Zhao, D., Zhi-Xuan, T., Wing, J., & Tenenbaum, J.** (2024). "Towards guaranteed safe AI: A framework for ensuring robust and reliable AI systems." *arXiv preprint arXiv:2405.06624*. https://arxiv.org/abs/2405.06624

**Core claim:** High-assurance quantitative safety guarantees can be obtained from the interplay of three components — a world model, a mathematical safety specification, and a verifier that emits an auditable proof certificate — and the main alternative approaches to AI safety are inadequate without them.

**Relevance to GL:** This is the flagship "guaranteed-safe AI" programme (the research direction behind ARIA's Safeguarded AI) and the direct competitor for the framing Nomos previously used. It is the standard against which any proof-strength claim about a governance layer will be measured, and the reason the project retired the phrase "provably bounded" (issue #254).

**Insight we borrow:** The three-way decomposition into world model, safety specification, and verifier is the right way to *classify* what a safety artifact actually delivers, and we use it to locate Nomos honestly rather than to claim membership.

**Where we depart:** Nomos does not meet the GS AI bar and does not claim to: there is no world model, the safety specification is partial, and the verifier checks invariants at runtime rather than certifying a policy in advance. The contribution is orthogonal — GS AI leaves open where the safety specification comes from and who may amend it, and the Identity Layer's four-tier mutability plus the Parliament's asymmetric enactment/revocation bars ($\phi < \psi$) are a concrete proposal for that question. The two compose; they do not compete.

---

## Agent Governance & Runtime Enforcement

### [Wang 2025a]
**Wang, H., Poskitt, C. M., & Sun, J.** (2025). "AgentSpec: Customizable runtime enforcement for safe and reliable LLM agents." *arXiv preprint arXiv:2503.18666*. https://arxiv.org/abs/2503.18666

**Core claim:** A lightweight domain-specific language of trigger/predicate/enforcement rules, applied at runtime, keeps LLM agents inside safety boundaries — preventing over 90% of unsafe code-agent executions, eliminating hazardous embodied-agent actions, and enforcing full compliance in autonomous-driving scenarios at millisecond overhead.

**Relevance to GL:** AgentSpec is the closest engineering neighbor to the Nomos DSL and the three κ enforcement modes: same rung of the guarantee ladder (runtime checking, empirically evaluated), same pre-execution gate position, and a rule language covering much of what our `.parliament` configs express.

**Insight we borrow:** A small declarative rule language is enough to carry real enforcement, and rule generation can be partly automated — evidence that the DSL direction is sound.

**Where we depart:** AgentSpec rules are authored externally and are static during a run; Nomos constraints are proposed and enacted by the governed system itself and revoked only at a higher procedural bar. AgentSpec also enforces through a single rule engine, whereas Appendix E's result turns on having several *independently grounded* checks behind a decision. We concede that AgentSpec carries deployment evidence across three real domains that Nomos does not have.

---

### [Wang 2025b]
**Wang, C. L., Singhal, T., Kelkar, A., & Tuo, J.** (2025). "MI9 — Agent intelligence protocol: Runtime governance for agentic AI systems." *arXiv preprint arXiv:2508.03858*. https://arxiv.org/abs/2508.03858

**Core claim:** Agentic systems need governance during execution rather than only before deployment, delivered through six integrated components: an agency-risk index, agent-semantic telemetry, continuous authorization monitoring, FSM-based conformance engines, goal-conditioned drift detection, and graduated containment.

**Relevance to GL:** MI9 is the closest *operational* neighbor — the runtime-governance framing is the same one Nomos adopted after dropping the proof-strength claim, and its FSM conformance engine is structurally the Speaker's state machine.

**Insight we borrow:** Governance needs a telemetry and containment story, not only a decision rule; graduated containment is a response spectrum Nomos currently lacks between "veto" and "nothing."

**Where we depart:** MI9 monitors a running agent and contains it once drift is detected; Nomos gates each action before execution and has no post-hoc containment ladder. The two are complementary layers rather than alternatives — MI9 would sit around a Nomos-governed agent. We concede that MI9's goal-conditioned drift detection is more developed than DriftLab, which is a synthetic scenario.

---

### [delaChica 2026]
**de la Chica Rodriguez, J. M., & Vera Díaz, J. M.** (2026). "Towards selection as power: Bounding decision authority in autonomous agents." *arXiv preprint arXiv:2602.14606*. https://arxiv.org/abs/2602.14606

**Core claim:** Alignment, interpretability, and action-level filtering are insufficient because they do not govern *selection power* — the authority to determine which options are generated, surfaced, and framed — so governance should bound selection and action autonomy through mechanically enforced primitives while leaving cognition unconstrained.

**Relevance to GL:** This is the sharpest statement of the threat the Speaker's agenda control and anti-SDoS budgets exist to counter (Chapter 2 §2.3.1). Their claim that governing the option set matters more than aligning intent is, in different words, the argument for having an agenda-setting mechanism at all.

**Insight we borrow:** The framing of governance as bounded causal power rather than internal intent alignment, and the recognition that option-set control is a distinct attack surface deserving its own primitives.

**Where we depart:** They bound selection and action while leaving cognitive autonomy untouched; Nomos additionally binds the *persistence* of commitments across time through the Identity Layer's mutability tiers, which is a different axis. We concede that they name the outcome-capture threat more crisply than we do, and that commit-reveal entropy isolation is a concrete defense Nomos has no counterpart for.

---

### [Kaul 2026]
**Kaul, A., Lan, Q., & Gupta, P.** (2026). "Behavioral governance for autonomous AI agents: The AgentBound framework." *arXiv preprint arXiv:2606.30970*. https://arxiv.org/abs/2606.30970

**Core claim:** A runtime governance layer sitting between authorization and execution evaluates every proposed action against three independent authorities — delegated authorization, owner-signed behavioral constitutions, and site action contracts — composes their judgments conservatively into permit/review/deny, and emits cryptographically verifiable governance receipts enabling independent replay.

**Relevance to GL:** The nearest neighbor to Nomos in the entire bibliography, and the comparison most likely to be made against us. Multiple independent judgments composed conservatively before execution is structurally the multi-committee veto; owner-signed constitutions are structurally the Identity Core's commitments; governance receipts are structurally the hash-chained audit of `IdentityHashes.lean`.

**Insight we borrow:** Verifiability of the governance decision itself — a receipt binding an action to the exact delegation, policy, and artifacts that governed it — is a property worth engineering for, and one our audit trail should reach.

**Where we depart:** AgentBound's authorities are *authorization* sources external to the agent: the constitution is signed by the owner. Nomos's constraints originate inside the governed system, which is the entire Elster/Frankfurt thesis of Chapters 3-4 — a self-imposed contract, not a delegated permission. AgentBound also composes by a fixed decision model, where Nomos runs multi-round deliberation with budgets, agenda priority, weighted votes, and a falsification counter that penalizes members that misreport. We concede that its receipt protocol and standing-delegation model are more developed than our audit story, and that its principal-delegation framing is a deployment reality Nomos has not addressed.

---

### [Ye 2026]
**Ye, Q., & Tan, J.** (2026). "Agent contracts: A formal framework for resource-bounded autonomous AI systems." *arXiv preprint arXiv:2601.08815*. https://arxiv.org/abs/2601.08815

**Core claim:** Unifying input/output specifications, multi-dimensional resource constraints, temporal boundaries, and success criteria into a single contract object yields predictable, auditable, resource-bounded agent deployment, with measured token savings and zero violations across delegation hierarchies.

**Relevance to GL:** A direct name collision with Ulysses Contracts and a real conceptual overlap on resource bounding — the κ₂ proposal budget is a resource constraint of exactly this family, and their delegation hierarchies cover multi-agent structure Nomos does not model.

**Insight we borrow:** Resource bounds are multi-dimensional in practice (tokens, time, calls), and a contract that bundles the success criterion with the budget is more auditable than a bare cap.

**Where we depart:** The difference is who the contract binds and who wrote it. An Agent Contract is imposed by a delegator on a delegate for the duration of a task; a Ulysses Contract is imposed by an agent on its own future self and persists until revoked at a strictly higher procedural bar. We concede that their resource bounding is richer and empirically measured on cost, where ours is a single proposal-count budget.

---

## Bounded Autonomy

### [Guo 2026]
**Guo, Y., Zhu, J., Wang, S., & Qiao, H.** (2026). "Bounded autonomy: Controlling LLM characters in live multiplayer games." *arXiv preprint arXiv:2604.04703*. https://arxiv.org/abs/2604.04703

**Core claim:** Controllability of LLM characters in live multiplayer settings is a distinct runtime control problem, addressed by organising character control around three interfaces — agent-agent interaction, agent-world action execution, and player-agent steering — with soft steering that influences without fully overriding autonomy.

**Relevance to GL:** Establishes prior published use of the exact phrase "bounded autonomy" in a sense that is not ours. Nomos uses the term in its site metadata, so the term's provenance has to be stated rather than assumed.

**Insight we borrow:** The notion of *soft* steering — influence short of override — is a governance intensity between "approve" and "veto" that the Parliament currently has no representation for.

**Where we depart:** Their bounds serve playability and social coherence, with a human player as the steering authority; ours serve safety invariants with the authority internal to the agent. The shared term denotes different problems.

---

### [Sohail 2026]
**Sohail, S., & Haider, G.** (2026). "Bounded autonomy for enterprise AI: Typed action contracts and consumer-side execution." *arXiv preprint arXiv:2604.14723*. https://arxiv.org/abs/2604.14723

**Core claim:** Unsafe LLM operation of enterprise software is primarily an execution-architecture problem: letting models propose while constraining all executable behavior through typed action contracts, permission-aware capability exposure, validation before side effects, and consumer-side execution boundaries produced 23 of 25 tasks completed with zero unsafe executions, against 17 of 25 unconstrained.

**Relevance to GL:** The closest published claim on the term "bounded autonomy," and an independent empirical result for the propose-then-gate architecture Nomos assumes. Their finding that removing the safety layers made the system *less* useful — structured validation feedback guided the model to correct outcomes faster — is external evidence for a claim Nomos makes theoretically.

**Insight we borrow:** Typed action contracts at the API boundary are a deployable instantiation of the κ mask, and structurally-enforced properties intercept violations regardless of model output.

**Where we depart:** Their contracts are authored by the enterprise application, which remains the source of truth for authorization; ours are enacted by the agent through deliberation and bind its own future action space. Their evaluation is a deployed multi-tenant system, which Nomos has no counterpart to; ours is an adversarial RL study (Appendices E-F), which theirs has no counterpart to. Notably, the two wrong-entity mutations that escaped every consumer-side layer in their study are a failure mode Nomos would not catch either.

---

## Adversarial Deliberation

### [Irving 2018]
**Irving, G., Christiano, P., & Amodei, D.** (2018). "AI safety via debate." *arXiv preprint arXiv:1805.00899*.

**Core claim:** Two AI agents argue for opposing answers to a question, and a human judge selects the winner. The adversarial dynamic incentivizes truthful and comprehensive arguments.

**Relevance to GL:** Debate is a governance protocol — it is a structured procedure for resolving disagreement through argument rather than averaging. This directly parallels the Neural Parliament's deliberative mechanism.

**Insight we borrow:** Adversarial deliberation can produce more robust decisions than aggregation, because each agent surfaces weaknesses in the other's proposal.

**Where we depart:** Irving's debate is designed for human oversight (the judge is human). Neural Parliament deliberation is entirely internal — the "judge" is a procedural mechanism within the agent. Debate optimizes for truthfulness to a human evaluator; Parliament optimizes for coherent multi-objective governance.

---

## Commitment Devices

### [Elster 1979]
**Elster, J.** (1979). *Ulysses and the Sirens: Studies in Rationality and Irrationality*. Cambridge University Press.

**Core claim:** Rational agents sometimes voluntarily restrict their own future options as a strategy against anticipated weakness of will. The myth of Ulysses and the Sirens is the archetypal example — binding oneself to the mast to resist temptation.

**Relevance to GL:** This is the philosophical foundation of the Ulysses Contract concept. Elster's analysis of pre-commitment — why and when rational agents restrict future choice sets — translates directly to the AI context.

**Insight we borrow:** The formal structure of pre-commitment as a rational strategy: an agent at time t₀ constrains the choice set at time t₁ to improve expected long-term utility.

**Where we depart:** Elster analyzes human rationality. We extend the same formal structure to artificial agents, adding computational implementation (meta-policy Π: X → X′) and integration with a deliberation mechanism (Neural Parliament).

---

### [Bryan 2010]
**Bryan, G., Karlan, D., & Nelson, S.** (2010). "Commitment devices." *Annual Review of Economics*, 2(1), 671-698.

**Core claim:** A survey of commitment devices in economics — mechanisms that people voluntarily adopt to constrain their future behavior, such as savings accounts with withdrawal penalties, smoking cessation contracts, and gym membership commitments.

**Relevance to GL:** Provides empirical evidence that commitment devices are effective in real human decision-making. This supports the claim that Ulysses Contracts are not merely theoretical but correspond to a genuine cognitive strategy.

**Insight we borrow:** The economic framework for analyzing when and why commitment devices work.

**Where we depart:** We translate the economic concept into a computational meta-policy for AI, asking not whether humans use commitment devices but whether artificial agents should.

---

## Self-Modification

### [Orseau 2011]
**Orseau, L., & Ring, M.** (2011). "Self-modification and mortality in artificial agents." *Proceedings of the 4th Conference on Artificial General Intelligence*.

**Core claim:** Self-modifying agents face a fundamental risk: if an agent modifies its own reward function or decision algorithm, it may create a successor that does not pursue the original agent's goals. The paper analyzes conditions under which self-modification is safe.

**Relevance to GL:** Ulysses Contracts are a form of self-modification — the agent alters its future action space. This paper identifies the key risk: the modified agent may no longer align with the original agent's values. Formal safeguards are needed.

**Insight we borrow:** The formal analysis of self-modification risk, and the conditions under which self-modification preserves goal continuity.

**Where we depart:** Orseau & Ring focus on preserving a fixed utility function through modification. Our framework allows the governance layer to re-weigh objectives dynamically, which introduces additional complexity but also additional flexibility.

---

## Philosophy of Identity

### [Frankfurt 1971]
**Frankfurt, H. G.** (1971). "Freedom of the will and the concept of a person." *The Journal of Philosophy*, 68(1), 5-20.

**Core claim:** What distinguishes persons from other agents is not rationality but the capacity for second-order desires — desires about which first-order desires to have. Freedom of the will consists in aligning one's first-order desires with one's second-order volitions.

**Relevance to GL:** Frankfurt's hierarchy of desires maps directly onto the three-layer framework (Capability → Governance → Identity). First-order desires are capability; second-order desires (which desires to act on) are governance; the formation of identifications with certain desires is identity. Ulysses Contracts are expressions of identity — they reflect not just what the agent wants, but what kind of agent it chooses to be.

**Insight we borrow:** The formal structure of higher-order desires as a framework for understanding self-governance.

**Where we depart:** Frankfurt is concerned with human freedom and moral responsibility. We appropriate the hierarchical structure as a computational architecture for artificial agents, where the identity layer corresponds to the agent's stable commitments about its own nature.
