
import sqlite3
from datetime import datetime
import uuid
import streamlit as st

DB_PATH = "discussion.db"

# 비밀번호는 GitHub 코드에 저장하지 않고 Streamlit Secrets에서 불러옵니다.
# Streamlit Community Cloud > App settings > Secrets 에서 설정하세요.
try:
    CLASS_PASSWORD = st.secrets["CLASS_PASSWORD"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    DEFAULT_CLASS_CODE = st.secrets.get("CLASS_CODE", "FINANCE101")
except KeyError:
    st.error("앱 비밀번호 설정이 필요합니다. Streamlit App settings > Secrets에서 CLASS_PASSWORD와 ADMIN_PASSWORD를 설정해주세요.")
    st.stop()

st.set_page_config(
    page_title="우리 수업 토론방",
    page_icon="💬",
    layout="wide",
)

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_code TEXT NOT NULL,
        nickname TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT,
        likes INTEGER DEFAULT 0,
        status TEXT DEFAULT '질문',
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        nickname TEXT NOT NULL,
        body TEXT NOT NULL,
        is_instructor INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(question_id) REFERENCES questions(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        question_id INTEGER NOT NULL,
        voter_key TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(question_id, voter_key)
    )
    """)
    conn.commit()
    conn.close()

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_question(class_code, nickname, title, body):
    conn = get_conn()
    conn.execute(
        "INSERT INTO questions(class_code,nickname,title,body,created_at) VALUES(?,?,?,?,?)",
        (class_code, nickname, title, body, now()),
    )
    conn.commit()
    conn.close()

def get_questions(class_code, sort_mode):
    conn = get_conn()
    order = "likes DESC, id DESC" if sort_mode == "공감 많은 순" else "id DESC"
    rows = conn.execute(
        f"SELECT * FROM questions WHERE class_code=? ORDER BY {order}",
        (class_code,),
    ).fetchall()
    conn.close()
    return rows

def get_comments(question_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM comments WHERE question_id=? ORDER BY id ASC",
        (question_id,),
    ).fetchall()
    conn.close()
    return rows

def add_comment(question_id, nickname, body, is_instructor=0):
    conn = get_conn()
    conn.execute(
        "INSERT INTO comments(question_id,nickname,body,is_instructor,created_at) VALUES(?,?,?,?,?)",
        (question_id, nickname, body, is_instructor, now()),
    )
    conn.commit()
    conn.close()

def toggle_like(question_id, voter_key):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO likes(question_id,voter_key,created_at) VALUES(?,?,?)",
            (question_id, voter_key, now()),
        )
        conn.execute(
            "UPDATE questions SET likes=likes+1 WHERE id=?",
            (question_id,),
        )
    except sqlite3.IntegrityError:
        conn.execute(
            "DELETE FROM likes WHERE question_id=? AND voter_key=?",
            (question_id, voter_key),
        )
        conn.execute(
            "UPDATE questions SET likes=CASE WHEN likes>0 THEN likes-1 ELSE 0 END WHERE id=?",
            (question_id,),
        )
    conn.commit()
    conn.close()

def update_status(question_id, status):
    conn = get_conn()
    conn.execute("UPDATE questions SET status=? WHERE id=?", (status, question_id))
    conn.commit()
    conn.close()

def delete_question(question_id):
    conn = get_conn()
    conn.execute("DELETE FROM likes WHERE question_id=?", (question_id,))
    conn.execute("DELETE FROM comments WHERE question_id=?", (question_id,))
    conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
    conn.commit()
    conn.close()

init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "nickname" not in st.session_state:
    st.session_state.nickname = ""
if "voter_key" not in st.session_state:
    st.session_state.voter_key = str(uuid.uuid4())

# ---------- 로그인 화면 ----------
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.3, 1])

    with center:
        st.title("💬 우리 수업 토론방")
        st.write("수업 비밀번호를 입력하고 입장하세요.")

        mode = st.radio(
            "입장 유형",
            ["학생", "교수자"],
            horizontal=True,
            label_visibility="collapsed"
        )

        nickname = ""
        if mode == "학생":
            nickname = st.text_input(
                "닉네임",
                placeholder="예: 2026김학생 / 학번 뒤 4자리"
            )
            password = st.text_input(
                "수업 비밀번호",
                type="password",
                placeholder="수업 비밀번호"
            )
        else:
            password = st.text_input(
                "교수자 비밀번호",
                type="password",
                placeholder="교수자 비밀번호"
            )

        if st.button("입장하기", type="primary", use_container_width=True):
            if mode == "학생":
                if not nickname.strip():
                    st.error("닉네임을 입력해주세요.")
                elif password == CLASS_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.role = "학생"
                    st.session_state.nickname = nickname.strip()
                    st.rerun()
                else:
                    st.error("수업 비밀번호가 올바르지 않습니다.")
            else:
                if password == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.role = "교수자"
                    st.session_state.nickname = "교수자"
                    st.rerun()
                else:
                    st.error("교수자 비밀번호가 올바르지 않습니다.")

        st.caption("학생과 교수자는 서로 다른 비밀번호를 사용합니다.")
    st.stop()

# ---------- 로그인 후 ----------
class_code = DEFAULT_CLASS_CODE

with st.sidebar:
    st.markdown(f"### {st.session_state.role} 모드")
    if st.session_state.role == "학생":
        st.write(f"닉네임: **{st.session_state.nickname}**")
    st.write(f"수업: **{class_code}**")
    st.divider()
    if st.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.nickname = ""
        st.rerun()

st.title("💬 우리 수업 토론방")

if st.session_state.role == "학생":
    tab1, tab2 = st.tabs(["질문 보기", "질문 올리기"])

    with tab2:
        st.subheader("새 질문")
        q_title = st.text_input(
            "질문 제목",
            placeholder="예: NPV와 IRR이 충돌하면 무엇을 우선하나요?"
        )
        q_body = st.text_area(
            "질문 내용",
            placeholder="헷갈린 부분이나 생각을 자유롭게 적어주세요.",
            height=120
        )

        if st.button("질문 올리기", type="primary", use_container_width=True):
            if not q_title.strip():
                st.error("질문 제목을 입력해주세요.")
            else:
                add_question(
                    class_code,
                    st.session_state.nickname,
                    q_title.strip(),
                    q_body.strip()
                )
                st.success("질문이 등록되었습니다.")
                st.rerun()

    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            sort_mode = st.selectbox("정렬", ["최신순", "공감 많은 순"])
        with col2:
            if st.button("새로고침", use_container_width=True):
                st.rerun()

        questions = get_questions(class_code, sort_mode)

        if not questions:
            st.info("아직 등록된 질문이 없습니다.")

        for q in questions:
            status_icon = {
                "질문": "❓",
                "중요": "⭐",
                "답변완료": "✅",
                "토론주제": "💡"
            }.get(q["status"], "❓")

            with st.container(border=True):
                st.markdown(f"### {status_icon} {q['title']}")
                st.caption(
                    f"{q['nickname']} · {q['created_at']} · 👍 {q['likes']} · {q['status']}"
                )

                if q["body"]:
                    st.write(q["body"])

                if st.button(
                    f"👍 공감 {q['likes']}",
                    key=f"like_{q['id']}"
                ):
                    toggle_like(q["id"], st.session_state.voter_key)
                    st.rerun()

                comments = get_comments(q["id"])
                if comments:
                    st.markdown("**댓글**")
                    for c in comments:
                        badge = " 👩‍🏫" if c["is_instructor"] else ""
                        st.markdown(
                            f"- **{c['nickname']}**{badge}: {c['body']}  \n"
                            f"  <span style='color:gray;font-size:12px'>{c['created_at']}</span>",
                            unsafe_allow_html=True
                        )

                with st.form(key=f"comment_{q['id']}", clear_on_submit=True):
                    reply = st.text_input(
                        "댓글",
                        placeholder="답변 또는 의견을 적어주세요.",
                        label_visibility="collapsed"
                    )
                    submitted = st.form_submit_button("댓글 등록")
                    if submitted and reply.strip():
                        add_comment(
                            q["id"],
                            st.session_state.nickname,
                            reply.strip()
                        )
                        st.rerun()

else:
    st.subheader("👩‍🏫 교수자 관리 화면")

    sort_mode = st.selectbox("정렬", ["공감 많은 순", "최신순"])
    questions = get_questions(class_code, sort_mode)

    c1, c2, c3 = st.columns(3)
    c1.metric("질문 수", len(questions))
    c2.metric("총 공감", sum(q["likes"] for q in questions))
    c3.metric(
        "답변 완료",
        sum(1 for q in questions if q["status"] == "답변완료")
    )

    st.divider()

    if not questions:
        st.info("아직 질문이 없습니다.")

    for q in questions:
        with st.container(border=True):
            st.markdown(f"### {q['title']}")
            st.caption(f"{q['nickname']} · {q['created_at']} · 👍 {q['likes']}")

            if q["body"]:
                st.write(q["body"])

            status_options = ["질문", "중요", "답변완료", "토론주제"]
            status = st.selectbox(
                "상태",
                status_options,
                index=status_options.index(q["status"]),
                key=f"status_{q['id']}"
            )

            if status != q["status"]:
                update_status(q["id"], status)
                st.rerun()

            comments = get_comments(q["id"])
            if comments:
                st.markdown("**댓글**")
                for c in comments:
                    badge = " 👩‍🏫" if c["is_instructor"] else ""
                    st.markdown(f"- **{c['nickname']}**{badge}: {c['body']}")

            with st.form(key=f"prof_reply_{q['id']}", clear_on_submit=True):
                prof_reply = st.text_input(
                    "교수자 답변",
                    placeholder="학생들에게 보일 답변을 입력하세요."
                )
                sent = st.form_submit_button("교수자 답변 등록")
                if sent and prof_reply.strip():
                    add_comment(
                        q["id"],
                        "교수자",
                        prof_reply.strip(),
                        is_instructor=1
                    )
                    st.rerun()

            if st.button("질문 삭제", key=f"delete_{q['id']}"):
                delete_question(q["id"])
                st.rerun()
