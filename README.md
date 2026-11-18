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
