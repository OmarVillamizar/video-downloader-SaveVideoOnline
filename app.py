from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import threading
import queue

app = Flask(__name__)

# FFmpeg is expected in /bin relative to cwd
FFMPEG_BIN = os.path.join(os.getcwd(), 'bin')

def check_ffmpeg_available():
    """Check if ffmpeg binaries are available"""
    # First check system path (for Docker/Production)
    import shutil
    if shutil.which('ffmpeg') and shutil.which('ffprobe'):
        return True
        
    # Then check local bin folder (for Windows Dev)
    return (os.path.exists(os.path.join(FFMPEG_BIN, 'ffmpeg.exe')) and 
            os.path.exists(os.path.join(FFMPEG_BIN, 'ffprobe.exe')))

def get_video_info_worker(url, result_queue):
    """Worker function to extract video info"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist', # Don't extract full playlist info
        'noplaylist': True, # CRITICAL: Ignore playlist if video is part of one
        'skip_download': True,
        'socket_timeout': 15,
        'source_address': '0.0.0.0', # Force IPv4
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        'extractor_retries': 2,
        'retries': 2,
        'no_check_certificate': True,
    }
    
    import shutil
    if shutil.which('ffmpeg'):
        # If ffmpeg is in system path (Docker), we don't need to check check_ffmpeg_available() 
        # or set ffmpeg_location, yt-dlp finds it automatically.
        pass
    elif check_ffmpeg_available():
        # Fallback to local bin for Windows dev
        ydl_opts['ffmpeg_location'] = FFMPEG_BIN
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First try lightweight extraction
            try:
                info = ydl.extract_info(url, download=False, process=False)
            except:
                # Fallback to normal extraction if lightweight fails
                info = ydl.extract_info(url, download=False)
                
            # If we got a playlist object but noplaylist is on, we might need to drill down
            # But usually noplaylist: True handles it. 
            
            # If info is None or incomplete, try fuller extraction
            if not info or 'title' not in info:
                 info = ydl.extract_info(url, download=False)

            result_queue.put({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': info.get('formats'),
                'webpage_url': info.get('webpage_url'),
                'extractor': info.get('extractor_key')
            })
    except Exception as e:
        print(f"[ERROR] Failed to extract info: {str(e)}")
        result_queue.put({'error': str(e)})

def get_video_info(url, timeout=45):
    """Get video info with timeout"""
    result_queue = queue.Queue()
    thread = threading.Thread(target=get_video_info_worker, args=(url, result_queue))
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        return {'error': 'Request timed out. The video might be unavailable or the server is slow.'}
    
    try:
        return result_queue.get_nowait()
    except queue.Empty:
        return {'error': 'No response from extractor'}

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
            'source_address': '0.0.0.0', # Force IPv4 - CRITICAL for speed
            'noplaylist': True, # Ignore playlists
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retries': 3,
            'no_check_certificate': True,
        }
        
        # System ffmpeg check for Docker/Production
        import shutil
        if has_ffmpeg:
            if shutil.which('ffmpeg'):
                # System ffmpeg found
                pass
            else:
                 ydl_opts['ffmpeg_location'] = FFMPEG_BIN
                 
            if format_type == 'video':
                ydl_opts['merge_output_format'] = 'mp4'
                # Ensure audio is AAC for compatibility (fix for Opus error)
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
                
                # Update format preference to explicitly request compatible codecs if possible
                if quality == 'best':
                    format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
                elif quality == '1080p':
                    format_str = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]'
                elif quality == '720p':
                     format_str = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]'
                elif quality == '480p':
                     format_str = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]'

            if format_type == 'audio':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                
            # Update format string in options
            ydl_opts['format'] = format_str
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
