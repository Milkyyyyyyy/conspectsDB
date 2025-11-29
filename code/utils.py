import re
from typing import List
import os

async def getkey(obj, key, default):
	try:
		return obj[key]
	except:
		return default
async def normalize_keywords(s: str) -> str:
	clean = re.sub(r'[^\w\s]', '', s, flags=re.UNICODE)
	clean = re.sub(r'\s+', ' ', clean).strip()
	return clean
async def normalize_paths(file_paths) -> List[str]:
	if isinstance(file_paths, str):
		file_paths = [file_paths, ]
	output_paths = []
	for path in file_paths:
		normalized = os.path.normpath(path)
		output_paths.append(normalized.replace(os.sep, '/'))
	return output_paths