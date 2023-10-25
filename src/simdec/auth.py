from panel.auth import GoogleLoginHandler
from panel.io.resources import CDN_DIST


class CustomGoogleLoginHandler(GoogleLoginHandler):
    def _simple_get(self):
        html = self._login_template.render(errormessage="", PANEL_CDN=CDN_DIST)
        self.write(html)

    async def get(self):
        if "login" in self.request.uri and "state" not in self.request.uri:
            self._simple_get()
        else:
            await super().get()

    async def post(self):
        await super().get()
