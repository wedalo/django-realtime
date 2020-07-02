import datetime
from django.conf import settings
from drealtime import iShoutClient

ishout_client = iShoutClient()
ishout_cookie_name = 'ishoutToken'

class iShoutCookieMiddleware(object):
    """
    call the iShout.js API interface and get a token
    for the currently logged-in user.
    set the token received from the API as a cookie.
    
    Put this before `AuthenticationMiddleware`.
    """
    anonymous_id = None

    def get_token(self, request):
        """
        use the HTTP client to get a token from the iShout.js server,
        for the currently logged in user.
        """
        print("iShoutCookieMiddleware>> get_token")
        if request.user.is_authenticated():
            print("iShoutCookieMiddleware>> is_authenticated")
            res = ishout_client.get_token(request.user.pk)
        elif self.anonymous_id:
            print("iShoutCookieMiddleware>> is_anonymous")
            res = ishout_client.get_token(self.anonymous_id)
            # res = ishout_client.get_token('5000')
        print("iShoutCookieMiddleware>> RES: ",res)
        return res

    def has_ishout_cookie(self, request):
        cookie = request.COOKIES.get(ishout_cookie_name)
        print("iShoutCookieMiddleware COOKIE",type(cookie))
        print("iShoutCookieMiddleware COOKIE",cookie)
        if cookie:
            return True
        return False

    def determine_path(self, request):
        # Use the same path as the session cookie.
        return settings.SESSION_COOKIE_PATH

    def determine_domain(self, request):
        # Use the same domain as the session cookie.
        return settings.SESSION_COOKIE_DOMAIN

    def set_ishout_cookie(self, request, response):
        cookie_path = self.determine_path(request)
        cookie_domain = self.determine_domain(request)
        ishout_cookie_value = self.get_token(request)
        
        # calculate expiry
        cookie_age = datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE)

        utc_date = datetime.datetime.utcnow()
        cookie_date_str = '%a, %d-%b-%Y %H:%M:%S GMT'
        expires = datetime.datetime.strftime(
            utc_date + cookie_age, cookie_date_str
        )

        # Set the cookie. use the same path, domain and expiry
        # as the cookie set for the session.
        response.set_cookie(
            ishout_cookie_name,
            ishout_cookie_value,
            max_age=settings.SESSION_COOKIE_AGE,
            expires=expires,
            path=cookie_path,
            domain=cookie_domain
        )
        return response

    def has_valid_anonymous_session(self,request):
        if not ishout_client.session_anonymous_item_id:
            # print "no setting var"
            return False

        print("has_valid_anonymous_session",request.session.session_key)
        if not request.session.session_key:
            return False

        #Validate it has the member key
        self.anonymous_id = request.session.get(ishout_client.session_anonymous_item_id,False)
        if not request.session.get(ishout_client.session_anonymous_item_id,False):
            return False

        # print("UUID", self.anonymous_id)
        return True

    def process_response(self, request, response):
        # We only use it for authenticated users
        if not hasattr(request, 'user'):
            return response
            
        if not request.user.is_authenticated() and \
        ishout_cookie_name in request.COOKIES:
            # If there is no authenticated user attached to this request,
            # but the ishout.js token cookie is still present, delete it.
            # This is usually called on logout.
            print("101")
            path = self.determine_path(request)
            domain = self.determine_domain(request)
            response.delete_cookie(
                ishout_cookie_name, path=path, domain=domain
            )
            return response
        
        # skip unauthenticated users
        self.anonymous_id = None
        if not request.user.is_authenticated() and not self.has_valid_anonymous_session(request):
            print("112")
            return response

        # Check if we have the cookie already set:
        if self.has_ishout_cookie(request):
            print("117")            
            return response

        # If not, set it.
        self.set_ishout_cookie(request, response)
        print("122") 
        return response
