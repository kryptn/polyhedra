import sys
from datetime import datetime

from flask import Flask, render_template
from flask_frozen import Freezer


app = Flask(__name__)
freezer = Freezer(app)
app.config['FREEZER_DESTINATION'] = 'out/build'
app.config['FREEZER_RELATIVE_URLS'] = True



@app.route('/')
def index():
    shorthand = datetime.now().strftime("%Y-%d-%m")
    longhand = datetime.now().strftime("%B %d, %Y")
    return render_template('index.html', shorthand=shorthand, longhand=longhand)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'build':
        freezer.freeze()
    else:
        app.run(debug=True, host='0.0.0.0')

