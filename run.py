from app.main import create_app
import os

if __name__ == '__main__':
    app = create_app()
    
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 btppg-driver alkalmazás indítása...")
    print(f"📍 URL: http://{host}:{port}")
    print(f"🐛 Debug mód: {debug}")
    
    app.run(host=host, port=port, debug=debug)
