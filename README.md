# 🎬 AI Video Studio

An AI-powered video studio built with Python. Type a topic, and the studio writes a script, creates scene images, records a voiceover, adds subtitles, generates animated clips and assembles one final video. A **Streamlit** dashboard lets you run and monitor every step from the browser.

## ✨ Features

- **Full pipeline:** topic → script → images → voiceover → subtitles → clips → final video
- **Streamlit dashboard:** 7 pages with a dark theme (Dashboard, Create New Video, Pipeline, My Videos, History, Settings, About)
- **Background jobs:** video generation runs in the background. A page refresh never starts a second job, and you can stop a running job at any time
- **Live progress:** stage status (Pending, Running, Completed, Failed) and a live log
- **Video library:** every finished video is saved with its script, subtitles and thumbnail
- **Generation history:** every run with its time, duration and any error
- **Script review:** edit the title and narration before building the video
- **Command-line scripts:** each step can also be run on its own from the terminal

## 🧰 Tech stack

| Part | Technology |
|---|---|
| Dashboard | Streamlit |
| Script and images | Cloudflare Workers AI (`gpt-oss-20b` for text, `flux-1-schnell` for images) |
| Voiceover | Piper TTS (offline, local model) |
| Subtitles | faster-whisper (Whisper, runs on CPU) |
| Video clips | Wan 2.2 through a Gradio model on Hugging Face |
| Final assembly | FFmpeg |

## 🔄 How the pipeline works

1. **Script:** AI writes the title, scenes, narration and visual prompts.
2. **Images:** one image is created for each scene.
3. **Voiceover:** narration is recorded offline with Piper, with timing for each scene.
4. **Subtitles:** Whisper transcribes the narration into an SRT file.
5. **Video clips:** each image is animated into a short clip with Wan 2.2.
6. **Final video:** FFmpeg joins the clips, narration and subtitles into one MP4.

## 📁 Project structure

```
app.py                  Streamlit entry point (navigation and theme)
core/                   Paths, job control, background runner, history, archive, library
ui/                     One module per dashboard page
assets/                 Dark theme CSS and logo
.streamlit/config.toml  Dark theme settings
generate_script.py      Step 1: script
generate_image.py       Step 2: scene images
generate_voice.py       Step 3: voiceover
generate_subtitles.py   Step 4: subtitles
generate_video.py       Step 5: video clips
assemble_video.py       Step 6: final video
requirements.txt        Python packages
```

## ⚙️ Setup

**Requirements:** Python 3.10 or newer, and FFmpeg (it must be available on your PATH).

1. Clone the repository:
   ```bash
   git clone https://github.com/muhammadyasir-Ai/AI_Video_Studio.git
   cd AI_Video_Studio
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS / Linux
   ```

3. Install the packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Download the Piper voice model `en_US-lessac-medium.onnx` and its `.json` file from the Piper voices project, and place both in the project folder. They are not stored in this repository because of their size.

5. Create a `.env` file in the project folder with your Cloudflare keys:
   ```
   CLOUDFLARE_ACCOUNT_ID=your_account_id
   CLOUDFLARE_API_TOKEN=your_api_token
   ```
   Never commit `.env` to GitHub. It is already listed in `.gitignore`.

## ▶️ How to run

**Streamlit dashboard (recommended):**
```bash
streamlit run app.py
```
Open http://localhost:8501 in your browser. Enter a topic on the **Create New Video** page and click **Generate video**.

**Command line (step by step):**
```bash
python generate_script.py
python generate_image.py
python generate_voice.py
python generate_subtitles.py
python generate_video.py
python assemble_video.py
```
Run them in this order. Each step reads the output of the previous one.

## 🗂️ Outputs

| Folder or file | Contents |
|---|---|
| `projects/project_data.json` | Script with title, scenes and prompts |
| `output/` | Scene images |
| `voiceovers/` | Scene audio and combined narration |
| `subtitles/subtitles.srt` | Subtitles |
| `video/` | Scene clips |
| `final/final_video.mp4` | Latest final video |
| `final/archive/` | Every finished video, with its script, subtitles and thumbnail |

## ⚠️ Notes

- The Wan 2.2 clip step uses a free Hugging Face Space, so it can be slow or hit usage limits. The dashboard shows a clear error if this happens, and you can run the step again later.
- Generated videos, audio and images are not stored in this repository, to keep it small.

## 👤 Author

**Muhammad Yasir**, Computer Science graduate (KUST)
- GitHub: [muhammadyasir-Ai](https://github.com/muhammadyasir-Ai)
- LinkedIn: [muhammad-yasir-17211a423](https://www.linkedin.com/in/muhammad-yasir-17211a423)
- Portfolio: [muhammadyasir-ai.github.io/portfolio](https://muhammadyasir-ai.github.io/portfolio/)
