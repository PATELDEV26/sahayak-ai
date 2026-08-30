import os
import google.generativeai as genai

genai.configure(api_key='AIzaSyCNaUjizaxOwqh6hJHl4oCe2brLMXaeV8c')
try:
    for m in genai.list_models():
        print(m.name)
except Exception as e:
    print("Error:", e)
