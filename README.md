# AI Video Studio

An AI-powered video studio built with Python. It generates a script, creates images and voiceovers, produces subtitles, generates video clips, and assembles them into a final video.

## Pipeline

1. `generate_script.py`: writes the video script with an AI text model.
2. `generate_image.py`: creates scene images.
3. `generate_voice.py`: creates voiceover audio with Piper TTS.
4. `generate_subtitles.py`: transcribes audio into subtitles with Whisper.
5. `generate_video.py`: generates video clips through a Gradio model.
6. `assemble_video.py`: joins clips, audio and subtitles with FFmpeg.

## Setup

1. Install Python 3.10 or newer, and FFmpeg (it must be available on PATH).
2. Create a virtual environment and install the packages:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Download the Piper voice model `en_US-lessac-medium.onnx` and its `.json` file from the Piper voices repository, and place both in the project folder. They are not stored in this repository because of their size.
4. Create a `.env` file in the project folder with your keys:
   ```
   CLOUDFLARE_ACCOUNT_ID=your_account_id
   CLOUDFLARE_API_TOKEN=your_api_token
   ```
   Never commit `.env` to GitHub.

## Run

Run the scripts in pipeline order, starting with `generate_script.py`.

## Streamlit GUI (AI Video Studio)

The GUI runs the same pipeline scripts as the command line. The original scripts
(`generate_script.py`, `generate_image.py`, `generate_voice.py`, `generate_subtitles.py`,
`generate_video.py`, `assemble_video.py`) are not changed.

### Run the GUI

```
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Pages

- **Dashboard:** totals, recent generations, 7-day activity, pipeline health and storage.
- **Create New Video:** enter a topic and generate a video, continue an existing script, or review and edit the script.
- **Video Generation Pipeline:** live stage status, log, stop button and run-one-stage buttons.
- **My Videos:** finished videos with search, sort, preview and download, plus script and subtitles.
- **Generation History:** every run started from the GUI, with errors and output files.
- **Settings:** credential presence check (values are never shown), read-only model list and maintenance actions.
- **About:** what the studio does and how the pipeline works.

### How it works

- Jobs run in a background process (`core/runner.py`). A page refresh does not start a second job, and only one job runs at a time.
- Progress is stored in `projects/job_status.json`. Output goes to `projects/job_log.txt`.
- History is stored in `projects/history.json`. It only contains runs started from the GUI.
- Each finished video is copied to `final/archive/` with its script, subtitles and thumbnail, so a new run does not overwrite it.

### Project structure

```
app.py              entry point, navigation and theme
core/               config, file checks, background job control, runner, history, archive, library
ui/                 one module per page, plus shared helpers
assets/             style.css (dark theme) and logo.svg
.streamlit/config.toml   dark theme settings
```

### Notes

- `.env` holds your API keys. Keep it out of Git (it is already in `.gitignore`).
- Test the full run on your own PC. The Cloudflare, Piper, Whisper, Wan 2.2 and FFmpeg steps need your local setup.
