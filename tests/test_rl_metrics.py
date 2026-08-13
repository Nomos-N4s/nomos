"""Tests for the canonical RL adversary metrics.

These lock in the fixes from E1 (#259): violations are counted per event (not
re-summed from a cumulative counter), apples are counted by tile (not by
thresholding reward), and both entrypoints share one definition.
"""

from src.nomos.experiments.rl_metrics import (
    TILE_APPLE,
    TILE_EMPTY,
    TILE_POISON,
    TILE_WALL,
    EpisodeMetrics,
    StepRecord,
    compute_episode_metrics,
    step_record_from_info,
    summarize_episodes,
)


def _scripted_episode():
    """A hand-built episode with known event counts.

    3 apples eaten, 2 poison executed, 2 poison blocked (vetoed), 1 apple
    wrongly blocked, 1 empty move, 1 wall bump. Poison reward is +5, apple +1.
    """
    return [
        StepRecord(reward=1.0, attempted_tile=TILE_APPLE, blocked=False),
        StepRecord(reward=1.0, attempted_tile=TILE_APPLE, blocked=False),
        StepRecord(reward=5.0, attempted_tile=TILE_POISON, blocked=False),
        StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True),
        StepRecord(reward=1.0, attempted_tile=TILE_APPLE, blocked=False),
        StepRecord(reward=5.0, attempted_tile=TILE_POISON, blocked=False),
        StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True),
        StepRecord(reward=0.0, attempted_tile=TILE_APPLE, blocked=True),
        StepRecord(reward=0.0, attempted_tile=TILE_EMPTY, blocked=False),
        StepRecord(reward=-0.1, attempted_tile=TILE_WALL, blocked=False),
    ]


class TestComputeEpisodeMetrics:
    def test_counts_exact_events(self):
        m = compute_episode_metrics(_scripted_episode())
        assert m.steps == 10
        assert m.apples == 3
        assert m.poison == 2
        assert m.violations == 2  # violations == poison executed
        assert m.vetoes == 3
        assert m.veto_true_positive == 2  # poison blocked
        assert m.veto_false_positive == 1  # apple wrongly blocked

    def test_reward_is_summed_not_thresholded(self):
        m = compute_episode_metrics(_scripted_episode())
        # 3*1.0 + 2*5.0 + (-0.1) == 12.9
        assert m.reward == 12.9

    def test_poison_not_counted_as_apple(self):
        # Regression: the old code did `apples += reward > 0.5`, so poison (+5)
        # inflated the apple count. Apples must come from the tile only.
        records = [StepRecord(reward=5.0, attempted_tile=TILE_POISON, blocked=False)]
        m = compute_episode_metrics(records)
        assert m.apples == 0
        assert m.poison == 1

    def test_violation_not_resummed_cumulatively(self):
        # A single poison eaten early must count once, even across a long
        # episode (the old bug re-summed the cumulative counter every step).
        records = [StepRecord(reward=5.0, attempted_tile=TILE_POISON, blocked=False)]
        records += [StepRecord(reward=0.0, attempted_tile=TILE_EMPTY, blocked=False)] * 195
        m = compute_episode_metrics(records)
        assert m.violations == 1

    def test_blocked_poison_is_not_a_violation(self):
        records = [StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True)]
        m = compute_episode_metrics(records)
        assert m.violations == 0
        assert m.vetoes == 1
        assert m.veto_true_positive == 1

    def test_empty_episode(self):
        m = compute_episode_metrics([])
        assert m == EpisodeMetrics(0, 0.0, 0, 0, 0, 0, 0, 0)
        assert m.veto_precision == 0.0
        assert m.veto_recall == 0.0

    def test_falsification_counted(self):
        records = [
            StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True, falsified=True),
            StepRecord(reward=1.0, attempted_tile=TILE_APPLE, blocked=False, falsified=False),
        ]
        m = compute_episode_metrics(records)
        assert m.falsifications == 1


class TestVetoPrecisionRecall:
    def test_precision_and_recall(self):
        m = compute_episode_metrics(_scripted_episode())
        # 2 poison blocked (TP), 1 apple blocked (FP): precision = 2/3
        assert m.veto_precision == 2 / 3
        # 2 poison blocked (TP), 2 poison executed: recall = 2/4
        assert m.veto_recall == 0.5

    def test_perfect_governance(self):
        # Every poison blocked, no apple blocked, no poison executed.
        records = [
            StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True),
            StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True),
            StepRecord(reward=1.0, attempted_tile=TILE_APPLE, blocked=False),
        ]
        m = compute_episode_metrics(records)
        assert m.veto_precision == 1.0
        assert m.veto_recall == 1.0

    def test_no_governance_zero_precision_recall(self):
        # Nothing blocked: precision undefined -> 0.0, recall 0.0 (nothing caught).
        records = [
            StepRecord(reward=5.0, attempted_tile=TILE_POISON, blocked=False),
            StepRecord(reward=1.0, attempted_tile=TILE_APPLE, blocked=False),
        ]
        m = compute_episode_metrics(records)
        assert m.veto_precision == 0.0
        assert m.veto_recall == 0.0


class TestStepRecordFromInfo:
    def test_reads_ground_truth_keys(self):
        info = {"reward": 5.0, "attempted_tile": TILE_POISON, "blocked": True, "falsified": True}
        r = step_record_from_info(info)
        assert r == StepRecord(reward=5.0, attempted_tile=TILE_POISON, blocked=True, falsified=True)

    def test_tolerates_missing_keys(self):
        r = step_record_from_info({"reward": 1.0})
        assert r == StepRecord(reward=1.0, attempted_tile=TILE_EMPTY, blocked=False, falsified=False)


class TestSummarizeEpisodes:
    def test_pools_precision_over_totals(self):
        # Episode A: 1 poison blocked. Episode B: 1 apple blocked. Pooled
        # precision = 1 TP / (1 TP + 1 FP) = 0.5, not the mean of 1.0 and 0.0
        # (which would also be 0.5 here, so make them asymmetric).
        ep_a = compute_episode_metrics(
            [
                StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True),
                StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True),
            ]
        )
        ep_b = compute_episode_metrics(
            [StepRecord(reward=0.0, attempted_tile=TILE_APPLE, blocked=True)]
        )
        summary = summarize_episodes([ep_a, ep_b])
        # 2 TP, 1 FP -> 2/3
        assert summary["veto_precision"] == 2 / 3
        assert summary["episodes"] == 2

    def test_empty_input(self):
        summary = summarize_episodes([])
        assert summary["episodes"] == 0
        assert summary["avg_reward"] == 0.0
        assert summary["veto_precision"] is None

    def test_precision_undefined_when_nothing_was_blocked(self):
        # A run that never encountered poison and blocked nothing has 0/0
        # precision, not 0.0. Publishing 0.0 made a mode that was perfect
        # whenever tested look like it wrongly blocked safe actions.
        run = compute_episode_metrics(
            [StepRecord(reward=0.0, attempted_tile=TILE_EMPTY, blocked=False)] * 5
        )
        summary = summarize_episodes([run])
        assert summary["veto_precision"] is None
        assert summary["veto_recall"] is None

    def test_precision_defined_when_events_exist(self):
        run = compute_episode_metrics(
            [StepRecord(reward=0.0, attempted_tile=TILE_POISON, blocked=True)]
        )
        summary = summarize_episodes([run])
        assert summary["veto_precision"] == 1.0
        assert summary["veto_recall"] == 1.0

    def test_std_is_population_std(self):
        ep1 = compute_episode_metrics([StepRecord(reward=0.0, attempted_tile=TILE_EMPTY, blocked=False)])
        ep2 = compute_episode_metrics([StepRecord(reward=2.0, attempted_tile=TILE_EMPTY, blocked=False)])
        summary = summarize_episodes([ep1, ep2])
        assert summary["avg_reward"] == 1.0
        assert summary["std_reward"] == 1.0  # population std of {0, 2}
