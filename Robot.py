from flask import Flask, request, send_file
import tempfile
import asyncio
import edge_tts
import pdfplumber
from docx import Document
import os

app = Flask(__name__)

# Функция, которая озвучивает текст с выбранным голосом
async def text_to_speech_with_voice(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

# Достаём текст из PDF
def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + " "
        return text

# Достаём текст из Word
def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text += paragraph.text + " "
    return text

# Главная страница — красивая!
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 Робот-Читатель</title>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: 'Arial', sans-serif;
                background: linear-gradient(135deg, #6e8efb, #a777e3);
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                text-align: center;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
                max-width: 500px;
            }
            h1 {
                margin: 0 0 20px;
                font-size: 2.5em;
            }
            input[type="file"] {
                margin: 20px 0;
                padding: 10px;
                width: 100%;
                border-radius: 10px;
                border: none;
                background: rgba(255,255,255,0.2);
                color: white;
            }
            button {
                background: #ff6b6b;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 18px;
                border-radius: 50px;
                cursor: pointer;
                transition: all 0.3s;
                margin: 10px;
                font-weight: bold;
            }
            button:hover {
                background: #ff5252;
                transform: scale(1.05);
            }
            select {
                padding: 10px;
                border-radius: 10px;
                border: none;
                background: rgba(255,255,255,0.2);
                color: white;
                margin: 10px 0;
                width: 100%;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Робот-Читатель</h1>
            <p>Загрузи PDF или Word — я прочитаю его вслух!</p>
            
            <form method="POST" action="/upload" enctype="multipart/form-data">
                <input type="file" name="file" accept=".pdf,.docx" required>
                
                <br>
                <label>🗣 Выбери голос:</label><br>
                <select name="voice">
                    <option value="ru-RU-DmitryNeural">Дмитрий (мужской)</option>
                    <option value="ru-RU-SvetlanaNeural">Светлана (женский)</option>
                    <option value="ru-RU-DariyaNeural">Дарья (женский, мягкий)</option>
                </select>
                
                <br><br>
                <button type="submit" name="action" value="play">▶️ Слушать онлайн</button>
                <button type="submit" name="action" value="download">💾 Скачать MP3</button>
            </form>
        </div>
    </body>
    </html>
    '''

# Обработка загрузки файла
@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if not file:
        return "Файл не выбран!"

    # Получаем выбор голоса и действия
    voice = request.form.get('voice', 'ru-RU-DmitryNeural')
    action = request.form.get('action', 'play')  # play или download

    # Сохраняем временно
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    # Читаем текст
    if file.filename.endswith('.pdf'):
        text = extract_text_from_pdf(tmp_path)
    elif file.filename.endswith('.docx'):
        text = extract_text_from_docx(tmp_path)
    else:
        return "Я умею читать только PDF и Word 😅"

    # Очищаем текст
    text = " ".join(text.split())
    if len(text) < 5:
        return "Файл пустой или текст не распознан 😢"

    # Генерируем аудио
    audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    asyncio.run(text_to_speech_with_voice(text, voice, audio_file))

    if action == 'play':
        # Отправляем страницу с плеером
        audio_filename = os.path.basename(audio_file)
        return f'''
        <!DOCTYPE html>
        <html>
        <head><title>Слушай! 🎧</title></head>
        <body style="text-align:center; padding:50px; background:linear-gradient(135deg, #74ebd5, #ACB6E5);">
            <h2>🔊 Слушай прямо здесь!</h2>
            <audio controls autoplay style="width:80%; max-width:500px; margin:20px;">
                <source src="/audio/{audio_filename}" type="audio/mpeg">
                Твой браузер не поддерживает аудио.
            </audio>
            <br>
            <a href="/audio/{audio_filename}" download="речь_робота.mp3">
                <button style="padding:10px 20px; background:#4CAF50; color:white; border:none; border-radius:5px; cursor:pointer;">
                    💾 Скачать файл
                </button>
            </a>
            <br><br>
            <a href="/" style="color:#333; text-decoration:none;">⬅️ Вернуться назад</a>
        </body>
        </html>
        '''
    else:
        # Скачивание
        return send_file(audio_file, as_attachment=True, download_name="речь_робота.mp3")

# Отдаём аудиофайл для проигрывания в браузере
@app.route('/audio/<filename>')
def serve_audio(filename):
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='audio/mpeg')
    else:
        return "Аудиофайл не найден", 404

# Запуск сервера
if __name__ == '__main__':
    print("🚀 Робот запущен! Открой в браузере: http://127.0.0.1:5000")
    app.run(debug=True)