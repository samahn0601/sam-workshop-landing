#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_case.py — 단국대 '디지털헬스케어 논문작성' 온라인 강의 시연용
합성 데이터 생성 · 통계 계산 · 검증 스크립트 (Python 표준 라이브러리만 사용, 외부 패키지 없음)

이 스크립트가 하는 일
  1. generate : 고정 시드로 40명(알림군 20 · 대조군 20)의 합성 걸음수 자료를 만들어
                synthetic_steps.csv 에 쓴다. 이미 있으면 --regenerate 없이는 다시 만들지 않는다.
                CSV 가 '기록된 데이터(data of record)' 다.
  2. compute  : CSV 를 읽어 군별 n·평균·SD, 1차 결과(변화량의 군 간 평균 차이)를 계산한다.
                불확실성 구간은 **결정적 부트스트랩 95% 신뢰구간(백분위법, B=10,000, 시드 고정)**,
                p 값은 **순열 검정(B=10,000, 시드 고정)** 으로 구한다. 둘 다 표준 라이브러리만 쓴다.
                참고용으로 Welch t 통계량·자유도·구간도 계산하지만, t 임계값은 외운 표 값을 쓰지 않고
                불완전 베타 함수를 수치 계산해서 얻으며, 닫힌 형식(df=1 코시, df=2, df→∞ 정규)으로만 자가검사한다.
                원고 예문(결과 문단 · 과장된 논의 · 범위를 지킨 논의)도 숫자를 넣어 생성해 case.json 에 쓴다.
  3. inject   : index.html 의 <script id="case-data" type="application/json"> 블록을 case.json 으로 바꾼다.
                (오프라인 단일 파일이라 fetch 를 쓰지 않는다.)
  4. verify   : CSV 에서 다시 계산한 값이 case.json 과 같은지, index.html 안의 JSON 이 case.json 과 같은지 확인한다.
                하나라도 다르면 종료 코드 1.
  5. selftest : 통계 함수의 닫힌 형식 대조 검사.

중요한 표기 원칙
  - 이 자료는 교육용 합성 데이터다. 실제 참여자·실제 앱·실제 효과와 무관하다.
  - 숫자는 모두 이 스크립트가 실행해서 얻은 값이다(언어 모델의 암산이 아니다).
  - 무작위 배정 라벨이 있어도 합성 자료이므로 임상적 결론을 내릴 수 없다.

사용법 (번들 Python 또는 python3)
  python compute_case.py              # generate(필요 시) → compute → inject → verify
  python compute_case.py --regenerate # CSV 를 시드로 다시 만든다(의도적으로만)
  python compute_case.py --verify-only
  python compute_case.py --selftest
  python compute_case.py --no-inject  # index.html 을 건드리지 않는다
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from typing import Dict, List, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "synthetic_steps.csv")
CASE_PATH = os.path.join(HERE, "case.json")
HTML_PATH = os.path.join(HERE, "index.html")

# ───────────────────────────── 생성 모수 (실행 전에 고정, 결과를 보고 바꾸지 않음) ─────────────────────────────
SEED = 20261031            # 강의 제작일(2026-10-31)
BOOT_SEED = SEED + 1       # 부트스트랩 재표본용
PERM_SEED = SEED + 2       # 순열 검정용
B_BOOT = 10_000
B_PERM = 10_000
CASE_DATE = "2026-10-31"
N_PER_GROUP = 20
BASE_MEAN, BASE_SD = 6400.0, 1400.0           # 기준 1주 일평균 걸음수
BASE_MIN, BASE_MAX = 3000, 11000
CHANGE_MEAN = {"notification": 700.0, "control": 100.0}   # 추적 − 기준 (생성 모수)
CHANGE_SD = 950.0
FOLLOW_MIN = 1500
GROUP_LABEL = {"notification": "알림군", "control": "대조군"}
GROUP_ORDER = ["notification", "control"]
CSV_COLUMNS = ["participant_id", "group", "baseline_steps", "followup_steps", "change_steps"]


# ───────────────────────────── 1. 데이터 생성 ─────────────────────────────
def _round10(x: float) -> int:
    return int(round(x / 10.0)) * 10


def generate_rows(seed: int = SEED) -> List[Dict]:
    rng = random.Random(seed)
    labels = ["notification"] * N_PER_GROUP + ["control"] * N_PER_GROUP
    rng.shuffle(labels)  # 1:1 무작위 배정(합성 라벨)
    rows = []
    for i, g in enumerate(labels, start=1):
        base = min(max(rng.gauss(BASE_MEAN, BASE_SD), BASE_MIN), BASE_MAX)
        delta = rng.gauss(CHANGE_MEAN[g], CHANGE_SD)
        base_i = _round10(base)
        follow_i = max(FOLLOW_MIN, _round10(base + delta))
        rows.append({
            "participant_id": f"P{i:02d}",
            "group": g,
            "baseline_steps": base_i,
            "followup_steps": follow_i,
            "change_steps": follow_i - base_i,
        })
    return rows


def write_csv(rows: Sequence[Dict], path: str = CSV_PATH) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in CSV_COLUMNS})


def read_csv(path: str = CSV_PATH) -> List[Dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != CSV_COLUMNS:
            raise ValueError(f"CSV 열이 다릅니다: {rd.fieldnames}")
        rows = []
        for r in rd:
            row = {
                "participant_id": r["participant_id"],
                "group": r["group"],
                "baseline_steps": int(r["baseline_steps"]),
                "followup_steps": int(r["followup_steps"]),
                "change_steps": int(r["change_steps"]),
            }
            if row["change_steps"] != row["followup_steps"] - row["baseline_steps"]:
                raise ValueError(f"{row['participant_id']}: change_steps 가 추적−기준과 다릅니다")
            rows.append(row)
    return rows


# ───────────────────────────── 2. 통계 (표준 라이브러리) ─────────────────────────────
def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def sd(xs: Sequence[float]) -> float:
    """표본 표준편차 (n−1)."""
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def quantile_type7(sorted_xs: Sequence[float], q: float) -> float:
    """정렬된 자료의 분위수 (선형 보간, R/numpy 기본형 type 7)."""
    n = len(sorted_xs)
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_xs[lo] * (1.0 - frac) + sorted_xs[hi] * frac


def _idx(rng: random.Random, n: int) -> int:
    """0..n-1 균등 정수. rng.random() 만 써서 파이썬 버전 간 재현성을 높인다."""
    return int(rng.random() * n)


def bootstrap_mean_diff_ci(a: Sequence[float], b: Sequence[float], B: int = B_BOOT,
                           seed: int = BOOT_SEED, conf: float = 0.95) -> Dict:
    """a − b 평균 차이의 부트스트랩(군별 복원추출) 백분위 신뢰구간. 결정적(시드 고정)."""
    rng = random.Random(seed)
    na, nb = len(a), len(b)
    diffs = []
    for _ in range(B):
        sa = sum(a[_idx(rng, na)] for _ in range(na)) / na
        sb = sum(b[_idx(rng, nb)] for _ in range(nb)) / nb
        diffs.append(sa - sb)
    diffs.sort()
    alpha = 1.0 - conf
    return {"lo": quantile_type7(diffs, alpha / 2.0), "hi": quantile_type7(diffs, 1.0 - alpha / 2.0),
            "B": B, "seed": seed, "method": "percentile"}


def bootstrap_mean_ci(a: Sequence[float], B: int, seed: int, conf: float = 0.95) -> Tuple[float, float]:
    """단일 군 평균의 부트스트랩 백분위 신뢰구간(그림 오차막대용). 결정적."""
    rng = random.Random(seed)
    n = len(a)
    ms = sorted(sum(a[_idx(rng, n)] for _ in range(n)) / n for _ in range(B))
    alpha = 1.0 - conf
    return quantile_type7(ms, alpha / 2.0), quantile_type7(ms, 1.0 - alpha / 2.0)


def permutation_p(a: Sequence[float], b: Sequence[float], B: int = B_PERM, seed: int = PERM_SEED) -> Dict:
    """군 라벨을 무작위로 섞어 |평균 차이| 가 관측값 이상인 비율. (count+1)/(B+1). 결정적."""
    rng = random.Random(seed)
    pooled = list(a) + list(b)
    na, n = len(a), len(pooled)
    obs = abs(mean(a) - mean(b))
    count = 0
    for _ in range(B):
        # Fisher–Yates, rng.random() 기반
        for i in range(n - 1, 0, -1):
            j = int(rng.random() * (i + 1))
            pooled[i], pooled[j] = pooled[j], pooled[i]
        d = abs(sum(pooled[:na]) / na - sum(pooled[na:]) / (n - na))
        if d >= obs - 1e-12:
            count += 1
    return {"p": (count + 1) / (B + 1), "B": B, "seed": seed, "count_ge": count}


# ── 참고용 Welch t: 임계값은 외운 표 값이 아니라 불완전 베타 함수를 수치 계산해서 얻는다 ──
def _betacf(a: float, b: float, x: float, max_iter: int = 500, eps: float = 3e-15) -> float:
    """정규화 불완전 베타 함수의 연분수 전개(수정 Lentz 법)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """정규화 불완전 베타 I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
           + a * math.log(x) + b * math.log(1.0 - x))
    bt = math.exp(lbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    """스튜던트 t 분포에서 |T| ≥ |t| 일 양측 확률."""
    x = df / (df + t * t)
    return betai(df / 2.0, 0.5, x)


def t_cdf(t: float, df: float) -> float:
    p_tail = 0.5 * t_two_sided_p(abs(t), df)
    return 1.0 - p_tail if t >= 0 else p_tail


def t_quantile(p: float, df: float) -> float:
    """상측 분위수 (0.5 < p < 1). CDF 를 이분법으로 뒤집는다. 표 값을 쓰지 않는다."""
    if not (0.5 < p < 1.0):
        raise ValueError("p 는 (0.5, 1) 범위")
    lo, hi = 0.0, 1000.0
    for _ in range(400):
        mid = (lo + hi) / 2.0
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2.0


def normal_quantile_erf(p: float) -> float:
    """표준정규 분위수. math.erf 기반 CDF 를 이분법으로 뒤집는다(닫힌 형식 대조용)."""
    lo, hi = 0.0, 40.0
    for _ in range(300):
        mid = (lo + hi) / 2.0
        if 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0))) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def welch_reference(a: Sequence[float], b: Sequence[float], conf: float = 0.95) -> Dict:
    na, nb = len(a), len(b)
    va, vb = sd(a) ** 2, sd(b) ** 2
    diff = mean(a) - mean(b)
    se = math.sqrt(va / na + vb / nb)
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    t = diff / se
    tcrit = t_quantile(0.5 + conf / 2.0, df)
    return {"diff": diff, "se": se, "df": df, "t": t, "p": t_two_sided_p(t, df),
            "t_crit": tcrit, "ci": (diff - tcrit * se, diff + tcrit * se)}


def selftest(verbose: bool = True) -> bool:
    """닫힌 형식과 대조한다. 외운 통계표 상수는 쓰지 않는다."""
    ok = True

    def check(name: str, got: float, expect: float, tol: float) -> None:
        nonlocal ok
        good = abs(got - expect) < tol
        ok &= good
        if verbose:
            print(f"  {name}: 계산 {got:.6f} / 닫힌형식 {expect:.6f}  {'OK' if good else 'FAIL'}")

    # df=1 (코시): 분위수 = tan(π(p−½))
    for p in (0.9, 0.975, 0.995):
        check(f"t_quantile(p={p}, df=1) vs tan", t_quantile(p, 1), math.tan(math.pi * (p - 0.5)), 1e-6)
    # df=2: 분위수 = (2p−1)·√2 / √(1−(2p−1)²)
    for p in (0.9, 0.975):
        u = 2 * p - 1
        check(f"t_quantile(p={p}, df=2) vs 닫힌형식", t_quantile(p, 2), u * math.sqrt(2.0) / math.sqrt(1 - u * u), 1e-6)
    # df→∞: 정규 분위수(erf) 와 근사 일치
    check("t_quantile(0.975, df=1e7) vs erf 정규", t_quantile(0.975, 1e7), normal_quantile_erf(0.975), 1e-4)
    # p 값 대칭·경계
    check("two_sided_p(t=0, df=5) = 1", t_two_sided_p(0.0, 5), 1.0, 1e-12)
    check("cdf(1,df=1) = 0.75 (코시)", t_cdf(1.0, 1), 0.75, 1e-9)
    # 기술통계: 손으로 계산 가능한 값
    check("mean([1,2,3,4]) = 2.5", mean([1, 2, 3, 4]), 2.5, 1e-12)
    check("sd([1,2,3,4]) = √(5/3)", sd([1, 2, 3, 4]), math.sqrt(5.0 / 3.0), 1e-12)
    check("quantile_type7([0..10], 0.25) = 2.5", quantile_type7(list(range(11)), 0.25), 2.5, 1e-12)
    # 부트스트랩·순열: 결정성(같은 시드 → 같은 결과)과 상식 범위
    a, b = [1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 3.0, 4.0, 5.0, 6.0]
    bs1 = bootstrap_mean_diff_ci(a, b, B=2000, seed=7)
    bs2 = bootstrap_mean_diff_ci(a, b, B=2000, seed=7)
    good = bs1 == bs2 and bs1["lo"] <= -1.0 <= bs1["hi"]
    ok &= good
    if verbose:
        print(f"  bootstrap 결정성·관측차 포함: [{bs1['lo']:.3f}, {bs1['hi']:.3f}]  {'OK' if good else 'FAIL'}")
    pp1 = permutation_p(a, b, B=1000, seed=7)
    pp2 = permutation_p(a, b, B=1000, seed=7)
    good = pp1 == pp2 and 0.0 < pp1["p"] <= 1.0
    ok &= good
    if verbose:
        print(f"  permutation 결정성·범위: p={pp1['p']:.4f}  {'OK' if good else 'FAIL'}")
    same = permutation_p([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], B=500, seed=3)["p"]
    good = same > 0.5
    ok &= good
    if verbose:
        print(f"  permutation 동일 자료 p>0.5: p={same:.4f}  {'OK' if good else 'FAIL'}")
    return ok


# ───────────────────────────── 3. 사례 JSON 구성 ─────────────────────────────
def r1(x: float) -> float:
    return round(x + 0.0, 1)


def fmt1(x: float) -> str:
    return f"{x:,.1f}"


def fmt_signed1(x: float) -> str:
    return f"{x:+,.1f}"


def fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def describe_group(rows: Sequence[Dict], g: str, seed_offset: int) -> Dict:
    sub = [r for r in rows if r["group"] == g]
    base = [float(r["baseline_steps"]) for r in sub]
    fol = [float(r["followup_steps"]) for r in sub]
    ch = [float(r["change_steps"]) for r in sub]
    lo, hi = bootstrap_mean_ci(ch, B=B_BOOT, seed=BOOT_SEED + 10 + seed_offset)
    return {
        "key": g,
        "label": GROUP_LABEL[g],
        "n": len(sub),
        "baseline": {"mean": r1(mean(base)), "sd": r1(sd(base))},
        "followup": {"mean": r1(mean(fol)), "sd": r1(sd(fol))},
        "change": {"mean": r1(mean(ch)), "sd": r1(sd(ch)),
                   "ci95_bootstrap": [r1(lo), r1(hi)],
                   "min": int(min(ch)), "max": int(max(ch))},
        # 화면 표시용 문자열(브라우저가 다시 반올림하지 않도록 스크립트가 직접 만든다)
        "display": {
            "baseline": f"{fmt1(mean(base))}±{fmt1(sd(base))}",
            "followup": f"{fmt1(mean(fol))}±{fmt1(sd(fol))}",
            "change": f"{fmt_signed1(mean(ch))}±{fmt1(sd(ch))}",
            "change_mean": fmt_signed1(mean(ch)),
            "change_ci95": f"{fmt1(lo)}~{fmt1(hi)}",
        },
    }


def build_case(rows: Sequence[Dict]) -> Dict:
    if len(rows) != 2 * N_PER_GROUP:
        raise ValueError("행 수가 40 이 아닙니다")
    groups = {g: describe_group(rows, g, k) for k, g in enumerate(GROUP_ORDER)}
    if any(groups[g]["n"] != N_PER_GROUP for g in GROUP_ORDER):
        raise ValueError("군별 n 이 20 이 아닙니다")

    ch_i = [float(r["change_steps"]) for r in rows if r["group"] == "notification"]
    ch_c = [float(r["change_steps"]) for r in rows if r["group"] == "control"]
    diff = mean(ch_i) - mean(ch_c)
    bs = bootstrap_mean_diff_ci(ch_i, ch_c)
    perm = permutation_p(ch_i, ch_c)
    wr = welch_reference(ch_i, ch_c)
    lo, hi = bs["lo"], bs["hi"]
    includes_zero = lo <= 0.0 <= hi
    width = hi - lo

    gi, gc = groups["notification"], groups["control"]
    d_s = fmt_signed1(diff)
    lo_s, hi_s = fmt1(lo), fmt1(hi)
    p_s = fmt_p(perm["p"])

    if includes_zero:
        hint = (f"95% 부트스트랩 신뢰구간({lo_s}~{hi_s})이 0을 포함한다. 이 자료만으로는 알림군과 대조군의 "
                f"변화량 차이가 없을 가능성을 배제할 수 없으므로 '효과가 있다'고 쓸 수 없다.")
        claim_core = (f"알림군(n=20)의 일평균 걸음수 변화는 대조군(n=20)보다 평균 {d_s}걸음 컸으나, 95% 신뢰구간"
                      f"({lo_s}~{hi_s}, 부트스트랩)이 0을 포함하여 차이가 없을 가능성을 배제할 수 없었다")
    else:
        hint = (f"95% 부트스트랩 신뢰구간({lo_s}~{hi_s})이 0을 포함하지 않으므로 '알림군의 변화량이 더 컸다'고 말할 수 "
                f"있다. 다만 구간 폭이 {fmt1(width)}걸음으로 넓어 효과의 크기는 불확실하고, 측정한 것은 걸음수뿐이다.")
        claim_core = (f"알림군(n=20)의 일평균 걸음수 변화는 대조군(n=20)보다 평균 {d_s}걸음 더 컸다"
                      f"(95% 신뢰구간 {lo_s}~{hi_s}, 부트스트랩)")

    results_paragraph = (
        f"알림군(n={gi['n']})의 일평균 걸음수는 기준 {fmt1(gi['baseline']['mean'])}±{fmt1(gi['baseline']['sd'])}에서 "
        f"추적 {fmt1(gi['followup']['mean'])}±{fmt1(gi['followup']['sd'])}로, 대조군(n={gc['n']})은 "
        f"{fmt1(gc['baseline']['mean'])}±{fmt1(gc['baseline']['sd'])}에서 {fmt1(gc['followup']['mean'])}±{fmt1(gc['followup']['sd'])}로 "
        f"변하였다(평균±SD, 걸음/일). 변화량(추적−기준)은 알림군 {fmt_signed1(gi['change']['mean'])}±{fmt1(gi['change']['sd'])}, "
        f"대조군 {fmt_signed1(gc['change']['mean'])}±{fmt1(gc['change']['sd'])}였고, 사전에 정한 1차 결과인 변화량의 군 간 평균 차이"
        f"(알림군−대조군)는 {d_s}걸음(95% CI {lo_s}~{hi_s}, 부트스트랩 백분위법 B={B_BOOT:,}; 순열 검정 p={p_s})이었다. "
        f"모든 수치는 교육용 합성 자료에서 계산한 값이다."
    )

    discussion_inflated = (
        f"본 연구는 걷기 앱 알림이 대학생의 신체활동을 유의하게 증진시켜 건강을 개선함을 입증하였다. "
        f"알림군은 대조군보다 일평균 {fmt1(abs(diff))}걸음 더 많이 걸었으며, 이 효과는 지속될 것으로 기대된다. "
        f"따라서 모든 대학생에게 알림 기반 개입을 적용할 수 있음을 시사한다."
    )
    inflated_markers = ["입증하였다", "건강을 개선함", "유의하게", "더 많이 걸었으며", "지속될 것으로 기대된다", "모든 대학생에게"]

    bounded_tail = ("측정한 결과는 걸음수만이므로 건강 결과에 대해서는 말할 수 없고, 4주 이후의 유지 여부와 "
                    "다른 대학·연령의 학생에 대한 일반화도 이 자료의 범위를 넘는다. "
                    "이 자료는 교육용 합성 데이터이므로 실제 효과에 대한 근거가 아니다.")
    discussion_bounded = f"이 교육용 합성 자료에서, 4주 동안 하루 2회 알림을 받은 {claim_core}. {bounded_tail}"
    bounded_additions = ["교육용 합성 자료", "4주 동안", "n=20", "95% 신뢰구간", "걸음수 변화", "걸음수만", "4주 이후",
                         "일반화도 이 자료의 범위를 넘는다", "실제 효과에 대한 근거가 아니다"]
    if includes_zero:
        bounded_additions.append("0을 포함")

    findings = [
        {
            "id": "F1", "severity": "높음",
            "quote": "건강을 개선함을 입증하였다",
            "why": "측정한 결과변수는 일평균 걸음수 하나다. 체중·혈압·기분 같은 건강 결과는 측정하지 않았고, "
                   "'입증'은 단일 소규모 합성 연구가 쓸 수 있는 말이 아니다.",
            "fix": f"\"알림군의 일평균 걸음수 변화가 대조군보다 평균 {d_s}걸음 더 컸다\"처럼 측정한 것만 쓴다.",
        },
        {
            "id": "F2", "severity": "높음",
            "quote": "모든 대학생에게 알림 기반 개입을 적용할 수 있음",
            "why": "한 대학의 40명을 4주 관찰한 자료다. 다른 대학·연령·국가·계절로 일반화할 근거가 없다.",
            "fix": "대상과 기간을 문장 안에 적는다: \"한 대학 재학생 40명을 4주 동안 관찰한 결과이며 다른 집단으로 일반화할 수 없다.\"",
        },
        {
            "id": "F3", "severity": "중간",
            "quote": f"유의하게 … 일평균 {fmt1(abs(diff))}걸음 더 많이 걸었으며",
            "why": "'유의하게'만 쓰면 효과의 크기와 불확실성이 사라진다. 또 비교한 것은 '걸음수'가 아니라 "
                   "'변화량(추적−기준)'의 군 간 차이다.",
            "fix": f"\"변화량의 군 간 차이는 {d_s}걸음(95% CI {lo_s}~{hi_s})\"처럼 구간을 함께 쓰고 비교 대상을 정확히 적는다.",
        },
        {
            "id": "F4", "severity": "중간",
            "quote": "(합성·교육용 자료 표기 없음) / 지속될 것으로 기대된다",
            "why": "숫자가 나오는 모든 곳에 합성 자료임을 적어야 독자가 실제 결과로 오해하지 않는다. "
                   "4주 뒤 유지는 측정하지 않았다.",
            "fix": "\"교육용 합성 자료\"를 첫 문장에 넣고, 유지 효과는 '측정하지 않았다'고 한계에 적는다.",
        },
    ]

    case = {
        "schema": "dku-digital-health-demo-case/2",
        "case_date": CASE_DATE,
        "title": "대학생에게 걷기 앱 알림을 보내면 걸음수가 늘까? — 교육용 합성 사례",
        "disclaimer": {
            "banner": "합성 데이터로 만든 시연 · 실시간 AI 응답 아님",
            "data": "이 자료의 참여자·앱·걸음수는 모두 컴퓨터가 만든 합성값이다. 실제 사람·실제 앱·실제 효과와 무관하다.",
            "randomization": "'무작위 배정'은 설계 설명을 위한 합성 라벨이다. 합성 자료에 무작위 배정이 있어도 임상적 결론은 나오지 않는다.",
            "numbers": "모든 숫자는 demo/compute_case.py 가 실행해서 계산한 값이다. 언어 모델의 암산이 아니다.",
            "ai_text": "시연 화면의 'AI 응답'은 교육용으로 미리 써 둔 고정 문장이다. 실시간 AI 응답이 아니다.",
            "association_vs_causation": "'앱을 많이 쓴 학생이 더 걸었다'는 관찰 연관이고, 연관은 효과의 증명이 아니다. "
                                        "무작위 배정은 비교 가능성을 높이지만, 합성 자료에서는 그조차 교육 예시일 뿐이다.",
        },
        "generation": {
            "script": "demo/compute_case.py",
            "data_of_record": "demo/synthetic_steps.csv",
            "seed": SEED,
            "method": "python random.Random(seed) · shuffle(1:1 배정) · gauss(기준, 변화) · 10걸음 단위 반올림",
            "params": {
                "n_per_group": N_PER_GROUP,
                "baseline_mean": BASE_MEAN, "baseline_sd": BASE_SD,
                "baseline_clip": [BASE_MIN, BASE_MAX],
                "change_mean_by_group": CHANGE_MEAN, "change_sd": CHANGE_SD,
                "followup_min": FOLLOW_MIN,
            },
            "note": "생성 모수는 시드와 함께 실행 전에 정했고 결과를 보고 바꾸지 않았다. 신뢰구간이 0을 포함하는지는 실행 결과에 따른다.",
        },
        "design": {
            "question": "대학생에게 걷기 앱 알림을 보내면 4주 후 일평균 걸음수가 늘까?",
            "population": "한 대학 재학생 40명(합성)",
            "intervention": "걷기 앱 + 하루 2회 알림(아침·오후), 4주",
            "comparator": "같은 걷기 앱, 알림 없음",
            "outcome": "일평균 걸음수 변화(추적 1주 평균 − 기준 1주 평균)",
            "timeline": ["기준 측정 1주", "무작위 배정(합성 라벨)", "중재 4주", "추적 측정 1주"],
            "allocation": "1:1, 20명/군",
            "cannot_answer": ["알림이 '건강'(체중·혈압·기분)을 바꾸는지", "4주 뒤에도 효과가 유지되는지",
                              "다른 대학·연령·국가 학생에게도 같은지"],
        },
        "analysis_plan": {
            "fixed_before_data": CASE_DATE,
            "primary_outcome": "변화량(추적−기준)의 군 간 평균 차이(알림군 − 대조군)",
            "uncertainty": f"95% 신뢰구간 — 부트스트랩 백분위법(군별 복원추출, B={B_BOOT:,}, 시드 고정)",
            "test": f"순열 검정(라벨 섞기 B={B_PERM:,}, 시드 고정) 양측 p",
            "reference": "Welch t 통계량·자유도·구간은 참고로만 보고(임계값은 수치 계산)",
            "report": ["군별 n · 평균 · SD (기준/추적/변화)", "평균 차이와 95% CI", "순열 검정 p"],
            "sample_size": "교육용 합성 예시로 20명/군 고정. 실제 연구는 검정력 계산으로 정한다.",
            "missing": "합성 자료에는 결측이 없다. 실제 연구는 배정대로 분석(ITT)하고 결측 처리 방법을 미리 적는다.",
            "secondary": "기준 걸음수 수준별 차이 — 탐색적. 이번 시연에서는 수행하지 않음.",
        },
        "columns": CSV_COLUMNS,
        "rows": list(rows),
        "groups": groups,
        "primary_result": {
            "outcome": "변화량의 군 간 평균 차이(알림군 − 대조군), 걸음/일",
            "mean_difference": r1(diff),
            "ci95": [r1(lo), r1(hi)],
            "ci95_method": f"부트스트랩 백분위법, 군별 복원추출, B={B_BOOT:,}, seed={bs['seed']}",
            "ci95_width": r1(width),
            "ci_includes_zero": includes_zero,
            "p_permutation": round(perm["p"], 4),
            "p_method": f"순열 검정(라벨 섞기), B={B_PERM:,}, seed={perm['seed']}, p=(개수+1)/(B+1)",
            "welch_reference": {
                "t": round(wr["t"], 3), "df": round(wr["df"], 2), "se": r1(wr["se"]),
                "p_two_sided": round(wr["p"], 4), "ci95": [r1(wr["ci"][0]), r1(wr["ci"][1])],
                "t_crit_0975": round(wr["t_crit"], 4),
                "note": "참고용. 임계값은 불완전 베타 함수를 수치 계산해 얻었고 닫힌 형식으로 자가검사했다(외운 표 값 아님).",
            },
            "interpretation_hint": hint,
            "computed_by": "demo/compute_case.py (Python 표준 라이브러리만 사용)",
            # 화면 표시용 문자열
            "display": {
                "mean_difference": d_s,
                "ci95": f"{lo_s}~{hi_s}",
                "ci95_width": fmt1(width),
                "p_permutation": p_s,
                "B_boot": f"{B_BOOT:,}",
                "B_perm": f"{B_PERM:,}",
                "welch_t": f"{wr['t']:.2f}",
                "welch_df": f"{wr['df']:.1f}",
                "welch_ci95": f"{fmt1(wr['ci'][0])}~{fmt1(wr['ci'][1])}",
                "welch_p": fmt_p(wr["p"]),
            },
        },
        "manuscript": {
            "results_paragraph": results_paragraph,
            "discussion_inflated": discussion_inflated,
            "inflated_markers": inflated_markers,
            "discussion_bounded": discussion_bounded,
            "bounded_additions": bounded_additions,
        },
        "critic_findings": findings,
        "deck_placeholders": {
            "DEMO_RESULT": f"{claim_core}. (교육용 합성 자료)",
            "DEMO_RESULT_SHORT": f"평균 차이 {d_s}걸음 (95% CI {lo_s}~{hi_s}, 부트스트랩; 합성 자료)",
            "DEMO_TABLE_ROW_NOTIFICATION": f"알림군 · n={gi['n']} · 기준 {fmt1(gi['baseline']['mean'])}±{fmt1(gi['baseline']['sd'])} · 추적 {fmt1(gi['followup']['mean'])}±{fmt1(gi['followup']['sd'])} · 변화 {fmt_signed1(gi['change']['mean'])}±{fmt1(gi['change']['sd'])}",
            "DEMO_TABLE_ROW_CONTROL": f"대조군 · n={gc['n']} · 기준 {fmt1(gc['baseline']['mean'])}±{fmt1(gc['baseline']['sd'])} · 추적 {fmt1(gc['followup']['mean'])}±{fmt1(gc['followup']['sd'])} · 변화 {fmt_signed1(gc['change']['mean'])}±{fmt1(gc['change']['sd'])}",
            "DEMO_STATS_LINE": f"95% CI {lo_s}~{hi_s}(부트스트랩 B={B_BOOT:,}) · 순열 검정 p={p_s} · 참고 Welch t={wr['t']:.2f}, df={wr['df']:.1f}",
        },
        # 참고 링크: 상위 폴더 references.json(coordinator 가 2026-10-31 공식 페이지로 확인)에서
        # 이 시연과 직접 맞는 네 항목만 옮겨 적었다. 제목·URL·요지는 그 파일의 값 그대로다.
        "references_source": "work/dku-digital-health-online-20261031/references.json (authors · ai · consort · ehealth)",
        "references": [
            {"id": "authors", "title": "ICMJE · 저자와 기여자", "org": "ICMJE",
             "url": "https://www.icmje.org/recommendations/browse/roles-and-responsibilities/defining-the-role-of-authors-and-contributors.html",
             "supports": "저자는 기여, 작성·비판적 검토, 최종 승인, 책임의 네 조건을 모두 충족한다.",
             "status": "확인 2026-10-31 · coordinator · 공식 페이지"},
            {"id": "ai", "title": "ICMJE · 저자의 AI 사용", "org": "ICMJE",
             "url": "https://www.icmje.org/recommendations/browse/artificial-intelligence/ai-use-by-authors.html",
             "supports": "AI는 저자가 될 수 없으며 인간이 검토·책임지고 사용을 공개한다. 저널 규정에 맞춰 사용 방법을 밝힌다.",
             "status": "확인 2026-10-31 · coordinator · 공식 페이지"},
            {"id": "consort", "title": "CONSORT 2025 · 무작위시험 보고", "org": "EQUATOR Network",
             "url": "https://www.equator-network.org/reporting-guidelines/consort/",
             "supports": "무작위시험 보고를 위한 현재 기본 지침. 연구 설계에 맞는 보고 지침을 고른다.",
             "status": "확인 2026-10-31 · coordinator · EQUATOR 공식 색인"},
            {"id": "ehealth", "title": "CONSORT-EHEALTH · 디지털 개입 보고", "org": "JMIR",
             "url": "https://www.jmir.org/2011/4/e126/", "doi": "10.2196/jmir.1923",
             "supports": "웹·모바일 개입의 구성, 이용 상황, 중도 이탈 등 재현과 해석에 필요한 세부를 보고하는 확장 지침.",
             "status": "확인 2026-10-31 · coordinator · 원 지침 본문"},
        ],
    }
    return case


# ───────────────────────────── 4. 저장 · 주입 · 검증 ─────────────────────────────
def dump_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def write_case(case: Dict, path: str = CASE_PATH) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump_json(case) + "\n")


def load_case(path: str = CASE_PATH) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_OPEN = '<script id="case-data" type="application/json">'
_CLOSE = "</script>"


def _html_block_span(html: str) -> Tuple[int, int]:
    start = html.find(_OPEN)
    if start < 0:
        raise ValueError("index.html 에 case-data 블록이 없습니다")
    body_start = start + len(_OPEN)
    end = html.find(_CLOSE, body_start)
    if end < 0:
        raise ValueError("case-data 블록이 닫히지 않았습니다")
    return body_start, end


def inject_html(case: Dict, path: str = HTML_PATH) -> None:
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    a, b = _html_block_span(html)
    payload = dump_json(case).replace("</", "<\\/")  # </script> 조기 종료 방지 (JSON 에서 \/ 는 / 와 같다)
    new_html = html[:a] + "\n" + payload + "\n" + html[b:]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_html)


def extract_html_case(path: str = HTML_PATH) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    a, b = _html_block_span(html)
    return json.loads(html[a:b])


def verify(csv_path: str = CSV_PATH, case_path: str = CASE_PATH, html_path: str = HTML_PATH) -> bool:
    ok = True
    print("[verify] 통계 함수 자가검사(닫힌 형식 대조)")
    if not selftest(verbose=True):
        print("  → FAIL: 통계 함수가 닫힌 형식과 다릅니다")
        ok = False
    rows = read_csv(csv_path)
    recomputed = build_case(rows)
    saved = load_case(case_path)
    for key in ("rows", "groups", "primary_result", "manuscript", "critic_findings", "deck_placeholders"):
        same = recomputed[key] == saved[key]
        print(f"[verify] case.json[{key}] CSV 재계산과 {'일치' if same else '불일치'}")
        ok &= same
    n_i = sum(1 for r in rows if r["group"] == "notification")
    n_c = sum(1 for r in rows if r["group"] == "control")
    counts_ok = (len(rows), n_i, n_c) == (40, 20, 20)
    print(f"[verify] 행 수 {len(rows)} · 알림군 {n_i} · 대조군 {n_c}  {'OK' if counts_ok else 'FAIL'}")
    ok &= counts_ok
    ids = [r["participant_id"] for r in rows]
    uniq = len(set(ids)) == len(ids)
    print(f"[verify] participant_id 중복 없음  {'OK' if uniq else 'FAIL'}")
    ok &= uniq
    if os.path.exists(html_path):
        try:
            in_html = extract_html_case(html_path)
            same = in_html == saved
            print(f"[verify] index.html 내장 JSON 이 case.json 과 {'일치' if same else '불일치'}")
            ok &= same
        except ValueError as e:
            print(f"[verify] index.html: {e}")
            ok = False
    else:
        print("[verify] index.html 없음 — HTML 검증 생략")
    pr = saved["primary_result"]
    print(f"[verify] 1차 결과: 평균 차이 {pr['mean_difference']:+,.1f}걸음, 95% CI(부트스트랩) {pr['ci95'][0]:,.1f}~{pr['ci95'][1]:,.1f}, "
          f"순열 p={pr['p_permutation']}, 0 포함={pr['ci_includes_zero']}; 참고 Welch t={pr['welch_reference']['t']}, "
          f"df={pr['welch_reference']['df']}, CI {pr['welch_reference']['ci95'][0]:,.1f}~{pr['welch_reference']['ci95'][1]:,.1f}")
    print("[verify] 결과:", "PASS" if ok else "FAIL")
    return ok


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regenerate", action="store_true", help="CSV 를 시드로 다시 생성(의도적으로만)")
    ap.add_argument("--no-inject", action="store_true", help="index.html 에 주입하지 않음")
    ap.add_argument("--verify-only", action="store_true", help="검증만 수행")
    ap.add_argument("--selftest", action="store_true", help="통계 함수 자가검사만 수행")
    args = ap.parse_args(argv)

    if args.selftest:
        return 0 if selftest() else 1
    if args.verify_only:
        return 0 if verify() else 1

    if args.regenerate or not os.path.exists(CSV_PATH):
        rows = generate_rows()
        write_csv(rows)
        print(f"[generate] seed={SEED} → {os.path.relpath(CSV_PATH, HERE)} ({len(rows)}행)")
    else:
        print(f"[generate] 기존 CSV 유지 (--regenerate 로만 다시 만든다): {os.path.relpath(CSV_PATH, HERE)}")

    rows = read_csv()
    case = build_case(rows)
    write_case(case)
    pr = case["primary_result"]
    print(f"[compute] case.json 기록 — 평균 차이 {pr['mean_difference']:+,.1f}걸음, 95% CI(부트스트랩) "
          f"{pr['ci95'][0]:,.1f}~{pr['ci95'][1]:,.1f}, 순열 p={pr['p_permutation']}")

    if not args.no_inject:
        if os.path.exists(HTML_PATH):
            inject_html(case)
            print("[inject] index.html 의 case-data 블록을 갱신")
        else:
            print("[inject] index.html 이 아직 없어 주입 생략")

    return 0 if verify() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
