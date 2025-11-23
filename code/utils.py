import re

async def getkey(obj, key, default):
	try:
		return obj[key]
	except:
		return default
async def normalize_keywords(s: str) -> str:
	clean = re.sub(r'[^\w\s]', '', s, flags=re.UNICODE)
	clean = re.sub(r'\s+', ' ', clean).strip()
	return clean