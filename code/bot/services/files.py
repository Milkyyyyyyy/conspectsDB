import os
import mimetypes
from typing import List, Tuple
import telebot
from code.logging import logger


async def save_files(bot,
               items: List[Tuple[str, ]],
               save_dir: str = 'downloads') -> list:
	os.makedirs(save_dir, exist_ok=True)
	paths = []
	for i, (file_type, msg) in enumerate(items, start=1):
		try:
			if file_type == 'photo':
				if not getattr(msg, 'photo', None):
					logger.error('Message has no photo')
					continue

				file_id = msg.photo[-1].file_id
				file_info = await bot.get_file(file_id)
				file_bytes = await  bot.download_file(file_info.file_path)

				_, ext = os.path.splitext(file_info.file_path)
				if not ext:
					ext = '.jpg'

				filename = (f'{i}.{msg.from_user.id if msg.from_user else 'unknown'}.'
				            f'{file_id}{ext}')
				path = os.path.join(save_dir, filename)
				with open(path, 'wb') as f:
					f.write(file_bytes)
				paths.append(path)
				logger.info(f'Saved photo {filename} -> {path}')

			elif file_type == 'document':
				if not getattr(msg, 'document', None):
					logger.error('Message has no document')
					continue
				doc = msg.document
				file_id = doc.file_id
				file_info = await bot.get_file(file_id)
				file_bytes = await bot.download_file(file_info.file_path)

				if getattr(doc, 'file_name', None):
					filename = doc.file_name
				else:
					ext = None
					if getattr(doc, 'mime_type', None):
						ext = mimetypes.guess_extension(doc.mime_type)
					if not ext:
						_, ext = os.path.splitext(file_info.file_path)
					if not ext:
						ext = ''
					filename = (f'{i}.{msg.from_user.id if msg.from_user else 'unknown'}.'
					            f'{file_id}{ext}')
				safe_path = os.path.join(save_dir, filename)
				base, ext = os.path.splitext(safe_path)
				counter = 1
				while os.path.exists(safe_path):
					safe_path = f'{base}_{counter}{ext}'
					counter += 1

				with open(safe_path, 'wb') as f:
					f.write(file_bytes)
				paths.append(safe_path)
				logger.info(f'Saved document {filename} -> {safe_path}')
			else:
				logger.error(f'Unknown type {file_type}')
				continue
		except Exception as e:
			logger.error(f'Error saving file {file_type}: {e}')
	return paths