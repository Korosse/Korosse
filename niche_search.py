from pathlib import Path
import quick_search as q

q.OUT=Path('niche_output'); q.OUT.mkdir(exist_ok=True)
q.SHEETS=q.OUT/'sheets'; q.SHEETS.mkdir(exist_ok=True)
q.QUERIES=[
# Stint and adjacent reaction/clip farms
'стинт нарезки shorts','стинт лучшие моменты shorts','стинт смотрит shorts','стинт реакции shorts','stint fun shorts','нарезки стинта shorts','стинт подкаст shorts','стинт интервью shorts','стинт тикток shorts','стинт майнкрафт shorts',
# T2X2 and Minecraft streamer clips
't2x2 нарезки shorts','t2x2 лучшие моменты shorts','t2x2 minecraft shorts','t2x2 стрим нарезки shorts','t2x2 clips shorts','твич нарезки t2x2 shorts','стример сверху minecraft снизу shorts','стример лицо сверху геймплей снизу shorts','реакция сверху minecraft parkour снизу shorts','реакция стримера геймплей shorts русский',
# Major youth streamers likely copied by small fan channels
'бустер нарезки shorts','бустер лучшие моменты shorts','бустер реакции shorts','парадеевич нарезки shorts','парадеевич лучшие моменты shorts','парадеевич реакции shorts','мазеллов нарезки shorts','мазеллов лучшие моменты shorts','мазеллов реакции shorts','меллстрой нарезки shorts','меллстрой лучшие моменты shorts','дк нарезки shorts','дк лучшие моменты shorts','дк реакции shorts','кореш нарезки shorts','кореш лучшие моменты shorts','фраметаймер нарезки shorts','фраметаймер лучшие моменты shorts','эvelone нарезки shorts русский','эвелон нарезки shorts','эдисон нарезки shorts','домер нарезки shorts','нео нарезки minecraft shorts','пятерка нарезки shorts minecraft','винди нарезки shorts','мокривский нарезки shorts',
# Podcast/interview source farms
'вписка нарезки shorts','вписка лучшие моменты shorts','вдудь нарезки shorts маленький канал','тиньков нарезки shorts канал','хованский нарезки shorts канал','поперечный нарезки shorts канал','50 вопросов нарезки shorts','без души нарезки shorts','подкаст нарезки тикток стиль shorts','подкаст клипы с геймплеем shorts','интервью клипы minecraft parkour shorts','разговорный контент gameplay bottom shorts русский',
# Format terms and games
'minecraft parkour storytime русский shorts','minecraft parkour reddit stories русский shorts','subway surfers истории русский shorts','subway surfers разговор русский shorts','gta parkour интервью shorts русский','майнкрафт паркур истории shorts русский','майнкрафт паркур факты shorts русский','майнкрафт паркур подкаст shorts','minecraft parkour подкаст русский','геймплей снизу субтитры shorts русский','два видео одновременно shorts русский','split screen shorts русский подкаст','сверху человек снизу майнкрафт shorts','сверху подкаст снизу игра shorts',
]

q.main()
