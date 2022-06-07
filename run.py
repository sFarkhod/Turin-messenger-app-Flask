from distutils.log import debug
from elturino import socketio
from elturino import app

if __name__ == '__main__':
    socketio.run(app, debug=True)