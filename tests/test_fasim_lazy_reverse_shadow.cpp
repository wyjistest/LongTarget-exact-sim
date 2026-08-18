#include "../fasim/gasal2_align_bridge.h"

#include <algorithm>
#include <iostream>
#include <random>
#include <string>
#include <vector>

namespace
{

void append_attempt(std::vector<FasimGasal2Attempt> &attempts,
                    std::vector<FasimGasal2ScoreOnlyAlignment> &scores,
                    int group,
                    int prealignScore,
                    int forwardScore,
                    int canonicalScore,
                    bool terminal,
                    int start = 10,
                    int cutlength = 20)
{
	FasimGasal2Attempt attempt;
	attempt.scoreinfo_index = group;
	attempt.prealign_score = prealignScore;
	attempt.start = start;
	attempt.cutlength = cutlength;
	attempts.push_back(attempt);

	FasimGasal2ScoreOnlyAlignment score;
	score.scoreinfo_index = group;
	score.prealign_score = prealignScore;
	score.start = start;
	score.cutlength = cutlength;
	score.forward_score = forwardScore;
	score.score = canonicalScore;
	score.query_end = forwardScore == 0 ? 0 : 15;
	score.ref_end = forwardScore == 0 ? -1 :
		(terminal ? start + cutlength - 1 : start + cutlength - 2);
	scores.push_back(score);
}

bool expect_equal(const char *label, uint64_t actual, uint64_t expected)
{
	if (actual == expected)
	{
		return true;
	}
	std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
	return false;
}

void reference_select(
	const std::vector<FasimGasal2Attempt> &attempts,
	const std::vector<FasimGasal2ScoreOnlyAlignment> &scores,
	std::vector<size_t> *selected,
	std::vector<std::string> *reasons)
{
	selected->clear();
	reasons->assign(attempts.size(), "not_selected_lower_score");
	int currentGroup = -1;
	size_t bestIndex = 0;
	int bestScore = 0;
	bool haveBest = false;
	size_t lastIndex = 0;
	int lastScore = 0;
	bool haveLast = false;
	bool emitted = false;
	auto flush = [&]()
	{
		if (currentGroup >= 0 && haveBest && !emitted)
		{
			selected->push_back(bestIndex);
			(*reasons)[bestIndex] = "best_fallback";
		}
		else if (currentGroup >= 0 && haveLast && !emitted && lastScore != 0)
		{
			selected->push_back(lastIndex);
			(*reasons)[lastIndex] = "last";
		}
		bestIndex = 0;
		bestScore = 0;
		haveBest = false;
		lastIndex = 0;
		lastScore = 0;
		haveLast = false;
		emitted = false;
	};
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		const FasimGasal2Attempt &attempt = attempts[i];
		const FasimGasal2ScoreOnlyAlignment &score = scores[i];
		if (attempt.scoreinfo_index != currentGroup)
		{
			flush();
			currentGroup = attempt.scoreinfo_index;
		}
		if (emitted)
		{
			(*reasons)[i] = "not_selected_after_threshold";
			continue;
		}
		lastIndex = i;
		lastScore = score.score;
		haveLast = true;
		if (score.score >= attempt.prealign_score)
		{
			selected->push_back(i);
			(*reasons)[i] = "threshold";
			emitted = true;
			continue;
		}
		const bool terminal = score.ref_end ==
			attempt.start + attempt.cutlength - 1;
		if (score.score > bestScore && terminal)
		{
			bestIndex = i;
			bestScore = score.score;
			haveBest = true;
		}
	}
	flush();
}

} // namespace

int main()
{
	std::vector<FasimGasal2Attempt> attempts;
	std::vector<FasimGasal2ScoreOnlyAlignment> scores;

	// Group 0: one threshold candidate fails canonical reverse, the next wins;
	// the final descriptor must be marked after-threshold and never reversed.
	append_attempt(attempts, scores, 0, 100, 90, 90, false);
	append_attempt(attempts, scores, 0, 100, 110, 95, false);
	append_attempt(attempts, scores, 0, 100, 120, 105, true);
	append_attempt(attempts, scores, 0, 100, 200, 200, false);

	// Group 1: exact terminal best is 80.  Forward 75 is certified below it;
	// forward 90 needs reverse but canonical 60 cannot replace it.
	append_attempt(attempts, scores, 1, 200, 100, 80, true);
	append_attempt(attempts, scores, 1, 200, 75, 70, true);
	append_attempt(attempts, scores, 1, 200, 90, 60, true);
	append_attempt(attempts, scores, 1, 200, 50, 40, false);

	// Group 2: failed threshold reverse is reused as the last fallback.
	append_attempt(attempts, scores, 2, 100, 110, 90, false);

	// Group 3: the final nonterminal fallback requests reverse only at flush.
	append_attempt(attempts, scores, 3, 100, 50, 40, false);

	// Group 4: forward zero proves canonical zero, including for last fallback.
	append_attempt(attempts, scores, 4, 100, 0, 0, false);

	// Group 5: a failed threshold reverse is reused to establish terminal best.
	append_attempt(attempts, scores, 5, 90, 100, 80, true);
	append_attempt(attempts, scores, 5, 90, 75, 75, true);

	FasimGasal2LazyReverseShadowResult result;
	std::string error;
	if (!fasim_gasal2_lazy_reverse_shadow_select(attempts, scores, &result, &error))
	{
		std::cerr << "lazy reverse audit failed: " << error << "\n";
		return 1;
	}

	const size_t expectedSelected[] = {2, 4, 8, 9, 11};
	const char *expectedReasons[] = {
		"not_selected_lower_score",
		"not_selected_lower_score",
		"threshold",
		"not_selected_after_threshold",
		"best_fallback",
		"not_selected_lower_score",
		"not_selected_lower_score",
		"not_selected_lower_score",
		"last",
		"last",
		"not_selected_lower_score",
		"best_fallback",
		"not_selected_lower_score"
	};

	bool ok = result.ok;
	ok = expect_equal("selected count", result.selected_attempt_indexes.size(), 5) && ok;
	for (size_t i = 0; i < 5 && i < result.selected_attempt_indexes.size(); ++i)
	{
		if (result.selected_attempt_indexes[i] != expectedSelected[i])
		{
			std::cerr << "selected[" << i << "] mismatch\n";
			ok = false;
		}
	}
	for (size_t i = 0; i < attempts.size(); ++i)
	{
		if (result.selection_reasons[i] != expectedReasons[i])
		{
			std::cerr << "reason[" << i << "]: expected " << expectedReasons[i]
			          << ", got " << result.selection_reasons[i] << "\n";
			ok = false;
		}
	}

	ok = expect_equal("total attempts", result.total_attempts, 13) && ok;
	ok = expect_equal("full reverse attempts", result.full_reverse_attempts, 12) && ok;
	ok = expect_equal("lazy reverse attempts", result.lazy_reverse_attempts, 7) && ok;
	ok = expect_equal("threshold reverse attempts",
	                  result.lazy_reverse_threshold_attempts, 4) && ok;
	ok = expect_equal("best reverse attempts", result.lazy_reverse_best_attempts, 2) && ok;
	ok = expect_equal("last reverse attempts", result.lazy_reverse_last_attempts, 1) && ok;
	ok = expect_equal("best reverse reuse", result.lazy_reverse_reused_for_best, 1) && ok;
	ok = expect_equal("last reverse reuse", result.lazy_reverse_reused_for_last, 1) && ok;
	ok = expect_equal("threshold groups", result.threshold_groups, 1) && ok;
	ok = expect_equal("best groups", result.best_fallback_groups, 2) && ok;
	ok = expect_equal("last groups", result.last_groups, 2) && ok;
	ok = expect_equal("empty groups", result.empty_groups, 1) && ok;
	ok = expect_equal("reverse reason conservation",
	                  result.lazy_reverse_threshold_attempts +
	                    result.lazy_reverse_best_attempts +
	                    result.lazy_reverse_last_attempts,
	                  result.lazy_reverse_attempts) && ok;
	if (result.lazy_reverse_envelope_cells >= result.full_reverse_envelope_cells)
	{
		std::cerr << "lazy reverse cell proxy did not decrease\n";
		ok = false;
	}

	// Property-check the upper-bound proof against the literal ordered
	// consumer on varied group sizes, thresholds, terminal states, and scores.
	std::mt19937 rng(0x6c617a79u);
	for (int trial = 0; trial < 500 && ok; ++trial)
	{
		std::vector<FasimGasal2Attempt> randomAttempts;
		std::vector<FasimGasal2ScoreOnlyAlignment> randomScores;
		const int groups = 1 + static_cast<int>(rng() % 24);
		for (int group = 0; group < groups; ++group)
		{
			const int count = 1 + static_cast<int>(rng() % 9);
			for (int ordinal = 0; ordinal < count; ++ordinal)
			{
				const int prealign = static_cast<int>(rng() % 241);
				const int forward = static_cast<int>(rng() % 281);
				const int canonical = static_cast<int>(rng() % (forward + 1));
				const bool terminal = (rng() & 1u) != 0;
				append_attempt(randomAttempts, randomScores, group, prealign,
				              forward, canonical, terminal,
				              20 + ordinal, 30 + ordinal);
			}
		}
		FasimGasal2LazyReverseShadowResult randomResult;
		std::string randomError;
		if (!fasim_gasal2_lazy_reverse_shadow_select(
				randomAttempts, randomScores, &randomResult, &randomError))
		{
			std::cerr << "random lazy audit failed at trial " << trial
			          << ": " << randomError << "\n";
			ok = false;
			break;
		}
		std::vector<size_t> expectedIndexes;
		std::vector<std::string> expectedReasons;
		reference_select(randomAttempts, randomScores,
		                 &expectedIndexes, &expectedReasons);
		if (randomResult.selected_attempt_indexes != expectedIndexes ||
			randomResult.selection_reasons != expectedReasons)
		{
			std::cerr << "random lazy selection mismatch at trial " << trial
			          << "\n";
			ok = false;
		}
	}
	return ok ? 0 : 1;
}
