# ORIS Skill Adoption Plan (2026-04-09)

## Goal
Use external OpenClaw/GitHub skills only to improve ORIS efficiency and delivery quality, without outsourcing ORIS core judgment.

## Adopt Now
1. agent-browser
   - Role: dynamic page / JS page / download page fallback
   - Position: official_source_ingest fallback layer

2. chain-of-density
   - Role: executive summary compression / PPT page-top conclusion compression
   - Position: synthesis compression helper

3. shelv
   - Role: PDF-heavy company deep parse sidecar
   - Position: optional PDF enhancement path, not default mainline

4. pdf-generation
   - Role: premium PDF export from HTML/CSS
   - Position: premium delivery sidecar

## Keep In-House
- company focus profile detection
- evidence scoring
- metric extraction / normalization
- risk decomposition
- tracking KPI system
- consulting-style PPT storyline and slide logic

## Architecture
A. acquisition
searxng -> official_source_ingest -> native_http -> agent-browser fallback -> pdf extract -> optional shelv

B. synthesis
focus_profile -> evidence scoring -> metric normalization -> chain-of-density compression

C. delivery
chat_md first -> docx/xlsx/pptx default -> optional premium pdf

## Constraints
- project-level install only
- no unaudited skill enters production mainline
- any API-based skill must remain optional sidecar
