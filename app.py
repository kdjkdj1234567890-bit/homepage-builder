#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5분 홈페이지 만들기 — 사장님용 홈페이지 제작 체험 데모
실행: bash run.sh  →  http://localhost:5005
외부 API · 유료 서비스 없이 Python Flask + SQLite 만으로 동작합니다.
"""
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime

from flask import (
    Flask, abort, g, redirect, render_template, request, session, url_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sites.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB (사진 업로드 제한)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

# ---------------------------------------------------------------------------
# 업종별 디자인 4종 (사장님 말: "디자인 고르기")
# ---------------------------------------------------------------------------
DESIGNS = {
    "beauty": {
        "key": "beauty",
        "biz": "미용실 · 네일 · 에스테틱",
        "title": "화사한 미용실 디자인",
        "desc": "분홍빛 톤의 부드러운 분위기. 여성 고객이 많은 가게에 잘 어울립니다.",
        "accent": "#e0608f", "accent2": "#f9d9e4", "bg": "#fff8fa",
        "ink": "#4a2e3a", "hero": "linear-gradient(135deg,#fbd3e0,#f6a9c6)",
        "radius": "18px",
        "sample_menus": [
            {"name": "여성 커트", "price": "25000"},
            {"name": "남성 커트", "price": "18000"},
            {"name": "전체 염색", "price": "80000"},
            {"name": "열펌", "price": "90000"},
            {"name": "두피 클리닉", "price": "35000"},
        ],
        "sample_intro": "동네에서 10년째, 머릿결 상담부터 꼼꼼한 시술까지. 첫 방문 고객님께는 두피 진단이 무료입니다.",
        "sample_hours": "매일 10:00 ~ 20:00 (수요일 휴무)",
    },
    "cleaning": {
        "key": "cleaning",
        "biz": "청소 · 입주청소 · 에어컨청소",
        "title": "깨끗한 청소업체 디자인",
        "desc": "시원한 파란 톤으로 믿음직한 인상을 줍니다. 견적 문의가 많은 업종에 최적화.",
        "accent": "#2b8fd4", "accent2": "#d7ecf9", "bg": "#f5fafd",
        "ink": "#1f3345", "hero": "linear-gradient(135deg,#cde9fa,#9fd0ef)",
        "radius": "12px",
        "sample_menus": [
            {"name": "신축 입주청소 (34평)", "price": "350000"},
            {"name": "이사청소 (34평)", "price": "320000"},
            {"name": "거주청소 (기본)", "price": "150000"},
            {"name": "에어컨 분해청소", "price": "90000"},
            {"name": "침대·소파 청소", "price": "70000"},
        ],
        "sample_intro": "청소 전후 사진으로 증명하는 입주청소 전문 업체입니다. 하자 발생 시 24시간 내 A/S 보장합니다.",
        "sample_hours": "매일 08:00 ~ 19:00 (명절 휴무)",
    },
    "moving": {
        "key": "moving",
        "biz": "이사짐센터 · 용달 · 포장이사",
        "title": "활기찬 이사업체 디자인",
        "desc": "주황빛 톤의 힘 있는 디자인. 전화 상담이 많은 업종에 어울립니다.",
        "accent": "#e8842a", "accent2": "#fbe8d3", "bg": "#fffaf4",
        "ink": "#4a3423", "hero": "linear-gradient(135deg,#ffd9ad,#f7a952)",
        "radius": "14px",
        "sample_menus": [
            {"name": "포장이사 (투룸)", "price": "900000"},
            {"name": "반포장이사 (투룸)", "price": "600000"},
            {"name": "일반이사 (원룸)", "price": "350000"},
            {"name": "용달이사", "price": "120000"},
            {"name": "보관이사 (월)", "price": "200000"},
        ],
        "sample_intro": "30년 경력의 베테랑 팀장이 직접 방문 견적합니다. 파손 시 100% 보상, 당일 정리까지 도와드립니다.",
        "sample_hours": "매일 07:00 ~ 21:00 (연중무휴)",
    },
    "interior": {
        "key": "interior",
        "biz": "인테리어 · 리모델링 · 셀프인테리어",
        "title": "고급스러운 인테리어 디자인",
        "desc": "차분한 베이지·브라운 톤. 포트폴리오 사진을 돋보이게 하는 고급형 디자인.",
        "accent": "#8a6d4b", "accent2": "#ece0cd", "bg": "#faf7f1",
        "ink": "#3d3226", "hero": "linear-gradient(135deg,#e6d7bd,#c9ae83)",
        "radius": "6px",
        "sample_menus": [
            {"name": "주방 리모델링 (기본)", "price": "8000000"},
            {"name": "욕실 리모델링", "price": "3500000"},
            {"name": "도배·장판 (30평)", "price": "2500000"},
            {"name": "필름 시공", "price": "1500000"},
            {"name": "무료 방문 상담", "price": "0"},
        ],
        "sample_intro": "상담부터 A/S까지 대표가 직접 챙기는 소수 정예 인테리어 팀입니다. 3D 설계도 무료 제공.",
        "sample_hours": "평일 09:00 ~ 18:00 (주말 상담 예약제)",
    },
}

# 견적 옵션 (사장님 말로)
QUOTE_OPTIONS = [
    {"key": "domain", "name": "도메인 연결", "desc": "가게이름.com 같은 쉬운 주소로 연결", "price": 50000},
    {"key": "booking", "name": "온라인 예약 기능", "desc": "손님이 전화 없이 홈페이지에서 예약", "price": 150000},
    {"key": "review", "name": "후기 게시판", "desc": "단골 손님들의 후기를 홈페이지에 공개", "price": 80000},
    {"key": "naver", "name": "네이버·카카오 연동", "desc": "네이버플레이스·카카오맵과 연결", "price": 30000},
    {"key": "page2", "name": "추가 페이지 1장", "desc": "포트폴리오·갤러리 등 원하는 페이지 추가", "price": 100000},
]
BASE_PRICE = 500000  # 기본 제작비

PHONE_RE = re.compile(r"^[0-9+\-() ]{9,20}$")


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS sites (
            id TEXT PRIMARY KEY,
            design TEXT NOT NULL DEFAULT 'beauty',
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT DEFAULT '',
            hours TEXT DEFAULT '',
            intro TEXT DEFAULT '',
            menus TEXT DEFAULT '[]',
            photo TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            memo TEXT DEFAULT '',
            options TEXT DEFAULT '[]',
            quote INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    db.commit()
    db.close()


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def row_to_site(row):
    site = dict(row)
    try:
        site["menus"] = json.loads(site.get("menus") or "[]")
    except Exception:
        site["menus"] = []
    site["design_info"] = DESIGNS.get(site.get("design"), DESIGNS["beauty"])
    return site


def new_slug():
    db = get_db()
    for _ in range(20):
        slug = secrets.token_urlsafe(6).lower().replace("-", "").replace("_", "")[:6]
        cur = db.execute("SELECT 1 FROM sites WHERE id = ?", (slug,))
        if cur.fetchone() is None:
            return slug
    return secrets.token_hex(4)


def fmt_price(value):
    try:
        v = int(str(value).replace(",", "").strip())
    except (ValueError, AttributeError):
        return str(value).strip()
    if v <= 0:
        return "무료"
    return f"{v:,}원"


app.jinja_env.filters["fmt_price"] = fmt_price


# ---------------------------------------------------------------------------
# 페이지
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", designs=DESIGNS)


@app.route("/designs")
def designs():
    """1단계: 디자인 고르기"""
    return render_template("designs.html", designs=DESIGNS)


@app.route("/builder")
def builder():
    """2단계: 가게 정보 입력 (+ 실시간 미리보기)"""
    design_key = request.args.get("design") or session.get("design") or "beauty"
    if design_key not in DESIGNS:
        design_key = "beauty"
    session["design"] = design_key
    edit_id = request.args.get("edit")
    site = None
    if edit_id:
        db = get_db()
        row = db.execute("SELECT * FROM sites WHERE id = ?", (edit_id,)).fetchone()
        if row:
            site = row_to_site(row)
            session["design"] = site["design"]
    errs = session.pop("design_errs", None)
    return render_template(
        "builder.html",
        designs=DESIGNS,
        design_key=site["design"] if site else design_key,
        site=site,
        errs=errs,
    )


@app.route("/build", methods=["POST"])
def build():
    """3단계: 홈페이지 완성하기 — 폼 저장 후 고유 주소로 공개"""
    design_key = request.form.get("design") or session.get("design") or "beauty"
    if design_key not in DESIGNS:
        design_key = "beauty"

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    hours = request.form.get("hours", "").strip()
    intro = request.form.get("intro", "").strip()

    errors = []
    if not name:
        errors.append("가게 이름을 입력해 주세요.")
    elif len(name) > 40:
        errors.append("가게 이름은 40자 이내로 입력해 주세요.")
    if not phone:
        errors.append("전화번호를 입력해 주세요.")
    elif not PHONE_RE.match(phone):
        errors.append("전화번호 형식을 확인해 주세요. (예: 010-1234-5678)")
    if len(address) > 120:
        errors.append("주소는 120자 이내로 입력해 주세요.")

    menu_names = request.form.getlist("menu_name")
    menu_prices = request.form.getlist("menu_price")
    menus = []
    for mn, mp in zip(menu_names, menu_prices):
        mn = (mn or "").strip()
        if not mn:
            continue
        menus.append({"name": mn[:40], "price": (mp or "").strip()[:20]})
    if len(menus) > 20:
        menus = menus[:20]

    # 사진 업로드 (선택)
    photo_file = request.files.get("photo")
    photo_path = ""
    if photo_file and photo_file.filename:
        ext = photo_file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            errors.append("사진은 png, jpg, gif, webp 형식만 올릴 수 있습니다.")
        else:
            tmp_slug = new_slug()
            safe = f"{tmp_slug}.{ext}"
            try:
                photo_file.save(os.path.join(UPLOAD_DIR, safe))
                photo_path = f"uploads/{safe}"
            except Exception:
                errors.append("사진 저장 중 문제가 발생했습니다. 다시 시도해 주세요.")

    edit_id = request.form.get("edit_id", "").strip()

    if errors:
        session["design"] = design_key
        for k, v in (("name", name), ("phone", phone), ("address", address),
                     ("hours", hours), ("intro", intro)):
            session["draft_" + k] = v
        session["draft_menus"] = menus
        session["design_errs"] = errors
        if edit_id:
            return redirect(url_for("builder", design=design_key, edit=edit_id))
        return redirect(url_for("builder", design=design_key))

    db = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    menus_json = json.dumps(menus, ensure_ascii=False)

    if edit_id:
        row = db.execute("SELECT * FROM sites WHERE id = ?", (edit_id,)).fetchone()
        if row:
            old_photo = row["photo"]
            if photo_path:
                if old_photo:
                    try:
                        os.remove(os.path.join(BASE_DIR, "static", old_photo))
                    except OSError:
                        pass
            else:
                photo_path = old_photo
            db.execute(
                """UPDATE sites SET design=?, name=?, phone=?, address=?, hours=?,
                   intro=?, menus=?, photo=? WHERE id=?""",
                (design_key, name, phone, address, hours, intro, menus_json, photo_path, edit_id),
            )
            db.commit()
            slug = edit_id
        else:
            slug = new_slug()
            db.execute(
                "INSERT INTO sites (id, design, name, phone, address, hours, intro, menus, photo, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (slug, design_key, name, phone, address, hours, intro, menus_json, photo_path, now),
            )
            db.commit()
    else:
        slug = new_slug()
        # 업로드한 사진 파일명을 최종 slug에 맞추지 않아도 동작하므로 그대로 사용
        db.execute(
            "INSERT INTO sites (id, design, name, phone, address, hours, intro, menus, photo, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (slug, design_key, name, phone, address, hours, intro, menus_json, photo_path, now),
        )
        db.commit()

    for k in ("design", "draft_name", "draft_phone", "draft_address",
              "draft_hours", "draft_intro", "draft_menus", "design_errs"):
        session.pop(k, None)
    return redirect(url_for("site", slug=slug, celebrate=1))


@app.route("/site/<slug>")
def site(slug):
    """4단계: 완성된 공개 홈페이지"""
    db = get_db()
    row = db.execute("SELECT * FROM sites WHERE id = ?", (slug,)).fetchone()
    if row is None:
        abort(404)
    site = row_to_site(row)
    return render_template("site.html", site=site, design=site["design_info"])


@app.route("/quote/<slug>")
def quote(slug):
    """5단계: 견적 산출"""
    db = get_db()
    row = db.execute("SELECT * FROM sites WHERE id = ?", (slug,)).fetchone()
    if row is None:
        abort(404)
    site = row_to_site(row)
    return render_template(
        "quote.html", site=site, options=QUOTE_OPTIONS, base_price=BASE_PRICE
    )


@app.route("/request/<slug>", methods=["POST"])
def submit_request(slug):
    """의뢰 폼 제출"""
    db = get_db()
    row = db.execute("SELECT * FROM sites WHERE id = ?", (slug,)).fetchone()
    if row is None:
        abort(404)

    customer_name = request.form.get("customer_name", "").strip()
    customer_phone = request.form.get("customer_phone", "").strip()
    memo = request.form.get("memo", "").strip()
    chosen = [k for k in request.form.getlist("opt")]

    errors = []
    if not customer_name:
        errors.append("성함을 입력해 주세요.")
    if not customer_phone:
        errors.append("연락처를 입력해 주세요.")
    elif not PHONE_RE.match(customer_phone):
        errors.append("연락처 형식을 확인해 주세요. (예: 010-1234-5678)")

    valid_keys = {o["key"] for o in QUOTE_OPTIONS}
    chosen = [k for k in chosen if k in valid_keys]
    total = BASE_PRICE + sum(o["price"] for o in QUOTE_OPTIONS if o["key"] in chosen)

    if errors:
        site = row_to_site(row)
        return render_template(
            "quote.html", site=site, options=QUOTE_OPTIONS, base_price=BASE_PRICE,
            chosen=chosen, req_errors=errors,
            req_name=customer_name, req_phone=customer_phone, req_memo=memo,
        ), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    db.execute(
        "INSERT INTO requests (site_id, customer_name, customer_phone, memo, options, quote, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (slug, customer_name, customer_phone, memo[:500],
         json.dumps(chosen, ensure_ascii=False), total, now),
    )
    db.commit()
    session.pop("design", None)
    return render_template(
        "request_done.html", site_name=row["name"], slug=slug, quote=total,
        customer_name=customer_name,
    )


@app.route("/manage")
def manage():
    """내 홈페이지 관리: 목록 · 수정 · 삭제"""
    db = get_db()
    rows = db.execute("SELECT * FROM sites ORDER BY created_at DESC").fetchall()
    sites = [row_to_site(r) for r in rows]
    req_count = {}
    for r in db.execute("SELECT site_id, COUNT(*) c FROM requests GROUP BY site_id"):
        req_count[r["site_id"]] = r["c"]
    return render_template("manage.html", sites=sites, req_count=req_count)


@app.route("/delete/<slug>", methods=["POST"])
def delete_site(slug):
    db = get_db()
    row = db.execute("SELECT * FROM sites WHERE id = ?", (slug,)).fetchone()
    if row is None:
        abort(404)
    if row["photo"]:
        try:
            os.remove(os.path.join(BASE_DIR, "static", row["photo"]))
        except OSError:
            pass
    db.execute("DELETE FROM sites WHERE id = ?", (slug,))
    db.execute("DELETE FROM requests WHERE site_id = ?", (slug,))
    db.commit()
    return redirect(url_for("manage"))


# ---------------------------------------------------------------------------
# 에러 처리 — 기술 용어(traceback) 노출 금지, 사장님 말로 안내
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template(
        "error.html", title="페이지를 찾을 수 없어요",
        message="주소가 바뀌었거나 삭제된 홈페이지일 수 있습니다. 아래 버튼으로 처음으로 돌아가 주세요."
    ), 404


@app.errorhandler(413)
def too_large(e):
    return render_template(
        "error.html", title="사진이 너무 커요",
        message="사진은 8MB 이하로 올려 주세요. 휴대폰 카메라 설정에서 '중간' 화질을 선택하면 대부분 해결됩니다."
    ), 413


@app.errorhandler(Exception)
def server_error(e):
    return render_template(
        "error.html", title="잠시 문제가 생겼어요",
        message="서버에 잠깐 문제가 생겼습니다. 잠시 후 다시 시도해 주세요."
    ), 500


@app.context_processor
def inject_designs():
    return {"all_designs": DESIGNS}


# ================================================================
# 리트로핏 (2026-10-12): 짜증 오프닝 · 감정 해방 · 심리 · 바이럴 ·
# 감동 · 입소문 · 레거시 · 가치원칙 · 존엄
# ================================================================

# 업종별 업체 평균 견적 (데모용 예시 — 화면에 반드시 "데모 기준" 표기)
QUOTE_BENCHMARK = {
    "beauty": 800000,
    "cleaning": 600000,
    "moving": 600000,
    "interior": 1200000,
}
BENCH_DEMO_NOTE = "데모용 예시 수치입니다"
MAINT_MONTHLY = 50000  # 업체 유지보수 월 평균 (데모 기준)


def greeting():
    """매일 루틴 — 시간대별 인사 (아침/저녁 감동 설계)"""
    h = datetime.now().hour
    if 5 <= h < 11:
        return "오늘도 힘내세요 😊"
    if 11 <= h < 17:
        return "오늘도 열심히 일하고 계시네요"
    if 17 <= h < 21:
        return "오늘 하루도 잘 보내고 계세요"
    return "오늘 수고하셨어요 🌙"


def get_setting(key, default=""):
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    db = get_db()
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    db.commit()


def referral_code():
    code = get_setting("referral_code")
    if not code:
        code = "HP-" + secrets.token_hex(3).upper()
        set_setting("referral_code", code)
    return code


def event_count(kind):
    db = get_db()
    row = db.execute("SELECT COUNT(*) AS c FROM events WHERE kind=?", (kind,)).fetchone()
    return row["c"] if row else 0


def log_event(kind):
    db = get_db()
    db.execute(
        "INSERT INTO events (kind, created_at) VALUES (?, ?)",
        (kind, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    db.commit()


def this_month():
    return datetime.now().strftime("%Y-%m")


def badge_list():
    db = get_db()
    site_cnt = db.execute("SELECT COUNT(*) c FROM sites").fetchone()["c"]
    req_cnt = db.execute("SELECT COUNT(*) c FROM requests").fetchone()["c"]
    rich = False
    for r in db.execute("SELECT menus FROM sites").fetchall():
        try:
            if len(json.loads(r["menus"] or "[]")) >= 5:
                rich = True
                break
        except Exception:
            pass
    referral_cnt = event_count("referral")
    export_cnt = event_count("export")
    badges = [
        {"icon": "🌱", "name": "첫 홈페이지", "desc": "첫 홈페이지를 완성했어요",
         "earned": site_cnt >= 1, "hint": "홈페이지를 1개 만들면 받아요"},
        {"icon": "📞", "name": "문의 1호", "desc": "첫 의뢰를 받았어요",
         "earned": req_cnt >= 1, "hint": "의뢰를 1건 받으면 받아요"},
        {"icon": "📋", "name": "알찬 가게", "desc": "메뉴를 5개 이상 채웠어요",
         "earned": rich, "hint": "메뉴(가격표)를 5개 이상 등록하면 받아요"},
        {"icon": "💌", "name": "소문의 주인공", "desc": "사장님 3분께 추천했어요",
         "earned": referral_cnt >= 3, "hint": "추천하기를 3번 기록하면 받아요"},
        {"icon": "📦", "name": "든든한 기록가", "desc": "내 데이터를 내려받았어요",
         "earned": export_cnt >= 1, "hint": "데이터 내려받기를 1번 하면 받아요"},
    ]
    return badges, sum(1 for b in badges if b["earned"])


# ---------------------------------------------------------------- 사장님 오늘 브리핑
@app.route("/briefing")
def briefing():
    db = get_db()
    month = this_month()
    sites = db.execute("SELECT * FROM sites ORDER BY created_at DESC").fetchall()
    reqs = db.execute(
        """SELECT r.*, s.name AS site_name FROM requests r
           LEFT JOIN sites s ON s.id = r.site_id
           ORDER BY r.id DESC LIMIT 10"""
    ).fetchall()
    month_reqs = db.execute(
        "SELECT COUNT(*) c, COALESCE(SUM(quote),0) q FROM requests WHERE substr(created_at,1,7)=?",
        (month,),
    ).fetchone()
    return render_template(
        "briefing.html",
        hello=greeting(),
        month=month,
        site_cnt=len(sites),
        sites=[row_to_site(r) for r in sites[:3]],
        req_cnt=db.execute("SELECT COUNT(*) c FROM requests").fetchone()["c"],
        month_req_cnt=month_reqs["c"] or 0,
        month_quote=month_reqs["q"] or 0,
        reqs=reqs,
    )


# ---------------------------------------------------------------- 가치 계산기
@app.route("/calculator", methods=["GET", "POST"])
def calculator():
    result = None
    design = "beauty"
    if request.method == "POST":
        design = request.form.get("design") or "beauty"
        if design not in DESIGNS:
            design = "beauty"
        agency = QUOTE_BENCHMARK[design]
        saved_once = agency  # 직접 만들기 비용 0원
        saved_year = MAINT_MONTHLY * 12  # 유지보수비 절감
        result = {
            "design": design,
            "design_name": DESIGNS[design]["biz"],
            "agency": agency,
            "agency_man": round(agency / 10000, 1),
            "saved_year_man": round(saved_year / 10000),
            "total_man": round((saved_once + saved_year) / 10000, 1),
        }
    return render_template("calculator.html", designs=DESIGNS, design=design,
                           result=result, demo_note=BENCH_DEMO_NOTE,
                           maint=MAINT_MONTHLY)


# ---------------------------------------------------------------- 월간 리포트 + 벤치마크
@app.route("/report")
def report():
    db = get_db()
    month = this_month()
    cur = {
        "sites": db.execute("SELECT COUNT(*) c FROM sites WHERE substr(created_at,1,7)=?",
                            (month,)).fetchone()["c"],
        "reqs": db.execute("SELECT COUNT(*) c FROM requests WHERE substr(created_at,1,7)=?",
                            (month,)).fetchone()["c"],
        "quote": db.execute("SELECT COALESCE(SUM(quote),0) q FROM requests WHERE substr(created_at,1,7)=?",
                            (month,)).fetchone()["q"] or 0,
    }
    total_sites = db.execute("SELECT COUNT(*) c FROM sites").fetchone()["c"]
    total_reqs = db.execute("SELECT COUNT(*) c FROM requests").fetchone()["c"]
    return render_template("report.html", month=month, cur=cur,
                           total_sites=total_sites, total_reqs=total_reqs,
                           demo_note=BENCH_DEMO_NOTE)


# ---------------------------------------------------------------- 성장 시뮬레이터
@app.route("/simulator")
def simulator():
    return render_template("simulator.html")


# ---------------------------------------------------------------- 추천 리워드 + FOMO
@app.route("/referral", methods=["GET", "POST"])
def referral():
    if request.method == "POST":
        log_event("referral")
        db = get_db()
        # 플래시 대신 세션 메시지로 친절 안내
        session["ref_msg"] = "추천을 기록했습니다. 좋은 건 나눌수록 커져요 💌"
        return redirect(url_for("referral"))
    msg = session.pop("ref_msg", None)
    return render_template("referral.html", code=referral_code(),
                           count=event_count("referral"), msg=msg)


# ---------------------------------------------------------------- 배지 + 단톡방 공유
@app.route("/badges")
def badges():
    items, earned = badge_list()
    return render_template("badges.html", badges=items, earned=earned, total=len(items))


# ---------------------------------------------------------------- 우리의 약속 (레거시 철학 + 가치 7원칙)
@app.route("/about")
def about():
    return render_template("about.html")


# ---------------------------------------------------------------- 가게 이어받기: 데이터 내려받기
@app.route("/export")
def export_data():
    db = get_db()
    data = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notice": "이 데이터는 10년 후에도 사장님의 것입니다.",
        "sites": [row_to_site(r) for r in db.execute("SELECT * FROM sites").fetchall()],
        "requests": [dict(r) for r in db.execute("SELECT * FROM requests").fetchall()],
    }
    for s in data["sites"]:
        s.pop("design_info", None)
    log_event("export")
    from flask import Response
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        body, mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=homepage-backup.json"},
    )


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "5005"))
    app.run(host="0.0.0.0", port=port, debug=False)
