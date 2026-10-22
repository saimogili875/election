from django.shortcuts import redirect
from django.conf import settings

class AuthProtectionMiddleware:
    """
    Protects all views requiring authentication with a single shared password.
    Exempts /login/, /logout/, static/, and media/ URLs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        
        # Exempted paths
        if (
            path.startswith('/login/') or 
            path.startswith('/logout/') or 
            path.startswith('/static/') or 
            path.startswith('/media/') or
            path.startswith('/admin/') # in case admin is accessed
        ):
            return self.get_response(request)

        # Check if user session has authenticated
        if not request.session.get('is_authenticated'):
            return redirect(f"/login/?next={request.path}")

        return self.get_response(request)
