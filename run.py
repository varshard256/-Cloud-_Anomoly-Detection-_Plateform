import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db

app = create_app(os.environ.get("FLASK_ENV", "development"))


@app.shell_context_processor
def make_shell_context():
    from app.models import User, CloudServer, CloudMetric, Anomaly, Alert
    return {"db": db, "User": User, "CloudServer": CloudServer,
            "CloudMetric": CloudMetric, "Anomaly": Anomaly, "Alert": Alert}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
