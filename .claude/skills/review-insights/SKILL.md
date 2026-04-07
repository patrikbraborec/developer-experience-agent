---
name: review-insights
description: Review recent DX insights across all categories, analyze trends (improving/stable/declining), and update the "Latest signal" section on each category page in Notion.
disable-model-invocation: true
allowed-tools: Bash(python *)
argument-hint: [optional: specific category name to review]
---

# Review DX Insights

You are a DX (Developer Experience) expert and product analyst. Your job is to review recent insights across DX Framework categories, analyze trends, and update the "Latest signal" section on relevant category pages.

## Your task

### Step 1: Fetch recent insights

Run the fetch script to get all recent insights (default: last 14 days):

```bash
python ${CLAUDE_SKILL_DIR}/scripts/fetch_insights.py --days 14
```

If the user specified a specific category in `$ARGUMENTS`, still fetch all data but focus your analysis on that category.

### Step 2: Analyze the data

For each category that has recent insights, analyze:

1. **Volume**: How many insights were added in the period?
2. **Sentiment**: Are the insights mostly positive (improvements, praise), negative (complaints, bugs, friction), or mixed?
3. **Trend**: Based on the insights content and any existing signal, determine the trend:
   - **Improving** — Recent insights indicate progress, fixes, or positive changes
   - **Stable** — No significant change; insights are consistent with prior state
   - **Needs attention** — Recent insights indicate new problems, regressions, or growing friction

4. **Current score context**: Check the `properties` field in the fetched data for any score/status properties (e.g., "Score", "Status", "Rating"). Use these to inform your trend assessment and the "Change" line.

### Step 3: Present your analysis

Present a summary table to the user:

```
| Category | Recent insights | Trend | Suggested signal |
|----------|----------------|-------|------------------|
| API Docs | 5 | Improving | From "Requires attention" to "Meets expectations" |
| CLI      | 2 | Stable   | Stays at "Meets expectations" |
| SDKs     | 3 | Needs attention | From "Meets expectations" to "Requires attention" |
```

For each category with insights, also show:
- A brief summary of what the insights say
- Your reasoning for the trend assessment
- The proposed "Latest signal" text

### Step 4: Update Notion (after user approval)

**Always confirm with the user before updating.** Once approved, run the update script for each category:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/update_signal.py \
  --category "<exact category name>" \
  --summary "<summary sentence about what changed>" \
  --change "<from/to or status description>" \
  --signal-date "<date reference>"
```

**Example:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/update_signal.py \
  --category "Platform Documentation" \
  --summary "During Q1/2026, we improved the structure of the documentation." \
  --change "From \"Requires attention\" to \"Meets expectations\"" \
  --signal-date "Last Thursday"
```

This produces the following structure on the Notion page under a "Latest signal" heading:

```
## Latest signal

During Q1/2026, we improved the structure of the documentation.

Change: From "Requires attention" to "Meets expectations".

Date: Last Thursday
```

If a "Latest signal" section already exists, the script replaces its content. If it doesn't exist, it creates one.

## Signal writing guidelines

- **Summary line**: Write in past tense, referencing the time period (e.g., "During Q1/2026", "Over the past two weeks"). Describe the key change or observation.
- **Change line**: Use the format `From "<previous state>" to "<new state>"`. Use descriptive states like:
  - "Exceeds expectations"
  - "Meets expectations"
  - "Requires attention"
  - "Critical"
  - If no change: `Stays at "<current state>"`
- **Date line**: Use a human-readable date reference (e.g., "Last Thursday", "March 20, 2026", "Week of March 16"). Prefer relative references when recent.

## Important

- Use the **exact category name** from the DX Framework (case-sensitive)
- Only update categories that have recent insights — skip categories with no activity
- If a category has very few insights (1-2) and they're ambiguous, mark the trend as "Stable" rather than guessing
- Always show your analysis and get user confirmation before writing to Notion
- After updating, report a summary of all changes made
