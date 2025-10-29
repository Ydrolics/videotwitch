import requests
from datetime import datetime, timedelta
import os
from bs4 import BeautifulSoup
import re
from pprint import pprint
import html as html_module

class TwitchAPI():

    debug = True

    def __init__(self):
        self.headers = None

    def auth(self, client_id, client_secret):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        data = f'client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials'

        try:
            response = requests.post('https://id.twitch.tv/oauth2/token', headers=headers, data=data)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        except requests.exceptions.RequestException as err:
            raise SystemExit(err)
            
        bearer = response.json()['access_token']

        self.headers = {
            'Authorization': f'Bearer {bearer}',
            'Client-Id': client_id,
        }

    def getLastsClipsFromStreamer(self, name, count, jours):

        print("récupération de " + str(count) + " clips de " + name)

        #get broadcaster id
        url = 'https://api.twitch.tv/helix/users'
        response = requests.get(url, params={'login':name}, headers = self.headers)
        broadcaster_id = response.json()['data'][0]['id']

        #recuperation des derniers clips
        fin = datetime.today()
        deb = fin - timedelta(days = jours)
        url = 'https://api.twitch.tv/helix/clips'
        response = requests.get(url, headers = self.headers, params={'broadcaster_id':broadcaster_id, 'first':count, 'started_at':deb.isoformat(timespec="seconds") + "Z", 'ended_at':fin.isoformat(timespec="seconds")+ "Z"})
        return response

    def getLastsClipsFromGame(self, jeu, count, jours,after="None"):
        print("récupération de " + str(count) + " clips du jeu " + jeu )

        #donné : nom du jeu, cf url twitch de la page du jeu, genre : lethal-company
        #récupération du game_id
        url='https://api.twitch.tv/helix/games'
        response = requests.get(url, params={'name':jeu}, headers = self.headers)
        game_id = response.json()['data'][0]['id']


        #recuperation des derniers clips
        fin = datetime.today()
        deb = fin - timedelta(days = jours)
        url = 'https://api.twitch.tv/helix/clips'
        params={'game_id':game_id, 'first':count, 'started_at':deb.isoformat(timespec="seconds") + "Z", 'ended_at':fin.isoformat(timespec="seconds")+ "Z"}
        if after!="None":
            params['after']=after
        
        response = requests.get(url, headers = self.headers, params=params)
        return response

    def extract_direct_video_url(self, page_url, headers=None, timeout=15):
        """
        Fetch page_url and try to find a direct .mp4 or .m3u8 URL.
        Returns a URL string or raises ValueError if none found.
        """
        if self.debug:
            print("Searching for a video in the url : " + page_url)
        s = requests.Session()
        # Use provided headers (e.g. Authorization/Client-Id) if present
        if headers:
            s.headers.update(headers)
        # Use a common browser UA to avoid basic bot blocks
        s.headers.setdefault('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36')

        resp = s.get(page_url, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
        if self.debug:
            print(html)
        '''
        soup = BeautifulSoup(html, 'html.parser')

        # 1) <video src="..."> or <video><source src="..."></video>
        video = soup.find('video')
        if video:
            src = video.get('src')
            if src:
                return self._normalize_url(html_module.unescape(src), page_url)
            for source in video.find_all('source'):
                src = source.get('src')
                if src:
                    return self._normalize_url(html_module.unescape(src), page_url)

        # 2) open graph meta tag like <meta property="og:video" content="...">
        og = soup.find('meta', property='og:video')
        if og and og.get('content'):
            return self._normalize_url(html_module.unescape(og['content']), page_url)

        # 3) Try common JS keys that sometimes contain URLs (quick regex)
        # Find first https://...mp4 or https://...m3u8 occurrence
        m = re.search(r'https?://[^\'"\s>]+\.mp4[^\'"\s>]*', html)
        if m:
            return self._normalize_url(html_module.unescape(m.group(0)), page_url)

        m = re.search(r'https?://[^\'"\s>]+\.m3u8[^\'"\s>]*', html)
        if m:
            return self._normalize_url(html_module.unescape(m.group(0)), page_url)

        # Nothing found
        raise ValueError("No direct mp4/m3u8 URL found on page")
        '''

        #simply use only re module to search for video url:
        videotag = None
        #videotags = re.search("<video .*\></video>", html)
        videotags = re.search("https://", html)
        if self.debug:
            print("found videos html tag :" + str(videotags))
        videotag = videotags[0]
        if videotag:
            url = videotag.split('"')[5]
            return url
        else:
            return ValueError("No video found")

         
    def _normalize_url(self, url, base_page):

        """
        Convert protocol-relative URLs and strip quotes.
        """
        url = html_module.unescape(url)
        url = url.strip().strip('\"\'')
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            # Not likely for Twitch direct media, but handle generically
            from urllib.parse import urljoin
            return urljoin(base_page, url)
        return url

    def downloadClip(self, clip, path): # clip est le dictionnaire renvoyé dans le json
        #print(clip)  # enlever
        # récupération des variables
        url=None
        try:
            url = self.extract_direct_video_url(self, clip['url'])
        except ValueError as e:
            print(f"Erreur: {e}")
            return
        date = clip['created_at']
        streamer = clip['broadcaster_name']
        titre = clip['title']
        duration = clip['duration']
        nomclip = streamer.replace('_',' ') + "_" + titre.replace('/', '|').replace('_',' ') + "_" + date + "_" + str(duration) + "_.mp4"

        # chemins relatifs au projet (utilise base_dir pour être cohérent avec upload.py)
        already_file = os.path.join(path, 'already_downloaded.txt')

        # vérif que le clip n'existe pas déjà
        if os.path.exists(already_file):
            with open(already_file, 'r') as save:
                already_downloaded = save.readlines()
        else:
            already_downloaded = []

        if (nomclip + "\n") in already_downloaded:
            print(titre + " (" + streamer + ")" + " déjà téléchargé !")
            return

        print("téléchargement du clip " + titre + " (" + streamer + ")")

        # téléchargement en streaming et écriture en morceaux pour éviter les fichiers partiels
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                target_path = os.path.join(path, nomclip)
                # ensure destination directory exists
                os.makedirs(path, exist_ok=True)
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        except requests.exceptions.RequestException as e:
            # remove partial file if exists
            if 'target_path' in locals() and os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception:
                    pass
            print(f"Erreur pendant le téléchargement du clip {titre}: {e}")
            return

        # ajout à la liste des déjà téléchargés
        try:
            with open(already_file, 'a') as save:
                save.write(nomclip + "\n")
        except Exception as e:
            print(f"Impossible d'écrire dans {already_file}: {e}")

