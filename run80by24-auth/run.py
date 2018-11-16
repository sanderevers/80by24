from run80by24.auth.app import create_app
import os

def debug():
    os.environ['AUTHLIB_INSECURE_TRANSPORT']='1'
    os.environ['FLASK_ENV'] = 'development'
    app.run(debug=True, use_debugger=False, use_reloader=False, port=app.config['PORT'])

# for running in PyCharm debugger
if __name__=='__main__':
    instance_path = os.path.abspath('instance')
    os.environ['INSTANCE_PATH'] = instance_path

app = create_app()

if __name__=='__main__':
    debug()

@app.cli.command()
def initdb():
    from run80by24.auth.models import db
    db.create_all()
