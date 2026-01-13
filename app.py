from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os

app = Flask(__name__)

# FFmpeg is expected in /bin relative to cwd
FFMPEG_BIN = os.path.join(os.getcwd(), 'bin')

def check_ffmpeg_available():
    """Check if ffmpeg binaries are available"""
    return (os.path.exists(os.path.join(FFMPEG_BIN, 'ffmpeg.exe')) and 
            os.path.exists(os.path.join(FFMPEG_BIN, 'ffprobe.exe')))

def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'socket_timeout': 30,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'retries': 3,
        'ignoreerrors': False,
        'no_check_certificate': True,
    }
    
    if check_ffmpeg_available():
        ydl_opts['ffmpeg_location'] = FFMPEG_BIN
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': info.get('formats'),
                'webpage_url': info.get('webpage_url'),
                'extractor': info.get('extractor_key')
            }
        except Exception as e:
            print(f"[ERROR] Failed to extract info: {str(e)}")
            return {'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def video_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    info = get_video_info(url)
    if 'error' in info:
        return jsonify({'error': info['error']}), 500
        
    return jsonify(info)

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    format_type = data.get('format', 'video') # video or audio
    quality = data.get('quality', 'best') # best, 1080p, 720p, etc.
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        has_ffmpeg = check_ffmpeg_available()
        
        # Construct format string based on quality preferences
        if format_type == 'video':
            if has_ffmpeg:
                # With FFmpeg, we can merge separate video+audio streams
                if quality == 'best':
                    format_str = 'bestvideo+bestaudio/best'
                elif quality == '1080p':
                    format_str = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
                elif quality == '720p':
                    format_str = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
                elif quality == '480p':
                    format_str = 'bestvideo[height<=480]+bestaudio/best[height<=480]/best'
                else:
                    format_str = 'bestvideo+bestaudio/best'
            else:
                # Without FFmpeg, use pre-merged formats only
                if quality == 'best':
                    format_str = 'best[ext=mp4]/best'
                elif quality == '1080p':
                    format_str = 'best[height<=1080][ext=mp4]/best[height<=1080]/best'
                elif quality == '720p':
                    format_str = 'best[height<=720][ext=mp4]/best[height<=720]/best'
                elif quality == '480p':
                    format_str = 'best[height<=480][ext=mp4]/best[height<=480]/best'
                else:
                    format_str = 'best[ext=mp4]/best'
        else:
            # Audio extraction
            if has_ffmpeg:
                format_str = 'bestaudio/best'
            else:
                # Without FFmpeg, we can't convert to MP3, so get best audio
                format_str = 'bestaudio[ext=m4a]/bestaudio/best'

        ydl_opts = {
            'format': format_str,
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'socket_timeout': 30,
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retries': 3,
            'no_check_certificate': True,
        }
        
        if has_ffmpeg:
            ydl_opts['ffmpeg_location'] = FFMPEG_BIN
            if format_type == 'video':
                ydl_opts['merge_output_format'] = 'mp4'
            
            if format_type == 'audio':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
        else:
            # Without FFmpeg, skip post-processing
            print("[WARNING] FFmpeg not available, downloading in native format")

        download_folder = os.path.join(os.getcwd(), 'downloads')
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
            
        ydl_opts['outtmpl'] = os.path.join(download_folder, '%(title)s.%(ext)s')

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if has_ffmpeg and format_type == 'audio':
                # Extension changed to mp3
                filename = os.path.splitext(filename)[0] + '.mp3'
            elif has_ffmpeg and format_type == 'video':
                # Enforce mp4 container if merge happened
                filename = os.path.splitext(filename)[0] + '.mp4'
                
        return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
