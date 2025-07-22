from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email address.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Check if the provided username is actually an email
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            # Try to find user by email first
            if '@' in username:
                # Handle potential duplicates by getting the first active user
                users = User.objects.filter(email=username, is_active=True)
                if users.exists():
                    user = users.first()
                else:
                    # Try without active filter as fallback
                    users = User.objects.filter(email=username)
                    if users.exists():
                        user = users.first()
                    else:
                        return None
            else:
                # Fall back to username lookup for existing users
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
