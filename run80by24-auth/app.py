from run80by24.auth.website.app import create_app
import os

print(os.getcwd())
instance_path = os.path.abspath('instance')
app = create_app(instance_path)

@app.cli.command()
def initdb():
    from run80by24.auth.website.models import db
    db.create_all()

# for running in PyCharm debugger
if __name__=='__main__':
    os.environ['AUTHLIB_INSECURE_TRANSPORT']='1'
    app.run(debug=True, use_debugger=False, use_reloader=False, port=app.config['PORT'])