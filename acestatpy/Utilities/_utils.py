'''
Last Modified: 2021-04-23

@author: Jesse M. Barr

Contains:
    -PKG_NAME
    -PKG_RESOURCE
    -resource_path()
    -resource_stream()
    -_get_platform()
    -PLATFORM

Changes:

ToDo:

'''
import sys
from os.path import join, dirname, realpath
from os import environ
from sys import platform as _sys_platform
import pkg_resources

PKG_NAME = "acestatpy"
PKG_RESOURCE = "resources"

def resource_path(add_path=None):
    path = PKG_RESOURCE
    if isinstance(add_path, list) and not isinstance(add_path, basestring):
        path = join(path, **add_path)
    elif add_path:
        path = join(path, add_path)
    return pkg_resources.resource_filename("acestatpy", path)

def resource_stream(add_path=None):
    path = PKG_RESOURCE
    if isinstance(add_path, list) and not isinstance(add_path, basestring):
        path = join(path, **add_path)
    elif add_path:
        path = join(path, add_path)
    return pkg_resources.resource_stream("acestatpy", path)

def _get_platform():
    # On Android sys.platform returns 'linux2', so prefer to check the
    # presence of python-for-android environment variables (ANDROID_ARGUMENT
    # or ANDROID_PRIVATE).
    if 'ANDROID_ARGUMENT' in environ:
        return 'android'
    elif environ.get('KIVY_BUILD', '') == 'ios':
        return 'ios'
    elif _sys_platform in ('win32', 'cygwin'):
        return 'win'
    elif _sys_platform == 'darwin':
        return 'macosx'
    elif _sys_platform.startswith('linux'):
        return 'linux'
    elif _sys_platform.startswith('freebsd'):
        return 'linux'
    return 'unknown'


PLATFORM = _get_platform()
