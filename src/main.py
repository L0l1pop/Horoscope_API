from typing import Annotated
from pydantic import BaseModel, field_validator
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from fastapi import Depends, FastAPI, HTTPException

app = FastAPI()

engine = create_async_engine('sqlite+aiosqlite:///horoscope.db')

new_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    async with new_session() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

ALLOWED_SIGNS = [
    "aries", #овен
    "taurus", #телец
    "gemini", #близнецы
    "cancer", #рак
    "leo", #лев
    "virgo", #дева
    "libra", #весы
    "scorpio", #скорпион
    "sagittarius", #стрелец
    "capricorn", #козерог
    "aquarius", #водолей
    "pisces" #рыбы
]

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    sign: Mapped[str]
    horoscope: Mapped[str]

@app.post("/setup_db")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"ok": True}

class UserAddSchema(BaseModel):
    name: str
    sign: str

    @field_validator("sign")
    def validate_sign(cls, v):
        v = v.lower()
        if v not in ALLOWED_SIGNS:
            raise ValueError(f"Invalid zodiac sign. Must be one of: {', '.join(ALLOWED_SIGNS)}")
        return v

class UserSchema(UserAddSchema):
    id: int
    horoscope: str | None



@app.post("/users")
async def add_user(data: UserAddSchema, session: SessionDep):
    horoscope = None
    response = requests.get(f"https://ohmanda.com/api/horoscope/{data.sign}")
    if response.status_code == 200:
        horoscope = response.json()["horoscope"]
    new_user = UserModel(
        name = data.name,
        sign = data.sign,
        horoscope = horoscope,
    )
    session.add(new_user)
    await session.commit()
    return {"ok": True}


@app.get("/users")
async def get_users(session: SessionDep):
    query = select(UserModel)
    result = await session.execute(query)
    return result.scalars().all()

@app.get("/users/{user_id}")
async def get_user(user_id: int, session: SessionDep):
    user = await session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, session: SessionDep):
    user = await session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()
    return {"ok": True, "message": f"User {user_id} deleted"}