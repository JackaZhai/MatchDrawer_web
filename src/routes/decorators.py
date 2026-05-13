"""
路由装饰器
"""

from functools import wraps
from typing import Any, Callable

from flask import jsonify, redirect, request, url_for

from ..services.auth import get_auth_service
from ..utils.errors import ApiError, AuthenticationError


def login_required(view_func: Callable) -> Callable:
    """登录要求装饰器"""

    @wraps(view_func)
    def wrapper(*args, **kwargs) -> Any:
        auth_service = get_auth_service()
        try:
            auth_service.require_auth()
        except AuthenticationError:
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view_func(*args, **kwargs)

    return wrapper


def api_login_required(view_func: Callable) -> Callable:
    """API登录要求装饰器（返回JSON错误）"""

    @wraps(view_func)
    def wrapper(*args, **kwargs) -> Any:
        auth_service = get_auth_service()
        try:
            auth_service.require_auth()
        except AuthenticationError as exc:
            return jsonify({"error": exc.message}), 401
        return view_func(*args, **kwargs)

    return wrapper


def handle_api_errors(view_func: Callable) -> Callable:
    """API错误处理装饰器"""

    @wraps(view_func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return view_func(*args, **kwargs)
        except ApiError as exc:
            return jsonify(exc.to_dict()), exc.status_code
        except Exception:
            # 记录未预期的错误
            import traceback

            traceback.print_exc()
            return jsonify({"error": "服务器内部错误"}), 500

    return wrapper
