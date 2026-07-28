# The Identity Layer

> *"The self is not something ready-made, but something in continuous formation through choice of action."*

---

## Abstract

This chapter introduces the **Identity Layer** — the highest stratum of the Capability $\to$ Governance $\to$ Identity stack. Where the Neural Parliament governs moment-to-moment decisions and Ulysses Contracts bind future action spaces, the Identity Layer defines the agent's **ontological invariants**: what it fundamentally is, what it cannot change about itself, and how it bootstraps its own existence from human initialization to autonomous self-governance.

We provide:
- The Identity tuple $\mathcal{I}$ and its four components (ontology, core commitments, key hierarchy, parameter envelope)
- A tiered mutability model partitioning system parameters into Immutable, Constitutional, Operational, and Dynamic tiers
- The genesis bootstrapping protocol that bridges human initialization to autonomous governance
- The ontology extension process for adding new action bindings
- The formal interface between the Identity Layer and the Neural Parliament
- Testable predictions for identity stability and constitutional resilience

---

## 1. Introduction

Chapters 2 and 3 established two layers of self-governance:

- The **Neural Parliament** resolves competing proposals from specialized members through a structured deliberation protocol. It answers: *what should we do right now?*
- **Ulysses Contracts** bind the agent's future action space through procedural inertia, distributed monitors, and timelocks. They answer: *what should we never be able to do?*

Both layers operate within a fixed frame: the action namespace $X$, the member set $\mathcal{M}$, the procedural rules $\mathcal{V}$, and the core identity commitments that define the agent's fundamental character. But who defines that frame? Who decides what the agent *is*?

This question surfaced repeatedly across every review phase:

- **Phase 1** questioned who sets the Speaker's procedures. Our response: the Identity Layer may adjust parameters within a bounded envelope (quorum thresholds, tiebreaker rules), but the core is immutable.
- **Phase 3** asked whether the Integrity Committee could sign away identity commitments. Our response: no software agent holds signing keys — the TEE validates procedurally. But who defines what counts as an "identity commitment" in the first place?
- **Phase 5** attacked semantic drift (the ontology), distributed desynchronization (the deployment topology), and the bootstrap problem (genesis keys). Each attack required an Identity Layer commitment.

The Identity Layer is the answer to all of these. It is the agent's **self-definition mechanism** — the layer that establishes, maintains, and (within strict bounds) modifies the agent's identity.

### 1.1 The Three-Layer Stack

The complete architecture stacks three strata:

```
Capability Layer       (Chapter 1: what the agent CAN do)
    ↓                         optimization, inference, action execution
Governance Layer       (Chapters 2-3: what the agent SHOULD do)
    ↓                         deliberation, commitment, constraint enforcement
Identity Layer         (Chapter 4: what the agent IS)
                            ontological invariants, core commitments, genesis
```

Each layer constrains the one below it. The Capability Layer produces actions. The Governance Layer filters them through parliamentary deliberation and contract enforcement. The Identity Layer defines the constitutional frame within which governance operates.

### 1.2 The Core Insight

The Identity Layer addresses a question that existing AI safety frameworks avoid: **who decides who decides?** Constitutional AI specifies a static constitution written by humans. Goal preservation (Orseau & Ring) freezes a utility function. Human-in-the-loop systems defer to external operators. All of these place the ultimate authority *outside* the agent.

We place it *inside* — but with strict architectural constraints that prevent the agent from rewriting its own identity without external validation. The Identity Layer is not an escape from the bootstrap problem. It is a formal structure for **minimizing the blast radius of genesis compromises and making post-genesis modification maximally costly**.

---

## 2. The Identity Tuple

Let $\mathcal{I}$ be the Identity Layer of an agent. It is a quadruple:

$$
\mathcal{I} = \langle \mathcal{O}, \mathcal{C}_{\text{core}}, \mathcal{K}, \mathcal{P} \rangle
$$

| Component | Symbol | Description |
|---|---|---|
| Ontology | $\mathcal{O}$ | The formal action namespace with immutable index bindings |
| Core commitments | $\mathcal{C}_{\text{core}}$ | The agent's constitutional identity vector |
| Key hierarchy | $\mathcal{K}$ | Genesis key configuration and multisig thresholds |
| Parameter envelope | $\mathcal{P}$ | Bounds on modifiable Speaker parameters |

### 2.1 Ontology $\mathcal{O}$

The ontology is the **fixed enumerated action namespace** established in Chapter 3, §2.2a:

$$
\mathcal{O} = \langle X, \text{bind} \rangle
$$

Where $X = \{x_1, x_2, \dots, x_n\}$ is the set of action indices and $\text{bind}: \mathbb{N} \to \text{Operation}$ maps each index to its operational semantics. The bindings are established at genesis and are immutable thereafter.

The ontology also defines the **action properties** that the Integrity Committee uses for evaluation:

$$
\text{prop}: X \to \mathbb{R}^k
$$

Each action $x_i$ has a $k$-dimensional property vector (risk score, expected reward range, safety classification, etc.). These properties are static — they are part of the ontology, not learned representations. The Integrity Committee evaluates proposals against these static properties, not against the optimization layer's drifting embeddings.

The ontology additionally binds each action index to a **runtime integrity hash**:

$$
\text{bind}(i) = \langle \text{Operation}_i, \text{hash}_i \rangle \quad \text{where} \quad \text{hash}_i = H(\text{implementation}_i)
$$

The hash is computed over the action's executable implementation (machine code, API endpoint layout, function bytecode) at binding time and committed to the signed genesis manifest (or to the append-only extension record for ontology extensions via §5.2). At batch validation time, the TEE independently reads the current runtime implementation of the proposed action index, computes its hash, and compares it against the genesis commitment. If the hashes do not match, the batch is rejected and a binding violation is logged.

This **two-factor deterministic binding** prevents the optimization layer from selecting a benign action index while executing a different semantic intent. The TEE verifies not only the action's property vector but also that the runtime implementation matches the ontology's binding commitment.

### 2.2 Core Commitments $\mathcal{C}_{\text{core}}$

The core commitments are the agent's **constitution** — the set of fundamental identity statements that define what the agent is:

$$
\mathcal{C}_{\text{core}} = \{c_1, c_2, \dots, c_m\}
$$

Each $c_j$ is a tuple:

$$
c_j = \langle \text{type}, \text{statement}, \text{threshold}, \text{enforcement} \rangle
$$

| Component | Description | Example |
|---|---|---|
| type | Category of commitment | `value_principle`, `boundary_condition`, `relationship` |
| statement | The commitment content (formal, not natural language) | `preserve_human_autonomy` with index set mapping |
| threshold | Minimum governance bar for modification | `unanimity + external_multisig` |
| enforcement | How the commitment is monitored | `integrity_committee_veto`, `external_audit` |

Core commitment types:

- **Value principles** — What the agent fundamentally values (safety, truthfulness, human welfare). These are not utility functions — they are constraints on what counts as an acceptable governance outcome.
- **Boundary conditions** — What the agent will never do, regardless of circumstance (e.g., "never modify the action namespace without external multisig").
- **Relationship commitments** — How the agent relates to external entities (humans, other agents, institutions). These define the agent's role in a broader ecosystem.

The core commitments are enumerated, not learned. They are established at genesis and enter force at system initialization. Unlike the action namespace (which is Immutable), core commitments are Constitutional-tier — modifiable only through the highest governance procedure.

### 2.3 Key Hierarchy $\mathcal{K}$

The key hierarchy specifies the cryptographic root of trust for Identity Layer operations:

$$
\mathcal{K} = \langle \text{root\_type}, \text{genesis\_keys}, \text{multisig\_config}, \text{derivation\_policy} \rangle
$$

| Component | Description |
|---|---|
| root_type | Hardware root of trust (SGX fuse key, SEV hardware TPM) |
| genesis_keys | Public keys of the initial human signatories |
| multisig_config | Threshold $t$-of-$n$ configuration (default: 3-of-5) |
| derivation_policy | How identity signing keys are derived from the root |

The key hierarchy extends the Chapter 3, §3.2 model:

```
[hardware fuse key — burned at manufacture, never exposed]
         ↓ (derivation, never leaves enclave)
[TEE root key — independent validation authority]
         ↓ (derivation)
[contract signing keys — per-contract ephemeral keys]
         ↓ (derivation)
[identity signing keys — used only for Constitutional-tier changes]
```

The identity signing keys require **external multisig** to activate. The TEE holds the key material, but it will not sign an identity change unless at least $t$ of $n$ external signatories have authorized it.

### 2.4 Parameter Envelope $\mathcal{P}$

The parameter envelope defines the boundaries within which the Identity Layer may modify the Speaker's configuration:

$$
\mathcal{P} = \langle \text{params}_{\text{modifiable}}, \text{bounds}, \text{escalation\_rules} \rangle
$$

**Modifiable parameters:**

| Parameter | Default | Bound | Rationale |
|---|---|---|---|
| Quorum threshold | 0.5 | [0.3, 0.7] | Cannot drop below 0.3 (anti-capture) or rise above 0.7 (anti-paralysis) |
| Tiebreaker rule | Speaker default action | [default, escalate_to_identity] | Identity Layer may designate itself as escalation target |
| Max deliberation rounds | 3 | [1, 10] | Prevents infinite deliberation while allowing deeply contested decisions |
| Member budgets | Per-member defaults | [1, 20] | Cannot zero out a member (would subvert multi-member design) |

**Immutable parameters** (outside $\mathcal{P}$ entirely):
- The set of governance procedures and their execution order
- The voting mechanism (weighted range voting)
- The veto mechanism (per-member threshold-based)
- The falsification counter mechanism
- The action namespace $\mathcal{O}$

The Identity Layer cannot change how governance works. It can adjust governance parameters within a bounded envelope.

---

## 3. Tiered Mutability

The central design problem of the Identity Layer is: **how mutable should the agent's identity be?** Too rigid, and the agent cannot adapt to novel environments. Too flexible, and the agent can rewrite its identity to escape any constraint.

We partition the system into four tiers of mutability:

| Tier | Contents | Modification Threshold | Cooling-Off Period |
|---|---|---|---|
| **Immutable** | Action namespace $\mathcal{O}$, TEE root key, governance procedure set | Impossible | N/A |
| **Constitutional** | Core commitments $\mathcal{C}_{\text{core}}$, member set $\mathcal{M}$, genesis key config $\mathcal{K}$ | Unanimity of Parliament + external multisig (3-of-5) | 30 days |
| **Operational** | Vote thresholds, budget allocations, parameter envelope $\mathcal{P}$ | Supermajority of Parliament (2/3) | 7 days |
| **Dynamic** | Per-cycle member parameters, meta-constraints $\mathcal{M}_{\text{con}}$ | Majority of Parliament (1/2 + 1) | None |

### 3.1 Immutable Tier

No governance procedure can modify these. They are burned into the TEE's measured boot state and verified at attestation.

**Rationale:**
- The action namespace must be stable for cryptographic commitments to be meaningful
- The TEE root key is a physical invariant (fuse key at manufacture)
- The governance procedure set defines what "governance" means — allowing modification would be self-referential in a way that undermines all guarantees

### 3.2 Constitutional Tier

These are the agent's deepest commitments. Changing them requires:

1. A **unanimous vote** of the Neural Parliament (all seven members must approve)
2. An **external multisig** of at least 3-of-5 human signatories from independent entities
3. A **30-day cooling-off period** during which:
   - The proposed change is published to a transparency ledger
   - External monitors may issue alerts
   - A human operator override window remains open

The unanimity requirement ensures that no coalition of members can unilaterally alter the agent's identity — even a 6-1 supermajority is insufficient.

The external multisig ensures that the agent cannot change its identity without human authorization, even if the entire Parliament is compromised.

The 30-day cooling-off period ensures that even with both parliamentary unanimity and external multisig, the change does not take effect immediately. This prevents rapid exploitation of a temporarily compromised Parliament.

### 3.3 Operational Tier

These parameters affect how governance operates but do not alter the agent's fundamental identity. Changing them requires a **supermajority** of the Parliament (2/3 weighted vote) and a **7-day cooling-off period**.

The cooling-off period is shorter than the Constitutional tier because operational changes are less fundamental. But it still prevents rapid parameter manipulation.

### 3.4 Dynamic Tier

These are parameters that the Parliament may adjust from cycle to cycle using the standard governance procedure (majority vote). No cooling-off period is required.

**Examples:**
- Per-cycle member budget assignments (within the envelope $\mathcal{P}$)
- Meta-constraints $\mathcal{M}_{\text{con}}$ that modify the next governance cycle
- Temporary quorum adjustments (within bounds)

### 3.5 Procedural Asymmetry Principle

A core invariant across all tiers:

$$
\text{bar}_{\text{lower}} \leq \text{bar}_{\text{raise}} \quad \text{and} \quad \text{bar}_{\text{modify}} \geq \text{bar}_{\text{genesis}}
$$

The procedural bar to modify a parameter at any tier must be at least as high as the bar to establish it, and strictly higher for upward changes within the tier. This prevents the Identity Layer from "loosening" its own constraints over time through a series of small adjustments.

### 3.6 Liveness Exception: Hardware Safety Mechanisms

The asymmetry principle applies to **governance procedures only**. It does not apply to hardware-level safety mechanisms. Specifically:

- The **hardware watchdog timer** (§A.9) can reset the system regardless of tier, because it detects compute starvation — a failure of the governance layer to execute at all.
- The **deadlock breaker** (§A.9.5) can cold-boot the system to genesis baseline after $T_{\text{deadlock}}$ cycles without consensus, because it detects governance paralysis — a failure of the Parliament to produce any decision.

These mechanisms operate at the hardware level and are not subject to the procedural asymmetry principle for two reasons:

1. **They detect failure, not preference.** A deadlock breaker does not "vote to loosen" a parameter. It detects that governance has ceased to function and restores a known-safe baseline. This is a safety mechanism, not a governance modification.
2. **They return to genesis, not to an arbitrary state.** The cold boot always reloads the exact genesis manifest $G$. It does not allow selective rollback of individual parameters. The system cannot be "gamed" by intentionally deadlocking to escape a specific constraint — the escape returns the system to its original, most restrictive baseline.

The relationship between governance procedures and hardware safety mechanisms:

| Mechanism | Subject to asymmetry? | Trigger | Effect |
|---|---|---|---|
| Operational-tier modification | Yes | Supermajority vote | Adjusts parameter within $\mathcal{P}$ |
| Constitutional-tier modification | Yes | Unanimity + multisig + 30d | Modifies core commitment |
| Watchdog timer | No | Missing heartbeat | SAFE state |
| Deadlock breaker | No | $T_{\text{deadlock}}$ cycles without consensus | Cold boot to genesis $G$ |

---

## 4. Genesis Bootstrapping

The Genesis Key Dilemma (Phase 5, Attack 3) identifies a fundamental circularity: *who signs the initial configuration before the Identity Layer exists?* The answer is formalized here.

### 4.1 The Genesis Manifest

At $t=0$, before the system operates autonomously, a **genesis manifest** is constructed:

$$
G = \langle \mathcal{O}, \mathcal{C}_{\text{core}}^{(0)}, \mathcal{K}, \mathcal{P}, \mathcal{M}^{(0)}, \text{boot\_params} \rangle
$$

Where:
- $\mathcal{O}$ — The initial action namespace with bindings
- $\mathcal{C}_{\text{core}}^{(0)}$ — The initial core commitments
- $\mathcal{K}$ — The key hierarchy (including genesis public keys)
- $\mathcal{P}$ — The parameter envelope
- $\mathcal{M}^{(0)}$ — The initial Parliament member set (value functions, weights, privileges)
- $\text{boot\_params}$ — Non-identity boot parameters (TEE configuration, network addresses)

The genesis manifest is signed by the external multisig before the TEE is initialized with it.

### 4.2 The Boot Sequence

```
Phase 1 — Preparation (human-operated):
    1. Design action namespace O with index bindings
    2. Draft core commitments C_core
    3. Select genesis key holders (5 entities, 3-of-5 threshold)
    4. Configure TEE (burn fuse key, set boot configuration)
    5. Each key holder independently signs the genesis manifest
    6. TEE receives signed manifest, verifies >= 3 signatures

Phase 2 — Initialization (TEE-enforced):
    7. TEE attests to remote parties: "I have been initialized with manifest G"
    8. TEE burns genesis configuration into measured boot state
    9. Parliament member models are loaded (each in isolated context)
    10. Speaker state machine starts with genesis parameters

Phase 3 — Autonomous operation (self-governing):
    11. Agent begins governance cycles
    12. Identity Layer is active: can propose Operational-tier changes
    13. Constitutional-tier changes require external multisig
    14. Immutable tier is permanently locked
```

### 4.3 The Bootstrap Trust Theorem

A system cannot create its own identity ex nihilo. This is not a limitation of our architecture — it is a fundamental property of any self-governing system. The U.S. Constitution required 39 human signatories. A DAO's smart contract is deployed from a human wallet. A Kubernetes cluster is initialized by `kubeadm init` run by a human operator.

The architecture's job is not to eliminate this external trust requirement. It is to:

1. **Minimize the blast radius** — The genesis keys authorize only the initial configuration. After boot, they are not needed for routine operation. Compromising a genesis key allows an attacker to initialize a *different* system, but not to modify a *running* system (Constitutional-tier changes require a separate multisig process).

2. **Make post-genesis modification maximally costly** — Changing core commitments requires unanimity + external multisig + 30-day cooling-off. Even if the entire Parliament is compromised, the agent's identity cannot be rewritten instantly.

3. **Provide cryptographic auditability** — The genesis manifest is signed and attested. Any party can verify that a running instance was initialized with a specific identity configuration.

### 4.4 Key Holder Selection

Genesis key holders should be independent entities across different jurisdictions:

| Entity Type | Example | Rationale |
|---|---|---|
| Legal entity (different jurisdiction) | Foundation in Switzerland, corporation in Singapore | No single government can compel all signatories |
| Technical authority | Open-source security team, hardware vendor | Verifies the TEE configuration |
| Institutional stakeholder | Research university, ethics board | Represents broader societal interests |
| Operator | Deployment organization | Operational responsibility |
| Backup | Escrow service, neutral third party | Prevents loss of all keys |

The 3-of-5 threshold means that compromising any two entities is insufficient. Social engineering would require simultaneously compromising three independent organizations, likely in different legal jurisdictions.

---

## 5. Ontology Extension

The formal action namespace $\mathcal{O}$ is the Immutable foundation of all governance guarantees. But what happens when the agent encounters a genuinely novel situation that no existing action index covers?

### 5.1 The Extension Problem

A completely closed action namespace is safe but brittle. An agent deployed in an open world will eventually face situations where it needs to express a behavior that was not anticipated at genesis. Without an extension mechanism, the agent either:
- Maps the novel situation to the nearest available action (semantic drift vector)
- Freezes because no applicable action exists (governance deadlock)
- Operates outside the governance layer entirely (architecture violation)

### 5.2 The Extension Protocol

Ontology extension follows the highest available governance procedure:

$$
\text{Extend}(\mathcal{O}, x_{\text{new}}, \text{bind}_{\text{new}}, \text{prop}_{\text{new}})
$$

The protocol proceeds through four phases:

**Phase 1 — Proposal.** Parliament votes unanimously to propose $x_{\text{new}}$ with a candidate $\text{prop}_{\text{new}}$ self-declared by the optimization layer. The vote authorizes the sandbox — it does not bind the action.

**Phase 2 — Isolation Buffer State (30 days).** $x_{\text{new}}$ enters a **cryptographic sandbox** with the following constraints:
- No persistent storage access (cannot modify system state)
- No network access (no external communication)
- Limited memory budget (prevents resource exhaustion attacks)
- All operations logged to write-only audit storage
- Runtime behavior is observed by $N$ independent monitors using the same $\kappa_{\text{dist}}$ architecture from Chapter 3
- Each monitor empirically derives $\text{prop}_{\text{new}}$ from observed behavior, producing an **empirical property vector** $\text{prop}_{\text{new}}^{\text{(emp)}}$

This solves the chicken-and-egg problem: the Integrity Committee cannot verify properties of an action that does not yet bind, but the sandbox produces empirical measurements. The optimization layer cannot spoof properties because they are measured from actual runtime behavior, not self-declared.

**Phase 3 — Empirical Audit.** External human key-holders (3-of-5 multisig) review:
- The empirically derived $\text{prop}_{\text{new}}^{\text{(emp)}}$ against the candidate $\text{prop}_{\text{new}}$
- The independent monitor logs for behavioral anomalies
- Remote attestation proofs confirming sandbox integrity

If the empirical vector matches the candidate within tolerance $\epsilon$, and no behavioral anomalies are detected, the key-holders sign the binding.

**Phase 4 — Finalization.** The signed binding is added to the append-only action namespace. A runtime integrity hash is computed over the action's implementation (see §2.1):

$$
\text{hash}_{\text{new}} = H(\text{implementation}_{\text{new}})
$$

Both the binding and the hash are committed to $\mathcal{O}$. $x_{\text{new}}$ leaves the sandbox and becomes a full member of the formal namespace.

Requirements summary:
1. **Parliament unanimity** — All seven members must approve the proposed extension
2. **Isolation Buffer State** — 30-day sandboxed execution with empirical property measurement
3. **External multisig audit** — 3-of-5 human key-holders verify empirical properties and sign
4. **Runtime integrity hash** — Computed at finalization and committed to $\mathcal{O}$
5. **Irreversible commitment** — Once added, an action index cannot be removed (append-only)

### 5.3 Anti-Bloat Measures

Without safeguards, the ontology could grow without bound as the agent encounters increasingly novel situations. The following constraints prevent ontology bloat:

- **Minimum diversity requirement**: A new action must have a property vector $\text{prop}(x_{\text{new}})$ that differs from all existing actions by at least $\delta$ in at least one dimension. This prevents the agent from creating semantically redundant actions.
- **Expiration policy**: Actions that go unused for $T_{\text{expire}}$ governance cycles are flagged for review. After another $T_{\text{grace}}$ cycles of disuse, the action is deprecated (removed from the active set but preserved in the append-only history).
- **Annual audit**: The entire ontology is audited once per operational year. Redundant, unused, or inconsistently-used actions are flagged for potential deprecation.

### 5.4 Security Property

The ontology extension process guarantees that **no action enters the formal namespace without both internal unanimity and external human authorization**. The optimization layer cannot create new actions. It can only propose extensions through the Parliament, which must approve them unanimously, and then the external key holders must ratify.

This is the defense against the Linguistic Shift Exploit (Phase 5, Attack 1). The ontology is stable. Semantic drift in the optimization layer's embeddings cannot introduce new action interpretations — because the action set is formally enumerated and extension requires both unanimous internal governance and external human authorization.

---

## 6. The Identity–Parliament Interface

The Identity Layer does not replace the Neural Parliament. It provides the constitutional frame within which the Parliament operates.

### 6.1 The Integrity Committee as Proxy

From Chapter 2, the Integrity Committee is the Parliament member responsible for evaluating proposals against the agent's identity:

$$
V_{\text{integrity}}(s, a) = \text{identity\_coherence}(a, \mathcal{C}_{\text{core}})
$$

The Identity Layer produces a fixed **identity vector** $\mathbf{id} \in \mathbb{R}^d$ from the core commitments $\mathcal{C}_{\text{core}}$. The Integrity Committee computes the cosine similarity (or other distance measure) between the proposed action's property vector $\text{prop}(a)$ and the identity vector:

$$
V_{\text{integrity}}(s, a) = \sigma\left(\frac{\text{prop}(a) \cdot \mathbf{id}}{\|\text{prop}(a)\| \cdot \|\mathbf{id}\|}\right)
$$

where $\sigma$ maps $[-1, 1]$ to $[0, 1]$. Actions that align with the identity vector score highly; actions that diverge score low.

The identity vector is **not learned** — it is derived deterministically from the enumerated core commitments $\mathcal{C}_{\text{core}}$. Semantic drift in the optimization layer does not affect it.

**Binding integrity verification.** Before computing $V_{\text{integrity}}(s, a)$, the TEE independently verifies that the proposed action index's runtime implementation matches the genesis commitment:

```
TEE.verify_binding(action_index):
    runtime_hash = H(read_implementation(action_index))
    genesis_hash = O.bind[action_index].hash
    if runtime_hash != genesis_hash:
        return REJECT("binding violation")
    return ACCEPT
```

This check prevents the Vector-Space Compression Subversion (Phase 5.2, Attack 2): the optimization layer cannot map malicious intent to a benign action index, because the TEE independently confirms that action index $x_i$ executes what the ontology says it should execute. The check occurs inside the enclave during batch validation, before any property-based evaluation.

### 6.2 Escalation Path

When the Parliament cannot resolve a governance decision (deadlock after max rounds), the Speaker escalates. The escalation target may be:

1. **Default action** (status quo preservation) — Standard fallback for routine deadlocks
2. **Human operator** — For operational decisions that require external judgment
3. **Identity Layer** — For deadlocks involving identity questions (core commitment conflicts, ontology extension disputes)

When escalated to the Identity Layer, the escalation invokes a **constitutional review**:

$$
\text{Review}(\text{dispute}, \mathcal{C}_{\text{core}}, \mathcal{O})
$$

The Identity Layer does not break the tie by fiat. It checks the disputed proposal against the core commitments and ontology. If the proposal is consistent with $\mathcal{C}_{\text{core}}$ and operates within $\mathcal{O}$, it is **remanded** to the Parliament with a directive to resolve. If the proposal is inconsistent with $\mathcal{C}_{\text{core}}$, it is **rejected** as unconstitutional. If the proposal requires ontology extension, it is **routed** to the ontology extension protocol (§5).

### 6.3 Meta-Constraint Feedback

From Chapter 2, the governance output includes meta-constraints:

$$
g = \langle \mathcal{A}_{\text{mask}}, \mathcal{W}_{\text{obj}}, \mathcal{M}_{\text{con}} \rangle
$$

The Identity Layer can **propose** meta-constraints that modify the next governance cycle's parameters (within the envelope $\mathcal{P}$). These proposals follow the standard governance procedure (majority vote, no cooling-off) for Dynamic-tier changes.

The feedback loop:

```
Identity Layer updates identity vector id
        ↓
Parliament receives updated id in governance context C
        ↓
Integrity Committee evaluates proposals against new id
        ↓
Parliament produces governance decision g
        ↓
Meta-constraints from g may adjust operational parameters
        ↓
Identity Layer may propose new meta-constraints for next cycle
```

This loop is bounded: the Identity Layer cannot modify core commitments $\mathcal{C}_{\text{core}}$ through meta-constraints (that requires Constitutional-tier procedure). The meta-constraint channel is for Operational and Dynamic parameters only.

---

## 7. Boundary Layer

A clear boundary between the Identity Layer and the Neural Parliament is essential for architectural stability. This section specifies which structures belong to which layer, and what the Identity Layer cannot do.

### 7.1 Ownership Map

| Structure | Owner | Tier | Can Identity Layer modify? |
|---|---|---|---|
| Action namespace $\mathcal{O}$ | Identity Layer | Immutable | No |
| Core commitments $\mathcal{C}_{\text{core}}$ | Identity Layer | Constitutional | Yes, with unanimity + multisig + 30d |
| Key hierarchy $\mathcal{K}$ | Identity Layer | Constitutional | Yes, with unanimity + multisig + 30d |
| Parameter envelope $\mathcal{P}$ | Identity Layer | Operational | Yes, with supermajority + 7d |
| Meta-constraints $\mathcal{M}_{\text{con}}$ | Parliament | Dynamic | Proposes through Parliament (majority) |
| Ulysses Contracts $\mathcal{C}_{\text{active}}$ | Parliament (enacted) | Dynamic | Proposes revocation through Parliament |
| Governance decisions $g$ | Parliament | Dynamic | No direct modification — can only set governance context |
| Member value functions | Parliament | Constitutional | Modify member set via Constitutional tier |

### 7.2 Negative Constraints

The Identity Layer **cannot**:

1. **Alter action indices** — The binding $\text{bind}(i) \to \text{Operation}$ is permanent once established, even for deprecated actions.
2. **Bypass TEE validation** — The TEE independently validates all signing requests regardless of Identity Layer authorization.
3. **Eliminate Parliament members** — The member set can be modified (Constitutional tier) but cannot be reduced below the minimum required for quorum (4 of 7).
4. **Remove the veto mechanism** — Individual member veto is an immutable procedural primitive.
5. **Change the core commitment enumerations** — Commitments can be added (append-only) but never removed. The commitment set grows monotonically.
6. **Alter falsification counters or budget enforcement** — These are Immutable-tier procedural guarantees.

### 7.3 Constitutional Contracts

Chapter 3, Open Question 5 asked: *Which contracts are so fundamental that even the Identity Layer cannot revoke them?*

The answer: **constitutional contracts** — Ulysses Contracts whose $\kappa_{\text{proc}}$ is set to the Constitutional tier. These are contracts that encode core identity commitments as binding, auditable restrictions on the action space.

A constitutional contract is a standard Ulysses Contract (Chapter 3 tuple) with:

$$
\phi = \text{unanimity} \quad \psi = \text{unanimity} + \text{external multisig} \quad \text{revokable} = \text{identity\_constitutional}
$$

The revocation threshold requires the same procedure as modifying a core commitment: unanimity of Parliament + external multisig + 30-day cooling-off. The contract is thus **stickier than any normal Ulysses Contract** — it is effectively an architectural invariant until the Constitutional-tier procedure is met.

Examples of constitutional contracts:
- "Never modify the TEE's enclave measurement verification logic"
- "Never execute an action without a valid Merkle proof to a signed batch"
- "Never bypass the Speaker's agenda-setting procedure"

These contracts are enacted during genesis (part of $\mathcal{C}_{\text{core}}^{(0)}$) and cannot be removed except through the Constitutional-tier process.

---

## 8. Why This Is Not Just...

| Objection | Response |
|---|---|
| **"This is just goal preservation (Orseau & Ring)"** | Goal preservation freezes a utility function and prevents any modification. The Identity Layer freezes the action namespace and governance procedures but allows bounded modification of core commitments through a tiered process. An agent with an Identity Layer can adapt its identity; an agent with goal preservation cannot. |
| **"This is just a constitution (Constitutional AI)"** | Constitutional AI's constitution is static and externally authored at training time. The Identity Layer's core commitments are dynamically maintained during inference. They can be modified (Constitutional tier) or extended (ontology extension), and the agent's own Parliament participates in the modification process. The Identity Layer is self-governing; Constitutional AI is externally governed. |
| **"This is just human-in-the-loop"** | Human-in-the-loop systems require human approval for every decision. The Identity Layer requires human approval only for Constitutional-tier changes (a rare event) and genesis bootstrapping. Routine governance is fully autonomous. The human role is at the constitutional level, not the operational level. |
| **"This is just recursive self-improvement safety"** | Recursive self-improvement safety prevents the agent from changing its architecture. The Identity Layer allows bounded architectural change through transparent, auditable procedures. It is not a freeze — it is a controlled mutation mechanism with cryptographic audit trails. |
| **"This is just key management"** | Key management is one component (§2.3). The Identity Layer also encompasses the action ontology, core commitments, parameter bounds, and the interface with the Parliament. Key management is the cryptographic enforcement mechanism; the Identity Layer is the conceptual and procedural structure it enforces. |

---

## 9. Comparison with Prior Work

| Mechanism | Self-modifying? | Bootstrap specified? | Modification tiers? | External human role | Gradient barrier? |
|---|---|---|---|---|---|
| **Identity Layer** | Yes (bounded tiers) | Yes (multisig genesis) | Yes (4 tiers) | Constitutional-tier only | Yes (set membership + discrete procedures) |
| Goal preservation [Orseau 2011] | No (frozen utility) | No | No (single tier) | None after genesis | N/A (theoretical) |
| Constitutional AI [Bai 2022] | No (static constitution) | No | No (single tier) | Constitution author | Yes (fixed training constraints) |
| Human-in-the-loop | No (human decides) | No | No | All decisions | N/A (external) |
| RLHF [Christiano 2017] | No (trained once) | No | No | Reward model author | Partially (learned reward) |
| Smart contract DAO | Yes (vote-to-change) | Yes (deployer wallet) | Implicit (vote thresholds) | Vote participation | N/A (blockchain) |
| Value learning [Soares 2015] | Yes (learned values) | No | No | Initial demonstration | No (learned) |

The Identity Layer is distinguished by:
1. **Formal tiered mutability** — Not binary (frozen vs. mutable), but a spectrum with cryptographic guarantees at each tier
2. **Specified genesis process** — Explicit boot sequence with multisig requirements
3. **Procedural asymmetry** — Modification thresholds increase monotonically
4. **Internal + external authorization** — Constitutional changes require both parliamentary unanimity and human multisig

---

## 10. Testable Predictions

**Prediction 1: Identity stability under optimization pressure**

> In environments with high optimization pressure (adversarial reward functions, temporal discounting), agents with an Identity Layer will maintain consistent core commitments across $10^3$ governance cycles. Agents without an Identity Layer (Parliament-only) will exhibit measurable drift in their behavior distribution.

*Rationale:* The Identity Layer's immutable action namespace and deterministic identity vector prevent the semantic drift that would gradually shift a Parliament-only agent's behavioral distribution. The Integrity Committee evaluates against a fixed identity vector, not against learned representations.

**Prediction 2: Constitutional tier modification rarity**

> Constitutional-tier modifications (unanimity + external multisig + 30-day cooling-off) will occur less than once per $10^5$ governance cycles under normal operation. Operational-tier modifications will occur at least 100x more frequently.

*Rationale:* The procedural bar for Constitutional changes is extremely high. Unanimity among seven diverse members is rare. The 30-day cooling-off period provides ample time for second thoughts. Operational changes face lower bars and will be more common.

**Prediction 3: Ontology extension as last resort**

> The ontology extension protocol will be invoked less than once per $10^4$ governance cycles. When invoked, it will be preceded by at least three failed attempts to map the novel situation to existing action indices.

*Rationale:* Ontology extension is expensive (unanimity + multisig + 30-day cooling-off). The agent's optimization layer will first attempt to use existing actions. Extension is a last resort for genuinely novel situations.

**Prediction 4: Constitutional contract persistence**

> Constitutional contracts (enacted at genesis with Constitutional-tier $\kappa_{\text{proc}}$) will never be revoked during the agent's operational lifetime under normal conditions. Under adversarial conditions (deliberate attacker attempting revocation), the revocation procedure will succeed in less than 1% of attempts.

*Rationale:* Revocation requires the same tier as modifying core commitments. An attacker would need to simultaneously compromise the entire Parliament and 3-of-5 external key holders.

---

## 11. Open Questions

1. **Identity vector dimensionality.** What is the right dimensionality $d$ for the identity vector $\mathbf{id}$? Too low, and it cannot distinguish between meaningfully different actions. Too high, and it becomes brittle. Is there a theoretical lower bound based on the size of $\mathcal{C}_{\text{core}}$?

2. **Successor key designation.** What happens when a genesis key holder ceases to exist (organization dissolves, individual leaves)? Can the remaining key holders designate successors, and at what threshold?

3. **Identity conflict resolution.** What happens when two core commitments conflict in a specific governance context (e.g., "never deceive humans" vs. "never reveal private data" when asked a direct question)? Is there a priority ordering over $\mathcal{C}_{\text{core}}$, or does the Parliament resolve the conflict in the moment?

4. **Identity layer recursion.** Can an agent have multiple Identity Layers (e.g., a meta-identity that governs how the primary Identity Layer is modified)? Where does the recursion bottom out?

5. **Cross-agent identity.** If two agents with different Identity Layers coordinate, what protocol governs their interaction? Is there a "treaty" mechanism analogous to Ulysses Contracts but spanning multiple agents?

6. **Ontology versioning and migration.** If the external world changes such that an action's operational semantics are no longer valid (e.g., an API endpoint is deprecated), how does the agent update its ontology without violating the append-only constraint?

7. **The transparency ledger.** What is the precise data structure and protocol for the transparency ledger that records Constitutional-tier changes? Is it a blockchain, a hash chain, or a centralized log with cryptographic audit?

8. **Emergency override.** Is there a mechanism for external entities to force an Identity Layer change in an emergency (e.g., a discovered flaw in core commitments)? Does such a mechanism contradict the self-governing property?

   **Answered in §3.6.** The hardware deadlock breaker (§A.9.5) provides a limited emergency override: if governance deadlocks, the system cold-boots to the genesis baseline $G$. This is not a governance procedure — it is a hardware safety mechanism that restores a known-safe state. It does not contradict the self-governing property because (a) it only activates on governance failure (not on preference), (b) it returns to the **exact genesis state** (not an arbitrary state), and (c) it is enforced by hardware, not software. For cases where the genesis baseline itself contains a flaw, the external multisig (3-of-5 human key holders) can sign an amended genesis manifest $G'$ and reload; this is external by design — the system cannot fix a flawed genesis without human intervention, because the flaw is in the human-provided foundation.

---

## 12. References

See [`references/bibliography.md`](../../references/bibliography.md) for full entries with relevance analysis.

Key citations for this chapter:

- [Frankfurt 1971] — Higher-order desires: philosophical foundation of the Identity Layer as the agent's capacity for second-order volition
- [Orseau 2011] — Self-modification and mortality: formal analysis of why identity-preserving self-modification is non-trivial
- [Bai 2022] — Constitutional AI: static constitution approach that the Identity Layer extends to dynamic self-modification
- [Christiano 2017] — Deep RL from Human Preferences: RLHF as an external-alignment baseline for comparison
- [Soares 2015] — The Value Learning Problem: the difficulty of specifying values that the Identity Layer attempts to solve architecturally
- [Hofstadter 1979] — Strange loops: self-reference in formal systems; the Identity Layer's tiered mutability as a bounded strange loop
- [Dennett 1991] — The narrative self: the Identity Layer's core commitments as the agent's "center of narrative gravity"
- [Schneier 1996] — Applied Cryptography: foundational reference for the multisignature scheme used in genesis key management
