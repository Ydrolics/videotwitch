
import os
import json
import google.oauth2.credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from twitchAPI import TwitchAPI as twapi
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
from moviepy.video.fx.all import resize
import random


base_dir = os.path.dirname(os.path.abspath(__file__))
debug = True

##Youtube
client_secret_youtube = os.path.join(base_dir, 'client_secret_youtube.json')
youtube_api_name = 'youtube'
youtube_api_version = 'v3'
youtube_scopes = ['https://www.googleapis.com/auth/youtube.upload']
youtube_choosen_port = 50137

##General
dir_to_upload = os.path.join(base_dir, 'shorts/')
dir_to_edit = os.path.join(base_dir, 'clips/')

##Twitch
client_secret_twitch = os.path.join(base_dir, 'client_secret_twitch.json')
streamers=["ponce","antoinedaniel","zerator","hortyunderscore","angledroit","etoiles","mynthos","joueur_du_grenier","bagherajones"]
clip_per_streamer = 1
games=[] #["Lethal Company",'Minecraft']
clip_per_game = 0
days = 7


##Youtube
def yt_authenticate(redirect_uri='urn:ietf:wg:oauth:2.0:oob'):
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_youtube, youtube_scopes, redirect_uri=redirect_uri)
    credentials = flow.run_local_server(port=youtube_choosen_port)
    return credentials

def yt_get_authenticated_service():
    credentials = None
    if os.path.exists('token.json'):
        credentials = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json')

    if not credentials or not credentials.valid:
        credentials = yt_authenticate(redirect_uri="http://localhost:" + str(youtube_choosen_port))
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())

    return build(youtube_api_name, youtube_api_version, credentials=credentials)

def upload_video_yt(youtube_server, video_file,titre="titre", description="", tags=["twitch","shorts","fr"]):
    print("uploading "+ titre + " from " + video_file)
    request_body = {
        'snippet': {
            'title': titre,
            'description': description,
            'tags': tags
        },
        'status': {
            'privacyStatus': 'private'  # Vous pouvez ajuster cela en fonction de vos besoins (private, public, unlisted)
        }
    }

    media_file = MediaFileUpload(video_file, resumable=True)

    response = youtube_server.videos().insert(
        part='snippet,status',
        body=request_body,
        media_body=media_file
    ).execute()

    print(f'Video uploaded successfully! Video ID: {response["id"]}')
    os.remove(video_file)

def upload_all():
    ytb_serv=yt_get_authenticated_service()

    for file in os.listdir(dir_to_upload):

        #récupération des informations dans le titre du clip
        filename_splitted=file.split('_')
        streamer,titre_clip,date,duration=filename_splitted[0],filename_splitted[1],filename_splitted[2],filename_splitted[-2]
        date_l = date.split('T')[0].split('-')
        date_clean=date_l[2] + "/" + date_l [1] + "/" + date_l[0]

        if file.endswith(".mp4"):
            upload_video_yt(ytb_serv, dir_to_upload + file, titre=titre_clip)

##Twitch
def twitch_authenticate():
    #notons les id donnés par twitch pour mon appli :
    with open(client_secret_twitch, 'r') as file:
        data = json.load(file)
        file.close()
        client_id=data['client_id']
        client_secret=data['client_secret']
    
    #initialisation, autorisation de twitch
    twapi.auth(twapi, client_id, client_secret)

def get_clips(max=0, streamers=streamers, clip_per_streamer=clip_per_streamer, games=games, clip_per_game=clip_per_game, days=days):
    ##récupération de tous les clips 
    allclips=[]


    if clip_per_game !=0:
        for jeu in games:
            clips_already_in=0
            after="None"

            while clips_already_in<clip_per_game:
                gameclips = twapi.getLastsClipsFromGame(twapi, jeu, 40, days, after).json()

                after=gameclips['pagination']['cursor']
                for clip in gameclips['data']:
                    if clip['language'] == 'fr' and clips_already_in<=clip_per_game:
                        allclips.append(clip)
                        clips_already_in += 1
            print(str(clip_per_game) + " clips fr sur " + jeu + " trouvés !")


    if clip_per_streamer != 0:
        for streamer in streamers:

            streamerclips = twapi.getLastsClipsFromStreamer(twapi, streamer, clip_per_streamer, days).json()['data']
            allclips = allclips + streamerclips
    
    #filter clips to return only the max number of clips
    if max==0:
        return allclips
    else:
        nclips=len(allclips)
        indices = set(int(nclips * random.random()) for _ in range(max))
        return [allclips[i] for i in indices]

##Video editing
def makeclips(input_path, output_path):
    def formatstring(inputstr):
        return '\n'.join(inputstr[i:i+20] for i in range(0, len(inputstr), 20))



    for filename in os.listdir(input_path):
        if filename.endswith('.mp4'):
            print("making short of " + filename)

            # ajout du clip (ou skip si ffmpeg ne peut pas le lire)
            clip_path = os.path.join(input_path, filename)
            try:
                clip = VideoFileClip(clip_path, target_resolution=(607, 1080)).set_position(('center','center'))
            except Exception as e:
                print(f"Erreur en ouvrant {clip_path} avec MoviePy/ffmpeg: {e}")
                # move corrupted file to a corrupt/ subfolder for inspection
                corrupt_dir = os.path.join(input_path, 'corrupt')
                os.makedirs(corrupt_dir, exist_ok=True)
                try:
                    os.rename(clip_path, os.path.join(corrupt_dir, filename))
                    print(f"Fichier déplacé vers {corrupt_dir} pour inspection.")
                except Exception as mv_e:
                    print(f"Impossible de déplacer le fichier corrompu: {mv_e}")
                continue

            #récupération des informations dans le titre du clip
            filename_splitted=filename.split('_')
            streamer,titre,date,duration=filename_splitted[0],filename_splitted[1],filename_splitted[2],filename_splitted[-2]
            date_l = date.split('T')[0].split('-')
            date_clean=date_l[2] + "/" + date_l [1] + "/" + date_l[0]

            #création des vidéos de textes et du fond
            txt_datenom = TextClip(date_clean + " \n" + streamer, fontsize=70, color='white', size=(1080,1920)).set_position(('center',700)).set_duration(duration)
            txt_titre = TextClip(formatstring(titre), fontsize=70, color='white', size=(1080,1920), stroke_width=40).set_position(('center',-600)).set_duration(duration)
            fond = ColorClip(size=(1080,1920), color=(100,0,100)).set_duration(duration)

            #assemblage du short
            short = CompositeVideoClip([fond, clip, txt_datenom, txt_titre])
            out_name = streamer + "_" + titre.replace('/', '|') + "_" + date + "_" + str(duration) + "_.mp4"
            out_path = os.path.join(output_path, out_name)
            short.write_videofile(out_path, fps=30)
            try:
                os.remove(os.path.join(input_path, filename))
            except Exception as e:
                print(f"Impossible de supprimer {filename}: {e}")
    
    if debug:
        print("All videos edited !!!\n")

if __name__ == "__main__":
    if debug:
        print("Twitch authentification ...\n")
    twitch_authenticate()

    #count the number of clips not exported yet
    nclips = sum(1 for file in os.listdir(dir_to_upload) if file.endswith(".mp4"))
    if debug:
        print("Getting " + str(10-nclips) + "clips\n")

    #get enough clips to reach 10 clips
    for clip in get_clips(max=10-nclips):
        twapi.downloadClip(twapi, clip, dir_to_edit)
    
    if debug:
        print("Starting video editing ...\n")
    #make videos
    makeclips(dir_to_edit, dir_to_upload)

    if debug:
        print("Starting uploading ...")
    #upload to youtube
    upload_all()

