from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """
    Middleware that redirects all unauthenticated users to the login page,
    except for specific allowed paths like the login page itself.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that don't require authentication
        self.exempt_paths = [
            '/login/',
            '/admin/',
        ]
    
    def __call__(self, request):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            # Check if current path is in the exempt list
            is_exempt = any(request.path.startswith(path) for path in self.exempt_paths)
            
            if not is_exempt:
                # Redirect to login page, preserving the original path as 'next'
                return redirect(f"{reverse('shop:login')}?next={request.path}")
        
        response = self.get_response(request)
        return response
