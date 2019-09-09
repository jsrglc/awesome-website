import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web
from apis import APIError

def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	def decorator(func):
		@functools.wraps(func):
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

def get_required_kw_args(fn):  #收集没有默认值的命名关键字参数
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)
	retun tuple(args)

def get_named_kw_args(fn):  #获取命名关键字参数
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)

def has_named_kw_args(fn):  #判断有没有命名关键字参数
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

def has_var_kw_args(fn):  #判断有没有可变关键字参数
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True

def has_request_arg(fn):  #判断是否含有名叫'request'参数，且该参数是否为最后一个参数
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name, param in params.items():
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITION and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request paramter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
	return found

class RequestHandler(object):

	def __init__(self, app, fn):
		self._app = app
		self._func = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	async def __call__(self, request):
		kw = None
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
			if request.method == 'POST':  #判断客户端发来的方法是否为POST
				if not request.content_type:  #查询有没提交数据的格式（EncType）
					return web.HTTPBadRequest(text='Missing Content-Type.')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = await request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest(text='JSON body must be object.')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = await request.post()
					kw = dict(**params)
					# reads POST parameters from request body.
					#If method is not POST, PUT, PATCH, TRACE or DELETE
					# or content_type is not empty or application/x-www-form-urlencoded or multipart/form-data
					# returns empty multidict.
				else:
					return HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
			if request.method = 'GET':
				qs = request.query_string  #The query string in the URL
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
						#Parse a query string given as a string argument.
						#Data are returned as a dictionary.
						#The dictionary keys are the unique query variable names and
						# the values are lists of values for each name.
						kw[k] = v[0]
		if kw is None:
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				#当函数参数没有关键字参数时，移去request除命名关键字参数所有的参数信息
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
					kw = copy
			for k, v in request.match_info.items():  #检查命名关键参数
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v
		if self._required_kw_args:  #假如命名关键字参数(没有附加默认值)，request没有提供相应的数值，报错
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest(text='Missing argument: %s' % name)
		logging.info('call with args: %s' % str(kw))
		try:
			r = await self._func(**kw)
			return r
		except:
			return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):  #添加静态文件夹的路径
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):  #编写一个add_route函数，用来注册一个URL处理函数
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		 #判断是否为协程且生成器,不是使用isinstance
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method, path, RequestHandler(app. fn))

	def add_routes(app, moudle_name):  #直接导入文件，批量注册一个URL处理函数
	n = module_name.rfind('.')
	if n == (-1):
		mod = __import__(module_name, globals(), locals())
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)