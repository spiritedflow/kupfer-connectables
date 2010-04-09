# -*- coding: UTF-8 -*-

"""
Copyright 2010 Artem <spiritedflow@gmail.com>

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""


import os
import stat
import glob
import yaml

from kupfer.objects import Leaf, Action, Source
from kupfer.obj.helplib import PicklingHelperMixin, FilesystemWatchMixin
from kupfer import utils

__kupfer_name__ = _("Connectables")
__kupfer_sources__ = ("ConnectableSource", )
__description__ = _("All connectable devices. You need to configure this plugin manually. See example <here>")
__version__ = "0.1"
__author__ = "Artem <spiritedflow@gmail.com>"

# ---------------------------------------------
# Paths
# ---------------------------------------------
config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
base_path = os.path.join(config_home, "kupfer", "connectables")
leafs_path = os.path.join(base_path, "leafs")
actions_path = os.path.join(base_path, "actions")

# ---------------------------------------------
# Action Cache
# ---------------------------------------------
class ActionDataCache:
	"""
	Cache for actions data
	"""
	def __init__(self, directory):
		self.directory = directory
		self.cache = {}

	def get_data(self, name):
		"""
		Returns data for actions with name
		
		At first it checks cache, then if there is no entry in the cache, it loads data from the file
		"""
		file = os.path.join (self.directory, name + '.yaml')
		mtime = os.stat(file)[stat.ST_MTIME]
		# check for cache entry,
		# if it's ok return it
		if name in self.cache and self.cache['name']['_mtime_'] == mtime:
			return self.cache['name']['data']
		# if there no cache entry or it is old,
		# make new one
		data = yaml.load(open(file))
		self.cache['name'] = {
			'data' : data,
			'_mtime_' : mtime
		}
		# and return new data
		return data

actions_cache = ActionDataCache(actions_path)

# ----------------------------------------
# Kupfer objects
# ----------------------------------------

class ConnectableSource (Source, PicklingHelperMixin, FilesystemWatchMixin):
	""" 
	Source for manually configured connectables objects
	
	The class contains all objects in your ~/.config/kupfer/connectables/leafs directory
	"""

	def __init__(self, name=_("Connectable Devices List")):
		self.directory = leafs_path
		Source.__init__(self, name)
		self.unpickle_finish()

	def unpickle_finish(self):
		self.monitor_token = self.monitor_directories(self.directory)

	def get_items(self):
		files = glob.glob(os.path.join(self.directory, '*.yaml'))
		for fullname in files:
			(filepath, filename) = os.path.split(fullname)
			(name, ext) = os.path.splitext(filename)
			data = yaml.load (open(fullname))
			yield ConnectableLeaf(data, name)

	def get_description(self):
		return _("All connectable objects")

	def get_icon_name(self):
		return "applications-internet"

	def provides(self):
		yield ConnectableLeaf


class ConnectableLeaf (Leaf):
	"""
	Connectable object
	
	Reads and holds all actions you can do with this device
	"""

	def __init__ (self, data, name):
		self.name = name
		obj = {
			'name' : name,
			'descr' : _("Connectable object %(name)s"),
			'icon_name': 'system'
			}
		obj.update(data)
		Leaf.__init__(self, obj, name)

	def get_actions(self):
		for act_name in self.object['actions']:
			yield ConnectableAction(act_name, self.object)

	def get_description(self):
		return substitute(self.object['descr'], self.object)

	def get_icon_name(self):
		return self.object['icon_name']


class ConnectableAction (Action):
	"""
	An action for connectable object
	
	Do what described in ~/.config/kupfer/connectables/actions/<action>.yaml
	"""
	def __init__(self, name, object):
		self.name = name
		self.object = object
		self.data = {
			'type': 'unkwnon',
			'name': 'Unknown',
			'descr': 'Seems an action file ' + name + '.yaml is missed',
			'rank': 20,
			'icon_name': 'system-run',
			'env': {},
		}
		self.data.update(actions_cache.get_data (name))
		Action.__init__(self, self.data['name'])

	def activate (self, leaf):
		run_command (self.data['type'], self.data, self.object)

	def get_description(self):
		return substitute(self.data['descr'], self.object)

	def get_icon_name(self):
		return self.data['icon_name']

	def get_rank(self):
		print 'Getting rank'
		return self.data['rank']


def substitute(s, data):
	"""Substitute all %(var)s with elements in data"""
	return s % data


def run_command(typ, action_data, leaf_data):
	"""Run command. Called from actions"""
	if typ == 'command':
		cmd = substitute(action_data['cmd'], leaf_data)
		env = action_data['env']
		utils.launch_commandline(cmd)
	elif typ == 'uri':
		uri = substitute(action_data['uri'], leaf_data)
		utils.show_url(uri)
