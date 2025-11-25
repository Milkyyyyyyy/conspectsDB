import aiosqlite

async def safe_row_to_dict(row) -> dict:
	if row is None:
		return {}
	else:
		return dict(row)