# 과제2 · 에이전트와 함께 만드는 URL 단축기

2026-2 **고급알고리즘**(SIT2001-01) 과제2의 **시작 저장소**입니다.
채팅창에 묻고 복사·붙여넣기 하던 방식에서 벗어나, Codespace 안의 에이전트가
저장소를 읽고, 파일을 고치고, 테스트를 직접 돌리게 하는 방법을 익힙니다.

- 과제 안내: [lec-algorithm.github.io/lecture/article/hw2-2026](https://lec-algorithm.github.io/lecture/article/hw2-2026/)
- 수업 슬라이드: [lec-algorithm.github.io/lecture/slides/hw2-2026](https://lec-algorithm.github.io/lecture/slides/hw2-2026/)
- 해시 테이블 복습: [주제 08 해시 테이블](https://lec-algorithm.github.io/lecture/course/topic-08-hashing/)

## 시작하기

1. 이 저장소 상단의 **Use this template** → **Create a new repository**
2. 저장소 이름은 `algorithms-hw2`처럼 정합니다. 공개(Public)로 만듭니다.
3. 만들어진 **내 저장소**에서 **Code** → **Codespaces** 탭 → **Create codespace on main**
4. 왼쪽 막대의 Copilot 아이콘을 눌러 채팅 창을 열고, 창 아래쪽에서 **Agent** 모드를 고릅니다.

## 들어 있는 것

| 파일 | 하는 일 |
| --- | --- |
| `SPEC.md` | 구현과 테스트의 기준이 되는 과제 명세 |
| `src/` | Base62, 체이닝·선형 탐사 해시 테이블, URL 단축기와 웹 서버 |
| `tests/` | 두 해시 테이블 방식, URL 단축기, 웹 서버와 실험 테스트 |
| `experiments/` | 충돌·탐사 횟수 실험 및 비교 결과와 그래프 |
| `tools/catchup.sh` | 수업 중 놓친 단계를 따라잡는 스크립트 |
| `Makefile` | 테스트, 서버, 해시 테이블 실험 실행 명령 |

현재 저장소에는 위 기능의 구현과 테스트가 들어 있습니다. 과제 명세와 테스트를
기준으로 구현을 확인하고, 실험 명령으로 결과를 다시 생성할 수 있습니다.

## 명령

컨테이너 안(Codespaces 터미널)에서 실행합니다.

| 하고 싶은 것 | 명령 |
| --- | --- |
| 테스트 | `make test` |
| 웹 서버 - 체이닝 (포트 8000) | `make serve` |
| 웹 서버 - 선형 탐사 (포트 8000) | `make serve STRATEGY=linear-probing` |
| 충돌 실험 | `make experiment` |
| 체이닝·선형 탐사 비교 | `make experiment-compare` |
| 놓친 단계 따라잡기 | `sh tools/catchup.sh <단계 번호>` |

외부 라이브러리는 쓰지 않습니다. Python 표준 모듈만으로 충분합니다.

## 로컬에서 하기

```sh
git clone https://github.com/<본인 계정>/<내 저장소>.git
cd <내 저장소>
docker compose up -d
docker compose exec lab bash
```

**이후 모든 `docker compose` 명령은 이 폴더에서 칩니다.**
