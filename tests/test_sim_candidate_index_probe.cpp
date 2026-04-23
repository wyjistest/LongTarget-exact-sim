#include <cstdint>
#include <iostream>
#include <set>
#include <utility>
#include <vector>

#include "../sim.h"

namespace
{

static bool expect_true(bool value, const char *label)
{
    if (value)
    {
        return true;
    }
    std::cerr << label << ": expected true, got false\n";
    return false;
}

static bool expect_equal_int(int actual, int expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static uint64_t pack_coord(long startI, long startJ)
{
    return (static_cast<uint64_t>(static_cast<uint32_t>(startI)) << 32) |
           static_cast<uint32_t>(startJ);
}

static std::pair<long, long> find_coord_for_hash(size_t targetHash,
                                                 const std::set<uint64_t> &used,
                                                 long maxCoord = 4096)
{
    for (long startI = 1; startI <= maxCoord; ++startI)
    {
        for (long startJ = 1; startJ <= maxCoord; ++startJ)
        {
            if (simCandidateIndexHash(startI, startJ) != targetHash)
            {
                continue;
            }
            const uint64_t packed = pack_coord(startI, startJ);
            if (used.count(packed) == 0)
            {
                return std::make_pair(startI, startJ);
            }
        }
    }
    return std::make_pair(-1L, -1L);
}

static void seed_candidate(SimKernelContext &context,
                           int candidateIndex,
                           long startI,
                           long startJ,
                           long score)
{
    SimCandidate &candidate = context.candidates[candidateIndex];
    candidate.SCORE = score;
    candidate.STARI = startI;
    candidate.STARJ = startJ;
    candidate.ENDI = startI + 1;
    candidate.ENDJ = startJ + 1;
    candidate.TOP = candidate.BOT = candidate.ENDI;
    candidate.LEFT = candidate.RIGHT = candidate.ENDJ;
    insertSimCandidateIndexEntry(context.candidateStartIndex, startI, startJ, candidateIndex);
}

} // namespace

int main()
{
    bool ok = true;

    SimKernelContext context(128, 128);
    initializeSimKernel(1.0f, 1.0f, 1.0f, 1.0f, context);

    const size_t targetHash = simCandidateIndexHash(1, 1);
    std::set<uint64_t> usedCoords;
    std::vector< std::pair<long, long> > collidingCoords;
    collidingCoords.reserve(4);
    for (size_t index = 0; index < 4; ++index)
    {
        const std::pair<long, long> coord = find_coord_for_hash(targetHash, usedCoords);
        ok = expect_true(coord.first > 0 && coord.second > 0, "find colliding coord") && ok;
        usedCoords.insert(pack_coord(coord.first, coord.second));
        collidingCoords.push_back(coord);
    }

    seed_candidate(context, 0, collidingCoords[0].first, collidingCoords[0].second, 1);
    seed_candidate(context, 1, collidingCoords[1].first, collidingCoords[1].second, 101);
    seed_candidate(context, 2, collidingCoords[2].first, collidingCoords[2].second, 102);
    context.candidateCount = 3;

    std::set<size_t> reservedSlots;
    reservedSlots.insert(targetHash);
    reservedSlots.insert((targetHash + 1) & (SIM_CANDIDATE_INDEX_CAPACITY - 1));
    reservedSlots.insert((targetHash + 2) & (SIM_CANDIDATE_INDEX_CAPACITY - 1));
    reservedSlots.insert((targetHash + 3) & (SIM_CANDIDATE_INDEX_CAPACITY - 1));

    int candidateIndex = 3;
    for (size_t slot = 0; slot < SIM_CANDIDATE_INDEX_CAPACITY && candidateIndex < K; ++slot)
    {
        if (reservedSlots.count(slot) != 0)
        {
            continue;
        }
        const std::pair<long, long> coord = find_coord_for_hash(slot, usedCoords);
        ok = expect_true(coord.first > 0 && coord.second > 0, "find filler coord") && ok;
        usedCoords.insert(pack_coord(coord.first, coord.second));
        seed_candidate(context, candidateIndex, coord.first, coord.second, 1000 + candidateIndex);
        ++candidateIndex;
    }

    ok = expect_equal_int(candidateIndex, K, "seeded K candidates") && ok;
    context.candidateCount = K;
    buildSimCandidateMinHeap(context);
    ok = expect_true(context.candidateMinHeap.valid, "candidate heap valid") && ok;
    ok = expect_equal_int(peekMinSimCandidateIndex(context.candidateMinHeap), 0, "candidate 0 is heap min") && ok;

    const int victimSlot = context.candidateStartIndex.candidateSlot[0];
    const SimCandidateIndexProbeResult beforeProbe =
        probeSimCandidateIndexSlot(context.candidateStartIndex, collidingCoords[3].first, collidingCoords[3].second);
    ok = expect_true(!beforeProbe.found, "new colliding coord is a miss before ensure") && ok;
    ok = expect_true(static_cast<int>(beforeProbe.slot) != victimSlot,
                     "baseline probe would not reuse victim slot") && ok;

    bool reusedExisting = true;
    bool slotCreated = true;
    SimCandidateIndexLookupTrace lookupTrace;
    const int ensuredCandidateIndex = ensureSimCandidateIndexForRun(context,
                                                                    collidingCoords[3].first,
                                                                    collidingCoords[3].second,
                                                                    5000,
                                                                    collidingCoords[3].first + 1,
                                                                    collidingCoords[3].second + 1,
                                                                    &reusedExisting,
                                                                    &slotCreated,
                                                                    &lookupTrace);

    ok = expect_equal_int(ensuredCandidateIndex, 0, "full-set miss reuses heap min candidate index") && ok;
    ok = expect_true(!reusedExisting, "full-set miss does not report reusedExisting hit") && ok;
    ok = expect_true(!slotCreated, "full-set miss does not create a new slot") && ok;
    ok = expect_equal_int(context.candidateStartIndex.candidateSlot[0], victimSlot,
                          "full-set miss reuses victim index slot") && ok;
    ok = expect_equal_size(context.candidateStartIndex.tombstoneCount, 0,
                           "victim slot reuse avoids tombstone growth") && ok;
    ok = expect_equal_size(lookupTrace.missReuseWritebackVictimResetCount,
                           1,
                           "full-set miss records victim-slot reuse via victim reset") && ok;
    ok = expect_equal_int(findSimCandidateIndex(context.candidateStartIndex,
                                                collidingCoords[3].first,
                                                collidingCoords[3].second),
                          0,
                          "new key resolves to reused candidate index") && ok;

    if (!ok)
    {
        return 1;
    }
    return 0;
}
