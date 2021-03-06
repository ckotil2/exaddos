# encoding: utf-8
"""
container.py

Created by Thomas Mangin on 2014-02-06.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

from threading import Lock
from copy import deepcopy

class ContainerSNMP (object):

	def __init__ (self,max_speakers=5):
		self.lock = Lock()
		self._data = {}

	def keys (self):
		with self.lock:
			return self._data.keys()

	def set (self,name,d):
		with self.lock:
			r = self._data.setdefault(name,{})
			for k,v in d.iteritems():
				r[k] = v

	def get (self,name):
		with self.lock:
			return dict(self._data[name].iteritems())

	def data (self):
		with self.lock:
			return deepcopy(self._data)


class ContainerFlow (object):

	# _overall = {
	# 	'tcp' : {'pckts': 0, 'bytes': 0},
	# 	'udp' : {'pckts': 0, 'bytes': 0},
	# 	'other': {'pckts': 0, 'bytes': 0},
	# 	'total': {'pckts': 0, 'bytes': 0},
	# }

	def __init__ (self,max_speakers=5):
		self.lock = Lock()

		# flow code
		self._counters = {}
		self._overall = {}
		self._threshold = {}
		self._traffic = {}

		self._max_speaker = max_speakers
		self.period = 5

		self.localhost = (127 << 24) + 1

		for minute in range(0,self.period):
			self.make_minute(minute)

	def make_minute (self,minute):
		counter = self._counters

		if minute not in counter:
			counter[minute] = {}
			for direction in ('sipv4','dipv4'):
				for counter in ('bytes','pckts'):
					# numbers need to be unique, and lower than our traffic
					self._threshold.setdefault(minute,{}).setdefault(direction,{})[counter] = list(range(0,-self._max_speaker,-1))
					self._traffic.setdefault(minute,{}).setdefault(direction,{})[counter] = dict(zip(range(0,-self._max_speaker,-1),[self.localhost,]*self._max_speaker))

	def purge_minute (self,minute):
		counter = self._counters
		for past in self._threshold.keys()[:-self.period]:
			del counter[past]
			del self._threshold[past]
			del self._traffic[past]

	def ipfix (self,update):
		minute = int(update['epoch'])/60

		with self.lock:
			self.purge_minute(minute)
			self.make_minute(minute)

			overall = self._overall
			counter = self._counters

			bytes = update['bytes']
			pckts = update['pckts']

			total = overall.setdefault('total',{})
			total['bytes'] = total.get('bytes',0) + bytes
			total['pckts'] = total.get('pckts',0) + pckts

			tcp = overall.setdefault('tcp',{})
			tcp['bytes'] = tcp.get('bytes',0) + bytes
			tcp['pckts'] = tcp.get('pckts',0) + pckts

			udp = overall.setdefault('udp',{})
			udp['bytes'] = udp.get('bytes',0) + bytes
			udp['pckts'] = udp.get('pckts',0) + pckts

			other = overall.setdefault('other',{})
			other['bytes'] = other.get('bytes',0) + bytes
			other['pckts'] = other.get('pckts',0) + pckts

			source = counter.setdefault(minute,{}).setdefault('sipv4',{}).setdefault('sipv4',{}).setdefault(update['sipv4'],{'pckts': 0, 'bytes': 0})
			source['bytes'] += bytes
			source['pckts'] += pckts

			destination = counter.setdefault(minute,{}).setdefault('dipv4',{}).setdefault(update['dipv4'],{'pckts': 0, 'bytes': 0})
			destination['bytes'] += bytes
			destination['pckts'] += pckts

			proto = counter.setdefault(minute,{}).setdefault('proto',{}).setdefault(update['proto'],{'pckts': 0, 'bytes': 0})
			proto['bytes'] += bytes
			proto['pckts'] += pckts


			for direction,data in (('sipv4',source),('dipv4',destination)):
				for counter in ('bytes','pckts'):
					traffic = self._traffic[minute][direction][counter]
					maximum = self._threshold[minute][direction][counter]
					drop = maximum[0]

					value = data[counter]
					if value > drop:
						# prevent duplicate entries by cheating
						while value in maximum:
							value += 1

						maximum = sorted(maximum[1:] + [value,])
						self._threshold[minute][direction][counter] = maximum

						del self._traffic[minute][direction][counter][drop]
						traffic[value] = update[direction]

	# def counters (self):
	# 	with self.lock:
	# 		return deepcopy(self._counters)

	def overall (self):
		with self.lock:
			return deepcopy(self._overall)

	def traffic (self):
		with self.lock:
			return deepcopy(self._traffic)


