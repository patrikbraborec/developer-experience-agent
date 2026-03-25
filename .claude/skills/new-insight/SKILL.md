---
name: new-insight
description: Add a new insight to the DX Framework Notion database. Analyzes the insight text and categorizes it into the appropriate DX Framework category.
disable-model-invocation: true
allowed-tools: Bash(python *)
argument-hint: <insight text>
---

# New DX Insight

You are a DX (Developer Experience) expert. The user has provided a new insight that needs to be added to the DX Framework Notion database.

## Your task

1. **Ask about the source/reference** — Before processing, ask the user two things:
   - **Source type**: Where this insight came from (e.g., Slack conversation, customer call, support ticket, internal meeting, GitHub issue, etc.). Use this as the parent description when adding segmented insights (e.g., "Slack conversation about Actor SDK architecture"). If the user already provided the source in their message, skip this question.
   - **Source link**: A URL to the original source (e.g., Slack message link, GitHub issue URL, meeting notes link). Append this link at the end of the parent description in the format: `(source: <URL>)`. If the user doesn't have a link, skip it.
2. **Analyze the insight text** provided in `$ARGUMENTS`
3. **Segment the feedback** if it covers multiple topics. Long messages often contain several distinct points — split them into separate, self-contained insights. Each segment should capture one actionable point.
4. **Determine the best matching category** for each segment from the DX Framework categories below
5. **Group segments by category** — segments going to the same category page are added together as sub-bullets under one parent bullet
6. **Run the script once per category** to add the insight(s) to the correct Notion page

## DX Framework Categories

Choose the single best matching category:

| Category | Definition |
|---|---|
| 2 mins to call API | Takes less than 2 mins from sign-up to first API call |
| API Key Access | It should be super easy for users to get API key |
| Platform Documentation | Documentation describing the platform |
| Tutorials, samples, guides, quickstarts | Step-by-step guides, conceptual overviews, or walkthroughs |
| Crawlee docs | Crawlee documentation |
| API Docs | API Documentation |
| API | Apify API |
| API Clients Docs | Documentation describing on how to use API Clients (JavaScript, Python) |
| API Clients | JavaScript and Python API clients |
| SDKs Docs | JavaScript and Python SDKs documentation |
| SDKs | JavaScript and Python SDKs |
| CLI Docs | CLI Documentation |
| CLI | CLI for interacting with Actors (locally and cloud) |
| Development Onboarding | Provides clear onboarding |
| Console Monitoring | Monitoring to monitor errors, traffic, and logs |
| Error Experience | Quality of error messages, stack traces, and debugging information |
| Local Development Experience | Ability to develop, test, and debug Actors locally before deployment |
| AI Development Experience | Tools, frameworks, and capabilities for building AI-powered Actors |
| CI/CD Integration | CI/CD pipelines and automation for building and deploying Actors |
| Community & Support | Community resources, support channels, and developer engagement |
| Integration Ecosystem | Third-party integrations and ecosystem connectivity |
| My Actors | Managing and organizing user's own Actors |
| Other | Insights that don't fit neatly into other categories |

## How to add the insight

### Single insight (short, single-topic feedback)

When the feedback is short and covers only one topic, add it as a simple bullet:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/add_insight.py --category "<exact category name>" --insight "<insight text>"
```

### Segmented insight (long, multi-topic feedback)

When the feedback is long and has been segmented, group segments by category. For each category, create a parent bullet with a description and nested sub-bullets for each segment:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/add_insight.py --category "<exact category name>" --insight "<parent description of the feedback source>" --segments "<segment 1 text>" "<segment 2 text>" "<segment 3 text>"
```

The script automatically uses `@Today` (Notion date mention) and appends as the last item in the Insights section. This produces the following Notion structure:
```
• @Today Feedback from DX workshop at the product offsite (source: https://slack.com/archives/...):
    ◦ The UX of the Web IDE is not good...
    ◦ The Web IDE should behave like an actual IDE...
    ◦ Idea: Use log messages in the form of Step [i]/[n]...
```

If segments span **multiple categories**, run the script once per category — each call groups only the segments belonging to that category.

**Important:**
- Use the **exact category name** from the table above (case-sensitive)
- For each segment, pick the most specific matching category
- Always confirm the segmentation and category choices with the user before running the scripts
- After running all scripts, report a summary of all insights added and their categories

## Segmentation guidelines

- **Split by topic:** If the feedback mentions documentation issues AND API problems, those are two separate insights
- **Split by actionable point:** Each segment should be a single, actionable piece of feedback
- **Preserve context:** When splitting, ensure each segment is self-contained and understandable on its own — add brief context if needed
- **Don't over-split:** Short, single-topic messages should remain as one insight
- **Present the breakdown:** Show the user how you segmented the text before adding, formatted as:

```
Category: <category name>
  → "<parent description>"
    • "<segment 1 text>"
    • "<segment 2 text>"

Category: <category name>
  → "<parent description>"
    • "<segment 3 text>"
```
