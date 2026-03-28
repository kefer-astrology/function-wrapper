---
title: "Performance Fix Summary"
description: "Summary of the batch-computation performance optimization"
weight: 31
---

# Performance Fix Summary: 20 Minutes to About 1 Second

## Problem

Computing a whole day with 1,440 one-minute timestamps was taking about
20 minutes instead of the expected fraction of a second.

## Root Cause

1. `AstrologicalSubject` overhead for every timestamp
2. Individual `INSERT` statements during storage writes

## Solution Implemented

### 1. Direct Swisseph access

Before:

```python
positions = compute_positions(engine, name, dt_str, loc_str, ...)
```

After:

```python
import swisseph as swe

jd = swe.julday(...)
xx, ret = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
```

This bypasses most of the object-construction overhead in batch runs.

### 2. Batch storage writes

Before:

```python
for datetime_str, positions in positions_batch:
    self.store_positions(...)
```

After:

```python
rows = [...]
self.conn.executemany("INSERT OR REPLACE ...", rows)
```

## Performance Results

### Before optimization

- 1 day: about 1,200 seconds
- per timestamp: about `0.83s`

### After optimization

- 1 day: about `1.4s`
- per timestamp: about `0.001s`

### Overall speedup

The target improvement is on the order of hundreds of times faster for bulk
series generation.

## Compatibility

The intended design stays backward compatible:

- fall back to `compute_positions()` if direct Swisseph import fails
- fall back to the old path if direct computation fails
- keep single-chart interactive flows on the existing code path

## Related Notes

- [Performance Bottleneck Analysis](performance_bottleneck_analysis)
- [Testing Guide](testing_guide)
