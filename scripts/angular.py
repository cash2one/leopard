import sh
from flask.ext.script import Manager

manager = Manager()


@manager.command
def build():
    sh.cd('leopard-ng')
    for line in sh.grunt(force=True, _iter=True):
        print(line, end='')


@manager.command
def clean():
    sh.cd('leopard-ng')
    sh.grunt.clean(force=True)
