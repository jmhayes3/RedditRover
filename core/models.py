from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class Module(Base):
    __tablename__ = "module"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    # TODO: Use enum for status (RUNNING, STOPPED, PENDING).
    status = Column(String(20), nullable=False, default="PENDING")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    user_ban = relationship("UserBan", back_populates="module", cascade="all, delete, delete-orphan")
    sub_ban = relationship("SubBan", back_populates="module", cascade="all, delete, delete-orphan")
    storage = relationship("Storage", back_populates="module", cascade="all, delete, delete-orphan")
    update_thread = relationship("UpdateThread", back_populates="module", cascade="all, delete, delete-orphan")
    messages = relationship("Message", back_populates="module", cascade="all, delete, delete-orphan")
    triggered_submission = relationship("TriggeredSubmission", back_populates="module", cascade="all, delete, delete-orphan")
    triggered_comment = relationship("TriggeredComment", back_populates="module", cascade="all, delete, delete-orphan")

    def __init__(self, name=None, status=None):
        self.name = name
        self.status = status

    def __repr__(self):
        return "<Module %r, %r>" % (self.name, self.status)


class UserBan(Base):
    __tablename__ = "user_ban"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    module = relationship("Module", back_populates="user_ban")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, username=None, module=None):
        self.username = username
        self.module = module

    def __repr__(self):
        return "<UserBan %r, %r>" % (self.username, self.module_id)


class SubBan(Base):
    __tablename__ = "sub_ban"
    id = Column(Integer, primary_key=True)
    subreddit = Column(String(50), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    module = relationship("Module", back_populates="sub_ban")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, subreddit=None, module=None):
        self.subreddit = subreddit
        self.module = module

    def __repr__(self):
        return "<SubBan %r, %r>" % (self.subreddit, self.module_id)


class Storage(Base):
    __tablename__ = "storage"
    id = Column(Integer, primary_key=True)
    thing_id = Column(String(15), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    module = relationship("Module", back_populates="storage")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, thing_id=None, module=None):
        self.thing_id = thing_id
        self.module = module

    def __repr__(self):
        return "<Storage %r, %r>" % (self.thing_id, self.module_id)


class UpdateThread(Base):
    __tablename__ = "update_thread"
    id = Column(Integer, primary_key=True)
    thing_id = Column(String(15), nullable=False)
    lifetime = Column(Integer, nullable=False)
    interval = Column(Integer, nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    module = relationship("Module", back_populates="update_thread")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, thing_id=None, module=None, lifetime=None, interval=None):
        self.thing_id = thing_id
        self.module = module
        self.lifetime = lifetime
        self.interval = interval

    def __repr__(self):
        return "<UpdateThread %r, %r>" % (self.thing_id, self.module_id)


class Message(Base):
    __tablename__ = "message"
    id = Column(String(10), primary_key=True)
    title = Column(String(300))
    author = Column(String(50))
    body = Column(Text)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    module = relationship("Module", back_populates="messages")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, module=None, title=None, author=None, body=None):
        self.module = module
        self.title = title
        self.author = author
        self.body = body

    def __repr__(self):
        return "<Message %r, %r>" % (self.title, self.module_id)


class TriggeredSubmission(Base):
    __tablename__ = "triggered_submission"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    selftext = Column(Text, nullable=True)
    author = Column(String(50), nullable=False)
    subreddit = Column(String(50), nullable=False)
    permalink = Column(String(150), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    module = relationship("Module", back_populates="triggered_submission")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, module=None, title=None, selftext=None, author=None, subreddit=None, permalink=None):
        self.module = module
        self.title = title
        self.selftext = selftext
        self.author = author
        self.subreddit = subreddit
        self.permalink = permalink

    def __repr__(self):
        return "<TriggeredSubmission %r, %r>" % (self.title, self.module_id)


class TriggeredComment(Base):
    __tablename__ = "triggered_comment"
    id = Column(Integer, primary_key=True)
    body = Column(Text, nullable=False)
    author = Column(String(50), nullable=False)
    subreddit = Column(String(50), nullable=False)
    permalink = Column(String(150), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    module = relationship("Module", back_populates="triggered_comment")
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, module=None, body=None, author=None, subreddit=None, permalink=None):
        self.module = module
        self.body = body
        self.author = author
        self.subreddit = subreddit
        self.permalink = permalink

    def __repr__(self):
        return "<TriggeredComment %r, %r>" % (self.text, self.module_id)


class MetaStats(Base):
    __tablename__ = "meta_stats"
    id = Column(Integer, primary_key=True)
    day = Column(Date, unique=True, nullable=False)
    seen_submissions = Column(Integer, default=0)
    seen_comments = Column(Integer, default=0)
    update_cycles = Column(Integer, default=0)
    created = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_onupdate=func.now())

    def __init__(self, day=None, seen_submissions=None, seen_comments=None, update_cycles=None):
        self.day = day
        self.seen_submissions = seen_submissions
        self.seen_comments = seen_comments
        self.update_cycles = update_cycles

    def __repr__(self):
        return "<MetaStats %r>" % (self.day)
