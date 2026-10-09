# 칠한 화면 그림 미리보기:  python tools/prevscreen.py 화면 [출력]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art
from PIL import Image
name = sys.argv[1]
cv, parts = art.screen_canvas(name)
im = cv.image()
im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(sys.argv[2] if len(sys.argv) > 2 else 'tools/prev_%s.png' % name)
