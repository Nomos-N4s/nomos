# References

This directory contains the living bibliography for the Nomos research project.

## Purpose

The bibliography serves two functions:

1. **Anchor claims.** Every assertion about prior art, existing limitations, or conceptual precursors is backed by a citation in `bibliography.md`.
2. **Pre-empt criticism.** By explicitly documenting related work and stating where our approach differs, we address "this is just X" objections before they arrive.

The sustained version of (2) is [Chapter 5: Related Work](../book/chapter-05/05-related-work.md),
which places Nomos against its nearest neighbors — shielding, CMDPs, reward
machines, guaranteed-safe AI, and the agent-governance frameworks — on four
axes, and states the concession as well as the delta for each.

## Citation Key Convention

Every entry in `bibliography.md` has an anchor key of the form:

    [AuthorShort Year]

Examples: `[Minsky 1986]`, `[Bai 2022]`, `[Friston 2010]`

When two entries would collide on author surname and year, disambiguate with a
lowercase suffix assigned in publication order: `[Wang 2025a]` (AgentSpec, March
2025) precedes `[Wang 2025b]` (MI9, August 2025). Multi-word surnames close up in
the key: `[delaChica 2026]`.

Chapters cite these keys inline. The bibliography entry provides the full citation, relevance analysis, and departure notes.

## Entry Format

```markdown
### [AuthorShort Year]
**Authors** (Year). *Title*. Venue. [URL]

**Core claim:** One-sentence distillation.

**Relevance to GL:** 2-3 sentences connecting to our thesis.

**Insight we borrow:** The specific idea we build on or argue against.

**Where we depart:** (Optional) How our framework adds what this work does not cover.
```

## Sorting

Entries in `bibliography.md` are sorted **conceptual → chronological → alphabetical**:
1. Grouped by topic area (conceptual proximity to Governance Layer concepts)
2. Within each group, ascending by year
3. Within the same year, alphabetically by first author

## Living Process

This bibliography evolves:
- When a new chapter is written, its citations are added
- When missed prior art is identified, it is added
- When new relevant work is published, it is added
- Each entry carries a date-stamped "Added" field on first commit

## When Adding an Entry

1. Place it in the appropriate conceptual group
2. Within the group, insert at the correct chronological position
3. If the group does not exist, create it at the appropriate position among groups
4. Ensure the citation key is unique and the anchor is properly formatted
