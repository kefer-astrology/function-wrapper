---
title: "Performance Bottleneck Analysis"
description: "Root-cause analysis of slow batch transit computation"
weight: 30
---

# Performance Bottleneck Analysis: Why 20 Minutes for a Day?

## Problem

**Expected**: Swisseph can compute a whole day in a fraction of a second  
**Actual**: Taking 20 minutes to compute a whole day

## Root Cause Analysis

### Current Implementation Flow

For each timestamp in `compute_and_store_series()`:

1. Call `compute_positions()`
2. `compute_positions()` calls `compute_subject()`
3. `compute_subject()` creates a new `AstrologicalSubject`
4. `AstrologicalSubject` initialization does full computation
5. Extract positions via the `Subject` wrapper and data extraction
6. Call `store_positions()` which does an individual `INSERT`

### Bottlenecks

#### 1. `AstrologicalSubject` creation overhead

```python
# This happens for EVERY timestamp!
subj = compute_subject(name, dt_str, loc_str)  # Creates new AstrologicalSubject
```

Even though the Swisseph math is fast, creating the full
`AstrologicalSubject` object adds heavy overhead:

- object initialization
- data structure building
- multiple method calls
- repeated memory allocation

#### 2. Individual `INSERT` statements

```python
for datetime_str, positions in positions_batch:
    self.store_positions(...)  # Individual INSERT per timestamp
```

Even though values are logically batched, storage still performs one insert per
timestamp instead of using `executemany()` with a single large row set.

#### 3. Subject wrapper overhead

```python
subject_wrapper = Subject(name)
subject_wrapper.computed = subj
object_list, degrees_list, labels = subject_wrapper.data()
```

This is smaller than the first two issues, but still adds avoidable object
creation and method dispatch in a hot loop.

## Performance Math

For 1 day with 1-minute intervals:

- timestamps: 1,440
- current runtime: 20 minutes = 1,200 seconds
- per timestamp: about `0.83s`

Expected if computation dominated:

- Swisseph computation: about `0.001s` per timestamp
- total expected: about `1.4s`

That implies the run time is mostly overhead rather than astronomy math.

## Candidate Solutions

### Option 1: direct Swisseph access

Bypass Kerykeion's `AstrologicalSubject` and call Swisseph directly:

```python
import swisseph as swe

def compute_positions_swisseph_direct(dt, location, planets):
    jd = swe.julday(
        dt.year, dt.month, dt.day,
        dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
        swe.GREG_CAL,
    )
    ...
```

This should be the fastest path for bulk transit work.

### Option 2: reuse `AstrologicalSubject`

If Kerykeion supports it safely, reuse one object and mutate time rather than
recreating it for each timestamp.

### Option 3: batch inserts

Collect rows first, then store with one `executemany()` call:

```python
self.conn.executemany(
    "INSERT OR REPLACE INTO computed_positions (...) VALUES (?, ?, ?, ...)",
    rows,
)
```

## Recommended Solution

Use a hybrid approach:

1. Direct Swisseph for bulk Kerykeion/Swisseph series work
2. Batch insert storage writes
3. Keep the current object-oriented path for single interactive chart
   computations where readability matters more than hot-path speed

## Expected Improvement

- current: 20 minutes for 1 day
- target: about 1.4 seconds for 1 day
- rough speedup: hundreds of times faster

## Related Notes

- [Performance Fix Summary](performance_fix_summary)
- [Architecture](architecture)
