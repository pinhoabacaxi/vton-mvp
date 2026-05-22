# Hugging Face Space build fix for IDM-VTON

The Space build log that starts from `python:3.13` fails while installing
`numpy==1.24.4`. That numpy pin is too old for Python 3.13, so pip tries to
build it from source and fails during the build backend setup.

Apply this fix in the duplicated Hugging Face Space repository, not in the
Render backend repository.

## README.md front matter

Set an explicit Python version in the YAML block at the top of the Space
`README.md`:

```yaml
---
title: IDM VTON
sdk: gradio
sdk_version: 4.24.0
python_version: 3.10
app_file: app.py
suggested_hardware: t4-small
---
```

Hugging Face Spaces reads this YAML block from the root `README.md`.
The `python_version` field accepts a valid Python `3.x` or `3.x.x` version.

## requirements.txt guidance

Keep the old IDM-VTON numerical stack on Python 3.10:

```txt
torch==2.8.0
torchvision==0.23.0
torchaudio==2.8.0
numpy==1.24.4
```

If the Space must stay on Python 3.13, then `numpy==1.24.4` has to be removed
or upgraded, but that is riskier for IDM-VTON because older computer-vision
code often assumes the Python 3.10 era dependency set.

## Backend behavior

The FastAPI backend treats build/runtime failures from the Space as a provider
failure. In `mode=auto`, the app still follows:

1. Replicate or external provider.
2. Hugging Face Space.
3. Local 2.5D mock fallback.

This prevents the user from seeing build logs, stack traces or raw Space errors.
