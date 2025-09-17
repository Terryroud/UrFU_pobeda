import threading
import webbrowser
from pathlib import Path

try:
    from flask import Flask, render_template, request, jsonify
except Exception:
    Flask = None
    render_template = None
    request = None
    jsonify = None

if __name__ == "__main__":
    host='127.0.0.1'
    port=5000
    debug=False
    """Запускает веб-интерфейс редактора"""
    if Flask is None:
        print("Flask не установлен. Установите flask, чтобы запустить веб-интерфейс: pip install flask")

    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)

    app = Flask(__name__)
    editor = JSONEditor(web_mode=True)

    @app.route('/')
    def index():
        patterns = editor.get_patterns_data()
        vectors = editor.get_vectors_data()
        
        patterns_text = '\n'.join(patterns.get('INJECTION_PATTERNS', []))
        vectors_json = json.dumps(vectors, ensure_ascii=False, indent=2)
        
        return render_template('editor.html', 
                             patterns_text=patterns_text,
                             vectors_data=vectors_json)

    @app.route('/api/patterns', methods=['POST'])
    def api_patterns():
        try:
            data = request.get_json()
            if editor.update_patterns_web(data):
                return jsonify({'success': True, 'message': 'INJECTION_PATTERNS успешно сохранены!'})
            else:
                return jsonify({'success': False, 'message': 'Ошибка сохранения patterns!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

    @app.route('/api/vectors', methods=['POST'])
    def api_vectors():
        try:
            data = request.get_json()
            if editor.update_vectors_web(data):
                return jsonify({'success': True, 'message': 'Vectors успешно сохранены!'})
            else:
                return jsonify({'success': False, 'message': 'Ошибка сохранения vectors!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

    @app.route('/api/data')
    def api_data():
        return jsonify({
            'patterns': editor.get_patterns_data(),
            'vectors': editor.get_vectors_data()
        })

    print(f"🚀 Запуск веб-интерфейса на http://{host}:{port}")
    print("💡 Нажмите Ctrl+C для остановки сервера")
    
    if debug:
        app.run(host=host, port=port, debug=debug)
    else:
        def run_flask():
            app.run(host=host, port=port, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        webbrowser.open(f"http://{host}:{port}")
        
        try:
            flask_thread.join()
        except KeyboardInterrupt:
            print("\n🛑 Остановка сервера...")
