from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import os
from datetime import datetime

from fabric.api import env, local
from commcare_cloud.fab.utils import generate_bower_command
from fabric.colors import blue, red
from fabric.context_managers import settings
from fabric.contrib import files
from commcare_cloud.fab.const import (
    OFFLINE_STAGING_DIR,
    WHEELS_ZIP_NAME,
    BOWER_ZIP_NAME,
    NPM_ZIP_NAME,
    YARN_LOCK,
)


def prepare_files():
    hq_dir = '{}/commcare-hq'.format(OFFLINE_STAGING_DIR)

    if not os.path.isdir(hq_dir):
        local(
            'git clone --recursive https://github.com/dimagi/commcare-hq.git {}'
            .format(hq_dir)
        )
    else:
        print(blue('Skipping clone stage because {} already exists'.format(hq_dir)))

    # Let's create bower and npm zip files

    yarn_lock = os.path.join(env.code_root, YARN_LOCK)

    # Bower
    if not files.exists(yarn_lock):
        local('cd {}/commcare-hq && {}'.format(OFFLINE_STAGING_DIR, generate_bower_command('install', {
            'interactive': 'false',
        })))

    # NPM or Yarn
    local('cd {}/commcare-hq'.format(OFFLINE_STAGING_DIR))
    if files.exists(yarn_lock):
        local('yarn install --production')
    else:
        local('npm install --production')

    prepare_pip_wheels(os.path.join('requirements', 'requirements.txt'))
    prepare_pip_wheels(os.path.join('requirements', 'prod-requirements.txt'))


def prepare_pip_wheels(requirements_file):
    local(
        'cd {}/commcare-hq && pip wheel --wheel-dir=wheelhouse -r {}'
        .format(OFFLINE_STAGING_DIR, requirements_file)
    )


def prepare_formplayer_build():
    jenkins_formplayer_build_url = 'https://jenkins.dimagi.com/job/formplayer/lastSuccessfulBuild/artifact/build/libs/formplayer.jar'

    local('wget -nv {} -O {}/formplayer.jar'.format(jenkins_formplayer_build_url, OFFLINE_STAGING_DIR))


def check_ready():
    _print_stats(os.path.join(OFFLINE_STAGING_DIR, 'commcare-hq'))
    _print_stats(os.path.join(OFFLINE_STAGING_DIR, 'commcare-hq', 'bower_components'))
    _print_stats(os.path.join(OFFLINE_STAGING_DIR, 'commcare-hq', 'node_modules'))
    _print_stats(os.path.join(OFFLINE_STAGING_DIR, 'commcare-hq', 'wheelhouse'))
    _print_stats(os.path.join(OFFLINE_STAGING_DIR, 'formplayer.jar'))

    with settings(warn_only=True):
        commit = local('cd {}/commcare-hq && git show-ref --hash --heads {}'.format(
            OFFLINE_STAGING_DIR,
            env.deploy_metadata.deploy_ref,
        ), capture=True)
    print('Preparing to deploy ref {} on commit {}'.format(env.deploy_metadata.deploy_ref, commit))


def _print_stats(filename):
    try:
        stat = os.stat(filename)
    except OSError:
        print(red('Not found {}'.format(filename)))
        print(red('Exiting.'))
        exit()

    last_modified = str(datetime.fromtimestamp(stat.st_mtime))
    print(blue('Found {}, last modifed: {}'.format(filename, last_modified)))
