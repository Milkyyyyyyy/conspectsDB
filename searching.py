import re
from typing import List, Dict, Any, Iterable, Optional, Sequence
from difflib import SequenceMatcher

# Попытка импортировать pymorphy2 (для лемматизации) и rapidfuzz (для скоринга)
try:
	import pymorphy2
	MORPH = pymorphy2.MorphAnalyzer()
except Exception:
	MORPH = None

try:
	from rapidfuzz import fuzz
	_HAS_RAPIDFUZZ = True
except Exception:
	_HAS_RAPIDFUZZ = False

_TOKEN_RE = re.compile(r'\w+', flags=re.UNICODE)


def _simple_russian_stem(word: str) -> str:
	"""Грубый фоллбэк-стеммер для русского (если нет pymorphy2)"""
	w = word.lower()
	suffixes = (
		'иями','ями','ами','иям','ием','иях','иях','ов','ев','ей','ам','ом','ям',
		'ах','ях','ою','ею','ие','ии','ию','ью','ю','у','ы','а','я','е','и','ь','ий'
	)
	for suf in suffixes:
		if w.endswith(suf) and len(w) - len(suf) >= 3:
			return w[:-len(suf)]
	return w


def normalize_text(text: str) -> str:
	if not text:
		return ""
	tokens = _TOKEN_RE.findall(str(text).lower())
	if MORPH:
		lemmas = []
		for t in tokens:
			# берем первую (наиболее вероятную) разборку
			p = MORPH.parse(t)[0]
			lemmas.append(p.normal_form)
		return " ".join(lemmas)
	else:
		return " ".join(_simple_russian_stem(t) for t in tokens)


def _seq_ratio(a: str, b: str) -> float:
	"""SequenceMatcher ratio -> 0..1"""
	if not a and not b:
		return 1.0
	if not a or not b:
		return 0.0
	return SequenceMatcher(None, a, b).ratio()


def _jaccard_from_token_lists(a_tokens: Sequence[str], b_tokens: Sequence[str]) -> float:
	if not a_tokens and not b_tokens:
		return 1.0
	if not a_tokens or not b_tokens:
		return 0.0
	sa, sb = set(a_tokens), set(b_tokens)
	inter = sa & sb
	union = sa | sb
	return len(inter) / len(union)


def _score_strings(item_lemmas: str, query_lemmas: str) -> float:
	if _HAS_RAPIDFUZZ:
		return float(fuzz.token_set_ratio(item_lemmas, query_lemmas)) / 100.0
	else:
		a_tokens = item_lemmas.split()
		b_tokens = query_lemmas.split()
		j = _jaccard_from_token_lists(a_tokens, b_tokens)
		s = _seq_ratio(item_lemmas, query_lemmas)
		return 0.6 * j + 0.4 * s


def search_and_rank(
		items: Iterable[Dict[str, Any]],
		query: str,
		keys: Sequence[str] = ('theme',),
		top_n: Optional[int] = None,
		min_score: float = 0.0) -> List[Dict[str, Any]]:
	"""
	:param items: Список словарей, по которому требуется произвести поиск.
	:param query: Запрос.
	:param keys: Ключи из словаря, по которым будет производиться поиск.
	:param top_n: Вернёт только n лучших вариантов.
	:param min_score: Отфильтровывает все записи со score < min_score
	"""
	q_lemmas = normalize_text(query).strip()
	if not q_lemmas:
		return []
	results: List[Dict[str, Any]] = []
	for it in items:
		# собираем текст из указанных полей
		parts = []
		for k in keys:
			try:
				v = it.get(k) if isinstance(it, dict) else None
			except Exception:
				v = None
			if v is None:
				continue
			if isinstance(v, (list, tuple)):
				parts.append(" ".join(str(x) for x in v))
			else:
				parts.append(str(v))
		raw = " ".join(parts)
		item_lemmas = normalize_text(raw).strip()
		if not item_lemmas:
			s = 0.0
		else:
			s = _score_strings(item_lemmas, q_lemmas)

		if s >= min_score:
			out = dict(it)  # shallow copy
			out['_score'] = s
			results.append(out)

	# сортировка: сначала самые релевантные (1 - самые релевантные)
	results.sort(key=lambda x: x['_score'], reverse=True)
	if top_n is not None:
		return results[:top_n]
	return results
