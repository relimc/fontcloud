from flask import Flask
from web.routes import register_routes
import config

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__,
            template_folder='web/templates',
            static_folder='web/static')
app.config.from_object(config)

app.secret_key = config.SECRET_KEY

# 注册所有路由
register_routes(app)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)