"""
the main file for our server. contains nearly everything.
"""

import json
from flask import Flask, jsonify, make_response, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate

import datetime

import os
import sys
import click
import shutil

app = Flask(__name__)
WIN = sys.platform.startswith('win')
prefix = 'sqlite:///' if WIN else 'sqlite:////'
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db') # where our database locate


CORS(app) # enable vue access flask.

db = SQLAlchemy(app) # init database
migrate = Migrate(app, db) # migrate: help us upgrade our database
ma = Marshmallow(app) # marshmallow: help us make our data json

@app.cli.command()  # 注册为命令
@click.option('--drop', is_flag=True, help='Create after drop.')  # 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')  # 输出提示信息

class Project(db.Model):
    """
    this class represents projects.

    Attributes
    ----------

    proj_id: int, generated automatically
    
    proj_name: str, REQUIRED
    
    pl_type: str, default='Python'
        the programming language of our project.
    
    location: str, REQUIRED
        where we save the file of this project.

    date: Date, generated
        when this project created.

    Usage
    -----
    >>> db.create_all() # create the database
    >>> db.session.add(Project(location='/', proj_name='greatProj1'))
    >>> db.session.commit() # don't forget this!!!
    # >>> Project.query.all() # show all
    """
    proj_id = db.Column(db.Integer, primary_key=True)
    proj_name = db.Column(db.String(100), nullable=False)
    pl_type = db.Column(db.String(20), default='Python')
    location = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.datetime.now())

    def __repr__(self) -> str:
        return f"Project {self.proj_id} in {self.pl_type} has been created since {self.date} "

    def __str__(self) -> str:
        return super().__repr__()

class ProjectSchema(ma.SQLAlchemySchema):
    """this class is used for serialize our data.

    Parameters
    ----------
    ma : marshmallow object
    
    Usage
    -----
    >>> ps = ProjectSchema(many=True)
    >>> ps.dump(Project.query.all())
    """
    class Meta:
        model = Project
        
    proj_id = ma.auto_field()
    pl_type = ma.auto_field()
    location = ma.auto_field()
    proj_name = ma.auto_field()
    date = ma.DateTime()

ps = ProjectSchema(many=True)

@app.route('/')
def index():
    """this site is just for test. show all projects.

    Returns
    -------
    json
        contains all our infomation about projs.
        
    Usage
    -----
    in bash:
    $ curl http://127.0.0.1:5000
    returns a dictionary.
    """
    return jsonify({'projects': ps.dump(Project.query.all())})

@app.route('/create', methods=['GET', 'POST'])
def create_project():
    """create a project. 
    
    Returns
    -------
    status: json
        {'status': 'ok' | 'error' | 'incomplete'}
        ok ---- ok
        error ---- internal problems
        incomplete ---- user form is wrong. (didn't give the proj's name or so.)
    Usage
    -----
    HTML form
    """
    try:
        if request.method == 'GET':
            return redirect(url_for('index'))
        data = request.json
        if 'proj_name' not in data:
            print('no name')
            return jsonify({'status': 'incomplete'})
        '''if 'location' not in data:
            print('no location')
            return jsonify({'status': 'incomplete'})'''
        proj_name = data['proj_name']
        #project name conflict
        if Project.query.filter_by(proj_name=proj_name).first()!=None:
            print('project name conflict')
            return jsonify({'status':'incomplete'})
        #location = data['location']
        if 'pl_type' in data:
            # 此处还应添加项目类型检测
            pl_type = data['pl_type']
        else:
            pl_type = 'Python'
        location = '/home/ubuntu/project/'+proj_name
        project = Project(proj_name=proj_name, pl_type=pl_type, location=location)
        db.session.add(project)
        db.session.commit()

        # add directory
        #print(os.path.exists("/home/ubuntu"))
        os.makedirs(location)

        return jsonify({'status': 'ok'})
    except:
        return jsonify({'status': 'error'})

@app.route('/proj/<proj_id>', methods=['DELETE', 'PUT'])
def delete_rename(proj_id):
    if request.method == 'DELETE':
        try:
            project = Project.query.get(proj_id)
            proj_name = project.proj_name
            db.session.delete(project)
            db.session.commit()

            #delete directory
            shutil.rmtree('/home/ubuntu/project/'+proj_name)

            return jsonify({'id': proj_id, 'status': 'ok'})
        except:
            return jsonify({'status': 'error'})
    elif request.method == 'PUT':
        try:
            if 'proj_name' not in request.form:
                return jsonify({'status': 'incomplete'})
            project = Project.query.get(proj_id)
            proj_name_old = project.proj_name
            project.proj_name = request.form['proj_name']
            path = "/home/ubuntu/project"
            project.location = os.path.join(path, request.form['proj_name'])
            db.session.commit()

            #rename directory

            os.rename(os.path.join(path, proj_name_old), os.path.join(path, request.form['proj_name']))

            return jsonify({'id': proj_id, 'status': 'ok'})
        except:
            return jsonify({'status': 'error'})
# should be matched to the ide page
@app.route('/open/<proj_id>', methods=['GET'])
def open_project(proj_id):
    try:
        project = Project.query.get(proj_id)
        location = project.location
        url_new = "82.157.251.229:8080/?folder="+location # IP address should be corrected
        return redirect(url_new)
    except:
        return jsonify({'status': 'error'})

