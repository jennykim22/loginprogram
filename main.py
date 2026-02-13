from fastapi import FastAPI, Form, Request, Depends, status, Query, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, desc, func, text, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
import httpx
import ollama

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/myboard"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
router=APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
SECRET_KEY="secret_key" #jwt토큰용

class User(Base): #users 테이블 정의
    __tablename__ = "users_time"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True) 
    password_hash = Column(String)
    is_admin=Column(Boolean, default=False)
    created_at=Column(DateTime,default=datetime.now, index=True) #가입일시 나타내기
    posts=relationship("Post", back_populates="owner")

class Post(Base):
    __tablename__="posts"
    id=Column(Integer, primary_key=True, index=True)
    title=Column(String, index=True)
    content=Column(String)
    filename = Column(String, nullable=True)
    is_notice=Column(Boolean, default=False)
    created_at=Column(DateTime,default=datetime.now, index=True)
    owner_id=Column(Integer, ForeignKey("users_time.id"))
    owner=relationship("User", back_populates="posts")

class ChatHistory(Base):
    __tablename__="chat_history"
    id=Column(Integer,primary_key=True,index=True)
    role=Column(String)
    content=Column(String)
    created_at=Column(DateTime, default=datetime.utcnow)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") #pw암호화

app = FastAPI()
app.mount("/static",StaticFiles(directory="static"),name="static") 
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)
        
@app.get("/check-username") #아이디 사용 가능 여부
def check_username(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user:
        return {"available": False} 
    return {"available": True} 

@app.get("/register", response_class=HTMLResponse)
def show_register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register") #회원가입
def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user=db.query(User).filter(User.username == username).first()
    if existing_user:
        return RedirectResponse(url="/register?error=register_fail", status_code=303)
    if(username=="admin"):
        is_admin_check=True
    else:
        is_admin_check=False
    
    hashed_password = pwd_context.hash(password)
    new_user=User(username=username, password_hash=hashed_password,is_admin=is_admin_check)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login", response_class=HTMLResponse)
def show_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_user(
    username: str=Form(...),
    password: str=Form(...),
    db: Session=Depends(get_db)
):
    user=db.query(User).filter(User.username==username).first()
    if(not user) or(not pwd_context.verify(password, user.password_hash)):
        return RedirectResponse(url="/login?error=login_fail", status_code=303)
    
    payload={"sub": user.username,"exp":datetime.utcnow()+timedelta(hours=1)}
    token=jwt.encode(payload,SECRET_KEY,algorithm="HS256")

    if user.is_admin:
        redirect_url="/admin"
    else:
        redirect_url="/board"

    response=RedirectResponse(url=redirect_url,status_code=303)
    response.set_cookie(key="token",value=token)
    return response    

def get_username_from_token(token: str): #welcome함수에서 확인
    if token is None:
        return None
    try:
        decoded_token=jwt.decode(token,SECRET_KEY,algorithms=["HS256"])
        return decoded_token.get("sub")
    except JWTError:
        return None

def get_current_user(request: Request, db: Session):
    token=request.cookies.get("token")
    if not token:
        return None
    username=get_username_from_token(token)
    if not username:
        return None
    user=db.query(User).filter(User.username==username).first()
    return user

@app.get("/welcome",response_class=HTMLResponse)
def welcome(request: Request):
    username=get_username_from_token(request.cookies.get("token"))
    if not username: #로그인하지않고 welcome페이지 접근시 로그인페이지로 이동
        return RedirectResponse(url="/login",status_code=303)
    return templates.TemplateResponse("welcome.html",{"request":request, "username":username})

@app.get("/admin",response_class=HTMLResponse) 
def admin(request: Request, db: Session = Depends(get_db)):
    token=request.cookies.get("token")
    username=get_username_from_token(token)
    if not username:
        return RedirectResponse(url="/login",status_code=303)
    
    user=db.query(User).filter(User.username==username).first()
    if not user or not user.is_admin:
        return RedirectResponse(url="/welcome", status_code=303)    
    
    all_users=db.query(User).all()
    return templates.TemplateResponse("admin.html",{
        "request": request,
        "users": all_users,
        "admin_name": user.username
    })

@app.post("/admin/delete/{user_id}")
def delete(request: Request, user_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("token")
    username = get_username_from_token(token)
    admin_user = db.query(User).filter(User.username == username).first()

    if not admin_user or not admin_user.is_admin:
        return RedirectResponse(url="/welcome", status_code=302)
    target_user = db.query(User).filter(User.id == user_id).first()

    if admin_user.id==user_id:
        print("관리자는 삭제할 수 없습니다")
        return RedirectResponse('/admin', status_code=303)

    if target_user:
        db.delete(target_user)
        db.commit()
    return RedirectResponse(url='/admin/users',status_code=303)

@app.post("/admin/toggle/{user_id}")
def toggle_admin(request: Request, user_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("token")
    username = get_username_from_token(token)
    admin_user = db.query(User).filter(User.username == username).first()

    if not admin_user or not admin_user.is_admin:
        return RedirectResponse(url="/welcome", status_code=302)
    
    target_user = db.query(User).filter(User.id == user_id).first()

    if target_user:
        if target_user.id==admin_user.id:
            return RedirectResponse(url="/admin", status_code=303)
        target_user.is_admin=not target_user.is_admin
        db.commit()
    return RedirectResponse(url='/admin/users',status_code=303)

@app.get("/logout")
def logout():
    response=RedirectResponse(url='/login',status_code=302)
    response.delete_cookie(key="token")
    return response

@app.get("/users") #db확인용
def read_users(db: Session = Depends(get_db)): 
    users = db.query(User).all() 
    return users

@app.get("/board/write", response_class=HTMLResponse) #작성 화면 보여주기
def show_write(request: Request, db: Session = Depends(get_db)):
    user=get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("board_write.html",{
        "request":request,
        "user":user
    })

@app.post("/board/write") #게시물 작성 화면
def create_post(
    request: Request,
    title: str=Form(...),
    content: str=Form(...),
    is_notice: bool=Form(False),
    db: Session=Depends(get_db)
):
    user=get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=302)
        
    if not user.is_admin:
        is_notice=False
        
    new_post=Post(
        title=title, 
        content=content,
        is_notice=is_notice,
        owner_id=user.id
    )

    db.add(new_post)
    db.commit()
    return RedirectResponse(url="/board", status_code=303)

@app.get("/board") #게시물 목록
def board_list(
    request: Request, 
    page: int=1, 
    keyword:str=Query(None),
    db: Session=Depends(get_db)
):
    query=db.query(Post).join(User)
    if keyword:
        search_kw = keyword

        query = query.filter(
            func.to_tsvector('simple', Post.title + ' ' + Post.content).match(search_kw)
        )
    
    user=get_current_user(request, db)
    limit=20
    page_limit=5
    total_count=query.count()
    total_pages=max(1, (total_count-1)//limit+1)
    offset=(page-1)*limit

    posts=query.order_by(
        Post.is_notice.desc(),
        Post.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    block_start=((page-1)//page_limit)*page_limit+1
    block_end=block_start+page_limit-1

    if block_end>total_pages:
        block_end=total_pages

    return templates.TemplateResponse("board_list.html", {
        "request":request,
        "posts":posts,
        "user":user,
        "current_page":page,
        "total_pages":total_pages,
        "limit": 20,
        "total_count":total_count,
        "block_start":block_start,
        "keyword":keyword,
        "block_end":block_end
    })

@app.post("/board/delete/{post_id}") # 게시물 삭제
def delete_post(request: Request, post_id: int, db: Session=Depends(get_db)):
    token = request.cookies.get("token")
    username = get_username_from_token(token)

    target_post = db.query(Post).filter(Post.id == post_id).first()
    user = db.query(User).filter(User.username == username).first()

    is_owner=(user and user.id ==target_post.owner_id)
    is_admin=(user and user.is_admin)
    
    if not is_owner and not is_admin:
        print("권한이 없습니다.")
        return RedirectResponse(url='/board', status_code=303)

    if target_post:
        db.delete(target_post)
        db.commit()
        return RedirectResponse('/board', status_code=303)
    else:
        return RedirectResponse('/board', status_code=303)

@app.get("/board/edit/{post_id}", response_class=HTMLResponse) #board_edit.html을 보여줌
def show_edit(request: Request, post_id: int, db: Session=Depends(get_db)):
    user=get_current_user(request,db)
    post=db.query(Post).filter(Post.id==post_id).first()  
    
    return templates.TemplateResponse("board_edit.html",{ #post객체를 넘겨서 수정전 내용을 확인
        "request":request,
        "post":post,
        "user":user
    })

@app.post("/board/edit/{post_id}") #게시물 수정해서 업데이트
def edit_post(
    request: Request, 
    post_id: int,
    title: str=Form(...),
    content: str=Form(...), 
    is_notice: bool = Form(False),
    db: Session=Depends(get_db)
):
    token = request.cookies.get("token")
    username = get_username_from_token(token)

    target_post = db.query(Post).filter(Post.id == post_id).first()
    if not target_post:
        return RedirectResponse('/board', status_code=303)
    user = db.query(User).filter(User.username == username).first()

    is_owner=(user and user.id ==target_post.owner_id)
    is_admin=(user and user.is_admin)
    if not (is_owner or is_admin):
        print("권한이 없습니다.")
        return RedirectResponse(url='/board', status_code=303)
    
    target_post.title=title #제목과 내용 수정해서 커밋
    target_post.content=content
    if is_admin:
        target_post.is_notice = is_notice
    db.commit()
    return RedirectResponse(url=f'/board/read/{post_id}', status_code=303)

@app.get("/board/read/{post_id}") #게시물 읽기
def read_post(request: Request, post_id: int, db: Session = Depends(get_db)):
    user=get_current_user(request, db)
    post=db.query(Post).filter(Post.id==post_id).first()

    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("board_read.html",{
        "request":request,
        "post":post,
        "user":user
    })

# admin page
@app.get("/admin/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not (user and user.is_admin):
        return RedirectResponse("/board", status_code=303)

    today = datetime.now().date()
    target_dates_short = [(today - timedelta(days=i)).strftime('%m-%d') for i in range(6, -1, -1)]
    target_dates_full = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]

    seven_days_ago = today - timedelta(days=6)
    post_stats = db.query(
        func.date(Post.created_at).label('date'),
        func.count(Post.id).label('count')
    ).filter(Post.created_at >= seven_days_ago)\
     .group_by(func.date(Post.created_at)).all()

    db_data = {str(row.date)[:10]: row.count for row in post_stats}

    final_values = []
    for date_key in target_dates_full:
        final_values.append(db_data.get(date_key, 0))

    stats = {
        "total_users": db.query(User).count(),
        "total_posts": db.query(Post).count(),
        "recent_users": db.query(User).order_by(User.id.desc()).limit(5).all(),
        "recent_posts": db.query(Post).order_by(Post.id.desc()).limit(5).all(),
        "chart_labels": target_dates_short, 
        "chart_values": final_values
    }
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "stats": stats, "user": user})

@app.get("/admin/users") #관리자페이지 회원관리
def admin_users(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not (user and user.is_admin): return RedirectResponse("/board", status_code=303)
    
    users = db.query(User).all()
    return templates.TemplateResponse("admin_users.html", {
        "request": request, 
        "users": users, 
        "user": user, 
        "admin_name": user.username
    })

@app.get("/admin/board") #관리자페이지 게시물 목록
def board_list(request: Request, page: int=1, db: Session=Depends(get_db)):
    user=get_current_user(request, db)
    limit=20
    page_limit=5
    offset=(page-1)*limit

    total_count=db.query(Post).count() 
    total_pages=max(1, (total_count-1)//limit+1)

    post=db.query(Post).order_by(
        Post.is_notice.desc(),
        Post.created_at.desc()
    ).offset(offset).limit(limit).all()

    block_start=((page-1)//page_limit)*page_limit+1 #전체블ㄹ가
    block_end=block_start+page_limit-1

    if block_end>total_pages:
        block_end=total_pages

    return templates.TemplateResponse("admin_board.html", {
        "request":request,
        "posts":post,
        "user":user,
        "current_page":page,
        "total_pages":total_pages,
        "total_count":total_count,
        "block_start":block_start,
        "block_end":block_end
    })

@app.get("/admin/read/{post_id}")
def admin_read(request: Request, post_id: int, db: Session = Depends(get_db)):
    user=get_current_user(request, db)
    post=db.query(Post).filter(Post.id==post_id).first()

    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("admin_read.html",{
        "request":request,
        "post":post,
        "user":user
    })

@app.get("/admin/edit/{post_id}", response_class=HTMLResponse) 
def show_edit(request: Request, post_id: int, db: Session=Depends(get_db)):
    user=get_current_user(request,db)
    post=db.query(Post).filter(Post.id==post_id).first()  
    
    return templates.TemplateResponse("admin_edit.html",{ 
        "request":request,
        "post":post,
        "user":user
    })

@app.post("/admin/edit/{post_id}") #게시물 수정해서 업데이트
def edit_post(
    request: Request, 
    post_id: int,
    title: str=Form(...),
    content: str=Form(...), 
    is_notice: bool = Form(False),
    db: Session=Depends(get_db)
):
    token = request.cookies.get("token")
    username = get_username_from_token(token)

    target_post = db.query(Post).filter(Post.id == post_id).first()
    if not target_post:
        return RedirectResponse('/board', status_code=303)
    user = db.query(User).filter(User.username == username).first()

    is_owner=(user and user.id ==target_post.owner_id)
    is_admin=(user and user.is_admin)
    if not (is_owner or is_admin):
        print("권한이 없습니다.")
        return RedirectResponse(url='/admin/board', status_code=303)
    
    target_post.title=title #제목과 내용 수정해서 커밋
    target_post.content=content
    if is_admin:
        target_post.is_notice = is_notice
    db.commit()
    return RedirectResponse(url=f'/admin/read/{post_id}', status_code=303)

@app.post("/admin/board/delete/{post_id}") # 관리자페이지 게시물 삭제
def delete_post(request: Request, post_id: int, db: Session=Depends(get_db)):
    token = request.cookies.get("token")
    username = get_username_from_token(token)

    target_post = db.query(Post).filter(Post.id == post_id).first()
    user = db.query(User).filter(User.username == username).first()

    is_owner=(user and user.id ==target_post.owner_id)
    is_admin=(user and user.is_admin)
    
    if not is_owner and not is_admin:
        print("권한이 없습니다.")
        return RedirectResponse(url='/board', status_code=303)

    if target_post and is_admin:
        db.delete(target_post)
        db.commit()
        return RedirectResponse('/admin/board', status_code=303)
    else:
        return RedirectResponse('/board', status_code=303)

@app.get("/posts") # db확인
def read_postsdb(db: Session = Depends(get_db)): 
    posts = db.query(Post).all() 
    return posts

@app.post("/chat")
async def chat_with_ai(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    user_message = data.get("message")

    history_data=db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(6)
    history_data.reverse()

    messages=[]
    for chat in history_data:
        messages.append({"role":chat.role,"content":chat.content})
    messages.append({"role":"user","content":user_message})

    import re
    id_match = re.search(r"(\d+)", user_message)

    if id_match and "summarize" in user_message:
        post_id = id_match.group(1)
        summary_data = summarize_post(int(post_id), db)
        if "error" in summary_data:
            return {"reply":summary_data["error"]}
        return {"reply": summary_data['summary']}
    
    ollama_payload = {
        "model": "qwen2.5:0.5B",  
        "messages": [{"role": "user", "content": user_message}],
        "stream": False          }

    async with httpx.AsyncClient(timeout=60.0) as client: #60초동안 비동기로 기다리기 그리고 클라이언트 호출
        try:
            response = await client.post(
                "http://localhost:11434/api/chat", #api주소
                json=ollama_payload #보낼 데이터
            )
            response_data = response.json()
            
            ai_reply = response_data["message"]["content"]
            db.add(ChatHistory(role="user", content=user_message))
            db.add(ChatHistory(role="assistant", content=ai_reply))
            db.commit()
            
            return {"reply": ai_reply}
            
        except Exception as e:
            print(f"Error: {e}")
            return {"reply": "죄송합니다. AI 서버 연결에 실패했습니다."}
        
@app.get("/ai/summarize/{post_id}")
def summarize_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        return {"error":"해당 글을 찾을 수 없습니다."}
    
    prompt=f"""
    ### POST CONTENT TO SUMMARIZE:
    Title: {post.title}
    Body: {post.content}

    ### INSTRUCTIONS:
    1. You are a board assistant. Summarize the 'Body' text above into exactly 3 bullet points in English.
    2. ONLY output the summary results.
    3. If the text is dummy data (like Latin), briefly state the main topics in English.

    ### SUMMARY (KOREAN):
    """
    response = ollama.chat(model='qwen2.5:0.5B', messages=[
        {'role': 'system', 'content': 'You are a board assistant.'},
        {'role': 'user', 'content': prompt}
    ])
    return {"summary": response['message']['content']}