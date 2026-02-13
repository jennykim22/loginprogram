# make_dummy_bulk.py
from main import Post, User, SessionLocal
from faker import Faker
import random
from datetime import datetime, timedelta
import time

# 1. 설정
TOTAL_COUNT = 100000  # 10만 개
BATCH_SIZE = 10000     # 한 번에 저장할 개수 (1만 개씩 끊어서 저장)

db = SessionLocal()
fake = Faker('ko_KR')

# 유저 확인
user = db.query(User).first()
if not user:
    print("❌ 유저가 없습니다. 회원가입 먼저 해주세요!")
    exit()

print(f"🚀 {TOTAL_COUNT}개 데이터 생성을 시작합니다... (작성자: {user.username})")
start_time = time.time()

# 2. 대량 생성 루프
buffer = [] # 데이터를 임시로 담아둘 리스트
for i in range(TOTAL_COUNT):
    
    # 딕셔너리 형태로 데이터를 만듭니다 (객체보다 빠름)
    post_data = {
        "title": fake.sentence(nb_words=4),
        "content": fake.text(max_nb_chars=50),
        "owner_id": user.id,
        "is_notice": False, # 공지사항은 뺌 (속도 위해)
        "created_at": datetime.now() - timedelta(days=random.randint(0, 365))
    }
    buffer.append(post_data)

    # 3. 버퍼가 꽉 차면(1만 개) DB에 한 번에 쏟아붓기
    if (i + 1) % BATCH_SIZE == 0:
        db.bulk_insert_mappings(Post, buffer) # ★ 핵심 기술: 벌크 인서트
        db.commit() # 저장 확정
        buffer = [] # 버퍼 비우기
        print(f"📦 {i + 1}개 저장 완료... ({(i+1)/TOTAL_COUNT*100:.1f}%)")

# 남은 데이터 처리
if buffer:
    db.bulk_insert_mappings(Post, buffer)
    db.commit()

end_time = time.time()
print(f"✅ 완료! 걸린 시간: {end_time - start_time:.2f}초")
db.close()