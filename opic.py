import base64
import streamlit as st
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
from dotenv import load_dotenv
load_dotenv()

st.title("영어 테스트")

con1 = st.container()
con2 = st.container()


with con2:
    audio_bytes = audio_recorder("녹음", pause_threshold=3.0)


    if audio_bytes:
        with open("./tmp_audio.wav", "wb") as f:
            f.write(audio_bytes)
