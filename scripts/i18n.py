# -*- coding: utf-8 -*-
"""language selection for the word window and the vocabulary sheet.

study/config.json:  {"lang": "ko", "game": "Game Title"}
glosses:            gloss_<lang>.tsv (above the learner's level), gloss_basic_<lang>.tsv (basic words)
To add a language, add one table to STR below. Missing keys fall back to English.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

STR = {
    'ko': {
        'html_lang': 'ko', 'font': 'Malgun Gothic',
        'title': '단어 창', 'prev_ch': '≪장', 'next_ch': '장≫', 'auto': '자동', 'manual': '수동',
        'kind_D': '대사', 'kind_T': '속마음', 'kind_N': '지문', 'voice': '음성',
        'head': '{ch}장  {n} / {total}', 'no_words': '이 줄에는 표시할 단어가 없습니다.',
        'wait_game': '게임 대기 중', 'wait_line': '대사 대기 중', 'wait_hint': '대사 대기 중 (연동 안 되면 ◀ ▶ 사용)',
        'linked': '연동됨', 'read_error': '읽기 오류',
        'sheet_title': '단어장', 'sheet_file': '단어장.html', 'launcher': '단어창 실행.bat',
        'th_word': '단어', 'th_reading': '읽기', 'th_meaning': '뜻', 'th_count': '횟수',
        'ch_heading': '제{ch}장', 'ch_tab': '{ch}장', 'n_words': '{n}단어',
        'search_ph': '검색 (단어·읽기·뜻)', 'hide_reading': '읽기 가리기', 'hide_meaning': '뜻 가리기',
        'note': '각 장에서 처음 나오는 단어 {total}개입니다. 횟수는 작품 전체 등장 횟수입니다. 가린 칸은 누르면 보입니다. '
                '검색하면 모든 장에서 찾습니다. 읽기와 뜻은 자동 분석을 바탕으로 한 사전적 풀이라 문맥에 따라 다를 수 있습니다.',
    },
    'en': {
        'html_lang': 'en', 'font': 'Segoe UI',
        'title': 'Word Window', 'prev_ch': '≪Ch', 'next_ch': 'Ch≫', 'auto': 'Auto', 'manual': 'Manual',
        'kind_D': 'Dialogue', 'kind_T': 'Thought', 'kind_N': 'Narration', 'voice': 'voiced',
        'head': 'Ch. {ch}  {n} / {total}', 'no_words': 'No words to show for this line.',
        'wait_game': 'Waiting for the game', 'wait_line': 'Waiting for a line', 'wait_hint': 'Waiting for a line (use ◀ ▶ if it never links)',
        'linked': 'Linked', 'read_error': 'Read error',
        'sheet_title': 'Vocabulary', 'sheet_file': 'vocabulary.html', 'launcher': 'Word Window.bat',
        'th_word': 'Word', 'th_reading': 'Reading', 'th_meaning': 'Meaning', 'th_count': 'Count',
        'ch_heading': 'Chapter {ch}', 'ch_tab': 'Ch. {ch}', 'n_words': '{n} words',
        'search_ph': 'Search (word, reading, meaning)', 'hide_reading': 'Hide readings', 'hide_meaning': 'Hide meanings',
        'note': '{total} words, listed in the chapter where each first appears. Count is the number of occurrences in the whole work. '
                'Click a hidden cell to reveal it. Searching looks in every chapter. Readings and meanings are dictionary-style glosses '
                'based on automatic analysis and may differ from the meaning in context.',
    },
    'ja': {
        'html_lang': 'ja', 'font': 'Yu Gothic UI',
        'title': '単語ウィンドウ', 'prev_ch': '≪章', 'next_ch': '章≫', 'auto': '自動', 'manual': '手動',
        'kind_D': '台詞', 'kind_T': '心の声', 'kind_N': '地の文', 'voice': '音声',
        'head': '第{ch}章  {n} / {total}', 'no_words': 'この行に表示する単語はありません。',
        'wait_game': 'ゲーム待機中', 'wait_line': '台詞待機中', 'wait_hint': '台詞待機中（連動しない場合は ◀ ▶ を使用）',
        'linked': '連動中', 'read_error': '読み取りエラー',
        'sheet_title': '単語帳', 'sheet_file': '単語帳.html', 'launcher': '単語ウィンドウ.bat',
        'th_word': '単語', 'th_reading': '読み', 'th_meaning': '意味', 'th_count': '回数',
        'ch_heading': '第{ch}章', 'ch_tab': '{ch}章', 'n_words': '{n}語',
        'search_ph': '検索（単語・読み・意味）', 'hide_reading': '読みを隠す', 'hide_meaning': '意味を隠す',
        'note': '各章で初めて出てくる単語 {total} 語です。回数は作品全体での出現回数です。隠したセルはクリックすると表示されます。'
                '検索は全章が対象です。読みと意味は自動解析に基づく辞書的な説明で、文脈によって異なる場合があります。',
    },
}


def config(folder=HERE):
    try:
        return json.load(open(os.path.join(folder, 'config.json'), encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def lang(folder=HERE):
    return config(folder).get('lang', 'ko')


def T(key, folder=HERE, **kw):
    s = STR.get(lang(folder), STR['en']).get(key) or STR['en'][key]
    return s.format(**kw) if kw else s


def gloss_files(folder=HERE):
    """(main, basic) gloss paths for the chosen language; older installs used ko.tsv / ko_basic.tsv"""
    lg = lang(folder)
    out = []
    for new, old in (('gloss_%s.tsv' % lg, 'ko.tsv'), ('gloss_basic_%s.tsv' % lg, 'ko_basic.tsv')):
        p = os.path.join(folder, new)
        if not os.path.exists(p) and lg == 'ko' and os.path.exists(os.path.join(folder, old)):
            p = os.path.join(folder, old)
        out.append(p)
    return out
