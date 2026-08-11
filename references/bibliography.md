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
