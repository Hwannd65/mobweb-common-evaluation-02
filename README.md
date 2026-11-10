# 공통평가 02 침입자 감시 시스템

YOLOv5가 새로 검출한 객체의 이미지와 게시물을 Django 서버에 보내고, Android 앱이 서버의 이미지를 조회한다. 공통평가 01 결과물을 복사하여 확장한 별도 제출 저장소다.

## 구성

```text
PhotoBlogServer/   Django 서버 및 REST API
PhotoViewer/       Android 클라이언트 (PhotoViewer 02)
YOLOv5/            YOLOv5 및 검출 변화 전송 코드
captures/          보고서에 포함한 실제 실행 캡처 원본
deployment/        PythonAnywhere 설정 및 배포 기록
공통평가 02 수행 결과 보고서.docx
```

루트의 Word 문서는 교수님 양식을 사용하며, 각 항목의 `관련증빙` 칸에 캡처를 포함한다. 보고서의 실제 파일명은 `모바일웹서비스 프로젝트_공통평가 02_수행 결과 보고서.docx`다.

## 데이터 흐름

아이폰 카메라 → YOLOv5 검출 → 객체 종류의 등장 변화 확인 → 테두리가 있는 JPEG(320×240) 저장 → 토큰 인증으로 Django에 게시물·이미지 전송 → 웹 목록 및 Android Sync에서 조회한다.

- 로그인: `POST /api-token-auth/`
- 게시물 및 이미지 등록: `POST /api_root/Post/` (multipart, `Authorization: Token …`)
- 게시물 조회: `GET /api_root/Post/`
- 웹 목록: `/`
- 배포 서버: <https://hwannd65mid.pythonanywhere.com>

## 로컬 Django 실행

검증 환경은 macOS, Python 3.13.16이다. 가상환경, 개인 비밀키, 사용자 DB 및 실행 중 생성된 이미지는 Git에 포함하지 않는다. 새로 내려받으면 DB와 계정을 먼저 만든다.

```bash
cd PhotoBlogServer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp mysite/local_settings.example.py mysite/local_settings.py
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

`local_settings.example.py`의 키는 로컬 실습용 공개 예시다. 배포에서는 `DJANGO_SECRET_KEY` 환경변수에 별도의 비밀키를 제공한다. 기존 로컬 설정 파일이 있는 경우 덮어쓰지 않는다.

## YOLOv5 실행

YOLOv5 원본은 [Ultralytics YOLOv5](https://github.com/ultralytics/yolov5)의 커밋 `0a85386d269bf8b49873a24591491c1a4b7024a8`을 기반으로 한다. 원본의 라이선스와 출처를 `YOLOv5/`에 유지했다. 핵심 추가 코드는 `changedetection.py`와 `detect.py`의 전송 연결 부분이다.

`ChangeDetection`은 강의자료 8~10쪽의 `__init__`, `add`, `send` 구조와 변수 이름을 따른다. `add`는 이전 프레임의 0과 현재 프레임의 1을 비교하고, 새로 나타난 종류가 있으면 한 번 전송한다. 여러 종류가 새로 나타나면 강의자료처럼 제목은 마지막 종류, 본문은 새 종류 전체가 된다. `detect.py`는 11쪽의 검출 배열 생성·종류 표시·`cd.add(names, detected, save_dir, im0)` 호출을 연결한다.

실행 환경에 맞춘 차이는 다음과 같다. 서버의 인증 방식에 맞춰 `JWT` 대신 `Token`을 사용하고, 실제 계정은 실행할 때 입력하며 토큰을 출력하지 않는다. 이미지 경로는 `pathlib.Path`로 만들고 OpenCV에는 문자열 경로를 전달한다. 서버 주소 선택, 요청 시간 제한, 파일 닫기 및 성공·실패 확인도 포함한다. 날짜 필드는 강의자료처럼 전송하지만 현재 서버에서는 서버 시각으로 생성한다.

```bash
cd YOLOv5
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
export YOLO_CONFIG_DIR="$VIRTUAL_ENV/.config/ultralytics"
export MPLCONFIGDIR="$VIRTUAL_ENV/.cache/matplotlib"
export XDG_CACHE_HOME="$VIRTUAL_ENV/.cache"
python detect.py --weights yolov5s.pt --source 1 --device cpu
```

`yolov5s.pt`는 Git에 포함하지 않는다. 없으면 YOLOv5가 공식 릴리스에서 내려받는다. 위 명령은 전송 기능을 켜지 않는 기본 검출 실행이다. 수정 전 기본 실행 증빙은 `captures/03_default_command.png`와 `03_default_detection.png`에 보존했다.

이 Mac에서 아이폰 연속성 카메라는 `--source 1`로 확인했다. 다른 컴퓨터의 카메라 번호는 다를 수 있다. 카메라 권한은 실행에 사용하는 터미널 앱에 허용한다.

로컬 서버로 전송할 때는 아래 명령을 사용한다. Django 서버는 별도 터미널에서 실행해야 한다. 사용자명과 비밀번호는 실행 후 입력하고, 코드에 저장하지 않는다.

```bash
python detect.py --weights yolov5s.pt --source 1 --device cpu --upload --nosave --classes 0 --conf-thres 0.6
```

클라우드로 전송할 때는 다음을 사용한다. 로컬과 클라우드는 계정과 DB가 별도다.

```bash
python detect.py --weights yolov5s.pt --source 1 --device cpu --upload --nosave --classes 0 --conf-thres 0.6 --server-url https://hwannd65mid.pythonanywhere.com
```

`Django post created: id=...`가 나오면 게시물 생성에 성공한 것이다. `--classes 0`은 사람만 검출하는 이번 실습 설정이며, 객체 종류 필터를 제거하면 다른 종류도 처리한다. `--nosave`는 기본 검출 동영상 저장을 생략하며, 전송용 JPEG는 `runs/detect/exp*/detected/날짜/`에 남긴다. 영상 창에서 Q를 눌러 종료한다.

## 추가 편의 기능 2개

**짧은 미검출에 따른 중복 게시물 방지.** 기본값은 `--absence-seconds 0`이며 강의자료의 프레임 단위 변화 방식을 그대로 사용한다. 편의 기능을 켜려면 위 전송 명령 뒤에 `--absence-seconds 2`를 추가한다. 그러면 별도 `StablePresence`가 2초 미만의 미검출을 보정한 뒤 기본 `ChangeDetection.add`에 검출 배열을 넘긴다. 2초 연속 미검출 후 다시 나타나면 한 번 더 전송한다. 2초는 교수님이 지정한 값이 아니다.

이 보정 규칙은 앞선 실제 카메라 테스트에서 정지 상태의 추가 전송이 멈추고, 화면을 나갔다 돌아왔을 때 한 장 더 등록됨을 확인한 규칙이다. 분리한 현재 코드에서도 자동 테스트로 검증했다. 통신 실패 시 오류를 표시하고 실행이 중단되며, 먼저 저장한 이미지는 로컬에 남는다. 서버 연결을 확인한 뒤 다시 실행한다.

**미확인 사진 표시.** Android 목록에 현재 표시된 미확인 사진 수와 사진별 확인 버튼을 제공한다. 확인 완료를 누르면 해당 사진의 게시물 ID를 기기의 SharedPreferences에 저장하며, 서버 주소와 로그인 계정별로 구분한다. 앱 재실행 후 같은 계정으로 로그인하고 동기화하면 확인 상태가 유지된다. 검색 중 개수는 현재 검색 결과를 기준으로 한다. 기기 간 확인 기록 동기화는 지원하지 않는다.

01에서 가져온 기존 기능은 유지했으며, 02의 추가 편의 기능으로 중복 계산하지 않았다.

## Android 실행

Android Studio에서 `PhotoViewer`를 연다. 기존 01 앱과 구분되는 앱 ID `com.example.photoviewer.evaluation02`, 앱 이름 `PhotoViewer 02`를 사용한다.

로컬 에뮬레이터의 서버 주소 기본값은 `http://10.0.2.2:8000`이다. 클라우드용 빌드는 아래와 같다.

```bash
cd PhotoViewer
./gradlew assembleDebug -PphotoBlogUrl=https://hwannd65mid.pythonanywhere.com
```

실행 후 Sync를 누르면 서버의 이미지를 갱신한다. 실물 Android 기기에서 로컬 서버에 연결하려면 기기에서 접근 가능한 서버 주소를 빌드 속성으로 지정해야 한다.

## 검증

- Django 기존 기능 테스트 76개 통과
- 검출 변화·로그인·전송의 집중 테스트 12개 통과
- 기본 검출 실행 및 실제 아이폰 사람 검출 확인
- 로컬 서버에 실제 검출 이미지 등록·조회 확인
- PythonAnywhere에 실제 검출 이미지 등록·웹 표시 확인
- Android의 표시 이미지와 서버의 실제 이미지가 같은지 로컬·클라우드 연결 테스트 통과

```bash
# PhotoBlogServer 가상환경
python manage.py test blog
# YOLOv5 가상환경
python -m unittest discover -s tests -p test_changedetection.py -v
# PhotoViewer (에뮬레이터 실행 필요)
./gradlew connectedDebugAndroidTest -PphotoBlogUrl=https://hwannd65mid.pythonanywhere.com -Pandroid.testInstrumentationRunnerArguments.class=com.example.photoviewer.IntruderImageSyncTest
```

배포 상세는 `deployment/DEPLOYMENT.txt`를 참고한다. PythonAnywhere 무료 웹앱은 관리 화면에 표시된 만료일 전에 갱신해야 한다. 이 저장소의 업로드와 LMS의 제출은 별개이며, LMS에 이 저장소 URL을 제출해야 한다.
