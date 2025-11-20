from app import create_app

app = create_app()

# Gunicorn은 기본적으로 모듈:변수 형태 (wsgi:app)로 이 객체를 로드합니다.