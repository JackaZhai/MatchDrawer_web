# MatchDrawer Rebrand Design

Date: 2026-04-13
Status: Approved for planning

## Summary

This change repositions the product from a paper-figure-focused tool into a broader drawing platform. The external brand becomes `MatchDrawer`, while `PaperBanana` remains a clearly visible, fully functional professional workflow inside the product.

The goal is to change how the product is presented without destabilizing the existing `PaperBanana` generation pipeline.

## Product Goals

- Rename the product from `SCIdrawer` to `MatchDrawer` across the repository, deployment assets, and user-facing surfaces.
- Expand product positioning so it is not limited to scientific paper figures.
- Preserve the complete `PaperBanana` workflow and keep it directly visible to users.
- Keep implementation risk low by avoiding unnecessary refactors of stable backend workflow internals.

## Non-Goals

- Replacing or renaming the `PaperBanana` workflow itself.
- Redesigning the entire application layout or navigation from scratch.
- Changing database schema, authentication flow, or generation pipeline semantics.
- Refactoring stable backend internals just to align naming.

## Core Decisions

### Branding

- External brand name: `MatchDrawer`
- Internal professional workflow name: `PaperBanana`
- Product relationship: `MatchDrawer` is the platform brand; `PaperBanana` is a distinct workflow exposed inside the platform.

### Positioning

`MatchDrawer` should be described as a general drawing tool for creating:

- paper figures
- flowcharts
- architecture diagrams
- mechanism diagrams
- comparison figures
- product or business illustrations
- other structured visual assets

The platform should no longer read as paper-only, but scientific and academic use cases should still remain visible.

### Workflow Exposure

`PaperBanana` remains directly visible in the interface. It should be described as an advanced or professional workflow rather than hidden behind generic generation controls.

Its parameters, retrieval options, critic loop, eval options, and stage display should remain intact.

## Scope

### Rename Scope

The following should be renamed from `SCIdrawer` to `MatchDrawer` where they represent the product brand:

- repository and directory naming references
- README title and setup instructions
- HTML page titles
- visible brand text in templates
- login and manual pages
- comments and logs that name the product
- deployment file names and descriptions
- deployment path examples and service descriptions

### Content and UX Scope

The following user-facing content should be updated:

- homepage/dashboard descriptions
- login page subtitle and branding text
- manual/help wording
- placeholder prompts and recommended templates
- settings/help explanations for workflow modes

Content should shift from paper-only language to general drawing language while still preserving some academic examples.

### Deployment Scope

Deployment assets should be updated so the branding is consistent:

- `systemd` unit name and description
- `nginx` config name and any path examples
- README links and references to deployment assets
- helper scripts or docs that reference old product naming

If a deployment-facing rename would break an existing stable runtime path, documentation and config must be updated together so there is no mismatch.

## Internal Naming Policy

Keep existing `PaperBanana` implementation names when they are part of the workflow integration or API contract, including examples such as:

- integration directory names
- service classes
- route names
- workflow stage names
- task status payload structure

These names should only change if required by a concrete functional issue, not for cosmetic consistency.

## Interface Direction

The application should present itself as a general drawing platform with a clearly visible professional workflow:

- `MatchDrawer` is the product users enter.
- General drawing use cases are shown first in descriptions and examples.
- `PaperBanana` remains explicitly labeled and available as a standalone workflow option.
- A short explanation should clarify that `PaperBanana` is suited for more complex multi-stage generation tasks.

## Example Content Direction

Recommended examples should become more general-purpose while keeping some scientific coverage. The example set should include a mix such as:

- user permission flowchart
- system architecture diagram
- operation funnel or product process figure
- course or concept map
- scientific mechanism diagram

This keeps the new positioning credible without discarding existing users.

## Compatibility Strategy

- Prefer changing user-visible branding first.
- Preserve stable internal workflow identifiers when renaming would create avoidable risk.
- Avoid changes to database models, auth, or workflow contracts unless directly required.
- Keep `PaperBanana` fully operational and visible after the rebrand.

## Validation Requirements

Before considering implementation complete, verify:

- the app loads successfully
- visible brand text shows `MatchDrawer`
- `PaperBanana` is still directly visible in the UI
- generation entry points still work
- deployment references do not point to old renamed files
- documentation does not contradict the new product positioning

## Expected Outcome

After this change, the project should read as a broader visual creation product named `MatchDrawer`, while retaining the full specialized `PaperBanana` workflow as a visible and operational capability.
