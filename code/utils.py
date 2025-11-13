async def getkey(obj, key, default):
	try:
		return obj[key]
	except:
		return default