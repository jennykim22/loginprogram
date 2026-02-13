# make_dummy.py
from main import Post, User, SessionLocal
from faker import Faker
import random
from datetime import datetime, timedelta

# 1. DB 세션 연결
db = SessionLocal()

# 2. 더미 데이터 생성기 (한글 설정)
fake = Faker('ko_KR') 

# 3. 작성자 설정 (DB에 있는 유저 ID 아무거나 하나 넣으세요. 보통 1번)
# 만약 유저가 없다면 먼저 회원가입 하나 하셔야 합니다!
user = db.query(User).first()

if not user:
    print("❌ 유저가 한 명도 없습니다! 먼저 회원가입을 해주세요.")
else:
    print(f"👤 작성자 '{user.username}' (ID: {user.id}) 명의로 글을 작성합니다.")

    # 4. 게시글 100개 생성 시작!
    print("🚀 데이터 생성 중...")
    
    for i in range(100):
        # 랜덤한 제목과 내용 생성
        title = fake.sentence(nb_words=6) # 단어 6개짜리 제목
        content = fake.text(max_nb_chars=200) # 200자 내외 본문
        
        # 날짜도 랜덤하게 (최근 30일 이내)
        random_day = random.randint(0, 30)
        created_at = datetime.now() - timedelta(days=random_day)

        # 공지사항 여부 (10% 확률로 공지사항)
        is_notice = random.choice([True] if i < 5 else [False]) 

        # 데이터 객체 만들기
        post = Post(
            title=title,
            content=content,
            owner_id=user.id, # ★ 외래키 연결
            is_notice=is_notice,
            created_at=created_at
        )
        db.add(post)

    # 5. 저장
    db.commit()
    print("✅ 게시글 100개 생성 완료!")

# 6. 연결 종료
db.close()