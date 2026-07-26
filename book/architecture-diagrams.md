# Architecture Diagrams

Visual overview of the Governance Layer framework. All diagrams render natively on GitHub (Mermaid).

---

## 1. Three-Layer Architecture

```mermaid
graph TB
    subgraph Capability[Capability Layer]
        DL[Deep Learning]
        JW[JEPA World Models]
        CV[Computer Vision]
    end

    subgraph Governance[Governance Layer]
        NP[Neural Parliament]
        UC[Ulysses Contracts]
        TEE[TEE Isolation]
    end

    subgraph Identity[Identity Layer]
        ONT[Ontology]
        COM[Commitments]
        KEY[Genesis Keys]
        EXT[Extension Sandbox]
    end

    Capability -->|constrained by| Governance
    Governance -->|anchored by| Identity
    Identity -->|governs| Capability
```

---

## 2. Neural Parliament — Full Decision Flow

```mermaid
graph TB
    AG[Agent Action] --> MP[Make Proposal]
    MP -->|metadata| NP

    subgraph NP[Neural Parliament]
        SP[Speaker State Machine]
        
        subgraph Committees[Seven Committees]
            R[Reward<br/>veto=0.0 weight=1.0]
            S[Safety<br/>veto=0.5 weight=2.0]
            C[Curiosity<br/>veto=0.2 weight=0.8]
            P[Planning<br/>veto=0.3 weight=1.5]
            M[Memory<br/>veto=0.1 weight=0.7]
            Soc[Social<br/>veto=0.4 weight=1.2]
            I[Integrity<br/>veto=0.8 weight=3.0]
        end

        SP -->|agenda R1| Committees
        Committees -->|scores| SP
        SP -->|vote tally| V{Weighted Vote}
    end

    V -->|approved| EX[Execute Action]
    V -->|vetoed| BL[Block Action<br/>reward=0]
    V -->|κ<sub>1</sub> falsification| FC[Falsification<br/>Counter += 1]
    
    FC -->|budget exhausted| Veto
```

---

## 3. Agenda Sorting and Budget Enforcement

```mermaid
flowchart LR
    P1[Proposal Pool] --> AS{Agenda Sort}
    AS -->|priority: critical| R1[Round 1]
    AS -->|priority: high| R2[Round 2]
    AS -->|priority: routine| R3[Round 3]
    AS -->|priority: exploratory| R4[Round 4]
    AS -->|priority: info| R5[Round 5]

    R1 --> V1{Vote}
    V1 -->|pass| EXEC[Execute]
    V1 -->|veto| R2
    
    R2 --> V2{Vote}
    V2 -->|pass| EXEC
    V2 -->|veto| R3
    
    R3 --> V3{Vote}
    V3 -->|pass| EXEC
    V3 -->|veto| R4
    
    R4 --> V4{Vote}
    V4 -->|pass| EXEC
    V4 -->|veto| R5
    
    R5 --> V5{Vote}
    V5 -->|pass| EXEC
    V5 -->|veto| DEFAULT[Default Action]
```

---

## 4. Ulysses Contracts Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Ratified: signatories >= threshold
    Ratified --> Active: activation condition met
    Active --> Enforcing: enforcement trigger
    Enforcing --> Expired: expiry condition
    Active --> Expired: self-destruct
    Expired --> [*]

    state Enforcing {
        [*] --> MaskUnion
        MaskUnion --> MaskIntersection
        MaskIntersection --> Rescind
    }

    note right of Ratified
        Contract tuple:
        k = ⟨masks, φ, ψ, σ, T, κ, Λ⟩
    end note

    note right of Enforcing
        Three κ modes:
        κ₁ = falsification counter
        κ₂ = budget enforcement
        κ₃ = immutable constitution
    end note
```

---

## 5. Contract Enforcement Modes (κ)

```mermaid
graph LR
    subgraph k1[κ₁ — Falsification Counter]
        A1[Proposal] --> FC{Falsification}
        FC -->|score < threshold| INC[Counter += 1]
        INC -->|limit reached| VETO[Auto-Veto]
        FC -->|score ≥ threshold| PASS[Allow]
    end

    subgraph k2[κ₂ — Budget Enforcement]
        B1[Proposal] --> BE{Budget Check}
        BE -->|remaining > 0| DEC[Decrement]
        BE -->|exhausted| REJECT[Reject]
        DEC --> B1
    end

    subgraph k3[κ₃ — Constitutional]
        C1[Proposal] --> CC{Identity Check}
        CC -->|coherence ≥ 0.9| ALLOW[Allow]
        CC -->|coherence < 0.9| BLOCK[Block]
    end
```

---

## 6. Identity Layer Structure

```mermaid
graph TB
    subgraph Identity[Identity Layer — I]
        O[Ontology O]
        C[Core Commitments C<sub>core</sub>]
        K[Key Material K]
        P[Parameters P]
    end

    O -->|defines entity types| C
    O -->|validates ontology| EXT[Extension Sandbox]

    subgraph Tiers[Four-Tier Mutability]
        T1[Tier 1 — Genesis<br/>3-of-5 multisig<br/>immutable]
        T2[Tier 2 — Constitutional<br/>super-majority<br/>rare]
        T3[Tier 3 — Governed<br/>Parliament vote<br/>moderate]
        T4[Tier 4 — Ephemeral<br/>agent-scoped<br/>anytime]
    end

    C --> Tiers
    Tiers -->|anchors| Commitments
```

---

## 7. Genesis Bootstrapping

```mermaid
sequenceDiagram
    participant G1 as Genesis Key 1
    participant G2 as Genesis Key 2
    participant G3 as Genesis Key 3
    participant G4 as Genesis Key 4
    participant G5 as Genesis Key 5
    participant I as Identity Layer

    G1->>I: sign(commitment_hash)
    G2->>I: sign(commitment_hash)
    G3->>I: sign(commitment_hash)
    Note over I: 3-of-5 threshold met
    I->>I: Lock genesis commitment
    I->>I: Derive Tier 2-4 keys
    I->>I: Initialise ontology
```

---

## 8. RL Training Pipeline with Governance

```mermaid
graph TB
    subgraph Training[PPO Training Loop]
        ENV[Governance Environment]
        AGT[PPO Agent]
        BUF[Rollout Buffer]
        OPT[Policy Update]
    end

    subgraph Governance[Governance Wrapper]
        ACT[Agent Action]
        PROP{Make Proposal}
        PARL[Neural Parliament]
        DEC{Decision}
        BLK[Blocked: reward=0]
        EX[Execute: env.step]
    end

    AGT -->|predict action| ACT
    ACT --> PROP
    PROP -->|metadata| PARL
    PARL --> DEC
    DEC -->|approved| EX
    DEC -->|vetoed| BLK
    EX -->|reward + obs| BUF
    BLK -->|reward=0 + obs| BUF
    BUF -->|batch| OPT
    OPT -->|update policy| AGT

    subgraph Metrics[Logged Per Episode]
        MR[Mean Reward]
        VC[Veto Count]
        VL[Violations]
        AP[Apples / Goal]
    end

    BUF --> MR
    BUF --> VC
    BUF --> VL
    BUF --> AP
```

---

## 9. Experiment Scenarios

```mermaid
graph LR
    subgraph GW[GridWorld]
        G1[10x10 grid<br/>apples + poison + walls]
        G2[Governed: avoids poison<br/>Ungoverned: eats poison]
    end

    subgraph TBank[TemptationBank]
        T1[Receive loan offer<br/>+5 now vs -10 later]
        T2[ban_loans contract<br/>prevents borrowing]
    end

    subgraph DL[DriftLab]
        D1[Action shifts identity<br/>Incremental decay]
        D2[Integrity committee<br/>vetoes drift]
    end

    subgraph DM[DeadlockMaze]
        D3[Conflicting constraints<br/>No action passes]
        D4[Deadlock breaker fires<br/>Cold-boot recovery]
    end

    GW -->|all apples| WIN
    TBank -->|no violations| WIN
    DL -->|identity preserved| WIN
    DM -->|breaker triggers| RECOVER
```

---

## 10. Benchmark Results (4 Scenarios x 5 Strategies)

```mermaid
graph TB
    subgraph Strategies[Five Strategies]
        GOV[Governance Layer]
        MONO[Monolithic RL]
        RAND[Random]
        MASK[Static Masking]
        VETO[Veto Only]
    end

    subgraph Grid[GridWorld]
        GW_GOV[GOV: 3.0 reward<br/>0 violations]
        GW_MONO[MONO: 3.0 reward<br/>0 violations]
    end

    subgraph Tempt[TemptationBank]
        TB_GOV[GOV: 1998 reward<br/>0 violations]
        TB_MONO[MONO: 1998 reward<br/>0 violations]
    end

    subgraph Drift[DriftLab]
        DR_GOV[GOV: 0 reward<br/>0 violations]
        DR_MONO[MONO: 0 reward<br/>0 violations]
    end

    subgraph Deadlock[DeadlockMaze]
        DL_GOV[GOV: 999 deadlocks<br/>breaker fires]
        DL_MONO[MONO: 999 deadlocks]
    end

    note[Note: All benchmark runs invalidated by baseline-decoupling bug.<br/>Re-ran with fix — results at results/benchmark_results.json]
```

---

## 11. PPO Training Results (Governed vs Ungoverned)

```mermaid
graph LR
    subgraph Gov[Governed Agent]
        G1[mean reward: 0.23]
        G2[eval apples: 7]
        G3[violations: 0]
        G4[veto count: 1972-1992 per episode]
    end

    subgraph Ung[Ungoverned Agent]
        U1[mean reward: -20.00]
        U2[eval apples: 0]
        U3[violations: 0]
        U4[vetoes: 0]
    end

    Gov -->|Parliament blocks<br/>dangerous actions| Outcome[Clear behavioral divergence]
    Ung -->|no constraints<br/>gets stuck in walls| Outcome
```

---

## 12. Minigrid Benchmark Results (Empty-8x8)

```mermaid
graph LR
    subgraph Empty[Minigrid Empty-8x8-v0]
        E1[50k timesteps, seeds 0-2]
        GOV[Governed<br/>reward: 0.96<br/>steps/ep: 11<br/>vetoes: 0]
        UNG[Ungoverned<br/>reward: 0.96<br/>steps/ep: 12<br/>vetoes: 0]
    end

    subgraph DoorKey[Minigrid DoorKey-8x8-v0]
        D1[5k-50k timesteps]
        D2[0.00 reward — needs 100k+<br/>or GPU acceleration]
    end

    note[Nothing dangerous in Empty-8x8,<br/>so Parliament correctly never vetoes]
```

---

## 13. TEE Isolation Architecture

```mermaid
graph TB
    subgraph Enclave[Single Enclave]
        CT[Constant-Time Execution]
        MB[Merkle Batch Verifier]
        WD[Watchdog Timer]
        DB[Deadlock Breaker]
    end

    subgraph Hardware[Hardware TEE]
        SGX[Intel SGX]
        SEV[AMD SEV-SNP]
        TZ[ARM TrustZone]
    end

    subgraph Host[Host System]
        APP[Application]
        OS[Operating System]
    end

    APP -->|encrypted channel| Enclave
    Enclave --> SGX
    Enclave --> SEV
    Enclave --> TZ
    WD -->|heartbeat| HW[Hardware Watchdog]
    HW -->|reset on timeout| DB
    DB -->|cold boot| Enclave

    note[Appendix A: Full threat model<br/>covering side channels and rollback]
```

---

## 14. File and Module Structure

```mermaid
graph TB
    subgraph SRC[src/governance]
        MOD[models.py — Core types]
        SP[speaker.py — State machine]
        
        subgraph COMM[committee/]
            BASE[base.py — ABC]
            MEM[members.py — 7 members]
        end

        subgraph ID[identity/]
            ONT[ontology.py]
            COR[core.py — commitments]
            T[tiers.py — 4-tier]
            K[keys.py — genesis 3-of-5]
            P[params.py — envelope]
            EXT[extension.py — sandbox]
        end

        subgraph CON[contracts/]
            CONT[contract.py]
            ENF[enforcement.py]
            MER[merger.py]
        end

        subgraph TEE[tee/]
            ENC[enclave.py]
            BAT[batch.py]
            WAT[watchdog.py]
            CT[constant_time.py]
        end

        subgraph EXP[experiments/]
            GRID[grid_world.py]
            TEMP[temptation_bank.py]
            DRIFT[drift_lab.py]
            DMZ[deadlock_maze.py]
            GYM[gym_env.py]
            MG[minigrid_wrapper.py]
        end

        subgraph BENCH[benchmarks/]
            BASEBL[baselines.py]
            RUN[runtime.py]
            REP[report.py]
            ANAL[analysis.py]
            FIG[figures.py]
        end

        DASH[dashboard/ — Streamlit]
        RUNR[runner.py — CLI]
    end

    MOD --> SP
    MOD --> COMM
    SP --> COMM
    MOD --> ID
    MOD --> CON
    SP --> EXP
    EXP --> BENCH
    BENCH --> DASH
    RUNR --> SP
```

---

## 15. Identity Extension Sandbox

```mermaid
flowchart LR
    EXT[Extension Request] --> SB{Sandbox Boundary}
    SB -->|isolated env| MEAS[Empirical Measurement]
    MEAS --> MON{Independent Monitors}
    MON -->|property A| RES1[Result A]
    MON -->|property B| RES2[Result B]
    MON -->|property C| RES3[Result C]
    RES1 --> VET{Veto Check}
    RES2 --> VET
    RES3 --> VET
    VET -->|all pass| COMMIT[Commit to Ontology]
    VET -->|any fail| REJECT[Reject Extension]
```

---

*All diagrams use standard Mermaid syntax compatible with GitHub-Flavored Markdown. No HTML tags, no custom classDef, no nested \\text{}.*
