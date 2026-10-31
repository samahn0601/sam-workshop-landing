# demo/ — 걷기 앱 알림 연구 6단계 오프라인 시연 (합성 데이터)

단국대 「AI를 활용한 디지털헬스케어 분야 논문작성」 온라인 강의(60분)에서 설치 없이 화면으로 보여 주는 교육 시연이다.
사례는 **"대학생에게 걷기 앱 알림을 보내면 걸음수가 늘까?"** 라는 가상의 무작위 비교 연구이고, 데이터·결과·AI 응답은 모두 교육용으로 만든 것이다.

> 화면 상단에 항상 보이는 문구: **합성 데이터로 만든 시연 · 실시간 AI 응답 아님**

## 이것은 무엇이고, 무엇이 아닌가

| 이것은 | 이것이 아닌 것 |
|---|---|
| `index.html` 한 파일로 열리는 오프라인 시연(외부 폰트·CDN·fetch·API 없음) | 실시간 AI 세션. 화면의 "AI 응답"은 미리 써 둔 **시연용 고정 응답**이다 |
| 40명(알림군 20·대조군 20)의 **합성** 걸음수 자료와, 그 자료를 **스크립트가 실제로 계산**한 표·그림 | 실제 참여자·실제 앱·실제 효과. 무작위 배정 라벨이 있어도 합성 자료이므로 임상적 결론은 없다 |
| 질문 → 분석 계획 → 데이터·표 → 초안 → 비평·저자 결정 → 수정·패키지 미리보기의 6단계 | 저널별 모든 검증을 갖춘 투고 도구. 패키지 미리보기는 교육용 축약판의 예시다 |
| 학생이 각 단계에서 "AI에게 요청 → 표시된 출력 → 내가 확인할 것"을 보는 화면 | 설치·터미널·파이썬·압축 해제 실습. 파이프라인 다운로드는 **수업 뒤 선택 자료**이고 이 강의에서 가르치지 않는다 |

"AI가 계산한 숫자"라는 표현은 쓰지 않았다. 숫자는 `compute_case.py`가 계산했고, 브라우저가 평균·SD·차이를 다시 계산해 일치 여부를 화면(3단계)에 표시한다.

## 파일

| 파일 | 역할 |
|---|---|
| `index.html` | 시연 본체. 단일 파일, 오프라인. 안쪽 `<script id="case-data">` 블록에 `case.json`이 주입되어 있다(손으로 고치지 않는다) |
| `synthetic_steps.csv` | **기록된 데이터(data of record)**. 열: `participant_id, group, baseline_steps, followup_steps, change_steps`. 40행 |
| `case.json` | 계산 결과와 원고 예문·비평·덱 자리표시자·참고 링크. `compute_case.py`가 만든다 |
| `compute_case.py` | 생성·계산·주입·검증 스크립트. Python 표준 라이브러리만 사용 |
| `verify_case.mjs` | Node 교차검증. 다른 언어·다른 난수 생성기로 다시 계산해 `case.json`·`index.html`과 대조 |
| `qa/` | 로컬 QA 증거(스크린샷·보고) |
| `README.md` | 이 문서 |

## 여는 법과 조작

- `index.html`을 더블클릭하면 브라우저에서 열린다(Chrome·Edge·Firefox·Safari 최신판). 인터넷이 없어도 된다.
- 1280×720(강의 녹화·화면 공유)에서는 상·하단 바가 고정되고 두 열이 각각 스크롤된다. 390px 폭(휴대전화)에서는 한 열로 쌓인다.
- 키보드: `←` `→` 단계 이동, `1`~`6` 바로 가기, `Home`/`End`, `T` 6단계 문장 토글, `?` 단축키 안내, `Esc` 닫기. 체크·선택·펼치기는 `Tab`·`Space`·`Enter`로 조작한다. 입력 칸에 커서가 있으면 단계 이동 단축키가 꺼진다.
- 딥링크: `index.html#step-3` 처럼 열면 그 단계부터 보인다. 현재 단계는 `body[data-step]`, `.step.is-active[aria-current="step"]`, `#progress` 텍스트에서 읽힌다(자동 캡처·수업 도구용).
- 프롬프트는 각 단계의 입력 칸에서 고쳐 쓸 수 있고 "프롬프트 복사"로 복사한다. 클립보드가 막힌 환경에서는 글을 자동으로 선택해 두고 `Ctrl+C` 안내를 띄운다. "원래 문구로"가 기본 문구를 되돌린다.
- 20초 생각(1·4·6단계): 시작·일시정지·초기화. 끝나면 "정답 예시 보기"를 펼친다. 움직임은 유한하고 `prefers-reduced-motion`에서는 애니메이션이 꺼진다.

## 화면 라벨 규약

| 라벨 | 뜻 |
|---|---|
| `시연용 고정 응답 · 실시간 AI 아님` (앰버) | 교육용으로 미리 써 둔 AI 문장. 모델이 지금 만든 것이 아니다 |
| `스크립트 실행 결과 · compute_case.py` (틸) | 실제로 코드가 실행되어 나온 숫자 |
| `합성 자료` | 사람의 자료가 아니다. 숫자가 보이는 모든 곳에 붙인다 |
| 노란 표시 | 표가 뒷받침하지 않는 말(과장) |
| 청록 표시 | 범위를 지키는 말(측정한 것·대상·기간·자료 성격·불확실성) |

## 데이터와 통계가 만들어진 방법

- 생성: `random.Random(20261031)`로 1:1 배정 라벨을 섞고, 기준 걸음수 N(6400, 1400)을 3,000~11,000으로 자르고, 변화량을 알림군 N(+700, 950)·대조군 N(+100, 950)에서 뽑아 10걸음 단위로 반올림했다. 모수와 시드는 실행 전에 정했고 결과를 보고 바꾸지 않았다(`case.json` → `generation`).
- 1차 결과(사전 지정): 변화량(추적 − 기준)의 군 간 평균 차이(알림군 − 대조군).
- 불확실성: **부트스트랩 95% 신뢰구간**(군별 복원추출, 백분위법, B=10,000, 시드 고정). p 값: **순열 검정**(라벨 섞기 B=10,000, 시드 고정), p = (개수+1)/(B+1).
- 참고: Welch t 통계량·자유도·구간도 계산해 두었다. t 임계값은 외운 통계표 값이 아니라 불완전 베타 함수를 수치 계산해 얻었고, 닫힌 형식(df=1 코시분포 `tan`, df=2 닫힌식, df→∞ `erf` 정규)으로만 자가검사한다.
- 2026-10-31 실행값(`case.json` 기준): 알림군 변화 +584.0±968.6, 대조군 −225.0±624.5, 평균 차이 **+809.0걸음/일, 95% CI 332.5~1,313.5(부트스트랩), 순열 p=0.003**(원값 0.0035); 참고 Welch t=3.14, df=32.5, CI 284.4~1,333.6, p=0.004.
- 해석의 한계(시연에서 그대로 가르치는 내용): 측정한 것은 걸음수뿐이다. 4주 이후, 다른 대학·연령, 건강 결과에 대해서는 말할 수 없다. 관찰 연관("앱을 많이 쓴 학생이 더 걸었다")은 효과의 증명이 아니고, 합성 자료의 무작위 배정은 비교 가능성을 설명하는 라벨일 뿐 임상 결론을 만들지 않는다.

## 다시 만들고 검증하는 명령

이 작업 환경에서는 `python3` 별칭이 실패할 수 있어 번들 Python 경로를 쓴다(다른 PC에서는 `python` 또는 `python3`).

```bash
# demo/ 폴더에서
PY="C:/Users/ansan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
rtk proxy "$PY" -X utf8 compute_case.py              # 계산 → case.json → index.html 주입 → 검증 (CSV 는 유지)
rtk proxy "$PY" -X utf8 compute_case.py --verify-only
rtk proxy "$PY" -X utf8 compute_case.py --selftest
rtk proxy "$PY" -X utf8 compute_case.py --regenerate # CSV 를 시드로 다시 만든다 — 의도적으로만

NODE="C:/Users/ansan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
rtk proxy "$NODE" verify_case.mjs                    # 독립 교차검증 (다른 언어·다른 PRNG)
```

검증이 확인하는 것: CSV 재계산 = `case.json`, `index.html` 내장 JSON = `case.json`, 행 40·군별 20·ID 중복 없음, 통계 함수의 닫힌 형식 대조, 다른 PRNG 부트스트랩·순열이 파이썬 값과 허용 오차 안, 외부 리소스 없음, 원고 예문의 숫자가 표시값과 같음.

## 강의 덱에서 가져다 쓰는 값 (`case.json` → `deck_placeholders`)

| 키 | 용도 |
|---|---|
| `DEMO_RESULT` | `{{DEMO_RESULT}}` 자리에 넣는 한 문장(신뢰구간·합성 표기 포함) |
| `DEMO_RESULT_SHORT` | 카드용 짧은 문장 |
| `DEMO_TABLE_ROW_NOTIFICATION` / `DEMO_TABLE_ROW_CONTROL` | 표 1의 두 행 |
| `DEMO_STATS_LINE` | 통계 방법 한 줄 |
| `manuscript.results_paragraph` / `discussion_inflated` / `discussion_bounded` | 결과 문단, 과장 초안, 범위를 지킨 수정문 |
| `critic_findings` | 비평 F1~F4(심각도·문제 문장·이유·고친 예문) |

숫자는 손으로 다시 치지 않고 이 값들을 복사한다. 스크립트를 다시 돌리면 값이 바뀔 수 있으니 덱 조립 시점의 `case_date`와 `generation.seed`를 적어 둔다.

## 참고 링크의 상태

`case.json` → `references`에는 상위 폴더 `references.json`에서 coordinator가 2026-10-31 공식 페이지로 확인한 항목 가운데 이 시연과 직접 맞는 네 개(ICMJE 저자와 기여자 · ICMJE 저자의 AI 사용 · CONSORT 2025(EQUATOR 색인) · CONSORT-EHEALTH(JMIR 2011, DOI 10.2196/jmir.1923))만 제목·URL·요지를 그대로 옮겨 적었다. 화면 6단계에는 "확인 2026-10-31 · coordinator"로 표기된다. 그 밖의 지침(SPIRIT·COPE 등)은 확인되지 않아 넣지 않았다. 실존하지 않는 논문·게재 사실·실제 효능 주장은 어디에도 없다.

## 로컬 QA 증거 (2026-10-31)

**자동 QA** — `qa/run_qa.mjs`를 번들 Playwright 1.62.1(Chromium)로 돌려 `index.html`을 `file://`로 열었다. **62개 확인 모두 통과.** 보고서 `qa/qa_report.json`, 스크린샷 `qa/shots/` 12장(`desktop-step1~6`, `desktop-step5-decided`, `desktop-step6-bounded`, `mobile-step1`, `mobile-step3`, `mobile-step6`, `mobile-deeplink-step3`).

| 영역 | 확인한 것 |
|---|---|
| 오류·외부 의존 | 콘솔·페이지 오류 0, 외부 네트워크 요청 0, 데이터 주입 오류 배너 숨김, 브라우저 재계산 배지 `pass` |
| 키보드 | `→` `←` `1`~`6` `Home` `End`로 단계 이동과 제목 포커스, 입력 칸 안에서는 꺼짐, `T` 토글, `Space`로 세그먼트·라디오·체크박스, `Enter`로 정답 펼치기, `?`/`Esc` 안내 |
| 상호작용 | 복사 버튼 상태 문구(헤드리스에서는 대체 경로 "복사됨 (대체 방식)"), 결정 기록 0/4 → 4/4와 기각 사유 표시, 20초 타이머 시작·일시정지·초기화 |
| 내용 | 3단계 KPI에 +809.0과 332.5~1,313.5, 요약표 3행, 원자료 40행, 그림 점 40개, 그림 `aria-label`에 합성 표기, 수정문에 신뢰구간·청록 표식, 초안에 노란 표식 |
| 390×844 | 오류 0, 1·3·6단계 가로 스크롤 없음, 단계 버튼·다음 버튼 탭, 토글 탭, 딥링크 `#step-3` 로드 후 헤더(합성 배지)가 맨 위에 보임 |
| 모션 줄이기 | `prefers-reduced-motion`에서 점 애니메이션 클래스 제거, 타이머 링 전환 0s |

**수동 확인** — Playwright MCP로 localhost 임시 서버(QA 뒤 종료)에서 1280×720과 390 폭을 열어 봤다. 스크린샷 `qa/mcp-*.png`.

**발견해서 고친 결함 2건**
1. 390 폭에서 표의 `nowrap` 때문에 그리드 열이 650px로 넓어져 페이지가 가로로 넘쳤다(`qa/mcp-mobile-step3-debug.png`). 그리드 트랙·항목에 `min-width:0`을 주어 표만 컨테이너 안에서 가로 스크롤되게 했다(`qa/mcp-mobile-step3-fixed.png`).
2. 처음 열 때 `#step-N` 해시를 바로 써서 브라우저가 섹션 위치로 약 100px 스크롤했고 상단 배지가 가려졌다. 초기 로드에서는 해시를 쓰지 않고 `.step{scroll-margin-top:140px}`을 두어 딥링크로 열어도 배지가 보이게 했다(`qa/mcp-mobile-deeplink-step3-final.png`, 자동 QA 항목 "딥링크 로드 후 헤더 보임").

**데이터 검증** — `compute_case.py --verify-only` PASS(닫힌 형식 자가검사, CSV 재계산 일치, HTML 내장 JSON 일치, 행 40·군별 20·ID 중복 없음). `verify_case.mjs` PASS(35항목; 다른 난수 생성기의 부트스트랩 334.5~1,311.5 vs 파이썬 332.5~1,313.5, 순열 p 0.0039 vs 0.0035). CSV는 처음 생성 뒤 다시 만들지 않았다.

**다시 돌리기** — `node qa/run_qa.mjs` (다른 PC에서는 `PW_MODULES`에 Playwright가 있는 `node_modules` 경로를 넣는다). 자동 QA는 Chromium만 돌렸으므로 Firefox·Safari는 수업 전에 한 번 손으로 연다.

## 알려진 한계

- `file://`로 열었을 때 일부 브라우저는 클립보드 쓰기를 막는다. 그때는 글을 자동 선택하고 `Ctrl+C` 안내를 띄운다.
- 체크·결정·사유 입력은 화면을 새로 고치면 사라진다(저장하지 않는다). 수업용 상태 표시일 뿐 기록 장치가 아니다.
- `<dialog>`(단축키 안내)는 2022년 이후 브라우저에서 동작한다. 그 이전 브라우저에서는 단축키 안내 버튼만 동작하지 않고 나머지는 그대로 쓸 수 있다.
- 인쇄(`Ctrl+P`)하면 6단계가 모두 펼쳐져 쪽마다 나온다.

## 바꾸지 말 것

- `index.html`의 `<script id="case-data">` 블록을 손으로 고치지 않는다. `compute_case.py`가 다시 쓴다.
- `synthetic_steps.csv`는 기록된 데이터다. 바꾸려면 `--regenerate`를 의도적으로 쓰고, 덱의 숫자도 함께 바꾼다.
- 이 폴더는 `work/dku-digital-health-online-20261031/demo/`에만 있다. 다른 작업자의 `editorial/`은 이 시연이 건드리지 않는다.
