import logging
import time
import uuid
from typing import Optional, List
from datetime import datetime, timedelta

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Boolean, BigInteger, Index
from sqlalchemy import func, and_

####################
# Usage Statistics DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class UsageStatistic(Base):
    __tablename__ = "usage_statistics"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    model_id = Column(String, nullable=False)
    chat_type = Column(String, nullable=False)  # "temporary" or "permanent"
    message_count = Column(Integer, default=1)
    created_at = Column(BigInteger, nullable=False)
    date_key = Column(String, nullable=False)  # YYYY-MM-DD for easy querying

    __table_args__ = (
        # Performance indexes for common queries
        Index("usage_date_key_idx", "date_key"),
        Index("usage_user_model_date_idx", "user_id", "model_id", "date_key"),
        Index("usage_model_date_idx", "model_id", "date_key"),
        Index("usage_chat_type_idx", "chat_type"),
    )


class UsageStatisticModel(BaseModel):
    id: str
    user_id: str
    model_id: str
    chat_type: str
    message_count: int
    created_at: int
    date_key: str

    class Config:
        from_attributes = True


####################
# Response Models
####################


class ModelUsageResponse(BaseModel):
    model_id: str
    temporary_messages: int = 0
    permanent_messages: int = 0
    total_messages: int = 0
    unique_users: int = 0


class WeeklyUsageResponse(BaseModel):
    start_date: str
    end_date: str
    models: List[ModelUsageResponse]
    total_temporary: int = 0
    total_permanent: int = 0
    total_messages: int = 0


####################
# Usage Statistics Table
####################


class UsageStatisticsTable:
    def log_usage(self, user_id: str, model_id: str, is_temporary: bool = False) -> bool:
        """Log a single usage event"""
        try:
            with get_db() as db:
                date_key = time.strftime("%Y-%m-%d")
                chat_type = "temporary" if is_temporary else "permanent"
                
                # Check if entry exists for today
                existing = db.query(UsageStatistic).filter(
                    and_(
                        UsageStatistic.user_id == user_id,
                        UsageStatistic.model_id == model_id,
                        UsageStatistic.chat_type == chat_type,
                        UsageStatistic.date_key == date_key
                    )
                ).first()
                
                if existing:
                    existing.message_count += 1
                else:
                    new_log = UsageStatistic(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        model_id=model_id,
                        chat_type=chat_type,
                        date_key=date_key,
                        created_at=int(time.time())
                    )
                    db.add(new_log)
                
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error logging usage: {e}")
            return False

    def get_weekly_stats(self, start_date: Optional[datetime] = None) -> List[UsageStatisticModel]:
        """Get weekly usage statistics"""
        try:
            with get_db() as db:
                if not start_date:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                else:
                    end_date = start_date + timedelta(days=7)
                
                start_key = start_date.strftime("%Y-%m-%d")
                end_key = end_date.strftime("%Y-%m-%d")
                
                results = db.query(UsageStatistic).filter(
                    and_(
                        UsageStatistic.date_key >= start_key,
                        UsageStatistic.date_key <= end_key
                    )
                ).all()
                
                return [UsageStatisticModel.model_validate(result) for result in results]
        except Exception as e:
            log.error(f"Error getting weekly stats: {e}")
            return []

    def get_model_usage_summary(self, start_date: Optional[datetime] = None) -> WeeklyUsageResponse:
        """Get aggregated weekly usage summary by model"""
        try:
            stats = self.get_weekly_stats(start_date)
            
            if not start_date:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
            else:
                end_date = start_date + timedelta(days=7)
            
            # Aggregate by model
            model_stats = {}
            total_temp = 0
            total_perm = 0
            
            for stat in stats:
                if stat.model_id not in model_stats:
                    model_stats[stat.model_id] = {
                        "temporary": 0,
                        "permanent": 0,
                        "users": set()
                    }
                
                if stat.chat_type == "temporary":
                    model_stats[stat.model_id]["temporary"] += stat.message_count
                    total_temp += stat.message_count
                else:
                    model_stats[stat.model_id]["permanent"] += stat.message_count
                    total_perm += stat.message_count
                
                model_stats[stat.model_id]["users"].add(stat.user_id)
            
            # Build response
            models = []
            for model_id, data in model_stats.items():
                models.append(ModelUsageResponse(
                    model_id=model_id,
                    temporary_messages=data["temporary"],
                    permanent_messages=data["permanent"],
                    total_messages=data["temporary"] + data["permanent"],
                    unique_users=len(data["users"])
                ))
            
            return WeeklyUsageResponse(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                models=models,
                total_temporary=total_temp,
                total_permanent=total_perm,
                total_messages=total_temp + total_perm
            )
        except Exception as e:
            log.error(f"Error getting model usage summary: {e}")
            return WeeklyUsageResponse(
                start_date="",
                end_date="",
                models=[]
            )

    def get_usage_by_model_id(self, model_id: str, days: int = 7) -> List[UsageStatisticModel]:
        """Get usage statistics for a specific model"""
        try:
            with get_db() as db:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                start_key = start_date.strftime("%Y-%m-%d")
                end_key = end_date.strftime("%Y-%m-%d")
                
                results = db.query(UsageStatistic).filter(
                    and_(
                        UsageStatistic.model_id == model_id,
                        UsageStatistic.date_key >= start_key,
                        UsageStatistic.date_key <= end_key
                    )
                ).all()
                
                return [UsageStatisticModel.model_validate(result) for result in results]
        except Exception as e:
            log.error(f"Error getting usage by model ID: {e}")
            return []

    def cleanup_old_statistics(self, days_to_keep: int = 30) -> bool:
        """Clean up old statistics older than specified days"""
        try:
            with get_db() as db:
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                cutoff_key = cutoff_date.strftime("%Y-%m-%d")
                
                deleted = db.query(UsageStatistic).filter(
                    UsageStatistic.date_key < cutoff_key
                ).delete()
                
                db.commit()
                log.info(f"Cleaned up {deleted} old usage statistics records")
                return True
        except Exception as e:
            log.error(f"Error cleaning up old statistics: {e}")
            return False


UsageStatistics = UsageStatisticsTable()