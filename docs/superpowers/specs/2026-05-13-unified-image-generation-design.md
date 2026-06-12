# Unified Image Generation Design

## Goal

Merge the current "图像生成" and "GPT 画图" experiences into one user-facing entry named "图像生成". The page uses one prompt input and one generate action, while the selected image model decides which generation backend runs.

## Navigation

- Remove the separate "GPT 画图" sidebar entry.
- Keep "图像生成", "生图工作台", "PaperBanana", and "设置" as separate features.
- Keep "API 设置" admin-only.

## Unified Image Page

The unified page keeps one primary prompt editor and one submit button. The image model selector includes:

- `nano-banana-pro`: routes to the existing general image generation path.
- `GPT Image`: routes to the existing GPT Image path.

Model-specific controls are shown only when relevant:

- `nano-banana-pro`: quality and reference images for the existing grsai path.
- `GPT Image`: GPT size, quality, format, count, import/export, and reference image controls.

PaperBanana remains independent because it has a multi-stage professional workflow and different progress UI.

## Home Page History

The home page becomes an operational drawing dashboard:

- Main section: "最近画图" history grid with thumbnails when available.
- Each history card shows prompt summary, model/source, status, and time.
- Failed or running records still render as state cards instead of disappearing.
- Secondary section keeps recommended prompt templates and recent text activity.

## History Storage

Use a frontend unified history layer first:

- Read existing GPT Image tasks from `gpt_image_tasks_v1`.
- Store unified records in `matchdrawer_image_history_v1`.
- Write completed or failed general image generations into the unified history.
- Refresh the dashboard history after any new record.

This avoids adding a database migration during the UI merge. A backend multi-user history table can be added later if cross-device persistence or admin auditing becomes required.

## Error Handling

- If no global API key exists, reuse the existing admin/non-admin messages.
- If a selected model fails, save a failed history record with the prompt and model label.
- If old GPT tasks cannot be parsed, ignore them without breaking the page.

## Verification

- Static-check edited JavaScript.
- Run the existing auth/assets/API unit tests.
- Verify the local app renders with one "图像生成" nav entry, no "GPT 画图" nav entry, and visible home history placeholders/cards.
