import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.models.usage_statistics import UsageStatistics, WeeklyUsageResponse, ModelUsageResponse
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter()

####################
# Usage Statistics API
####################


@router.get("/weekly")
async def get_weekly_usage_statistics(
    start_date: Optional[str] = None,
    user=Depends(get_verified_user)
) -> WeeklyUsageResponse:
    """
    Get weekly usage statistics for all models including temporary chats.
    
    Args:
        start_date (Optional[str]): Start date in YYYY-MM-DD format. Defaults to 7 days ago.
    
    Returns:
        WeeklyUsageResponse: Aggregated weekly usage statistics
    """
    try:
        parsed_start_date = None
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        return UsageStatistics.get_model_usage_summary(parsed_start_date)
    
    except Exception as e:
        log.error(f"Error retrieving weekly usage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/model/{model_id}")
async def get_model_usage_statistics(
    model_id: str,
    days: int = 7,
    user=Depends(get_verified_user)
):
    """
    Get usage statistics for a specific model.
    
    Args:
        model_id (str): The model identifier
        days (int): Number of days to look back (default: 7)
    
    Returns:
        List of usage statistics for the specified model
    """
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days parameter must be between 1 and 365"
            )
        
        stats = UsageStatistics.get_usage_by_model_id(model_id, days)
        
        # Aggregate the results for easier consumption
        temp_count = sum(stat.message_count for stat in stats if stat.chat_type == "temporary")
        perm_count = sum(stat.message_count for stat in stats if stat.chat_type == "permanent")
        unique_users = len(set(stat.user_id for stat in stats))
        
        return {
            "model_id": model_id,
            "period_days": days,
            "temporary_messages": temp_count,
            "permanent_messages": perm_count,
            "total_messages": temp_count + perm_count,
            "unique_users": unique_users,
            "daily_breakdown": stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving model usage statistics for {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/temporary-vs-permanent")
async def get_temporary_vs_permanent_stats(
    days: int = 7,
    user=Depends(get_verified_user)
):
    """
    Get comparison statistics between temporary and permanent chat usage.
    
    Args:
        days (int): Number of days to look back (default: 7)
    
    Returns:
        Comparison statistics between temporary and permanent chats
    """
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days parameter must be between 1 and 365"
            )
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stats = UsageStatistics.get_weekly_stats(start_date)
        
        temp_total = sum(stat.message_count for stat in stats if stat.chat_type == "temporary")
        perm_total = sum(stat.message_count for stat in stats if stat.chat_type == "permanent")
        
        temp_users = len(set(stat.user_id for stat in stats if stat.chat_type == "temporary"))
        perm_users = len(set(stat.user_id for stat in stats if stat.chat_type == "permanent"))
        
        temp_models = len(set(stat.model_id for stat in stats if stat.chat_type == "temporary"))
        perm_models = len(set(stat.model_id for stat in stats if stat.chat_type == "permanent"))
        
        return {
            "period_days": days,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "temporary_chats": {
                "total_messages": temp_total,
                "unique_users": temp_users,
                "unique_models": temp_models
            },
            "permanent_chats": {
                "total_messages": perm_total,
                "unique_users": perm_users,
                "unique_models": perm_models
            },
            "totals": {
                "total_messages": temp_total + perm_total,
                "temporary_percentage": (temp_total / (temp_total + perm_total) * 100) if (temp_total + perm_total) > 0 else 0,
                "permanent_percentage": (perm_total / (temp_total + perm_total) * 100) if (temp_total + perm_total) > 0 else 0
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving temporary vs permanent statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/test-log")
async def test_log_usage(
    model_id: str = "test-model",
    is_temporary: bool = True,
    user=Depends(get_verified_user)
):
    """
    Test endpoint to manually log usage statistics.
    """
    try:
        success = UsageStatistics.log_usage(user.id, model_id, is_temporary)
        return {
            "success": success,
            "user_id": user.id,
            "model_id": model_id,
            "is_temporary": is_temporary,
            "message": "Usage logged successfully" if success else "Failed to log usage"
        }
    except Exception as e:
        log.error(f"Error in test log usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/debug/raw")
async def get_raw_usage_data(
    user=Depends(get_verified_user)
):
    """
    Debug endpoint to get raw usage statistics from database.
    """
    try:
        from open_webui.internal.db import get_db
        from open_webui.models.usage_statistics import UsageStatistic
        
        with get_db() as db:
            results = db.query(UsageStatistic).all()
            return {
                "total_records": len(results),
                "records": [
                    {
                        "id": r.id,
                        "user_id": r.user_id,
                        "model_id": r.model_id,
                        "chat_type": r.chat_type,
                        "message_count": r.message_count,
                        "date_key": r.date_key,
                        "created_at": r.created_at
                    } for r in results
                ]
            }
    except Exception as e:
        log.error(f"Error getting raw usage data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/cleanup")
async def cleanup_old_usage_statistics(
    days_to_keep: int = 30,
    user=Depends(get_verified_user)
):
    """
    Clean up old usage statistics (admin only).
    
    Args:
        days_to_keep (int): Number of days of statistics to keep (default: 30)
    
    Returns:
        Success message
    """
    try:
        # Check if user has admin role
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        if days_to_keep < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days to keep must be at least 1"
            )
        
        success = UsageStatistics.cleanup_old_statistics(days_to_keep)
        
        if success:
            return {"message": f"Successfully cleaned up usage statistics older than {days_to_keep} days"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cleanup old statistics"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error cleaning up usage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )