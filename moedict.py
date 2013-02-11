#!/usr/bin/env python
# encoding: utf-8

import sublime, sublime_plugin
import threading
import urllib, urllib2, json

# What the command actually does is to fetch JSON files representing
# definitions of Chinese characters or phrases stored on Audrey Tang's
# personal website, then insert them to the editor, while We fetch and
# cache "prefix.json" for doing auto-completion.

PREFIX_MAP = None
PREFIX_JSON_URL = "http://www.moedict.tw/prefix.json"
DATA_JSON_TEMPLATE = "http://www.moedict.tw/uni/%s.json"

class APICall(threading.Thread):
	'''
	Thread object which is able to return value.
	'''
	def __init__(self, group=None, target=None, name=None,
		args=(), kwargs=None, verbose=None):
		threading.Thread.__init__(self, group, target, name, args, kwargs, verbose)
		self._return = None
	def run(self):
		if self._Thread__target is not None:
			print self._Thread__args
			print self._Thread__kwargs
			self._return = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
	def join(self):
		threading.Thread.join(self)
		return self._return

class MoeDictCommand(sublime_plugin.WindowCommand):
	'''
	The Sublime Text plug-in which queries definitions within MOE
	Chinese Dictionary.
	'''

	prefix = ''
	current_list = []
	current_item = ''

	def run(self):
		self.window.show_input_panel('Prefix:', self.prefix, self.on_input_prefix, None, None)

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
				sublime.error_message('Failed to load MOE dictionary! ' + str(e))

		def render(data):
			text = ''
			if 'radical' in data:
				text += u'* 部首： %s\n' % data['radical']
			if 'stroke_count' in data:
				text += u'* 筆畫： %s\n' % str(data['stroke_count'])
			if 'non_radical_stroke_count' in data:
				text += u'* 非部首筆畫： %s\n' % str(data['non_radical_stroke_count'])
			text += '\n'

			for heteronym in data['heteronyms']:
				text += '-' * 76 + '\n'
				if 'bopomofo' in heteronym:
					text += u'* 注音一式： %s\n' % heteronym['bopomofo']
				if 'bopomofo2' in heteronym:
					text += u'* 注音二式： %s\n' % heteronym['bopomofo2']
				if 'hanyu_pinyin' in heteronym:
					text += u'* 漢語拼音： %s\n' % heteronym['hanyu_pinyin']

				if 'definitions' in heteronym:
					from collections import defaultdict
					definitions = defaultdict(list)
					for d in heteronym['definitions']:
						key = d.get('type', '')
						definitions[key].append(d)

					for pos in definitions:
						text += '\n[%s]\n\n' % pos if len(pos) else '\n'
						count = 1
						section = definitions[pos]
						for d in section:
							if 'def' in d:
								if len(section) > 1:
									text += '%d. %s\n' % (count, d['def'])
								else:
									text += '%s\n' % d['def']
							if 'example' in d:
								for quote in d['example']:
									text += '    * %s\n' % quote
							if 'quote' in d:
								for quote in d['quote']:
									text += '    * %s\n' % quote
							if 'link' in d:
								for link in d['link']:
									text += '%s\n' % link

							count += 1
				return text + '\n\n'

		self.current_item = self.current_list[picked] if picked != -1 else self.prefix
		thread = APICall(target=fetch_item)
		thread.start()
		data = thread.join()
		print type(data)
		if data and len(data):
			text = '# %s\n\n' % self.current_item
			text += render(data)
			view = self.window.new_file()
			view.set_name(self.current_item)
			try:
				view.set_syntax_file(u'Packages/Markdown/Markdown.tmLanguage'
				)
			except:
				pass
			edit = view.begin_edit()
			view.insert(edit, 0, text)
			view.end_edit(edit)
