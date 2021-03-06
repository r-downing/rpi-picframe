import cherrypy
import os
import random
import requests
import time
import subprocess
from threading import Thread

import config

hue_ip = requests.get('https://www.meethue.com/api/nupnp').json()[0]['internalipaddress']
os.makedirs('public/pictures', exist_ok=True)

def watch_bulb():
    while 1:
        time.sleep(5)
        try:
            state = requests.get('http://'+hue_ip+'/api/'+config.hue_user_id+'/lights/4').json()['state']
            if state['reachable'] and state['on']:
                print("ON")
                subprocess.run('vcgencmd display_power 1'.split())
            else:
                print("OFF")
                subprocess.run('vcgencmd display_power 0'.split())
        except Exception as e:
            print('error' +repr(e))


Thread(target=watch_bulb, daemon=True).start()


class PictureFrameServer:
    def __init__(self):
        self.dir = 'public'
        self.index = 'index.html'
        self.generate_index = True
        self.pictures = []

    @cherrypy.expose
    def upload_picture(self):
        return """
        <html><body>
            <h2>Upload a file</h2>
            <form action="upload" method="post" enctype="multipart/form-data">
            filename: <input type="file" name="myFile" /><br />
            <br />
            url: <input type="text" name="url" /><br />
            <input type="submit" />
            </form>
        </body></html>
        """

    @cherrypy.expose
    def upload(self, myFile, url):
        if url:
            r = requests.get(url, allow_redirects=True)
            filename = url.split('?')[0].split('/')[-1]
            open('public/pictures/'+filename, 'wb').write(r.content)
        elif myFile:
            filename = myFile.filename
            open('public/pictures/'+filename, 'wb').write(myFile.file.read())
        self.pictures += [filename]
        raise cherrypy.HTTPRedirect('upload_picture')

    @cherrypy.expose
    def next_picture(self):
        if not self.pictures:
            self.pictures = os.listdir('public/pictures')
            random.shuffle(self.pictures)
        return 'pictures/' + self.pictures.pop()

    @cherrypy.expose
    def default(self, *a, **kw):
        uri = '/'.join(a)
        puri = self.dir + '/' + uri
        if os.path.exists(puri):
            if os.path.isdir(puri):
                if os.path.exists(puri + '/' + self.index):
                    puri += '/' + self.index
                else:
                    if self.generate_index:
                        return ('<h2>Index of /%s</h2><hr/>' % uri) + '<br/>'.join(('<a href="%s/%s">%s</a>' % (uri, f, f)) for f in os.listdir(puri))
            return cherrypy.lib.static.serve_file(os.path.abspath(puri))
        raise cherrypy.HTTPError(404, 'not found: %s' % uri)


if __name__ == '__main__':
    # cherrypy.config.update({'server.socket_port': 800})
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.quickstart(PictureFrameServer())
