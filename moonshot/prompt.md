# 학생용 연구 파이프라인을 준비해 주세요

첨부한 pipeline.zip을 사용해 내가 선택한 작업 폴더 안에 research-workshop을 만들고, 합성 걷기 사례를 실행해 주세요. 설치 설명을 길게 안내하지 말고 직접 파일·실행 작업을 진행해 주세요.

1. 로컬 파일을 읽고 쓸 수 있는 에이전트 모드인지 확인하세요. 일반 채팅이면 research-brief.md 작성부터 도와주고, 실제 파일 작업이 가능한 앱 모드에서 이어갈 수 있도록 필요한 한 단계만 안내하세요.
2. 작업할 상위 폴더가 이미 선택돼 있으면 그 안에 새 폴더를 만드세요. 아니라면 앱의 폴더 선택을 한 번 안내하세요. 이 요청은 해당 폴더 안의 압축 해제·환경 준비·합성 예제 실행을 허용합니다. 기존 파일은 덮어쓰지 마세요.
3. ZIP SHA256이 `175eb9e97efeea0695203dc11ef1cb0c2c6193bb5ebaa9d9d1f11a3e7a68c81e`인지 확인하세요. 정확한 멤버 `research-workshop/install.py`를 임시 폴더에 꺼내고 SHA256 `43f1b2e9c7f7fd9f9724a12bf480033c9959dd8c16a8655f6f4199c50c99ca6e`를 확인하세요. Python 3.11 이상이 실제 실행되는지 점검하세요. 없으면 ZIP의 RUNTIME_BOOTSTRAP.md와 runtime.json에 있는 사용자 범위 런타임 절차를 사용하세요. 이 과정의 다운로드·압축 해제·환경 설정은 당신이 수행하세요.
4. install.py --zip <ZIP 경로> --workspace <선택된 상위 폴더> --sha256 175eb9e97efeea0695203dc11ef1cb0c2c6193bb5ebaa9d9d1f11a3e7a68c81e 를 준비된 Python으로 실행하세요. 설치 도구는 모든 ZIP 멤버 경로와 파일 해시를 검증합니다.
5. research-workshop/START_HERE.md와 AGENTS.md를 읽고 lesson.py doctor, demo, verify를 실행하세요. 실제 생성된 table1.csv, figure1.svg, results.md, claims.csv, review-decisions.csv, manuscript.docx, RUN_MANIFEST.json을 열어 보여 주세요. 검산 실패나 실행 불가를 완료로 말하지 마세요.
6. 결과를 보여주기 전 나에게 “이 표로 무엇을 말할 수 있고, 무엇은 말할 수 없을까요?”라고 묻고, 답을 받은 뒤 비교해 주세요. 내 질문을 정리할 templates/research-brief.md도 복사해 주세요.
7. 내가 실제 자료 분석을 선택할 때만 StatSam 선택 도구를 준비하세요. 강의 기본 사례와 방법·결과가 다른 분석을 섞지 마세요. 내 자료나 원문을 외부 모델에 자동 전송하지 마세요.

모든 자료는 교육용입니다. 실제 저널 투고나 저자·기관의 동의를 완료한 것으로 표시하지 마세요. 내 주제로 이어갈 때 필요한 결정과 다음 요청 문장을 짧게 알려 주세요.
