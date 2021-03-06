# encoding: utf-8
"""
flow.py

Created by Thomas Mangin on 2014-02-09.
Copyright (c) 2014-2014 Exa Networks. All rights reserved.
"""

import sys
import socket

from .thread import Thread
from .ipfix import IPFIX


class _FlowServerFactory (object):
	def __init__ (self,host,port,container,queue):
		print 'ipfix server on %s:%d' % (host,port)
		self.flowd = None
		self.queue = queue

		self.host = host
		self.port = port

		self.parser = IPFIX(container.ipfix)

	def serve (self):
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.bind((self.host,self.port))
			self.running = True
		except:
			print >> sys.stderr, 'could not start ipfix server'
			raise

		try:
			while self.running:
				data, addr = sock.recvfrom(8192)
				self.parser.read(data)
		except Exception,e:
			self.running = False
			raise e

	def start (self):
		self.flowd = Thread(self.serve,self.queue)
		self.flowd.daemon = True
		self.flowd.start()

	def alive (self):
		return self.running

	def join (self):
		if self.flowd:
			self.flowd.join(0.1)


class FlowServer (object):
	servers = {}

	def __init__ (self,configuration,container):
		# This will be shared among all instrance
		self.configuration = configuration
		self.container = container

	def add (self,host,port,queue):
		key = '%s:%d' % (host,port)
		if key not in self.servers:
			server = _FlowServerFactory(host,port,self.container,queue)
			server.parent = self
			self.servers[key] = server

	def run (self):
		for key in self.servers:
			self.servers[key].start()

	def join (self):
		for key in self.servers:
			self.servers[key].join()

	def alive (self):
		for key in self.servers:
			if self.servers[key].flowd.isAlive():
				return True
		return False
