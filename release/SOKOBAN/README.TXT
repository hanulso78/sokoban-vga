소코반 (SOKO-BAN) - 1988년 원판 그대로

  1988년 Spectrum HoloByte 판 소코반(SKB.EXE)을 역어셈블해서 C 로 옮긴 판입니다.
  원판 명령을 하나하나 C 로 옮겼기 때문에 게임은 원판과 똑같이 움직입니다.
  (옮긴 결과는 에뮬레이터로 돌린 원판과 인터럽트 단위로 대조했습니다)
  화면은 VGA 로 보여 주지만 색은 원판과 같은 CGA 4색 / Tandy 16색입니다.

시작할 때 묻는 것
  ENTER YOUR SYSTEM   C = IBM CGA,  T = Tandy   (치고 Enter)
  J <JOYSTICK> or K <KEYBOARD>   보통 K         (치고 Enter)

하는 법
  첫 화면에서 Enter -> 로비에서 PLAY 엘리베이터 앞에서 Enter
  -> 선수 이름을 치고 Enter, 빈 칸에서 한 번 더 Enter (혼자 하기)
  -> 엘리베이터에서 층(단계) 번호를 누르고 A (Accept)
     C = 지우기, L = 로비로
  로비의 EDIT 엘리베이터 = 단계 편집기,  EXIT 문 = 끝내기

판에서 쓰는 키
  화살표   움직이기 / 상자 밀기
  U        한 수 되돌리기          F1   이 단계 처음부터
  P        일시정지 (기록 보기, 게임 저장)
  F2       소리 켜기/끄기          F3   이 단계 기록 지우기
  Esc      판에서 나가기

실행
  DOSBox 나 도스에서 이 폴더로 가서  SOKOBAN  이라고 칩니다.

이 폴더의 파일
  SOKOBAN.EXE    게임
  CWSDPMI.EXE    도스에서 32비트로 돌리기 위한 DPMI 서버 (같이 있어야 합니다)
  나머지         원판 자료 파일 (그림, 단계 TABxxxx, 편집 단계 EDTxxxx,
                 기록 MOVE/PUSH/TIME/SCORE/NAMES)

  자료 파일과 기록은 원본 배포판(1987~1990) 그대로입니다.
