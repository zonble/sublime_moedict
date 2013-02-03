#!/usr/bin/env python
# encoding: utf-8

import sublime, sublime_plugin
import threading
import urllib, urllib2, json

PREFIX_MAP = None
PREFIX_JSON_URL = "http://www.audreyt.org/newdict/moedict-webkit/prefix.json"
DATA_JSON_TEMPLATE = "http://www.audreyt.org/newdict/moedict-webkit/api/data/%s.json"

class APICall(threading.Thread):
	'''
	Thread object which is able to return value.
	'''
	def __init__(self, group=None, target=None, name=None,
		args=(), kwargs=None, verbose=None):
		threading.Thread.__init__(self, group, target, name, args,
								  kwargs, verbose)
		self._return = None
	def run(self):
		if self._Thread__target is not None:
			print self._Thread__args
			print self._Thread__kwargs
			self._return = self._Thread__target(*self._Thread__args,
												 **self._Thread__kwargs)
	def join(self):
		threading.Thread.join(self)
		return self._return

class MoeDictCommand(sublime_plugin.WindowCommand):

	prefix = ''
	current_list = []
	current_item = ''

	def run(self):
		self.window.show_input_panel('Prefix:', self.prefix,
							 self.on_input_prefix, None, None)

	def on_input_prefix(self, input):
		def fetch_prefix():
			global PREFIX_MAP
			try:
				PREFIX_MAP = json.loads(urllib2.urlopen(PREFIX_JSON_URL).read())
			except Exception, e:
				sublime.error_message('Failed to load MOE dictionary!')

		if not PREFIX_MAP or not len(PREFIX_MAP):
			thread = APICall(target=fetch_prefix)
			thread.start()
			thread.join()

		if PREFIX_MAP and len(PREFIX_MAP):
			self.prefix = input.strip()
			m = PREFIX_MAP.get(self.prefix)
			self.current_list = [self.prefix] + [self.prefix + x for x in m.split('|') if len(x)] if m else []
			self.window.show_quick_panel(self.current_list, self.on_choose_key)

	def on_choose_key(self, picked):
		def fetch_item():
			try:
				url = DATA_JSON_TEMPLATE % urllib.quote(self.current_item.encode('utf-8'))
				print url
				return json.loads(urllib2.urlopen(url).read())
			except Exception, e:
				sublime.error_message('Failed to load MOE dictionary!' + str(e))

		def render(data):
			text = ''
			if 'bopomofo' in data:
				text += '* %s\n' % data['bopomofo']
			if 'bopomofo2' in data:
				text += '* %s\n' % data['bopomofo2']

			if 'definitions' in data:
				from collections import defaultdict
				definitions = defaultdict(list)
				for d in data['definitions']:
					key = d.get('pos', '')
					definitions[key].append(d)

				for pos in definitions:
					text += '\n## %s \n\n' % pos if len(pos) else '\n'
					count = 1
					section = definitions[pos]
					for d in section:
						if len(section) > 1:
							text += '%d. %s\n' % (count, d['definition'])
						else:
							text += '%s\n' % d['definition']
						if 'quote' in d:
							for quote in d['quote']:
								text += '> %s\n' % quote
						count += 1
			return text

		self.current_item = self.current_list[picked] if picked != -1 else self.prefix
		thread = APICall(target=fetch_item)
		thread.start()
		data = thread.join()
		print type(data)
		if data and len(data):
			text = '# %s\n\n' % self.current_item
			for d in data:
				text += render(d)
			view = self.window.new_file()
			edit = view.begin_edit()
			view.insert(edit, 0, text)
			view.end_edit(edit)




