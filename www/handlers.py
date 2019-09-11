import asyncio
from aiohttp import web
from coroweb import get, post

@get('/')
async def handler_url_blog(*,request):
	body='<h1>Awesome</h1>'
	return body

@get('/greeting')
async def handler_url_greeting(*,name='Bob',request):
	body='<h1>Awesome: /greeting %s</h1>'%name
	return body

@get('/test')
async def handler_url_test(*,request):
	return web.Response(body=b'<h1>Awesome: test</h1>', content_type='text/html')