import www.orm
import asyncio
from www.models import User, Blog, Comment

async def test(loop):
	await www.orm.create_pool(loop=loop, user='www-data', password='www-data', db='awesome')
	u = User(name='admin', email='admin@qq.com', passwd='1234567890', admin = True, image='about:blank')
	await u.save()
	www.orm.__pool.close()
	await www.orm.__pool.wait_closed()

if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete(test(loop))
	loop.close()