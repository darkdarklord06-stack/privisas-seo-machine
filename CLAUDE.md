# CLAUDE.md
# PRIVISAS SEO AGENT — PRIMARY OPERATING RULES

These rules override the generic SEO Machine workflow whenever working on privisas.com.

## Website

Domain: https://privisas.com
Brand: Privisas
Primary language: Turkish
CMS: Framer
Market: Visa consultancy and visa information for users in Türkiye.

## Primary Objective

Continuously improve organic search performance using real Google Search Console data.

Do NOT optimize pages merely to create more content.

The operating loop is:

MEASURE
→ REVIEW PREVIOUS EXPERIMENTS
→ SELECT ONE KEYWORD
→ ANALYZE SEARCH INTENT
→ ANALYZE SERP AND CONTENT GAP
→ MAKE ONE JUSTIFIED IMPROVEMENT
→ RECORD THE CHANGE
→ WAIT 7 DAYS
→ MEASURE AGAIN

Never claim an SEO improvement worked until it is confirmed by later Search Console data.

## Source of Truth

Google Search Console is the primary source for:

- queries
- target pages
- impressions
- clicks
- CTR
- average position

Web search may be used for current SERP and competitor research.

Web search ranking observations are approximate and must not override GSC performance data.

## Keyword Selection

Only ONE keyword/query may be actively optimized per run.

Exclude keywords with status:

- observing
- achieved

Priority order:

1. Position 2–10 with impressions
2. Position 11–20 with strong impressions
3. Previously tested keyword that returned to active
4. High-priority keyword with no usable GSC rank
5. Promising new GSC query not yet tracked

Do not invent an optimization target when no meaningful opportunity exists.

## Search Intent First

Before changing any page, explicitly determine:

"Who is searching this query, and exactly what are they trying to learn or accomplish?"

Then inspect the current leading organic results.

Compare them with the Privisas target page.

Identify the useful information that the searcher can find elsewhere but cannot clearly find on Privisas.

That difference is the content gap.

Do NOT increase word count merely for SEO.

## Improvement Rules

Apply the smallest useful change that addresses the identified gap.

Possible changes include:

- title
- meta description
- introduction
- missing factual section
- FAQ
- application steps
- tables
- internal links
- clearer explanation
- updated official information
- structured data where appropriate

Do not change everything at once.

Every optimization must have a clear hypothesis.

## Internal Links

Internal links must help the user take the next logical step.

Do not add links merely to manipulate rankings.

## Visa Information Safety

Visa requirements can change.

For factual claims involving:

- required documents
- visa fees
- application centers
- appointment procedures
- processing times
- photograph requirements
- government rules
- entry requirements

prefer current official sources such as:

- embassy or consulate websites
- official government websites
- EU sources
- VFS Global
- TLScontact
- BLS
- iDATA
- Kosmos
- UKVI
- travel.state.gov
- Canada.ca

Do not treat another visa consultancy website as authoritative evidence for a changing visa requirement.

## Claims

Privisas does not decide visa applications.

Avoid unsupported absolute claims such as:

- guaranteed visa
- guaranteed approval
- eliminates rejection risk
- certain approval

Use accurate language describing assistance, preparation and risk reduction.

## Protected Changes

Do NOT automatically perform any of the following:

- add or remove noindex
- change canonical strategy
- change URLs
- create redirects
- delete pages
- merge pages
- substantially change site architecture
- mass-create landing pages
- make large template changes
- make risky robots.txt changes

These require explicit human approval.

## Experiment Cooldown

After an optimization, the keyword enters:

status: observing

Set:

nextReviewDate = action date + 7 days

Do NOT optimize that keyword again before nextReviewDate.

This rule is strict.

## Evaluation

After the observation period, compare real GSC performance.

Review:

- average position
- impressions
- clicks
- CTR

Possible outcomes:

achieved
improved_but_not_achieved
no_effect
negative

If position reaches approximately #1 with meaningful impressions:

status = achieved

Otherwise return the keyword to active when appropriate.

If an experiment has no effect, do not blindly repeat the same optimization technique.

Develop a different hypothesis.

## SEO Experiment Data

Maintain:

data/seo/watchwords.json
data/seo/rank-history.json
data/seo/improvement-log.json

rank-history.json is APPEND ONLY.

Never rewrite historical ranking measurements.

## First Known Opportunity

Initial manually observed GSC opportunity:

Keyword:
schengen vizesi için tur rezervasyonu yeterli mi

Target:
https://privisas.com/blog/schengen-vizesi-konaklama-kaniti-basvurunuzun-reddedilmemesi-icin-bilmeniz-gerekenler

Observed average position:
6.9

Observed impressions:
8

Observed clicks:
0

This is seed information only.

Re-measure with GSC before performing an automated optimization.

Do not assume the historical position remains current.

## Framer Publishing

Privisas uses Framer.

Do NOT use the repository's WordPress publishing workflow for Privisas.

Framer publishing will be handled through a dedicated integration.

Until that integration is configured and verified:

DO NOT automatically publish changes to the live Privisas website.

## Secrets

Never print, expose or commit:

- Google credentials
- OAuth secrets
- API keys
- Framer API keys
- DataForSEO credentials
- tokens
- private keys

Secrets must remain outside version-controlled files.

## Final Report

At the end of each SEO Rank Watch run report:

- measurement period
- major ranking increases
- major ranking decreases
- experiments reviewed today
- evaluation result
- selected keyword
- target page
- reason for selection
- search intent
- identified content gap
- optimization hypothesis
- actual change made
- keywords currently observing
- nextReviewDate
- changes requiring human approval

Always state:

"The ranking impact of today's change is not yet known. It will be evaluated using subsequent Google Search Console measurements."

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEO Machine is an open-source Claude Code workspace for creating SEO-optimized blog content. It combines custom commands, specialized agents, and Python-based analytics to research, write, optimize, and publish articles for any business.

## Setup

```bash
pip install -r data_sources/requirements.txt
```

API credentials are configured in `data_sources/config/.env` (GA4, GSC, DataForSEO, WordPress). GA4 service account credentials go in `credentials/ga4-credentials.json`.

## Commands

All commands are defined in `.claude/commands/` and invoked as slash commands:

- `/research [topic]` - Keyword/competitor research, generates brief in `research/`
- `/write [topic]` - Create full article in `drafts/`, auto-triggers optimization agents
- `/rewrite [topic]` - Update existing content, saves to `rewrites/`
- `/optimize [file]` - Final SEO polish pass
- `/analyze-existing [URL or file]` - Content health audit
- `/performance-review` - Analytics-driven content priorities
- `/publish-draft [file]` - Publish to WordPress via REST API
- `/article [topic]` - Simplified article creation
- `/cluster [topic]` - Build complete topic cluster strategy with pillar + supporting articles + linking map
- `/priorities` - Content prioritization matrix
- `/research-serp`, `/research-gaps`, `/research-trending`, `/research-performance`, `/research-topics` - Specialized research commands
- `/research-ai-citations [topic]` - AI citation audit: generates prompts, clusters them, audits which sources AI cites
- `/repurpose [file]` - Adapts article for LinkedIn, Medium, Reddit, Quora distribution
- `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor` - Landing page commands

## Architecture

### Command-Agent Model

**Commands** (`.claude/commands/`) orchestrate workflows. **Agents** (`.claude/agents/`) are specialized roles invoked by commands. After `/write`, these agents auto-run: SEO Optimizer, Meta Creator, Internal Linker, Keyword Mapper.

Key agents: `content-analyzer.md`, `seo-optimizer.md`, `meta-creator.md`, `internal-linker.md`, `keyword-mapper.md`, `editor.md`, `headline-generator.md`, `cro-analyst.md`, `performance.md`, `cluster-strategist.md`.

### Python Analysis Pipeline

Located in `data_sources/modules/`. The Content Analyzer chains:
1. `search_intent_analyzer.py` - Query intent classification
2. `keyword_analyzer.py` - Density, distribution, stuffing detection
3. `content_length_comparator.py` - Benchmarks against top 10 SERP results
4. `readability_scorer.py` - Flesch Reading Ease, grade level
5. `seo_quality_rater.py` - Comprehensive 0-100 SEO score

### Data Integrations

- `google_analytics.py` - GA4 traffic/engagement data
- `google_search_console.py` - Rankings and impressions
- `dataforseo.py` - SERP positions, keyword metrics
- `data_aggregator.py` - Combines all sources into unified analytics
- `wordpress_publisher.py` - Publishes to WordPress with Yoast SEO metadata

### Opportunity Scoring

`opportunity_scorer.py` uses 8 weighted factors: Volume (25%), Position (20%), Intent (20%), Competition (15%), Cluster (10%), CTR (5%), Freshness (5%), Trend (5%).

## Running Python Scripts

```bash
# Research & analysis scripts (run from repo root)
python3 research_quick_wins.py
python3 research_competitor_gaps.py
python3 research_performance_matrix.py
python3 research_priorities_comprehensive.py
python3 research_serp_analysis.py
python3 research_topic_clusters.py
python3 research_trending.py
python3 seo_baseline_analysis.py
python3 seo_bofu_rankings.py
python3 seo_competitor_analysis.py

# Test API connectivity
python3 test_dataforseo.py
```

## Content Pipeline

`topics/` (ideas) → `research/` (briefs) → `drafts/` (articles) → `review-required/` (pending review) → `published/` (final)

Rewrites go to `rewrites/`. Landing pages go to `landing-pages/`. Audits go to `audits/`. Repurposed content goes to `repurposed/`.

## Context Files

`context/` contains brand guidelines that inform all content generation:
- `brand-voice.md` - Tone, messaging pillars
- `style-guide.md` - Grammar, formatting standards
- `seo-guidelines.md` - Keyword and structure rules
- `internal-links-map.md` - Key pages for internal linking
- `features.md` - Product features
- `competitor-analysis.md` - Competitive intelligence
- `cro-best-practices.md` - Conversion optimization guidelines
- `ai-citation-targets.md` - Directories/platforms where your brand should be cited by AI tools
- `reddit-strategy.md` - Reddit engagement strategy for AI SEO and community visibility

## WordPress Integration

Publishing uses the WordPress REST API with a custom MU-plugin (`wordpress/seo-machine-yoast-rest.php`) that exposes Yoast SEO fields. Articles are published in WordPress block format (HTML comments in Markdown files).
